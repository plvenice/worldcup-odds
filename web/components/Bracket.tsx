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

// Layout constants (px)
const SLOT_W = 148;       // width of slot leaf nodes (col 0)
const SLOT_H = 54;        // min-height of slot nodes
const MATCH_W = 162;      // width of match winner nodes (cols 1–5)
const MATCH_H = 72;       // min-height of match nodes (3 teams)
const SLOT_ROW_H = 40;    // vertical pitch between slot leaves
const COL_GAP = 28;       // horizontal gap between column edges
const PAD_TOP = 26;       // space for column headers
const PAD_LEFT = 4;

type ColRound = "slot" | "r32" | "r16" | "qf" | "sf" | "final";
const COL_ROUNDS: ColRound[] = ["slot", "r32", "r16", "qf", "sf", "final"];
const COL_LABELS: Record<ColRound, string> = {
  slot: "Slots",
  r32: "Rd. of 32",
  r16: "Rd. of 16",
  qf: "Quarters",
  sf: "Semis",
  final: "Final",
};

function colX(col: number): number {
  // col 0 = slots (SLOT_W wide); col 1+ = match nodes (MATCH_W wide)
  if (col === 0) return PAD_LEFT;
  return PAD_LEFT + SLOT_W + COL_GAP + (col - 1) * (MATCH_W + COL_GAP);
}
function colW(col: number): number {
  return col === 0 ? SLOT_W : MATCH_W;
}

function slotDesc(s: BracketSlot): string {
  if (s.type === "W") return `1st · ${s.group}`;
  if (s.type === "R") return `2nd · ${s.group}`;
  // "T" = third place
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
  label?: string; // slot label ("1st · A", "2nd · B", "3rd · ABCD")
}

export default function BracketView({ forecast }: Props) {
  const { bracket } = forecast;
  const [hovered, setHovered] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<NodeId | null>(null);

  const { nodes, totalW, totalH } = useMemo(() => {
    const byId = new Map<NodeId, BNode>();
    const add = (n: BNode) => byId.set(n.id, n);

    // --- Col 0: 32 slot leaf nodes (home + away for each R32 match) ---
    bracket.r32.forEach((m: BracketR32Match) => {
      add({
        id: `s-${m.match}-h`, round: "slot", col: 0,
        dist: m.home_dist, feeders: [],
        x: 0, y: 0, w: SLOT_W, h: SLOT_H,
        label: slotDesc(m.home_slot),
      });
      add({
        id: `s-${m.match}-a`, round: "slot", col: 0,
        dist: m.away_dist, feeders: [],
        x: 0, y: 0, w: SLOT_W, h: SLOT_H,
        label: slotDesc(m.away_slot),
      });
    });

    // --- Col 1: R32 match winner nodes ---
    bracket.r32.forEach((m: BracketR32Match) => {
      add({
        id: `m-${m.match}`, round: "r32", col: 1,
        dist: m.winner_dist,
        feeders: [`s-${m.match}-h`, `s-${m.match}-a`],
        x: 0, y: 0, w: MATCH_W, h: MATCH_H,
      });
    });

    // --- Cols 2–4: R16, QF, SF ---
    (["r16", "qf", "sf"] as const).forEach((rnd, ci) => {
      (bracket[rnd] as BracketLaterMatch[]).forEach((m) => {
        add({
          id: `m-${m.match}`, round: rnd, col: ci + 2,
          dist: m.winner_dist,
          feeders: (m.feeders ?? []).map((f) => `m-${f}`),
          x: 0, y: 0, w: MATCH_W, h: MATCH_H,
        });
      });
    });

    // --- Col 5: Final ---
    const fin = bracket.final as BracketFinal;
    const sfIds = (bracket.sf as BracketLaterMatch[]).map((m) => `m-${m.match}`);
    add({
      id: `m-${fin.match}`, round: "final", col: 5,
      dist: fin.winner_dist,
      feeders: sfIds,
      x: 0, y: 0, w: MATCH_W, h: MATCH_H,
    });

    // Depth-first walk from final → collect slot leaves in bracket order
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

  // Hover: any node containing the hovered team is "on-path"
  const onPath = (n: BNode) =>
    hovered != null && n.dist.some((d) => d.team === hovered);

  // Connector paths: feeder right-edge → parent left-edge
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
        Each slot shows who is projected to fill it. Hover any node to trace that team through the draw; click to expand odds.
      </p>

      <div className="overflow-auto pb-3">
        <div style={{ position: "relative", width: totalW, height: totalH, minWidth: totalW }}>
          {/* Column headers */}
          {COL_ROUNDS.map((r, i) => (
            <div
              key={r}
              className="font-heading font-bold text-xs uppercase tracking-widest"
              style={{
                position: "absolute",
                left: colX(i),
                top: 0,
                width: colW(i),
                textAlign: "center",
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
            const isLit = onPath(n);
            const isDim = hovered != null && !isLit;
            const isOpen = expanded === n.id;
            const showN = isOpen ? 8 : isSlot ? 2 : 3;

            return (
              <div
                key={n.id}
                onClick={() => setExpanded(isOpen ? null : n.id)}
                onMouseEnter={() => setHovered(n.dist[0]?.team ?? null)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  position: "absolute",
                  left: n.x,
                  top: n.y,
                  width: n.w,
                  minHeight: n.h,
                  background: isFinal ? "rgba(245,195,66,0.07)" : "var(--panel)",
                  border: `1px solid ${
                    isLit
                      ? "var(--gold)"
                      : isFinal
                      ? "rgba(245,195,66,0.45)"
                      : "var(--border)"
                  }`,
                  borderRadius: isSlot ? 5 : 7,
                  padding: isSlot ? "3px 7px 4px" : "5px 9px",
                  cursor: "pointer",
                  opacity: isDim ? 0.28 : 1,
                  transition: "opacity .12s, border-color .12s",
                  zIndex: isOpen ? 20 : 1,
                  boxShadow: isOpen ? "0 6px 20px rgba(0,0,0,0.5)" : undefined,
                }}
              >
                {/* Slot label */}
                {isSlot && n.label && (
                  <div
                    style={{
                      color: "var(--muted)",
                      fontSize: 8.5,
                      fontWeight: 700,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      marginBottom: 2,
                    }}
                  >
                    {n.label}
                  </div>
                )}

                {n.dist.length === 0 ? (
                  <div style={{ color: "var(--muted)", fontSize: 11 }}>TBD</div>
                ) : (
                  n.dist.slice(0, showN).map((t, ti) => (
                    <div
                      key={t.team}
                      className="flex items-center gap-1"
                      style={{ marginBottom: ti < Math.min(showN, n.dist.length) - 1 ? 2 : 0 }}
                    >
                      <Flag id={t.team} h={isSlot ? 10 : 12} />
                      <Link
                        href={`/team?id=${t.team}`}
                        className="truncate hover:underline"
                        style={{
                          color:
                            isFinal && ti === 0
                              ? "var(--gold)"
                              : ti === 0
                              ? "var(--text)"
                              : "var(--muted)",
                          fontSize: isSlot ? 10.5 : ti === 0 ? 12.5 : 11,
                          fontWeight: ti === 0 ? 600 : 400,
                          flex: 1,
                          minWidth: 0,
                        }}
                        title={getName(t.team)}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {getName(t.team)}
                      </Link>
                      <span
                        className="tabular shrink-0"
                        style={{
                          color: ti === 0 ? "var(--text)" : "var(--muted)",
                          fontSize: isSlot ? 9.5 : 10.5,
                          paddingLeft: 3,
                        }}
                      >
                        {(t.p * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
