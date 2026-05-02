# DeckCast — Deployment Guide

## Steam Deck Connection

- **IP**: 192.168.1.231 (check Settings > Network on Deck if changed)
- **User**: deck
- **Password**: redhat
- **SSH**: `sshpass -p 'redhat' ssh deck@192.168.1.231`

## Build & Deploy

### 1. Build Frontend
```bash
pnpm build
```
Builds React/TypeScript frontend to `dist/`.

### 2. Package Plugin
```bash
rm -rf out DeckCast.zip
mkdir -p out/DeckCast
cp -r dist backend defaults assets out/DeckCast/
cp main.py plugin.json package.json LICENSE out/DeckCast/
cd out && zip -r ../DeckCast.zip DeckCast/
```

### 3. Upload & Deploy
```bash
# Remove old plugin
sshpass -p 'redhat' ssh deck@192.168.1.231 \
  "echo 'redhat' | sudo -S rm -rf ~/homebrew/plugins/DeckCast"

# Upload zip
sshpass -p 'redhat' scp DeckCast.zip deck@192.168.1.231:/tmp/DeckCast.zip

# Unzip + restart (MUST use stop/sleep/start — see below)
sshpass -p 'redhat' ssh deck@192.168.1.231 \
  "echo 'redhat' | sudo -S systemctl stop plugin_loader; \
   sleep 3; \
   echo 'redhat' | sudo -S unzip -o /tmp/DeckCast.zip -d ~/homebrew/plugins/ > /dev/null 2>&1 && \
   echo 'redhat' | sudo -S systemctl start plugin_loader && \
   echo 'deployed and restarted'"
```

### Hot-Deploy Single Files (No Restart)
For backend/web files that don't need a plugin restart (e.g., `cast.html`):
```bash
sshpass -p 'redhat' scp backend/web/cast.html deck@192.168.1.231:/tmp/cast.html
sshpass -p 'redhat' ssh deck@192.168.1.231 \
  "echo 'redhat' | sudo -S cp /tmp/cast.html /home/deck/homebrew/plugins/DeckCast/backend/web/cast.html"
```
Browser refresh picks up the new file. No plugin restart needed.
Note: if a cast is running, it keeps using OLD FFmpeg arguments until stop + start.

## Critical: Plugin Restart Method

**NEVER use `systemctl restart plugin_loader`.**

Decky Loader binds ports 1337 and 44443. `restart` doesn't give the old process time to release them, causing:
- Port conflict → crash
- Crash triggers restart → port still held → crash loop
- Steam UI shows login screen repeatedly
- Requires hard power cycle to recover

**Always use stop → sleep 3 → start:**
```bash
sudo systemctl stop plugin_loader
sleep 3
sudo systemctl start plugin_loader
```

The 3-second sleep gives the old process time to release ports.

## Plugin Path
```
/home/deck/homebrew/plugins/DeckCast/
```
This directory is root-owned. All writes need `sudo`.

## Checking Logs

### Decky Plugin Loader
```bash
sudo journalctl -u plugin_loader --no-pager -n 50
# Filter for DeckCast only:
sudo journalctl -u plugin_loader --since '5 minutes ago' --no-pager | grep -i deckcast
```

### Cast Logs
```bash
cat /tmp/deckcast_gsr.log     # GSR output (fps, PipeWire state)
cat /tmp/deckcast_ffmpeg.log  # FFmpeg output (fps, segment writes, errors)
cat /tmp/deckcast_cast_state.json  # PID persistence state
```

### Process Check
```bash
ps aux | grep -E 'gpu-screen-recorder|ffmpeg|deckcast' | grep -v grep
```

### API Check
```bash
curl -s http://localhost:8420/api/cast/status
curl -s -X POST http://localhost:8420/api/cast/stop
```

## Debugging Cast Issues

### Video blank / no segments
1. Check GSR log for `paused → unconnected` (PipeWire disconnected)
2. Check if both GSR and FFmpeg are running (`ps aux`)
3. Check `/tmp/deckcast_live/` for segments
4. Check segment sizes (very small = no video data)

### Double start / orphan processes
1. Check Decky log for duplicate "GSR started" / "FFmpeg started" lines
2. `pkill -9 -f deckcast_gsr_pipe` to kill orphans manually
3. State guard in `start()` prevents this now

### Frame drops / not 60fps
1. Verify FFmpeg log shows `fps= 60`
2. Verify GSR log shows `update fps: 60`
3. Check that `split_by_time` is NOT in the FFmpeg command (`ps aux | grep ffmpeg`)
4. Check segments start with keyframes: `ffprobe -show_frames -select_streams v:0 /tmp/deckcast_live/seg_XXXXX.ts | head -4`

### Transfer server port conflict
Server.py has `fuser -k {port}/tcp` retry on OSError. If port 8420 is stuck:
```bash
fuser -k 8420/tcp
```

### Deck stuck in login loop
Caused by `systemctl restart plugin_loader`. Hard power-off (hold power button 10s), then boot and use stop/sleep/start method.
