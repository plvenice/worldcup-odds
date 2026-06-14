"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type {
  Forecast,
  TeamDist,
  BracketR32Match,
  BracketLaterMatch,
  BracketFinal,
  BracketSlot,
} from "@/lib/types";
import { Flag, getName } from "@/lib/flags";

interface Props {
  forecast: Forecast;
}

// Venue lookup (bracket matches only — 31 knockout venues)
const VENUE: Record<string, { name: string; city: string }> = {
  azteca:      { name: "Estadio Azteca",         city: "Mexico City" },
  akron:       { name: "Estadio Akron",           city: "Guadalajara" },
  bbva:        { name: "Estadio BBVA",            city: "Monterrey" },
  bmo:         { name: "BMO Field",               city: "Toronto" },
  bcplace:     { name: "BC Place",                city: "Vancouver" },
  sofi:        { name: "SoFi Stadium",            city: "Inglewood" },
  levis:       { name: "Levi's Stadium",          city: "Santa Clara" },
  lumen:       { name: "Lumen Field",             city: "Seattle" },
  att:         { name: "AT&T Stadium",            city: "Arlington" },
  nrg:         { name: "NRG Stadium",             city: "Houston" },
  arrowhead:   { name: "Arrowhead Stadium",       city: "Kansas City" },
  mercedesbenz:{ name: "Mercedes-Benz Stadium",   city: "Atlanta" },
  hardrock:    { name: "Hard Rock Stadium",       city: "Miami Gardens" },
  metlife:     { name: "MetLife Stadium",         city: "East Rutherford" },
  lincoln:     { name: "Lincoln Financial Field", city: "Philadelphia" },
  gillette:    { name: "Gillette Stadium",        city: "Foxborough" },
};

