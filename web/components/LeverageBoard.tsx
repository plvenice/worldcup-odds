"use client";

import { useState } from "react";
import Link from "next/link";
import type { Match } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct, fmtMatchDate } from "@/lib/utils";

interface Props {
  matches: Match[];
}

function OutcomeBar({ home, draw, away }: { home: number; draw: number; away: number }) {
  const total = home + draw + away;
  const hp = (home / total) * 100;
  const dp = (draw / total) * 100;
  const ap = (away / total) * 100;

  return (
    <div className="flex rounded overflow-hidden h-5 text-xs font-semibold tabular">
      <div
        className="flex items-center justify-center transition-all"
        style={{
          width: `${hp}%`,
          background: "var(--green)",
          color: "#000",
          minWidth: hp > 8 ? undefined : 0,
          overflow: "hidden",
        }}
      >
        {hp > 12 ? `${hp.toFixed(0)}%` : ""}
      </div>
      <div
        className="flex items-center justify-center transition-all"
        style={{
          width: `${dp}%`,
          background: "var(--draw)",
          color: "var(--text)",
          minWidth: dp > 8 ? undefined : 0,
          overflow: "hidden",
        }}
      >
        {dp > 12 ? `${dp.toFixed(0)}%` : ""}
      </div>
      <div
        className="flex items-center justify-center transition-all"
        style={{
          width: `${ap}%`,
          background: "var(--blue)",
          color: "#000",
          minWidth: ap > 8 ? undefined : 0,
          overflow: "hidden",
        }}
      >
        {ap > 12 ? `${ap.toFixed(0)}%` : ""}
      </div>
    </div>
  );
}

function AttributionChips({ attr }: { attr: Record<string, string | number> }) {
  const entries = Object.entries(attr);
  if (entries.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {entries.map(([k, v]) => (
        <span
          key={k}
          className="text-xs px-1.5 py-0.5 rounded"
          style={{ background: "rgba(255,255,255,0.06)", color: "var(--muted)" }}
        >
          {k}: {typeof v === "number" ? (v > 0 ? `+${v}` : v) : v}
        </span>
      ))}
    </div>
  );
}

function MarketCompare({ m }: { m: Match }) {
  if (!m.market_probs || !m.model_probs || !m.probs) return null;
  const Row = ({
    label,
    p,
    bold,
  }: {
    label: string;
    p: { home: number; draw: number; away: number };
    bold?: boolean;
  }) => (
    <div className="flex tabular" style={{ fontSize: 11, fontWeight: bold ? 600 : 400 }}>
      <span style={{ width: 56, color: bold ? "var(--gold)" : "var(--muted)" }}>{label}</span>
      <span style={{ width: 50, color: "var(--green)" }}>{fmtPct(p.home)}</span>
      <span style={{ width: 50, color: "var(--draw)" }}>{fmtPct(p.draw)}</span>
      <span style={{ width: 50, color: "var(--blue)" }}>{fmtPct(p.away)}</span>
    </div>
  );
  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 6, marginBottom: 4 }}>
      <div className="flex" style={{ fontSize: 9.5, color: "var(--muted)" }}>
        <span style={{ width: 56 }} />
        <span style={{ width: 50 }}>Home</span>
        <span style={{ width: 50 }}>Draw</span>
        <span style={{ width: 50 }}>Away</span>
      </div>
      <Row label="Model" p={m.model_probs} />
      <Row label="Market" p={m.market_probs} />
      <Row label="Blended" p={m.probs} bold />
    </div>
  );
}

