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
} from "recharts";
import type { Forecast, HistoryRow, LiveForecast } from "@/lib/types";
import { flagUrl, getName, Flag } from "@/lib/flags";
import { fmtPct, fmtPctNum, fmtShortDate, getTimestamps, teamColor } from "@/lib/utils";

interface Props {
  forecast: Forecast;
  history: HistoryRow[];
  liveTitleUpdates?: Record<string, number>;
  liveForecast?: LiveForecast | null;
}

export default function TitleRaceChart({ forecast, history, liveTitleUpdates = {}, liveForecast }: Props) {
  const isLive = (liveForecast?.available ?? false) || Object.keys(liveTitleUpdates).length > 0;

  // Prefer the conditioned-MC resim (live_forecast.json) when available — it
  // re-simulates 5k paths from the current scoreline every 20 s.  Fall back to
  // the leverage approximation (title_updates in live.json), then to the static
  // forecast.json value.
  const teamsWithLive = forecast.teams.map((t) => ({
    ...t,
    p_title: liveForecast?.teams?.[t.id]?.p_title ?? liveTitleUpdates[t.id] ?? t.p_title,
  }));
  // Re-sort since live probabilities can reorder the top field.
  teamsWithLive.sort((a, b) => b.p_title - a.p_title);
  const top14 = teamsWithLive.slice(0, 14);
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

  // History line chart — top 8 teams
  const top8 = teamsWithLive.slice(0, 8).map((t) => t.id);
  const top8Set = new Set(top8);

  // O(1) lookup: ts → team → p_title (replaces O(n) find() inside map)
  const histLookup = new Map<string, Map<string, number>>();
  for (const h of history) {
    if (!top8Set.has(h.team)) continue;
    if (!histLookup.has(h.ts)) histLookup.set(h.ts, new Map());
    histLookup.get(h.ts)!.set(h.team, parseFloat(fmtPctNum(h.p_title)));
  }

  const allTimestamps = getTimestamps(history);

  // Stride-sample to ≤180 render points as history grows; always keep last point
  const MAX_RENDER_PTS = 180;
  const stride = Math.max(1, Math.ceil(allTimestamps.length / MAX_RENDER_PTS));
  const sampledTimestamps = allTimestamps.filter(
    (_, i) => i % stride === 0 || i === allTimestamps.length - 1
  );

  const lineData = sampledTimestamps.map((ts) => {
    const row: Record<string, number | string> = { ts };
    const teamMap = histLookup.get(ts);
    for (const tid of top8) {
      row[tid] = teamMap?.get(tid) ?? 0;
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
        x={x + width + 14}
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
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3 flex items-center gap-2"
        style={{ color: "var(--text)" }}
      >
        Title Race
        {isLive && (
          <span
            className="flex items-center gap-1 text-xs font-normal normal-case tracking-normal px-2 py-0.5 rounded-full"
            style={{ background: "rgba(255,77,77,0.15)", color: "var(--red)", border: "1px solid var(--red)" }}
          >
            <span
              className="inline-block rounded-full"
              style={{ width: 6, height: 6, background: "var(--red)", animation: "pulse 1.4s infinite" }}
            />
            live conditioned
          </span>
        )}
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
        <div
          className="font-heading font-semibold text-sm uppercase tracking-wide mb-3"
          style={{ color: "var(--muted)" }}
        >
          P(Title) Over Time — Top 8
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
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const sorted = [...payload].sort((a, b) => Number(b.value) - Number(a.value));
                return (
                  <div style={{ background: "#131A26", border: "1px solid #1E2939", borderRadius: 6, padding: "8px 12px", fontSize: 12 }}>
                    <div style={{ color: "#8B97A8", marginBottom: 4 }}>{fmtShortDate(String(label))}</div>
                    {sorted.map((p) => (
                      <div key={String(p.dataKey)} style={{ color: String(p.color), display: "flex", justifyContent: "space-between", gap: 16 }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                          <Flag id={String(p.dataKey)} h={10} /> {getName(String(p.dataKey))}
                        </span>
                        <span style={{ fontVariantNumeric: "tabular-nums" }}>{Number(p.value).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                );
              }}
              wrapperStyle={{ zIndex: 100, outline: "none" }}
            />
            <Legend
              content={() => (
                <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", paddingTop: 4 }}>
                  {top8.map((tid, i) => (
                    <span key={tid} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "var(--muted)" }}>
                      <span style={{ display: "inline-block", width: 16, height: 2, background: teamColor(tid, i), borderRadius: 1 }} />
                      <Flag id={tid} h={10} /> {getName(tid)}
                    </span>
                  ))}
                </div>
              )}
            />
            {top8.map((tid, i) => (
              <Line
                key={tid}
                type="monotone"
                dataKey={tid}
                stroke={teamColor(tid, i)}
                strokeWidth={2}
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
