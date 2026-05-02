import asyncio
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from backend.transfer.handlers import (
    _clip_id_from_recording,
    _find_recording,
    list_clips,
    serve_index,
    rename_clip,
    delete_clip,
    create_folder,
    list_folders,
    rename_folder,
    delete_folder,
    assign_clips,
    remove_clips,
    upload_client_secrets,
    client_secrets_status,
    download_file,
    download_enhanced_file,
)
from backend.transfer.file_manager import FileManager


@pytest.fixture
def data_dir():
    d = tempfile.mkdtemp(prefix="deckcast_handler_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def fm(data_dir):
    return FileManager(data_dir)


@pytest.fixture
def mock_writer():
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


@pytest.fixture
def sample_recordings(data_dir):
    vid = data_dir / "test_clip.mp4"
    vid.write_bytes(b"\x00" * 256)
    return [
        {
            "path": str(vid),
            "filename": "TestGame - 2024-01-01.mp4",
            "game": "TestGame",
            "size": 256,
            "duration": 10.0,
            "width": 1280,
            "height": 800,
            "codec": "h264",
            "modified": 1704067200.0,
            "is_dash": False,
        }
    ]


@pytest.fixture
def dash_recordings(data_dir):
    clip_dir = data_dir / "clip_12345_20240101_120000"
    clip_dir.mkdir()
    (clip_dir / "session.mpd").write_text("<MPD/>")
    (clip_dir / "chunk.m4s").write_bytes(b"\x00" * 100)
    return [
        {
            "path": str(clip_dir),
            "filename": "TestGame - 2024-01-01.mp4",
            "game": "TestGame",
            "size": 100,
            "duration": 10.0,
            "width": 1280,
            "height": 800,
            "codec": "h264",
            "modified": 1704067200.0,
            "is_dash": True,
        }
    ]


def make_request_ctx(method="GET", path="/", body=b"", params=None, groups=None):
    return {
        "method": method,
        "path": path,
        "clean_path": path,
        "headers": {},
        "body": body,
        "params": params or {},
        "groups": groups or [],
    }


def make_server_ctx(recordings, fm, web_dir="/tmp"):
    return {
        "recordings": recordings,
        "file_manager": fm,
        "web_dir": web_dir,
        "password": None,
    }


class TestClipIdHelpers:
    def test_dash_clip_id(self):
        rec = {"path": "/home/deck/clips/clip_12345_20240101", "is_dash": True}
        assert _clip_id_from_recording(rec) == "clip_12345_20240101"

    def test_loose_file_id(self):
        rec = {"path": "/home/deck/Videos/gameplay.mp4", "is_dash": False}
        assert _clip_id_from_recording(rec) == "gameplay"

    def test_find_recording_found(self):
        recs = [
            {"path": "/clips/clip_a", "is_dash": True},
            {"path": "/clips/clip_b", "is_dash": True},
        ]
        result = _find_recording(recs, "clip_b")
        assert result is not None
        assert result["path"] == "/clips/clip_b"

    def test_find_recording_not_found(self):
        recs = [{"path": "/clips/clip_a", "is_dash": True}]
        assert _find_recording(recs, "nonexistent") is None


@pytest.mark.asyncio
class TestListClips:
    async def test_returns_all_clips(self, mock_writer, sample_recordings, fm):
        req = make_request_ctx()
        srv = make_server_ctx(sample_recordings, fm)
        await list_clips(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written
        assert b"TestGame" in written

    async def test_search_filter(self, mock_writer, sample_recordings, fm):
        req = make_request_ctx(params={"search": "nonexistent"})
        srv = make_server_ctx(sample_recordings, fm)
        await list_clips(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        body = written.split(b"\r\n\r\n", 1)[1]
        data = json.loads(body)
        assert data == []


@pytest.mark.asyncio
class TestServeIndex:
    async def test_serves_index(self, mock_writer, fm, data_dir):
        web_dir = data_dir / "web"
        web_dir.mkdir()
        (web_dir / "index.html").write_text("<html>DeckCast</html>")
        req = make_request_ctx()
        srv = make_server_ctx([], fm, str(web_dir))
        await serve_index(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written
        assert b"DeckCast" in written

    async def test_missing_index(self, mock_writer, fm, data_dir):
        req = make_request_ctx()
        srv = make_server_ctx([], fm, str(data_dir / "nonexistent"))
        await serve_index(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"404" in written


@pytest.mark.asyncio
class TestRenameClip:
    async def test_rename_success(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        body = json.dumps({"name": "New Name"}).encode()
        req = make_request_ctx(method="PUT", body=body, groups=[clip_id])
        srv = make_server_ctx(sample_recordings, fm)
        await rename_clip(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b'"success": true' in written or b'"success":true' in written

    async def test_rename_not_found(self, mock_writer, sample_recordings, fm):
        body = json.dumps({"name": "New Name"}).encode()
        req = make_request_ctx(method="PUT", body=body, groups=["nonexistent"])
        srv = make_server_ctx(sample_recordings, fm)
        await rename_clip(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"404" in written

    async def test_rename_empty_name(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        body = json.dumps({"name": ""}).encode()
        req = make_request_ctx(method="PUT", body=body, groups=[clip_id])
        srv = make_server_ctx(sample_recordings, fm)
        await rename_clip(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"400" in written


@pytest.mark.asyncio
class TestDeleteClip:
    async def test_delete_requires_confirm(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        body = json.dumps({}).encode()
        req = make_request_ctx(method="DELETE", body=body, groups=[clip_id])
        srv = make_server_ctx(sample_recordings, fm)
        await delete_clip(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"400" in written

    async def test_delete_success(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        body = json.dumps({"confirm": True}).encode()
        req = make_request_ctx(method="DELETE", body=body, groups=[clip_id])
        srv = make_server_ctx(sample_recordings, fm)
        await delete_clip(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b'"success": true' in written or b'"success":true' in written


@pytest.mark.asyncio
class TestFolderHandlers:
    async def test_list_folders_empty(self, mock_writer, fm):
        req = make_request_ctx()
        srv = make_server_ctx([], fm)
        await list_folders(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written
        body = written.split(b"\r\n\r\n", 1)[1]
        assert json.loads(body) == []

    async def test_create_folder(self, mock_writer, fm):
        body = json.dumps({"name": "Test Folder"}).encode()
        req = make_request_ctx(method="POST", body=body)
        srv = make_server_ctx([], fm)
        await create_folder(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"201" in written
        assert b"Test Folder" in written

    async def test_create_folder_empty_name(self, mock_writer, fm):
        body = json.dumps({"name": ""}).encode()
        req = make_request_ctx(method="POST", body=body)
        srv = make_server_ctx([], fm)
        await create_folder(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"400" in written

    async def test_delete_folder(self, mock_writer, fm):
        folder = fm.create_folder("ToDelete")
        req = make_request_ctx(method="DELETE", groups=[folder["id"]])
        srv = make_server_ctx([], fm)
        await delete_folder(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b'"success": true' in written or b'"success":true' in written

    async def test_delete_nonexistent_folder(self, mock_writer, fm):
        req = make_request_ctx(method="DELETE", groups=["fake_id"])
        srv = make_server_ctx([], fm)
        await delete_folder(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"404" in written


@pytest.mark.asyncio
class TestAssignClips:
    async def test_assign_clips(self, mock_writer, fm):
        folder = fm.create_folder("F1")
        body = json.dumps({"clip_ids": ["clip_a", "clip_b"]}).encode()
        req = make_request_ctx(method="POST", body=body, groups=[folder["id"]])
        srv = make_server_ctx([], fm)
        await assign_clips(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b'"success": true' in written or b'"success":true' in written

    async def test_assign_empty_list(self, mock_writer, fm):
        folder = fm.create_folder("F1")
        body = json.dumps({"clip_ids": []}).encode()
        req = make_request_ctx(method="POST", body=body, groups=[folder["id"]])
        srv = make_server_ctx([], fm)
        await assign_clips(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"400" in written


@pytest.mark.asyncio
class TestClientSecrets:
    async def test_upload_valid_secrets(self, mock_writer, fm):
        secrets = {"installed": {"client_id": "abc", "client_secret": "xyz"}}
        body = json.dumps(secrets).encode()
        req = make_request_ctx(method="POST", body=body)
        srv = make_server_ctx([], fm)
        await upload_client_secrets(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b'"success": true' in written or b'"success":true' in written

    async def test_upload_empty_body(self, mock_writer, fm):
        req = make_request_ctx(method="POST", body=b"")
        srv = make_server_ctx([], fm)
        await upload_client_secrets(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"400" in written

    async def test_secrets_status(self, mock_writer, fm):
        req = make_request_ctx()
        srv = make_server_ctx([], fm)
        await client_secrets_status(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written
        assert b"has_client_secrets" in written


@pytest.mark.asyncio
class TestDownload:
    async def test_download_regular_file(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        req = make_request_ctx(groups=[clip_id])
        srv = make_server_ctx(sample_recordings, fm)
        await download_file(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written or b"206" in written

    async def test_download_not_found(self, mock_writer, fm):
        req = make_request_ctx(groups=["nonexistent"])
        srv = make_server_ctx([], fm)
        await download_file(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"404" in written

    async def test_download_enhanced_not_found(self, mock_writer, fm):
        req = make_request_ctx(groups=["nonexistent"])
        srv = make_server_ctx([], fm)
        await download_enhanced_file(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"404" in written

    async def test_download_enhanced_falls_back(self, mock_writer, sample_recordings, fm):
        clip_id = _clip_id_from_recording(sample_recordings[0])
        req = make_request_ctx(groups=[clip_id], params={"res": "1920x1080"})
        srv = make_server_ctx(sample_recordings, fm)
        with patch("backend.recording_scanner.enhance_recording", return_value=None):
            await download_enhanced_file(mock_writer, req, srv)
        written = b"".join(call.args[0] for call in mock_writer.write.call_args_list)
        assert b"200 OK" in written or b"206" in written
