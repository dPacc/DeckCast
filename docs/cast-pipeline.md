# DeckCast — Live Cast Pipeline

## Overview

DeckCast casts the Steam Deck screen to any browser on the local network via HLS.
Two-process pipeline: gpu-screen-recorder → named pipe → FFmpeg → HLS segments → browser.

## Architecture

```
Steam Deck Screen
       ↓
gpu-screen-recorder (portal mode, PipeWire/xdg-desktop-portal-gamescope)
       ↓ raw H264 via named pipe (/tmp/deckcast_gsr_pipe)
FFmpeg (copies video, encodes audio to AAC)
       ↓ HLS segments (/tmp/deckcast_live/seg_XXXXX.ts + stream.m3u8)
Transfer Server (async TCP, port 8420)
       ↓ HTTP
Browser (HLS.js player at /cast)
```

## Key Files

| File | Role |
|------|------|
| `backend/cast_manager.py` | Manages GSR + FFmpeg lifecycle, PID persistence, orphan cleanup |
| `backend/transfer/server.py` | Async HTTP server, serves HLS segments and cast page |
| `backend/transfer/handlers.py` | HTTP route handlers including `/api/cast/start`, `/api/cast/stop` |
| `backend/transfer/router.py` | URL routing table |
| `backend/web/cast.html` | Browser-side HLS player with HLS.js |
| `main.py` | Decky plugin entry point, exposes callables to frontend |
| `src/index.tsx` | Deck UI — single Start/Stop button, cast settings state |
| `src/components/CastPanel.tsx` | Cast settings panel (resolution, bitrate, record toggle) |

## Cast Pipeline Details

### gpu-screen-recorder (GSR)
- Installed as flatpak: `com.dec05eba.gpu_screen_recorder`
- Binary located at: `/var/lib/flatpak/app/com.dec05eba.gpu_screen_recorder/x86_64/stable/*/files/bin/gpu-screen-recorder`
- Uses portal mode (`-w portal`) for PipeWire capture via xdg-desktop-portal-gamescope
- Outputs raw H264 to named pipe
- Runs as `deck` user (demoted from root via `preexec_fn`)
- Environment needs: `WAYLAND_DISPLAY=gamescope-0`, `XDG_RUNTIME_DIR=/run/user/1000`, `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`
- GSR's `LD_LIBRARY_PATH` must point to its flatpak lib dir
- Keyframe interval: ~2 seconds (120 frames at 60fps)

### FFmpeg
- Reads raw H264 from pipe: `-f h264 -framerate 60 -i /tmp/deckcast_gsr_pipe`
- Captures system audio: `-f pulse -ac 2 -i default`
- Video is copied (no re-encode): `-c:v copy`
- Audio encoded to AAC: `-c:a aac -b:a 128k -ar 44100`
- HLS output: `-f hls -hls_time 2 -hls_list_size 5`
- HLS flags: `delete_segments+append_list+omit_endlist`
- Segments written to `/tmp/deckcast_live/`
- Also runs as `deck` user

### HLS Configuration

**Critical: do NOT use `split_by_time`.**
GSR's keyframe interval is ~2 seconds. `split_by_time` forces segment cuts at exact time boundaries regardless of keyframes. This means half the segments start without a keyframe, causing the browser decoder to drop frames at every segment boundary — resulting in stuttery, sub-60fps playback. Without `split_by_time`, FFmpeg waits for the next keyframe to cut, producing clean segments that decode perfectly.

**Critical: `hls_time` must match GSR's keyframe interval (~2s).**
Setting `hls_time=1` with no `split_by_time` still produces 2s segments (FFmpeg waits for keyframe), but the `TARGETDURATION` in the playlist would be wrong. Use `hls_time=2`.

### HLS.js Browser Config
```javascript
{
  liveSyncDurationCount: 2,      // stay 2 segments (4s) behind live edge
  liveMaxLatencyDurationCount: 4, // max 4 segments (8s) behind
  maxLiveSyncPlaybackRate: 1.5,   // catch up at 1.5x if falling behind
  enableWorker: true,
  lowLatencyMode: true,           // start playback quickly
  backBufferLength: 4,
  maxBufferLength: 6,             // must be > liveSyncDurationCount * segment_duration
  maxMaxBufferLength: 12,
  liveDurationInfinity: true,
  highBufferWatchdogPeriod: 1,
}
```

