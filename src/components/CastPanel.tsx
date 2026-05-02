import { FC, useState, useEffect, useCallback } from "react";
import {
  ButtonItem,
  Focusable,
  PanelSectionRow,
  ToggleField,
} from "@decky/ui";
import {
  startCast,
  stopCast,
  getCastStatus,
  getTransferStatus,
  startTransferServer,
} from "../utils/api";
import { CAST_RESOLUTION_OPTIONS, BITRATE_OPTIONS, DEFAULT_TRANSFER_PORT } from "../utils/constants";
import type { CastStatus } from "../types";

export const CastPanel: FC = () => {
  const [resolution, setResolution] = useState("1280x800");
  const [bitrate, setBitrate] = useState("6000k");
  const [record, setRecord] = useState(false);
  const [status, setStatus] = useState<CastStatus>({ status: "offline" });
  const [transferRunning, setTransferRunning] = useState(false);
  const [transferIp, setTransferIp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const castSt = await getCastStatus();
      if (castSt && castSt.status) setStatus(castSt);
    } catch { /* ignore */ }
    try {
      const transferSt = await getTransferStatus();
      if (transferSt) {
        setTransferRunning(transferSt.running);
        if (transferSt.ip) setTransferIp(transferSt.ip);
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    pollStatus();
    const interval = setInterval(pollStatus, 5000);
    return () => clearInterval(interval);
  }, [pollStatus]);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      // Auto-start transfer server if not running
      if (!transferRunning) {
        await startTransferServer(DEFAULT_TRANSFER_PORT, null);
        setTransferRunning(true);
      }
      const result = await startCast(resolution, bitrate, 60, record);
      if (!result.success) {
        setError(result.error || "Failed to start cast");
      }
      await pollStatus();
    } catch (e: any) {
      setError(e?.message || "Cast error");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopCast();
      await pollStatus();
    } catch (e: any) {
      setError(e?.message || "Failed to stop cast");
    } finally {
      setLoading(false);
    }
  };

  const isLive = status.status === "live";
  const isStarting = status.status === "starting";
  const statusColor = {
    offline: "#888",
    starting: "#ffa500",
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
            boxShadow: isLive ? "0 0 8px rgba(255, 68, 68, 0.6)" : undefined,
          }} />
          <span style={{ color: statusColor, fontWeight: "bold", textTransform: "uppercase" }}>
            {status.status}
          </span>
        </div>
      </PanelSectionRow>

      {(isLive || isStarting) ? (
        <>
          <PanelSectionRow>
            <div style={{
              padding: "16px",
              textAlign: "center",
              background: "rgba(255, 68, 68, 0.1)",
              borderRadius: "8px",
              border: "1px solid rgba(255, 68, 68, 0.2)",
            }}>
              <div style={{ color: "#ff4444", fontSize: "1.1em", fontWeight: "bold", marginBottom: "4px" }}>
                {isStarting ? "Starting..." : "LIVE"}
              </div>
              {transferIp && (
                <div style={{
                  fontSize: "0.95em",
                  color: "#7c3aed",
                  fontFamily: "monospace",
                  marginTop: "8px",
                  wordBreak: "break-all",
                }}>
                  http://{transferIp}:8420/cast
                </div>
              )}
              <div style={{ fontSize: "0.78em", color: "#888", marginTop: "4px" }}>
                Open this URL on any device to watch
              </div>
            </div>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleStop} disabled={loading}>
              {loading ? "Stopping..." : "Stop Casting"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : (
        <>
          <PanelSectionRow>
            <div style={{ padding: "8px", fontSize: "0.9em", color: "#ccc" }}>
              Cast your screen to any device on your network. No app needed — just a browser.
            </div>
          </PanelSectionRow>

          <PanelSectionRow>
            <Focusable
              onActivate={() => {
                const idx = CAST_RESOLUTION_OPTIONS.findIndex((o) => o.value === resolution);
                setResolution(CAST_RESOLUTION_OPTIONS[(idx + 1) % CAST_RESOLUTION_OPTIONS.length].value);
              }}
              onClick={() => {
                const idx = CAST_RESOLUTION_OPTIONS.findIndex((o) => o.value === resolution);
                setResolution(CAST_RESOLUTION_OPTIONS[(idx + 1) % CAST_RESOLUTION_OPTIONS.length].value);
              }}
              onOKButton={() => {
                const idx = CAST_RESOLUTION_OPTIONS.findIndex((o) => o.value === resolution);
                setResolution(CAST_RESOLUTION_OPTIONS[(idx + 1) % CAST_RESOLUTION_OPTIONS.length].value);
              }}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", cursor: "pointer", borderRadius: "4px" }}
            >
              <span style={{ color: "#aaa", fontSize: "0.9em" }}>Resolution</span>
              <span style={{ color: "#fff", fontSize: "0.9em", fontWeight: 600 }}>
                {CAST_RESOLUTION_OPTIONS.find((o) => o.value === resolution)?.label}
              </span>
            </Focusable>
          </PanelSectionRow>

          <PanelSectionRow>
            <Focusable
              onActivate={() => {
                const idx = BITRATE_OPTIONS.findIndex((o) => o.value === bitrate);
                setBitrate(BITRATE_OPTIONS[(idx + 1) % BITRATE_OPTIONS.length].value);
              }}
              onClick={() => {
                const idx = BITRATE_OPTIONS.findIndex((o) => o.value === bitrate);
                setBitrate(BITRATE_OPTIONS[(idx + 1) % BITRATE_OPTIONS.length].value);
              }}
              onOKButton={() => {
                const idx = BITRATE_OPTIONS.findIndex((o) => o.value === bitrate);
                setBitrate(BITRATE_OPTIONS[(idx + 1) % BITRATE_OPTIONS.length].value);
              }}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 16px", cursor: "pointer", borderRadius: "4px" }}
            >
              <span style={{ color: "#aaa", fontSize: "0.9em" }}>Quality</span>
              <span style={{ color: "#fff", fontSize: "0.9em", fontWeight: 600 }}>
                {BITRATE_OPTIONS.find((o) => o.value === bitrate)?.label}
              </span>
            </Focusable>
          </PanelSectionRow>

          <PanelSectionRow>
            <ToggleField
              label="Record while casting"
              checked={record}
              onChange={setRecord}
            />
          </PanelSectionRow>

          {error && (
            <PanelSectionRow>
              <div style={{ color: "#ff6b6b", padding: "8px", fontSize: "0.85em" }}>{error}</div>
            </PanelSectionRow>
          )}

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleStart}
              disabled={loading}
            >
              {loading ? "Starting..." : "Start Casting"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      )}
    </>
  );
};
