"use client";

import { useState, useEffect, useCallback } from "react";
import type { Forecast, HistoryRow, LiveForecast, LiveMatch } from "./types";
import { parseCsv } from "./utils";

const REMOTE_BASE =
  process.env.NEXT_PUBLIC_DATA_BASE ??
  "https://raw.githubusercontent.com/plvenice/worldcup-odds/data";

const FALLBACK_BASE = "/data";
const REFRESH_MS = 5 * 60 * 1000;
const LIVE_REFRESH_MS = 20 * 1000;
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
  liveTitleUpdates: Record<string, number>;
  liveForecast: LiveForecast | null;
  liveMatches: LiveMatch[];
}

export function useData(): DataState & { refresh: () => void } {
  const [state, setState] = useState<DataState>({
    forecast: null,
    history: [],
    loading: true,
    error: null,
    lastFetched: null,
    liveTitleUpdates: {},
    liveForecast: null,
    liveMatches: [],
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

  const pollLive = useCallback(async () => {
    if (!LIVE_URL) return;
    try {
      const [liveRes, liveFcRes] = await Promise.all([
        fetch(`${LIVE_URL}/live.json`, { cache: "no-store" }),
        fetch(`${LIVE_URL}/live_forecast.json`, { cache: "no-store" }),
      ]);

      const updates: Record<string, number> = {};
      let liveMatches: LiveMatch[] = [];
      if (liveRes.ok) {
        const j = await liveRes.json();
        if (j?.live) {
          Object.assign(updates, j.title_updates ?? {});
          liveMatches = j.matches ?? [];
        }
      }

      let liveForecast: LiveForecast | null = null;
      if (liveFcRes.ok) {
        const j: LiveForecast = await liveFcRes.json();
        if (j?.available) liveForecast = j;
      }

      setState((s) => ({ ...s, liveTitleUpdates: updates, liveForecast, liveMatches }));
    } catch {
      /* worker unreachable -- keep last known state */
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
