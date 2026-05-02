import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import socket
from pathlib import Path
from typing import Optional
from http import HTTPStatus

logger = logging.getLogger("DeckCast")

DOWNLOAD_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DeckCast - Steam Deck Recordings</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #1a1a2e; color: #eee; padding: 16px; }
  h1 { text-align: center; margin: 16px 0; font-size: 1.5rem; color: #7c3aed; }
  .subtitle { text-align: center; color: #888; margin-bottom: 24px; font-size: 0.9rem; }
  .clip { background: #16213e; border-radius: 12px; padding: 16px; margin-bottom: 12px;
          display: flex; justify-content: space-between; align-items: center; }
  .clip-info h3 { font-size: 1rem; margin-bottom: 4px; }
  .clip-info p { color: #888; font-size: 0.85rem; }
  .dl-btn { background: #7c3aed; color: white; border: none; border-radius: 8px;
            padding: 10px 20px; font-size: 0.95rem; cursor: pointer; text-decoration: none; }
  .dl-btn:hover { background: #6d28d9; }
</style>
</head>
<body>
<h1>DeckCast</h1>
<p class="subtitle">Steam Deck Recordings</p>
<div id="clips">Loading...</div>
<script>
fetch('/api/clips').then(r=>r.json()).then(clips=>{
  const el=document.getElementById('clips');
  if(!clips.length){el.innerHTML='<p style="text-align:center;color:#888">No recordings found.</p>';return;}
  el.innerHTML=clips.map(c=>`
    <div class="clip">
      <div class="clip-info">
        <h3>${c.filename}</h3>
        <p>${c.game} &middot; ${formatSize(c.size)} &middot; ${formatDuration(c.duration)}</p>
      </div>
      <a class="dl-btn" href="/download/${encodeURIComponent(c.filename)}">Download</a>
    </div>`).join('');
});
function formatSize(b){if(b<1e6)return (b/1024).toFixed(1)+'KB';if(b<1e9)return (b/1e6).toFixed(1)+'MB';return (b/1e9).toFixed(2)+'GB';}
function formatDuration(s){const m=Math.floor(s/60);const sec=Math.floor(s%60);return m+':'+(sec<10?'0':'')+sec;}
</script>
</body>
</html>"""


class TransferServer:
    def __init__(self):
        self._server: Optional[asyncio.AbstractServer] = None
        self._recordings: list[dict] = []
        self._password: Optional[str] = None
        self._port: int = 8420

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def generate_qr_data(self, url: str) -> str:
        try:
            import qrcode
            qr = qrcode.make(url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()
        except ImportError:
            logger.warning("qrcode library not available, returning URL only")
            return ""

    async def start(self, recordings: list[dict], port: int = 8420,
                    password: str = None) -> dict:
        if self._server is not None:
            await self.stop()

        self._recordings = recordings
        self._password = password
        self._port = port

        self._server = await asyncio.start_server(
            self._handle_connection, "0.0.0.0", port
        )

        ip = self.get_local_ip()
        url = f"http://{ip}:{port}"
        qr_base64 = self.generate_qr_data(url)

        logger.info(f"Transfer server started at {url}")
        return {"url": url, "ip": ip, "port": port, "qr_base64": qr_base64}

    async def stop(self) -> bool:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("Transfer server stopped")
            return True
        return False

    @property
    def is_running(self) -> bool:
        return self._server is not None

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter):
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10)
            request = request_line.decode("utf-8", errors="replace").strip()

            headers = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10)
                line = line.decode("utf-8", errors="replace").strip()
                if not line:
                    break
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            if not request:
                writer.close()
                return

            parts = request.split()
            if len(parts) < 2:
                writer.close()
                return

            method, path = parts[0], parts[1]

            if self._password:
                import hashlib
                auth = headers.get("authorization", "")
                if not auth:
                    if "?pw=" in path:
                        pw = path.split("?pw=")[1].split("&")[0]
                        if pw != self._password:
                            await self._send_response(writer, 401, "Unauthorized")
                            return
                    else:
                        await self._send_response(writer, 401, "Unauthorized")
                        return

            if path == "/" or path.startswith("/?"):
                await self._send_html(writer, DOWNLOAD_PAGE_HTML)
            elif path == "/api/clips":
                await self._send_json(writer, [
                    {
                        "filename": r["filename"],
                        "game": r["game"],
                        "size": r["size"],
                        "duration": r["duration"],
                    }
                    for r in self._recordings
                ])
            elif path.startswith("/download/"):
                filename = path[len("/download/"):]
                filename = _url_decode(filename)
                await self._send_file(writer, filename, headers)
            else:
                await self._send_response(writer, 404, "Not Found")

        except Exception as e:
            logger.error(f"Transfer server error: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_response(self, writer, status: int, body: str):
        reason = HTTPStatus(status).phrase
        resp = (
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{body}"
        )
        writer.write(resp.encode())
        await writer.drain()

    async def _send_html(self, writer, html: str):
        encoded = html.encode("utf-8")
        header = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(encoded)}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(header.encode() + encoded)
        await writer.drain()

    async def _send_json(self, writer, data):
        body = json.dumps(data).encode("utf-8")
        header = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(header.encode() + body)
        await writer.drain()

    async def _send_file(self, writer, filename: str, headers: dict):
        recording = None
        for r in self._recordings:
            if r["filename"] == filename:
                recording = r
                break

        if not recording or not os.path.exists(recording["path"]):
            await self._send_response(writer, 404, "File not found")
            return

        filepath = recording["path"]
        file_size = os.path.getsize(filepath)
        content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

        range_header = headers.get("range", "")
        start = 0
        end = file_size - 1

        if range_header.startswith("bytes="):
            range_spec = range_header[6:]
            parts = range_spec.split("-")
            if parts[0]:
                start = int(parts[0])
            if parts[1]:
                end = int(parts[1])
            end = min(end, file_size - 1)

            resp_header = (
                f"HTTP/1.1 206 Partial Content\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {end - start + 1}\r\n"
                f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
                f"Accept-Ranges: bytes\r\n"
                f"Content-Disposition: attachment; filename=\"{filename}\"\r\n"
                f"Connection: close\r\n\r\n"
            )
        else:
            resp_header = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {file_size}\r\n"
                f"Accept-Ranges: bytes\r\n"
                f"Content-Disposition: attachment; filename=\"{filename}\"\r\n"
                f"Connection: close\r\n\r\n"
            )

        writer.write(resp_header.encode())
        await writer.drain()

        chunk_size = 64 * 1024
        with open(filepath, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
                remaining -= len(chunk)


def _url_decode(s: str) -> str:
    import urllib.parse
    return urllib.parse.unquote(s)
