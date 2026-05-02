import asyncio
import logging
import subprocess
from typing import Optional

logger = logging.getLogger("DeckCast")


class StreamManager:
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._status = "offline"  # offline, connecting, live, error
        self._error: Optional[str] = None

    @property
    def status(self) -> dict:
        running = self._process is not None and self._process.poll() is None
        if self._status == "live" and not running:
            self._status = "offline"
        return {
            "status": self._status,
            "error": self._error,
            "running": running,
        }

    def start(
        self,
        rtmp_url: str,
        stream_key: str,
        resolution: str = "1280x720",
        bitrate: str = "4000k",
        framerate: int = 30,
    ) -> dict:
        if self._process and self._process.poll() is None:
            return {"success": False, "error": "Stream already running"}

        full_url = f"{rtmp_url.rstrip('/')}/{stream_key}"
        width, height = resolution.split("x")

        cmd = [
            "ffmpeg",
            "-f", "x11grab",
            "-framerate", str(framerate),
            "-video_size", resolution,
            "-i", ":0.0",
            "-f", "pulse",
            "-i", "default",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:v", bitrate,
            "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.replace("k", "")) * 2) + "k",
            "-g", str(framerate * 2),
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            full_url,
        ]

        try:
            self._status = "connecting"
            self._error = None

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self._status = "live"
            logger.info(f"Stream started: {resolution} @ {bitrate}")
            return {"success": True, "status": "live"}

        except FileNotFoundError:
            self._status = "error"
            self._error = "FFmpeg not found"
            return {"success": False, "error": "FFmpeg not found on system"}
        except Exception as e:
            self._status = "error"
            self._error = str(e)
            logger.error(f"Stream start failed: {e}")
            return {"success": False, "error": str(e)}

    def stop(self) -> dict:
        if not self._process:
            return {"success": True, "status": "offline"}

        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)

            self._process = None
            self._status = "offline"
            self._error = None
            logger.info("Stream stopped")
            return {"success": True, "status": "offline"}

        except Exception as e:
            logger.error(f"Stream stop failed: {e}")
            return {"success": False, "error": str(e)}
