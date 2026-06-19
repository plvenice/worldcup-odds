"use client";

import Link from "next/link";
import type { Forecast, Match } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct } from "@/lib/utils";

const VENUES: Record<string, { name: string; city: string }> = {
  azteca:       { name: "Estadio Azteca",         city: "Mexico City" },
  akron:        { name: "Estadio Akron",           city: "Guadalajara" },
  bbva:         { name: "Estadio BBVA",            city: "Monterrey" },
  bmo:          { name: "BMO Field",               city: "Toronto" },
  bcplace:      { name: "BC Place",                city: "Vancouver" },
  sofi:         { name: "SoFi Stadium",            city: "Inglewood" },
  levis:        { name: "Levi's Stadium",          city: "Santa Clara" },
  lumen:        { name: "Lumen Field",             city: "Seattle" },
  att:          { name: "AT&T Stadium",            city: "Arlington" },
  nrg:          { name: "NRG Stadium",             city: "Houston" },
  arrowhead:    { name: "Arrowhead Stadium",       city: "Kansas City" },
  mercedesbenz: { name: "Mercedes-Benz Stadium",   city: "Atlanta" },
  hardrock:     { name: "Hard Rock Stadium",       city: "Miami Gardens" },
  metlife:      { name: "MetLife Stadium",         city: "East Rutherford" },
  lincoln:      { name: "Lincoln Financial Field", city: "Philadelphia" },
  gillette:     { name: "Gillette Stadium",        city: "Foxborough" },
};

function ProbBar({
  home, draw, away, homeName, awayName,
}: {
  home: number; draw: number; away: number;
  homeName: string; awayName: string;
}) {
  return (
    <div>
      <div className="flex rounded overflow-hidden h-6 text-xs font-semibold tabular-nums">
        <div
          className="flex items-center justify-center overflow-hidden"
          style={{ width: `${home * 100}%`, background: "var(--green)", color: "#000" }}
        >
          {home > 0.13 ? `${Math.round(home * 100)}%` : ""}
        </div>
        <div
          className="flex items-center justify-center overflow-hidden"
          style={{ width: `${draw * 100}%`, background: "var(--draw)", color: "var(--text)" }}
        >
          {draw > 0.13 ? `${Math.round(draw * 100)}%` : ""}
        </div>
        <div
          className="flex items-center justify-center overflow-hidden"
          style={{ width: `${away * 100}%`, background: "var(--blue)", color: "#000" }}
        >
          {away > 0.13 ? `${Math.round(away * 100)}%` : ""}
        </div>
      </div>
      <div className="flex justify-between text-xs mt-1 tabular-nums" style={{ color: "var(--muted)" }}>
        <span style={{ color: "var(--green)" }}>{homeName} win</span>
        <span>Draw</span>
        <span style={{ color: "var(--blue)" }}>{awayName} win</span>
      </div>
    </div>
  );
}

function StakesRow({ m, teamId }: { m: Match; teamId: string }) {
  const entry = m.leverage?.find((l) => l.team === teamId);
  if (!entry) return null;

  const isHome = m.home === teamId;
  const [h, d, a] = entry.p_advance_by_outcome;
  const ifWin  = isHome ? h : a;
  const ifDraw = d;
  const ifLose = isHome ? a : h;
  const swingPp = Math.round(entry.advance_swing * 100);

  return (
    <div
      className="flex items-center gap-2 text-xs py-1.5 tabular-nums"
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <span className="inline-flex items-center gap-1.5 shrink-0" style={{ minWidth: 130 }}>
        <Flag id={teamId} h={11} />
        <Link href={`/team?id=${teamId}`} className="hover:underline truncate" style={{ color: "var(--text)" }}>
          {getName(teamId)}
        </Link>
      </span>
      <span style={{ color: "var(--green)" }}>W {fmtPct(ifWin)}</span>
      <span style={{ color: "var(--draw)" }}>D {fmtPct(ifDraw)}</span>
      <span style={{ color: ifLose < 0.06 ? "var(--red)" : "var(--muted)" }}>L {fmtPct(ifLose)}</span>
      <span
        className="ml-auto font-semibold shrink-0"
        style={{ color: swingPp >= 35 ? "var(--gold)" : "var(--muted)" }}
        title="Advance probability swing (best minus worst outcome)"
      >
        ↕{swingPp}pp
      </span>
    </div>
  );
}

