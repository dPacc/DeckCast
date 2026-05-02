import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")


class FileManager:
    """
    Manages virtual folders, clip renames, deletions, and client secrets.

    All config data is stored as JSON files in the data directory. Folders are
    virtual -- clips are not moved on disk, only tagged via config. Writes are
    atomic (write temp, then os.rename).
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._folders_file = self._data_dir / "folders.json"
        self._renames_file = self._data_dir / "renames.json"
        self._secrets_file = self._data_dir / "client_secrets.json"
        self._mux_cache_dir = self._data_dir / "muxed"
        self._thumb_dir = self._data_dir / "thumbnails"

        self._folders: dict = self._load_json(self._folders_file, {"folders": []})
        self._renames: dict = self._load_json(self._renames_file, {"renames": {}})

    # ── Persistence helpers ────────────────────────────────────

    @staticmethod
    def _load_json(filepath: Path, default: dict) -> dict:
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text("utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load {filepath}: {e}")
        return dict(default)  # copy

    def _save_json(self, filepath: Path, data: dict) -> None:
        """Atomic write: write to temp file then rename."""
        tmp = filepath.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.rename(str(tmp), str(filepath))
        except OSError as e:
            logger.error(f"Failed to save {filepath}: {e}")
            # Clean up temp on failure
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _save_folders(self) -> None:
        self._save_json(self._folders_file, self._folders)

    def _save_renames(self) -> None:
        self._save_json(self._renames_file, self._renames)

    @staticmethod
    def _gen_id() -> str:
        return uuid.uuid4().hex[:8]

    # ── Folders (virtual, config-backed) ───────────────────────

    def get_folders(self) -> list[dict]:
        """Return all folders with their clip assignments."""
        return list(self._folders.get("folders", []))

    def create_folder(self, name: str) -> dict:
        """Create a new virtual folder. Returns the folder dict."""
        folder = {
            "id": self._gen_id(),
            "name": name.strip(),
            "clips": [],
        }
        self._folders.setdefault("folders", []).append(folder)
        self._save_folders()
        return {"id": folder["id"], "name": folder["name"]}

    def rename_folder(self, folder_id: str, name: str) -> dict:
        """Rename a folder. Returns the updated folder dict, or empty dict on failure."""
        for folder in self._folders.get("folders", []):
            if folder["id"] == folder_id:
                folder["name"] = name.strip()
                self._save_folders()
                return {"id": folder["id"], "name": folder["name"]}
        return {}

    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder (clips are not affected on disk). Returns True on success."""
        folders = self._folders.get("folders", [])
        original_len = len(folders)
        self._folders["folders"] = [f for f in folders if f["id"] != folder_id]
        if len(self._folders["folders"]) < original_len:
            self._save_folders()
            return True
        return False

    def assign_clips(self, folder_id: str, clip_ids: list[str]) -> bool:
        """Add clips to a folder (idempotent). Returns True on success."""
        for folder in self._folders.get("folders", []):
            if folder["id"] == folder_id:
                existing = set(folder.get("clips", []))
                for cid in clip_ids:
                    # Remove from any other folder first
                    self._remove_clip_from_all_folders(cid)
                    existing.add(cid)
                folder["clips"] = list(existing)
                self._save_folders()
                return True
        return False

    def remove_clips(self, folder_id: str, clip_ids: list[str]) -> bool:
        """Remove clips from a folder. Returns True on success."""
        for folder in self._folders.get("folders", []):
            if folder["id"] == folder_id:
                remove_set = set(clip_ids)
                folder["clips"] = [c for c in folder.get("clips", []) if c not in remove_set]
                self._save_folders()
                return True
        return False

    def _remove_clip_from_all_folders(self, clip_id: str) -> None:
        """Remove a clip from every folder (used before assigning to a new one)."""
        for folder in self._folders.get("folders", []):
            if clip_id in folder.get("clips", []):
                folder["clips"] = [c for c in folder["clips"] if c != clip_id]

    def get_folder_for_clip(self, clip_id: str) -> Optional[str]:
        """Return the folder_id containing this clip, or None."""
        for folder in self._folders.get("folders", []):
            if clip_id in folder.get("clips", []):
                return folder["id"]
        return None

    # ── Renames (display name in config, also renames mux cache) ─

    def get_display_name(self, clip_id: str, default: str) -> str:
        """Return the user-set display name, or the default."""
        return self._renames.get("renames", {}).get(clip_id, default)

    def rename_clip(self, clip_id: str, new_name: str) -> bool:
        """
        Set a display name for a clip. Also renames the muxed cache file
        if one exists, so a re-download gets the updated filename.
        """
        new_name = new_name.strip()
        if not new_name:
            return False

        old_name = self._renames.get("renames", {}).get(clip_id)
        self._renames.setdefault("renames", {})[clip_id] = new_name
        self._save_renames()

        # Rename the muxed cache file if it exists
        self._rename_mux_cache(clip_id, new_name)

        return True

    def _rename_mux_cache(self, clip_id: str, new_name: str) -> None:
        """If a muxed .mp4 exists for this clip, rename it to match the display name."""
        if not self._mux_cache_dir.is_dir():
            return
        # Mux cache files are named after the clip directory name
        old_path = self._mux_cache_dir / f"{clip_id}.mp4"
        if old_path.is_file():
            # Sanitise the new name for filesystem use
            safe = self._sanitise_filename(new_name)
            if not safe.lower().endswith(".mp4"):
                safe += ".mp4"
            new_path = self._mux_cache_dir / safe
            try:
                os.rename(str(old_path), str(new_path))
            except OSError as e:
                logger.warning(f"Could not rename mux cache {old_path} -> {new_path}: {e}")

    @staticmethod
    def _sanitise_filename(name: str) -> str:
        """Remove or replace characters that are unsafe in filenames."""
        # Replace path separators and null bytes
        for ch in ('/', '\\', '\0', ':', '*', '?', '"', '<', '>', '|'):
            name = name.replace(ch, '_')
        return name.strip().strip('.')

    # ── Delete (actual filesystem deletion) ────────────────────

    def delete_clip(self, clip_dir: str, clip_id: str) -> bool:
        """
        Permanently delete a clip from disk.

        Removes:
          - The clip directory (DASH segments, MPD, etc.)
          - The muxed cache file
          - The thumbnail
          - Any config references (folder assignments, renames)
        """
        success = True

        # Remove clip directory
        clip_path = Path(clip_dir)
        if clip_path.is_dir():
            try:
                shutil.rmtree(str(clip_path))
            except OSError as e:
                logger.error(f"Failed to delete clip dir {clip_path}: {e}")
                success = False
        elif clip_path.is_file():
            try:
                clip_path.unlink()
            except OSError as e:
                logger.error(f"Failed to delete clip file {clip_path}: {e}")
                success = False

        # Remove muxed cache
        if self._mux_cache_dir.is_dir():
            mux_file = self._mux_cache_dir / f"{clip_id}.mp4"
            if mux_file.is_file():
                try:
                    mux_file.unlink()
                except OSError as e:
                    logger.warning(f"Failed to delete mux cache {mux_file}: {e}")

            # Also check for renamed mux files
            display = self._renames.get("renames", {}).get(clip_id)
            if display:
                safe = self._sanitise_filename(display)
                if not safe.lower().endswith(".mp4"):
                    safe += ".mp4"
                renamed_mux = self._mux_cache_dir / safe
                if renamed_mux.is_file():
                    try:
                        renamed_mux.unlink()
                    except OSError as e:
                        logger.warning(f"Failed to delete renamed mux {renamed_mux}: {e}")

        # Remove thumbnail
        if self._thumb_dir.is_dir():
            for ext in (".jpg", ".png"):
                thumb = self._thumb_dir / f"{clip_id}{ext}"
                if thumb.is_file():
                    try:
                        thumb.unlink()
                    except OSError as e:
                        logger.warning(f"Failed to delete thumbnail {thumb}: {e}")

        # Remove from folder assignments
        self._remove_clip_from_all_folders(clip_id)
        self._save_folders()

        # Remove rename entry
        renames = self._renames.get("renames", {})
        if clip_id in renames:
            del renames[clip_id]
            self._save_renames()

        return success

    # ── Client Secrets ─────────────────────────────────────────

    def save_client_secrets(self, data: dict) -> bool:
        """
        Validate and save OAuth client_secrets.json.

        Expects a dict with either "installed" or "web" key containing
        "client_id" and "client_secret".
        """
        # Basic validation
        app_type = None
        for key in ("installed", "web"):
            if key in data:
                app_type = key
                break

        if not app_type:
            logger.error("client_secrets: missing 'installed' or 'web' key")
            return False

        inner = data[app_type]
        if not isinstance(inner, dict):
            logger.error("client_secrets: app config is not a dict")
            return False

        if "client_id" not in inner or "client_secret" not in inner:
            logger.error("client_secrets: missing client_id or client_secret")
            return False

        self._save_json(self._secrets_file, data)
        # Restrict permissions
        try:
            self._secrets_file.chmod(0o600)
        except OSError:
            pass
        return True

    def has_client_secrets(self) -> bool:
        """Check if client_secrets.json exists and is valid."""
        if not self._secrets_file.is_file():
            return False
        try:
            data = json.loads(self._secrets_file.read_text("utf-8"))
            return "installed" in data or "web" in data
        except (json.JSONDecodeError, OSError):
            return False
