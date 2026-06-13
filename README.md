# worldcup-odds

Real-time probability model and dashboard for the 2026 FIFA World Cup.

## How it works

```
GitHub Actions (every 15 min)
  -> pipeline/refresh.py
       fixtures + results  (Wikipedia group pages; API-Football planned)
       betting market      (The Odds API, optional, 2 pulls/day)
       weather             (Open-Meteo, free)
       -> Elo (live, replayed from real results)
       -> Dixon-Coles match model + factor adjustments
          (host, rest, travel, altitude, heat, surface, availability)
       -> 50k-sim Monte Carlo of the remaining tournament
          (FIFA tiebreakers, third-place ranking, 2026 R32 bracket)
       -> forecast.json + history.csv
  -> force-pushed to the `data` branch
web/ (Next.js on Vercel) reads the data branch via raw.githubusercontent.com
```

The running system makes zero LLM calls; it is pure Python + JS.

## Key outputs (forecast.json)

- Per team: P(title), P(reach each round), group-finish probabilities
- Per upcoming match: win/draw/loss probabilities, factor attribution, and
  **leverage** — how much each outcome swings every affected team's
  P(title) and P(advance), computed by conditioning the simulation set
- Group standings with full FIFA tiebreakers

## Run locally

```
pip install -r pipeline/requirements.txt
python pipeline/refresh.py --nsims 20000
python -m pytest pipeline/tests
```

## Configuration (all optional)

| Env var / secret | Purpose |
|---|---|
| `ODDS_API_KEY` | The Odds API key — adds the market-implied line to charts |
| `API_FOOTBALL_KEY` | planned: lineups, injuries, live in-match data |

## Honest limitations

- Third-place R32 slot assignment uses a constraint-respecting deterministic
  matching; FIFA's annexed 495-row table may pick a different feasible
  assignment in some combinations (`data/third_place_table.json` overrides
  when present).
- Injury data is manual (`data/availability_overrides.json`) until
  API-Football is wired in.
- Knockout heat/weather not yet modeled (group stage only).
