import { FC } from "react";
import {
  ButtonItem,
  Focusable,
  PanelSectionRow,
  ToggleField,
} from "@decky/ui";
import { CAST_RESOLUTION_OPTIONS, BITRATE_OPTIONS } from "../utils/constants";
import type { CastStatus } from "../types";

interface CastPanelProps {
  castStatus: CastStatus;
  transferIp: string;
  resolution: string;
  bitrate: string;
  record: boolean;
  loading: boolean;
  onResolutionChange: (v: string) => void;
  onBitrateChange: (v: string) => void;
  onRecordChange: (v: boolean) => void;
  onStop: () => void;
}

export const CastPanel: FC<CastPanelProps> = ({
  castStatus,
  transferIp,
  resolution,
  bitrate,
  record,
  loading,
  onResolutionChange,
  onBitrateChange,
  onRecordChange,
  onStop,
}) => {
  const isLive = castStatus.status === "live";
  const isStarting = castStatus.status === "starting";
  const isActive = isLive || isStarting;

  const statusColor = {
    offline: "#888",
    starting: "#ffa500",
    live: "#ff4444",
    error: "#ff6b6b",
  }[castStatus.status] || "#888";

  const cycleResolution = () => {
    const idx = CAST_RESOLUTION_OPTIONS.findIndex((o) => o.value === resolution);
    onResolutionChange(CAST_RESOLUTION_OPTIONS[(idx + 1) % CAST_RESOLUTION_OPTIONS.length].value);
  };

  const cycleBitrate = () => {
    const idx = BITRATE_OPTIONS.findIndex((o) => o.value === bitrate);
    onBitrateChange(BITRATE_OPTIONS[(idx + 1) % BITRATE_OPTIONS.length].value);
  };

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
            {castStatus.status}
          </span>
        </div>
      </PanelSectionRow>

      {isActive && (
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
            <ButtonItem layout="below" onClick={onStop} disabled={loading}>
              {loading ? "Stopping..." : "Stop Casting"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      )}

      <PanelSectionRow>
        <div style={{ padding: "8px", fontSize: "0.85em", color: "#888" }}>
          {isActive ? "Settings apply on next cast." : "Configure settings, then start from the main screen."}
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <Focusable
          onActivate={cycleResolution}
          onClick={cycleResolution}
          onOKButton={cycleResolution}
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
          onActivate={cycleBitrate}
          onClick={cycleBitrate}
          onOKButton={cycleBitrate}
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
          onChange={onRecordChange}
        />
      </PanelSectionRow>
    </>
  );
};
