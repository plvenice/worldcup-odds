import type { HistoryRow } from "./types";

/** Format a probability (0–1) as "17.9%" */
export function fmtPct(p: number): string {
  return (p * 100).toFixed(1) + "%";
}

/** Format a probability as a plain number string "17.9" */
export function fmtPctNum(p: number): string {
  return (p * 100).toFixed(1);
}

/** Elo as integer */
export function fmtElo(e: number): string {
  return Math.round(e).toString();
}

/** "2026-06-13T01:48:26.556803+00:00" → human-readable "Jun 13, 01:48 UTC" */
export function fmtTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

/** Minutes since a timestamp */
export function minutesAgo(iso: string): number {
  return Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
}

/** Parse history.csv into HistoryRow[] */
export function parseCsv(raw: string): HistoryRow[] {
  const lines = raw.trim().split("\n");
  if (lines.length < 2) return [];
  // skip header
  const rows: HistoryRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    if (parts.length < 8) continue;
    rows.push({
      ts: parts[0].trim(),
      team: parts[1].trim(),
      p_title: parseFloat(parts[2]),
      p_final: parseFloat(parts[3]),
      p_sf: parseFloat(parts[4]),
      p_qf: parseFloat(parts[5]),
      p_advance: parseFloat(parts[6]),
      elo: parseFloat(parts[7]),
    });
  }
  return rows;
}

/** Get unique sorted timestamps from history rows */
export function getTimestamps(rows: HistoryRow[]): string[] {
  const set = new Set(rows.map((r) => r.ts));
  return Array.from(set).sort();
}

/** Short date format for x-axis labels */
export function fmtShortDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Format a match date string */
export function fmtMatchDate(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", weekday: "short" });
}

/** Chart colors for top teams (deterministic by team id) */
const TEAM_COLORS: Record<string, string> = {
  ESP: "#F5C342",
  ARG: "#4D9FFF",
  FRA: "#00C26E",
  ENG: "#FF5C5C",
  BRA: "#F59E0B",
  POR: "#8B5CF6",
  COL: "#EC4899",
  ECU: "#14B8A6",
  NED: "#FB923C",
  GER: "#94A3B8",
  MEX: "#22D3EE",
  TUR: "#A78BFA",
};

export function teamColor(id: string, index: number): string {
  if (TEAM_COLORS[id]) return TEAM_COLORS[id];
  const palette = [
    "#00C26E", "#F5C342", "#4D9FFF", "#FF5C5C",
    "#F59E0B", "#8B5CF6", "#EC4899", "#14B8A6",
    "#FB923C", "#94A3B8", "#22D3EE", "#A78BFA",
    "#84CC16", "#F87171", "#60A5FA",
  ];
  return palette[index % palette.length];
}

/** Clamp a number */
export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}
