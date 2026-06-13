"use client";

import Link from "next/link";
import type { Forecast, GroupRow } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct } from "@/lib/utils";

interface Props {
  forecast: Forecast;
}

function AdvanceBar({ team, forecast }: { team: string; forecast: Forecast }) {
  const t = forecast.teams.find((t) => t.id === team);
  if (!t) return null;

  const barWidth = Math.round(t.p_advance * 100);
  const gwPct = Math.round(t.p_group_win * 100);
  const gsPct = Math.round(t.p_group_second * 100);
  const taPct = Math.round(t.p_third_advance * 100);

  return (
    <div className="group relative">
      <div
        className="h-2 rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.08)" }}
        title={`1st: ${gwPct}% | 2nd: ${gsPct}% | 3rd+: ${taPct}%`}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${barWidth}%`,
            background:
              t.p_advance > 0.85
                ? "var(--green)"
                : t.p_advance > 0.5
                ? "var(--gold)"
                : "var(--draw)",
          }}
        />
      </div>
      <div className="flex justify-between text-xs mt-0.5 tabular" style={{ color: "var(--muted)" }}>
        <span>{fmtPct(t.p_advance)} adv</span>
        <span style={{ fontSize: 10 }}>
          1st {gwPct}% · 2nd {gsPct}% · 3rd {taPct}%
        </span>
      </div>
    </div>
  );
}

function GroupCard({
  groupName,
  rows,
  forecast,
}: {
  groupName: string;
  rows: GroupRow[];
  forecast: Forecast;
}) {
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div
        className="px-3 py-2 font-heading font-bold text-base tracking-widest uppercase"
        style={{
          color: "var(--gold)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        Group {groupName}
      </div>
      <table className="w-full text-xs tabular">
        <thead>
          <tr style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>
            <th className="text-left px-3 py-1.5 font-semibold">Team</th>
            <th className="px-1 py-1.5 font-semibold">P</th>
            <th className="px-1 py-1.5 font-semibold">W</th>
            <th className="px-1 py-1.5 font-semibold">D</th>
            <th className="px-1 py-1.5 font-semibold">L</th>
            <th className="px-1 py-1.5 font-semibold">GD</th>
            <th className="px-1 py-1.5 font-semibold">Pts</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const teamForecast = forecast.teams.find((t) => t.id === row.team);
            return (
              <tr
                key={row.team}
                style={{
                  borderTop: i > 0 ? "1px solid var(--border)" : undefined,
                  opacity: teamForecast ? 1 : 0.5,
                }}
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <Flag id={row.team} h={13} />
                    <Link
                      href={`/team?id=${row.team}`}
                      className="font-semibold hover:underline whitespace-nowrap"
                      style={{
                        color: i === 0 ? "var(--gold)" : "var(--text)",
                        fontFamily: "'Barlow Condensed', system-ui",
                        fontSize: 14,
                      }}
                    >
                      {getName(row.team)}
                    </Link>
                  </div>
                  {teamForecast && (
                    <div className="mt-1">
                      <AdvanceBar team={row.team} forecast={forecast} />
                    </div>
                  )}
                </td>
                <td className="text-center px-1 py-2" style={{ color: "var(--muted)" }}>
                  {row.played}
                </td>
                <td className="text-center px-1 py-2" style={{ color: row.won > 0 ? "var(--green)" : "var(--muted)" }}>
                  {row.won}
                </td>
                <td className="text-center px-1 py-2" style={{ color: "var(--muted)" }}>
                  {row.drawn}
                </td>
                <td className="text-center px-1 py-2" style={{ color: row.lost > 0 ? "var(--red)" : "var(--muted)" }}>
                  {row.lost}
                </td>
                <td
                  className="text-center px-1 py-2"
                  style={{ color: row.gd > 0 ? "var(--green)" : row.gd < 0 ? "var(--red)" : "var(--muted)" }}
                >
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td
                  className="text-center px-1 py-2 font-bold"
                  style={{ color: "var(--text)" }}
                >
                  {row.pts}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Groups({ forecast }: Props) {
  const groupKeys = Object.keys(forecast.groups).sort();

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3"
        style={{ color: "var(--text)" }}
      >
        Groups
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {groupKeys.map((g) => (
          <GroupCard
            key={g}
            groupName={g}
            rows={forecast.groups[g]}
            forecast={forecast}
          />
        ))}
      </div>
    </section>
  );
}
