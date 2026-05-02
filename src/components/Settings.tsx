import { FC, useState, useEffect } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  TextField,
  ToggleField,
  SliderField,
  DropdownItem,
} from "@decky/ui";
import { getSettings, saveSettings } from "../utils/api";
import { PRIVACY_OPTIONS } from "../utils/constants";
import type { PluginSettings } from "../types";

interface SettingsProps {
  onSettingsChanged: (settings: PluginSettings) => void;
}

export const Settings: FC<SettingsProps> = ({ onSettingsChanged }) => {
  const [settings, setSettings] = useState<PluginSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        setSettings(s);
      } catch {
        // use null
      }
    })();
  }, []);

  if (!settings) {
    return (
      <PanelSectionRow>
        <div style={{ padding: "8px", color: "#888" }}>Loading settings...</div>
      </PanelSectionRow>
    );
  }

  const update = (partial: Partial<PluginSettings>) => {
    const next = { ...settings, ...partial };
    setSettings(next);
    setSaved(false);
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      await saveSettings(settings);
      onSettingsChanged(settings);
      setSaved(true);
    } catch {
      // show nothing — user will retry
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* YouTube defaults */}
      <PanelSectionRow>
        <div style={{ padding: "8px 0", fontWeight: "bold", color: "#7c3aed" }}>YouTube</div>
      </PanelSectionRow>

      <PanelSectionRow>
        <TextField
          label="Title Template"
          value={settings.youtube.title_template}
          onChange={(e) =>
            update({ youtube: { ...settings.youtube, title_template: e.target.value } })
          }
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <DropdownItem
          label="Default Privacy"
          rgOptions={PRIVACY_OPTIONS.map((o) => ({ label: o.label, data: o.value }))}
          selectedOption={settings.youtube.default_privacy}
          onChange={(opt) =>
            update({ youtube: { ...settings.youtube, default_privacy: opt.data } })
          }
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <TextField
          label="Default Tags (comma separated)"
          value={settings.youtube.default_tags.join(", ")}
          onChange={(e) =>
            update({
              youtube: {
                ...settings.youtube,
                default_tags: e.target.value.split(",").map((t: string) => t.trim()).filter(Boolean),
              },
            })
          }
        />
      </PanelSectionRow>

      {/* Transfer settings */}
      <PanelSectionRow>
        <div style={{ padding: "8px 0", fontWeight: "bold", color: "#7c3aed" }}>Transfer Server</div>
      </PanelSectionRow>

      <PanelSectionRow>
        <SliderField
          label={`Port: ${settings.transfer.port}`}
          value={settings.transfer.port}
          min={1024}
          max={65535}
          step={1}
          onChange={(val) =>
            update({ transfer: { ...settings.transfer, port: val } })
          }
          showValue={false}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <ToggleField
          label="Password Protection"
          checked={settings.transfer.password_enabled}
          onChange={(val) =>
            update({ transfer: { ...settings.transfer, password_enabled: val } })
          }
        />
      </PanelSectionRow>

      {settings.transfer.password_enabled && (
        <PanelSectionRow>
          <TextField
            label="Password"
            value={settings.transfer.password}
            onChange={(e) =>
              update({ transfer: { ...settings.transfer, password: e.target.value } })
            }
            bIsPassword
          />
        </PanelSectionRow>
      )}

      {/* Recording paths */}
      <PanelSectionRow>
        <div style={{ padding: "8px 0", fontWeight: "bold", color: "#7c3aed" }}>Recording Paths</div>
      </PanelSectionRow>

      <PanelSectionRow>
        <TextField
          label="Extra scan paths (one per line)"
          value={settings.recording_paths.join("\n")}
          onChange={(e) =>
            update({
              recording_paths: e.target.value.split("\n").filter(Boolean),
            })
          }
        />
      </PanelSectionRow>

      {/* Save */}
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : saved ? "Saved!" : "Save Settings"}
        </ButtonItem>
      </PanelSectionRow>

      {saved && (
        <PanelSectionRow>
          <div style={{ color: "#4ade80", padding: "4px 8px", fontSize: "0.85em", textAlign: "center" }}>
            Settings saved successfully
          </div>
        </PanelSectionRow>
      )}
    </>
  );
};
