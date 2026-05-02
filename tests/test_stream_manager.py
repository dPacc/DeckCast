import subprocess
from unittest.mock import patch, MagicMock

import pytest

from backend.stream_manager import StreamManager


class TestStreamManagerInit:
    def test_starts_offline(self):
        sm = StreamManager()
        status = sm.status
        assert status["status"] == "offline"
        assert status["running"] is False
        assert status["error"] is None


class TestStreamManagerStart:
    def test_start_returns_success(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        with patch("backend.stream_manager.subprocess.Popen", return_value=mock_process):
            result = sm.start("rtmp://example.com/live", "key123")
            assert result["success"] is True
            assert result["status"] == "live"
            assert sm.status["running"] is True

    def test_start_with_custom_settings(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        with patch("backend.stream_manager.subprocess.Popen", return_value=mock_process) as mock_popen:
            result = sm.start(
                "rtmp://example.com/live",
                "key123",
                resolution="1920x1080",
                bitrate="6000k",
                framerate=60,
            )
            assert result["success"] is True
            call_args = mock_popen.call_args[0][0]
            assert "1920x1080" in call_args
            assert "6000k" in call_args

    def test_start_fails_when_already_running(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        with patch("backend.stream_manager.subprocess.Popen", return_value=mock_process):
            sm.start("rtmp://example.com/live", "key123")
            result = sm.start("rtmp://example.com/live", "key456")
            assert result["success"] is False
            assert "already running" in result["error"].lower()

    def test_start_handles_ffmpeg_not_found(self):
        sm = StreamManager()
        with patch("backend.stream_manager.subprocess.Popen", side_effect=FileNotFoundError):
            result = sm.start("rtmp://example.com/live", "key123")
            assert result["success"] is False
            assert sm.status["status"] == "error"

    def test_start_handles_generic_exception(self):
        sm = StreamManager()
        with patch("backend.stream_manager.subprocess.Popen", side_effect=OSError("pipe error")):
            result = sm.start("rtmp://example.com/live", "key123")
            assert result["success"] is False
            assert sm._error is not None

    def test_builds_correct_rtmp_url(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        with patch("backend.stream_manager.subprocess.Popen", return_value=mock_process) as mock_popen:
            sm.start("rtmp://a.rtmp.youtube.com/live2", "my-stream-key")
            call_args = mock_popen.call_args[0][0]
            assert "rtmp://a.rtmp.youtube.com/live2/my-stream-key" in call_args

    def test_strips_trailing_slash_from_rtmp_url(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        with patch("backend.stream_manager.subprocess.Popen", return_value=mock_process) as mock_popen:
            sm.start("rtmp://a.rtmp.youtube.com/live2/", "key123")
            call_args = mock_popen.call_args[0][0]
            assert "rtmp://a.rtmp.youtube.com/live2/key123" in call_args


class TestStreamManagerStop:
    def test_stop_when_not_running(self):
        sm = StreamManager()
        result = sm.stop()
        assert result["success"] is True
        assert result["status"] == "offline"

    def test_stop_terminates_process(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        sm._process = mock_process
        sm._status = "live"

        result = sm.stop()
        assert result["success"] is True
        assert sm.status["status"] == "offline"
        mock_process.terminate.assert_called_once()

    def test_stop_kills_if_terminate_times_out(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.terminate.return_value = None
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("ffmpeg", 5), None]
        sm._process = mock_process
        sm._status = "live"

        result = sm.stop()
        assert result["success"] is True
        mock_process.kill.assert_called_once()


class TestStreamManagerStatus:
    def test_status_reflects_dead_process(self):
        sm = StreamManager()
        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process exited
        sm._process = mock_process
        sm._status = "live"

        status = sm.status
        assert status["status"] == "offline"
        assert status["running"] is False
