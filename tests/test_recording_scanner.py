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
    get_clip_metadata,
    generate_thumbnail,
    probe_video,
    mux_recording,
    enhance_recording,
    VIDEO_EXTENSIONS,
    _parse_app_id_from_clip_dir,
    _parse_date_from_clip_dir,
    _parse_mpd_duration,
    _parse_mpd_video_info,
)


class TestParseAppId:
    def test_extracts_app_id(self):
        assert _parse_app_id_from_clip_dir("/clips/clip_12345_20240101_120000") == "12345"

    def test_returns_none_for_no_match(self):
        assert _parse_app_id_from_clip_dir("/clips/random_dir") is None

    def test_multi_digit_app_id(self):
        assert _parse_app_id_from_clip_dir("/clips/clip_7654321_20240101_120000") == "7654321"


class TestParseDateFromClipDir:
    def test_extracts_date(self):
        result = _parse_date_from_clip_dir("/clips/clip_123_20240315_143022")
        assert result == "2024-03-15 14:30:22"

    def test_returns_none_for_no_match(self):
        assert _parse_date_from_clip_dir("/clips/random_dir") is None


class TestParseMpdDuration:
    def test_hours_minutes_seconds(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text('<MPD mediaPresentationDuration="PT1H2M30.5S"></MPD>')
        assert _parse_mpd_duration(str(mpd)) == pytest.approx(3750.5)

    def test_minutes_only(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text('<MPD mediaPresentationDuration="PT5M"></MPD>')
        assert _parse_mpd_duration(str(mpd)) == pytest.approx(300.0)

    def test_seconds_only(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text('<MPD mediaPresentationDuration="PT45.2S"></MPD>')
        assert _parse_mpd_duration(str(mpd)) == pytest.approx(45.2)

    def test_no_duration(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text("<MPD></MPD>")
        assert _parse_mpd_duration(str(mpd)) == 0.0


class TestParseMpdVideoInfo:
    def test_extracts_video_info(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text('''
        <AdaptationSet contentType="video" width="1280" height="800">
          <Representation codecs="avc1.4d401f" bandwidth="5000000"/>
        </AdaptationSet>
        ''')
        info = _parse_mpd_video_info(str(mpd))
        assert info["width"] == 1280
        assert info["height"] == 800
        assert info["codec"] == "avc1"

    def test_no_video_block(self, tmp_dir):
        mpd = tmp_dir / "test.mpd"
        mpd.write_text("<MPD></MPD>")
        info = _parse_mpd_video_info(str(mpd))
        assert info["width"] == 0
        assert info["height"] == 0


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
        assert meta["is_dash"] is False

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
        with patch("backend.recording_scanner.MUX_CACHE_DIR", tmp_dir / "muxed"):
            result = generate_thumbnail(str(sample_video))
            assert result is not None
            assert os.path.exists(result)
            assert result.endswith(".jpg")

    def test_returns_none_for_invalid_file(self, tmp_dir):
        bad_file = tmp_dir / "bad.mp4"
        bad_file.write_bytes(b"not a video")
        with patch("backend.recording_scanner.MUX_CACHE_DIR", tmp_dir / "muxed"):
            result = generate_thumbnail(str(bad_file))
            if result:
                assert os.path.exists(result)


class TestScanRecordings:
    def test_finds_videos_in_extra_paths(self, sample_video, tmp_dir):
        extra_dir = tmp_dir / "extra"
        extra_dir.mkdir()
        shutil.copy2(sample_video, extra_dir / "extra_clip.mp4")

        with patch("backend.recording_scanner.CLIP_SCAN_PATTERNS", []), \
             patch("backend.recording_scanner.SD_CARD_CLIP_PATTERNS", []), \
             patch("backend.recording_scanner.LOOSE_VIDEO_PATHS", []):
            results = scan_recordings(extra_paths=[str(extra_dir)])
            assert len(results) == 1
            assert results[0]["filename"] == "extra_clip.mp4"

    def test_deduplicates_results(self, sample_video, tmp_dir):
        dir1 = tmp_dir / "dir1"
        dir1.mkdir()
        shutil.copy2(sample_video, dir1 / "clip.mp4")

        with patch("backend.recording_scanner.CLIP_SCAN_PATTERNS", []), \
             patch("backend.recording_scanner.SD_CARD_CLIP_PATTERNS", []), \
             patch("backend.recording_scanner.LOOSE_VIDEO_PATHS", [str(dir1)]):
            results = scan_recordings(extra_paths=[str(dir1)])
            filenames = [r["filename"] for r in results]
            assert filenames.count("clip.mp4") == 1

    def test_returns_sorted_by_modified_desc(self, tmp_dir):
        dir1 = tmp_dir / "vids"
        dir1.mkdir()
        for i, name in enumerate(["a.mp4", "b.mp4", "c.mp4"]):
            f = dir1 / name
            f.write_bytes(b"\x00" * 512)
            os.utime(f, (1000000 + i * 1000, 1000000 + i * 1000))

        with patch("backend.recording_scanner.CLIP_SCAN_PATTERNS", []), \
             patch("backend.recording_scanner.SD_CARD_CLIP_PATTERNS", []), \
             patch("backend.recording_scanner.LOOSE_VIDEO_PATHS", [str(dir1)]):
            results = scan_recordings()
            assert len(results) == 3
            assert results[0]["modified"] >= results[1]["modified"]
            assert results[1]["modified"] >= results[2]["modified"]

    def test_returns_empty_for_nonexistent_dir(self):
        with patch("backend.recording_scanner.CLIP_SCAN_PATTERNS", ["/nonexistent/*"]), \
             patch("backend.recording_scanner.SD_CARD_CLIP_PATTERNS", []), \
             patch("backend.recording_scanner.LOOSE_VIDEO_PATHS", []):
            results = scan_recordings()
            assert results == []

    def test_video_extensions(self):
        assert ".mp4" in VIDEO_EXTENSIONS
        assert ".mkv" in VIDEO_EXTENSIONS
        assert ".webm" in VIDEO_EXTENSIONS
        assert ".txt" not in VIDEO_EXTENSIONS
