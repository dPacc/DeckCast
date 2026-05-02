import { useState, useCallback } from "react";
import { startTransferServer, stopTransferServer, getTransferStatus } from "../utils/api";
import type { TransferStatus } from "../types";

export function useTransfer() {
  const [status, setStatus] = useState<TransferStatus>({
    running: false,
    ip: "",
  });
  const [qrData, setQrData] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async (port = 8420, password: string | null = null) => {
    setLoading(true);
    setError(null);
    try {
      const result = await startTransferServer(port, password);
      setStatus({
        running: true,
        url: result.url,
        ip: result.ip,
        port: result.port,
      });
      setQrData(result.qr_base64 || "");
    } catch (e: any) {
      setError(e?.message || "Failed to start transfer server");
    } finally {
      setLoading(false);
    }
  }, []);

  const stop = useCallback(async () => {
    setLoading(true);
    try {
      await stopTransferServer();
      setStatus({ running: false, ip: "" });
      setQrData("");
    } catch (e: any) {
      setError(e?.message || "Failed to stop transfer server");
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const result = await getTransferStatus();
      setStatus(result);
    } catch {
      // Silently fail on refresh
    }
  }, []);

  return { status, qrData, loading, error, start, stop, refresh };
}