### Autoplay
The video element uses `muted` attribute and starts playback muted, then unmutes after `play()` resolves. This satisfies browser autoplay policies (Chrome blocks unmuted autoplay without user gesture).

## Process Lifecycle

### Starting a Cast
1. `CastManager.start()` checks state guard (`starting`/`live` → reject)
2. `_prepare()` kills orphan processes via `pkill -9 -f`, recreates pipe and live dir
3. GSR started → 2 second wait → check if alive
4. FFmpeg started → 4 second wait → check both alive
5. State transitions to `live`, PID state saved to `/tmp/deckcast_cast_state.json`
6. Total startup time: ~6 seconds

### Stopping a Cast
1. FFmpeg terminated first (SIGTERM → wait 5s → SIGKILL)
2. GSR terminated second
3. `_kill_system_orphans()` catches any strays via pkill
4. Live dir and pipe cleaned up
5. State file removed

### Surviving Plugin Reloads
- `_reattach()` reads `/tmp/deckcast_cast_state.json` on init
- If both GSR and FFmpeg PIDs are alive → reattach (cast continues)
- If only one alive → kill it, clean state
- Transfer server auto-restarts if cast is active on reload
- **Important**: Reattached casts use OLD FFmpeg arguments. Config changes only apply after stop + start.

## Concurrency Guard

`start()` was called twice concurrently (from Deck UI quick cast + Cast panel, or Deck + browser). The second call's `_prepare()` killed the first's GSR, then both calls created FFmpeg processes fighting over the same pipe → corrupted segments → blank video.

Fix: `if self._is_running() or self._state in ("starting", "live"): return error`

The `_is_running()` check alone wasn't enough because it requires BOTH GSR and FFmpeg to be alive. During the 6-second startup (only GSR running, no FFmpeg yet), `_is_running()` returns False, letting a second call through.

## Deck UI Structure

- **Main screen**: One Start/Stop Cast button + URL when live. Nav buttons for sub-pages.
- **Cast page**: Settings only (resolution, bitrate, record toggle). No start button — prevents double-start confusion.
- Cast settings state lives in `index.tsx`, passed to `CastPanel` via props.
- Optimistic status update: clicking Start immediately sets status to "starting" so the button doesn't snap back.

## Failed Approaches (Do Not Repeat)

| Change | Result | Why |
|--------|--------|-----|
| `-fflags +nobuffer+flush_packets` on FFmpeg | `time=N/A`, blank video | Raw H264 pipe input needs buffering for timestamps |
| `-flags +low_delay` on FFmpeg | Broke timestamps | Same reason |
| `hls_time=0.5` | Empty/broken segments | Segments smaller than keyframe interval with `-c:v copy` |
| `hls_list_size=3` | Segments deleted before player fetches | Too few segments in playlist |
| `liveSyncDurationCount: 1` on HLS.js | Not enough buffer, stalls | Too aggressive for 2s segments |
| `lowLatencyMode: false` on HLS.js | Video stuck on first frame | Disables fast playback start |
| `split_by_time` HLS flag | Frame drops at segment boundaries | Segments don't start on keyframes |
| `bufferStalledError` handler seeking back 0.5s | Duplicate frames, stuttery FPS | Replayed frames on every stall |
| `asyncio.to_thread()` on async methods | Unawaited coroutines, cast never starts | `cm.start()`/`cm.stop()` are async — use `await` directly |

## Latency

Expected end-to-end latency: ~5-8 seconds.
- Segment duration: 2 seconds
- `liveSyncDurationCount: 2` → 4 seconds behind live edge
- Encoding + network overhead: ~1-2 seconds

The 10-second latency seen earlier was caused by `split_by_time` — frame drops at segment boundaries caused playback to fall behind, and `maxLiveSyncPlaybackRate: 1.5` couldn't catch up fast enough, so latency drifted over time.
