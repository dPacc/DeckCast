# 📺 DeckCast

**Cast your Steam Deck screen to any browser at 60fps. Share recordings, upload to YouTube, stream to Twitch — all from Gaming Mode.**

A [Decky Loader](https://decky.xyz) plugin that does what Steam's built-in sharing should have done from the start.

---

## 💡 Why DeckCast?

Steam Deck's built-in sharing is broken for anything serious:

| | What you want | Steam's answer | DeckCast's answer |
|---|---|---|---|
| 📺 | Cast screen to phone/TV | ❌ Not possible | ✅ Live 60fps to any browser |
| 📲 | Transfer a 20-min clip | ❌ QR code caps at 60s | ✅ Wi-Fi transfer, any size |
| 🎬 | Upload to YouTube | 😩 Desktop Mode + Chrome | ✅ One-tap from Gaming Mode |
| 💻 | Send to your PC | 🐌 "Send to PC" — up to 2 days | ✅ Instant Wi-Fi download |
| ✂️ | Trim before sharing | ❌ Nothing | ✅ Built-in trimmer, zero quality loss |
| 📡 | Live stream | ❌ Not possible | ✅ RTMP to YouTube/Twitch |

---

## ✨ Features

### 📺 Live Cast
Cast your Steam Deck screen to **any browser** on your local network in real-time at **60fps**.

One tap to start — the cast URL appears on screen. Open it on your phone, tablet, laptop, or TV browser.

- 🎮 Hardware-accelerated capture via gpu-screen-recorder + PipeWire
- 🎯 60fps with zero re-encoding overhead
- 📐 Configurable resolution (720p, 800p native, 1080p) and quality (4–12 Mbps)
- ⏱️ ~5–8 second latency over local network
- 🔴 Optional simultaneous recording while casting
- 🖥️ Browser player with volume control, fullscreen, and Picture-in-Picture
- 🔄 Cast survives plugin reloads — pick up where you left off
- 🎛️ Start/stop from the browser page or the Deck UI

### 📁 Recording Browser
Browse all your Steam recordings in one place. Game name, duration, file size, and date at a glance. Scans internal storage and SD card automatically.

### 📲 Wi-Fi Transfer
Start a local web server, scan the QR code, download clips directly to your phone or PC. **No internet needed, no file size caps.** Supports resumable downloads and optional password protection.

### 🎬 YouTube Upload
Upload recordings straight to YouTube without leaving Gaming Mode. Set title, description, tags, privacy, and category. Uploads run in the background so you keep gaming.

### ✂️ Clip Trimmer
Set start and end points, trim instantly using FFmpeg codec copy — **zero quality loss, no re-encoding**. Save the trimmed clip or upload it directly.

### 📡 Live Streaming
Stream gameplay to YouTube, Twitch, or any RTMP endpoint. Configure resolution, bitrate, and framerate. Save your stream key for one-tap **Go Live**.

### ⚡ Background Operations
Uploads, transfers, and casts keep running while you game. Come back to check progress whenever you want.

---

## 🚀 Installation

### From Decky Plugin Store (recommended)
1. Install [Decky Loader](https://decky.xyz) on your Steam Deck
2. Open the Quick Access Menu ( `...` button)
3. Go to the Decky tab (🔌 plug icon)
4. Open the plugin store (🛍️ shopping bag icon)
5. Search for **DeckCast** → Install

### Manual Install
1. Download `DeckCast.zip` from [Releases](https://github.com/dPacc/DeckCast/releases)
2. Extract to `~/homebrew/plugins/DeckCast/`
3. Restart the plugin loader (see below)

### Install via SSH
```bash
curl -L https://github.com/dPacc/DeckCast/releases/latest/download/DeckCast.zip -o /tmp/DeckCast.zip
unzip /tmp/DeckCast.zip -d ~/homebrew/plugins/
sudo systemctl stop plugin_loader && sleep 3 && sudo systemctl start plugin_loader
```

> ⚠️ **Never use `systemctl restart plugin_loader`.** Decky binds ports that need time to release — `restart` causes a port conflict crash loop. Always use **stop → sleep 3 → start**.

---

## ⚙️ Setup

### 📺 Live Cast
**No setup needed.** Tap **Start Casting** → cast URL appears → open it on any device's browser.

**Requirement:** gpu-screen-recorder must be installed (pre-installed on most SteamOS setups):
```bash
flatpak install com.dec05eba.gpu_screen_recorder
```

### 📲 Wi-Fi Transfer
**No setup needed.** Open DeckCast → **Share** → **Start Transfer Server** → scan QR code.

### 🎬 YouTube Integration
DeckCast uses the YouTube Data API v3. Since this is open-source, you provide your own Google API credentials (takes ~5 minutes):

<details>
<summary><strong>Click to expand YouTube setup steps</strong></summary>

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. "DeckCast")
3. **APIs & Services** → **Library** → search **YouTube Data API v3** → **Enable**
4. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure the OAuth consent screen if prompted (External, add your email as test user)
6. Application type: **Desktop app**, name: "DeckCast"
7. **Download JSON** on the created credential
8. Transfer the JSON to your Deck and save as:
   ```
   ~/homebrew/data/DeckCast/client_secrets.json
   ```
9. In DeckCast → **YouTube** tab → **Connect YouTube Account**
10. Follow the on-screen instructions to authorize

> **Why my own credentials?** Google requires OAuth credentials to be private. Since DeckCast is open source, we can't bundle them — every user creates their own free API project. This is standard practice for open-source YouTube tools.

</details>

### 📡 Live Streaming
1. Go to [YouTube Studio](https://studio.youtube.com) → **Go Live** → copy your **Stream key**
2. In DeckCast → **Stream** tab → paste stream key (saved for next time)
3. Configure resolution/bitrate → **Go Live**

Works with any RTMP endpoint — YouTube, Twitch (`rtmp://live.twitch.tv/app`), or custom servers.

---

## 📦 Python Dependencies

```bash
pip install google-auth google-auth-oauthlib google-api-python-client qrcode Pillow
```

> Only needed for YouTube upload and QR code features. **Live Cast and Wi-Fi Transfer work without these.**

FFmpeg is pre-installed on SteamOS.

---

## 🛠️ Building from Source

```bash
git clone https://github.com/dPacc/DeckCast.git
cd DeckCast
pnpm install
pnpm build
```

### Run Tests
```bash
pnpm test                              # Frontend (vitest)
pip install pytest pytest-asyncio
python -m pytest tests/ -v             # Backend (pytest)
```

### Package for Installation
```bash
mkdir -p out/DeckCast
cp -r dist backend defaults assets main.py plugin.json package.json LICENSE out/DeckCast/
cd out && zip -r ../DeckCast.zip DeckCast/
```

---

## 🗂️ Project Structure

```
DeckCast/
├── main.py                        # Plugin entry point
├── backend/
│   ├── cast_manager.py            # Live cast pipeline (GSR → FFmpeg → HLS)
│   ├── recording_scanner.py       # Find and catalog recordings
│   ├── clip_trimmer.py            # FFmpeg trim (codec copy)
│   ├── youtube_auth.py            # YouTube OAuth 2.0
│   ├── youtube_upload.py          # YouTube Data API v3
│   ├── stream_manager.py          # RTMP live streaming
│   ├── transfer/
│   │   ├── server.py              # Async HTTP server (port 8420)
│   │   ├── handlers.py            # Route handlers (cast API, HLS, files)
│   │   └── router.py              # URL routing
│   └── web/
│       └── cast.html              # Browser HLS player (HLS.js)
├── src/
│   ├── index.tsx                  # Plugin entry (React UI + cast state)
│   ├── components/
│   │   ├── CastPanel.tsx          # Cast settings
│   │   ├── RecordingBrowser.tsx   # Recording list
│   │   ├── TransferPanel.tsx      # Wi-Fi transfer
│   │   ├── YouTubeAuth.tsx        # YouTube login
│   │   ├── YouTubeUpload.tsx      # YouTube upload
│   │   ├── ClipTrimmer.tsx        # Trim UI
│   │   ├── LiveStreamSetup.tsx    # RTMP config
│   │   └── Settings.tsx           # Plugin settings
│   ├── hooks/                     # React hooks
│   ├── utils/                     # API helpers, constants
│   └── types/                     # TypeScript interfaces
├── docs/
│   ├── cast-pipeline.md           # Cast architecture & troubleshooting
│   └── deployment.md              # Build, deploy & debug guide
├── tests/                         # Backend tests (pytest)
├── plugin.json                    # Decky plugin metadata
└── package.json                   # Frontend config
```

---

## ❓ FAQ

<details>
<summary><strong>Does this work in Desktop Mode?</strong></summary>
DeckCast is designed for Gaming Mode via Decky Loader. It won't appear in Desktop Mode.
</details>

<details>
<summary><strong>Can I transfer files larger than 4GB?</strong></summary>
Yes. The Wi-Fi transfer server has no file size limit and supports resumable downloads.
</details>

<details>
<summary><strong>Do uploads count against my YouTube quota?</strong></summary>
YouTube's free API quota is 10,000 units/day. A single upload costs ~1,600 units — about 6 videos per day. Plenty for personal use.
</details>

<details>
<summary><strong>Can I stream to Twitch instead of YouTube?</strong></summary>
Yes. Change the RTMP URL to <code>rtmp://live.twitch.tv/app</code> and use your Twitch stream key.
</details>

<details>
<summary><strong>Where are my recordings stored?</strong></summary>
Steam stores recordings in <code>~/.local/share/Steam/userdata/&lt;id&gt;/gamerecordings/</code>. DeckCast also checks <code>~/Videos/</code> and SD card paths. You can add custom paths in Settings.
</details>

<details>
<summary><strong>The trim is instant — does it lose quality?</strong></summary>
No. Trimming uses FFmpeg's <code>-c copy</code> flag which copies video/audio streams without re-encoding. Zero quality loss.
</details>

<details>
<summary><strong>What latency does Live Cast have?</strong></summary>
~5–8 seconds over local network. This is inherent to HLS — segments are 2 seconds each, and the player buffers 2 segments behind the live edge.
</details>

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pnpm test && python -m pytest tests/`)
5. Submit a pull request

Issues, feature requests, and bug reports welcome on [GitHub Issues](https://github.com/dPacc/DeckCast/issues).

## 📄 License

GPL-3.0 — see [LICENSE](LICENSE)

## 🙏 Credits

Built with [Decky Loader](https://decky.xyz) and the [decky-plugin-template](https://github.com/SteamDeckHomebrew/decky-plugin-template).

---

<p align="center">
<em>Born from the frustration of trying to share a 20-minute NFS Most Wanted clip from a Steam Deck. The built-in sharing breaks for long clips, "Send to PC" takes forever, and Desktop Mode kills the gaming flow. DeckCast makes sharing game clips as easy as it should be.</em>
</p>
