export interface Recording {
  path: string;
  filename: string;
  size: number;
  modified: number;
  duration: number;
  width: number;
  height: number;
  codec: string;
  game: string;
}

export interface TransferStatus {
  running: boolean;
  url?: string;
  ip: string;
  port?: number;
  qr_base64?: string;
}

export interface YouTubeAuthStatus {
  authenticated: boolean;
  has_client_secrets: boolean;
  channel: {
    name: string;
    thumbnail: string;
  } | null;
}

export interface UploadProgress {
  active: boolean;
  percent: number;
  video_id: string | null;
  error: string | null;
}

export interface UploadFormData {
  filepath: string;
  title: string;
  description: string;
  tags: string[];
  privacy: "public" | "unlisted" | "private";
  category: string;
}

export interface StreamStatus {
  status: "offline" | "connecting" | "live" | "error";
  error: string | null;
  running: boolean;
}

export interface StreamConfig {
  rtmp_url: string;
  stream_key: string;
  resolution: string;
  bitrate: string;
  framerate: number;
}

export interface PluginSettings {
  youtube: {
    default_privacy: string;
    title_template: string;
    default_category: string;
    default_tags: string[];
  };
  transfer: {
    port: number;
    password_enabled: boolean;
    password: string;
  };
  recording_paths: string[];
  sd_card_paths: string[];
  stream: {
    resolution: string;
    bitrate: string;
    framerate: number;
    saved_stream_keys: string[];
  };
}

export type SortMode = "date" | "size" | "game";
