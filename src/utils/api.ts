import { callable } from "@decky/api";

function unwrap<T>(res: any): T {
  if (res && typeof res === "object" && "result" in res) {
    return res.result as T;
  }
  return res as T;
}

const getRecordingsCall = callable<[], any>("get_recordings");
const getRecordingInfoCall = callable<[string], any>("get_recording_info");
const getThumbnailCall = callable<[string, number], any>("get_thumbnail");
const startTransferServerCall = callable<[number, string | null], any>("start_transfer_server");
const stopTransferServerCall = callable<[], any>("stop_transfer_server");
const getTransferStatusCall = callable<[], any>("get_transfer_status");
const youtubeAuthStartCall = callable<[], any>("youtube_auth_start");
const youtubeAuthCallbackCall = callable<[string], any>("youtube_auth_callback");
const youtubeDisconnectCall = callable<[], any>("youtube_disconnect");
const youtubeGetAuthStatusCall = callable<[], any>("youtube_get_auth_status");
const youtubeUploadCall = callable<[string, string, string, string[], string, string], any>("youtube_upload");
const getUploadProgressCall = callable<[], any>("get_upload_progress");
const trimClipCall = callable<[string, number, number, string | null], any>("trim_clip");
const startStreamCall = callable<[string, string, string, string, number], any>("start_stream");
const stopStreamCall = callable<[], any>("stop_stream");
const getStreamStatusCall = callable<[], any>("get_stream_status");
const startCastCall = callable<[string, string, number, boolean], any>("start_cast");
const stopCastCall = callable<[], any>("stop_cast");
const getCastStatusCall = callable<[], any>("get_cast_status");
const getSettingsCall = callable<[], any>("get_settings");
const saveSettingsCall = callable<[PluginSettings], any>("save_settings");

export async function getRecordings(): Promise<Recording[]> {
  return unwrap<Recording[]>(await getRecordingsCall());
}

export async function getRecordingInfo(filepath: string) {
  return unwrap<any>(await getRecordingInfoCall(filepath));
}

export async function getThumbnail(filepath: string, timestamp = 5.0) {
  return unwrap<string>(await getThumbnailCall(filepath, timestamp));
}

export async function startTransferServer(port = 8420, password: string | null = null) {
  return unwrap<TransferServerResult>(await startTransferServerCall(port, password));
}

export async function stopTransferServer() {
  return unwrap<boolean>(await stopTransferServerCall());
}

export async function getTransferStatus() {
  return unwrap<TransferStatus>(await getTransferStatusCall());
}

export async function youtubeAuthStart() {
  return unwrap<AuthStartResult>(await youtubeAuthStartCall());
}

export async function youtubeAuthCallback(code: string) {
  return unwrap<AuthResult>(await youtubeAuthCallbackCall(code));
}

export async function youtubeDisconnect() {
  return unwrap<boolean>(await youtubeDisconnectCall());
}

export async function youtubeGetAuthStatus() {
  return unwrap<YouTubeAuthStatus>(await youtubeGetAuthStatusCall());
}

export async function youtubeUpload(
  filepath: string,
  title: string,
  description: string,
  tags: string[],
  privacy: string,
  category: string,
) {
  return unwrap<UploadStartResult>(await youtubeUploadCall(filepath, title, description, tags, privacy, category));
}

export async function getUploadProgress() {
  return unwrap<UploadProgress>(await getUploadProgressCall());
}

export async function trimClip(
  filepath: string,
  startTime: number,
  endTime: number,
  outputPath: string | null = null,
) {
  return unwrap<TrimResult>(await trimClipCall(filepath, startTime, endTime, outputPath));
}

export async function startStream(
  rtmpUrl: string,
  streamKey: string,
  resolution: string,
  bitrate: string,
  framerate: number,
) {
  return unwrap<StreamResult>(await startStreamCall(rtmpUrl, streamKey, resolution, bitrate, framerate));
}

export async function stopStream() {
  return unwrap<StreamResult>(await stopStreamCall());
}

export async function getStreamStatus() {
  return unwrap<StreamStatus>(await getStreamStatusCall());
}

export async function startCast(
  resolution: string,
  bitrate: string,
  framerate: number,
  record: boolean,
) {
  return unwrap<CastResult>(await startCastCall(resolution, bitrate, framerate, record));
}

export async function stopCast() {
  return unwrap<CastResult>(await stopCastCall());
}

export async function getCastStatus() {
  return unwrap<CastStatus>(await getCastStatusCall());
}

export async function getSettings() {
  return unwrap<PluginSettings>(await getSettingsCall());
}

export async function saveSettings(settings: PluginSettings) {
  return unwrap<boolean>(await saveSettingsCall(settings));
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
