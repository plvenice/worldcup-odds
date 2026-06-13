"use client";

import { useState, useEffect, useCallback } from "react";
import type { Forecast, HistoryRow } from "./types";
import { parseCsv } from "./utils";

const REMOTE_BASE =
  process.env.NEXT_PUBLIC_DATA_BASE ??
  "https://raw.githubusercontent.com/plvenice/worldcup-odds/data";

const FALLBACK_BASE = "/data";
const REFRESH_MS = 5 * 60 * 1000; // 5 minutes
const LIVE_REFRESH_MS = 20 * 1000; // 20 seconds — same cadence as LiveMatches poll
const LIVE_URL = (process.env.NEXT_PUBLIC_LIVE_URL ?? "").replace(/\/$/, "");

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
  // Live title updates: team_id -> conditional p_title given current in-match state.
  // Non-empty only when at least one match is live and the worker has leverage data.
  liveTitleUpdates: Record<string, number>;
}

export function useData(): DataState & { refresh: () => void } {
  const [state, setState] = useState<DataState>({
    forecast: null,
    history: [],
    loading: true,
    error: null,
    lastFetched: null,
    liveTitleUpdates: {},
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
      setState((s) => ({
        ...s,
        forecast,
        history,
        loading: false,
        error: null,
        lastFetched: new Date(),
      }));
    } catch (e) {
      setState((s) => ({
        ...s,
        loading: false,
        error: e instanceof Error ? e.message : "Unknown error",
      }));
    }
  }, []);

  // Poll the live worker for title_updates independently of the forecast refresh.
  const pollLive = useCallback(async () => {
    if (!LIVE_URL) return;
    try {
      const res = await fetch(`${LIVE_URL}/live.json`, { cache: "no-store" });
      if (!res.ok) return;
      const j = await res.json();
      const updates: Record<string, number> = j?.live ? (j.title_updates ?? {}) : {};
      setState((s) => ({ ...s, liveTitleUpdates: updates }));
    } catch {
      /* worker unreachable — keep last known state */
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    if (!LIVE_URL) return;
    pollLive();
    const interval = setInterval(pollLive, LIVE_REFRESH_MS);
    return () => clearInterval(interval);
  }, [pollLive]);

  return { ...state, refresh: load };
}
