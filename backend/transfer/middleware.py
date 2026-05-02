import asyncio
import json
import logging
import urllib.parse
from typing import Optional

logger = logging.getLogger("DeckCast")

# Maximum request body size: 1 MB
_MAX_BODY_SIZE = 1 * 1024 * 1024

# Timeout for reading individual lines / body
_READ_TIMEOUT = 10


async def parse_request(
    reader: asyncio.StreamReader,
) -> tuple[str, str, dict[str, str], bytes]:
    """
    Read and parse a raw HTTP/1.1 request from the stream.

    Returns:
        (method, path, headers, body) where headers keys are lowercase.
        On malformed/empty requests returns ("", "", {}, b"").
    """
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=_READ_TIMEOUT)
    except (asyncio.TimeoutError, ConnectionResetError):
        return ("", "", {}, b"")

    request_str = request_line.decode("utf-8", errors="replace").strip()
    if not request_str:
        return ("", "", {}, b"")

    parts = request_str.split(None, 2)
    if len(parts) < 2:
        return ("", "", {}, b"")

    method = parts[0].upper()
    raw_path = parts[1]

    # Decode percent-encoded path (but not query string yet)
    path = urllib.parse.unquote(raw_path)

    # Parse headers
    headers: dict[str, str] = {}
    while True:
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=_READ_TIMEOUT)
        except (asyncio.TimeoutError, ConnectionResetError):
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            break
        if ":" in decoded:
            key, val = decoded.split(":", 1)
            headers[key.strip().lower()] = val.strip()

    # Read body if Content-Length is present
    body = b""
    content_length = headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
            length = min(length, _MAX_BODY_SIZE)
            body = await asyncio.wait_for(reader.readexactly(length), timeout=_READ_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, ValueError):
            pass

    return (method, path, headers, body)


def check_auth(headers: dict[str, str], path: str, password: Optional[str]) -> bool:
    """
    Validate the request against the configured password.

    Returns True if:
      - No password is set (open server)
      - The Authorization header matches "Bearer <password>"
      - The query string contains ?pw=<password>
    """
    if not password:
        return True

    # Check Authorization header
    auth = headers.get("authorization", "")
    if auth:
        # Support "Bearer <pw>" and plain "<pw>"
        token = auth
        if token.lower().startswith("bearer "):
            token = token[7:]
        if token == password:
            return True

    # Check query-string fallback
    if "?pw=" in path or "&pw=" in path:
        _, query_part = parse_query_params(path)
        if query_part.get("pw") == password:
            return True

    return False


def parse_json_body(body: bytes) -> dict:
    """
    Parse a JSON request body.

    Returns an empty dict if the body is empty or not valid JSON.
    """
    if not body:
        return {}
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def parse_query_params(path: str) -> tuple[str, dict[str, str]]:
    """
    Split the path from query parameters.

    Returns:
        (clean_path, params_dict) where params_dict maps param names to values.
    """
    if "?" not in path:
        return (path, {})

    clean_path, query_string = path.split("?", 1)
    params: dict[str, str] = {}
    for pair in query_string.split("&"):
        if "=" in pair:
            key, val = pair.split("=", 1)
            params[urllib.parse.unquote(key)] = urllib.parse.unquote(val)
        elif pair:
            params[urllib.parse.unquote(pair)] = ""

    return (clean_path, params)