function LeverageDetail({ match }: { match: Match }) {
  if (!match.leverage?.length && !match.market_probs) return null;

  return (
    <div
      className="mt-2 pt-2 grid grid-cols-1 gap-2 text-xs"
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <MarketCompare m={match} />
      {(match.leverage ?? []).map((lev) => (
        <div key={lev.team} className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5 font-semibold" style={{ color: "var(--text)" }}>
            <Flag id={lev.team} h={12} />
            <Link href={`/team?id=${lev.team}`} className="hover:underline" style={{ color: "inherit" }}>{getName(lev.team)}</Link>
          </div>
          <div className="flex gap-3 flex-wrap">
            <div>
              <div style={{ color: "var(--muted)" }}>P(Title) by outcome</div>
              <div className="flex gap-2 tabular">
                <span style={{ color: "var(--green)" }}>H: {fmtPct(lev.p_title_by_outcome[0])}</span>
                <span style={{ color: "var(--draw)" }}>D: {fmtPct(lev.p_title_by_outcome[1])}</span>
                <span style={{ color: "var(--blue)" }}>A: {fmtPct(lev.p_title_by_outcome[2])}</span>
              </div>
            </div>
            <div>
              <div style={{ color: "var(--muted)" }}>P(Advance) by outcome</div>
              <div className="flex gap-2 tabular">
                <span style={{ color: "var(--green)" }}>H: {fmtPct(lev.p_advance_by_outcome[0])}</span>
                <span style={{ color: "var(--draw)" }}>D: {fmtPct(lev.p_advance_by_outcome[1])}</span>
                <span style={{ color: "var(--blue)" }}>A: {fmtPct(lev.p_advance_by_outcome[2])}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3 tabular text-xs" style={{ color: "var(--muted)" }}>
            <span>
              Title swing:{" "}
              <span style={{ color: lev.title_swing > 0.01 ? "var(--gold)" : "var(--muted)" }}>
                {(lev.title_swing * 100).toFixed(2)}pp
              </span>
            </span>
            <span>
              Advance swing:{" "}
              <span
                style={{
                  color: lev.advance_swing > 0.1 ? "var(--red)" : "var(--muted)",
                }}
              >
                {(lev.advance_swing * 100).toFixed(1)}pp
              </span>
            </span>
          </div>
        </div>
      ))}
      {/* Attribution */}
      {match.attribution && (
        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 6, marginTop: 2 }}>
          <div style={{ color: "var(--muted)" }} className="mb-1">
            Factors
          </div>
          <div className="flex flex-col gap-1">
            {Object.keys(match.attribution.home).length > 0 && (
              <div>
                <span style={{ color: "var(--green)", marginRight: 4 }}>Home:</span>
                <AttributionChips attr={match.attribution.home} />
              </div>
            )}
            {Object.keys(match.attribution.away).length > 0 && (
              <div>
                <span style={{ color: "var(--blue)", marginRight: 4 }}>Away:</span>
                <AttributionChips attr={match.attribution.away} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LeverageBoard({ matches }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const unplayed = matches
    .filter((m) => !m.played && m.leverage_index !== undefined)
    .sort((a, b) => (b.leverage_index ?? 0) - (a.leverage_index ?? 0))
    .slice(0, 12);

  if (unplayed.length === 0) {
    return (
      <section>
        <h2 className="font-heading font-bold text-lg uppercase tracking-wider mb-3" style={{ color: "var(--text)" }}>
          Leverage Board
        </h2>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>No upcoming matches with leverage data.</p>
      </section>
    );
  }

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3"
        style={{ color: "var(--text)" }}
      >
        Leverage Board
        <span
          className="font-normal text-sm ml-2"
          style={{ color: "var(--muted)" }}
        >
          — what's at stake
        </span>
      </h2>

      <div className="flex flex-col gap-2">
        {unplayed.map((m) => {
          const isOpen = expanded.has(m.id);
          const hasProbs = !!m.probs;

          return (
            <div
              key={m.id}
              style={{
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "10px 12px",
              }}
            >
              <div
                className="flex items-center gap-3 cursor-pointer"
                onClick={() => toggle(m.id)}
              >
                {/* Date + group */}
                <div className="shrink-0 text-center" style={{ minWidth: 52 }}>
                  <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                    {m.group && <span className="mr-1">Grp {m.group}</span>}
                  </div>
                  <div className="text-xs tabular" style={{ color: "var(--muted)" }}>
                    {fmtMatchDate(m.date)}
                  </div>
                </div>

                {/* Teams */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 text-sm font-semibold flex-wrap">
                    <Flag id={m.home} h={14} />
                    <Link href={`/team?id=${m.home}`} onClick={(e) => e.stopPropagation()} className="hover:underline" style={{ color: "var(--text)" }}>{getName(m.home)}</Link>
                    <span style={{ color: "var(--muted)", fontWeight: 400 }}>vs</span>
                    <Flag id={m.away} h={14} />
                    <Link href={`/team?id=${m.away}`} onClick={(e) => e.stopPropagation()} className="hover:underline" style={{ color: "var(--text)" }}>{getName(m.away)}</Link>
                  </div>

                  {hasProbs && (
                    <div className="mt-1.5">
                      <OutcomeBar
                        home={m.probs!.home}
                        draw={m.probs!.draw}
                        away={m.probs!.away}
                      />
                      <div className="flex justify-between text-xs mt-0.5 tabular" style={{ color: "var(--muted)" }}>
                        <span>{fmtPct(m.probs!.home)}</span>
                        <span>{fmtPct(m.probs!.draw)}</span>
                        <span>{fmtPct(m.probs!.away)}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Leverage index */}
                <div className="shrink-0 text-right">
                  <div className="text-xs" style={{ color: "var(--muted)" }}>Leverage</div>
                  <div
                    className="font-heading font-bold tabular"
                    style={{
                      color:
                        (m.leverage_index ?? 0) > 0.03
                          ? "var(--gold)"
                          : "var(--text)",
                      fontSize: 16,
                    }}
                  >
                    {((m.leverage_index ?? 0) * 100).toFixed(2)}
                  </div>
                  <div className="text-xs" style={{ color: "var(--muted)" }}>
                    {isOpen ? "▲ hide" : "▼ detail"}
                  </div>
                </div>
              </div>

              {isOpen && <LeverageDetail match={m} />}
            </div>
          );
        })}
      </div>
    </section>
  );
}
