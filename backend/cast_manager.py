import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")

LIVE_DIR = "/tmp/deckcast_live"
RECORDINGS_DIR = Path("/home/deck/homebrew/data/DeckCast/recordings")


class CastManager:
    """
    Captures the Steam Deck screen via DRM/KMS (kmsgrab) with VAAPI
    hardware encoding and outputs HLS for browser playback.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._state = "offline"  # offline | starting | live | error
        self._error: Optional[str] = None
        self._start_time: Optional[float] = None
        self._is_recording = False

    @property
    def status(self) -> dict:
        running = self._process is not None and self._process.poll() is None
        if self._state == "live" and not running:
            self._state = "offline"
            self._start_time = None

        duration = 0.0
        if self._state == "live" and self._start_time is not None:
            duration = time.time() - self._start_time

        return {
            "status": self._state,
            "live": self._state == "live" and running,
            "error": self._error,
            "running": running,
            "duration_seconds": round(duration, 1),
            "is_recording": self._is_recording and running,
            "hls_url": "/live/stream.m3u8" if self._state == "live" else None,
            "started_at": self._start_time,
        }

    def _clean_live_dir(self) -> None:
        if os.path.exists(LIVE_DIR):
            shutil.rmtree(LIVE_DIR, ignore_errors=True)
        os.makedirs(LIVE_DIR, exist_ok=True)

    def start(
        self,
        resolution: str = "1280x800",
        bitrate: str = "4000k",
        framerate: int = 30,
        record: bool = False,
    ) -> dict:
        if self._process and self._process.poll() is None:
            return {"success": False, "error": "Cast already running"}

        self._clean_live_dir()

        playlist_path = os.path.join(LIVE_DIR, "stream.m3u8")
        segment_pattern = os.path.join(LIVE_DIR, "seg_%05d.ts")

        width, height = resolution.split("x")
        vf = f"hwmap=derive_device=vaapi,scale_vaapi=w={width}:h={height}:format=nv12"

        cmd = [
            "ffmpeg",
            "-fflags", "+nobuffer+flush_packets",
            "-flags", "+low_delay",
            "-f", "kmsgrab",
            "-device", "/dev/dri/card0",
            "-framerate", str(framerate),
            "-i", "-",
            "-f", "pulse",
            "-ac", "2",
            "-i", "default",
            "-vf", vf,
            "-c:v", "h264_vaapi",
            "-b:v", bitrate,
            "-maxrate", bitrate,
            "-g", str(framerate),
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
        ]

        hls_flags = "delete_segments+append_list+omit_endlist+split_by_time"

        if record:
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            recording_path = str(RECORDINGS_DIR / f"cast_{timestamp}.mp4")

            cmd += [
                "-f", "tee",
                "-map", "0:v", "-map", "1:a",
                (
                    f"[f=hls:hls_time=1:hls_list_size=5"
                    f":hls_flags={hls_flags}"
                    f":hls_segment_filename={segment_pattern}]{playlist_path}"
                    f"|[f=mp4:movflags=+faststart]{recording_path}"
                ),
            ]
        else:
            cmd += [
                "-f", "hls",
                "-hls_time", "1",
                "-hls_list_size", "5",
                "-hls_flags", hls_flags,
                "-hls_segment_filename", segment_pattern,
                playlist_path,
            ]

        # kmsgrab needs root for DRM; PulseAudio accessed via socket
        env = os.environ.copy()
        env["XDG_RUNTIME_DIR"] = "/run/user/1000"
        env["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
        env["HOME"] = "/home/deck"

        try:
            self._state = "starting"
            self._error = None
            self._is_recording = record

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            # Wait for first HLS segment to confirm capture works
            time.sleep(3)
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode(errors="replace")
                logger.error(f"FFmpeg exited immediately: {stderr[-500:]}")
                self._state = "error"
                self._error = "FFmpeg failed to start"
                self._process = None
                return {"success": False, "error": f"FFmpeg failed: {stderr[-200:]}"}

            self._state = "live"
            self._start_time = time.time()
            logger.info(f"Cast started: {resolution} @ {bitrate}, recording={record}")
            return {"success": True, "status": "live", "hls_url": "/live/stream.m3u8"}

        except FileNotFoundError:
            self._state = "error"
            self._error = "FFmpeg not found"
            return {"success": False, "error": "FFmpeg not found on system"}
        except Exception as e:
            self._state = "error"
            self._error = str(e)
            logger.error(f"Cast start failed: {e}")
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
            self._state = "offline"
            self._error = None
            self._start_time = None
            self._is_recording = False

            self._clean_live_dir()

            logger.info("Cast stopped")
            return {"success": True, "status": "offline"}

        except Exception as e:
            logger.error(f"Cast stop failed: {e}")
            return {"success": False, "error": str(e)}
