# DeckCast Architecture

## Overview

DeckCast is a Decky Loader plugin for Steam Deck that lets users browse, share, cast, trim, and upload their game recordings. It follows the standard Decky plugin architecture: a Python backend running inside the plugin loader, and a React/TypeScript frontend rendered in the Steam client's CEF browser.

```
┌─────────────────────────────────────────────────┐
│                  Steam Deck                      │
│                                                  │
│  ┌──────────────┐     ┌───────────────────────┐  │
│  │ React/TS UI  │────▶│   Python Backend      │  │
│  │ (QAM Panel)  │     │   (plugin_loader)     │  │
│  └──────────────┘     └───────┬───────────────┘  │
│                               │                  │
│               ┌───────────────┼──────────┐       │
│               ▼               ▼          ▼       │
│        ┌───────────┐  ┌────────────┐ ┌────────┐  │
│        │ Transfer  │  │   Cast     │ │ Stream │  │
│        │ Server    │  │   Manager  │ │Manager │  │
│        │ :8420     │  │ (kmsgrab)  │ │ (RTMP) │  │
│        └─────┬─────┘  └────────────┘ └────────┘  │
│              │                                   │
│              ▼                                   │
│    ┌──────────────────┐                          │
│    │   Web UI         │                          │
│    │ (browser clients)│                          │
│    └──────────────────┘                          │
└─────────────────────────────────────────────────┘
```

## Directory Structure

```
DeckCast/
├── main.py                    # Plugin entry point — wires all backend modules
├── plugin.json                # Decky plugin manifest
├── package.json               # Node build config
├── rollup.config.js           # Frontend bundler config
│
├── backend/
│   ├── recording_scanner.py   # Scans DASH/loose recordings, ffprobe, thumbnails, enhancement
│   ├── clip_trimmer.py        # FFmpeg clip trimming with codec copy
│   ├── cast_manager.py        # Live screen capture via DRM/KMS → HLS
│   ├── stream_manager.py      # RTMP streaming to YouTube/Twitch
│   ├── youtube_auth.py        # OAuth 2.0 device flow for YouTube
│   ├── youtube_upload.py      # Resumable chunked upload via YouTube Data API v3
│   │
│   ├── transfer/              # Modular HTTP transfer server
│   │   ├── __init__.py        # Exports TransferServer
│   │   ├── server.py          # Raw asyncio TCP server, TLS-free
│   │   ├── router.py          # Regex-based route table (GET/POST/DELETE)
│   │   ├── middleware.py      # Auth checking, JSON body parsing, query params
│   │   ├── handlers.py        # Request handlers for all endpoints
│   │   ├── responses.py       # HTTP response helpers (JSON, HTML, file, static)
│   │   └── file_manager.py    # Virtual folders, renames, delete, client secrets
│   │
│   └── web/                   # Static files served by the transfer server
│       ├── index.html         # Main clip browser SPA
│       ├── styles.css         # Dark theme stylesheet
│       ├── app.js             # Client-side JavaScript
│       └── cast.html          # Live cast viewer with HLS.js
│
├── src/                       # React/TypeScript frontend (Decky QAM panel)
│   ├── index.tsx              # Plugin entry, tab navigation, definePlugin()
│   ├── components/
│   │   ├── RecordingBrowser.tsx
│   │   ├── TransferPanel.tsx
│   │   ├── CastPanel.tsx      # Live casting controls
│   │   ├── LiveStreamSetup.tsx
│   │   ├── YouTubeAuth.tsx
│   │   ├── YouTubeUpload.tsx
│   │   ├── ClipTrimmer.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useRecordings.ts
│   │   ├── useTransfer.ts
│   │   └── useYouTube.ts
│   ├── types/index.ts         # TypeScript interfaces
│   └── utils/
│       ├── api.ts             # callable() wrappers for backend methods
│       ├── constants.ts       # UI option arrays and defaults
│       └── fileUtils.ts       # Size formatting, duration formatting
│
├── tests/                     # pytest + vitest test suites
│   ├── test_recording_scanner.py
│   ├── test_transfer_server.py
│   ├── test_router.py
│   ├── test_middleware.py
│   ├── test_handlers.py
│   ├── test_file_manager.py
│   ├── test_clip_trimmer.py
│   ├── test_stream_manager.py
│   ├── test_youtube_auth.py
│   └── test_youtube_upload.py
│
└── defaults/
    └── config.json            # Default plugin settings
```

