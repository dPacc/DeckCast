import { describe, it, expect, vi, beforeEach } from "vitest";
import { call } from "@decky/api";
import {
  getRecordings,
  getThumbnail,
  startTransferServer,
  stopTransferServer,
  getTransferStatus,
  youtubeAuthStart,
  youtubeAuthCallback,
  youtubeDisconnect,
  youtubeGetAuthStatus,
  youtubeUpload,
  getUploadProgress,
  trimClip,
  startStream,
  stopStream,
  getStreamStatus,
  getSettings,
  saveSettings,
} from "./api";

const mockCall = vi.mocked(call);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getRecordings", () => {
  it("calls backend get_recordings", async () => {
    mockCall.mockResolvedValue([{ path: "/test.mp4" }]);
    const result = await getRecordings();
    expect(mockCall).toHaveBeenCalledWith("get_recordings");
    expect(result).toEqual([{ path: "/test.mp4" }]);
  });
});

describe("getThumbnail", () => {
  it("passes filepath and timestamp", async () => {
    mockCall.mockResolvedValue("base64data");
    await getThumbnail("/video.mp4", 3.0);
    expect(mockCall).toHaveBeenCalledWith("get_thumbnail", "/video.mp4", 3.0);
  });

  it("defaults timestamp to 5.0", async () => {
    mockCall.mockResolvedValue("");
    await getThumbnail("/video.mp4");
    expect(mockCall).toHaveBeenCalledWith("get_thumbnail", "/video.mp4", 5.0);
  });
});

describe("transfer server", () => {
  it("startTransferServer passes port and password", async () => {
    mockCall.mockResolvedValue({ url: "http://192.168.1.1:8420", ip: "192.168.1.1", port: 8420, qr_base64: "" });
    await startTransferServer(9000, "secret");
    expect(mockCall).toHaveBeenCalledWith("start_transfer_server", 9000, "secret");
  });

  it("stopTransferServer calls backend", async () => {
    mockCall.mockResolvedValue(true);
    const result = await stopTransferServer();
    expect(mockCall).toHaveBeenCalledWith("stop_transfer_server");
    expect(result).toBe(true);
  });

  it("getTransferStatus returns status object", async () => {
    const status = { running: true, ip: "192.168.1.1" };
    mockCall.mockResolvedValue(status);
    const result = await getTransferStatus();
    expect(result).toEqual(status);
  });
});

describe("youtube auth", () => {
  it("youtubeAuthStart calls backend", async () => {
    mockCall.mockResolvedValue({ success: true, auth_url: "https://..." });
    const result = await youtubeAuthStart();
    expect(mockCall).toHaveBeenCalledWith("youtube_auth_start");
    expect(result.success).toBe(true);
  });

  it("youtubeAuthCallback passes code", async () => {
    mockCall.mockResolvedValue({ success: true });
    await youtubeAuthCallback("mycode");
    expect(mockCall).toHaveBeenCalledWith("youtube_auth_callback", "mycode");
  });

  it("youtubeDisconnect calls backend", async () => {
    mockCall.mockResolvedValue(true);
    await youtubeDisconnect();
    expect(mockCall).toHaveBeenCalledWith("youtube_disconnect");
  });

  it("youtubeGetAuthStatus returns status", async () => {
    const status = { authenticated: true, has_client_secrets: true, channel: { name: "Test" } };
    mockCall.mockResolvedValue(status);
    const result = await youtubeGetAuthStatus();
    expect(result.authenticated).toBe(true);
  });
});

describe("youtube upload", () => {
  it("youtubeUpload passes all parameters", async () => {
    mockCall.mockResolvedValue({ success: true });
    await youtubeUpload("/video.mp4", "Title", "Desc", ["tag"], "unlisted", "20");
    expect(mockCall).toHaveBeenCalledWith(
      "youtube_upload", "/video.mp4", "Title", "Desc", ["tag"], "unlisted", "20"
    );
  });

  it("getUploadProgress returns progress", async () => {
    mockCall.mockResolvedValue({ active: true, percent: 50, video_id: null, error: null });
    const result = await getUploadProgress();
    expect(result.percent).toBe(50);
  });
});

describe("trimClip", () => {
  it("passes trim parameters", async () => {
    mockCall.mockResolvedValue({ success: true, output_path: "/trimmed.mp4" });
    await trimClip("/video.mp4", 10, 30, "/out.mp4");
    expect(mockCall).toHaveBeenCalledWith("trim_clip", "/video.mp4", 10, 30, "/out.mp4");
  });

  it("defaults outputPath to null", async () => {
    mockCall.mockResolvedValue({ success: true });
    await trimClip("/video.mp4", 0, 10);
    expect(mockCall).toHaveBeenCalledWith("trim_clip", "/video.mp4", 0, 10, null);
  });
});

describe("streaming", () => {
  it("startStream passes all config", async () => {
    mockCall.mockResolvedValue({ success: true });
    await startStream("rtmp://url", "key", "1280x720", "4000k", 30);
    expect(mockCall).toHaveBeenCalledWith("start_stream", "rtmp://url", "key", "1280x720", "4000k", 30);
  });

  it("stopStream calls backend", async () => {
    mockCall.mockResolvedValue({ success: true });
    await stopStream();
    expect(mockCall).toHaveBeenCalledWith("stop_stream");
  });

  it("getStreamStatus returns status", async () => {
    mockCall.mockResolvedValue({ status: "live", error: null, running: true });
    const result = await getStreamStatus();
    expect(result.status).toBe("live");
  });
});

describe("settings", () => {
  it("getSettings returns config", async () => {
    const config = { youtube: { default_privacy: "unlisted" } };
    mockCall.mockResolvedValue(config);
    const result = await getSettings();
    expect(result).toEqual(config);
  });

  it("saveSettings passes settings object", async () => {
    mockCall.mockResolvedValue(true);
    const settings = { youtube: { default_privacy: "private" } } as any;
    await saveSettings(settings);
    expect(mockCall).toHaveBeenCalledWith("save_settings", settings);
  });
});