function fmtDate(iso: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// Layout constants (px)
const SLOT_W    = 148;   // col 0 node width
const SLOT_H    = 40;    // col 0 node height — must be ≤ SLOT_ROW_H
const MATCH_W   = 162;   // col 1+ node width
const MATCH_H   = 72;    // col 1+ node height (3 teams)
const SLOT_ROW_H = 44;   // vertical pitch between slot leaves (≥ SLOT_H)
const COL_GAP   = 28;
const PAD_TOP   = 26;
const PAD_LEFT  = 4;

type ColRound = "slot" | "r32" | "r16" | "qf" | "sf" | "final";
const COL_ROUNDS: ColRound[] = ["slot", "r32", "r16", "qf", "sf", "final"];
const COL_LABELS: Record<ColRound, string> = {
  slot: "Slots", r32: "Rd. of 32", r16: "Rd. of 16",
  qf: "Quarters", sf: "Semis", final: "Final",
};

function colX(col: number): number {
  if (col === 0) return PAD_LEFT;
  return PAD_LEFT + SLOT_W + COL_GAP + (col - 1) * (MATCH_W + COL_GAP);
}
function colW(col: number): number {
  return col === 0 ? SLOT_W : MATCH_W;
}

function slotDesc(s: BracketSlot): string {
  if (s.type === "W") return `1st · Group ${s.group}`;
  if (s.type === "R") return `2nd · Group ${s.group}`;
  return `3rd · ${(s.allowed ?? []).join("")}`;
}

type NodeId = string;

interface BNode {
  id: NodeId;
  round: ColRound;
  col: number;
  dist: TeamDist[];
  feeders: NodeId[];
  x: number;
  y: number;
  w: number;
  h: number;
  label?: string;    // slot label or match label
  matchNum?: number; // for match nodes
  date?: string;
  venue?: string;
}

// Right-side detail panel shown when a node is selected
function DetailPanel({
  node,
  onClose,
}: {
  node: BNode;
  onClose: () => void;
}) {
  const isSlot = node.round === "slot";
  const venueData = node.venue ? VENUE[node.venue] : null;

  return (
    <div
      className="w-full md:w-[220px]"
      style={{
        flexShrink: 0,
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "10px 12px",
        alignSelf: "flex-start",
        position: "sticky",
        top: 0,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <div
            className="font-heading font-bold text-sm uppercase tracking-wide"
            style={{ color: "var(--text)" }}
          >
            {isSlot ? "Slot" : `Match ${node.matchNum ?? ""}`}
          </div>
          {node.label && (
            <div style={{ color: "var(--muted)", fontSize: 10.5, marginTop: 1 }}>
              {node.label}
            </div>
          )}
          {!isSlot && node.date && (
            <div style={{ color: "var(--muted)", fontSize: 10.5 }}>
              {fmtDate(node.date)}
              {venueData && ` · ${venueData.city}`}
            </div>
          )}
          {!isSlot && venueData && (
            <div style={{ color: "var(--muted)", fontSize: 9.5, opacity: 0.75 }}>
              {venueData.name}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--muted)",
            fontSize: 16,
            lineHeight: 1,
            padding: "0 2px",
            flexShrink: 0,
          }}
        >
          ×
        </button>
      </div>

      {/* Probability distribution */}
      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        <div style={{ color: "var(--muted)", fontSize: 9.5, marginBottom: 4 }}>
          {isSlot ? "Projected to fill this slot" : "Projected to advance"}
        </div>
        {node.dist.slice(0, 10).map((t, ti) => (
          <div
            key={t.team}
            className="flex items-center gap-1.5"
            style={{ marginBottom: ti < node.dist.length - 1 ? 3 : 0 }}
          >
            <Flag id={t.team} h={11} />
            <Link
              href={`/team?id=${t.team}`}
              className="truncate hover:underline"
              style={{
                color: ti === 0 ? "var(--text)" : "var(--muted)",
                fontSize: 11.5,
                fontWeight: ti === 0 ? 600 : 400,
                flex: 1,
                minWidth: 0,
              }}
              title={getName(t.team)}
            >
              {getName(t.team)}
            </Link>
            <span
              className="tabular shrink-0"
              style={{ color: ti === 0 ? "var(--gold)" : "var(--muted)", fontSize: 10.5 }}
            >
              {(t.p * 100).toFixed(1)}%
            </span>
          </div>
        ))}
        {node.dist.length > 10 && (
          <div style={{ color: "var(--muted)", fontSize: 9.5, marginTop: 4 }}>
            +{node.dist.length - 10} more teams
          </div>
        )}
      </div>
    </div>
  );
}

export default function BracketView({ forecast }: Props) {
  const { bracket } = forecast;
  const [selected, setSelected] = useState<NodeId | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const { nodes, totalW, totalH } = useMemo(() => {
    const byId = new Map<NodeId, BNode>();
    const add = (n: BNode) => byId.set(n.id, n);

    // Col 0: 32 slot leaf nodes (home + away for each R32 match)
    bracket.r32.forEach((m: BracketR32Match) => {
      add({
        id: `s-${m.match}-h`, round: "slot", col: 0,
        dist: m.home_dist, feeders: [],
        x: 0, y: 0, w: SLOT_W, h: SLOT_H,
        label: slotDesc(m.home_slot),
        date: m.date, venue: m.venue,
      });
      add({
        id: `s-${m.match}-a`, round: "slot", col: 0,
        dist: m.away_dist, feeders: [],
        x: 0, y: 0, w: SLOT_W, h: SLOT_H,
        label: slotDesc(m.away_slot),
        date: m.date, venue: m.venue,
      });
    });

    // Col 1: R32 match winner nodes
    bracket.r32.forEach((m: BracketR32Match) => {
      add({
        id: `m-${m.match}`, round: "r32", col: 1,
        dist: m.winner_dist,
        feeders: [`s-${m.match}-h`, `s-${m.match}-a`],
        x: 0, y: 0, w: MATCH_W, h: MATCH_H,
        matchNum: m.match, date: m.date, venue: m.venue,
        label: `Match ${m.match}`,
      });
    });

    // Cols 2–4: R16, QF, SF
    (["r16", "qf", "sf"] as const).forEach((rnd, ci) => {
      (bracket[rnd] as BracketLaterMatch[]).forEach((m) => {
        add({
          id: `m-${m.match}`, round: rnd, col: ci + 2,
          dist: m.winner_dist,
          feeders: (m.feeders ?? []).map((f) => `m-${f}`),
          x: 0, y: 0, w: MATCH_W, h: MATCH_H,
          matchNum: m.match, date: m.date, venue: m.venue,
          label: `Match ${m.match}`,
        });
      });
    });

    // Col 5: Final
    const fin = bracket.final as BracketFinal;
    const sfIds = (bracket.sf as BracketLaterMatch[]).map((m) => `m-${m.match}`);
    add({
      id: `m-${fin.match}`, round: "final", col: 5,
      dist: fin.winner_dist, feeders: sfIds,
      x: 0, y: 0, w: MATCH_W, h: MATCH_H,
      matchNum: fin.match, date: fin.date, venue: fin.venue,
      label: `Match ${fin.match}`,
    });

    // Walk final → collect slot leaves in bracket order
    const orderedSlots: NodeId[] = [];
    const walk = (id: NodeId) => {
      const n = byId.get(id);
      if (!n) return;
      if (n.feeders.length === 0) { orderedSlots.push(id); return; }
      n.feeders.forEach(walk);
    };
    walk(`m-${fin.match}`);

    // Assign y to leaves
    orderedSlots.forEach((id, i) => {
      byId.get(id)!.y = PAD_TOP + i * SLOT_ROW_H;
    });

    // Propagate y to internal nodes (centroid of feeder midpoints)
    const yOf = (id: NodeId): number => {
      const n = byId.get(id)!;
      if (n.feeders.length === 0) return n.y + n.h / 2;
      const ys = n.feeders.map(yOf);
      return ys.reduce((a, b) => a + b, 0) / ys.length;
    };
    byId.forEach((n) => {
      if (n.feeders.length > 0) n.y = yOf(n.id) - n.h / 2;
      n.x = colX(n.col);
    });

    const w = colX(5) + MATCH_W + 4;
    const lastSlot = byId.get(orderedSlots[orderedSlots.length - 1]);
    const h = (lastSlot ? lastSlot.y + lastSlot.h : 0) + 12;
    return { nodes: [...byId.values()], totalW: w, totalH: h };
  }, [bracket]);

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const selectedNode = selected ? byId.get(selected) ?? null : null;

  const onPath = (n: BNode) =>
    hovered != null && n.dist.some((d) => d.team === hovered);

  // Connector paths
  const connectors = nodes.flatMap((n) =>
    n.feeders.flatMap((fId) => {
      const child = byId.get(fId);
      if (!child) return [];
      const x1 = child.x + child.w;
      const y1 = child.y + child.h / 2;
      const x2 = n.x;
      const y2 = n.y + n.h / 2;
      const midX = (x1 + x2) / 2;
      const isLit = hovered != null && onPath(n) && onPath(child);
      return [{ d: `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`, isLit, id: `${fId}->${n.id}` }];
    })
  );

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-1"
        style={{ color: "var(--text)" }}
      >
        Bracket
      </h2>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        Each slot shows who is projected to fill it. Hover any node to trace that team; click for full odds, venue, and date.
      </p>

      <div className="flex flex-col gap-4 items-start md:flex-row">
        {/* Scrollable bracket */}
        <div className="overflow-auto pb-3 flex-1 min-w-0">
          <div style={{ position: "relative", width: totalW, height: totalH, minWidth: totalW }}>
            {/* Column headers */}
            {COL_ROUNDS.map((r, i) => (
              <div
                key={r}
                className="font-heading font-bold text-xs uppercase tracking-widest"
                style={{
                  position: "absolute",
                  left: colX(i), top: 0,
                  width: colW(i), textAlign: "center",
                  color: r === "final" ? "var(--gold)" : "var(--muted)",
                }}
              >
                {COL_LABELS[r]}
              </div>
            ))}

            {/* Connectors */}
            <svg
              width={totalW}
              height={totalH}
              style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}
            >
              {connectors.map((c) => (
                <path
                  key={c.id}
                  d={c.d}
                  fill="none"
                  stroke={c.isLit ? "var(--gold)" : "var(--border)"}
                  strokeWidth={c.isLit ? 2 : 1}
                  opacity={hovered != null && !c.isLit ? 0.18 : 0.85}
                />
              ))}
            </svg>

            {/* Nodes */}
            {nodes.map((n) => {
              const isSlot = n.round === "slot";
              const isFinal = n.round === "final";
              const isSelected = selected === n.id;
              const isLit = onPath(n);
              const isDim = hovered != null && !isLit;
              const top1 = n.dist[0];
              const top2 = n.dist[1];

              return (
                <div
                  key={n.id}
                  onClick={() => setSelected(isSelected ? null : n.id)}
                  onMouseEnter={() => setHovered(top1?.team ?? null)}
                  onMouseLeave={() => setHovered(null)}
                  style={{
                    position: "absolute",
                    left: n.x, top: n.y,
                    width: n.w, height: n.h,
                    background: isFinal
                      ? "rgba(245,195,66,0.07)"
                      : isSelected
                      ? "rgba(255,255,255,0.06)"
                      : "var(--panel)",
                    border: `1px solid ${
                      isSelected
                        ? "var(--green)"
                        : isLit
                        ? "var(--gold)"
                        : isFinal
                        ? "rgba(245,195,66,0.45)"
                        : "var(--border)"
                    }`,
                    borderRadius: isSlot ? 5 : 7,
                    padding: isSlot ? "3px 7px" : "5px 9px",
                    cursor: "pointer",
                    opacity: isDim ? 0.28 : 1,
                    transition: "opacity .12s, border-color .12s, background .12s",
                    overflow: "hidden",
                    boxSizing: "border-box",
                  }}
                >
                  {/* Slot label */}
                  {isSlot && n.label && (
                    <div style={{
                      color: "var(--muted)", fontSize: 8, fontWeight: 700,
                      letterSpacing: "0.05em", textTransform: "uppercase",
                      marginBottom: 1, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis",
                    }}>
                      {n.label}
                    </div>
                  )}

                  {/* Top team (all nodes) */}
                  {top1 ? (
                    <div className="flex items-center gap-1" style={{ overflow: "hidden" }}>
                      <Flag id={top1.team} h={isSlot ? 10 : 12} />
                      <span
                        className="truncate"
                        style={{
                          color: isFinal ? "var(--gold)" : "var(--text)",
                          fontSize: isSlot ? 10.5 : 12.5,
                          fontWeight: 600,
                          flex: 1,
                          minWidth: 0,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {getName(top1.team)}
                      </span>
                      <span className="tabular shrink-0" style={{ color: "var(--muted)", fontSize: isSlot ? 9.5 : 10.5, paddingLeft: 2 }}>
                        {(top1.p * 100).toFixed(0)}%
                      </span>
                    </div>
                  ) : (
                    <div style={{ color: "var(--muted)", fontSize: 11 }}>TBD</div>
                  )}

                  {/* 2nd + 3rd team rows (match nodes only, not slot nodes) */}
                  {!isSlot && top2 && (
                    <div className="flex items-center gap-1" style={{ marginTop: 2, overflow: "hidden" }}>
                      <Flag id={top2.team} h={10} />
                      <span className="truncate" style={{ color: "var(--muted)", fontSize: 10.5, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {getName(top2.team)}
                      </span>
                      <span className="tabular shrink-0" style={{ color: "var(--muted)", fontSize: 9.5, paddingLeft: 2 }}>
                        {(top2.p * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {!isSlot && n.dist[2] && (
                    <div className="flex items-center gap-1" style={{ marginTop: 2, overflow: "hidden" }}>
                      <Flag id={n.dist[2].team} h={10} />
                      <span className="truncate" style={{ color: "var(--muted)", fontSize: 10, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", opacity: 0.7 }}>
                        {getName(n.dist[2].team)}
                      </span>
                      <span className="tabular shrink-0" style={{ color: "var(--muted)", fontSize: 9, paddingLeft: 2, opacity: 0.7 }}>
                        {(n.dist[2].p * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        {selectedNode && (
          <DetailPanel node={selectedNode} onClose={() => setSelected(null)} />
        )}
      </div>
    </section>
  );
}
