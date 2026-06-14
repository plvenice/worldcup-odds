"use client";

interface Props {
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3
        className="font-heading font-bold uppercase tracking-wider text-sm mb-2"
        style={{ color: "var(--gold)" }}
      >
        {title}
      </h3>
      <div style={{ color: "var(--text)", fontSize: 13, lineHeight: 1.65 }}>
        {children}
      </div>
    </div>
  );
}

export default function InfoModal({ onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)" }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl"
        style={{
          background: "var(--panel)",
          border: "1px solid var(--border)",
          padding: "28px 32px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2
              className="font-heading font-bold text-xl tracking-wide"
              style={{ color: "var(--gold)" }}
            >
              World Cup 2026 Probability Model
            </h2>
            <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 4 }}>
              A personal forecasting project. Not affiliated with FIFA.
            </p>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 ml-4 text-xl leading-none"
            style={{ color: "var(--muted)", background: "none", border: "none", cursor: "pointer" }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-col gap-6">
          <Section title="What this is">
            A self-built probabilistic model for the 2026 FIFA World Cup. It runs continuously
            in the cloud, updating every 15 minutes as results come in. Every number on this
            site comes from simulating the remaining tournament 50,000 times from the current
            state.
          </Section>

          <Section title="How the model works">
            <ol className="list-none flex flex-col gap-2 ml-0">
              {[
                ["Elo ratings", "Each team starts from a pre-tournament Elo rating and updates after every real result."],
                ["Expected goals", "For each remaining fixture, the Elo differential feeds into a Dixon-Coles model that produces expected goal rates (λ) for home and away. Situational adjustments apply: host advantage, altitude, rest days, travel distance, surface quality, and heat index."],
                ["Market blend", "Bookmaker match odds (via Odds API) are de-vigged and blended with the model at 65% market weight. Markets price the full group stage ahead."],
                ["Monte Carlo", "50,000 independent simulations sample scorelines from each fixture's probability matrix, rank every group, resolve third-place slots, and play out the bracket. Probabilities are the fraction of simulations in which each outcome occurs."],
              ].map(([term, desc]) => (
                <li key={term as string} style={{ paddingLeft: 0 }}>
                  <span className="font-semibold" style={{ color: "var(--green)" }}>{term}</span>
                  {" — "}
                  {desc}
                </li>
              ))}
            </ol>
          </Section>

          <Section title="What the numbers mean">
            <ul className="flex flex-col gap-1.5 list-none ml-0">
              {[
                ["P(title)", "Probability of winning the World Cup outright."],
                ["P(advance)", "Probability of reaching the Round of 32 from the group stage."],
                ["1st / 2nd / 3rd", "Breakdown of how a team advances: as group winner, runner-up, or best third-place finisher."],
                ["Leverage board", "Which upcoming group-stage matches matter most for title contention, ranked by how much the result shifts winner probabilities."],
              ].map(([term, desc]) => (
                <li key={term as string}>
                  <span className="font-semibold" style={{ color: "var(--gold)" }}>{term}</span>
                  {" — "}
                  {desc}
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Live matches">
            During a live match, a 5,000-path re-simulation runs every 20 seconds conditioned
            on the current score and minute elapsed. The affected group card goes green. Group
            advancement bars update in real time as the match unfolds. The title race chart
            updates continuously via a faster leverage-weighted calculation.
          </Section>

          <Section title="Calibration">
            Backtested on 2018 and 2022. The model is well-calibrated through the 10–70%
            range. Above 70%, treat predictions with humility: 2022 produced four major upsets
            in the group stage (Saudi Arabia over Argentina, Japan over Germany and Spain,
            Morocco's run to the semifinal) that the model and every other forecaster missed.
            A temperature scaling factor of T=1.40, fit out-of-sample across both tournaments,
            is applied to soften overconfident extreme predictions.
          </Section>

          <Section title="Data sources">
            <ul className="flex flex-col gap-1 list-none ml-0">
              {[
                ["Results", "Wikipedia (updates within minutes of full time)"],
                ["Live scores", "API-Football (polling every 20 seconds during matches)"],
                ["Market odds", "The Odds API (match h2h odds, up to 8 pulls/day)"],
                ["Weather", "Open-Meteo (heat index for fixtures within 8 days)"],
              ].map(([src, desc]) => (
                <li key={src as string}>
                  <span className="font-semibold" style={{ color: "var(--muted)" }}>{src}</span>
                  {" — "}
                  {desc}
                </li>
              ))}
            </ul>
          </Section>

          <p style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>
            Built for fun. Not a betting tool. Source:{" "}
            <a
              href="https://github.com/plvenice/worldcup-odds"
              target="_blank"
              rel="noreferrer"
              style={{ color: "var(--green)" }}
            >
              github.com/plvenice/worldcup-odds
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
