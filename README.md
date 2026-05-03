# DeckCast

A [Decky Loader](https://decky.xyz) plugin for Steam Deck that lets you cast your screen live, share recordings, upload to YouTube, and stream to Twitch — all from Gaming Mode. No Desktop Mode, no size limits, no workarounds.

## Why DeckCast?

Steam Deck's built-in sharing is broken for anything serious:

| What you want | What Steam gives you | What DeckCast gives you |
|---|---|---|
| Cast screen to phone/TV | Not possible | Live 60fps cast to any browser on your network |
| Transfer a 20-min clip to your phone | QR code caps at 60 seconds | Wi-Fi transfer, any size, scan & download |
| Upload to YouTube | Desktop Mode + Chrome + keyboard struggle | One-tap upload from Gaming Mode |
| Send to your PC | "Send to PC" — takes up to 2 days | Instant Wi-Fi download from any browser |
| Trim before sharing | Nothing | Built-in trimmer, no re-encoding |
| Live stream | Not possible | RTMP streaming to YouTube/Twitch |

## Features

### Live Cast (New)
Cast your Steam Deck screen to any browser on your local network in real-time at 60fps. One tap to start — open the URL on your phone, tablet, laptop, or TV browser to watch. Uses gpu-screen-recorder for hardware-accelerated capture via PipeWire, piped through FFmpeg to HLS segments served over HTTP. Features include:
- 60fps hardware capture with zero re-encoding overhead
- Configurable resolution (720p, 800p native, 1080p) and quality (4-12 Mbps)
- ~5-8 second latency over local network
- Optional simultaneous recording while casting
- Browser player with volume control, fullscreen, and Picture-in-Picture
- Cast survives plugin reloads — pick up where you left off
- Start/stop from the browser page or the Deck UI

### Recording Browser
Browse all your Steam recordings in one place. See game name, duration, file size, and date. Sort by date, size, or game. Scans both internal storage and SD card automatically.

### Wi-Fi Transfer (No Size Limits)
Start a local web server on your Deck, scan the QR code with your phone, and download clips directly. Works on your local network — no internet needed, no file size caps. Supports resumable downloads for large files. Optional password protection.

### YouTube Upload
Upload recordings straight to YouTube without leaving Gaming Mode. Set title, description, tags, privacy, and category. Uploads run in the background so you can keep gaming. Progress bar shows upload status. Auto-populates title from game name and date.

### Clip Trimmer
Set start and end points with sliders, then trim using FFmpeg's codec copy — instant trim with no quality loss and no re-encoding. Save the trimmed clip or upload it directly.

### Live Streaming
Stream your gameplay to YouTube, Twitch, or any RTMP endpoint. Configure resolution (720p/1080p), bitrate, and framerate. Save your stream key for one-tap "Go Live" next time.

### Background Operations
Uploads, transfers, and casts continue running while you game. Come back to check progress whenever you want.

## Installation

### From Decky Plugin Store (recommended)
1. Install [Decky Loader](https://decky.xyz) on your Steam Deck
2. Open the Quick Access Menu (`...` button)
3. Go to the Decky tab (plug icon)
4. Open the plugin store (shopping bag icon)
5. Search for **DeckCast**
6. Install

### Manual Install / Sideload
1. Download `DeckCast.zip` from [Releases](https://github.com/dPacc/DeckCast/releases)
2. On your Steam Deck, open Desktop Mode
3. Extract the zip to `~/homebrew/plugins/DeckCast/`
4. Reboot back to Gaming Mode (or restart Decky from Desktop Mode)

### Install via SSH
```bash
# From another computer on the same network
curl -L https://github.com/dPacc/DeckCast/releases/latest/download/DeckCast.zip -o /tmp/DeckCast.zip
unzip /tmp/DeckCast.zip -d ~/homebrew/plugins/
sudo systemctl stop plugin_loader && sleep 3 && sudo systemctl start plugin_loader
```

> **Warning:** Never use `systemctl restart plugin_loader`. Decky binds ports that need time to release — `restart` causes a port conflict crash loop. Always use `stop`, wait 3 seconds, then `start`.

## Setup

### Live Cast
No setup needed for basic casting. Just tap **Start Casting** in DeckCast — the cast URL appears on screen. Open it on any device's browser on the same network.

**Requirement:** [gpu-screen-recorder](https://flathub.org/apps/com.dec05eba.gpu_screen_recorder) must be installed as a Flatpak:
```bash
flatpak install com.dec05eba.gpu_screen_recorder
```
This is pre-installed on most SteamOS setups. FFmpeg is also pre-installed on SteamOS.

### Wi-Fi Transfer
No setup needed. Open DeckCast, tap **Transfer**, tap **Start Transfer Server**, and scan the QR code from any device on your network.

### YouTube Integration
DeckCast uses the YouTube Data API v3. Since this is an open-source plugin, you need to provide your own Google API credentials (takes ~5 minutes):

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. "DeckCast")
3. Go to **APIs & Services** → **Library** → search for **YouTube Data API v3** → **Enable**
4. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. If prompted, configure the OAuth consent screen (External, add your email as test user)
6. Application type: **Desktop app**, name: "DeckCast"
7. Click **Download JSON** on the created credential
8. Transfer the JSON file to your Steam Deck and save it as:
   ```
   ~/homebrew/data/DeckCast/client_secrets.json
   ```
9. In DeckCast, go to the **YouTube** tab and tap **Connect YouTube Account**
10. Follow the on-screen instructions to authorize

> **Why do I need my own credentials?** Google requires OAuth credentials to be kept private. Since DeckCast is open source, we can't bundle credentials — every user creates their own free API project. This is standard practice for open-source YouTube tools.

### Live Streaming
1. On your phone/PC, go to [YouTube Studio](https://studio.youtube.com) → **Go Live** → **Stream**
2. Copy your **Stream key**
3. In DeckCast, go to the **Stream** tab
4. Paste your stream key (it's saved for next time)
5. Configure resolution/bitrate if needed
6. Tap **Go Live**

Works with any RTMP endpoint — YouTube, Twitch (`rtmp://live.twitch.tv/app`), or custom servers.

## Python Dependencies

These libraries are needed on the Steam Deck for full functionality:

```bash
# SSH into your Deck or use Desktop Mode terminal
pip install google-auth google-auth-oauthlib google-api-python-client qrcode Pillow
```

FFmpeg is pre-installed on SteamOS — no setup needed for trimming and streaming.

## Building from Source

### Prerequisites
- Node.js 18+ (20 recommended)
- pnpm
- Python 3.10+
- FFmpeg (for tests)

### Build
```bash
git clone https://github.com/dPacc/DeckCast.git
cd DeckCast
pnpm install
pnpm build
```

### Run Tests
```bash
# Frontend tests (vitest)
pnpm test

# Backend tests (pytest)
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

### Package for Installation
```bash
mkdir -p out/DeckCast
cp -r dist backend defaults assets main.py plugin.json package.json LICENSE README.md out/DeckCast/
cd out && zip -r ../DeckCast.zip DeckCast/
```

### Docker Build (for CI)
```bash
# Uses the Decky plugin template's Dockerfile pattern
docker build -t deckcast .
docker run --rm -v $(pwd)/out:/out deckcast
```

## Project Structure

```
DeckCast/
├── main.py                    # Plugin entry point — Decky calls this
├── backend/
│   ├── cast_manager.py        # Live cast pipeline (GSR → pipe → FFmpeg → HLS)
│   ├── recording_scanner.py   # Find and catalog .mp4 files
│   ├── clip_trimmer.py        # FFmpeg trim (codec copy, no re-encoding)
│   ├── youtube_auth.py        # YouTube OAuth 2.0 flow
│   ├── youtube_upload.py      # YouTube Data API v3 upload
│   ├── stream_manager.py      # RTMP live stream via FFmpeg
│   ├── transfer/
│   │   ├── server.py          # Async HTTP server (port 8420)
│   │   ├── handlers.py        # Route handlers (cast API, file serving, HLS)
│   │   └── router.py          # URL routing table
│   └── web/
│       └── cast.html          # Browser-side HLS player (HLS.js)
├── src/
│   ├── index.tsx              # Plugin entry (React sidebar UI + cast state)
│   ├── components/
│   │   ├── CastPanel.tsx      # Cast settings (resolution, bitrate, record)
│   │   ├── RecordingBrowser.tsx
│   │   ├── TransferPanel.tsx
│   │   ├── YouTubeAuth.tsx
│   │   ├── YouTubeUpload.tsx
│   │   ├── ClipTrimmer.tsx
│   │   ├── LiveStreamSetup.tsx
│   │   └── Settings.tsx
│   ├── hooks/                 # React hooks for state management
│   ├── utils/                 # API helpers, formatting, constants
│   └── types/                 # TypeScript interfaces
├── docs/
│   ├── cast-pipeline.md       # Cast architecture & troubleshooting
│   └── deployment.md          # Build, deploy, and debug guide
├── tests/                     # Python backend tests (pytest)
├── defaults/config.json       # Default plugin settings
├── plugin.json                # Decky plugin metadata
└── .github/workflows/build.yml  # CI: build + test + release
```

## FAQ

**Q: Does this work in Desktop Mode?**
A: DeckCast is designed for Gaming Mode via Decky Loader. It won't appear in Desktop Mode.

**Q: Can I transfer files larger than 4GB?**
A: Yes. The Wi-Fi transfer server has no file size limit and supports resumable downloads.

**Q: Do uploads count against my YouTube quota?**
A: YouTube's free API quota is 10,000 units/day. A single upload costs ~1,600 units, so you can upload about 6 videos per day. This is plenty for personal use.

**Q: Can I stream to Twitch instead of YouTube?**
A: Yes. Change the RTMP URL to `rtmp://live.twitch.tv/app` and use your Twitch stream key.

**Q: Where are my recordings stored?**
A: Steam stores recordings in `~/.local/share/Steam/userdata/<id>/gamerecordings/`. DeckCast also checks `~/Videos/` and SD card paths. You can add custom paths in Settings.

**Q: The trim is instant — does it lose quality?**
A: No. Trimming uses FFmpeg's `-c copy` flag which copies the video/audio streams without re-encoding. Zero quality loss.

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pnpm test && python -m pytest tests/`)
5. Submit a pull request

Issues, feature requests, and bug reports welcome on [GitHub Issues](https://github.com/dPacc/DeckCast/issues).

## License

GPL-3.0 — see [LICENSE](LICENSE)

## Credits

Built with [Decky Loader](https://decky.xyz) and the [decky-plugin-template](https://github.com/SteamDeckHomebrew/decky-plugin-template).

---

*Born from the frustration of trying to upload a 20-minute NFS Most Wanted clip from a Steam Deck to YouTube. The built-in sharing breaks for long clips, "Send to PC" takes forever, and Desktop Mode kills the gaming flow. DeckCast makes sharing game clips as easy as it should be.*
