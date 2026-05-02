import { FC, useState } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  TextField,
  DropdownItem,
  ProgressBarItem,
} from "@decky/ui";
import { useYouTube } from "../hooks/useYouTube";
import { YOUTUBE_CATEGORIES, PRIVACY_OPTIONS } from "../utils/constants";
import { formatFileSize, formatDuration, generateTitle } from "../utils/fileUtils";
import type { Recording, PluginSettings } from "../types";

interface YouTubeUploadProps {
  recording: Recording;
  settings: PluginSettings | null;
  onBack: () => void;
}

export const YouTubeUpload: FC<YouTubeUploadProps> = ({ recording, settings, onBack }) => {
  const { authStatus, uploadProgress, error, startUpload } = useYouTube();
  const template = settings?.youtube?.title_template || "{game} - {date}";
  const defaultPrivacy = settings?.youtube?.default_privacy || "unlisted";
  const defaultCategory = settings?.youtube?.default_category || "20";
  const defaultTags = settings?.youtube?.default_tags || ["steamdeck", "gaming"];

  const [title, setTitle] = useState(generateTitle(template, recording.game));
  const [description, setDescription] = useState(
    `Recorded on Steam Deck\nGame: ${recording.game}\nDuration: ${formatDuration(recording.duration)}`
  );
  const [tags, setTags] = useState(defaultTags.join(", "));
  const [privacy, setPrivacy] = useState(defaultPrivacy);
  const [category, setCategory] = useState(defaultCategory);

  const categoryOptions = Object.entries(YOUTUBE_CATEGORIES).map(([id, name]) => ({
    label: name,
    data: id,
  }));

  if (!authStatus.authenticated) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "12px", color: "#ffa500" }}>
            Please connect your YouTube account first in the YouTube Auth tab.
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onBack}>Back</ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

  if (uploadProgress.active) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "8px", textAlign: "center" }}>
            <div style={{ fontSize: "1.1em", marginBottom: "8px" }}>Uploading to YouTube...</div>
            <div style={{ color: "#888" }}>{recording.filename}</div>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ProgressBarItem
            nProgress={uploadProgress.percent}
            label={`${uploadProgress.percent}%`}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ padding: "8px", fontSize: "0.85em", color: "#4ade80", textAlign: "center" }}>
            You can continue gaming — upload runs in the background
          </div>
        </PanelSectionRow>
      </>
    );
  }

  if (uploadProgress.video_id) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "16px", textAlign: "center" }}>
            <div style={{ fontSize: "1.2em", color: "#4ade80", marginBottom: "8px" }}>
              Upload Complete!
            </div>
            <div style={{ fontFamily: "monospace", color: "#7c3aed" }}>
              youtu.be/{uploadProgress.video_id}
            </div>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={onBack}>Done</ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

  const handleUpload = () => {
    const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);
    startUpload(recording.path, title, description, tagList, privacy, category);
  };

  return (
    <>
      <PanelSectionRow>
        <div style={{ padding: "8px", background: "#1a1a2e", borderRadius: "8px" }}>
          <div style={{ fontWeight: "bold" }}>{recording.filename}</div>
          <div style={{ fontSize: "0.85em", color: "#888" }}>
            {recording.game} · {formatFileSize(recording.size)} · {formatDuration(recording.duration)}
          </div>
        </div>
      </PanelSectionRow>

      {recording.duration > 900 && (
        <PanelSectionRow>
          <div style={{ padding: "8px", fontSize: "0.85em", color: "#ffa500" }}>
            This clip is over 15 minutes. Your YouTube account must be verified to upload videos this long.
          </div>
        </PanelSectionRow>
      )}

      {error && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", padding: "8px" }}>{error}</div>
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      </PanelSectionRow>

      <PanelSectionRow>
        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <TextField
          label="Tags (comma separated)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          label="Privacy"
          rgOptions={PRIVACY_OPTIONS.map((o) => ({ label: o.label, data: o.value }))}
          selectedOption={privacy}
          onChange={(opt) => setPrivacy(opt.data)}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          label="Category"
          rgOptions={categoryOptions}
          selectedOption={category}
          onChange={(opt) => setCategory(opt.data)}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={handleUpload} disabled={!title}>
          Upload to YouTube
        </ButtonItem>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onBack}>Back</ButtonItem>
      </PanelSectionRow>
    </>
  );
};