## Backend Components

### Plugin Entry (`main.py`)

The `Plugin` class is the Decky entry point. It exposes async methods that the frontend calls via `callable()`. On load (`_main`), it initializes the TransferServer, StreamManager, and FileManager. On unload (`_unload`), it stops all running services.

Key responsibilities:
- Scan recordings and apply FileManager display names
- Start/stop the transfer server, cast, and RTMP stream
- Proxy YouTube auth and upload operations
- Folder CRUD and clip management
- Settings persistence via JSON config

### Recording Scanner (`recording_scanner.py`)

Steam Game Recording stores clips in MPEG-DASH format: each clip is a directory containing `session.mpd` (manifest) and `.m4s` segment files. The scanner:

1. Scans `CLIP_SCAN_PATTERNS` for DASH clip directories
2. Scans `LOOSE_VIDEO_PATHS` for standalone video files
3. Parses MPD manifests for duration, resolution, codec info
4. Falls back to `ffprobe` for loose files
5. Generates thumbnails via FFmpeg
6. Muxes DASH segments into a single MP4 for download (cached in `/tmp/deckcast_mux/`)
7. Enhances recordings via Lanczos upscaling (cached in `/tmp/deckcast_mux/../enhanced/`)

### Transfer Server (`backend/transfer/`)

A raw asyncio TCP HTTP server with no framework dependencies (required for the Decky sandbox). Architecture:

```
Client Request
     │
     ▼
  server.py    ← Accepts TCP connections, reads HTTP request
     │
     ▼
  router.py    ← Matches URL pattern → handler function
     │
     ▼
middleware.py  ← Checks auth, parses JSON body, extracts query params
     │
     ▼
 handlers.py   ← Executes business logic, calls responses.py
     │
     ▼
responses.py   ← Formats HTTP response (JSON, HTML, file, static)
```

**Router**: Regex-based route table supporting path parameters via capture groups. Routes are registered with HTTP method + pattern + handler. Returns 404 for no match, 405 for wrong method.

**Middleware**: Optional password authentication via Bearer token or `?pw=` query param. JSON body parsing for POST requests. Query string parsing for GET requests.

**File Manager**: Config-backed virtual folders (JSON persistence, not filesystem moves). Clip renames stored in `renames.json`. Atomic writes via temp file + `os.rename`.

### Cast Manager (`backend/cast_manager.py`)

Live screen casting pipeline:

```
DRM Framebuffer ──▶ kmsgrab ──▶ VAAPI H.264 ──▶ HLS Segments ──▶ Browser
(/dev/dri/card0)                (hardware enc)   (/tmp/deckcast_live/)
                                                       │
PulseAudio ──────▶ AAC encode ─────────────────────────┘
```

Why kmsgrab instead of x11grab:
- Steam Deck Gaming Mode uses gamescope (Wayland compositor with DRM/KMS output)
- Xwayland instances (`:0`, `:1`) are started with `-rootless` — their root windows are empty
- x11grab on `:0.0` captures a black screen
- kmsgrab reads the DRM framebuffer directly — the actual composited display output

Why VAAPI instead of libx264:
- Hardware encoding on the AMD APU — negligible CPU impact
- Outputs browser-compatible H.264 High profile with yuv420p (nv12 via VAAPI)
- x11grab + libx264 produced yuv444p (High 4:4:4 Predictive) which browsers can't decode

Why run as root:
- kmsgrab requires DRM master access (root only)
- PulseAudio accessed via `PULSE_SERVER=unix:/run/user/1000/pulse/native`
- Plugin loader already runs as root

HLS configuration: 2-second segments, 10-segment playlist, `delete_segments+append_list` flags for live streaming with bounded disk usage.

### Stream Manager (`backend/stream_manager.py`)

RTMP streaming to external platforms (YouTube, Twitch). Uses FFmpeg with x11grab (works for Desktop Mode) or can be extended to use kmsgrab. Manages FFmpeg subprocess lifecycle with status polling.

