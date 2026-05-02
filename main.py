import os
import sys
import json
import logging
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import decky_plugin
from backend.recording_scanner import scan_recordings, get_recording_metadata, generate_thumbnail
from backend.transfer_server import TransferServer
from backend.youtube_auth import (
    start_auth_flow,
    complete_auth_flow,
    clear_credentials,
    get_channel_info,
    get_stored_credentials,
    has_client_secrets,
)
from backend.youtube_upload import upload_video_async, get_progress as get_upload_progress
from backend.clip_trimmer import trim_clip
from backend.stream_manager import StreamManager

logger = decky_plugin.logger

DATA_DIR = Path.home() / "homebrew/data/DeckCast"
CONFIG_FILE = DATA_DIR / "config.json"
DEFAULT_CONFIG = Path(__file__).parent / "defaults/config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    if DEFAULT_CONFIG.exists():
        return json.loads(DEFAULT_CONFIG.read_text())
    return {}


def _save_config(config: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


class Plugin:
    transfer_server: TransferServer = None
    stream_manager: StreamManager = None

    async def _main(self):
        logger.info("DeckCast plugin loaded")
        self.transfer_server = TransferServer()
        self.stream_manager = StreamManager()

    async def _unload(self):
        logger.info("DeckCast plugin unloading")
        if self.transfer_server:
            await self.transfer_server.stop()
        if self.stream_manager:
            self.stream_manager.stop()

    # ── Recordings ──────────────────────────────────────────────

    async def get_recordings(self) -> list:
        config = _load_config()
        extra_paths = config.get("recording_paths", []) + config.get("sd_card_paths", [])
        return scan_recordings(extra_paths)

    async def get_recording_info(self, filepath: str) -> dict:
        return get_recording_metadata(filepath)

    async def get_thumbnail(self, filepath: str, timestamp: float = 5.0) -> str:
        result = generate_thumbnail(filepath, timestamp)
        if result:
            import base64
            with open(result, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return ""

    # ── Transfer Server ─────────────────────────────────────────

    async def start_transfer_server(self, port: int = 8420, password: str = None) -> dict:
        recordings = await self.get_recordings()
        return await self.transfer_server.start(recordings, port, password)

    async def stop_transfer_server(self) -> bool:
        return await self.transfer_server.stop()

    async def get_transfer_status(self) -> dict:
        return {
            "running": self.transfer_server.is_running if self.transfer_server else False,
            "ip": self.transfer_server.get_local_ip() if self.transfer_server else "",
        }

    # ── YouTube Auth ────────────────────────────────────────────

    async def youtube_auth_start(self) -> dict:
        return start_auth_flow()

    async def youtube_auth_callback(self, code: str) -> dict:
        return complete_auth_flow(code)

    async def youtube_disconnect(self) -> bool:
        clear_credentials()
        return True

    async def youtube_get_auth_status(self) -> dict:
        creds = get_stored_credentials()
        has_secrets = has_client_secrets()
        channel = None
        if creds:
            channel = get_channel_info()
        return {
            "authenticated": creds is not None,
            "has_client_secrets": has_secrets,
            "channel": channel,
        }

    # ── YouTube Upload ──────────────────────────────────────────

    async def youtube_upload(
        self,
        filepath: str,
        title: str,
        description: str = "",
        tags: list = None,
        privacy: str = "unlisted",
        category: str = "20",
    ) -> dict:
        upload_video_async(filepath, title, description, tags or [], privacy, category)
        return {"success": True, "message": "Upload started in background"}

    async def get_upload_progress(self) -> dict:
        return get_upload_progress()

    # ── Clip Trimmer ────────────────────────────────────────────

    async def trim_clip(
        self,
        filepath: str,
        start_time: float,
        end_time: float,
        output_path: str = None,
    ) -> dict:
        return trim_clip(filepath, start_time, end_time, output_path)

    # ── Live Streaming ──────────────────────────────────────────

    async def start_stream(
        self,
        rtmp_url: str,
        stream_key: str,
        resolution: str = "1280x720",
        bitrate: str = "4000k",
        framerate: int = 30,
    ) -> dict:
        return self.stream_manager.start(rtmp_url, stream_key, resolution, bitrate, framerate)

    async def stop_stream(self) -> dict:
        return self.stream_manager.stop()

    async def get_stream_status(self) -> dict:
        return self.stream_manager.status if self.stream_manager else {"status": "offline"}

    # ── Settings ────────────────────────────────────────────────

    async def get_settings(self) -> dict:
        return _load_config()

    async def save_settings(self, settings: dict) -> bool:
        _save_config(settings)
        return True
