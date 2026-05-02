import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.clip_trimmer import trim_clip, TRIM_OUTPUT_DIR


class TestTrimClip:
    def test_trims_valid_video(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available (ffmpeg not installed)")
        output = tmp_dir / "trimmed.mp4"
        result = trim_clip(str(sample_video), 0.0, 2.0, str(output))
        assert result["success"] is True
        assert os.path.exists(result["output_path"])
        assert result["size"] > 0

    def test_returns_error_for_nonexistent_file(self):
        result = trim_clip("/nonexistent/file.mp4", 0, 5)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_returns_error_when_end_before_start(self, sample_video):
        result = trim_clip(str(sample_video), 5.0, 2.0)
        assert result["success"] is False
        assert "end time" in result["error"].lower()

    def test_returns_error_when_end_equals_start(self, sample_video):
        result = trim_clip(str(sample_video), 2.0, 2.0)
        assert result["success"] is False

    def test_clamps_negative_start_to_zero(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        output = tmp_dir / "trimmed_neg.mp4"
        result = trim_clip(str(sample_video), -5.0, 2.0, str(output))
        assert result["success"] is True

    def test_auto_generates_output_path(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        with patch("backend.clip_trimmer.TRIM_OUTPUT_DIR", tmp_dir):
            result = trim_clip(str(sample_video), 0.0, 2.0)
            assert result["success"] is True
            assert "trimmed" in result["output_path"]

    def test_avoids_overwriting_existing_output(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        with patch("backend.clip_trimmer.TRIM_OUTPUT_DIR", tmp_dir):
            # Create first trimmed file
            existing = tmp_dir / f"{sample_video.stem}_trimmed.mp4"
            existing.write_bytes(b"\x00" * 100)

            result = trim_clip(str(sample_video), 0.0, 2.0)
            assert result["success"] is True
            assert result["output_path"] != str(existing)
            assert "_trimmed_1" in result["output_path"] or "_trimmed_" in result["output_path"]


class TestTrimClipEdgeCases:
    def test_handles_ffmpeg_timeout(self, sample_video, tmp_dir):
        """Verify the timeout parameter is passed to subprocess."""
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        output = tmp_dir / "timeout_test.mp4"
        with patch("backend.clip_trimmer.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 120)
            result = trim_clip(str(sample_video), 0.0, 2.0, str(output))
            assert result["success"] is False
            assert "timed out" in result["error"].lower()

    def test_handles_ffmpeg_error_return_code(self, sample_video, tmp_dir):
        if sample_video.stat().st_size <= 1024:
            pytest.skip("No real video available")
        output = tmp_dir / "error_test.mp4"
        with patch("backend.clip_trimmer.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="Some ffmpeg error"
            )
            result = trim_clip(str(sample_video), 0.0, 2.0, str(output))
            assert result["success"] is False
            assert "error" in result["error"].lower()
