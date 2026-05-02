import { FC, useState } from "react";
import {
  ButtonItem,
  PanelSectionRow,
  TextField,
} from "@decky/ui";
import { useYouTube } from "../hooks/useYouTube";

export const YouTubeAuth: FC = () => {
  const { authStatus, authUrl, loading, error, startAuth, submitAuthCode, disconnect } = useYouTube();
  const [authCode, setAuthCode] = useState("");

  if (authStatus.authenticated && authStatus.channel) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "12px", background: "#1a1a2e", borderRadius: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {authStatus.channel.thumbnail && (
                <img
                  src={authStatus.channel.thumbnail}
                  alt=""
                  style={{ width: "40px", height: "40px", borderRadius: "50%" }}
                />
              )}
              <div>
                <div style={{ fontWeight: "bold" }}>{authStatus.channel.name}</div>
                <div style={{ fontSize: "0.85em", color: "#4ade80" }}>Connected</div>
              </div>
            </div>
          </div>
        </PanelSectionRow>

        <PanelSectionRow>
          <ButtonItem layout="below" onClick={disconnect}>
            Disconnect YouTube Account
          </ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

  if (!authStatus.has_client_secrets) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "12px", color: "#ffa500", fontSize: "0.9em" }}>
            YouTube API credentials not configured. To set up:
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ padding: "0 12px 12px", fontSize: "0.85em", color: "#ccc" }}>
            1. Go to console.cloud.google.com{"\n"}
            2. Create a project and enable YouTube Data API v3{"\n"}
            3. Create OAuth 2.0 credentials (Desktop app){"\n"}
            4. Download the JSON and save as:{"\n"}
            ~/homebrew/data/DeckCast/client_secrets.json
          </div>
        </PanelSectionRow>
      </>
    );
  }

  if (authUrl) {
    return (
      <>
        <PanelSectionRow>
          <div style={{ padding: "8px", fontSize: "0.9em", color: "#ccc" }}>
            Open this URL on your phone or PC and sign in with your Google account:
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{
            padding: "12px",
            background: "#1a1a2e",
            borderRadius: "8px",
            fontSize: "0.8em",
            fontFamily: "monospace",
            wordBreak: "break-all",
            color: "#7c3aed",
          }}>
            {authUrl}
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ padding: "8px", fontSize: "0.9em", color: "#ccc" }}>
            Paste the authorization code below:
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <TextField
            label="Authorization Code"
            value={authCode}
            onChange={(e) => setAuthCode(e.target.value)}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => submitAuthCode(authCode)}
            disabled={!authCode || loading}
          >
            {loading ? "Authenticating..." : "Submit Code"}
          </ButtonItem>
        </PanelSectionRow>
      </>
    );
  }

  return (
    <>
      <PanelSectionRow>
        <div style={{ padding: "8px", fontSize: "0.9em", color: "#ccc" }}>
          Connect your YouTube account to upload recordings directly from your Steam Deck.
        </div>
      </PanelSectionRow>

      {error && (
        <PanelSectionRow>
          <div style={{ color: "#ff6b6b", padding: "8px" }}>{error}</div>
        </PanelSectionRow>
      )}

      <PanelSectionRow>
        <ButtonItem layout="below" onClick={startAuth} disabled={loading}>
          {loading ? "Starting..." : "Connect YouTube Account"}
        </ButtonItem>
      </PanelSectionRow>
    </>
  );
};
