"""Group standings with FIFA 2026 tiebreakers (scalar, exact).

Tiebreaker order (FIFA WC26 regulations Art. 13):
  1. points  2. goal difference  3. goals for
  4. head-to-head points among tied  5. h2h GD among tied  6. h2h GF among tied
  7. fair play points (not tracked -> skipped)  8. drawing of lots (random)

Used for: actual current standings, the exact-tie slow path inside the Monte
Carlo, and as the reference implementation for tests.
"""
import random


def table(team_ids, results):
    """results: list of (home_id, away_id, hg, ag) completed matches.
    Returns list of row dicts, unranked."""
    rows = {t: {"team": t, "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "gd": 0, "pts": 0} for t in team_ids}
    for h, a, hg, ag in results:
        if h not in rows or a not in rows:
            continue
        rh, ra = rows[h], rows[a]
        rh["played"] += 1; ra["played"] += 1
        rh["gf"] += hg; rh["ga"] += ag
        ra["gf"] += ag; ra["ga"] += hg
        if hg > ag:
            rh["won"] += 1; ra["lost"] += 1; rh["pts"] += 3
        elif hg < ag:
            ra["won"] += 1; rh["lost"] += 1; ra["pts"] += 3
        else:
            rh["drawn"] += 1; ra["drawn"] += 1; rh["pts"] += 1; ra["pts"] += 1
    for r in rows.values():
        r["gd"] = r["gf"] - r["ga"]
    return [rows[t] for t in team_ids]


def rank(team_ids, results, rng=None):
    """Returns team ids ranked 1st..4th applying full tiebreakers."""
    rng = rng or random.Random(0)
    rows = {r["team"]: r for r in table(team_ids, results)}

    def base_key(t):
        r = rows[t]
        return (r["pts"], r["gd"], r["gf"])

    ordered = sorted(team_ids, key=base_key, reverse=True)
    # resolve groups tied on the full base key via head-to-head mini-table
    out = []
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and base_key(ordered[j + 1]) == base_key(ordered[i]):
            j += 1
        tied = ordered[i:j + 1]
        if len(tied) > 1:
            tied = _resolve_h2h(tied, results, rng)
        out.extend(tied)
        i = j + 1
    return out


def _resolve_h2h(tied, results, rng):
    sub = [r for r in results if r[0] in tied and r[1] in tied]
    rows = {r["team"]: r for r in table(tied, sub)}

    def h2h_key(t):
        r = rows[t]
        return (r["pts"], r["gd"], r["gf"])

    # random jitter stands in for fair play + drawing of lots
    jitter = {t: rng.random() for t in tied}
    return sorted(tied, key=lambda t: (h2h_key(t), jitter[t]), reverse=True)


def rank_thirds(third_rows, rng=None):
    """Rank the 12 third-placed teams; top 8 advance.
    third_rows: list of row dicts (from table()) for each group's 3rd.
    Tiebreakers: pts, gd, gf, then lots (fair play not tracked)."""
    rng = rng or random.Random(0)
    jitter = {r["team"]: rng.random() for r in third_rows}
    ranked = sorted(third_rows,
                    key=lambda r: (r["pts"], r["gd"], r["gf"], jitter[r["team"]]),
                    reverse=True)
    return [r["team"] for r in ranked]
