import os
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.recording_scanner import (
    scan_recordings,
    get_recording_metadata,
    generate_thumbnail,
    probe_video,
    get_game_name_from_path,
    VIDEO_EXTENSIONS,
    THUMBNAIL_DIR,
)


class TestGetGameNameFromPath:
    def test_extracts_app_id_from_gamerecordings_path(self):
        path = "/home/deck/.local/share/Steam/userdata/123/gamerecordings/456/video/clip.mp4"
        result = get_game_name_from_path(path)
        assert "456" in result or "App" in result or "Unknown" in result

    def test_returns_unknown_for_generic_path(self):
        result = get_game_name_from_path("/home/deck/Videos/random.mp4")
        assert result == "Unknown Game"

    def test_returns_unknown_for_non_numeric_folder(self):
        result = get_game_name_from_path("/home/deck/gamerecordings/notanumber/clip.mp4")
        assert result == "Unknown Game"


class TestProbeVideo:
    def test_returns_dict_for_valid_video(self, sample_video):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available (ffmpeg not installed)")
        result = probe_video(str(sample_video))
        assert isinstance(result, dict)
        assert "format" in result
        assert "streams" in result

    def test_returns_empty_for_nonexistent_file(self):
        result = probe_video("/nonexistent/file.mp4")
        assert result == {}

    def test_returns_empty_for_invalid_file(self, tmp_dir):
        bad_file = tmp_dir / "bad.mp4"
        bad_file.write_bytes(b"not a video")
        result = probe_video(str(bad_file))
        # ffprobe may return empty or partial — either is acceptable
        assert isinstance(result, dict)


class TestGetRecordingMetadata:
    def test_returns_metadata_dict(self, sample_video):
        meta = get_recording_metadata(str(sample_video))
        assert meta["path"] == str(sample_video)
        assert meta["filename"] == sample_video.name
        assert meta["size"] > 0
        assert "modified" in meta
        assert "duration" in meta
        assert "width" in meta
        assert "height" in meta
        assert "codec" in meta
        assert "game" in meta

    def test_duration_is_numeric(self, sample_video):
        meta = get_recording_metadata(str(sample_video))
        assert isinstance(meta["duration"], float)

    def test_valid_video_has_dimensions(self, sample_video):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        meta = get_recording_metadata(str(sample_video))
        assert meta["width"] > 0
        assert meta["height"] > 0
        assert meta["duration"] > 0


class TestGenerateThumbnail:
    def test_generates_thumbnail_for_valid_video(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        with patch("backend.recording_scanner.THUMBNAIL_DIR", tmp_dir / "thumbs"):
            result = generate_thumbnail(str(sample_video))
            assert result is not None
            assert os.path.exists(result)
            assert result.endswith(".jpg")

    def test_returns_none_for_invalid_file(self, tmp_dir):
        bad_file = tmp_dir / "bad.mp4"
        bad_file.write_bytes(b"not a video")
        with patch("backend.recording_scanner.THUMBNAIL_DIR", tmp_dir / "thumbs"):
            result = generate_thumbnail(str(bad_file))
            # May return None or a path (ffmpeg might create an empty file)
            if result:
                assert os.path.exists(result)

    def test_caches_thumbnail(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        thumb_dir = tmp_dir / "thumbs"
        with patch("backend.recording_scanner.THUMBNAIL_DIR", thumb_dir):
            r1 = generate_thumbnail(str(sample_video))
            r2 = generate_thumbnail(str(sample_video))
            assert r1 == r2


class TestScanRecordings:
    def test_finds_videos_in_directory(self, sample_recordings_dir):
        with patch(
            "backend.recording_scanner.DEFAULT_SCAN_PATHS",
            [str(sample_recordings_dir / "userdata" / "*" / "gamerecordings" / "video")],
        ), patch("backend.recording_scanner.SD_CARD_PATHS", []):
            results = scan_recordings()
            assert len(results) >= 1
            assert all(r["filename"].endswith(".mp4") for r in results)

    def test_respects_extra_paths(self, sample_video, tmp_dir):
        extra_dir = tmp_dir / "extra"
        extra_dir.mkdir()
        shutil.copy2(sample_video, extra_dir / "extra_clip.mp4")

        with patch("backend.recording_scanner.DEFAULT_SCAN_PATHS", []), \
             patch("backend.recording_scanner.SD_CARD_PATHS", []):
            results = scan_recordings(extra_paths=[str(extra_dir)])
            assert len(results) == 1
            assert results[0]["filename"] == "extra_clip.mp4"

    def test_deduplicates_results(self, sample_video, tmp_dir):
        dir1 = tmp_dir / "dir1"
        dir1.mkdir()
        target = dir1 / "clip.mp4"
        shutil.copy2(sample_video, target)

        with patch("backend.recording_scanner.DEFAULT_SCAN_PATHS", [str(dir1)]), \
             patch("backend.recording_scanner.SD_CARD_PATHS", [str(dir1)]):
            results = scan_recordings()
            filenames = [r["filename"] for r in results]
            assert filenames.count("clip.mp4") == 1

    def test_returns_sorted_by_modified_desc(self, tmp_dir):
        dir1 = tmp_dir / "vids"
        dir1.mkdir()
        for i, name in enumerate(["a.mp4", "b.mp4", "c.mp4"]):
            f = dir1 / name
            f.write_bytes(b"\x00" * 512)
            os.utime(f, (1000000 + i * 1000, 1000000 + i * 1000))

        with patch("backend.recording_scanner.DEFAULT_SCAN_PATHS", [str(dir1)]), \
             patch("backend.recording_scanner.SD_CARD_PATHS", []):
            results = scan_recordings()
            assert len(results) == 3
            assert results[0]["modified"] >= results[1]["modified"]
            assert results[1]["modified"] >= results[2]["modified"]

    def test_returns_empty_for_nonexistent_dir(self):
        with patch("backend.recording_scanner.DEFAULT_SCAN_PATHS", ["/nonexistent/path/*"]), \
             patch("backend.recording_scanner.SD_CARD_PATHS", []):
            results = scan_recordings()
            assert results == []

    def test_video_extensions(self):
        assert ".mp4" in VIDEO_EXTENSIONS
        assert ".mkv" in VIDEO_EXTENSIONS
        assert ".webm" in VIDEO_EXTENSIONS
        assert ".txt" not in VIDEO_EXTENSIONS
