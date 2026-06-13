"use client";

import Link from "next/link";
import type { Forecast } from "@/lib/types";
import { getFlag } from "@/lib/flags";
import { fmtPct, minutesAgo } from "@/lib/utils";

interface Props {
  forecast: Forecast | null;
  loading: boolean;
  lastFetched: Date | null;
}

export default function Header({ forecast, loading, lastFetched }: Props) {
  const top6 = forecast?.teams.slice(0, 6) ?? [];
  const minsAgo = lastFetched ? minutesAgo(forecast?.generated_at ?? lastFetched.toISOString()) : null;

  return (
    <header
      style={{ background: "var(--panel)", borderBottom: "1px solid var(--border)" }}
      className="sticky top-0 z-50 w-full"
    >
      <div className="max-w-7xl mx-auto px-3 py-2">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <h1
              className="font-heading text-xl font-bold tracking-wide"
              style={{ color: "var(--gold)" }}
            >
              World Cup 2026
            </h1>
            <span
              className="font-heading text-sm font-semibold uppercase tracking-widest"
              style={{ color: "var(--muted)" }}
            >
              Live Forecast
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs" style={{ color: "var(--muted)" }}>
            {loading && (
              <span className="animate-pulse" style={{ color: "var(--green)" }}>
                ⟳ Updating...
              </span>
            )}
            {minsAgo !== null && !loading && (
              <span>
                Updated{" "}
                <span style={{ color: "var(--text)" }}>
                  {minsAgo === 0 ? "just now" : `${minsAgo}m ago`}
                </span>
              </span>
            )}
            {forecast && (
              <span>
                · {forecast.nsims.toLocaleString()} sims ·{" "}
                <span style={{ color: "var(--muted)" }}>{forecast.results_source}</span>
              </span>
            )}
          </div>
        </div>

        {/* Top 6 strip */}
        {top6.length > 0 && (
          <div className="flex gap-2 mt-2 overflow-x-auto pb-1">
            {top6.map((team, i) => (
              <Link
                key={team.id}
                href={`/team?id=${team.id}`}
                className="flex items-center gap-1.5 rounded px-2 py-1 shrink-0 hover:opacity-80 transition-opacity"
                style={{
                  background: i === 0 ? "rgba(245,195,66,0.15)" : "rgba(255,255,255,0.05)",
                  border: `1px solid ${i === 0 ? "var(--gold)" : "var(--border)"}`,
                }}
              >
                <span className="text-base leading-none">{getFlag(team.id)}</span>
                <span
                  className="font-heading font-semibold text-sm tracking-wide"
                  style={{ color: i === 0 ? "var(--gold)" : "var(--text)" }}
                >
                  {team.id}
                </span>
                <span
                  className="tabular text-xs font-semibold"
                  style={{ color: "var(--green)" }}
                >
                  {fmtPct(team.p_title)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
