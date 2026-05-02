import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useRecordings } from "./useRecordings";
import * as api from "../utils/api";
import type { Recording } from "../types";

vi.mock("../utils/api");

const mockRecordings: Recording[] = [
  {
    path: "/rec/game1.mp4",
    filename: "game1.mp4",
    size: 500_000_000,
    modified: 1700000000,
    duration: 120,
    width: 1920,
    height: 1080,
    codec: "h264",
    game: "Portal 2",
  },
  {
    path: "/rec/game2.mp4",
    filename: "game2.mp4",
    size: 1_200_000_000,
    modified: 1700001000,
    duration: 300,
    width: 1280,
    height: 720,
    codec: "h264",
    game: "Hades",
  },
  {
    path: "/rec/game3.mp4",
    filename: "game3.mp4",
    size: 200_000_000,
    modified: 1700002000,
    duration: 60,
    width: 1920,
    height: 1080,
    codec: "h264",
    game: "Portal 2",
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useRecordings", () => {
  it("loads recordings on mount", async () => {
    vi.mocked(api.getRecordings).mockResolvedValue(mockRecordings);
    const { result } = renderHook(() => useRecordings());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.recordings).toHaveLength(3);
    expect(result.current.error).toBeNull();
  });

  it("handles errors gracefully", async () => {
    vi.mocked(api.getRecordings).mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useRecordings());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Network error");
    expect(result.current.recordings).toHaveLength(0);
  });

  it("sorts by date descending by default", async () => {
    vi.mocked(api.getRecordings).mockResolvedValue(mockRecordings);
    const { result } = renderHook(() => useRecordings());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.sortMode).toBe("date");
    expect(result.current.recordings[0].modified).toBeGreaterThanOrEqual(
      result.current.recordings[1].modified
    );
  });

  it("sorts by size when mode changes", async () => {
    vi.mocked(api.getRecordings).mockResolvedValue(mockRecordings);
    const { result } = renderHook(() => useRecordings());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setSortMode("size");
    });

    expect(result.current.sortMode).toBe("size");
    expect(result.current.recordings[0].size).toBeGreaterThanOrEqual(
      result.current.recordings[1].size
    );
  });

  it("sorts by game name alphabetically", async () => {
    vi.mocked(api.getRecordings).mockResolvedValue(mockRecordings);
    const { result } = renderHook(() => useRecordings());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setSortMode("game");
    });

    expect(result.current.recordings[0].game).toBe("Hades");
    expect(result.current.recordings[1].game).toBe("Portal 2");
  });

  it("refresh reloads data", async () => {
    vi.mocked(api.getRecordings).mockResolvedValue(mockRecordings);
    const { result } = renderHook(() => useRecordings());

    await waitFor(() => expect(result.current.loading).toBe(false));

    vi.mocked(api.getRecordings).mockResolvedValue([mockRecordings[0]]);

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.recordings).toHaveLength(1);
  });
});
