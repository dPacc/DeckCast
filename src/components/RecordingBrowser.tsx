import { FC } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  Focusable,
  ProgressBarItem,
  DropdownItem,
} from "@decky/ui";
import { useRecordings } from "../hooks/useRecordings";
import { formatFileSize, formatDuration, formatDate } from "../utils/fileUtils";
import type { Recording, SortMode } from "../types";

interface RecordingBrowserProps {
  onSelect: (recording: Recording) => void;
}

const SORT_OPTIONS = [
  { label: "Newest First", data: "date" as SortMode },
  { label: "Largest First", data: "size" as SortMode },
  { label: "By Game", data: "game" as SortMode },
];

export const RecordingBrowser: FC<RecordingBrowserProps> = ({ onSelect }) => {
  const { recordings, loading, error, refresh, sortMode, setSortMode } = useRecordings();

  if (loading) {
    return (
      <PanelSectionRow>
        <ProgressBarItem indeterminate label="Scanning recordings..." />
      </PanelSectionRow>
    );
  }

  if (error) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", padding: "8px" }}>{error}</div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={refresh}>
            Retry
          </ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

  return (
    <>
      <PanelSectionRow>
        <DropdownItem
          label="Sort by"
          rgOptions={SORT_OPTIONS}
          selectedOption={sortMode}
          onChange={(opt) => setSortMode(opt.data)}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={refresh}>
          Refresh
        </ButtonItem>
      </PanelSectionRow>

      {recordings.length === 0 ? (
        <PanelSectionRow>
          <div style={{ padding: "16px", textAlign: "center", color: "#888" }}>
            No recordings found. Record gameplay using Steam's built-in recording feature.
          </div>
        </PanelSectionRow>
      ) : (
        <Focusable>
          {recordings.map((rec) => (
            <PanelSectionRow key={rec.path}>
              <ButtonItem
                layout="below"
                onClick={() => onSelect(rec)}
                description={`${rec.game} · ${formatFileSize(rec.size)} · ${formatDuration(rec.duration)}`}
                bottomSeparator="none"
              >
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {rec.filename}
                  </span>
                  <span style={{ color: "#888", fontSize: "0.85em", flexShrink: 0, marginLeft: "8px" }}>
                    {formatDate(rec.modified)}
                  </span>
                </div>
              </ButtonItem>
            </PanelSectionRow>
          ))}
        </Focusable>
      )}

      <PanelSectionRow>
        <div style={{ padding: "8px", color: "#888", fontSize: "0.85em", textAlign: "center" }}>
          {recordings.length} recording{recordings.length !== 1 ? "s" : ""} found
        </div>
      </PanelSectionRow>
    </>
  );
};
