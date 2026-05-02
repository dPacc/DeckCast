import asyncio
import base64
import io
import logging
import socket
from pathlib import Path
from typing import Optional

from backend.cast_manager import CastManager
from backend.transfer import file_manager as fm_module
from backend.transfer import handlers
from backend.transfer import router
from backend.transfer.middleware import check_auth, parse_query_params, parse_request
from backend.transfer.responses import send_error, send_json

logger = logging.getLogger("DeckCast")

DECK_HOME = Path("/home/deck")
DATA_DIR = DECK_HOME / "homebrew/data/DeckCast"
WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class TransferServer:
    """
    Async HTTP server for browsing and downloading Steam Deck recordings
    over Wi-Fi. Runs as a raw asyncio TCP server (no framework dependencies).

    Public interface:
        start(recordings, port, password) -> dict
        stop() -> bool
        is_running -> bool
        get_local_ip() -> str
        generate_qr_data(url) -> str
    """

    def __init__(self):
        self._server: Optional[asyncio.AbstractServer] = None
        self._recordings: list[dict] = []
        self._password: Optional[str] = None
        self._port: int = 8420
        self._file_manager: Optional[fm_module.FileManager] = None
        self._cast_manager: CastManager = CastManager()

    # ── Public API ──────────────────────────────────────────────

    async def start(
        self,
        recordings: list[dict],
        port: int = 8420,
        password: Optional[str] = None,
    ) -> dict:
        """
        Start the transfer server.

        Args:
            recordings: List of recording dicts from scan_recordings().
            port: TCP port to listen on (default 8420).
            password: Optional password for access control.

        Returns:
            dict with keys: url, ip, port, qr_base64
        """
        if self._server is not None:
            await self.stop()

        self._recordings = recordings
        self._password = password
        self._port = port
        self._file_manager = fm_module.FileManager(DATA_DIR)

        self._server = await asyncio.start_server(
            self._handle_connection, "0.0.0.0", port
        )

        ip = self.get_local_ip()
        url = f"http://{ip}:{port}"
        qr_base64 = self.generate_qr_data(url)

        logger.info(f"Transfer server started at {url}")
        return {"url": url, "ip": ip, "port": port, "qr_base64": qr_base64}

    async def stop(self) -> bool:
        """Stop the transfer server. Cast continues running independently."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("Transfer server stopped")
            return True
        return False

    @property
    def is_running(self) -> bool:
        """True if the server is currently listening."""
        return self._server is not None

    @property
    def cast_manager(self) -> CastManager:
        """Access the CastManager instance."""
        return self._cast_manager

    @staticmethod
    def get_local_ip() -> str:
        """Detect the local LAN IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def generate_qr_data(url: str) -> str:
        """Generate a QR code PNG as base64, or empty string if qrcode is unavailable."""
        try:
            import qrcode
            qr = qrcode.make(url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        except ImportError:
            logger.warning("qrcode library not available, returning URL only")
            return ""

    # ── Connection handler ──────────────────────────────────────

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single HTTP connection: parse, auth, route, respond."""
        try:
            # 1. Parse the request
            method, path, headers, body = await parse_request(reader)
            if not method or not path:
                writer.close()
                return

            # 2. Check authentication
            if not check_auth(headers, path, self._password):
                await send_json(writer, {"error": "Unauthorized"}, status=401)
                return

            # 3. Strip query params for routing; keep them in context
            clean_path, params = parse_query_params(path)

            # 4. Match route
            match = router.match_route(method, clean_path)

            if match is None:
                # Check if any route matches the path (wrong method -> 405)
                if router.match_route_any(clean_path):
                    await send_error(writer, 405, "Method Not Allowed")
                else:
                    await send_error(writer, 404, "Not Found")
                return

            handler_name, groups = match

            # 5. Build contexts
            request_ctx = {
                "method": method,
                "path": path,
                "clean_path": clean_path,
                "headers": headers,
                "body": body,
                "params": params,
                "groups": groups,
            }

            server_ctx = {
                "recordings": self._recordings,
                "file_manager": self._file_manager,
                "web_dir": str(WEB_DIR),
                "password": self._password,
                "cast_manager": self._cast_manager,
            }

            # 6. Call the handler
            handler_fn = getattr(handlers, handler_name, None)
            if handler_fn is None:
                logger.error(f"Handler not found: {handler_name}")
                await send_error(writer, 500, "Internal Server Error")
                return

            await handler_fn(writer, request_ctx, server_ctx)

        except ConnectionResetError:
            pass
        except Exception as e:
            logger.error(f"Transfer server error: {e}")
            try:
                await send_error(writer, 500, "Internal Server Error")
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
