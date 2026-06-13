import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import matchmodel as mm
from wc26 import factors


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
