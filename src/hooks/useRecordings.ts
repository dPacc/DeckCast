import { useState, useEffect, useCallback } from "react";
import { getRecordings } from "../utils/api";
import type { Recording, SortMode } from "../types";

export function useRecordings() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>("date");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getRecordings();
      setRecordings(result || []);
    } catch (e: any) {
      setError(String(e?.message || e || "Unknown error"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const sorted = [...recordings].sort((a, b) => {
    switch (sortMode) {
      case "size":
        return b.size - a.size;
      case "game":
        return a.game.localeCompare(b.game);
      case "date":
      default:
        return b.modified - a.modified;
    }
  });

  return { recordings: sorted, loading, error, refresh, sortMode, setSortMode };
}
