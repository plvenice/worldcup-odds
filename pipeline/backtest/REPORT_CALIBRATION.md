# Calibration Temperature — Out-of-Sample Fit (2018 ↔ 2022)

Temperature T>1 softens the model toward the base rate. Fit on one World Cup, tested on the other (never seen during fitting).

## Cross-validation (fit on one, test on the other)

| Fit on | T | Tested on | Brier T=1 | Brier T | Log-loss T=1 | Log-loss T | ECE T=1 | ECE T |
|---|---|---|---|---|---|---|---|---|
| 2018 | 1.40 | 2022 | 0.6363 | **0.6304** | 1.0949 | **1.0648** | 6.4pp | **6.4pp** |
| 2022 | 2.40 | 2018 | 0.5670 | **0.5695** | 0.9591 | **0.9635** | 6.7pp | **5.8pp** |

## Temperature sweep (pooled 2018+2022)

| T | Brier | Skill vs uniform | Log-loss | 700-Elo favorite wins |
|---|---|---|---|---|
| 1.00 | 0.6016 | 9.8% | 1.0270 | 90% |
| 1.15 | 0.5992 | 10.1% | 1.0179 | 88% |
| 1.25 | 0.5982 | 10.3% | 1.0138 | 87% |
| 1.40 | 0.5973 | 10.4% | 1.0096 | 86% |
| 1.60 | 0.5969 | 10.5% | 1.0064 | 84% |
| 1.94 | 0.5974 | 10.4% | 1.0049 | 82% |
| 2.40 | 0.5992 | 10.1% | 1.0067 | 80% |

## Production temperature (shipped): **T = 1.40**
Chosen at the Brier-skill plateau (~10.4%, essentially the max) because it keeps a 700-Elo favorite at ~86% (historically right) instead of over-softening to ~80%. It is also the value an independent 2018 fit produced, which improved 2022 out-of-sample — so it generalises rather than chasing 2022's upsets.

| Tournament | Brier T=1 → T | Log-loss T=1 → T | ECE T=1 → T |
|---|---|---|---|
| 2018 | 0.5670 → **0.5642** | 0.9591 → **0.9543** | 6.7 → **7.5pp** |
| 2022 | 0.6363 → **0.6304** | 1.0949 → **1.0648** | 6.4 → **6.4pp** |

## Reliability, pooled 2018+2022 (mean predicted → observed)

| Band | n | T=1 | T=1.40 |
|---|---|---|---|
| 0%–10% | 4 | 7%→75% | 9%→100% |
| 10%–20% | 39 | 15%→15% | 17%→17% |
| 20%–30% | 136 | 26%→21% | 24%→20% |
| 30%–40% | 24 | 35%→33% | 35%→32% |
| 40%–50% | 34 | 45%→56% | 45%→53% |
| 50%–70% | 47 | 58%→64% | 57%→65% |
| 70%–101% | 4 | 77%→25% | 75%→0% |

- Pooled Brier skill vs uniform: **9.8% → 10.4%**
- Set `MODEL_TEMPERATURE = 1.40` in pipeline/wc26/matchmodel.py
