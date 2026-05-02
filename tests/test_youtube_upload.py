import os
import sys
import threading
from unittest.mock import patch, MagicMock

import pytest

from backend.youtube_upload import (
    get_progress,
    upload_video,
    upload_video_async,
    YOUTUBE_CATEGORIES,
    _set_progress,
)


class TestProgressTracking:
    def test_initial_progress_is_inactive(self):
        _set_progress(percent=0, active=False, video_id=None, error=None)
        progress = get_progress()
        assert progress["active"] is False
        assert progress["percent"] == 0
        assert progress["video_id"] is None
        assert progress["error"] is None

    def test_set_and_get_progress(self):
        _set_progress(percent=50, active=True)
        progress = get_progress()
        assert progress["active"] is True
        assert progress["percent"] == 50

    def test_progress_with_video_id(self):
        _set_progress(percent=100, active=False, video_id="abc123")
        progress = get_progress()
        assert progress["video_id"] == "abc123"

    def test_progress_with_error(self):
        _set_progress(percent=0, active=False, error="Upload failed")
        progress = get_progress()
        assert progress["error"] == "Upload failed"

    def test_progress_is_thread_safe(self):
        _set_progress(percent=0, active=False)
        results = []

        def updater():
            for i in range(100):
                _set_progress(percent=i)
            results.append("done")

        threads = [threading.Thread(target=updater) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        progress = get_progress()
        assert isinstance(progress["percent"], int)


def _make_mock_google_modules(mock_creds_return=None, mock_youtube=None, mock_media=None):
    """Create mock google modules for patching lazy imports."""
    mock_auth_mod = MagicMock()
    mock_auth_mod.get_authenticated_credentials.return_value = mock_creds_return

    mock_discovery_mod = MagicMock()
    if mock_youtube:
        mock_discovery_mod.build.return_value = mock_youtube

    mock_http_mod = MagicMock()
    if mock_media:
        mock_http_mod.MediaFileUpload = mock_media

    return mock_auth_mod, mock_discovery_mod, mock_http_mod


class TestUploadVideo:
    def test_returns_error_when_not_authenticated(self, sample_video):
        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=None)
        with patch.dict("sys.modules", {"backend.youtube_auth": mock_auth}):
            # Re-import to pick up the mocked module
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            result = yu.upload_video(str(sample_video), "Test Title")
            assert result["success"] is False
            assert "not authenticated" in result["error"].lower()

    def test_returns_error_for_nonexistent_file(self):
        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=MagicMock())
        with patch.dict("sys.modules", {"backend.youtube_auth": mock_auth}):
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            result = yu.upload_video("/nonexistent/file.mp4", "Test")
            assert result["success"] is False
            assert "not found" in result["error"].lower()

    def test_successful_upload(self, sample_video):
        mock_creds = MagicMock()
        mock_youtube = MagicMock()
        mock_request = MagicMock()
        mock_status = MagicMock()
        mock_status.progress.return_value = 0.5
        mock_request.next_chunk.side_effect = [
            (mock_status, None),
            (None, {"id": "video123"}),
        ]
        mock_youtube.videos.return_value.insert.return_value = mock_request

        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=mock_creds)

        mock_discovery = MagicMock()
        mock_discovery.build.return_value = mock_youtube

        mock_http = MagicMock()

        with patch.dict("sys.modules", {
            "backend.youtube_auth": mock_auth,
            "googleapiclient.discovery": mock_discovery,
            "googleapiclient.http": mock_http,
            "googleapiclient": MagicMock(),
        }):
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            result = yu.upload_video(str(sample_video), "Test Title", "desc", ["tag1"], "unlisted", "20")
            assert result["success"] is True
            assert result["video_id"] == "video123"
            assert "youtu.be" in result["url"]

    def test_handles_upload_limit_exceeded(self, sample_video):
        mock_creds = MagicMock()
        mock_youtube = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.side_effect = Exception("uploadLimitExceeded: daily limit")
        mock_youtube.videos.return_value.insert.return_value = mock_request

        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=mock_creds)
        mock_discovery = MagicMock()
        mock_discovery.build.return_value = mock_youtube

        with patch.dict("sys.modules", {
            "backend.youtube_auth": mock_auth,
            "googleapiclient.discovery": mock_discovery,
            "googleapiclient.http": MagicMock(),
            "googleapiclient": MagicMock(),
        }):
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            result = yu.upload_video(str(sample_video), "Test")
            assert result["success"] is False
            assert "daily" in result["error"].lower()

    def test_handles_forbidden_error(self, sample_video):
        mock_creds = MagicMock()
        mock_youtube = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.side_effect = Exception("forbidden: access denied")
        mock_youtube.videos.return_value.insert.return_value = mock_request

        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=mock_creds)
        mock_discovery = MagicMock()
        mock_discovery.build.return_value = mock_youtube

        with patch.dict("sys.modules", {
            "backend.youtube_auth": mock_auth,
            "googleapiclient.discovery": mock_discovery,
            "googleapiclient.http": MagicMock(),
            "googleapiclient": MagicMock(),
        }):
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            result = yu.upload_video(str(sample_video), "Test")
            assert result["success"] is False
            assert "verification" in result["error"].lower() or "forbidden" in result["error"].lower()


class TestUploadVideoAsync:
    def test_starts_background_thread(self, sample_video):
        mock_auth, _, _ = _make_mock_google_modules(mock_creds_return=None)
        with patch.dict("sys.modules", {"backend.youtube_auth": mock_auth}):
            import importlib
            import backend.youtube_upload as yu
            importlib.reload(yu)
            with patch.object(yu, "upload_video") as mock_upload:
                mock_upload.return_value = {"success": True}
                yu.upload_video_async(str(sample_video), "Test", "desc", ["tag"], "unlisted", "20")
                import time
                time.sleep(0.2)
                assert mock_upload.called


class TestYouTubeCategories:
    def test_gaming_category_exists(self):
        assert "20" in YOUTUBE_CATEGORIES
        assert YOUTUBE_CATEGORIES["20"] == "Gaming"

    def test_all_categories_have_string_values(self):
        for key, val in YOUTUBE_CATEGORIES.items():
            assert isinstance(key, str)
            assert isinstance(val, str)