### YouTube Integration

**Auth** (`youtube_auth.py`): OAuth 2.0 with manual code entry (no redirect server needed in the Steam Deck environment). Stores credentials in the plugin data directory.

**Upload** (`youtube_upload.py`): Resumable chunked upload via YouTube Data API v3. Runs in a background thread with progress tracking. Supports title, description, tags, privacy, and category.

## Frontend Architecture

### Decky Plugin UI (React/TypeScript)

The frontend runs inside Steam's CEF browser as a Quick Access Menu (QAM) panel. It uses Decky's component library (`@decky/ui`) for native-looking controls.

**Navigation**: Tab-based with state managed in `index.tsx`. Tabs: Recordings (default), Share, Cast, YouTube, Stream, Settings.

**API Layer** (`api.ts`): All backend communication goes through `callable()` from `@decky/api`, which handles the Decky RPC protocol. Each Python method in `main.py` gets a typed wrapper function.

**State Management**: Local component state with `useState`/`useEffect`. Custom hooks (`useRecordings`, `useTransfer`, `useYouTube`) encapsulate polling and API calls.

### Web UI (Vanilla HTML/CSS/JS)

Served by the transfer server at `http://<deck-ip>:8420/`. No build step — plain HTML, CSS, and JavaScript. Designed for phones, tablets, and desktops accessing the Deck over Wi-Fi.

**Main page** (`index.html` + `styles.css` + `app.js`): Clip browser with grid layout, search/sort/filter, folder sidebar, context menus, video preview lightbox, download (original + enhanced), rename, delete, bulk operations, and settings dialog.

**Cast page** (`cast.html`): Self-contained live viewer. Uses HLS.js for low-latency playback. Offline state with start casting controls, live state with fullscreen video + stop/volume/PiP/fullscreen controls. Auto-polls for stream availability, auto-reconnects on drop.

## Data Flow

### Recording Discovery
```
Filesystem scan → MPD parsing → ffprobe fallback → metadata dict
                                                      │
                                           FileManager display names
                                                      │
                                              Frontend display
```

### Live Casting
```
Deck Plugin UI: "Start Cast"
       │
       ▼
main.py: start_cast()
       │
       ▼
CastManager.start()
  1. Clean /tmp/deckcast_live/
  2. Build FFmpeg command (kmsgrab + VAAPI + HLS)
  3. Spawn subprocess (as root)
  4. Wait 3s, verify process alive
  5. Set state → "live"
       │
       ▼
Browser loads /cast page
  1. Polls /api/cast/status
  2. Detects live=true
  3. HLS.js loads /live/stream.m3u8
  4. Fetches .ts segments via /live/<file>
  5. Plays video in <video> element
```

### File Transfer
```
Browser: GET /api/clips → JSON clip list
Browser: GET /download/<clip_id> → file download (muxes DASH if needed)
Browser: GET /download-enhanced/<clip_id> → enhanced 1080p download
Browser: GET /stream/<clip_id> → inline video playback (no attachment header)
```

## Configuration

Settings stored in `/home/deck/homebrew/data/DeckCast/config.json`:
- `recording_paths`: Additional directories to scan for recordings
- `sd_card_paths`: SD card mount points to scan
- `transfer.port`: HTTP server port (default 8420)
- `transfer.password_enabled` / `transfer.password`: Optional auth
- `youtube.*`: Default upload settings (privacy, title template, tags)
- `stream.*`: Default streaming settings (resolution, bitrate, saved keys)

## Deployment

The plugin runs inside the Decky Loader sandbox on SteamOS. Key constraints:
- No pip install — all Python dependencies must be vendored or stdlib
- No framework dependencies for the HTTP server (raw asyncio)
- Frontend bundle must be a single ESM file (`dist/index.js`)
- Plugin loader runs as root, but X11 display belongs to `deck` user (uid 1000)
- Paths are hardcoded to `/home/deck/homebrew/` (Decky standard)

Deploy: zip the project → scp to Deck → unzip to `/home/deck/homebrew/plugins/DeckCast/` → restart `plugin_loader` service.
