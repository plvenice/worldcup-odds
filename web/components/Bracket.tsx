"use client";

import Link from "next/link";
import type { Forecast, TeamDist, BracketR32Match, BracketLaterMatch, BracketFinal } from "@/lib/types";
import { getFlag } from "@/lib/flags";

interface Props {
  forecast: Forecast;
}

function DistList({ dist, maxShow = 3 }: { dist: TeamDist[]; maxShow?: number }) {
  const shown = dist.slice(0, maxShow);
  const rest = dist.slice(maxShow).reduce((sum, t) => sum + t.p, 0);

  return (
    <div className="flex flex-col gap-0.5">
      {shown.map((t) => (
        <div key={t.team} className="flex items-center gap-1.5">
          <span className="text-sm">{getFlag(t.team)}</span>
          <Link
            href={`/team?id=${t.team}`}
            className="font-heading font-semibold hover:underline tabular"
            style={{ color: "var(--text)", fontSize: 12, letterSpacing: "0.05em" }}
          >
            {t.team}
          </Link>
          <span
            className="tabular text-xs ml-auto"
            style={{ color: "var(--muted)" }}
          >
            {(t.p * 100).toFixed(0)}%
          </span>
        </div>
      ))}
      {rest > 0 && (
        <div className="text-xs" style={{ color: "var(--muted)", paddingLeft: 24 }}>
          others {(rest * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
}

function SlotLabel({ slot }: { slot: { type: string; group?: string } }) {
  if (slot.type === "R") return <span style={{ color: "var(--muted)" }}>Runner {slot.group}</span>;
  if (slot.type === "W") return <span style={{ color: "var(--muted)" }}>Winner {slot.group}</span>;
  return <span style={{ color: "var(--muted)" }}>{slot.type} {slot.group}</span>;
}

function R32Card({ match }: { match: BracketR32Match }) {
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "8px 10px",
        minWidth: 140,
        maxWidth: 180,
      }}
    >
      <div className="text-xs mb-1.5" style={{ color: "var(--muted)" }}>
        #{match.match} · {match.date?.slice(5)}
      </div>
      <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 6, marginBottom: 6 }}>
        <div className="text-xs mb-1" style={{ color: "var(--muted)" }}>
          <SlotLabel slot={match.home_slot} />
        </div>
        <DistList dist={match.home_dist} maxShow={2} />
      </div>
      <div>
        <div className="text-xs mb-1" style={{ color: "var(--muted)" }}>
          <SlotLabel slot={match.away_slot} />
        </div>
        <DistList dist={match.away_dist} maxShow={2} />
      </div>
      <div style={{ borderTop: "1px solid var(--border)", marginTop: 6, paddingTop: 6 }}>
        <div className="text-xs mb-1" style={{ color: "var(--gold)" }}>Winner likely</div>
        <DistList dist={match.winner_dist} maxShow={3} />
      </div>
    </div>
  );
}

function LaterCard({ match, label }: { match: BracketLaterMatch; label: string }) {
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "8px 10px",
        minWidth: 140,
        maxWidth: 180,
      }}
    >
      <div className="text-xs mb-1.5" style={{ color: "var(--muted)" }}>
        {label} #{match.match} · {match.date?.slice(5)}
      </div>
      <DistList dist={match.winner_dist} maxShow={4} />
    </div>
  );
}

function FinalCard({ match }: { match: BracketFinal }) {
  return (
    <div
      style={{
        background: "rgba(245,195,66,0.08)",
        border: "1px solid var(--gold)",
        borderRadius: 8,
        padding: "8px 10px",
        minWidth: 150,
        maxWidth: 200,
      }}
    >
      <div className="text-xs mb-1.5" style={{ color: "var(--gold)" }}>
        Final · {match.date}
      </div>
      <DistList dist={match.winner_dist} maxShow={6} />
    </div>
  );
}

export default function BracketView({ forecast }: Props) {
  const { bracket } = forecast;

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3"
        style={{ color: "var(--text)" }}
      >
        Bracket
      </h2>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        Probabilities shown are most likely occupants — scroll right on mobile.
      </p>

      <div className="overflow-x-auto pb-3">
        <div className="flex gap-4" style={{ minWidth: 900 }}>
          {/* R32 */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="font-heading font-bold text-xs uppercase tracking-widest mb-1" style={{ color: "var(--muted)" }}>
              R32 ({bracket.r32.length} matches)
            </div>
            {bracket.r32.map((m) => (
              <R32Card key={m.match} match={m} />
            ))}
          </div>

          {/* R16 */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="font-heading font-bold text-xs uppercase tracking-widest mb-1" style={{ color: "var(--muted)" }}>
              R16
            </div>
            {bracket.r16.map((m) => (
              <LaterCard key={m.match} match={m} label="R16" />
            ))}
          </div>

          {/* QF */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="font-heading font-bold text-xs uppercase tracking-widest mb-1" style={{ color: "var(--muted)" }}>
              QF
            </div>
            {bracket.qf.map((m) => (
              <LaterCard key={m.match} match={m} label="QF" />
            ))}
          </div>

          {/* SF */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="font-heading font-bold text-xs uppercase tracking-widest mb-1" style={{ color: "var(--muted)" }}>
              SF
            </div>
            {bracket.sf.map((m) => (
              <LaterCard key={m.match} match={m} label="SF" />
            ))}
          </div>

          {/* Final */}
          <div className="flex flex-col gap-2 shrink-0">
            <div className="font-heading font-bold text-xs uppercase tracking-widest mb-1" style={{ color: "var(--gold)" }}>
              Final
            </div>
            <FinalCard match={bracket.final} />
          </div>
        </div>
      </div>
    </section>
  );
}
