"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  Legend,
  ReferenceLine,
} from "recharts";
import type { Forecast, HistoryRow } from "@/lib/types";
import { flagUrl, getName, Flag } from "@/lib/flags";
import { fmtPct, fmtPctNum, fmtShortDate, getTimestamps, teamColor } from "@/lib/utils";

interface Props {
  forecast: Forecast;
  history: HistoryRow[];
}

export default function TitleRaceChart({ forecast, history }: Props) {
  const top14 = forecast.teams.slice(0, 14);
  const hasMarket = forecast.market !== null;

  // Bar chart data
  const barData = top14.map((t) => ({
    id: t.id,
    name: t.name,
    model: parseFloat(fmtPctNum(t.p_title)),
    market: hasMarket
      ? forecast.market
        ? parseFloat(fmtPctNum(forecast.market.implied[t.id] ?? 0))
        : 0
      : undefined,
  }));

  // Leader baseline for the line chart
  const leader = forecast.teams[0];
  const leaderPct = parseFloat(fmtPctNum(leader?.p_title ?? 0));

  // History line chart — top 8 teams
  const top8 = forecast.teams.slice(0, 8).map((t) => t.id);
  const timestamps = getTimestamps(history);
  const lineData = timestamps.map((ts) => {
    const row: Record<string, number | string> = { ts };
    for (const tid of top8) {
      const entry = history.find((h) => h.ts === ts && h.team === tid);
      row[tid] = entry ? parseFloat(fmtPctNum(entry.p_title)) : 0;
    }
    return row;
  });

  // Bar shape: the model bar plus, when market data exists, a gold dot at the
  // team's market-implied probability on the same axis scale (directly
  // comparable to where the bar ends). pxPerPct = width/model is the global
  // px-per-percent constant since the axis is linear from 0.
  const BarWithMarketDot = (props: {
    x?: number | string;
    y?: number | string;
    width?: number | string;
    height?: number | string;
    fill?: string;
    payload?: { model?: number; market?: number };
  }) => {
    const x = Number(props.x ?? 0);
    const y = Number(props.y ?? 0);
    const width = Number(props.width ?? 0);
    const height = Number(props.height ?? 0);
    const model = Number(props.payload?.model ?? 0);
    const market = props.payload?.market;
    const pxPerPct = model > 0 ? width / model : 0;
    const showDot =
      hasMarket && market != null && Number.isFinite(market) && market > 0 && pxPerPct > 0;
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} rx={2.5} fill={props.fill} opacity={0.85} />
        {showDot && (
          <circle
            cx={x + Number(market) * pxPerPct}
            cy={y + height / 2}
            r={4.5}
            fill="var(--gold)"
            stroke="#0B0F17"
            strokeWidth={1.5}
          />
        )}
      </g>
    );
  };

  // Custom bar label
  const renderCustomBarLabel = (props: {
    x?: unknown;
    y?: unknown;
    width?: unknown;
    value?: unknown;
  }) => {
    const x = Number(props.x ?? 0);
    const y = Number(props.y ?? 0);
    const width = Number(props.width ?? 0);
    const value = Number(props.value ?? 0);
    return (
      <text
        x={x + width + 4}
        y={y + 10}
        fill="var(--muted)"
        fontSize={10}
        fontFamily="system-ui"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        {value.toFixed(1)}%
      </text>
    );
  };

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: Array<{ name: string; value: number; color: string }>;
    label?: string;
  }) => {
    if (!active || !payload?.length) return null;
    return (
      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          padding: "8px 12px",
          fontSize: 12,
        }}
      >
        <div style={{ color: "var(--text)", fontWeight: 600, marginBottom: 4 }}>{getName(label ?? "")}</div>
        {payload.map((p) => (
          <div key={p.name} style={{ color: p.color }}>
            {p.name}: {p.value.toFixed(1)}%
          </div>
        ))}
      </div>
    );
  };

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3"
        style={{ color: "var(--text)" }}
      >
        Title Race
      </h2>

      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "12px 16px",
          marginBottom: 12,
        }}
      >
        <div className="flex items-center gap-4 mb-3 text-xs" style={{ color: "var(--muted)" }}>
          <span>
            <span
              className="inline-block w-3 h-3 rounded-sm mr-1.5"
              style={{ background: "var(--green)", verticalAlign: "middle" }}
            />
            Model probability
          </span>
          {hasMarket && (
            <span>
              <span
                className="inline-block w-2 h-2 rounded-full mr-1.5"
                style={{ background: "var(--gold)", verticalAlign: "middle" }}
              />
              Market implied
            </span>
          )}
        </div>

        <ResponsiveContainer width="100%" height={Math.max(260, top14.length * 26)}>
          <BarChart
            data={barData}
            layout="vertical"
            margin={{ top: 6, right: 60, left: 0, bottom: 6 }}
            barCategoryGap="18%"
          >
            <XAxis
              type="number"
              domain={[0, "auto"]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="id"
              width={140}
              interval={0}
              tick={(props: { x?: number | string; y?: number | string; payload?: { value?: string } }) => {
                const id = props.payload?.value ?? "";
                const yy = Number(props.y);
                const url = flagUrl(id);
                return (
                  <g>
                    {url && (
                      <image
                        href={url}
                        x={2}
                        y={yy - 6.5}
                        width={18}
                        height={13}
                        preserveAspectRatio="xMidYMid meet"
                      />
                    )}
                    <text
                      x={url ? 26 : 4}
                      y={yy + 4}
                      textAnchor="start"
                      fill="var(--text)"
                      fontSize={12.5}
                      fontFamily="'Barlow Condensed', system-ui"
                    >
                      {getName(id)}
                    </text>
                  </g>
                );
              }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
            <Bar
              dataKey="model"
              name="Model"
              label={renderCustomBarLabel}
              shape={BarWithMarketDot}
              isAnimationActive={false}
            >
              {barData.map((entry, i) => (
                <Cell key={entry.id} fill={teamColor(entry.id, i)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* History line chart */}
      <div
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "12px 16px",
        }}
      >
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div
            className="font-heading font-semibold text-sm uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            P(Title) Over Time — Top 8
          </div>
          {leader && (
            <div className="flex items-center gap-1.5 text-xs" style={{ color: "var(--gold)" }}>
              <svg width={12} height={12} viewBox="0 0 12 12" fill="none">
                <line x1="0" y1="6" x2="12" y2="6" stroke="var(--gold)" strokeWidth="1.5" strokeDasharray="3 2" />
              </svg>
              Leader ({getName(leader.id)}) — {leaderPct.toFixed(1)}%
            </div>
          )}
        </div>

        {lineData.length < 2 ? (
          <div style={{ color: "var(--muted)", fontSize: 12, padding: "8px 0" }}>
            {lineData.length === 0
              ? "No history data yet."
              : "Only one data point so far — history will appear after the next update."}
          </div>
        ) : null}

        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={lineData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="ts"
              tickFormatter={fmtShortDate}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              minTickGap={60}
            />
            <YAxis
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: "var(--muted)", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toFixed(1)}%`,
                getName(String(name)),
              ]}
              contentStyle={{
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: "var(--muted)" }}
            />
            <Legend
              formatter={(value) => (
                <span
                  className="inline-flex items-center gap-1"
                  style={{ color: "var(--muted)", fontSize: 11 }}
                >
                  <Flag id={String(value)} h={10} /> {getName(String(value))}
                </span>
              )}
            />
            {leader && leaderPct > 0 && (
              <ReferenceLine
                y={leaderPct}
                stroke="var(--gold)"
                strokeDasharray="4 3"
                strokeWidth={1}
                strokeOpacity={0.45}
              />
            )}
            {top8.map((tid, i) => (
              <Line
                key={tid}
                type="monotone"
                dataKey={tid}
                stroke={teamColor(tid, i)}
                strokeWidth={tid === leader?.id ? 2.5 : 1.5}
                dot={lineData.length === 1 ? { r: 4 } : false}
                activeDot={{ r: 4 }}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
