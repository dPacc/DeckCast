import asyncio
import pytest

from backend.transfer.middleware import check_auth, parse_json_body, parse_query_params


class TestCheckAuth:
    def test_no_password_always_passes(self):
        assert check_auth({}, "/api/clips", None) is True

    def test_empty_password_always_passes(self):
        assert check_auth({}, "/api/clips", "") is True

    def test_bearer_token_match(self):
        headers = {"authorization": "Bearer secret123"}
        assert check_auth(headers, "/api/clips", "secret123") is True

    def test_bearer_token_mismatch(self):
        headers = {"authorization": "Bearer wrongpw"}
        assert check_auth(headers, "/api/clips", "secret123") is False

    def test_plain_token_match(self):
        headers = {"authorization": "secret123"}
        assert check_auth(headers, "/api/clips", "secret123") is True

    def test_query_string_pw(self):
        headers = {}
        assert check_auth(headers, "/api/clips?pw=secret123", "secret123") is True

    def test_query_string_pw_wrong(self):
        headers = {}
        assert check_auth(headers, "/api/clips?pw=wrong", "secret123") is False

    def test_no_auth_provided(self):
        assert check_auth({}, "/api/clips", "secret123") is False

    def test_query_string_ampersand_pw(self):
        headers = {}
        assert check_auth(headers, "/api/clips?foo=bar&pw=secret123", "secret123") is True


class TestParseJsonBody:
    def test_valid_json(self):
        body = b'{"name": "test", "value": 42}'
        result = parse_json_body(body)
        assert result == {"name": "test", "value": 42}

    def test_empty_body(self):
        assert parse_json_body(b"") == {}

    def test_invalid_json(self):
        assert parse_json_body(b"not json") == {}

    def test_non_dict_json(self):
        assert parse_json_body(b'[1, 2, 3]') == {}

    def test_nested_json(self):
        body = b'{"installed": {"client_id": "abc", "client_secret": "xyz"}}'
        result = parse_json_body(body)
        assert "installed" in result
        assert result["installed"]["client_id"] == "abc"

    def test_unicode_body(self):
        body = '{"name": "tëst"}'.encode("utf-8")
        result = parse_json_body(body)
        assert result["name"] == "tëst"


class TestParseQueryParams:
    def test_no_query_string(self):
        path, params = parse_query_params("/api/clips")
        assert path == "/api/clips"
        assert params == {}

    def test_single_param(self):
        path, params = parse_query_params("/api/clips?folder=abc")
        assert path == "/api/clips"
        assert params == {"folder": "abc"}

    def test_multiple_params(self):
        path, params = parse_query_params("/api/clips?folder=abc&search=hello")
        assert path == "/api/clips"
        assert params == {"folder": "abc", "search": "hello"}

    def test_encoded_params(self):
        path, params = parse_query_params("/api/clips?search=hello%20world")
        assert params["search"] == "hello world"

    def test_param_without_value(self):
        path, params = parse_query_params("/api/clips?flag")
        assert params == {"flag": ""}

    def test_empty_query_string(self):
        path, params = parse_query_params("/api/clips?")
        assert path == "/api/clips"
        assert params == {}
