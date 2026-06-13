"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type {
  Forecast,
  TeamDist,
  BracketR32Match,
  BracketLaterMatch,
  BracketFinal,
} from "@/lib/types";
import { Flag, getName } from "@/lib/flags";

interface Props {
  forecast: Forecast;
}

// Layout constants (px)
const NODE_W = 170;
const NODE_H = 42;
const COL_W = 200;
const ROW_H = 46;
const PAD_TOP = 30;
const PAD_LEFT = 4;

type Round = "r32" | "r16" | "qf" | "sf" | "final";
const ROUND_ORDER: Round[] = ["r32", "r16", "qf", "sf", "final"];
const ROUND_LABEL: Record<Round, string> = {
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarterfinals",
  sf: "Semifinals",
  final: "Final",
};

interface Node {
  match: number;
  round: Round;
  col: number;
  date?: string;
  winner: TeamDist[];
  feeders: number[]; // child match numbers (empty for r32)
  x: number;
  y: number; // top-left of node box
}

export default function BracketView({ forecast }: Props) {
  const { bracket } = forecast;
  const [hovered, setHovered] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  const { nodes, height, width } = useMemo(() => {
    const byMatch = new Map<number, Node>();

    const add = (
      match: number,
      round: Round,
      col: number,
      winner: TeamDist[],
      feeders: number[],
      date?: string
    ) => {
      byMatch.set(match, { match, round, col, winner, feeders, date, x: 0, y: 0 });
    };

    bracket.r32.forEach((m: BracketR32Match) =>
      add(m.match, "r32", 0, m.winner_dist, [], m.date)
    );
    (["r16", "qf", "sf"] as const).forEach((rnd, i) =>
      (bracket[rnd] as BracketLaterMatch[]).forEach((m) =>
        add(m.match, rnd, i + 1, m.winner_dist, m.feeders ?? [], m.date)
      )
    );
    const fin = bracket.final as BracketFinal;
    add(fin.match, "final", 4, fin.winner_dist, [101, 102], fin.date);

    // Order the R32 leaves by a depth-first walk from the final, so each
    // match's two feeders sit adjacent — this produces the classic bracket shape.
    const leaves: number[] = [];
    const walk = (match: number) => {
      const n = byMatch.get(match);
      if (!n) return;
      if (n.feeders.length === 0) {
        leaves.push(match);
        return;
      }
      n.feeders.forEach(walk);
    };
    walk(fin.match);

    // Assign y: leaves evenly spaced; internal nodes = midpoint of feeders.
    const leafY = new Map<number, number>();
    leaves.forEach((m, i) => leafY.set(m, PAD_TOP + i * ROW_H));

    const yOf = (match: number): number => {
      const n = byMatch.get(match)!;
      if (n.feeders.length === 0) return leafY.get(match)!;
      const ys = n.feeders.map(yOf);
      return ys.reduce((a, b) => a + b, 0) / ys.length;
    };

    byMatch.forEach((n) => {
      n.y = yOf(n.match);
      n.x = PAD_LEFT + n.col * COL_W;
    });

    const h = PAD_TOP + leaves.length * ROW_H + 8;
    const w = PAD_LEFT + 5 * COL_W;
    return { nodes: [...byMatch.values()], height: h, width: w };
  }, [bracket]);

  const nodeByMatch = useMemo(
    () => new Map(nodes.map((n) => [n.match, n])),
    [nodes]
  );

  const favorite = (n: Node) => n.winner[0]?.team;
  const onPath = (n: Node) => hovered != null && favorite(n) === hovered;

  // Connector paths: from each feeder's right edge to the child's left edge.
  const connectors: { d: string; lit: boolean }[] = [];
  for (const n of nodes) {
    for (const f of n.feeders) {
      const child = nodeByMatch.get(f);
      if (!child) continue;
      const x1 = child.x + NODE_W;
      const y1 = child.y + NODE_H / 2;
      const x2 = n.x;
      const y2 = n.y + NODE_H / 2;
      const midX = (x1 + x2) / 2;
      connectors.push({
        d: `M ${x1} ${y1} H ${midX} V ${y2} H ${x2} ${y2}`,
        lit: hovered != null && onPath(n) && onPath(child),
      });
    }
  }

  return (
    <section>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-1"
        style={{ color: "var(--text)" }}
      >
        Bracket
      </h2>
      <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
        Each slot shows the favorite to reach it. Hover a team to trace its
        projected path; tap a match for the full picture. Scroll to pan.
      </p>

      <div className="overflow-auto pb-3" style={{ maxWidth: "100%" }}>
        <div style={{ position: "relative", width, height, minWidth: width }}>
          {/* round headers */}
          {ROUND_ORDER.map((r, i) => (
            <div
              key={r}
              className="font-heading font-bold text-xs uppercase tracking-widest"
              style={{
                position: "absolute",
                left: PAD_LEFT + i * COL_W,
                top: 0,
                width: NODE_W,
                textAlign: "center",
                color: r === "final" ? "var(--gold)" : "var(--muted)",
              }}
            >
              {ROUND_LABEL[r]}
            </div>
          ))}

          {/* connectors */}
          <svg
            width={width}
            height={height}
            style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none" }}
          >
            {connectors.map((c, i) => (
              <path
                key={i}
                d={c.d}
                fill="none"
                stroke={c.lit ? "var(--gold)" : "var(--border)"}
                strokeWidth={c.lit ? 2 : 1}
                opacity={hovered != null && !c.lit ? 0.35 : 1}
              />
            ))}
          </svg>

          {/* nodes */}
          {nodes.map((n) => {
            const fav = n.winner[0];
            const second = n.winner[1];
            const isFinal = n.round === "final";
            const lit = onPath(n);
            const dim = hovered != null && !lit;
            const isOpen = expanded === n.match;
            return (
              <div
                key={n.match}
                onClick={() => setExpanded(isOpen ? null : n.match)}
                style={{
                  position: "absolute",
                  left: n.x,
                  top: n.y,
                  width: NODE_W,
                  minHeight: NODE_H,
                  background: isFinal ? "rgba(245,195,66,0.08)" : "var(--panel)",
                  border: `1px solid ${
                    lit ? "var(--gold)" : isFinal ? "var(--gold)" : "var(--border)"
                  }`,
                  borderRadius: 7,
                  padding: "4px 8px",
                  cursor: "pointer",
                  opacity: dim ? 0.4 : 1,
                  transition: "opacity .15s, border-color .15s",
                  zIndex: isOpen ? 20 : 1,
                  boxShadow: isOpen ? "0 6px 20px rgba(0,0,0,0.5)" : undefined,
                }}
              >
                {fav ? (
                  <div
                    className="flex items-center gap-1.5"
                    onMouseEnter={() => setHovered(fav.team)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <Flag id={fav.team} h={12} />
                    <Link
                      href={`/team?id=${fav.team}`}
                      className="font-heading font-semibold truncate hover:underline"
                      style={{ color: isFinal ? "var(--gold)" : "var(--text)", fontSize: 12.5 }}
                      title={getName(fav.team)}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {getName(fav.team)}
                    </Link>
                    <span
                      className="tabular ml-auto pl-1 shrink-0"
                      style={{ color: "var(--muted)", fontSize: 11 }}
                    >
                      {(fav.p * 100).toFixed(0)}%
                    </span>
                  </div>
                ) : (
                  <div style={{ color: "var(--muted)", fontSize: 11 }}>TBD</div>
                )}

                {second && !isOpen && (
                  <div className="flex items-center gap-1.5" style={{ opacity: 0.55 }}>
                    <Flag id={second.team} h={9} />
                    <span
                      className="truncate"
                      style={{ color: "var(--muted)", fontSize: 10.5 }}
                      title={getName(second.team)}
                    >
                      {getName(second.team)}
                    </span>
                    <span
                      className="tabular ml-auto pl-1 shrink-0"
                      style={{ color: "var(--muted)", fontSize: 10 }}
                    >
                      {(second.p * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                {isOpen && (
                  <div className="mt-1 pt-1" style={{ borderTop: "1px solid var(--border)" }}>
                    <div className="text-xs mb-1" style={{ color: "var(--muted)", fontSize: 9.5 }}>
                      #{n.match}
                      {n.date ? ` · ${n.date.slice(5)}` : ""} · full odds
                    </div>
                    {n.winner.slice(0, 6).map((t) => (
                      <div key={t.team} className="flex items-center gap-1.5">
                        <Flag id={t.team} h={9} />
                        <span className="truncate" style={{ color: "var(--text)", fontSize: 11 }}>
                          {getName(t.team)}
                        </span>
                        <span
                          className="tabular ml-auto pl-1 shrink-0"
                          style={{ color: "var(--muted)", fontSize: 10 }}
                        >
                          {(t.p * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
