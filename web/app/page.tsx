"use client";

import { useData } from "@/lib/useData";
import Header from "@/components/Header";
import LiveMatches from "@/components/LiveMatches";
import TitleRaceChart from "@/components/TitleRaceChart";
import LeverageBoard from "@/components/LeverageBoard";
import Groups from "@/components/Groups";
import BracketView from "@/components/Bracket";

export default function HomePage() {
  const { forecast, history, loading, error, lastFetched } = useData();

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      <Header forecast={forecast} loading={loading} lastFetched={lastFetched} />

      <main className="flex-1 max-w-7xl mx-auto w-full px-3 py-4 flex flex-col gap-8">
        <LiveMatches />

        {error && (
          <div
            className="rounded-lg px-4 py-3 text-sm"
            style={{ background: "rgba(255,92,92,0.1)", border: "1px solid var(--red)", color: "var(--red)" }}
          >
            Data error: {error}. Showing last known data.
          </div>
        )}

        {!forecast && loading && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div
              className="animate-spin w-8 h-8 rounded-full border-2"
              style={{ borderColor: "var(--border)", borderTopColor: "var(--green)" }}
            />
            <span style={{ color: "var(--muted)", fontSize: 13 }}>Loading forecast data…</span>
          </div>
        )}

        {forecast && (
          <>
            <TitleRaceChart forecast={forecast} history={history} />
            <LeverageBoard matches={forecast.matches} />
            <Groups forecast={forecast} />
            <BracketView forecast={forecast} />
          </>
        )}
      </main>

      <footer
        className="text-center py-3 text-xs"
        style={{
          color: "var(--muted)",
          borderTop: "1px solid var(--border)",
          background: "var(--panel)",
        }}
      >
        World Cup 2026 Probability Model · Monte Carlo simulation · Updates every 15 min ·{" "}
        <a
          href="https://github.com/plvenice/worldcup-odds"
          target="_blank"
          rel="noreferrer"
          className="hover:underline"
          style={{ color: "var(--green)" }}
        >
          github.com/plvenice/worldcup-odds
        </a>
      </footer>
    </div>
  );
}
