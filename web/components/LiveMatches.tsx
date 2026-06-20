"use client";

import { useEffect, useRef, useState } from "react";
import { LineChart, Line, ResponsiveContainer, YAxis } from "recharts";
import { Flag, getName } from "@/lib/flags";
import type { LiveMatch } from "@/lib/types";

// Set NEXT_PUBLIC_LIVE_URL to the Railway worker base URL (e.g.
// https://worldcup-odds-worker.up.railway.app) to activate the live view.
const LIVE_URL = process.env.NEXT_PUBLIC_LIVE_URL || "";
const POLL_MS = 20000;

interface LiveState {
  updated_at?: string;
  live: boolean;
  matches: LiveMatch[];
}

function Seg({ p, color }: { p: number; color: string }) {
  if (p < 0.005) return null;
  return (
    <div
      className="h-full flex items-center justify-center"
      style={{ width: `${p * 100}%`, background: color }}
    >
      {p > 0.12 && (
        <span style={{ fontSize: 10, fontWeight: 700, color: "#08130C" }} className="tabular">
          {(p * 100).toFixed(0)}
        </span>
      )}
    </div>
  );
}

function LiveCard({ m, worm }: { m: LiveMatch; worm: { p: number }[] }) {
  const hasProb = m.p_home != null;
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--red)",
        borderRadius: 10,
        padding: "10px 12px",
        minWidth: 280,
        flex: "1 1 300px",
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="flex items-center gap-1" style={{ color: "var(--red)", fontSize: 11, fontWeight: 700 }}>
          <span
            className="inline-block rounded-full"
            style={{ width: 7, height: 7, background: "var(--red)", animation: "pulse 1.4s infinite" }}
          />
          LIVE
        </span>
        <span className="tabular" style={{ color: "var(--text)", fontSize: 12 }}>
          {m.status === "HT" ? "HT" : `${m.minute}'`}
        </span>
        {m.group && (
          <span style={{ color: "var(--muted)", fontSize: 10 }}>Group {m.group}</span>
        )}
      </div>

      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Flag id={m.home} h={15} />
          <span className="truncate" style={{ color: "var(--text)", fontSize: 14, fontWeight: 600 }}>
            {getName(m.home)}
          </span>
        </div>
        <div
          className="font-heading tabular shrink-0"
          style={{ color: "var(--gold)", fontSize: 22, fontWeight: 700, letterSpacing: "0.05em" }}
        >
          {m.hg}–{m.ag}
        </div>
        <div className="flex items-center gap-1.5 min-w-0 justify-end">
          <span className="truncate text-right" style={{ color: "var(--text)", fontSize: 14, fontWeight: 600 }}>
            {getName(m.away)}
          </span>
          <Flag id={m.away} h={15} />
        </div>
      </div>

      {hasProb && (
        <>
          <div className="flex rounded overflow-hidden h-5 tabular">
            <Seg p={m.p_home!} color="var(--green)" />
            <Seg p={m.p_draw!} color="var(--draw)" />
            <Seg p={m.p_away!} color="var(--blue)" />
          </div>
          <div className="flex justify-between mt-0.5" style={{ color: "var(--muted)", fontSize: 10 }}>
            <span>win {(m.p_home! * 100).toFixed(0)}%</span>
            <span>draw {(m.p_draw! * 100).toFixed(0)}%</span>
            <span>win {(m.p_away! * 100).toFixed(0)}%</span>
          </div>
          {worm.length > 2 && (
            <div style={{ height: 40, marginTop: 6 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={worm} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
                  <YAxis domain={[0, 100]} hide />
                  <Line
                    type="monotone"
                    dataKey="p"
                    stroke="var(--green)"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function LiveMatches() {
  const [state, setState] = useState<LiveState | null>(null);
  const worms = useRef<Record<string, { p: number }[]>>({});

  useEffect(() => {
    if (!LIVE_URL) return;
    let stop = false;
    const load = async () => {
      try {
        const r = await fetch(`${LIVE_URL.replace(/\/$/, "")}/live.json`, { cache: "no-store" });
        const j: LiveState = await r.json();
        for (const m of j.matches ?? []) {
          if (m.p_home != null) {
            const key = `${m.home}-${m.away}`;
            const arr = (worms.current[key] = worms.current[key] ?? []);
            const last = arr[arr.length - 1];
            if (!last || Math.abs(last.p - m.p_home * 100) > 0.01) {
              arr.push({ p: m.p_home * 100 });
              if (arr.length > 200) arr.shift();
            }
          }
        }
        if (!stop) setState(j);
      } catch {
        /* worker unreachable — stay hidden */
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, []);

  if (!LIVE_URL || !state || !state.live || !state.matches?.length) return null;

  return (
    <section>
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.25}}`}</style>
      <h2
        className="font-heading font-bold text-lg uppercase tracking-wider mb-3 flex items-center gap-2"
        style={{ color: "var(--text)" }}
      >
        <span style={{ color: "var(--red)" }}>● Live Now</span>
        <span className="font-normal text-sm" style={{ color: "var(--muted)" }}>
          win probability updating in-match
        </span>
      </h2>
      <div className="flex flex-wrap gap-3">
        {state.matches.map((m) => (
          <LiveCard key={`${m.home}-${m.away}`} m={m} worm={worms.current[`${m.home}-${m.away}`] ?? []} />
        ))}
      </div>
    </section>
  );
}
