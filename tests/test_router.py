import pytest

from backend.transfer.router import match_route, match_route_any


class TestMatchRoute:
    def test_root_get(self):
        result = match_route("GET", "/")
        assert result == ("serve_index", [])

    def test_root_post_no_match(self):
        result = match_route("POST", "/")
        assert result is None

    def test_static_file(self):
        result = match_route("GET", "/static/css/styles.css")
        assert result is not None
        handler, groups = result
        assert handler == "serve_static"
        assert groups == ["css/styles.css"]

    def test_api_clips_get(self):
        result = match_route("GET", "/api/clips")
        assert result == ("list_clips", [])

    def test_api_clips_post_no_match(self):
        assert match_route("POST", "/api/clips") is None

    def test_clip_thumbnail(self):
        result = match_route("GET", "/api/clips/my_clip_123/thumbnail")
        assert result is not None
        handler, groups = result
        assert handler == "serve_thumbnail"
        assert groups == ["my_clip_123"]

    def test_rename_clip(self):
        result = match_route("PUT", "/api/clips/clip_abc/rename")
        assert result is not None
        assert result[0] == "rename_clip"
        assert result[1] == ["clip_abc"]

    def test_delete_clip(self):
        result = match_route("DELETE", "/api/clips/clip_abc")
        assert result is not None
        assert result[0] == "delete_clip"
        assert result[1] == ["clip_abc"]

    def test_folders_get(self):
        assert match_route("GET", "/api/folders") == ("list_folders", [])

    def test_folders_post(self):
        assert match_route("POST", "/api/folders") == ("create_folder", [])

    def test_folder_put(self):
        result = match_route("PUT", "/api/folders/abc123")
        assert result == ("rename_folder", ["abc123"])

    def test_folder_delete(self):
        result = match_route("DELETE", "/api/folders/abc123")
        assert result == ("delete_folder", ["abc123"])

    def test_folder_assign_clips(self):
        result = match_route("POST", "/api/folders/abc123/clips")
        assert result == ("assign_clips", ["abc123"])

    def test_folder_remove_clips(self):
        result = match_route("DELETE", "/api/folders/abc123/clips")
        assert result == ("remove_clips", ["abc123"])

    def test_download(self):
        result = match_route("GET", "/download/test_video.mp4")
        assert result is not None
        assert result[0] == "download_file"
        assert result[1] == ["test_video.mp4"]

    def test_download_enhanced(self):
        result = match_route("GET", "/download-enhanced/test_video.mp4")
        assert result is not None
        assert result[0] == "download_enhanced_file"
        assert result[1] == ["test_video.mp4"]

    def test_upload_client_secrets(self):
        result = match_route("POST", "/api/youtube/client-secrets")
        assert result == ("upload_client_secrets", [])

    def test_client_secrets_status(self):
        result = match_route("GET", "/api/youtube/client-secrets/status")
        assert result == ("client_secrets_status", [])

    def test_nonexistent_path(self):
        assert match_route("GET", "/api/nonexistent") is None

    def test_method_case_insensitive(self):
        assert match_route("get", "/") is not None
        assert match_route("Get", "/") is not None


class TestMatchRouteAny:
    def test_existing_path_wrong_method(self):
        assert match_route_any("/") is True

    def test_nonexistent_path(self):
        assert match_route_any("/api/nonexistent") is False

    def test_clips_path(self):
        assert match_route_any("/api/clips") is True

    def test_folder_path(self):
        assert match_route_any("/api/folders/abc") is True
