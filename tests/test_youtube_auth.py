import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.youtube_auth import (
    get_stored_credentials,
    save_credentials,
    clear_credentials,
    has_client_secrets,
    start_auth_flow,
    complete_auth_flow,
    get_authenticated_credentials,
    SCOPES,
    TOKEN_FILE,
    CLIENT_SECRETS_FILE,
)


class TestCredentialStorage:
    def test_save_and_load_credentials(self, tmp_dir):
        token_file = tmp_dir / "token.json"
        with patch("backend.youtube_auth.TOKEN_FILE", token_file), \
             patch("backend.youtube_auth.CREDENTIALS_DIR", tmp_dir):
            creds = {"token": "abc123", "refresh_token": "ref456"}
            save_credentials(creds)

            assert token_file.exists()
            # Check file permissions (should be 0o600)
            mode = oct(token_file.stat().st_mode)[-3:]
            assert mode == "600"

            loaded = get_stored_credentials()
            assert loaded["token"] == "abc123"
            assert loaded["refresh_token"] == "ref456"

    def test_get_stored_returns_none_when_no_file(self, tmp_dir):
        with patch("backend.youtube_auth.TOKEN_FILE", tmp_dir / "nonexistent.json"):
            assert get_stored_credentials() is None

    def test_get_stored_returns_none_for_corrupt_file(self, tmp_dir):
        token_file = tmp_dir / "corrupt.json"
        token_file.write_text("not valid json{{{")
        with patch("backend.youtube_auth.TOKEN_FILE", token_file):
            assert get_stored_credentials() is None

    def test_clear_credentials(self, tmp_dir):
        token_file = tmp_dir / "token.json"
        token_file.write_text('{"token": "test"}')
        with patch("backend.youtube_auth.TOKEN_FILE", token_file):
            clear_credentials()
            assert not token_file.exists()

    def test_clear_credentials_when_no_file(self, tmp_dir):
        with patch("backend.youtube_auth.TOKEN_FILE", tmp_dir / "nonexistent.json"):
            clear_credentials()  # Should not raise


class TestHasClientSecrets:
    def test_returns_true_when_file_exists(self, tmp_dir):
        secrets_file = tmp_dir / "client_secrets.json"
        secrets_file.write_text("{}")
        with patch("backend.youtube_auth.CLIENT_SECRETS_FILE", secrets_file):
            assert has_client_secrets() is True

    def test_returns_false_when_no_file(self, tmp_dir):
        with patch("backend.youtube_auth.CLIENT_SECRETS_FILE", tmp_dir / "missing.json"):
            assert has_client_secrets() is False


class TestStartAuthFlow:
    def test_returns_error_when_no_client_secrets(self, tmp_dir):
        with patch("backend.youtube_auth.CLIENT_SECRETS_FILE", tmp_dir / "missing.json"), \
             patch("backend.youtube_auth.CREDENTIALS_DIR", tmp_dir):
            result = start_auth_flow()
            assert result["success"] is False
            assert "client_secrets" in result["error"].lower()

    def test_returns_auth_url_with_valid_secrets(self, tmp_dir):
        secrets_file = tmp_dir / "client_secrets.json"
        secrets_file.write_text('{"installed": {"client_id": "test"}}')

        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = (
            "https://accounts.google.com/auth?...",
            "state123",
        )

        mock_flow_mod = MagicMock()
        mock_flow_mod.Flow.from_client_secrets_file.return_value = mock_flow_instance

        with patch.dict("sys.modules", {"google_auth_oauthlib.flow": mock_flow_mod, "google_auth_oauthlib": MagicMock()}):
            import importlib
            import backend.youtube_auth as ya
            importlib.reload(ya)
            with patch.object(ya, "CLIENT_SECRETS_FILE", secrets_file), \
                 patch.object(ya, "CREDENTIALS_DIR", tmp_dir):
                result = ya.start_auth_flow()
                assert result["success"] is True
                assert "auth_url" in result


class TestCompleteAuthFlow:
    def test_returns_error_when_no_client_secrets(self, tmp_dir):
        with patch("backend.youtube_auth.CLIENT_SECRETS_FILE", tmp_dir / "missing.json"):
            result = complete_auth_flow("somecode")
            assert result["success"] is False

    def test_saves_credentials_on_success(self, tmp_dir):
        secrets_file = tmp_dir / "client_secrets.json"
        secrets_file.write_text('{}')
        token_file = tmp_dir / "token.json"

        mock_creds = MagicMock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "client_id"
        mock_creds.client_secret = "client_secret"
        mock_creds.scopes = set(SCOPES)

        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds

        with patch("backend.youtube_auth.CLIENT_SECRETS_FILE", secrets_file), \
             patch("backend.youtube_auth.TOKEN_FILE", token_file), \
             patch("backend.youtube_auth.CREDENTIALS_DIR", tmp_dir):
            try:
                from google_auth_oauthlib.flow import Flow
                with patch.object(Flow, "from_client_secrets_file", return_value=mock_flow):
                    result = complete_auth_flow("testcode")
                    assert result["success"] is True
                    assert token_file.exists()
            except ImportError:
                pytest.skip("google-auth-oauthlib not installed")


class TestScopes:
    def test_includes_upload_scope(self):
        assert any("upload" in s for s in SCOPES)

    def test_includes_youtube_scope(self):
        assert any("youtube" in s for s in SCOPES)
