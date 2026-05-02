import asyncio
import json
import mimetypes
import os
from http import HTTPStatus
from pathlib import Path
from typing import Optional

# Chunk size for streaming file responses
_CHUNK_SIZE = 64 * 1024  # 64 KB

# Additional MIME types not always in the default database
_EXTRA_MIME_TYPES = {
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".m4s": "video/iso.segment",
    ".mpd": "application/dash+xml",
    ".map": "application/json",
}


def _reason(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Unknown"


def _header_block(status: int, headers: dict[str, str]) -> bytes:
    parts = [f"HTTP/1.1 {status} {_reason(status)}"]
    for key, val in headers.items():
        parts.append(f"{key}: {val}")
    parts.append("")
    parts.append("")
    return "\r\n".join(parts).encode("utf-8")


async def send_json(writer: asyncio.StreamWriter, data, status: int = 200) -> None:
    """Send a JSON response."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        "Connection": "close",
    }
    writer.write(_header_block(status, headers) + body)
    await writer.drain()


async def send_html(writer: asyncio.StreamWriter, html_bytes: bytes, status: int = 200) -> None:
    """Send an HTML response. Accepts pre-encoded bytes."""
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(html_bytes)),
        "Connection": "close",
    }
    writer.write(_header_block(status, headers) + html_bytes)
    await writer.drain()


async def send_error(writer: asyncio.StreamWriter, status: int, message: str) -> None:
    """Send a plain-text error response."""
    body = message.encode("utf-8")
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Length": str(len(body)),
        "Connection": "close",
    }
    writer.write(_header_block(status, headers) + body)
    await writer.drain()


def _guess_content_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext in _EXTRA_MIME_TYPES:
        return _EXTRA_MIME_TYPES[ext]
    ct = mimetypes.guess_type(filepath)[0]
    return ct or "application/octet-stream"


async def send_file(
    writer: asyncio.StreamWriter,
    filepath: str,
    filename: str,
    request_headers: dict[str, str],
    content_type: Optional[str] = None,
) -> None:
    """
    Stream a file to the client with range-request support.

    Args:
        writer: The asyncio stream writer.
        filepath: Absolute path to the file on disk.
        filename: Name to present in Content-Disposition.
        request_headers: Parsed HTTP request headers (lowercase keys).
        content_type: Override MIME type; auto-detected if None.
    """
    if not os.path.isfile(filepath):
        await send_error(writer, 404, "File not found")
        return

    file_size = os.path.getsize(filepath)
    ct = content_type or _guess_content_type(filepath)

    # Sanitise filename for Content-Disposition
    safe_name = filename.replace('"', '\\"')

    range_header = request_headers.get("range", "")
    start = 0
    end = file_size - 1

    if range_header.startswith("bytes=") and file_size > 0:
        range_spec = range_header[6:]
        parts = range_spec.split("-", 1)
        if parts[0]:
            start = int(parts[0])
        if len(parts) > 1 and parts[1]:
            end = int(parts[1])
        # Clamp
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))

        resp_headers = {
            "Content-Type": ct,
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Connection": "close",
        }
        writer.write(_header_block(206, resp_headers))
    else:
        resp_headers = {
            "Content-Type": ct,
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Connection": "close",
        }
        writer.write(_header_block(200, resp_headers))

    await writer.drain()

    # Stream the file in chunks
    with open(filepath, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
            remaining -= len(chunk)


async def send_file_inline(
    writer: asyncio.StreamWriter,
    filepath: str,
    request_headers: dict[str, str],
    content_type: Optional[str] = None,
) -> None:
    """Stream a file for inline playback (no Content-Disposition: attachment)."""
    if not os.path.isfile(filepath):
        await send_error(writer, 404, "File not found")
        return

    file_size = os.path.getsize(filepath)
    ct = content_type or _guess_content_type(filepath)

    range_header = request_headers.get("range", "")
    start = 0
    end = file_size - 1

    if range_header.startswith("bytes=") and file_size > 0:
        range_spec = range_header[6:]
        parts = range_spec.split("-", 1)
        if parts[0]:
            start = int(parts[0])
        if len(parts) > 1 and parts[1]:
            end = int(parts[1])
        start = max(0, min(start, file_size - 1))
        end = max(start, min(end, file_size - 1))

        resp_headers = {
            "Content-Type": ct,
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Connection": "close",
        }
        writer.write(_header_block(206, resp_headers))
    else:
        resp_headers = {
            "Content-Type": ct,
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Connection": "close",
        }
        writer.write(_header_block(200, resp_headers))

    await writer.drain()

    with open(filepath, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
            remaining -= len(chunk)


async def send_static(
    writer: asyncio.StreamWriter,
    rel_path: str,
    web_dir: str,
    request_headers: Optional[dict[str, str]] = None,
) -> None:
    """
    Serve a static file from web_dir with proper MIME types.

    Args:
        writer: The asyncio stream writer.
        rel_path: The path relative to web_dir (e.g. "css/style.css").
        web_dir: Absolute path to the static files directory.
        request_headers: Optional request headers for cache/range support.
    """
    # Resolve and prevent path traversal
    base = Path(web_dir).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        await send_error(writer, 403, "Forbidden")
        return

    if not target.is_file():
        await send_error(writer, 404, "Not Found")
        return

    ct = _guess_content_type(str(target))
    file_size = target.stat().st_size
    body = target.read_bytes()

    headers = {
        "Content-Type": ct,
        "Content-Length": str(file_size),
        "Cache-Control": "no-cache",
        "Connection": "close",
    }
    writer.write(_header_block(200, headers) + body)
    await writer.drain()
