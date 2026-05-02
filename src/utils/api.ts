import { call } from "@decky/api";

export async function getRecordings() {
  return await call<[], Recording[]>("get_recordings");
}

export async function getRecordingInfo(filepath: string) {
  return await call<[string], Recording>("get_recording_info", filepath);
}

export async function getThumbnail(filepath: string, timestamp = 5.0) {
  return await call<[string, number], string>("get_thumbnail", filepath, timestamp);
}

export async function startTransferServer(port = 8420, password: string | null = null) {
  return await call<[number, string | null], TransferServerResult>(
    "start_transfer_server", port, password
  );
}

export async function stopTransferServer() {
  return await call<[], boolean>("stop_transfer_server");
}

export async function getTransferStatus() {
  return await call<[], TransferStatus>("get_transfer_status");
}

export async function youtubeAuthStart() {
  return await call<[], AuthStartResult>("youtube_auth_start");
}

export async function youtubeAuthCallback(code: string) {
  return await call<[string], AuthResult>("youtube_auth_callback", code);
}

export async function youtubeDisconnect() {
  return await call<[], boolean>("youtube_disconnect");
}

export async function youtubeGetAuthStatus() {
  return await call<[], YouTubeAuthStatus>("youtube_get_auth_status");
}

export async function youtubeUpload(
  filepath: string,
  title: string,
  description: string,
  tags: string[],
  privacy: string,
  category: string,
) {
  return await call<[string, string, string, string[], string, string], UploadStartResult>(
    "youtube_upload", filepath, title, description, tags, privacy, category
  );
}

export async function getUploadProgress() {
  return await call<[], UploadProgress>("get_upload_progress");
}

export async function trimClip(
  filepath: string,
  startTime: number,
  endTime: number,
  outputPath: string | null = null,
) {
  return await call<[string, number, number, string | null], TrimResult>(
    "trim_clip", filepath, startTime, endTime, outputPath
  );
}

export async function startStream(
  rtmpUrl: string,
  streamKey: string,
  resolution: string,
  bitrate: string,
  framerate: number,
) {
  return await call<[string, string, string, string, number], StreamResult>(
    "start_stream", rtmpUrl, streamKey, resolution, bitrate, framerate
  );
}

export async function stopStream() {
  return await call<[], StreamResult>("stop_stream");
}

export async function getStreamStatus() {
  return await call<[], StreamStatus>("get_stream_status");
}

export async function getSettings() {
  return await call<[], PluginSettings>("get_settings");
}

export async function saveSettings(settings: PluginSettings) {
  return await call<[PluginSettings], boolean>("save_settings", settings);
}

// Local types for API responses
import type {
  Recording,
  TransferStatus,
  YouTubeAuthStatus,
  UploadProgress,
  StreamStatus,
  PluginSettings,
} from "../types";

interface TransferServerResult {
  url: string;
  ip: string;
  port: number;
  qr_base64: string;
}

interface AuthStartResult {
  success: boolean;
  auth_url?: string;
  error?: string;
}

interface AuthResult {
  success: boolean;
  error?: string;
}

interface UploadStartResult {
  success: boolean;
  message?: string;
  error?: string;
}

interface TrimResult {
  success: boolean;
  output_path?: string;
  size?: number;
  error?: string;
}

interface StreamResult {
  success: boolean;
  status?: string;
  error?: string;
}
