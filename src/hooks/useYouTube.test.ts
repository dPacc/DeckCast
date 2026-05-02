import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useYouTube } from "./useYouTube";
import * as api from "../utils/api";

vi.mock("../utils/api");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useYouTube", () => {
  it("fetches auth status on mount", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: true,
      has_client_secrets: true,
      channel: { name: "TestChannel", thumbnail: "" },
    });

    const { result } = renderHook(() => useYouTube());

    await waitFor(() => {
      expect(result.current.authStatus.authenticated).toBe(true);
    });

    expect(result.current.authStatus.channel?.name).toBe("TestChannel");
  });

  it("starts auth flow and returns URL", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: false,
      has_client_secrets: true,
      channel: null,
    });
    vi.mocked(api.youtubeAuthStart).mockResolvedValue({
      success: true,
      auth_url: "https://accounts.google.com/o/oauth2/auth?...",
    });

    const { result } = renderHook(() => useYouTube());

    await act(async () => {
      await result.current.startAuth();
    });

    expect(result.current.authUrl).toContain("accounts.google.com");
    expect(result.current.error).toBeNull();
  });

  it("handles auth start failure", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: false,
      has_client_secrets: false,
      channel: null,
    });
    vi.mocked(api.youtubeAuthStart).mockResolvedValue({
      success: false,
      error: "No client secrets",
    });

    const { result } = renderHook(() => useYouTube());

    await act(async () => {
      await result.current.startAuth();
    });

    expect(result.current.error).toBe("No client secrets");
    expect(result.current.authUrl).toBe("");
  });

  it("submits auth code successfully", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: false,
      has_client_secrets: true,
      channel: null,
    });
    vi.mocked(api.youtubeAuthCallback).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useYouTube());

    // Wait for initial auth check
    await waitFor(() => {
      expect(api.youtubeGetAuthStatus).toHaveBeenCalled();
    });

    // Now mock a successful re-fetch after auth
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: true,
      has_client_secrets: true,
      channel: { name: "MyChannel", thumbnail: "" },
    });

    await act(async () => {
      await result.current.submitAuthCode("test-code");
    });

    expect(api.youtubeAuthCallback).toHaveBeenCalledWith("test-code");
  });

  it("disconnects account", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: true,
      has_client_secrets: true,
      channel: { name: "Test", thumbnail: "" },
    });
    vi.mocked(api.youtubeDisconnect).mockResolvedValue(true);

    const { result } = renderHook(() => useYouTube());

    await waitFor(() => {
      expect(result.current.authStatus.authenticated).toBe(true);
    });

    await act(async () => {
      await result.current.disconnect();
    });

    expect(result.current.authStatus.authenticated).toBe(false);
    expect(result.current.authStatus.channel).toBeNull();
  });

  it("starts upload", async () => {
    vi.mocked(api.youtubeGetAuthStatus).mockResolvedValue({
      authenticated: true,
      has_client_secrets: true,
      channel: { name: "Test", thumbnail: "" },
    });
    vi.mocked(api.youtubeUpload).mockResolvedValue({ success: true });
    vi.mocked(api.getUploadProgress).mockResolvedValue({
      active: false,
      percent: 100,
      video_id: "abc123",
      error: null,
    });

    const { result } = renderHook(() => useYouTube());

    await waitFor(() => {
      expect(result.current.authStatus.authenticated).toBe(true);
    });

    await act(async () => {
      await result.current.startUpload("/video.mp4", "Title", "Desc", ["tag"], "unlisted", "20");
    });

    expect(api.youtubeUpload).toHaveBeenCalledWith(
      "/video.mp4", "Title", "Desc", ["tag"], "unlisted", "20"
    );
  });
});
