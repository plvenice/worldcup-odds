"use client";

import Link from "next/link";
import type { Forecast, HistoryRow, Match } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { getTimestamps } from "@/lib/utils";

interface Props {
  forecast: Forecast | null;
  history: HistoryRow[];
}

// Swings smaller than this are normal model noise, not news.
const MIN_SWING_PTS = 1.0;

function matchClause(team: string, m: Match): string | null {
  if (m.hg == null || m.ag == null) return null;
  const isHome = m.home === team;
  const opp = isHome ? m.away : m.home;
  const mine = isHome ? m.hg : m.ag;
  const theirs = isHome ? m.ag : m.hg;
  if (mine > theirs) return `after beating ${getName(opp)} ${mine}–${theirs}`;
  if (mine < theirs) return `after losing to ${getName(opp)} ${theirs}–${mine}`;
  return `after drawing ${mine}–${theirs} with ${getName(opp)}`;
}

export default function BiggestMover({ forecast, history }: Props) {
  if (!forecast || history.length === 0) return null;

  const timestamps = getTimestamps(history);
  if (timestamps.length < 2) return null;

  const latestTs = timestamps[timestamps.length - 1];
  const targetBaseline = new Date(latestTs).getTime() - 24 * 3600 * 1000;

  // Closest available snapshot at or before 24h ago; falls back to the
  // earliest snapshot we have when the tournament hasn't run a full day yet.
  let baselineTs = timestamps[0];
  for (const ts of timestamps) {
    if (new Date(ts).getTime() <= targetBaseline) baselineTs = ts;
    else break;
  }
  if (baselineTs === latestTs) return null;

  const atBaseline = new Map<string, number>();
  const atLatest = new Map<string, number>();
  for (const r of history) {
    if (r.ts === baselineTs) atBaseline.set(r.team, r.p_title);
    if (r.ts === latestTs) atLatest.set(r.team, r.p_title);
  }

  let bestTeam: string | null = null;
  let bestDelta = 0;
  for (const t of forecast.teams) {
    const before = atBaseline.get(t.id);
    const after = atLatest.get(t.id);
    if (before == null || after == null) continue;
    const delta = after - before;
    if (Math.abs(delta) > Math.abs(bestDelta)) {
      bestDelta = delta;
      bestTeam = t.id;
    }
  }

  if (!bestTeam || Math.abs(bestDelta) * 100 < MIN_SWING_PTS) return null;

  const before = (atBaseline.get(bestTeam) ?? 0) * 100;
  const after = (atLatest.get(bestTeam) ?? 0) * 100;
  const rose = bestDelta > 0;

  const elapsedHours = (new Date(latestTs).getTime() - new Date(baselineTs).getTime()) / 3600000;
  const window = elapsedHours >= 18 ? "over the last 24 hours" : "since tracking began";

  // Only attribute the swing to a result that actually happened inside the
  // window we're describing — an older group match isn't the cause of today's move.
  const baselineDate = baselineTs.slice(0, 10);
  const recentMatch = forecast.matches
    .filter((m) => m.played && m.date >= baselineDate && (m.home === bestTeam || m.away === bestTeam))
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0))[0];
  const clause = recentMatch ? matchClause(bestTeam, recentMatch) : null;

  return (
    <div
      className="flex items-center gap-2 flex-wrap"
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        padding: "10px 16px",
        fontSize: 13,
      }}
    >
      <span style={{ color: rose ? "var(--green)" : "var(--red)", fontWeight: 700 }}>
        {rose ? "▲" : "▼"}
      </span>
      <Flag id={bestTeam} h={14} />
      <Link
        href={`/team?id=${bestTeam}`}
        className="hover:underline font-semibold"
        style={{ color: "var(--text)" }}
      >
        {getName(bestTeam)}
      </Link>
      <span style={{ color: "var(--muted)" }}>
        &apos;s title chance {rose ? "rose" : "fell"} from {before.toFixed(1)}% to{" "}
        <span style={{ color: "var(--text)", fontWeight: 600 }}>{after.toFixed(1)}%</span> {window}
        {clause ? `, ${clause}` : ""}.
      </span>
    </div>
  );
}
