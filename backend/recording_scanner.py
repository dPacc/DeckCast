import os
import glob
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")

STEAM_USERDATA = Path.home() / ".local/share/Steam/userdata"
THUMBNAIL_DIR = Path.home() / "homebrew/data/DeckCast/thumbnails"

DEFAULT_SCAN_PATHS = [
    str(STEAM_USERDATA / "*/gamerecordings/video"),
    str(STEAM_USERDATA / "*/screenshots/videos"),
    str(Path.home() / "Videos"),
]

SD_CARD_PATHS = [
    "/run/media/mmcblk0p1/steamapps/common",
    "/run/media/mmcblk0p1/Videos",
]

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov"}


def get_game_name_from_path(filepath: str) -> str:
    parts = Path(filepath).parts
    for i, part in enumerate(parts):
        if part == "gamerecordings" and i + 1 < len(parts):
            app_id = parts[i + 1] if parts[i + 1] != "video" else None
            if app_id and app_id.isdigit():
                return _lookup_app_name(app_id) or f"App {app_id}"
    return "Unknown Game"


def _lookup_app_name(app_id: str) -> Optional[str]:
    acf_patterns = [
        Path.home() / ".local/share/Steam/steamapps" / f"appmanifest_{app_id}.acf",
        Path(f"/run/media/mmcblk0p1/steamapps/appmanifest_{app_id}.acf"),
    ]
    for acf_path in acf_patterns:
        if acf_path.exists():
            try:
                text = acf_path.read_text()
                for line in text.splitlines():
                    if '"name"' in line:
                        return line.split('"')[3]
            except Exception:
                pass
    return None


def probe_video(filepath: str) -> dict:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"ffprobe failed for {filepath}: {e}")
        return {}


def get_recording_metadata(filepath: str) -> dict:
    stat = os.stat(filepath)
    info = probe_video(filepath)

    duration = 0.0
    width = 0
    height = 0
    codec = "unknown"

    fmt = info.get("format", {})
    duration = float(fmt.get("duration", 0))

    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            codec = stream.get("codec_name", "unknown")
            if duration == 0:
                duration = float(stream.get("duration", 0))
            break

    return {
        "path": filepath,
        "filename": os.path.basename(filepath),
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "duration": duration,
        "width": width,
        "height": height,
        "codec": codec,
        "game": get_game_name_from_path(filepath),
    }


def generate_thumbnail(filepath: str, timestamp: float = 5.0) -> Optional[str]:
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    name = Path(filepath).stem
    thumb_path = THUMBNAIL_DIR / f"{name}.jpg"

    if thumb_path.exists():
        return str(thumb_path)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss", str(min(timestamp, 1.0)),
                "-i", filepath,
                "-vframes", "1",
                "-q:v", "5",
                "-vf", "scale=320:-1",
                "-y",
                thumb_path,
            ],
            capture_output=True,
            timeout=15,
        )
        if thumb_path.exists():
            return str(thumb_path)
    except Exception as e:
        logger.error(f"Thumbnail generation failed for {filepath}: {e}")

    return None


def scan_recordings(extra_paths: list[str] = None) -> list[dict]:
    all_paths = DEFAULT_SCAN_PATHS + SD_CARD_PATHS
    if extra_paths:
        all_paths.extend(extra_paths)

    recordings = []
    seen = set()

    for pattern in all_paths:
        for expanded in glob.glob(pattern):
            base = Path(expanded)
            if not base.is_dir():
                if base.suffix.lower() in VIDEO_EXTENSIONS and str(base) not in seen:
                    seen.add(str(base))
                    try:
                        recordings.append(get_recording_metadata(str(base)))
                    except Exception as e:
                        logger.error(f"Error scanning {base}: {e}")
                continue

            for root, _, files in os.walk(expanded):
                for f in files:
                    fp = os.path.join(root, f)
                    if Path(f).suffix.lower() in VIDEO_EXTENSIONS and fp not in seen:
                        seen.add(fp)
                        try:
                            recordings.append(get_recording_metadata(fp))
                        except Exception as e:
                            logger.error(f"Error scanning {fp}: {e}")

    recordings.sort(key=lambda r: r["modified"], reverse=True)
    return recordings
