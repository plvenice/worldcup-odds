"use client";

import Link from "next/link";
import type { Forecast, GroupRow } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct } from "@/lib/utils";

interface Props {
  forecast: Forecast;
}

function advColor(p: number): string {
  if (p >= 0.85) return "var(--green)";
  if (p >= 0.5)  return "var(--gold)";
  return "var(--draw)";
}

function AdvanceBar({ team, forecast }: { team: string; forecast: Forecast }) {
  const t = forecast.teams.find((t) => t.id === team);
  if (!t) return null;

  const barWidth = Math.round(t.p_advance * 100);
  const gwPct   = Math.round(t.p_group_win * 100);
  const gsPct   = Math.round(t.p_group_second * 100);
  const taPct   = Math.round(t.p_third_advance * 100);
  const color   = advColor(t.p_advance);

  return (
    <div>
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.08)" }}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${barWidth}%`, background: color }}
        />
      </div>
      <div className="flex items-center justify-between mt-1">
        {/* Advance % stacked over "adv" label */}
        <div className="flex flex-col items-center leading-none" style={{ minWidth: 38 }}>
          <span className="tabular font-bold text-xs" style={{ color }}>
            {fmtPct(t.p_advance)}
          </span>
          <span style={{ color: "var(--muted)", fontSize: 8.5, marginTop: 1 }}>adv</span>
        </div>
        {/* Breakdown */}
        <span style={{ color: "var(--muted)", fontSize: 9.5, whiteSpace: "nowrap" }}>
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
        style={{ color: "var(--gold)", borderBottom: "1px solid var(--border)" }}
      >
        Group {groupName}
      </div>
      <table className="w-full text-xs tabular" style={{ tableLayout: "fixed" }}>
        <colgroup>
          {/* Team column: takes remaining space */}
          <col style={{ width: "auto" }} />
          {/* Stat columns: fixed narrow */}
          <col style={{ width: 22 }} />
          <col style={{ width: 30 }} />
          <col style={{ width: 28 }} />
        </colgroup>
        <thead>
          <tr style={{ color: "var(--muted)", borderBottom: "1px solid var(--border)" }}>
            <th className="text-left px-3 py-1.5 font-semibold">Team</th>
            <th className="text-center py-1.5 font-semibold">P</th>
            <th className="text-center py-1.5 font-semibold">GD</th>
            <th className="text-center py-1.5 font-semibold">Pts</th>
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
                      className="font-semibold hover:underline truncate"
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
                    <div className="mt-1.5">
                      <AdvanceBar team={row.team} forecast={forecast} />
                    </div>
                  )}
                </td>
                <td className="text-center py-2" style={{ color: "var(--muted)" }}>
                  {row.played}
                </td>
                <td
                  className="text-center py-2"
                  style={{ color: row.gd > 0 ? "var(--green)" : row.gd < 0 ? "var(--red)" : "var(--muted)" }}
                >
                  {row.gd > 0 ? `+${row.gd}` : row.gd}
                </td>
                <td className="text-center py-2 font-bold" style={{ color: "var(--text)" }}>
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

  // Sort group cards by the highest p_title in the group (most interesting groups first)
  const sortedGroups = groupKeys.slice().sort((a, b) => {
    const bestA = Math.max(
      ...forecast.groups[a].map(
        (row) => forecast.teams.find((t) => t.id === row.team)?.p_title ?? 0
      )
    );
    const bestB = Math.max(
      ...forecast.groups[b].map(
        (row) => forecast.teams.find((t) => t.id === row.team)?.p_title ?? 0
      )
    );
    return bestB - bestA;
  });

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3"
        style={{ color: "var(--text)" }}
      >
        Groups
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {sortedGroups.map((g) => (
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
