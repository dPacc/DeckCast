import { FC, useState } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  SliderField,
  ProgressBarItem,
} from "@decky/ui";
import { trimClip } from "../utils/api";
import { formatDuration, formatFileSize } from "../utils/fileUtils";
import type { Recording } from "../types";

interface ClipTrimmerProps {
  recording: Recording;
  onTrimmed: (outputPath: string) => void;
  onBack: () => void;
}

export const ClipTrimmer: FC<ClipTrimmerProps> = ({ recording, onTrimmed, onBack }) => {
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(Math.floor(recording.duration));
  const [trimming, setTrimming] = useState(false);
  const [result, setResult] = useState<{ success: boolean; output_path?: string; size?: number; error?: string } | null>(null);

  const maxTime = Math.floor(recording.duration);

  const handleTrim = async () => {
    setTrimming(true);
    setResult(null);
    try {
      const res = await trimClip(recording.path, startTime, endTime);
      setResult(res);
      if (res.success && res.output_path) {
        onTrimmed(res.output_path);
      }
    } catch (e: any) {
      setResult({ success: false, error: e?.message || "Trim failed" });
    } finally {
      setTrimming(false);
    }
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

      <PanelSectionRow>
        <SliderField
          label={`Start: ${formatDuration(startTime)}`}
          value={startTime}
          min={0}
          max={Math.max(0, endTime - 1)}
          step={1}
          onChange={setStartTime}
          showValue={false}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <SliderField
          label={`End: ${formatDuration(endTime)}`}
          value={endTime}
          min={startTime + 1}
          max={maxTime}
          step={1}
          onChange={setEndTime}
          showValue={false}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={{ padding: "8px", textAlign: "center", color: "#ccc" }}>
          Trimmed duration: {formatDuration(endTime - startTime)}
        </div>
      </PanelSectionRow>

      {trimming && (
        <PanelSectionRow>
          <ProgressBarItem indeterminate label="Trimming (fast copy, no re-encoding)..." />
        </PanelSectionRow>
      )}

      {result && !result.success && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", padding: "8px" }}>{result.error}</div>
        </PanelSectionRow>
      )}

      {result && result.success && (
        <PanelSectionRow>
          <div style={{ color: "#4ade80", padding: "8px", textAlign: "center" }}>
            Trimmed! Saved to: {result.output_path}
            {result.size && ` (${formatFileSize(result.size)})`}
          </div>
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleTrim}
          disabled={trimming || endTime <= startTime}
        >
          {trimming ? "Trimming..." : "Trim Clip"}
        </ButtonItem>
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={onBack}>Back</ButtonItem>
      </PanelSectionRow>
    </>
  );
};
