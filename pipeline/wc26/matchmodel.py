"""Match probability model: Elo -> Dixon-Coles bivariate Poisson -> outcome probabilities.

Calibration constants chosen against international-tournament scoring norms
(~2.5 goals/match at even strength); the backtest (scripts/backtest_2022.py)
validates Brier score vs market closing odds before these numbers are trusted.
"""
import numpy as np

# Elo -> expected goals mapping
BASE_LAMBDA = 1.25          # per-team goals at even strength (2.5 total)
ELO_GOAL_SCALE = 1630.0     # dr=400 -> ~1.5 expected-goal margin
MAX_GOALS = 12              # score matrix truncation
DC_RHO = -0.10              # Dixon-Coles low-score correction (boosts draws)
PEN_TILT_PER_400 = 0.02     # max penalty-shootout edge at |dr|>=400 is 52/48
ET_LAMBDA_FACTOR = 0.30     # extra time ~30 min at slightly reduced intensity


def lambdas(dr, total_factor=1.0):
    """Expected goals (home-ish, away-ish) given adjusted Elo difference dr.

    dr already includes all factor adjustments (host, rest, travel, altitude,
    availability). total_factor scales total goals (heat shrinks it).
    Works on scalars or numpy arrays.
    """
    x = np.asarray(dr, dtype=float) / ELO_GOAL_SCALE
    lh = BASE_LAMBDA * np.power(10.0, x) * total_factor
    la = BASE_LAMBDA * np.power(10.0, -x) * total_factor
    return lh, la


def score_matrix(lh, la, max_goals=MAX_GOALS, rho=DC_RHO):
    """(max_goals+1)^2 matrix of P(home=i, away=j), Dixon-Coles corrected."""
    g = np.arange(max_goals + 1)
    ph = np.exp(-lh) * np.power(lh, g) / _factorials(max_goals)
    pa = np.exp(-la) * np.power(la, g) / _factorials(max_goals)
    m = np.outer(ph, pa)
    # Dixon-Coles tau correction on the four low-score cells
    m[0, 0] *= max(1 - lh * la * rho, 0.05)
    m[1, 0] *= max(1 + la * rho, 0.05)
    m[0, 1] *= max(1 + lh * rho, 0.05)
    m[1, 1] *= max(1 - rho, 0.05)
    return m / m.sum()


_FACT_CACHE = {}


def _factorials(n):
    if n not in _FACT_CACHE:
        f = np.ones(n + 1)
        for i in range(1, n + 1):
            f[i] = f[i - 1] * i
        _FACT_CACHE[n] = f
    return _FACT_CACHE[n]


def outcome_probs(dr, total_factor=1.0):
    """(p_home_win, p_draw, p_away_win) over 90 minutes."""
    lh, la = lambdas(float(dr), total_factor)
    m = score_matrix(lh, la)
    return float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum())


def advance_prob(dr, total_factor=1.0):
    """P(home advances) in a knockout match: 90 min + extra time + penalties."""
    lh, la = lambdas(float(dr), total_factor)
    m = score_matrix(lh, la)
    p_win90 = float(np.tril(m, -1).sum())
    p_draw90 = float(np.trace(m))
    # extra time: shortened Poisson at reduced intensity
    met = score_matrix(lh * ET_LAMBDA_FACTOR, la * ET_LAMBDA_FACTOR, max_goals=6)
    p_win_et = float(np.tril(met, -1).sum())
    p_level = float(np.trace(met))
    p_pen = 0.5 + np.clip(dr, -400, 400) / 400.0 * PEN_TILT_PER_400
    return p_win90 + p_draw90 * (p_win_et + p_level * p_pen)


# Precomputed lookup so the Monte Carlo can evaluate advance_prob on big arrays.
_GRID_DR = np.arange(-1500, 1501, 10, dtype=float)
_GRID_ADV = None
_GRID_ADV_HOT = None


def advance_prob_vec(dr_array, hot=False):
    """Vectorized advance prob via interpolation on a dr grid."""
    global _GRID_ADV, _GRID_ADV_HOT
    if _GRID_ADV is None:
        _GRID_ADV = np.array([advance_prob(d) for d in _GRID_DR])
        _GRID_ADV_HOT = np.array([advance_prob(d * 0.9, total_factor=0.95) for d in _GRID_DR])
    table = _GRID_ADV_HOT if hot else _GRID_ADV
    return np.interp(dr_array, _GRID_DR, table)


def elo_update(elo_a, elo_b, goals_a, goals_b, dr_extra=0.0, k=60.0):
    """World Football Elo update for team A. dr_extra = situational Elo edge
    for A (host advantage etc.) included in expectation but not stored rating."""
    margin = abs(goals_a - goals_b)
    if margin <= 1:
        g = 1.0
    elif margin == 2:
        g = 1.5
    else:
        g = (11.0 + margin) / 8.0
    w = 1.0 if goals_a > goals_b else (0.5 if goals_a == goals_b else 0.0)
    we = 1.0 / (1.0 + 10.0 ** (-((elo_a + dr_extra) - elo_b) / 400.0))
    return elo_a + k * g * (w - we)
