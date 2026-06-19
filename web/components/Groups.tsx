"use client";

import Link from "next/link";
import type { Forecast, GroupRow, LiveForecast } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct } from "@/lib/utils";

interface Props {
  forecast: Forecast;
  liveForecast?: LiveForecast | null;
}

function advColor(p: number): string {
  if (p >= 0.85) return "var(--green)";
  if (p >= 0.5)  return "var(--gold)";
  return "var(--draw)";
}

function AdvanceBar({
  team,
  forecast,
  liveForecast,
}: {
  team: string;
  forecast: Forecast;
  liveForecast?: LiveForecast | null;
}) {
  const t = forecast.teams.find((t) => t.id === team);
  if (!t) return null;

  const live = liveForecast?.available ? liveForecast.teams?.[team] : null;

  const pAdvance     = live ? live.p_advance      : t.p_advance;
  const pGroupWin    = live ? live.p_group_win    : t.p_group_win;
  const pGroupSecond = live ? live.p_group_second : t.p_group_second;
  const pThirdAdv    = live ? live.p_third_advance : t.p_third_advance;

  const barWidth = Math.round(pAdvance * 100);
  const color    = advColor(pAdvance);

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
        <div className="flex flex-col items-center leading-none" style={{ minWidth: 38 }}>
          <span className="tabular font-bold text-xs" style={{ color }}>
            {fmtPct(pAdvance)}
          </span>
          <span style={{ color: "var(--muted)", fontSize: 8.5, marginTop: 1 }}>adv</span>
        </div>
        <span style={{ color: "var(--muted)", fontSize: 9.5, whiteSpace: "nowrap" }}>
          1st {Math.round(pGroupWin * 100)}% · 2nd {Math.round(pGroupSecond * 100)}% · 3rd {Math.round(pThirdAdv * 100)}%
        </span>
      </div>
    </div>
  );
}

function GroupCard({
  groupName,
  rows,
  forecast,
  liveForecast,
}: {
  groupName: string;
  rows: GroupRow[];
  forecast: Forecast;
  liveForecast?: LiveForecast | null;
}) {
  const isLive = liveForecast?.available &&
    liveForecast.groups_affected?.includes(groupName);

  return (
    <div
      style={{
        background: "var(--panel)",
        border: `1px solid ${isLive ? "var(--green)" : "var(--border)"}`,
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div
        className="px-3 py-2 flex items-center justify-between font-heading font-bold text-base tracking-widest uppercase"
        style={{ color: "var(--gold)", borderBottom: "1px solid var(--border)" }}
      >
        <span>Group {groupName}</span>
        {isLive && (
          <span
            className="font-heading font-bold uppercase"
            style={{
              color: "var(--green)",
              fontSize: 9,
              letterSpacing: "0.08em",
              border: "1px solid var(--green)",
              borderRadius: 4,
              padding: "1px 4px",
            }}
          >
            LIVE
          </span>
        )}
      </div>
      <table className="w-full text-xs tabular" style={{ tableLayout: "fixed" }}>
        <colgroup>
          <col style={{ width: "auto" }} />
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
                      <AdvanceBar
                        team={row.team}
                        forecast={forecast}
                        liveForecast={liveForecast}
                      />
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

export default function Groups({ forecast, liveForecast }: Props) {
  const groupKeys = Object.keys(forecast.groups).sort();

  const sortedGroups = groupKeys.slice().sort((a, b) => {
    const nextA = forecast.matches.filter(m => m.group === a && !m.played).map(m => m.date).sort()[0];
    const nextB = forecast.matches.filter(m => m.group === b && !m.played).map(m => m.date).sort()[0];
    if (nextA && !nextB) return -1;
    if (!nextA && nextB) return 1;
    if (nextA && nextB) return nextA < nextB ? -1 : nextA > nextB ? 1 : a.localeCompare(b);
    return a.localeCompare(b);
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
            liveForecast={liveForecast}
          />
        ))}
      </div>
    </section>
  );
}
