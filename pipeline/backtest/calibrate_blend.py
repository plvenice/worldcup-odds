"""Calibrate the market blend weight from live 2026 WC predictions.

Reads out/blend_log.json (written by forecast.py on every pipeline run)
for fixtures that were priced before kick-off AND whose result is now
known. Sweeps blend weights 0.0–1.0 in 0.05 steps, scores each against
the actual outcomes, and writes the optimal weight to
out/blend_optimum.json. forecast.py reads that file on the next run.

Run manually after each round:  python pipeline/backtest/calibrate_blend.py

The tuned weight takes effect once MIN_SAMPLES completed priced matches
exist. Before that the pipeline uses the principled default (0.65).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wc26 import data

BLEND_LOG   = data.ROOT / "out" / "blend_log.json"
BLEND_OPT   = data.ROOT / "out" / "blend_optimum.json"
MIN_SAMPLES = 10
GRID        = [round(i * 0.05, 2) for i in range(21)]  # 0.00 .. 1.00


def _brier(entries, weight):
    total = 0.0
    for e in entries:
        m      = e["model_probs"]
        k      = e["market_probs"]
        actual = e["actual"]
        bl     = [weight * k[j] + (1 - weight) * m[j] for j in range(3)]
        s      = sum(bl)
        bl     = [b / s for b in bl]
        total += sum((bl[j] - (1.0 if j == actual else 0.0)) ** 2 for j in range(3))
    return total / len(entries)


def main():
    if not BLEND_LOG.exists():
        print("No blend_log.json — run the pipeline with ODDS_API_KEY set first.")
        return

    log     = json.loads(BLEND_LOG.read_text(encoding="utf-8"))
    entries = log.get("entries", [])
    scored  = [
        e for e in entries
        if e.get("model_probs") and e.get("market_probs") and e.get("actual") is not None
    ]

    n = len(scored)
    print(f"Blend calibration: {n} completed priced fixtures "
          f"({len(entries) - n} awaiting result)")

    if n < MIN_SAMPLES:
        print(f"Need >= {MIN_SAMPLES} samples to trust calibration. Skipping weight update.")
        return

    results      = sorted([(w, _brier(scored, w)) for w in GRID], key=lambda x: x[1])
    best_w, best_b = results[0]

    print("\nBrier by blend weight (lower = better):")
    for w, b in sorted(results, key=lambda x: x[0]):
        print(f"  w={w:.2f}: {b:.4f}{'  <-- optimal' if w == best_w else ''}")
    print(f"\nOptimal : {best_w:.2f}  (Brier {best_b:.4f})")
    print(f"Default : 0.65  (Brier {_brier(scored, 0.65):.4f})")
    print(f"Pure model : {_brier(scored, 0.0):.4f}")
    print(f"Pure market: {_brier(scored, 1.0):.4f}")

    BLEND_OPT.parent.mkdir(exist_ok=True)
    BLEND_OPT.write_text(json.dumps({
        "weight":     best_w,
        "brier":      round(best_b, 5),
        "n":          n,
        "updated_at": datetime.utcnow().isoformat(),
    }), encoding="utf-8")
    print(f"\nWrote {BLEND_OPT}")


if __name__ == "__main__":
    main()
