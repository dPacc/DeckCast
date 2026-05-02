import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeckCast")

CREDENTIALS_DIR = Path.home() / "homebrew/data/DeckCast"
TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

# Users must supply their own OAuth client credentials via plugin settings.
# This avoids embedding secrets in the open-source repo. The plugin ships
# a setup guide that walks users through creating a Google Cloud project.
CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "client_secrets.json"


def _ensure_dir():
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def has_client_secrets() -> bool:
    return CLIENT_SECRETS_FILE.exists()


def get_stored_credentials() -> Optional[dict]:
    if not TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_FILE.read_text())
        return data
    except Exception:
        return None


def save_credentials(creds_data: dict):
    _ensure_dir()
    TOKEN_FILE.write_text(json.dumps(creds_data))
    TOKEN_FILE.chmod(0o600)


def clear_credentials():
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def start_auth_flow() -> dict:
    _ensure_dir()

    if not CLIENT_SECRETS_FILE.exists():
        return {
            "success": False,
            "error": "client_secrets.json not found. See plugin settings for setup instructions.",
        }

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        )

        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        return {"success": True, "auth_url": auth_url, "state": state}

    except ImportError:
        return {
            "success": False,
            "error": "google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib",
        }
    except Exception as e:
        logger.error(f"Auth flow start failed: {e}")
        return {"success": False, "error": str(e)}


def complete_auth_flow(code: str) -> dict:
    if not CLIENT_SECRETS_FILE.exists():
        return {"success": False, "error": "client_secrets.json not found"}

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        )

        flow.fetch_token(code=code)
        creds = flow.credentials

        creds_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes),
        }
        save_credentials(creds_data)

        return {"success": True}

    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        return {"success": False, "error": str(e)}


def get_authenticated_credentials():
    stored = get_stored_credentials()
    if not stored:
        return None

    try:
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=stored["token"],
            refresh_token=stored.get("refresh_token"),
            token_uri=stored.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=stored.get("client_id"),
            client_secret=stored.get("client_secret"),
            scopes=stored.get("scopes", SCOPES),
        )

        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            save_credentials({
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes or SCOPES),
            })

        return creds

    except Exception as e:
        logger.error(f"Credential refresh failed: {e}")
        return None


def get_channel_info() -> Optional[dict]:
    creds = get_authenticated_credentials()
    if not creds:
        return None

    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()

        items = response.get("items", [])
        if items:
            snippet = items[0]["snippet"]
            return {
                "name": snippet.get("title", "Unknown"),
                "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            }
    except Exception as e:
        logger.error(f"Failed to get channel info: {e}")

    return None
