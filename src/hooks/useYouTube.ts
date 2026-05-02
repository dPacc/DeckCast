import { useState, useEffect, useCallback, useRef } from "react";
import {
  youtubeGetAuthStatus,
  youtubeAuthStart,
  youtubeAuthCallback,
  youtubeDisconnect,
  youtubeUpload,
  getUploadProgress,
} from "../utils/api";
import type { YouTubeAuthStatus, UploadProgress } from "../types";

export function useYouTube() {
  const [authStatus, setAuthStatus] = useState<YouTubeAuthStatus>({
    authenticated: false,
    has_client_secrets: false,
    channel: null,
  });
  const [authUrl, setAuthUrl] = useState<string>("");
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    active: false,
    percent: 0,
    video_id: null,
    error: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshAuth = useCallback(async () => {
    try {
      const status = await youtubeGetAuthStatus();
      setAuthStatus(status);
    } catch {
      // Silently fail
    }
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  const startAuth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await youtubeAuthStart();
      if (result.success && result.auth_url) {
        setAuthUrl(result.auth_url);
      } else {
        setError(result.error || "Failed to start auth flow");
      }
    } catch (e: any) {
      setError(e?.message || "Auth error");
    } finally {
      setLoading(false);
    }
  }, []);

  const submitAuthCode = useCallback(async (code: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await youtubeAuthCallback(code);
      if (result.success) {
        setAuthUrl("");
        await refreshAuth();
      } else {
        setError(result.error || "Authentication failed");
      }
    } catch (e: any) {
      setError(e?.message || "Auth callback error");
    } finally {
      setLoading(false);
    }
  }, [refreshAuth]);

  const disconnect = useCallback(async () => {
    await youtubeDisconnect();
    setAuthStatus({ authenticated: false, has_client_secrets: false, channel: null });
    setAuthUrl("");
  }, []);

  const startUpload = useCallback(async (
    filepath: string,
    title: string,
    description: string,
    tags: string[],
    privacy: string,
    category: string,
  ) => {
    setError(null);
    try {
      const result = await youtubeUpload(filepath, title, description, tags, privacy, category);
      if (!result.success) {
        setError(result.error || "Upload failed to start");
        return;
      }

      pollRef.current = setInterval(async () => {
        const progress = await getUploadProgress();
        setUploadProgress(progress);
        if (!progress.active) {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }
      }, 2000);
    } catch (e: any) {
      setError(e?.message || "Upload error");
    }
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  return {
    authStatus,
    authUrl,
    uploadProgress,
    loading,
    error,
    startAuth,
    submitAuthCode,
    disconnect,
    refreshAuth,
    startUpload,
  };
}
