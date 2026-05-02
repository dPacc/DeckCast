import os
import sys
import json
import logging
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import decky_plugin
from backend.recording_scanner import scan_recordings, get_recording_metadata, generate_thumbnail, mux_recording
from backend.transfer import TransferServer
from backend.transfer.file_manager import FileManager
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

DATA_DIR = Path("/home/deck") / "homebrew/data/DeckCast"
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
    file_manager: FileManager = None

    async def _main(self):
        logger.info("DeckCast plugin loaded")
        self.transfer_server = TransferServer()
        self.stream_manager = StreamManager()
        self.file_manager = FileManager(DATA_DIR)

    async def _unload(self):
        logger.info("DeckCast plugin unloading")
        if self.transfer_server:
            await self.transfer_server.stop()
        if self.stream_manager:
            self.stream_manager.stop()

    # ── Recordings ──────────────────────────────────────────────

    async def get_recordings(self):
        try:
            config = _load_config()
            extra_paths = config.get("recording_paths", []) + config.get("sd_card_paths", [])
            result = scan_recordings(extra_paths)
            if self.file_manager:
                from backend.transfer.handlers import _clip_id_from_recording
                for rec in result:
                    clip_id = _clip_id_from_recording(rec)
                    rec["filename"] = self.file_manager.get_display_name(clip_id, rec["filename"])
            logger.info(f"Found {len(result)} recordings")
            return result
        except Exception as e:
            logger.error(f"get_recordings failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def get_recording_info(self, filepath: str) -> dict:
        return get_recording_metadata(filepath)

    async def get_thumbnail(self, filepath: str, timestamp: float = 5.0) -> str:
        result = generate_thumbnail(filepath, timestamp)
        if result:
            import base64
            with open(result, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return ""

    async def mux_recording(self, clip_dir: str) -> dict:
        output = mux_recording(clip_dir)
        if output:
            return {"success": True, "path": output}
        return {"success": False, "error": "Failed to mux recording"}

    # ── DeckCast Sharing ──────────────────────────────────────────

    async def start_transfer_server(self, port: int = 8420, password: str = None) -> dict:
        """Start DeckCast sharing server."""
        recordings = await self.get_recordings()
        return await self.transfer_server.start(recordings, port, password)

    async def stop_transfer_server(self) -> bool:
        """Stop DeckCast sharing server."""
        return await self.transfer_server.stop()

    async def get_transfer_status(self) -> dict:
        """Get DeckCast sharing status."""
        return {
            "running": self.transfer_server.is_running if self.transfer_server else False,
            "ip": self.transfer_server.get_local_ip() if self.transfer_server else "",
        }

    # ── Recording Management ──────────────────────────────────────

    async def save_client_secrets(self, json_content: str) -> dict:
        """Save YouTube OAuth client secrets from a JSON string."""
        try:
            data = json.loads(json_content)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": "Invalid JSON"}
        if self.file_manager.save_client_secrets(data):
            return {"success": True}
        return {"success": False, "error": "Invalid client_secrets format"}

    async def delete_recording(self, clip_id: str, confirm: bool) -> dict:
        """Delete a recording from disk. Requires confirm=True."""
        if not confirm:
            return {"success": False, "error": "Confirmation required"}
        recordings = await self.get_recordings()
        from backend.transfer.handlers import _clip_id_from_recording
        recording = None
        for rec in recordings:
            if _clip_id_from_recording(rec) == clip_id:
                recording = rec
                break
        if not recording:
            return {"success": False, "error": "Recording not found"}
        ok = self.file_manager.delete_clip(recording["path"], clip_id)
        return {"success": ok}

    async def rename_recording(self, clip_id: str, new_name: str) -> dict:
        """Rename a recording (sets display name in config)."""
        if not new_name or not new_name.strip():
            return {"success": False, "error": "Name is required"}
        ok = self.file_manager.rename_clip(clip_id, new_name.strip())
        if ok:
            return {"success": True, "name": new_name.strip()}
        return {"success": False, "error": "Rename failed"}

    # ── Folder Management ──────────────────────────────────────

    async def get_folders(self) -> list:
        """Return all virtual folders."""
        return self.file_manager.get_folders()

    async def create_folder(self, name: str) -> dict:
        """Create a new virtual folder."""
        if not name or not name.strip():
            return {"success": False, "error": "Folder name is required"}
        folder = self.file_manager.create_folder(name.strip())
        return {"success": True, "folder": folder}

    async def rename_folder(self, folder_id: str, name: str) -> dict:
        """Rename a virtual folder."""
        if not name or not name.strip():
            return {"success": False, "error": "Folder name is required"}
        result = self.file_manager.rename_folder(folder_id, name.strip())
        if result:
            return {"success": True, "folder": result}
        return {"success": False, "error": "Folder not found"}

    async def delete_folder(self, folder_id: str) -> dict:
        """Delete a virtual folder (clips remain on disk)."""
        ok = self.file_manager.delete_folder(folder_id)
        if ok:
            return {"success": True}
        return {"success": False, "error": "Folder not found"}

    async def assign_clips_to_folder(self, folder_id: str, clip_ids: list) -> dict:
        """Assign clips to a folder."""
        ok = self.file_manager.assign_clips(folder_id, clip_ids)
        if ok:
            return {"success": True}
        return {"success": False, "error": "Folder not found"}

    async def remove_clips_from_folder(self, folder_id: str, clip_ids: list) -> dict:
        """Remove clips from a folder."""
        ok = self.file_manager.remove_clips(folder_id, clip_ids)
        if ok:
            return {"success": True}
        return {"success": False, "error": "Folder not found"}

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

    # ── Live Casting ───────────────────────────────────────────

    async def start_cast(self, resolution="1280x800", bitrate="4000k", framerate=30, record=False):
        """Start live casting the Steam Deck screen via HLS."""
        if not self.transfer_server or not self.transfer_server.is_running:
            return {"success": False, "error": "Start sharing first"}
        return self.transfer_server.cast_manager.start(resolution, bitrate, framerate, record)

    async def stop_cast(self):
        """Stop the active live cast."""
        if self.transfer_server and self.transfer_server.cast_manager:
            return self.transfer_server.cast_manager.stop()
        return {"success": True, "status": "offline"}

    async def get_cast_status(self):
        """Return the current live cast status."""
        if self.transfer_server and self.transfer_server.cast_manager:
            return self.transfer_server.cast_manager.status
        return {"status": "offline"}

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
