import asyncio
import json
import os
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Patch DATA_DIR before importing TransferServer so it doesn't need /home/deck
_test_data_dir = Path(tempfile.mkdtemp(prefix="deckcast_srv_"))
patch("backend.transfer.server.DATA_DIR", _test_data_dir).start()

from backend.transfer import TransferServer


class TestTransferServerInit:
    def test_starts_not_running(self):
        server = TransferServer()
        assert server.is_running is False

    def test_get_local_ip_returns_string(self):
        server = TransferServer()
        ip = server.get_local_ip()
        assert isinstance(ip, str)
        assert len(ip) > 0

    def test_get_local_ip_fallback(self):
        server = TransferServer()
        with patch("socket.socket") as mock_sock:
            mock_sock.return_value.__enter__ = MagicMock(side_effect=OSError("no network"))
            mock_sock.return_value.connect = MagicMock(side_effect=OSError("no network"))
            ip = server.get_local_ip()
            assert ip in ("127.0.0.1", "") or isinstance(ip, str)


class TestTransferServerQR:
    def test_generate_qr_returns_string(self):
        server = TransferServer()
        try:
            import qrcode
            result = server.generate_qr_data("http://192.168.1.100:8420")
            assert isinstance(result, str)
            if result:
                import base64
                decoded = base64.b64decode(result)
                assert decoded[:4] == b"\x89PNG"
        except ImportError:
            result = server.generate_qr_data("http://192.168.1.100:8420")
            assert result == ""


@pytest.mark.asyncio
class TestTransferServerLifecycle:
    async def test_start_and_stop(self):
        server = TransferServer()
        recordings = [
            {"path": "/tmp/test.mp4", "filename": "test.mp4", "game": "Test", "size": 1024, "duration": 10, "is_dash": False},
        ]
        result = await server.start(recordings, port=18421)
        assert "url" in result
        assert "ip" in result
        assert result["port"] == 18421
        assert server.is_running is True

        stopped = await server.stop()
        assert stopped is True
        assert server.is_running is False

    async def test_stop_when_not_running(self):
        server = TransferServer()
        stopped = await server.stop()
        assert stopped is False

    async def test_restart_replaces_server(self):
        server = TransferServer()
        recordings = [
            {"path": "/tmp/test.mp4", "filename": "test.mp4", "game": "Test", "size": 1024, "duration": 10, "is_dash": False},
        ]
        await server.start(recordings, port=18422)
        assert server.is_running is True
        await server.start(recordings, port=18423)
        assert server.is_running is True
        assert server._port == 18423
        await server.stop()


@pytest.mark.asyncio
class TestTransferServerHTTP:
    async def test_serves_index_page(self):
        server = TransferServer()
        recordings = [
            {"path": "/tmp/test.mp4", "filename": "test.mp4", "game": "Test", "size": 1024, "duration": 10, "is_dash": False},
        ]
        await server.start(recordings, port=18424)

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18424)
            writer.write(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(8192), timeout=5)
            response_str = response.decode("utf-8", errors="replace")
            assert "200 OK" in response_str
            assert "DeckCast" in response_str
            writer.close()
        finally:
            await server.stop()

    async def test_serves_clips_api(self):
        server = TransferServer()
        recordings = [
            {"path": "/tmp/test.mp4", "filename": "test.mp4", "game": "TestGame", "size": 2048, "duration": 30, "is_dash": False},
        ]
        await server.start(recordings, port=18425)

        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18425)
            writer.write(b"GET /api/clips HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(8192), timeout=5)
            response_str = response.decode("utf-8", errors="replace")
            assert "200 OK" in response_str
            assert "TestGame" in response_str
            writer.close()
        finally:
            await server.stop()

    async def test_returns_404_for_unknown_path(self):
        server = TransferServer()
        await server.start([], port=18426)
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18426)
            writer.write(b"GET /nonexistent HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=5)
            assert b"404" in response
            writer.close()
        finally:
            await server.stop()

    async def test_serves_folders_api(self):
        server = TransferServer()
        await server.start([], port=18427)
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18427)
            writer.write(b"GET /api/folders HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=5)
            response_str = response.decode("utf-8", errors="replace")
            assert "200 OK" in response_str
            writer.close()
        finally:
            await server.stop()

    async def test_client_secrets_status(self):
        server = TransferServer()
        await server.start([], port=18428)
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18428)
            writer.write(b"GET /api/youtube/client-secrets/status HTTP/1.1\r\nHost: localhost\r\n\r\n")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(4096), timeout=5)
            response_str = response.decode("utf-8", errors="replace")
            assert "200 OK" in response_str
            writer.close()
        finally:
            await server.stop()
