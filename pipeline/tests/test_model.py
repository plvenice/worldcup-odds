import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import matchmodel as mm
from wc26 import factors
from wc26 import forecast


def test_outcome_probs_sum_to_one():
    for dr in (-800, -200, 0, 150, 600):
        ph, pd, pa = mm.outcome_probs(dr)
        assert abs(ph + pd + pa - 1.0) < 1e-9


def test_symmetry_at_zero():
    ph, pd, pa = mm.outcome_probs(0)
    assert abs(ph - pa) < 1e-9
    assert 0.20 < pd < 0.35   # sane international draw rate


def test_favorite_monotonic():
    probs = [mm.outcome_probs(dr)[0] for dr in (0, 100, 200, 400, 800)]
    assert all(b > a for a, b in zip(probs, probs[1:]))
    assert probs[-1] > 0.75   # +800 Elo should be a heavy favorite


def test_advance_prob_bounds_and_symmetry():
    assert abs(mm.advance_prob(0) - 0.5) < 0.01
    assert mm.advance_prob(400) > 0.75
    assert abs(mm.advance_prob(300) + mm.advance_prob(-300) - 1.0) < 0.02


def test_advance_vec_matches_scalar():
    drs = np.array([-500.0, -100.0, 0.0, 250.0, 700.0])
    vec = mm.advance_prob_vec(drs)
    for d, v in zip(drs, vec):
        assert abs(v - mm.advance_prob(d)) < 0.01


def test_elo_update_directions():
    # favorite wins narrowly: small gain
    gain = mm.elo_update(2000, 1600, 1, 0) - 2000
    assert 0 < gain < 10
    # underdog wins big: large gain
    gain_u = mm.elo_update(1600, 2000, 3, 0) - 1600
    assert gain_u > 50


def test_availability_penalty():
    overrides = [{"team": "FRA", "player": "X", "weight": 45, "until": None},
                 {"team": "FRA", "player": "Y", "weight": 30, "until": "2026-06-01"}]
    import datetime
    pen, names = factors.availability_penalty("FRA", overrides,
                                              datetime.date(2026, 6, 12))
    assert pen == 45 and names == ["X"]   # Y returned June 1


def test_merge_auto_injuries():
    manual = [{"team": "FRA", "player": "X", "weight": 45, "until": None}]
    auto = [
        {"team": "FRA", "player": "X"},        # already manual -- skip
        {"team": "USA", "player": "Pulisic"},  # new -- gets flat default
        {"team": "USA", "player": "Pulisic"},  # dup within API response -- skip
    ]
    merged = forecast._merge_auto_injuries(manual, auto)
    assert len(merged) == 2
    usa = next(o for o in merged if o["team"] == "USA")
    assert usa["weight"] == factors.AUTO_INJURY_WEIGHT
    assert usa["reason"] == "auto-detected (API-Football)"


def test_merge_auto_injuries_normalizes_accents():
    # manual entry uses the accented spelling; API returns it bare -- must
    # still dedupe, or the same injury gets docked twice (once manual, once auto)
    manual = [{"team": "FRA", "player": "Mbappé", "weight": 45, "until": None}]
    auto = [{"team": "FRA", "player": "Mbappe", "player_id": 1}]
    merged = forecast._merge_auto_injuries(manual, auto)
    assert len(merged) == 1


def test_merge_auto_injuries_scales_with_minutes():
    auto = [{"team": "USA", "player": "Pulisic", "player_id": 9}]
    lookup = {9: 2700.0}.get
    merged = forecast._merge_auto_injuries([], auto, minutes_lookup=lookup)
    assert merged[0]["weight"] == factors.AUTO_INJURY_MAX_WEIGHT


def test_auto_injury_weight_scaling():
    assert factors.auto_injury_weight(None) == factors.AUTO_INJURY_WEIGHT
    assert factors.auto_injury_weight(0) == factors.AUTO_INJURY_MIN_WEIGHT
    assert factors.auto_injury_weight(factors.AUTO_INJURY_FULL_MINUTES) == factors.AUTO_INJURY_MAX_WEIGHT
    half = factors.auto_injury_weight(factors.AUTO_INJURY_FULL_MINUTES / 2)
    assert factors.AUTO_INJURY_MIN_WEIGHT < half < factors.AUTO_INJURY_MAX_WEIGHT
    # minutes beyond a full season don't push the dock past the manual cap
    assert factors.auto_injury_weight(factors.AUTO_INJURY_FULL_MINUTES * 2) == factors.AUTO_INJURY_MAX_WEIGHT


def test_blend_outcome():
    model = (0.5, 0.3, 0.2)
    market = (0.3, 0.3, 0.4)
    b = mm.blend_outcome(model, market, 0.65)
    assert abs(sum(b) - 1.0) < 1e-9
    # 0.65 weight on market pulls toward market
    assert b[0] < model[0] and b[2] > model[2]
    # weight 0 returns model; weight 1 returns market
    assert mm.blend_outcome(model, market, 0.0) == pytest.approx(model)
    assert mm.blend_outcome(model, market, 1.0) == pytest.approx(market)


def test_reweight_to_outcome_matches_target():
    lh, la = mm.lambdas(150.0)
    m = mm.score_matrix(float(lh), float(la))
    target = (0.55, 0.25, 0.20)
    m2 = mm.reweight_to_outcome(m, target)
    assert abs(m2.sum() - 1.0) < 1e-9
    H = np.tril(m2, -1).sum()
    D = np.trace(m2)
    A = np.triu(m2, 1).sum()
    assert H == pytest.approx(0.55, abs=1e-6)
    assert D == pytest.approx(0.25, abs=1e-6)
    assert A == pytest.approx(0.20, abs=1e-6)


def test_devig_three():
    from wc26 import odds
    ph, pd, pa = odds._devig_three(2.0, 3.5, 4.0)
    assert abs(ph + pd + pa - 1.0) < 1e-9
    assert ph > pa  # lower odds -> higher prob


def test_host_advantage_sign():
    home = {"id": "USA", "host": True}
    away = {"id": "GER", "host": False}
    venue = {"country": "USA", "lat": 40.8, "lon": -74.0, "altitude_m": 2,
             "tz": "America/New_York", "climate_controlled": False,
             "surface_quality": 1.0}
    dr, tf, hot, att = factors.match_adjustments(home, away, venue, {})
    assert dr == factors.HOST_ADV
    # and reversed
    dr2, _, _, _ = factors.match_adjustments(away, home, venue, {})
    assert dr2 == -factors.HOST_ADV
