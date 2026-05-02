import asyncio
import glob
import json
import logging
import os
import pwd
import signal
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")

LIVE_DIR = "/tmp/deckcast_live"
PIPE_PATH = "/tmp/deckcast_gsr_pipe"
RECORDINGS_DIR = Path("/home/deck/homebrew/data/DeckCast/recordings")
STATE_FILE = "/tmp/deckcast_cast_state.json"
GSR_LOG = "/tmp/deckcast_gsr.log"
FFMPEG_LOG = "/tmp/deckcast_ffmpeg.log"

GSR_FLATPAK_BASE = "/var/lib/flatpak/app/com.dec05eba.gpu_screen_recorder/x86_64/stable"


def _find_gsr_paths() -> tuple:
    matches = glob.glob(f"{GSR_FLATPAK_BASE}/*/files/bin/gpu-screen-recorder")
    if not matches:
        raise FileNotFoundError(
            "gpu-screen-recorder not found. "
            "Install: flatpak install com.dec05eba.gpu_screen_recorder"
        )
    base = str(Path(matches[0]).parent.parent)
    return base + "/bin/gpu-screen-recorder", base + "/lib"


def _bitrate_to_quality(bitrate: str) -> str:
    try:
        kbps = int(bitrate.rstrip("kK"))
    except (ValueError, AttributeError):
        return "very_high"
    if kbps <= 4000:
        return "high"
    if kbps <= 6000:
        return "very_high"
    return "ultra"


def _demote_to_deck():
    pw = pwd.getpwnam("deck")
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)


