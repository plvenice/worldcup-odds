"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Forecast, LiveMatch, Match } from "@/lib/types";
import { Flag, getName } from "@/lib/flags";
import { fmtPct, fmtMatchDate } from "@/lib/utils";

const STORAGE_KEY = "wc26_followed_team";

/** Reads/writes the followed team id in localStorage. Starts null and only
 * touches localStorage inside an effect, so the server-rendered export and
 * the first client render always agree (no hydration mismatch). Validity
 * against the live team list is checked by the caller, not here, since the
 * team list may not have loaded yet on the very first render. */
function useFollowedTeam() {
  const [team, setTeam] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTeam(localStorage.getItem(STORAGE_KEY));
    setReady(true);
  }, []);

  const follow = (id: string | null) => {
    setTeam(id);
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  };

  return { team, ready, follow };
}

function verdict(p: number): { text: string; color: string } {
  if (p >= 0.55) return { text: "Favored", color: "var(--green)" };
  if (p >= 0.45) return { text: "Even matchup", color: "var(--muted)" };
  return { text: "Underdog", color: "var(--blue)" };
}

function Picker({ forecast, onPick }: { forecast: Forecast; onPick: (id: string) => void }) {
  const options = forecast.teams
    .map((t) => ({ id: t.id, name: getName(t.id) }))
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div
      className="flex items-center gap-3 flex-wrap"
      style={{ background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 12, padding: "12px 16px" }}
    >
      <span className="font-heading font-semibold text-sm uppercase tracking-wide" style={{ color: "var(--text)" }}>
        Follow a team
      </span>
      <span style={{ color: "var(--muted)", fontSize: 12 }}>
        Pin their next match and odds to the top of the page.
      </span>
      <select
        defaultValue=""
        onChange={(e) => {
          if (e.target.value) onPick(e.target.value);
        }}
        style={{
          background: "var(--bg)",
          color: "var(--text)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: "4px 8px",
          fontSize: 13,
          marginLeft: "auto",
        }}
      >
        <option value="" disabled>
          Choose a team…
        </option>
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function LiveRow({ live, team }: { live: LiveMatch; team: string }) {
  const isHome = live.home === team;
  const opp = isHome ? live.away : live.home;
  const pFor = isHome ? live.p_home : live.p_away;
  return (
    <div className="flex items-center gap-2 flex-wrap" style={{ fontSize: 13 }}>
      <span className="inline-flex items-center gap-1" style={{ color: "var(--red)", fontWeight: 700, fontSize: 11 }}>
        <span className="inline-block rounded-full" style={{ width: 6, height: 6, background: "var(--red)" }} />
        LIVE {live.status === "HT" ? "HT" : `${live.minute}'`}
      </span>
      <span className="inline-flex items-center gap-1" style={{ color: "var(--text)" }}>
        vs <Flag id={opp} h={13} /> {getName(opp)}
      </span>
      <span className="font-heading font-bold tabular" style={{ color: "var(--gold)" }}>
        {live.hg}–{live.ag}
      </span>
      {pFor != null && (
        <span style={{ color: "var(--muted)" }}>· {fmtPct(pFor)} to win right now</span>
      )}
    </div>
  );
}

function NextMatchRow({ match, team }: { match: Match; team: string }) {
  const isHome = match.home === team;
  const opp = isHome ? match.away : match.home;
  const probs = match.probs;
  const pFor = probs ? (isHome ? probs.home : probs.away) : null;
  const v = pFor != null ? verdict(pFor) : null;

  return (
    <div className="flex items-center gap-2 flex-wrap" style={{ fontSize: 13 }}>
      <span style={{ color: "var(--muted)" }}>Next: {fmtMatchDate(match.date)}</span>
      <span className="inline-flex items-center gap-1" style={{ color: "var(--text)" }}>
        vs <Flag id={opp} h={13} /> {getName(opp)}
      </span>
      {v && pFor != null && (
        <span style={{ color: v.color }}>
          · {v.text} ({fmtPct(pFor)})
        </span>
      )}
    </div>
  );
}

function StatusLine({ pAdvance }: { pAdvance: number }) {
  if (pAdvance >= 0.99) {
    return (
      <span style={{ color: "var(--green)", fontSize: 13 }}>
        Group stage done — through to the knockout rounds.
      </span>
    );
  }
  if (pAdvance <= 0.01) {
    return <span style={{ color: "var(--muted)", fontSize: 13 }}>Eliminated in the group stage.</span>;
  }
  return (
    <span style={{ color: "var(--muted)", fontSize: 13 }}>
      Group stage done — still waiting on other results to confirm advancement.
    </span>
  );
}

interface Props {
  forecast: Forecast | null;
  liveMatches?: LiveMatch[];
}

export default function FollowedTeam({ forecast, liveMatches = [] }: Props) {
  const { team, ready, follow } = useFollowedTeam();

  if (!forecast || !ready) return null;

  if (!team) {
    return <Picker forecast={forecast} onPick={follow} />;
  }

  const t = forecast.teams.find((x) => x.id === team);
  if (!t) return <Picker forecast={forecast} onPick={follow} />;

  const rank = forecast.teams.findIndex((x) => x.id === team) + 1;
  const live = liveMatches.find((lm) => lm.home === team || lm.away === team);

  const remaining = forecast.matches
    .filter((m) => !m.played && (m.home === team || m.away === team))
    .sort((a, b) => {
      const ka = `${a.date}T${a.time_utc ?? "99:99"}`;
      const kb = `${b.date}T${b.time_utc ?? "99:99"}`;
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });
  const next = remaining[0];

  return (
    <div
      style={{
        background: "var(--panel)",
        border: `1px solid ${live ? "var(--red)" : "var(--gold)"}`,
        borderRadius: 12,
        padding: "12px 16px",
      }}
    >
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <Link
          href={`/team?id=${team}`}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          style={{ textDecoration: "none" }}
        >
          <Flag id={team} h={20} />
          <span className="font-heading font-bold text-base" style={{ color: "var(--text)" }}>
            {getName(team)}
          </span>
          <span style={{ color: "var(--muted)", fontSize: 11 }}>#{rank} by title odds</span>
        </Link>
        <div className="flex items-center gap-3" style={{ fontSize: 11 }}>
          <span style={{ color: "var(--muted)" }}>
            Title chance <span style={{ color: "var(--gold)", fontWeight: 600 }}>{fmtPct(t.p_title)}</span>
          </span>
          <button
            onClick={() => follow(null)}
            style={{
              background: "none",
              border: "none",
              color: "var(--muted)",
              cursor: "pointer",
              fontSize: 11,
              textDecoration: "underline",
              padding: 0,
            }}
          >
            change
          </button>
        </div>
      </div>

      <div className="mt-2">
        {live ? (
          <LiveRow live={live} team={team} />
        ) : next ? (
          <NextMatchRow match={next} team={team} />
        ) : (
          <StatusLine pAdvance={t.p_advance} />
        )}
      </div>
    </div>
  );
}
