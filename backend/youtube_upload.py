import logging
import os
import threading
from typing import Optional

logger = logging.getLogger("DeckCast")

_upload_progress = {"active": False, "percent": 0, "video_id": None, "error": None}
_upload_lock = threading.Lock()


def get_progress() -> dict:
    with _upload_lock:
        return dict(_upload_progress)


def _set_progress(percent: int = 0, active: bool = False,
                  video_id: str = None, error: str = None):
    with _upload_lock:
        _upload_progress["percent"] = percent
        _upload_progress["active"] = active
        _upload_progress["video_id"] = video_id
        _upload_progress["error"] = error


YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
}


def upload_video(
    filepath: str,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "unlisted",
    category: str = "20",
) -> dict:
    from backend.youtube_auth import get_authenticated_credentials

    creds = get_authenticated_credentials()
    if not creds:
        return {"success": False, "error": "Not authenticated with YouTube"}

    if not os.path.exists(filepath):
        return {"success": False, "error": f"File not found: {filepath}"}

    file_size = os.path.getsize(filepath)

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": (tags or [])[:500],
                "categoryId": category,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            filepath,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10MB chunks
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        _set_progress(percent=0, active=True)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                _set_progress(percent=percent, active=True)
                logger.info(f"Upload progress: {percent}%")

        video_id = response["id"]
        video_url = f"https://youtu.be/{video_id}"

        _set_progress(percent=100, active=False, video_id=video_id)

        logger.info(f"Upload complete: {video_url}")
        return {"success": True, "video_id": video_id, "url": video_url}

    except Exception as e:
        error_msg = str(e)
        if "uploadLimitExceeded" in error_msg:
            error_msg = "Daily upload limit exceeded. Try again tomorrow."
        elif "forbidden" in error_msg.lower():
            error_msg = "Upload forbidden. Your YouTube account may need verification for videos over 15 minutes."

        _set_progress(percent=0, active=False, error=error_msg)
        logger.error(f"Upload failed: {e}")
        return {"success": False, "error": error_msg}


def upload_video_async(
    filepath: str,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "unlisted",
    category: str = "20",
):
    thread = threading.Thread(
        target=upload_video,
        args=(filepath, title, description, tags, privacy, category),
        daemon=True,
    )
    thread.start()
