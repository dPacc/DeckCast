import { FC, useState, useEffect, useCallback } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  TextField,
  DropdownItem,
} from "@decky/ui";
import { startStream, stopStream, getStreamStatus, getSettings, saveSettings } from "../utils/api";
import { RESOLUTION_OPTIONS, BITRATE_OPTIONS, FRAMERATE_OPTIONS } from "../utils/constants";
import type { StreamStatus, PluginSettings } from "../types";

export const LiveStreamSetup: FC = () => {
  const [rtmpUrl, setRtmpUrl] = useState("rtmp://a.rtmp.youtube.com/live2");
  const [streamKey, setStreamKey] = useState("");
  const [resolution, setResolution] = useState("1280x720");
  const [bitrate, setBitrate] = useState("4000k");
  const [framerate, setFramerate] = useState(30);
  const [status, setStatus] = useState<StreamStatus>({
    status: "offline",
    error: null,
    running: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const s = await getStreamStatus();
      setStatus(s);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    pollStatus();
    const interval = setInterval(pollStatus, 5000);
    return () => clearInterval(interval);
  }, [pollStatus]);

  useEffect(() => {
    (async () => {
      try {
        const settings = await getSettings();
        if (settings.stream) {
          setResolution(settings.stream.resolution || "1280x720");
          setBitrate(settings.stream.bitrate || "4000k");
          setFramerate(settings.stream.framerate || 30);
          if (settings.stream.saved_stream_keys?.length) {
            setStreamKey(settings.stream.saved_stream_keys[0]);
          }
        }
      } catch {
        // use defaults
      }
    })();
  }, []);

  const handleStart = async () => {
    if (!streamKey) {
      setError("Stream key is required");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await startStream(rtmpUrl, streamKey, resolution, bitrate, framerate);
      if (!result.success) {
        setError(result.error || "Failed to start stream");
      } else {
        // Save stream key for reuse
        try {
          const settings = await getSettings();
          const keys = settings.stream?.saved_stream_keys || [];
          if (!keys.includes(streamKey)) {
            keys.unshift(streamKey);
            settings.stream = { ...settings.stream, saved_stream_keys: keys.slice(0, 5) };
            await saveSettings(settings);
          }
        } catch {
          // non-critical
        }
      }
      await pollStatus();
    } catch (e: any) {
      setError(e?.message || "Stream error");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopStream();
      await pollStatus();
    } catch (e: any) {
      setError(e?.message || "Failed to stop stream");
    } finally {
      setLoading(false);
    }
  };

  const statusColor = {
    offline: "#888",
    connecting: "#ffa500",
    live: "#ff4444",
    error: "#ff6b6b",
  }[status.status];

  return (
    <>
      <PanelSectionRow>
        <div style={{ padding: "8px", textAlign: "center" }}>
          <span style={{
            display: "inline-block",
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: statusColor,
            marginRight: "8px",
          }} />
          <span style={{ color: statusColor, fontWeight: "bold", textTransform: "uppercase" }}>
            {status.status}
          </span>
        </div>
      </PanelSectionRow>

      {status.running ? (
        <>
          <PanelSectionRow>
            <div style={{ padding: "12px", textAlign: "center", color: "#ff4444", fontSize: "1.1em" }}>
              You are LIVE
            </div>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleStop} disabled={loading}>
              {loading ? "Stopping..." : "Stop Stream"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : (
        <>
          <PanelSectionRow>
            <TextField
              label="RTMP URL"
              value={rtmpUrl}
              onChange={(e) => setRtmpUrl(e.target.value)}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <TextField
              label="Stream Key"
              value={streamKey}
              onChange={(e) => setStreamKey(e.target.value)}
              bIsPassword
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              label="Resolution"
              rgOptions={RESOLUTION_OPTIONS.map((o) => ({ label: o.label, data: o.value }))}
              selectedOption={resolution}
              onChange={(opt) => setResolution(opt.data)}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              label="Bitrate"
              rgOptions={BITRATE_OPTIONS.map((o) => ({ label: o.label, data: o.value }))}
              selectedOption={bitrate}
              onChange={(opt) => setBitrate(opt.data)}
            />
          </PanelSectionRow>

          <PanelSectionRow>
            <DropdownItem
              label="Framerate"
              rgOptions={FRAMERATE_OPTIONS.map((o) => ({ label: o.label, data: o.value }))}
              selectedOption={framerate}
              onChange={(opt) => setFramerate(opt.data)}
            />
          </PanelSectionRow>

          {error && (
            <PanelSectionRow>
              <div style={{ color: "#ff6b6b", padding: "8px" }}>{error}</div>
            </PanelSectionRow>
          )}

          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleStart} disabled={loading || !streamKey}>
              {loading ? "Starting..." : "Go Live"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      )}

      <PanelSectionRow>
        <div style={{ padding: "8px", fontSize: "0.8em", color: "#888" }}>
          Get your stream key from YouTube Studio &gt; Go Live &gt; Stream settings
        </div>
      </PanelSectionRow>
    </>
  );
};
