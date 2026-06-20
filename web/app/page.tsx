"use client";

import { useState, useMemo } from "react";
import { useData } from "@/lib/useData";
import Header from "@/components/Header";
import LiveMatches from "@/components/LiveMatches";
import GamesToday from "@/components/GamesToday";
import TitleRaceChart from "@/components/TitleRaceChart";
import LeverageBoard from "@/components/LeverageBoard";
import Groups from "@/components/Groups";
import BracketView from "@/components/Bracket";
import InfoModal from "@/components/InfoModal";

const BASE_NAV = [
  {
    id: "title-race",
    label: "Title Race",
    icon: (
      <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
        <rect x="1" y="7" width="3" height="6" rx="1" fill="currentColor" />
        <rect x="5.5" y="4" width="3" height="9" rx="1" fill="currentColor" />
        <rect x="10" y="1" width="3" height="12" rx="1" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: "bracket",
    label: "Bracket",
    icon: (
      <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
        <rect x="1" y="2" width="4" height="2.5" rx="0.8" fill="currentColor" />
        <rect x="1" y="9.5" width="4" height="2.5" rx="0.8" fill="currentColor" />
        <rect x="9" y="5.75" width="4" height="2.5" rx="0.8" fill="currentColor" />
        <path d="M5 3.25 H7 V10.75 H5" stroke="currentColor" strokeWidth="1" fill="none" />
        <line x1="7" y1="7" x2="9" y2="7" stroke="currentColor" strokeWidth="1" />
      </svg>
    ),
  },
  {
    id: "groups",
    label: "Groups",
    icon: (
      <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
        <rect x="1" y="1" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.8" />
        <rect x="7.5" y="1" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.8" />
        <rect x="1" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.5" />
        <rect x="7.5" y="7.5" width="5.5" height="5.5" rx="1" fill="currentColor" opacity="0.5" />
      </svg>
    ),
  },
  {
    id: "leverage",
    label: "Leverage",
    icon: (
      <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
        <path d="M7 1 L8.5 5.5 H13 L9.5 8.5 L10.5 13 L7 10.5 L3.5 13 L4.5 8.5 L1 5.5 H5.5 Z" fill="currentColor" />
      </svg>
    ),
  },
];

const TODAY_NAV = {
  id: "today",
  label: "Today",
  icon: (
    <svg width={14} height={14} viewBox="0 0 14 14" fill="none">
      <rect x="1" y="2.5" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" fill="none" />
      <line x1="1" y1="6" x2="13" y2="6" stroke="currentColor" strokeWidth="1.2" />
      <line x1="4" y1="1" x2="4" y2="4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="10" y1="1" x2="10" y2="4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="7" cy="9.5" r="1.2" fill="currentColor" />
    </svg>
  ),
};

export default function HomePage() {
  const { forecast, history, loading, error, lastFetched, liveTitleUpdates, liveForecast, liveMatches } = useData();
  const [showInfo, setShowInfo] = useState(false);

  const hasTodayMatches = useMemo(() => {
    if (!forecast) return false;
    const d = new Date();
    const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    return forecast.matches.some((m) => m.date === today);
  }, [forecast]);

  const NAV_ITEMS = useMemo(
    () => hasTodayMatches ? [TODAY_NAV, ...BASE_NAV] : BASE_NAV,
    [hasTodayMatches]
  );

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg)" }}>
      <Header forecast={forecast} loading={loading} lastFetched={lastFetched} onInfoClick={() => setShowInfo(true)} />
      {showInfo && <InfoModal onClose={() => setShowInfo(false)} />}

      <main className="flex-1 max-w-7xl mx-auto w-full px-3 py-4 flex flex-col gap-8">
        <LiveMatches />

        {/* Section nav */}
        {forecast && (
          <nav className="flex items-center gap-1 flex-wrap">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className="flex items-center gap-1.5 text-xs font-heading font-semibold uppercase tracking-wide px-3 py-1.5 rounded-full transition-colors"
                style={{
                  color: "var(--muted)",
                  border: "1px solid var(--border)",
                  textDecoration: "none",
                  background: "var(--panel)",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.color = "var(--text)";
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--green)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.color = "var(--muted)";
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                }}
              >
                {item.icon}
                {item.label}
              </a>
            ))}
          </nav>
        )}

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
            <div id="today">
              <GamesToday forecast={forecast} liveMatches={liveMatches} />
            </div>
            <div id="title-race">
              <TitleRaceChart forecast={forecast} history={history} liveTitleUpdates={liveTitleUpdates} liveForecast={liveForecast} />
            </div>
            <div id="bracket">
              <BracketView forecast={forecast} />
            </div>
            <div id="groups">
              <Groups forecast={forecast} liveForecast={liveForecast} />
            </div>
            <div id="leverage">
              <LeverageBoard matches={forecast.matches} />
            </div>
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
