import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTransfer } from "./useTransfer";
import * as api from "../utils/api";

vi.mock("../utils/api");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useTransfer", () => {
  it("starts with server not running", () => {
    const { result } = renderHook(() => useTransfer());
    expect(result.current.status.running).toBe(false);
    expect(result.current.qrData).toBe("");
  });

  it("starts transfer server", async () => {
    vi.mocked(api.startTransferServer).mockResolvedValue({
      url: "http://192.168.1.100:8420",
      ip: "192.168.1.100",
      port: 8420,
      qr_base64: "base64qr",
    });

    const { result } = renderHook(() => useTransfer());

    await act(async () => {
      await result.current.start(8420, null);
    });

    expect(result.current.status.running).toBe(true);
    expect(result.current.status.url).toBe("http://192.168.1.100:8420");
    expect(result.current.qrData).toBe("base64qr");
    expect(result.current.error).toBeNull();
  });

  it("stops transfer server", async () => {
    vi.mocked(api.startTransferServer).mockResolvedValue({
      url: "http://192.168.1.100:8420",
      ip: "192.168.1.100",
      port: 8420,
      qr_base64: "",
    });
    vi.mocked(api.stopTransferServer).mockResolvedValue(true);

    const { result } = renderHook(() => useTransfer());

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.status.running).toBe(true);

    await act(async () => {
      await result.current.stop();
    });
    expect(result.current.status.running).toBe(false);
    expect(result.current.qrData).toBe("");
  });

  it("handles start error", async () => {
    vi.mocked(api.startTransferServer).mockRejectedValue(new Error("Port in use"));

    const { result } = renderHook(() => useTransfer());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.error).toBe("Port in use");
    expect(result.current.status.running).toBe(false);
  });

  it("refresh updates status", async () => {
    vi.mocked(api.getTransferStatus).mockResolvedValue({
      running: true,
      ip: "10.0.0.1",
    });

    const { result } = renderHook(() => useTransfer());

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.status.running).toBe(true);
    expect(result.current.status.ip).toBe("10.0.0.1");
  });
});
