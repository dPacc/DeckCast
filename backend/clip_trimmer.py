import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("DeckCast")

TRIM_OUTPUT_DIR = Path.home() / "Videos/DeckCast_Trimmed"


def trim_clip(
    filepath: str,
    start_time: float,
    end_time: float,
    output_path: str = None,
) -> dict:
    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}

    if start_time < 0:
        start_time = 0
    if end_time <= start_time:
        return {"success": False, "error": "End time must be after start time"}

    if not output_path:
        TRIM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        stem = Path(filepath).stem
        ext = Path(filepath).suffix
        output_path = str(TRIM_OUTPUT_DIR / f"{stem}_trimmed{ext}")

        counter = 1
        while os.path.exists(output_path):
            output_path = str(TRIM_OUTPUT_DIR / f"{stem}_trimmed_{counter}{ext}")
            counter += 1

    try:
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", filepath,
            "-to", str(end_time - start_time),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-y",
            output_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg trim error: {result.stderr}")
            return {"success": False, "error": f"FFmpeg error: {result.stderr[-200:]}"}

        if not os.path.exists(output_path):
            return {"success": False, "error": "Output file was not created"}

        output_size = os.path.getsize(output_path)
        return {
            "success": True,
            "output_path": output_path,
            "size": output_size,
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Trim operation timed out"}
    except Exception as e:
        logger.error(f"Trim failed: {e}")
        return {"success": False, "error": str(e)}
