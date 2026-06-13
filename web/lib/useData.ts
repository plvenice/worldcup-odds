"use client";

import { useState, useEffect, useCallback } from "react";
import type { Forecast, HistoryRow } from "./types";
import { parseCsv } from "./utils";

const REMOTE_BASE =
  process.env.NEXT_PUBLIC_DATA_BASE ??
  "https://raw.githubusercontent.com/plvenice/worldcup-odds/data";

const FALLBACK_BASE = "/data";
const REFRESH_MS = 5 * 60 * 1000; // 5 minutes

async function fetchWithFallback(path: string): Promise<string> {
  const remoteUrl = `${REMOTE_BASE}/${path}?t=${Date.now()}`;
  const fallbackUrl = `${FALLBACK_BASE}/${path}`;

  try {
    const res = await fetch(remoteUrl, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } catch {
    const res = await fetch(fallbackUrl);
    if (!res.ok) throw new Error(`Fallback fetch failed: HTTP ${res.status}`);
    return await res.text();
  }
}

export interface DataState {
  forecast: Forecast | null;
  history: HistoryRow[];
  loading: boolean;
  error: string | null;
  lastFetched: Date | null;
}

export function useData(): DataState & { refresh: () => void } {
  const [state, setState] = useState<DataState>({
    forecast: null,
    history: [],
    loading: true,
    error: null,
    lastFetched: null,
  });

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const [forecastText, historyText] = await Promise.all([
        fetchWithFallback("forecast.json"),
        fetchWithFallback("history.csv"),
      ]);
      const forecast: Forecast = JSON.parse(forecastText);
      const history = parseCsv(historyText);
      setState({
        forecast,
        history,
        loading: false,
        error: null,
        lastFetched: new Date(),
      });
    } catch (e) {
      setState((s) => ({
        ...s,
        loading: false,
        error: e instanceof Error ? e.message : "Unknown error",
      }));
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  return { ...state, refresh: load };
}
