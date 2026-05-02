import { definePlugin } from "@decky/api";
import { FC, useState, useCallback, useEffect } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  Focusable,
} from "@decky/ui";
import { FaVideo, FaWifi, FaYoutube, FaCut, FaBroadcastTower, FaCog, FaTv } from "react-icons/fa";
import { RecordingBrowser } from "./components/RecordingBrowser";
import { TransferPanel } from "./components/TransferPanel";
import { CastPanel } from "./components/CastPanel";
import { YouTubeAuth } from "./components/YouTubeAuth";
import { YouTubeUpload } from "./components/YouTubeUpload";
import { ClipTrimmer } from "./components/ClipTrimmer";
import { LiveStreamSetup } from "./components/LiveStreamSetup";
import { Settings } from "./components/Settings";
import { startCast, stopCast, getCastStatus, getTransferStatus, startTransferServer } from "./utils/api";
import { DEFAULT_TRANSFER_PORT } from "./utils/constants";
import type { Recording, PluginSettings, CastStatus } from "./types";

type Tab = "recordings" | "transfer" | "cast" | "youtube-auth" | "youtube-upload" | "trimmer" | "stream" | "settings";

const DeckCastPanel: FC = () => {
  const [tab, setTab] = useState<Tab>("recordings");
  const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);
  const [settings, setSettings] = useState<PluginSettings | null>(null);

  // Cast state — single source of truth
  const [castStatus, setCastStatus] = useState<CastStatus>({ status: "offline" });
  const [castLoading, setCastLoading] = useState(false);
  const [transferIp, setTransferIp] = useState("");

  // Cast settings
  const [castResolution, setCastResolution] = useState("1280x800");
  const [castBitrate, setCastBitrate] = useState("6000k");
  const [castRecord, setCastRecord] = useState(false);

  const goTo = useCallback((t: Tab) => setTab(t), []);

  useEffect(() => {
    const poll = async () => {
      try {
        const st = await getCastStatus();
        if (st && st.status) setCastStatus(st);
      } catch {}
      try {
        const tr = await getTransferStatus();
        if (tr?.ip) setTransferIp(tr.ip);
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  const castIsLive = castStatus.status === "live" || castStatus.status === "starting";

  const handleStartCast = useCallback(async () => {
    if (castIsLive) return;
    setCastLoading(true);
    try {
      const tr = await getTransferStatus();
      if (!tr?.running) {
        await startTransferServer(DEFAULT_TRANSFER_PORT, null);
      }
      setCastStatus({ status: "starting" });
      startCast(castResolution, castBitrate, 60, castRecord).catch(() => {});
    } catch {}
    setCastLoading(false);
  }, [castIsLive, castResolution, castBitrate, castRecord]);

  const handleStopCast = useCallback(async () => {
    setCastLoading(true);
    try {
      await stopCast();
      const st = await getCastStatus();
      if (st && st.status) setCastStatus(st);
    } catch {}
    setCastLoading(false);
  }, []);

  const handleToggleCast = useCallback(async () => {
    if (castIsLive) {
      await handleStopCast();
    } else {
      await handleStartCast();
    }
  }, [castIsLive, handleStartCast, handleStopCast]);

  const handleSelectRecording = useCallback((rec: Recording) => {
    setSelectedRecording(rec);
  }, []);

  const handleBack = useCallback(() => {
    setSelectedRecording(null);
    setTab("recordings");
  }, []);

  const handleTrimmed = useCallback((_outputPath: string) => {}, []);

  // Recording action menu
  if (selectedRecording && tab === "recordings") {
    return (
      <PanelSection title="DeckCast">
        <PanelSectionRow>
          <div style={{ padding: "8px", background: "#1a1a2e", borderRadius: "8px" }}>
            <div style={{ fontWeight: "bold", marginBottom: "4px" }}>{selectedRecording.filename}</div>
            <div style={{ fontSize: "0.85em", color: "#888" }}>{selectedRecording.game}</div>
          </div>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => goTo("youtube-upload")}>
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaYoutube /> Upload to YouTube
            </span>
          </ButtonItem>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => goTo("trimmer")}>
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FaCut /> Trim Clip
            </span>
          </ButtonItem>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleBack}>
            Back to Recordings
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <PanelSection title="DeckCast">
      {tab === "recordings" && (
        <>
          {/* Cast control — single start/stop button */}
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleToggleCast}
              disabled={castLoading}
              bottomSeparator="none"
            >
              <span style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: castIsLive ? "#ff4444" : "#fff",
              }}>
                {castIsLive && (
                  <span style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "#ff4444",
                    boxShadow: "0 0 6px rgba(255,68,68,0.6)",
                  }} />
                )}
                <FaTv />
                {castLoading
                  ? (castIsLive ? "Stopping..." : "Starting...")
                  : (castIsLive ? "Stop Casting" : "Start Casting")}
              </span>
            </ButtonItem>
          </PanelSectionRow>

          {/* Cast URL when live */}
          {castIsLive && transferIp && (
            <PanelSectionRow>
              <div style={{
                padding: "8px",
                textAlign: "center",
                background: "rgba(255, 68, 68, 0.1)",
                borderRadius: "8px",
                border: "1px solid rgba(255, 68, 68, 0.2)",
              }}>
                <div style={{ fontSize: "0.85em", color: "#7c3aed", fontFamily: "monospace", wordBreak: "break-all" }}>
                  http://{transferIp}:8420/cast
                </div>
                <div style={{ fontSize: "0.72em", color: "#888", marginTop: "2px" }}>
                  Open on any device to watch
                </div>
              </div>
            </PanelSectionRow>
          )}

          {/* Navigation */}
          <PanelSectionRow>
            <Focusable style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
              <NavButton icon={<FaWifi />} label="Share" onClick={() => goTo("transfer")} />
              <NavButton icon={<FaTv />} label="Cast" onClick={() => goTo("cast")} />
              <NavButton icon={<FaYoutube />} label="YouTube" onClick={() => goTo("youtube-auth")} />
              <NavButton icon={<FaBroadcastTower />} label="Stream" onClick={() => goTo("stream")} />
              <NavButton icon={<FaCog />} label="Settings" onClick={() => goTo("settings")} />
            </Focusable>
          </PanelSectionRow>

          <RecordingBrowser onSelect={handleSelectRecording} />
        </>
      )}

      {tab === "transfer" && (
        <>
          <BackButton onClick={() => goTo("recordings")} />
          <TransferPanel settings={settings} />
        </>
      )}

      {tab === "cast" && (
        <>
          <BackButton onClick={() => goTo("recordings")} />
          <CastPanel
            castStatus={castStatus}
            transferIp={transferIp}
            resolution={castResolution}
            bitrate={castBitrate}
            record={castRecord}
            loading={castLoading}
            onResolutionChange={setCastResolution}
            onBitrateChange={setCastBitrate}
            onRecordChange={setCastRecord}
            onStop={handleStopCast}
          />
        </>
      )}

      {tab === "youtube-auth" && (
        <>
          <BackButton onClick={() => goTo("recordings")} />
          <YouTubeAuth />
        </>
      )}

      {tab === "youtube-upload" && selectedRecording && (
        <YouTubeUpload recording={selectedRecording} settings={settings} onBack={handleBack} />
      )}

      {tab === "trimmer" && selectedRecording && (
        <ClipTrimmer recording={selectedRecording} onTrimmed={handleTrimmed} onBack={handleBack} />
      )}

      {tab === "stream" && (
        <>
          <BackButton onClick={() => goTo("recordings")} />
          <LiveStreamSetup />
        </>
      )}

      {tab === "settings" && (
        <>
          <BackButton onClick={() => goTo("recordings")} />
          <Settings onSettingsChanged={setSettings} />
        </>
      )}
    </PanelSection>
  );
};

const NavButton: FC<{ icon: React.ReactNode; label: string; onClick: () => void }> = ({
  icon,
  label,
  onClick,
}) => (
  <ButtonItem layout="below" onClick={onClick} bottomSeparator="none">
    <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.9em" }}>
      {icon} {label}
    </span>
  </ButtonItem>
);

const BackButton: FC<{ onClick: () => void }> = ({ onClick }) => (
  <PanelSectionRow>
    <Focusable
      onActivate={onClick}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "10px 16px",
        cursor: "pointer",
        fontSize: "0.9em",
        color: "#aaa",
        borderRadius: "4px",
        background: "transparent",
      }}
      onOKButton={onClick}
    >
      ← Back
    </Focusable>
  </PanelSectionRow>
);

export default definePlugin(() => ({
  name: "DeckCast",
  titleView: (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <FaVideo />
      <span>DeckCast</span>
    </div>
  ),
  content: <DeckCastPanel />,
  icon: <FaVideo />,
}));
