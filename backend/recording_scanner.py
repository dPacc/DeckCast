import os
import glob
import json
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")

STEAM_USERDATA = Path.home() / ".local/share/Steam/userdata"
MUX_CACHE_DIR = Path.home() / "homebrew/data/DeckCast/muxed"

CLIP_SCAN_PATTERNS = [
    str(STEAM_USERDATA / "*/gamerecordings/clips/clip_*"),
]

SD_CARD_CLIP_PATTERNS = [
    "/run/media/mmcblk0p1/steamapps/userdata/*/gamerecordings/clips/clip_*",
]

LOOSE_VIDEO_PATHS = [
    str(Path.home() / "Videos"),
]

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov"}


def _parse_app_id_from_clip_dir(clip_dir: str) -> Optional[str]:
    name = Path(clip_dir).name
    m = re.match(r"clip_(\d+)_", name)
    return m.group(1) if m else None


def _parse_date_from_clip_dir(clip_dir: str) -> Optional[str]:
    name = Path(clip_dir).name
    m = re.search(r"_(\d{8}_\d{6})$", name)
    if m:
        raw = m.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]} {raw[9:11]}:{raw[11:13]}:{raw[13:15]}"
    return None


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


def _find_mpd(clip_dir: str) -> Optional[str]:
    for mpd in Path(clip_dir).rglob("session.mpd"):
        return str(mpd)
    return None


def _parse_mpd_duration(mpd_path: str) -> float:
    try:
        text = Path(mpd_path).read_text()
        m = re.search(r'mediaPresentationDuration="PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?"', text)
        if m:
            h = float(m.group(1) or 0)
            mins = float(m.group(2) or 0)
            s = float(m.group(3) or 0)
            return h * 3600 + mins * 60 + s
    except Exception as e:
        logger.error(f"Failed to parse MPD duration: {e}")
    return 0.0


def _parse_mpd_video_info(mpd_path: str) -> dict:
    info = {"width": 0, "height": 0, "codec": "unknown"}
    try:
        text = Path(mpd_path).read_text()
        video_block = re.search(r'contentType="video".*?</AdaptationSet>', text, re.DOTALL)
        if video_block:
            block = video_block.group(0)
            w = re.search(r'width="(\d+)"', block)
            h = re.search(r'height="(\d+)"', block)
            c = re.search(r'codecs="([^"]+)"', block)
            if w:
                info["width"] = int(w.group(1))
            if h:
                info["height"] = int(h.group(1))
            if c:
                codecs = c.group(1)
                info["codec"] = codecs.split(".")[0] if "." in codecs else codecs
    except Exception as e:
        logger.error(f"Failed to parse MPD video info: {e}")
    return info


def _get_clip_size(clip_dir: str) -> int:
    total = 0
    video_dir = Path(clip_dir)
    for f in video_dir.rglob("*.m4s"):
        total += f.stat().st_size
    return total


def _get_clip_thumbnail(clip_dir: str) -> Optional[str]:
    thumb = Path(clip_dir) / "thumbnail.jpg"
    if thumb.exists():
        return str(thumb)
    return None


def get_clip_metadata(clip_dir: str) -> dict:
    mpd_path = _find_mpd(clip_dir)
    app_id = _parse_app_id_from_clip_dir(clip_dir)
    date_str = _parse_date_from_clip_dir(clip_dir)

    game = "Unknown Game"
    if app_id:
        game = _lookup_app_name(app_id) or f"App {app_id}"

    duration = 0.0
    width = 0
    height = 0
    codec = "unknown"

    if mpd_path:
        duration = _parse_mpd_duration(mpd_path)
        vinfo = _parse_mpd_video_info(mpd_path)
        width = vinfo["width"]
        height = vinfo["height"]
        codec = vinfo["codec"]

    clip_path = Path(clip_dir)
    modified = clip_path.stat().st_mtime

    clip_name = clip_path.name
    filename = f"{game} - {date_str}.mp4" if date_str else f"{clip_name}.mp4"

    return {
        "path": clip_dir,
        "filename": filename,
        "size": _get_clip_size(clip_dir),
        "modified": modified,
        "duration": duration,
        "width": width,
        "height": height,
        "codec": codec,
        "game": game,
        "thumbnail_path": _get_clip_thumbnail(clip_dir),
        "is_dash": True,
    }


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
        "game": "Unknown Game",
        "is_dash": False,
    }


def generate_thumbnail(filepath: str, timestamp: float = 5.0) -> Optional[str]:
    clip_dir = Path(filepath)
    if clip_dir.is_dir():
        thumb = _get_clip_thumbnail(filepath)
        if thumb:
            return thumb

    mpd = _find_mpd(filepath) if clip_dir.is_dir() else filepath
    if not mpd:
        return None

    thumb_dir = MUX_CACHE_DIR.parent / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    name = Path(filepath).stem if not clip_dir.is_dir() else clip_dir.name
    thumb_path = thumb_dir / f"{name}.jpg"

    if thumb_path.exists():
        return str(thumb_path)

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss", str(min(timestamp, 1.0)),
                "-i", mpd,
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
        logger.error(f"Thumbnail generation failed: {e}")

    return None


def mux_recording(clip_dir: str) -> Optional[str]:
    MUX_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    clip_name = Path(clip_dir).name
    output_path = MUX_CACHE_DIR / f"{clip_name}.mp4"

    if output_path.exists():
        return str(output_path)

    mpd_path = _find_mpd(clip_dir)
    if not mpd_path:
        logger.error(f"No session.mpd found in {clip_dir}")
        return None

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", mpd_path,
                "-c", "copy",
                "-movflags", "+faststart",
                "-y",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error(f"Mux failed: {result.stderr}")
            return None
        return str(output_path)
    except Exception as e:
        logger.error(f"Mux failed for {clip_dir}: {e}")
        return None


def scan_recordings(extra_paths: list[str] = None) -> list[dict]:
    recordings = []
    seen = set()

    all_clip_patterns = CLIP_SCAN_PATTERNS + SD_CARD_CLIP_PATTERNS
    for pattern in all_clip_patterns:
        for clip_dir in glob.glob(pattern):
            if clip_dir in seen or not Path(clip_dir).is_dir():
                continue
            seen.add(clip_dir)
            try:
                recordings.append(get_clip_metadata(clip_dir))
            except Exception as e:
                logger.error(f"Error scanning clip {clip_dir}: {e}")

    all_loose_paths = list(LOOSE_VIDEO_PATHS)
    if extra_paths:
        all_loose_paths.extend(extra_paths)

    for scan_path in all_loose_paths:
        for expanded in glob.glob(scan_path):
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
