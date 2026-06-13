"""In-match win probability.

Given a fixture's pre-match expected goals (lh, la) and the current state
(score, minute, red cards), the final score is the current score plus the
remaining goals, which are Poisson with rate scaled by the time left and by
any man-advantage. So the live W/D/L is the convolution of the current score
with the remaining-goals distribution.

Properties:
  - At minute 0, score 0-0, no reds -> approximately the pre-match outcome.
  - As minute -> full time, the distribution collapses onto the current score.
  - A red card shifts remaining goals toward the team with more players.

Knockout matches add extra time + penalties when level at full time.
"""
import numpy as np

from .matchmodel import _factorials, score_matrix, MODEL_TEMPERATURE, PEN_TILT_PER_400

RED_BOOST = 0.12      # opponent down a man -> your remaining goals up ~12%/card
RED_PENALTY = 0.10    # you down a man -> your remaining goals down ~10%/card
STOPPAGE_MIN = 5      # assume ~5 minutes of added time
ET_FRACTION = 0.30    # extra time ~30 min at reduced intensity (matches pre-match)


def _pmf(lam, kmax):
    g = np.arange(kmax + 1)
    return np.exp(-lam) * np.power(lam, g) / _factorials(kmax)


def remaining_lambdas(lh, la, minute, red_h=0, red_a=0):
    total = 90 + STOPPAGE_MIN
    frac = max(0.0, (total - minute)) / 90.0
    lh_r = lh * frac * (1 + RED_BOOST * red_a) * (1 - RED_PENALTY * red_h)
    la_r = la * frac * (1 + RED_BOOST * red_h) * (1 - RED_PENALTY * red_a)
    return max(lh_r, 1e-9), max(la_r, 1e-9)


def live_outcome(lh, la, hg, ag, minute, red_h=0, red_a=0, kmax=10,
                 temperature=None):
    """Live (P_home_win, P_draw, P_away_win) at full time of regulation."""
    lhr, lar = remaining_lambdas(lh, la, minute, red_h, red_a)
    m = np.outer(_pmf(lhr, kmax), _pmf(lar, kmax))  # remaining goals (i, j)
    t = MODEL_TEMPERATURE if temperature is None else temperature
    if t != 1.0:
        m = np.power(m, 1.0 / t)
        m /= m.sum()
    i = np.arange(kmax + 1)
    fh = hg + i[:, None]
    fa = ag + i[None, :]
    ph = float(m[fh > fa].sum())
    pd = float(m[fh == fa].sum())
    pa = float(m[fh < fa].sum())
    return ph, pd, pa


def live_advance(lh, la, hg, ag, minute, red_h=0, red_a=0, dr=0.0, kmax=10):
    """Live P(home advances) for a knockout match: regulation win, or draw
    then extra time / penalties. dr (Elo diff incl. factors) tilts penalties."""
    ph, pd, pa = live_outcome(lh, la, hg, ag, minute, red_h, red_a, kmax)
    # extra time from a level score: short Poisson at reduced intensity
    et = score_matrix(lh * ET_FRACTION, la * ET_FRACTION, max_goals=6)
    p_et_home = float(np.tril(et, -1).sum())
    p_et_level = float(np.trace(et))
    p_pen = 0.5 + np.clip(dr, -400, 400) / 400.0 * PEN_TILT_PER_400
    return ph + pd * (p_et_home + p_et_level * p_pen)
