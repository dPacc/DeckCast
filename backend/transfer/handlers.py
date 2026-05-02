import asyncio
import logging
import os
import urllib.parse
from pathlib import Path
from typing import Any

from backend.transfer.middleware import parse_json_body, parse_query_params
from backend.transfer.responses import send_error, send_file, send_file_inline, send_html, send_json, send_static

logger = logging.getLogger("DeckCast")


# ── Type aliases for handler arguments ──────────────────────────

# request_context = {
#     "method": str,
#     "path": str,
#     "headers": dict[str, str],
#     "body": bytes,
#     "params": dict[str, str],    # query parameters
#     "groups": list[str],         # regex capture groups from route
# }
#
# server_context = {
#     "recordings": list[dict],
#     "file_manager": FileManager,
#     "web_dir": str,              # path to backend/web/
#     "password": str | None,
# }


# ── Index & Static ──────────────────────────────────────────────

async def serve_index(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Serve the main index.html page from the web directory."""
    web_dir = server_ctx["web_dir"]
    index_path = Path(web_dir) / "index.html"

    if index_path.is_file():
        html_bytes = index_path.read_bytes()
        await send_html(writer, html_bytes)
    else:
        await send_error(writer, 404, "index.html not found")


async def serve_static(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Serve static files from the web directory, preventing path traversal."""
    groups = request_ctx["groups"]
    rel_path = groups[0] if groups else ""

    if not rel_path:
        await send_error(writer, 400, "Bad Request")
        return

    web_dir = server_ctx["web_dir"]
    await send_static(writer, rel_path, web_dir, request_ctx.get("headers"))


# ── Clips API ───────────────────────────────────────────────────

async def list_clips(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """
    Return recordings augmented with display names, folder assignments,
    and thumbnail URLs. Supports ?folder=<id> and ?search=<query> filters.
    """
    recordings = server_ctx["recordings"]
    fm = server_ctx["file_manager"]
    params = request_ctx.get("params", {})

    folder_filter = params.get("folder")
    search_filter = params.get("search", "").strip().lower()

    result = []
    for rec in recordings:
        clip_id = _clip_id_from_recording(rec)
        display_name = fm.get_display_name(clip_id, rec.get("filename", ""))
        folder_id = fm.get_folder_for_clip(clip_id)

        # Apply folder filter
        if folder_filter is not None:
            if folder_filter == "":
                # Empty folder filter = unassigned clips only
                if folder_id is not None:
                    continue
            elif folder_id != folder_filter:
                continue

        # Apply search filter
        if search_filter:
            searchable = (display_name + " " + rec.get("game", "")).lower()
            if search_filter not in searchable:
                continue

        clip_data = {
            "id": clip_id,
            "filename": display_name,
            "original_filename": rec.get("filename", ""),
            "game": rec.get("game", "Unknown Game"),
            "size": rec.get("size", 0),
            "duration": rec.get("duration", 0.0),
            "width": rec.get("width", 0),
            "height": rec.get("height", 0),
            "codec": rec.get("codec", "unknown"),
            "modified": rec.get("modified", 0),
            "is_dash": rec.get("is_dash", False),
            "folder_id": folder_id,
            "thumbnail_url": f"/api/clips/{urllib.parse.quote(clip_id, safe='')}/thumbnail",
        }
        result.append(clip_data)

    await send_json(writer, result)


async def serve_thumbnail(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Serve thumbnail.jpg from the clip directory, or generate a fallback."""
    groups = request_ctx["groups"]
    clip_id = urllib.parse.unquote(groups[0]) if groups else ""

    recording = _find_recording(server_ctx["recordings"], clip_id)
    if not recording:
        await send_error(writer, 404, "Clip not found")
        return

    clip_dir = recording.get("path", "")

    # Check for existing thumbnail
    thumb_path = recording.get("thumbnail_path")
    if thumb_path and os.path.isfile(thumb_path):
        await _serve_image(writer, thumb_path, request_ctx["headers"])
        return

    # Try thumbnail.jpg in clip directory
    if os.path.isdir(clip_dir):
        direct_thumb = os.path.join(clip_dir, "thumbnail.jpg")
        if os.path.isfile(direct_thumb):
            await _serve_image(writer, direct_thumb, request_ctx["headers"])
            return

    # Try generated thumbnail in data dir
    data_dir = server_ctx["file_manager"]._data_dir
    thumb_dir = data_dir / "thumbnails"
    for ext in (".jpg", ".png"):
        generated = thumb_dir / f"{clip_id}{ext}"
        if generated.is_file():
            await _serve_image(writer, str(generated), request_ctx["headers"])
            return

    # Try to generate a thumbnail on the fly
    try:
        from backend.recording_scanner import generate_thumbnail
        result = generate_thumbnail(clip_dir)
        if result and os.path.isfile(result):
            await _serve_image(writer, result, request_ctx["headers"])
            return
    except Exception as e:
        logger.debug(f"Thumbnail generation failed for {clip_id}: {e}")

    # Return a 1x1 transparent PNG as fallback
    await _send_fallback_thumbnail(writer)


async def _serve_image(
    writer: asyncio.StreamWriter,
    filepath: str,
    headers: dict[str, str],
) -> None:
    """Serve an image file with proper content type."""
    ext = Path(filepath).suffix.lower()
    ct = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    data = Path(filepath).read_bytes()

    from backend.transfer.responses import _header_block
    resp_headers = {
        "Content-Type": ct,
        "Content-Length": str(len(data)),
        "Cache-Control": "public, max-age=300",
        "Connection": "close",
    }
    writer.write(_header_block(200, resp_headers) + data)
    await writer.drain()


async def _send_fallback_thumbnail(writer: asyncio.StreamWriter) -> None:
    """Send a minimal 1x1 transparent PNG as a fallback thumbnail."""
    # 1x1 transparent PNG (67 bytes)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    from backend.transfer.responses import _header_block
    resp_headers = {
        "Content-Type": "image/png",
        "Content-Length": str(len(png_data)),
        "Cache-Control": "public, max-age=60",
        "Connection": "close",
    }
    writer.write(_header_block(200, resp_headers) + png_data)
    await writer.drain()


async def rename_clip(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Rename a clip (sets display name in config)."""
    groups = request_ctx["groups"]
    clip_id = urllib.parse.unquote(groups[0]) if groups else ""

    recording = _find_recording(server_ctx["recordings"], clip_id)
    if not recording:
        await send_json(writer, {"success": False, "error": "Clip not found"}, status=404)
        return

    body = parse_json_body(request_ctx["body"])
    new_name = body.get("name", "").strip()
    if not new_name:
        await send_json(writer, {"success": False, "error": "Name is required"}, status=400)
        return

    fm = server_ctx["file_manager"]
    ok = fm.rename_clip(clip_id, new_name)
    if ok:
        await send_json(writer, {"success": True, "name": new_name})
    else:
        await send_json(writer, {"success": False, "error": "Rename failed"}, status=500)


async def delete_clip(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Delete a clip from disk. Requires {"confirm": true} in the request body."""
    groups = request_ctx["groups"]
    clip_id = urllib.parse.unquote(groups[0]) if groups else ""

    recording = _find_recording(server_ctx["recordings"], clip_id)
    if not recording:
        await send_json(writer, {"success": False, "error": "Clip not found"}, status=404)
        return

    body = parse_json_body(request_ctx["body"])
    if not body.get("confirm", False):
        await send_json(
            writer,
            {"success": False, "error": "Confirmation required: {\"confirm\": true}"},
            status=400,
        )
        return

    fm = server_ctx["file_manager"]
    clip_dir = recording.get("path", "")
    ok = fm.delete_clip(clip_dir, clip_id)

    if ok:
        # Remove from the in-memory recordings list
        recordings = server_ctx["recordings"]
        server_ctx["recordings"] = [r for r in recordings if _clip_id_from_recording(r) != clip_id]
        await send_json(writer, {"success": True})
    else:
        await send_json(writer, {"success": False, "error": "Delete failed"}, status=500)


# ── Download ────────────────────────────────────────────────────

async def download_file(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """
    Find the recording, mux if DASH, and stream the file with range support.
    The URL path is /download/<clip_id_or_filename>.
    """
    groups = request_ctx["groups"]
    raw_name = groups[0] if groups else ""

    if not raw_name:
        await send_error(writer, 400, "Bad Request")
        return

    recordings = server_ctx["recordings"]
    fm = server_ctx["file_manager"]
    recording = None

    # Try matching by clip_id first, then by filename / display name
    for rec in recordings:
        cid = _clip_id_from_recording(rec)
        display = fm.get_display_name(cid, rec.get("filename", ""))
        if cid == raw_name or rec.get("filename") == raw_name or display == raw_name:
            recording = rec
            break

    if not recording:
        await send_error(writer, 404, "Recording not found")
        return

    filepath = recording.get("path", "")
    if not filepath or not os.path.exists(filepath):
        await send_error(writer, 404, "File not found on disk")
        return

    # Determine the download filename
    clip_id = _clip_id_from_recording(recording)
    download_name = fm.get_display_name(clip_id, recording.get("filename", "recording.mp4"))
    if not download_name.lower().endswith(".mp4"):
        download_name += ".mp4"

    # Mux DASH recordings to MP4 (run in thread to avoid blocking event loop)
    if recording.get("is_dash"):
        from backend.recording_scanner import mux_recording
        muxed = await asyncio.to_thread(mux_recording, filepath)
        if not muxed:
            await send_error(writer, 500, "Failed to prepare recording for download")
            return
        filepath = muxed

    await send_file(writer, filepath, download_name, request_ctx["headers"])


async def stream_file(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """
    Stream a recording for inline playback (no Content-Disposition: attachment).
    Used by the video preview lightbox.
    """
    groups = request_ctx["groups"]
    raw_name = groups[0] if groups else ""

    if not raw_name:
        await send_error(writer, 400, "Bad Request")
        return

    recordings = server_ctx["recordings"]
    fm = server_ctx["file_manager"]
    recording = None

    for rec in recordings:
        cid = _clip_id_from_recording(rec)
        display = fm.get_display_name(cid, rec.get("filename", ""))
        if cid == raw_name or rec.get("filename") == raw_name or display == raw_name:
            recording = rec
            break

    if not recording:
        await send_error(writer, 404, "Recording not found")
        return

    filepath = recording.get("path", "")
    if not filepath or not os.path.exists(filepath):
        await send_error(writer, 404, "File not found on disk")
        return

    if recording.get("is_dash"):
        from backend.recording_scanner import mux_recording
        muxed = await asyncio.to_thread(mux_recording, filepath)
        if not muxed:
            await send_error(writer, 500, "Failed to prepare recording")
            return
        filepath = muxed

    await send_file_inline(writer, filepath, request_ctx["headers"])


async def download_enhanced_file(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """
    Upscale the recording to 1080p with Lanczos + sharpening, then stream.
    Falls back to regular download if ffmpeg fails.
    """
    groups = request_ctx["groups"]
    raw_name = groups[0] if groups else ""

    if not raw_name:
        await send_error(writer, 400, "Bad Request")
        return

    recordings = server_ctx["recordings"]
    fm = server_ctx["file_manager"]
    recording = None

    for rec in recordings:
        cid = _clip_id_from_recording(rec)
        display = fm.get_display_name(cid, rec.get("filename", ""))
        if cid == raw_name or rec.get("filename") == raw_name or display == raw_name:
            recording = rec
            break

    if not recording:
        await send_error(writer, 404, "Recording not found")
        return

    filepath = recording.get("path", "")
    if not filepath or not os.path.exists(filepath):
        await send_error(writer, 404, "File not found on disk")
        return

    clip_id = _clip_id_from_recording(recording)
    download_name = fm.get_display_name(clip_id, recording.get("filename", "recording.mp4"))
    if not download_name.lower().endswith(".mp4"):
        download_name += ".mp4"
    base, ext = os.path.splitext(download_name)
    download_name = f"{base}_enhanced{ext}"

    if recording.get("is_dash"):
        from backend.recording_scanner import mux_recording
        muxed = await asyncio.to_thread(mux_recording, filepath)
        if not muxed:
            await send_error(writer, 500, "Failed to prepare recording")
            return
        filepath = muxed

    params = request_ctx.get("params", {})
    resolution = params.get("res", "1920x1080")
    if resolution not in ("1920x1080", "2560x1440", "3840x2160"):
        resolution = "1920x1080"

    from backend.recording_scanner import enhance_recording
    enhanced = await asyncio.to_thread(enhance_recording, filepath, resolution)
    if not enhanced:
        await send_file(writer, filepath, download_name, request_ctx["headers"])
        return

    await send_file(writer, enhanced, download_name, request_ctx["headers"])


# ── Folders API ─────────────────────────────────────────────────

async def list_folders(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Return all virtual folders."""
    fm = server_ctx["file_manager"]
    folders = fm.get_folders()
    await send_json(writer, folders)


async def create_folder(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Create a new virtual folder."""
    body = parse_json_body(request_ctx["body"])
    name = body.get("name", "").strip()

    if not name:
        await send_json(writer, {"success": False, "error": "Folder name is required"}, status=400)
        return

    fm = server_ctx["file_manager"]
    folder = fm.create_folder(name)
    await send_json(writer, {"success": True, "folder": folder}, status=201)


async def rename_folder(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Rename an existing folder."""
    groups = request_ctx["groups"]
    folder_id = groups[0] if groups else ""

    body = parse_json_body(request_ctx["body"])
    name = body.get("name", "").strip()

    if not name:
        await send_json(writer, {"success": False, "error": "Folder name is required"}, status=400)
        return

    fm = server_ctx["file_manager"]
    result = fm.rename_folder(folder_id, name)

    if result:
        await send_json(writer, {"success": True, "folder": result})
    else:
        await send_json(writer, {"success": False, "error": "Folder not found"}, status=404)


async def delete_folder(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Delete a virtual folder (clips remain on disk)."""
    groups = request_ctx["groups"]
    folder_id = groups[0] if groups else ""

    fm = server_ctx["file_manager"]
    ok = fm.delete_folder(folder_id)

    if ok:
        await send_json(writer, {"success": True})
    else:
        await send_json(writer, {"success": False, "error": "Folder not found"}, status=404)


async def assign_clips(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Assign clips to a folder."""
    groups = request_ctx["groups"]
    folder_id = groups[0] if groups else ""

    body = parse_json_body(request_ctx["body"])
    clip_ids = body.get("clip_ids", [])

    if not isinstance(clip_ids, list) or not clip_ids:
        await send_json(writer, {"success": False, "error": "clip_ids list is required"}, status=400)
        return

    fm = server_ctx["file_manager"]
    ok = fm.assign_clips(folder_id, clip_ids)

    if ok:
        await send_json(writer, {"success": True})
    else:
        await send_json(writer, {"success": False, "error": "Folder not found"}, status=404)


async def remove_clips(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Remove clips from a folder."""
    groups = request_ctx["groups"]
    folder_id = groups[0] if groups else ""

    body = parse_json_body(request_ctx["body"])
    clip_ids = body.get("clip_ids", [])

    if not isinstance(clip_ids, list) or not clip_ids:
        await send_json(writer, {"success": False, "error": "clip_ids list is required"}, status=400)
        return

    fm = server_ctx["file_manager"]
    ok = fm.remove_clips(folder_id, clip_ids)

    if ok:
        await send_json(writer, {"success": True})
    else:
        await send_json(writer, {"success": False, "error": "Folder not found"}, status=404)


# ── YouTube Client Secrets ──────────────────────────────────────

async def upload_client_secrets(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Validate and save a client_secrets.json for YouTube OAuth."""
    body = parse_json_body(request_ctx["body"])

    if not body:
        await send_json(
            writer,
            {"success": False, "error": "Request body must be valid JSON with 'installed' or 'web' key"},
            status=400,
        )
        return

    fm = server_ctx["file_manager"]
    ok = fm.save_client_secrets(body)

    if ok:
        await send_json(writer, {"success": True})
    else:
        await send_json(
            writer,
            {"success": False, "error": "Invalid client_secrets format. Must contain 'installed' or 'web' with client_id and client_secret."},
            status=400,
        )


async def client_secrets_status(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Check if client_secrets.json exists and is valid."""
    fm = server_ctx["file_manager"]
    has_secrets = fm.has_client_secrets()
    await send_json(writer, {"has_client_secrets": has_secrets})


# ── Cast (Live) ────────────────────────────────────────────

async def serve_cast_page(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Serve the cast viewer page."""
    web_dir = server_ctx["web_dir"]
    cast_path = Path(web_dir) / "cast.html"

    if cast_path.is_file():
        html_bytes = cast_path.read_bytes()
        await send_html(writer, html_bytes)
    else:
        await send_error(writer, 404, "cast.html not found")


async def cast_status(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Return current cast state as JSON."""
    cm = server_ctx["cast_manager"]
    await send_json(writer, cm.status)


async def cast_start(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Start casting. Accepts JSON body with resolution, bitrate, framerate, record."""
    body = parse_json_body(request_ctx["body"])
    resolution = body.get("resolution", "1280x800")
    bitrate = body.get("bitrate", "4000k")
    framerate = body.get("framerate", 30)
    record = body.get("record", False)

    cm = server_ctx["cast_manager"]
    result = await asyncio.to_thread(cm.start, resolution, bitrate, framerate, record)
    status_code = 200 if result.get("success") else 400
    await send_json(writer, result, status=status_code)


async def cast_stop(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Stop the active cast."""
    cm = server_ctx["cast_manager"]
    result = await asyncio.to_thread(cm.stop)
    await send_json(writer, result)


async def serve_live_segment(
    writer: asyncio.StreamWriter,
    request_ctx: dict[str, Any],
    server_ctx: dict[str, Any],
) -> None:
    """Serve HLS playlist and segment files from the live directory."""
    from backend.transfer.responses import _header_block

    groups = request_ctx["groups"]
    filename = groups[0] if groups else ""

    if not filename:
        await send_error(writer, 400, "Bad Request")
        return

    # Prevent path traversal
    live_dir = Path("/tmp/deckcast_live")
    target = (live_dir / filename).resolve()
    if not str(target).startswith(str(live_dir.resolve())):
        await send_error(writer, 403, "Forbidden")
        return

    if not target.is_file():
        await send_error(writer, 404, "Not Found")
        return

    data = target.read_bytes()
    ext = target.suffix.lower()

    if ext == ".m3u8":
        content_type = "application/vnd.apple.mpegurl"
        cache_control = "no-cache"
    elif ext == ".ts":
        content_type = "video/mp2t"
        cache_control = "public, max-age=10"
    else:
        content_type = "application/octet-stream"
        cache_control = "no-cache"

    resp_headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(data)),
        "Cache-Control": cache_control,
        "Access-Control-Allow-Origin": "*",
        "Connection": "close",
    }
    writer.write(_header_block(200, resp_headers) + data)
    await writer.drain()


# ── Helpers ─────────────────────────────────────────────────────

def _clip_id_from_recording(rec: dict) -> str:
    """
    Derive a stable clip ID from a recording dict.

    For DASH clips the ID is the directory name (e.g. clip_12345_20240101_120000).
    For loose video files the ID is the filename without extension.
    """
    path = rec.get("path", "")
    p = Path(path)
    if rec.get("is_dash"):
        return p.name  # directory name
    return p.stem  # filename without extension


def _find_recording(recordings: list[dict], clip_id: str) -> dict | None:
    """Find a recording by clip ID."""
    for rec in recordings:
        if _clip_id_from_recording(rec) == clip_id:
            return rec
    return None
