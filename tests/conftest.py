import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="deckcast_test_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_video(tmp_dir):
    """Create a tiny valid mp4 file using ffmpeg if available, otherwise a dummy."""
    video_path = tmp_dir / "test_recording.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=black:s=320x240:d=3",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", "3",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac",
                video_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if video_path.exists() and video_path.stat().st_size > 0:
            return video_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: create a dummy file for tests that don't need a real video
    video_path.write_bytes(b"\x00" * 1024)
    return video_path


@pytest.fixture
def sample_recordings_dir(tmp_dir, sample_video):
    """Create a directory structure mimicking Steam recordings."""
    rec_dir = tmp_dir / "userdata" / "12345" / "gamerecordings" / "video"
    rec_dir.mkdir(parents=True)
    dest = rec_dir / "gameplay.mp4"
    shutil.copy2(sample_video, dest)

    screenshots_dir = tmp_dir / "userdata" / "12345" / "screenshots" / "videos"
    screenshots_dir.mkdir(parents=True)
    dest2 = screenshots_dir / "clip.mp4"
    shutil.copy2(sample_video, dest2)

    return tmp_dir


@pytest.fixture
def config_dir(tmp_dir):
    """Create a temporary config directory."""
    cfg_dir = tmp_dir / "config"
    cfg_dir.mkdir()
    return cfg_dir


@pytest.fixture
def sample_config():
    return {
        "youtube": {
            "default_privacy": "unlisted",
            "title_template": "{game} - {date}",
            "default_category": "20",
            "default_tags": ["steamdeck", "gaming"],
        },
        "transfer": {
            "port": 8420,
            "password_enabled": False,
            "password": "",
        },
        "recording_paths": [],
        "sd_card_paths": [],
        "stream": {
            "resolution": "1280x720",
            "bitrate": "4000k",
            "framerate": 30,
            "saved_stream_keys": [],
        },
    }
