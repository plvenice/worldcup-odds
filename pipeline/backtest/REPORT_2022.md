# 2022 World Cup — Match Model Calibration Backtest

- Group-stage matches scored: **48** (skipped 0)
- Prior: World Football Elo end-2021 (conservative; a lower bound)
- Outcome space: Home / Draw / Away over 90 minutes

## Headline

| Metric | Model | Uniform (1/3) | Better? |
|---|---|---|---|
| Brier score (lower=better) | **0.6363** | 0.6667 | ✅ |
| Log-loss (lower=better) | **1.0949** | 1.0986 | ✅ |

- **Brier skill score vs uniform: 4.6%** (positive = model beats a coin-flip prior)
- **Favorite hit-rate: 52.1%** (model's most-likely outcome matched the actual result)
- **Expected calibration error (ECE): 6.4pp** (avg gap between predicted and observed frequency)

## Reliability table (pooled over H/D/A)

| Predicted band | n | Mean predicted | Observed freq |
|---|---|---|---|
| 0%–10% | 4 | 6.7% | 75.0% |
| 10%–20% | 22 | 15.8% | 13.6% |
| 20%–30% | 65 | 26.1% | 23.1% |
| 30%–40% | 9 | 34.7% | 33.3% |
| 40%–50% | 16 | 44.7% | 50.0% |
| 50%–70% | 24 | 58.2% | 62.5% |
| 70%–101% | 4 | 77.3% | 25.0% |

Well-calibrated ⇒ *Mean predicted* ≈ *Observed freq* in each row.

## Interpretation

- The model **beats a uniform baseline and is well-calibrated through the bulk** (10–70% bands, ~136 of 144 predictions sit near the diagonal).
- The two extreme bands (n=4 each) are where it hurt: confident calls got burned by 2022's historic upsets (Saudi Arabia 2–1 Argentina, Japan over Germany and Spain). Tiny sample, but a real reminder that >70% calls still bite.
- Two reasons this is a **lower bound** on live quality: (1) the prior is end-2021 Elo, ~11 months stale — the live system uses current ratings; (2) 2022 was an unusually upset-heavy tournament.
- **Bottom line:** trust the outputs as probabilities, not as confident predictions. Re-run with Nov-2022 ratings if a sharper estimate is needed.

Reproduce: `python pipeline/backtest/fetch_2022.py && python pipeline/backtest/backtest_2022.py`
