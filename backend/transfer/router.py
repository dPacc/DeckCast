import re
from typing import Optional

# Each entry: (HTTP method, regex pattern, handler function name)
# Patterns are matched against the clean path (without query string).
routes: list[tuple[str, str, str]] = [
    ("GET",    r"^/$",                                   "serve_index"),
    ("GET",    r"^/static/(.+)$",                        "serve_static"),
    ("GET",    r"^/api/clips$",                          "list_clips"),
    ("GET",    r"^/api/clips/([^/]+)/thumbnail$",        "serve_thumbnail"),
    ("PUT",    r"^/api/clips/([^/]+)/rename$",           "rename_clip"),
    ("DELETE", r"^/api/clips/([^/]+)$",                  "delete_clip"),
    ("GET",    r"^/api/folders$",                        "list_folders"),
    ("POST",   r"^/api/folders$",                        "create_folder"),
    ("PUT",    r"^/api/folders/([^/]+)$",                "rename_folder"),
    ("DELETE", r"^/api/folders/([^/]+)$",                "delete_folder"),
    ("POST",   r"^/api/folders/([^/]+)/clips$",          "assign_clips"),
    ("DELETE", r"^/api/folders/([^/]+)/clips$",          "remove_clips"),
    ("GET",    r"^/download/(.+)$",                      "download_file"),
    ("GET",    r"^/download-enhanced/(.+)$",              "download_enhanced_file"),
    ("GET",    r"^/stream/(.+)$",                         "stream_file"),
    ("POST",   r"^/api/youtube/client-secrets$",         "upload_client_secrets"),
    ("GET",    r"^/api/youtube/client-secrets/status$",  "client_secrets_status"),
    ("GET",    r"^/cast$",                                "serve_cast_page"),
    ("GET",    r"^/api/cast/status$",                     "cast_status"),
    ("POST",   r"^/api/cast/start$",                      "cast_start"),
    ("POST",   r"^/api/cast/stop$",                       "cast_stop"),
    ("GET",    r"^/live/(.+)$",                           "serve_live_segment"),
]

# Pre-compile patterns for performance
_compiled_routes: list[tuple[str, re.Pattern, str]] = [
    (method, re.compile(pattern), handler)
    for method, pattern, handler in routes
]


def match_route(method: str, path: str) -> Optional[tuple[str, list[str]]]:
    """
    Match an HTTP method and path against the route table.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: URL path without query string.

    Returns:
        (handler_name, captured_groups) if a route matches, else None.
        If the path matches a route but with the wrong method, this still
        returns None -- the caller should check separately for 405 if desired.
    """
    method = method.upper()
    path_matches_any = False

    for route_method, pattern, handler_name in _compiled_routes:
        m = pattern.match(path)
        if m:
            path_matches_any = True
            if route_method == method:
                return (handler_name, list(m.groups()))

    # Return None for both "no match" and "wrong method".
    # Callers that need to distinguish can use match_route_any().
    return None


def match_route_any(path: str) -> bool:
    """
    Check if any route matches the given path regardless of HTTP method.
    Used to determine whether to send 404 (no route) or 405 (wrong method).
    """
    for _, pattern, _ in _compiled_routes:
        if pattern.match(path):
            return True
    return False
