import { FC, useEffect } from "react";
import {
  ButtonItem,
  PanelSectionRow,
} from "@decky/ui";
import { useTransfer } from "../hooks/useTransfer";
import { DEFAULT_TRANSFER_PORT } from "../utils/constants";
import type { PluginSettings } from "../types";

interface TransferPanelProps {
  settings: PluginSettings | null;
}

export const TransferPanel: FC<TransferPanelProps> = ({ settings }) => {
  const { status, qrData, loading, error, start, stop, refresh } = useTransfer();

  useEffect(() => {
    refresh();
  }, [refresh]);

  const port = settings?.transfer?.port || DEFAULT_TRANSFER_PORT;
  const password = settings?.transfer?.password_enabled ? settings.transfer.password : null;

  const handleToggle = async () => {
    if (status.running) {
      await stop();
    } else {
      await start(port, password);
    }
  };

  return (
    <>
      <PanelSectionRow>
        <div style={{ padding: "8px", fontSize: "0.9em", color: "#ccc" }}>
          Start a local server so any device on your Wi-Fi can download your recordings.
          No size limits, no internet required.
        </div>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleToggle}
          disabled={loading}
        >
          {loading ? "..." : status.running ? "Stop Server" : "Start Transfer Server"}
        </ButtonItem>
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", padding: "8px" }}>{error}</div>
        </PanelSectionRow>
      )}

      {status.running && (
        <>
          <PanelSectionRow>
            <div style={{ padding: "12px", background: "#1a1a2e", borderRadius: "8px", textAlign: "center" }}>
              <div style={{ fontSize: "0.85em", color: "#888", marginBottom: "4px" }}>
                Open this URL on your phone or PC:
              </div>
              <div style={{ fontSize: "1.1em", color: "#7c3aed", fontFamily: "monospace", wordBreak: "break-all" }}>
                {status.url}
              </div>
            </div>
          </PanelSectionRow>

          {qrData && (
            <PanelSectionRow>
              <div style={{ textAlign: "center", padding: "8px" }}>
                <img
                  src={`data:image/png;base64,${qrData}`}
                  alt="QR Code"
                  style={{ width: "180px", height: "180px", imageRendering: "pixelated" }}
                />
                <div style={{ fontSize: "0.8em", color: "#888", marginTop: "4px" }}>
                  Scan with your phone camera
                </div>
              </div>
            </PanelSectionRow>
          )}

          {password && (
            <PanelSectionRow>
              <div style={{ padding: "8px", fontSize: "0.85em", color: "#ffa500" }}>
                Password protection is enabled
              </div>
            </PanelSectionRow>
          )}
        </>
      )}
    </>
  );
};
