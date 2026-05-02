import { callable } from "@decky/api";

const getRecordingsCall = callable<[], any>("get_recordings");
const getRecordingInfoCall = callable<[string], any>("get_recording_info");
const getThumbnailCall = callable<[string, number], string>("get_thumbnail");
const startTransferServerCall = callable<[number, string | null], TransferServerResult>("start_transfer_server");
const stopTransferServerCall = callable<[], boolean>("stop_transfer_server");
const getTransferStatusCall = callable<[], TransferStatus>("get_transfer_status");
const youtubeAuthStartCall = callable<[], AuthStartResult>("youtube_auth_start");
const youtubeAuthCallbackCall = callable<[string], AuthResult>("youtube_auth_callback");
const youtubeDisconnectCall = callable<[], boolean>("youtube_disconnect");
const youtubeGetAuthStatusCall = callable<[], YouTubeAuthStatus>("youtube_get_auth_status");
const youtubeUploadCall = callable<[string, string, string, string[], string, string], UploadStartResult>("youtube_upload");
const getUploadProgressCall = callable<[], UploadProgress>("get_upload_progress");
const trimClipCall = callable<[string, number, number, string | null], TrimResult>("trim_clip");
const startStreamCall = callable<[string, string, string, string, number], StreamResult>("start_stream");
const stopStreamCall = callable<[], StreamResult>("stop_stream");
const getStreamStatusCall = callable<[], StreamStatus>("get_stream_status");
const startCastCall = callable<[string, string, number, boolean], CastResult>("start_cast");
const stopCastCall = callable<[], CastResult>("stop_cast");
const getCastStatusCall = callable<[], CastStatus>("get_cast_status");
const getSettingsCall = callable<[], PluginSettings>("get_settings");
const saveSettingsCall = callable<[PluginSettings], boolean>("save_settings");

export async function getRecordings() {
  const res = await getRecordingsCall();
  if (res && typeof res === "object" && "result" in res) {
    return res.result as Recording[];
  }
  return res as Recording[];
}

export async function getRecordingInfo(filepath: string) {
  return await getRecordingInfoCall(filepath);
}

export async function getThumbnail(filepath: string, timestamp = 5.0) {
  return await getThumbnailCall(filepath, timestamp);
}

export async function startTransferServer(port = 8420, password: string | null = null) {
  return await startTransferServerCall(port, password);
}

export async function stopTransferServer() {
  return await stopTransferServerCall();
}

export async function getTransferStatus() {
  return await getTransferStatusCall();
}

export async function youtubeAuthStart() {
  return await youtubeAuthStartCall();
}

export async function youtubeAuthCallback(code: string) {
  return await youtubeAuthCallbackCall(code);
}

export async function youtubeDisconnect() {
  return await youtubeDisconnectCall();
}

export async function youtubeGetAuthStatus() {
  return await youtubeGetAuthStatusCall();
}

export async function youtubeUpload(
  filepath: string,
  title: string,
  description: string,
  tags: string[],
  privacy: string,
  category: string,
) {
  return await youtubeUploadCall(filepath, title, description, tags, privacy, category);
}

export async function getUploadProgress() {
  return await getUploadProgressCall();
}

export async function trimClip(
  filepath: string,
  startTime: number,
  endTime: number,
  outputPath: string | null = null,
) {
  return await trimClipCall(filepath, startTime, endTime, outputPath);
}

export async function startStream(
  rtmpUrl: string,
  streamKey: string,
  resolution: string,
  bitrate: string,
  framerate: number,
) {
  return await startStreamCall(rtmpUrl, streamKey, resolution, bitrate, framerate);
}

export async function stopStream() {
  return await stopStreamCall();
}

export async function getStreamStatus() {
  return await getStreamStatusCall();
}

export async function startCast(
  resolution: string,
  bitrate: string,
  framerate: number,
  record: boolean,
) {
  return await startCastCall(resolution, bitrate, framerate, record);
}

export async function stopCast() {
  return await stopCastCall();
}

export async function getCastStatus() {
  return await getCastStatusCall();
}

export async function getSettings() {
  return await getSettingsCall();
}

export async function saveSettings(settings: PluginSettings) {
  return await saveSettingsCall(settings);
}

// Local types for API responses
import type {
  Recording,
  TransferStatus,
  YouTubeAuthStatus,
  UploadProgress,
  StreamStatus,
  CastStatus,
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

interface CastResult {
  success: boolean;
  status?: string;
  error?: string;
}
