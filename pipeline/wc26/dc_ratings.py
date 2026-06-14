"""Poisson team-strength fitter: attack and defense ratings via EM.

Iterative proportional fitting (standard MLE for Poisson team-strength
models, Dixon & Coles 1997-style, without the tau correction — DC tau
is applied downstream in the score matrix).

Model (neutral-venue WC matches):
  goals_h ~ Poisson(attack[h] * defense[a] * mu)
  goals_a ~ Poisson(attack[a] * defense[h] * mu)

  attack[i]  = goals-scored-per-match vs average opponent (avg = 1.0)
  defense[i] = goals-conceded-per-match vs average opponent (avg = 1.0;
               LOWER defense = better — strong teams concede fewer goals)
  mu         = global mean goals-per-team-per-match (fixed from data)

Identifiability: geometric mean(attack) = 1.0; mu absorbs the scale.

Regularization: prior_games pseudo-matches pull each team toward its
Elo-implied prior. Teams with no observed data fall back entirely to Elo.
"""
import math


def _elo_strength(elo, median_elo, sigma=350.0):
    """Elo -> strength multiplier relative to the median team (= 1.0)."""
    return math.exp((elo - median_elo) / (sigma * 2.0))


def fit(matches, team_ids, elo_map, max_iter=500, tol=1e-8, prior_games=5):
    """Fit attack/defense from match results.

    matches    : iterable of {"home": id, "away": id, "hg": int, "ag": int}
    team_ids   : list of all team IDs to produce ratings for
    elo_map    : {team_id: float} used as regularization prior
    prior_games: pseudo-match weight anchoring sparse teams toward Elo

    Returns {"_mu": float, team_id: {"attack": float, "defense": float, "n": int}, ...}
    """
    n = len(team_ids)
    idx = {t: i for i, t in enumerate(team_ids)}
    median_elo = sorted(elo_map.values())[n // 2]

    ms = [
        (m["home"], m["away"], int(m["hg"]), int(m["ag"]))
        for m in matches
        if m.get("home") in idx and m.get("away") in idx
        and m.get("hg") is not None and m.get("ag") is not None
    ]

    gfor  = [0.0] * n
    gagn  = [0.0] * n
    games = [0] * n
    for h, a, hg, ag in ms:
        gfor[idx[h]] += hg;  gagn[idx[h]] += ag;  games[idx[h]] += 1
        gfor[idx[a]] += ag;  gagn[idx[a]] += hg;  games[idx[a]] += 1

    total_goals = sum(hg + ag for _, _, hg, ag in ms)
    total_slots = sum(games)
    mu = total_goals / total_slots if total_slots > 0 else 1.25

    ep      = [_elo_strength(elo_map.get(t, median_elo), median_elo) for t in team_ids]
    attack  = list(ep)
    defense = [1.0 / max(e, 0.05) for e in ep]

    for _ in range(max_iter):
        prev_a, prev_d = list(attack), list(defense)

        # update attack: MLE closed form with Elo prior pseudo-matches
        for i, t in enumerate(team_ids):
            num   = gfor[i] + prior_games * ep[i] * mu
            denom = prior_games * mu  # prior: average opponent defense = 1.0
            for h, a, hg, ag in ms:
                if h == t:
                    denom += defense[idx[a]] * mu
                elif a == t:
                    denom += defense[idx[h]] * mu
            attack[i] = num / denom if denom > 1e-12 else ep[i]

        # update defense: goals-conceded / expected-opponent-offense
        for i, t in enumerate(team_ids):
            num   = gagn[i] + prior_games * (1.0 / max(ep[i], 0.05)) * mu
            denom = prior_games * mu  # prior: average opponent attack = 1.0
            for h, a, hg, ag in ms:
                if h == t:
                    denom += attack[idx[a]] * mu
                elif a == t:
                    denom += attack[idx[h]] * mu
            defense[i] = num / denom if denom > 1e-12 else (1.0 / max(ep[i], 0.05))

        # renormalize: geometric mean(attack) = 1.0; mu absorbs the scale
        log_geo = sum(math.log(max(a, 1e-9)) for a in attack) / n
        scale   = math.exp(log_geo)
        attack  = [a / scale for a in attack]
        mu     *= scale

        delta = max(
            abs(attack[i] - prev_a[i]) + abs(defense[i] - prev_d[i])
            for i in range(n)
        )
        if delta < tol:
            break

    return {
        "_mu": round(mu, 4),
        **{
            team_ids[i]: {
                "attack":  round(attack[i], 4),
                "defense": round(defense[i], 4),
                "n":       games[i],
            }
            for i in range(n)
        },
    }


def dc_lambdas(home_id, away_id, ratings, total_factor=1.0):
    """Expected goals (lh, la) from fitted attack/defense ratings.

    lambda_h = attack[home] * defense[away] * mu
    defense is a goals-conceded-rate: >1.0 = weak defense, <1.0 = strong.
    """
    mu = ratings.get("_mu", 1.25)
    hr = ratings.get(home_id, {})
    ar = ratings.get(away_id, {})
    lh = hr.get("attack", 1.0) * ar.get("defense", 1.0) * mu * total_factor
    la = ar.get("attack", 1.0) * hr.get("defense", 1.0) * mu * total_factor
    return float(max(lh, 0.05)), float(max(la, 0.05))
