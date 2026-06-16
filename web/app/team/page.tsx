"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useData } from "@/lib/useData";
import { Flag, getName } from "@/lib/flags";
import { fmtPct, fmtElo, fmtMatchDate, fmtShortDate } from "@/lib/utils";
import type { Match, HistoryRow } from "@/lib/types";

const ROUNDS: { key: keyof RoundProbs; label: string }[] = [
  { key: "p_r32", label: "Round of 32" },
  { key: "p_r16", label: "Round of 16" },
  { key: "p_qf", label: "Quarterfinal" },
  { key: "p_sf", label: "Semifinal" },
  { key: "p_final", label: "Final" },
  { key: "p_title", label: "Champion" },
];

type RoundProbs = {
  p_r32: number;
  p_r16: number;
  p_qf: number;
  p_sf: number;
  p_final: number;
  p_title: number;
};

function panel(): React.CSSProperties {
  return {
    background: "var(--panel)",
    border: "1px solid var(--border)",
    borderRadius: 12,
  };
}

function TeamContent() {
  const params = useSearchParams();
  const id = params.get("id") ?? "";
  const { forecast, history, loading } = useData();

  if (loading && !forecast) {
    return (
      <div className="flex items-center justify-center py-24" style={{ color: "var(--muted)" }}>
        Loading…
      </div>
    );
  }

  const team = forecast?.teams.find((t) => t.id === id);
  if (!forecast || !team) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center" style={{ color: "var(--muted)" }}>
        <p>Team “{id}” not found.</p>
        <Link href="/" style={{ color: "var(--green)" }} className="hover:underline">
          ← Back to forecast
        </Link>
      </div>
    );
  }

  const rank = forecast.teams.findIndex((t) => t.id === id) + 1;
  const eloDelta = team.elo - team.elo_seed;
  const groupRows = forecast.groups[team.group] ?? [];
  const remaining = forecast.matches.filter(
    (m) => !m.played && (m.home === id || m.away === id)
  );
  const market = forecast.market?.implied?.[id];

  // history sparkline for this team — stride-sampled to ≤180 render points
  const MAX_RENDER_PTS = 180;
  const allSeries = history
    .filter((r: HistoryRow) => r.team === id)
    .map((r) => ({ ts: r.ts, p: r.p_title * 100 }));
  const stride = Math.max(1, Math.ceil(allSeries.length / MAX_RENDER_PTS));
  const series = allSeries.filter((_, i) => i % stride === 0 || i === allSeries.length - 1);

  // baseline: overall leader's current probability
  const leaderTeam = forecast.teams[0];
  const leaderPct = (leaderTeam?.p_title ?? 0) * 100;
  const isLeader = leaderTeam?.id === id;

  const maxRound = Math.max(...ROUNDS.map((r) => team[r.key]));

  return (
    <div className="max-w-5xl mx-auto w-full px-3 py-5 flex flex-col gap-6">
      <Link href="/" style={{ color: "var(--muted)", fontSize: 13 }} className="hover:underline">
        ← All teams
      </Link>

      {/* hero */}
      <div className="flex items-center gap-4 flex-wrap">
        <Flag id={team.id} h={40} style={{ borderRadius: 4 }} />
        <div>
          <h1
            style={{
              fontFamily: "'Barlow Condensed', sans-serif",
              fontSize: 40,
              fontWeight: 700,
              color: "var(--text)",
              lineHeight: 1,
            }}
          >
            {team.name}
          </h1>
          <div style={{ color: "var(--muted)", fontSize: 14 }}>
            Group {team.group} · #{rank} by title odds
          </div>
        </div>
        <div className="ml-auto flex gap-6">
          <Stat label="P(title)" value={fmtPct(team.p_title)} accent="var(--gold)" />
          <Stat label="P(advance)" value={fmtPct(team.p_advance)} accent="var(--green)" />
          <Stat
            label="Elo"
            value={fmtElo(team.elo)}
            sub={`${eloDelta >= 0 ? "+" : ""}${eloDelta.toFixed(0)} vs seed`}
            subColor={eloDelta >= 0 ? "var(--green)" : "var(--red)"}
          />
          {market !== undefined && (
            <Stat label="Market" value={fmtPct(market)} accent="var(--blue)" />
          )}
        </div>
      </div>

      {/* round progression funnel */}
      <section style={panel()} className="p-4">
        <h2 className="font-heading font-bold text-lg uppercase tracking-wider" style={{ color: "var(--text)" }}>Path to the title</h2>
        <div className="flex flex-col gap-2 mt-3">
          {ROUNDS.map((r) => {
            const p = team[r.key];
            const w = maxRound > 0 ? (p / maxRound) * 100 : 0;
            return (
              <div key={r.key} className="flex items-center gap-3">
                <span style={{ width: 96, color: "var(--muted)", fontSize: 12 }}>{r.label}</span>
                <div
                  className="flex-1 h-6 rounded overflow-hidden"
                  style={{ background: "var(--bg)" }}
                >
                  <div
                    className="h-full flex items-center px-2"
                    style={{
                      width: `${Math.max(w, 6)}%`,
                      background: "linear-gradient(90deg, var(--green), var(--gold))",
                      transition: "width .3s",
                    }}
                  >
                    <span
                      style={{ fontSize: 11, fontWeight: 600, color: "#08130C" }}
                      className="tabular-nums"
                    >
                      {fmtPct(p)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="grid md:grid-cols-2 gap-6">
        {/* group context */}
        <section style={panel()} className="p-4">
          <h2 className="font-heading font-bold text-lg uppercase tracking-wider" style={{ color: "var(--text)" }}>Group {team.group}</h2>
          <table className="w-full mt-3 text-sm tabular-nums">
            <thead>
              <tr style={{ color: "var(--muted)", fontSize: 11 }} className="text-left">
                <th className="font-normal pb-1">Team</th>
                <th className="font-normal pb-1 text-center">Pld</th>
                <th className="font-normal pb-1 text-center">GD</th>
                <th className="font-normal pb-1 text-center">Pts</th>
              </tr>
            </thead>
            <tbody>
              {groupRows.map((row, i) => {
                const me = row.team === id;
                return (
                  <tr
                    key={row.team}
                    style={{
                      color: me ? "var(--gold)" : "var(--text)",
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <td className="py-1">
                      <span className="inline-flex items-center gap-1.5">
                        <span style={{ color: "var(--muted)" }}>{i + 1}</span>
                        <Flag id={row.team} h={12} />
                        {getName(row.team)}
                      </span>
                    </td>
                    <td className="text-center">{row.played}</td>
                    <td className="text-center">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                    <td className="text-center font-semibold">{row.pts}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        {/* p_title history sparkline */}
        <section style={panel()} className="p-4">
          <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
            <h2 className="font-heading font-bold text-lg uppercase tracking-wider" style={{ color: "var(--text)" }}>Title odds over time</h2>
            {!isLeader && leaderPct > 0 && (
              <div className="flex items-center gap-1.5" style={{ color: "var(--muted)", fontSize: 11 }}>
                <svg width={16} height={8} viewBox="0 0 16 8" fill="none">
                  <line x1="0" y1="4" x2="16" y2="4" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="3 2" />
                </svg>
                Leader ({getName(leaderTeam.id)}) {leaderPct.toFixed(1)}%
              </div>
            )}
          </div>
          {series.length > 1 ? (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={series} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
                <XAxis
                  dataKey="ts"
                  tickFormatter={fmtShortDate}
                  tick={{ fill: "var(--muted)", fontSize: 9 }}
                  stroke="var(--border)"
                  minTickGap={40}
                />
                <YAxis
                  tick={{ fill: "var(--muted)", fontSize: 9 }}
                  stroke="var(--border)"
                  tickFormatter={(v) => `${v.toFixed(0)}%`}
                  domain={[0, isLeader ? "auto" : Math.max(leaderPct * 1.05, 1)]}
                  width={40}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--panel)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelFormatter={(label) => fmtShortDate(String(label))}
                  formatter={(v) => [`${Number(v).toFixed(2)}%`, "P(title)"]}
                />
                {!isLeader && leaderPct > 0 && (
                  <ReferenceLine
                    y={leaderPct}
                    stroke="var(--muted)"
                    strokeDasharray="4 3"
                    strokeWidth={1}
                    strokeOpacity={0.5}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="p"
                  stroke="var(--gold)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: "var(--muted)", fontSize: 13 }} className="mt-3">
              Not enough history yet — the line builds as the model refreshes.
            </p>
          )}
        </section>
      </div>

      {/* remaining matches */}
      <section style={panel()} className="p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-heading font-bold text-lg uppercase tracking-wider" style={{ color: "var(--text)" }}>Remaining group matches</h2>
          <div className="flex items-center gap-3" style={{ fontSize: 11, color: "var(--muted)" }}>
            <MatchLegend color="var(--green)" label="Win" />
            <MatchLegend color="var(--draw)" label="Draw" />
            <MatchLegend color="var(--blue)" label="Loss" />
          </div>
        </div>
        {remaining.length === 0 ? (
          <p style={{ color: "var(--muted)", fontSize: 13 }} className="mt-3">
            No remaining group matches.
          </p>
        ) : (
          <div className="flex flex-col gap-2 mt-3">
            {remaining.map((m) => (
              <RemainingMatch key={m.id} m={m} teamId={id} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function RemainingMatch({ m, teamId }: { m: Match; teamId: string }) {
  const isHome = m.home === teamId;
  const opp = isHome ? m.away : m.home;
  const probs = m.probs;
  const winP = probs ? (isHome ? probs.home : probs.away) : 0;
  const drawP = probs?.draw ?? 0;
  const loseP = probs ? (isHome ? probs.away : probs.home) : 0;

  return (
    <div className="flex items-center gap-3">
      <span style={{ width: 92, color: "var(--muted)", fontSize: 11 }}>
        {fmtMatchDate(m.date)}
      </span>
      <span className="inline-flex items-center gap-1.5" style={{ width: 150, fontSize: 13 }}>
        <span style={{ color: "var(--muted)" }}>{isHome ? "vs" : "@"}</span>
        <Flag id={opp} h={12} />
        <span className="truncate" title={getName(opp)}>{getName(opp)}</span>
      </span>
      <div className="flex-1 h-5 rounded overflow-hidden flex" style={{ background: "var(--bg)" }}>
        <Seg p={winP} color="var(--green)" label="W" />
        <Seg p={drawP} color="var(--draw)" label="D" />
        <Seg p={loseP} color="var(--blue)" label="L" />
      </div>
    </div>
  );
}

function Seg({ p, color, label }: { p: number; color: string; label: string }) {
  if (p < 0.001) return null;
  const showFull = p > 0.14;
  const showLetter = p > 0.06;
  return (
    <div
      className="h-full flex items-center justify-center gap-0.5"
      style={{ width: `${p * 100}%`, background: color, minWidth: p > 0.06 ? undefined : 0 }}
      title={`${label} ${fmtPct(p)}`}
    >
      {showLetter && (
        <span style={{ fontSize: 10, fontWeight: 600, color: "#08130C" }} className="tabular-nums">
          {showFull ? `${label} ${(p * 100).toFixed(0)}` : label}
        </span>
      )}
    </div>
  );
}

function MatchLegend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: color }} />
      {label}
    </span>
  );
}

function Stat({
  label,
  value,
  sub,
  subColor,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
  accent?: string;
}) {
  return (
    <div className="text-right">
      <div style={{ color: "var(--muted)", fontSize: 11 }}>{label}</div>
      <div
        className="tabular-nums"
        style={{
          fontFamily: "'Barlow Condensed', sans-serif",
          fontSize: 26,
          fontWeight: 700,
          color: accent ?? "var(--text)",
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      {sub && <div style={{ color: subColor ?? "var(--muted)", fontSize: 11 }}>{sub}</div>}
    </div>
  );
}

export default function TeamPage() {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <Suspense
        fallback={
          <div className="flex items-center justify-center py-24" style={{ color: "var(--muted)" }}>
            Loading…
          </div>
        }
      >
        <TeamContent />
      </Suspense>
    </div>
  );
}