function MatchCard({ m, forecast }: { m: Match; forecast: Forecast }) {
  const venue = VENUES[m.venue];
  const hasStakes =
    !m.played &&
    !!m.leverage?.some((l) => l.team === m.home || l.team === m.away);

  // Flag a winner for played matches
  const homeWon = m.played && m.hg != null && m.ag != null && m.hg > m.ag;
  const awayWon = m.played && m.hg != null && m.ag != null && m.ag > m.hg;

  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      {/* Card header */}
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ borderBottom: "1px solid var(--border)", background: "rgba(255,255,255,0.025)" }}
      >
        <span
          className="font-heading font-bold uppercase tracking-widest"
          style={{ color: "var(--gold)", fontSize: 11 }}
        >
          Group {m.group}
        </span>
        <span style={{ color: "var(--muted)", fontSize: 11 }}>
          {venue ? `${venue.name} · ${venue.city}` : m.venue}
        </span>
      </div>

      <div className="px-4 py-3 flex flex-col gap-3">
        {/* Teams row */}
        <div className="flex items-center gap-3">
          {/* Home */}
          <Link
            href={`/team?id=${m.home}`}
            className="flex-1 flex items-center justify-end gap-2 min-w-0 hover:opacity-80 transition-opacity"
            style={{ textDecoration: "none" }}
          >
            <span
              className="font-heading font-bold truncate"
              style={{
                color: homeWon ? "var(--green)" : "var(--text)",
                fontSize: 15,
                textAlign: "right",
              }}
            >
              {getName(m.home)}
            </span>
            <Flag id={m.home} h={24} style={{ borderRadius: 3, flexShrink: 0 }} />
          </Link>

          {/* Score or vs */}
          {m.played ? (
            <div
              className="shrink-0 text-center font-heading font-bold tabular-nums"
              style={{ color: "var(--text)", fontSize: 22, minWidth: 60, letterSpacing: "0.02em" }}
            >
              {m.hg}&thinsp;–&thinsp;{m.ag}
            </div>
          ) : (
            <div
              className="shrink-0 text-center"
              style={{ color: "var(--muted)", fontSize: 12, minWidth: 36, fontWeight: 500 }}
            >
              vs
            </div>
          )}

          {/* Away */}
          <Link
            href={`/team?id=${m.away}`}
            className="flex-1 flex items-center justify-start gap-2 min-w-0 hover:opacity-80 transition-opacity"
            style={{ textDecoration: "none" }}
          >
            <Flag id={m.away} h={24} style={{ borderRadius: 3, flexShrink: 0 }} />
            <span
              className="font-heading font-bold truncate"
              style={{ color: awayWon ? "var(--green)" : "var(--text)", fontSize: 15 }}
            >
              {getName(m.away)}
            </span>
          </Link>
        </div>

        {/* Prob bar — unplayed only */}
        {!m.played && m.probs && (
          <ProbBar
            home={m.probs.home}
            draw={m.probs.draw}
            away={m.probs.away}
            homeName={getName(m.home)}
            awayName={getName(m.away)}
          />
        )}

        {/* Stakes */}
        {hasStakes && (
          <div>
            <div
              className="text-xs font-semibold uppercase tracking-wide mb-1"
              style={{ color: "var(--muted)", fontSize: 10 }}
            >
              Advance probability by result
            </div>
            <StakesRow m={m} teamId={m.home} />
            <StakesRow m={m} teamId={m.away} />
          </div>
        )}
      </div>
    </div>
  );
}

/** Returns local YYYY-MM-DD (not UTC) so "today" matches the viewer's calendar day. */
function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

interface Props {
  forecast: Forecast;
}

export default function GamesToday({ forecast }: Props) {
  const today = localToday();
  const todayMatches = forecast.matches.filter((m) => m.date === today);

  if (todayMatches.length === 0) return null;

  const played = todayMatches.filter((m) => m.played).length;
  const total  = todayMatches.length;

  return (
    <section id="today">
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3 flex items-center gap-3"
        style={{ color: "var(--text)" }}
      >
        Today&apos;s Matches
        <span
          className="font-heading font-normal text-sm"
          style={{ color: "var(--muted)", letterSpacing: 0 }}
        >
          {played === total
            ? "all final"
            : played === 0
            ? `${total} match${total > 1 ? "es" : ""}`
            : `${played} / ${total} final`}
        </span>
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {todayMatches.map((m) => (
          <MatchCard key={m.id} m={m} forecast={forecast} />
        ))}
      </div>
    </section>
  );
}
