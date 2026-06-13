"""Pipeline entry point. Run from repo root or pipeline/:

    python pipeline/refresh.py [--nsims 50000] [--no-weather] [--seed N]

Writes out/forecast.json and appends out/history.csv.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wc26 import forecast


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsims", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-weather", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    fc = forecast.run(nsims=args.nsims, seed=args.seed,
                      fetch_weather=not args.no_weather)
    top = fc["teams"][:8]
    print(f"forecast generated in {time.time() - t0:.1f}s "
          f"({fc['nsims']} sims, source: {fc['results_source']})")
    for t in top:
        print(f"  {t['id']}  P(title)={t['p_title']:.3f}  "
              f"P(final)={t['p_final']:.3f}  elo={t['elo']}")
    # sanity: title probabilities must sum to 1
    s = sum(t["p_title"] for t in fc["teams"])
    assert abs(s - 1.0) < 1e-6, f"title probs sum to {s}"
    print("sanity: title probs sum to 1.0 OK")


if __name__ == "__main__":
    main()
