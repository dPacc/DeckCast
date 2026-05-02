import { definePlugin } from "@decky/api";
import { FC, useState, useCallback } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  Focusable,
} from "@decky/ui";
import { FaVideo, FaWifi, FaYoutube, FaCut, FaBroadcastTower, FaCog } from "react-icons/fa";
import { RecordingBrowser } from "./components/RecordingBrowser";
import { TransferPanel } from "./components/TransferPanel";
import { YouTubeAuth } from "./components/YouTubeAuth";
import { YouTubeUpload } from "./components/YouTubeUpload";
import { ClipTrimmer } from "./components/ClipTrimmer";
import { LiveStreamSetup } from "./components/LiveStreamSetup";
import { Settings } from "./components/Settings";
import type { Recording, PluginSettings } from "./types";

type Tab = "recordings" | "transfer" | "youtube-auth" | "youtube-upload" | "trimmer" | "stream" | "settings";

const DeckCastPanel: FC = () => {
  const [tab, setTab] = useState<Tab>("recordings");
  const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);
  const [settings, setSettings] = useState<PluginSettings | null>(null);

  const goTo = useCallback((t: Tab) => setTab(t), []);

  const handleSelectRecording = useCallback((rec: Recording) => {
    setSelectedRecording(rec);
  }, []);

  const handleBack = useCallback(() => {
    setSelectedRecording(null);
    setTab("recordings");
  }, []);

  const handleTrimmed = useCallback((_outputPath: string) => {
    // Could auto-navigate to upload, for now just stay on trimmer
  }, []);

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
      {/* Navigation tabs */}
      {tab === "recordings" && (
        <>
          <PanelSectionRow>
            <Focusable style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
              <NavButton icon={<FaWifi />} label="Transfer" onClick={() => goTo("transfer")} />
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
    <ButtonItem layout="below" onClick={onClick} bottomSeparator="none">
      ← Back
    </ButtonItem>
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