class CastManager:
    """
    Two-process pipeline for live screen casting on Steam Deck:
      gpu-screen-recorder (portal mode) → named pipe → FFmpeg → HLS

    Portal mode uses PipeWire via xdg-desktop-portal-gamescope for
    true 60fps capture. Survives plugin hot-reloads via PID persistence.
    """

    def __init__(self):
        self._gsr_proc: Optional[subprocess.Popen] = None
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._gsr_pid: Optional[int] = None
        self._ffmpeg_pid: Optional[int] = None
        self._state = "offline"
        self._error: Optional[str] = None
        self._start_time: Optional[float] = None
        self._is_recording = False
        self._reattach()

    def _reattach(self):
        try:
            state = json.loads(Path(STATE_FILE).read_text())

            if "pid" in state and "gsr_pid" not in state:
                old_pid = state["pid"]
                try:
                    os.kill(old_pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                self._clean_state_file()
                return

            gsr_pid = state["gsr_pid"]
            ffmpeg_pid = state["ffmpeg_pid"]
            gsr_alive = self._pid_alive(gsr_pid)
            ffmpeg_alive = self._pid_alive(ffmpeg_pid)

            if gsr_alive and ffmpeg_alive:
                self._gsr_pid = gsr_pid
                self._ffmpeg_pid = ffmpeg_pid
                self._state = state.get("state", "live")
                self._start_time = state.get("start_time")
                self._is_recording = state.get("is_recording", False)
                logger.info(f"Re-attached to cast (gsr={gsr_pid}, ffmpeg={ffmpeg_pid})")
            else:
                for pid, alive in [(gsr_pid, gsr_alive), (ffmpeg_pid, ffmpeg_alive)]:
                    if alive:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                self._clean_state_file()

        except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError):
            self._clean_state_file()

    def _save_state(self):
        Path(STATE_FILE).write_text(json.dumps({
            "gsr_pid": self._gsr_pid,
            "ffmpeg_pid": self._ffmpeg_pid,
            "state": self._state,
            "start_time": self._start_time,
            "is_recording": self._is_recording,
        }))

    def _clean_state_file(self):
        try:
            os.unlink(STATE_FILE)
        except FileNotFoundError:
            pass

    def _pid_alive(self, pid: Optional[int]) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _is_running(self) -> bool:
        gsr = (
            (self._gsr_proc is not None and self._gsr_proc.poll() is None)
            or self._pid_alive(self._gsr_pid)
        )
        ffmpeg = (
            (self._ffmpeg_proc is not None and self._ffmpeg_proc.poll() is None)
            or self._pid_alive(self._ffmpeg_pid)
        )
        return gsr and ffmpeg

    @property
    def status(self) -> dict:
        running = self._is_running()
        if self._state == "live" and not running:
            self._kill_orphans()
            self._state = "offline"
            self._start_time = None
            self._clean_state_file()

        duration = 0.0
        if self._state == "live" and self._start_time:
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

    def _kill_orphans(self):
        for proc, pid in [
            (self._gsr_proc, self._gsr_pid),
            (self._ffmpeg_proc, self._ffmpeg_pid),
        ]:
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
            elif self._pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass

    def _kill_system_orphans(self):
        for pattern in [PIPE_PATH, LIVE_DIR]:
            try:
                subprocess.run(["pkill", "-9", "-f", pattern], capture_output=True, timeout=5)
            except Exception:
                pass

    def _prepare(self):
        self._kill_system_orphans()
        if os.path.exists(LIVE_DIR):
            shutil.rmtree(LIVE_DIR, ignore_errors=True)
        os.makedirs(LIVE_DIR, mode=0o777, exist_ok=True)
        os.chmod(LIVE_DIR, 0o777)

        if os.path.exists(PIPE_PATH):
            os.unlink(PIPE_PATH)
        os.mkfifo(PIPE_PATH)
        os.chmod(PIPE_PATH, 0o666)

    async def start(
        self,
        resolution: str = "1280x800",
        bitrate: str = "6000k",
        framerate: int = 60,
        record: bool = False,
    ) -> dict:
        if self._is_running() or self._state in ("starting", "live"):
            return {"success": False, "error": "Cast already running"}

        try:
            gsr_bin, gsr_lib = _find_gsr_paths()
        except FileNotFoundError as e:
            self._state = "error"
            self._error = str(e)
            return {"success": False, "error": str(e)}

        self._prepare()

        quality = _bitrate_to_quality(bitrate)
        playlist = os.path.join(LIVE_DIR, "stream.m3u8")
        seg_pattern = os.path.join(LIVE_DIR, "seg_%05d.ts")

        gsr_env = os.environ.copy()
        gsr_env.update({
            "LD_LIBRARY_PATH": gsr_lib,
            "WAYLAND_DISPLAY": "gamescope-0",
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
            "HOME": "/home/deck",
        })

        gsr_cmd = [
            gsr_bin,
            "-w", "portal",
            "-f", str(framerate),
            "-c", "h264",
            "-q", quality,
            "-o", PIPE_PATH,
        ]

        ffmpeg_env = os.environ.copy()
        ffmpeg_env.update({
            "XDG_RUNTIME_DIR": "/run/user/1000",
            "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
            "HOME": "/home/deck",
        })

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "h264", "-framerate", str(framerate), "-i", PIPE_PATH,
            "-f", "pulse", "-ac", "2", "-i", "default",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        ]

        hls_flags = "delete_segments+append_list+omit_endlist"

        if record:
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            os.chmod(str(RECORDINGS_DIR), 0o777)
            ts = time.strftime("%Y%m%d_%H%M%S")
            rec_path = str(RECORDINGS_DIR / f"cast_{ts}.mp4")
            ffmpeg_cmd += [
                "-f", "tee", "-map", "0:v", "-map", "1:a",
                (
                    f"[f=hls:hls_time=2:hls_list_size=5"
                    f":hls_flags={hls_flags}"
                    f":hls_segment_filename={seg_pattern}]{playlist}"
                    f"|[f=mp4:movflags=+faststart]{rec_path}"
                ),
            ]
        else:
            ffmpeg_cmd += [
                "-f", "hls",
                "-hls_time", "2",
                "-hls_list_size", "5",
                "-hls_flags", hls_flags,
                "-hls_segment_filename", seg_pattern,
                playlist,
            ]

        try:
            self._state = "starting"
            self._error = None
            self._is_recording = record

            self._gsr_proc = subprocess.Popen(
                gsr_cmd,
                stdout=subprocess.DEVNULL,
                stderr=open(GSR_LOG, "w"),
                env=gsr_env,
                preexec_fn=_demote_to_deck,
                start_new_session=True,
            )
            self._gsr_pid = self._gsr_proc.pid
            logger.info(f"GSR started (pid={self._gsr_pid})")

            await asyncio.sleep(2)
            if self._gsr_proc.poll() is not None:
                err = self._tail_log(GSR_LOG)
                self._abort_start()
                return {"success": False, "error": f"Screen capture failed: {err}"}

            self._ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=open(FFMPEG_LOG, "w"),
                env=ffmpeg_env,
                preexec_fn=_demote_to_deck,
                start_new_session=True,
            )
            self._ffmpeg_pid = self._ffmpeg_proc.pid
            logger.info(f"FFmpeg started (pid={self._ffmpeg_pid})")

            await asyncio.sleep(4)

            if self._gsr_proc.poll() is not None:
                err = self._tail_log(GSR_LOG)
                self._abort_start()
                return {"success": False, "error": f"Screen capture died: {err}"}

            if self._ffmpeg_proc.poll() is not None:
                err = self._tail_log(FFMPEG_LOG)
                self._abort_start()
                return {"success": False, "error": f"HLS muxer died: {err}"}

            self._state = "live"
            self._start_time = time.time()
            self._save_state()
            logger.info(f"Cast started: {quality} quality @ {framerate}fps, record={record}")
            return {"success": True, "status": "live", "hls_url": "/live/stream.m3u8"}

        except Exception as e:
            self._state = "error"
            self._error = str(e)
            logger.error(f"Cast start failed: {e}")
            self._abort_start()
            return {"success": False, "error": str(e)}

    def _tail_log(self, path: str) -> str:
        try:
            return Path(path).read_text()[-300:]
        except Exception:
            return "unknown error"

    def _abort_start(self):
        for proc in [self._gsr_proc, self._ffmpeg_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._gsr_proc = None
        self._ffmpeg_proc = None
        self._gsr_pid = None
        self._ffmpeg_pid = None
        self._state = "error"

    async def stop(self) -> dict:
        if not self._is_running():
            self._kill_orphans()
            self._reset()
            return {"success": True, "status": "offline"}

        try:
            for proc, pid in [
                (self._ffmpeg_proc, self._ffmpeg_pid),
                (self._gsr_proc, self._gsr_pid),
            ]:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                elif pid and self._pid_alive(pid):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        continue
                    await asyncio.sleep(2)
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

            self._kill_system_orphans()
            self._reset()

            if os.path.exists(LIVE_DIR):
                shutil.rmtree(LIVE_DIR, ignore_errors=True)
            try:
                os.unlink(PIPE_PATH)
            except FileNotFoundError:
                pass

            logger.info("Cast stopped")
            return {"success": True, "status": "offline"}

        except Exception as e:
            logger.error(f"Cast stop failed: {e}")
            return {"success": False, "error": str(e)}

    def _reset(self):
        self._gsr_proc = None
        self._ffmpeg_proc = None
        self._gsr_pid = None
        self._ffmpeg_pid = None
        self._state = "offline"
        self._error = None
        self._start_time = None
        self._is_recording = False
        self._clean_state_file()
