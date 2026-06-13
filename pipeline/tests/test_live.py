import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import live
from wc26.matchmodel import outcome_probs, lambdas


def test_kickoff_matches_prematch():
    """At minute 0, 0-0, live W/D/L ~ pre-match outcome probs."""
    lh, la = lambdas(150.0)
    live_p = live.live_outcome(lh, la, 0, 0, 0)
    pre_p = outcome_probs(150.0)
    for a, b in zip(live_p, pre_p):
        assert abs(a - b) < 0.03


def test_probs_sum_to_one():
    lh, la = lambdas(200.0)
    for minute, hg, ag in [(0, 0, 0), (30, 1, 0), (75, 1, 1), (89, 2, 1)]:
        p = live.live_outcome(lh, la, hg, ag, minute)
        assert abs(sum(p) - 1.0) < 1e-9


def test_leading_late_is_near_certain():
    """2-0 up at minute 88 -> home win prob very high."""
    lh, la = lambdas(0.0)
    ph, pd, pa = live.live_outcome(lh, la, 2, 0, 88)
    assert ph > 0.95


def test_full_time_deterministic():
    """At/after full time the current score decides it."""
    lh, la = lambdas(100.0)
    ph, pd, pa = live.live_outcome(lh, la, 1, 2, 96)
    assert pa > 0.98  # away leads, match over


def test_red_card_shifts_toward_more_players():
    lh, la = lambdas(0.0)
    base = live.live_outcome(lh, la, 0, 0, 30)
    # away team down to 10 men -> home win prob rises
    with_red = live.live_outcome(lh, la, 0, 0, 30, red_a=1)
    assert with_red[0] > base[0]
    assert with_red[2] < base[2]


def test_live_advance_bounds():
    lh, la = lambdas(0.0)
    # level late in a knockout -> advance ~ 0.5 (plus tiny ET/pen)
    adv = live.live_advance(lh, la, 1, 1, 89, dr=0.0)
    assert 0.4 < adv < 0.6
    # 1-0 up late -> high advance
    adv2 = live.live_advance(lh, la, 1, 0, 89, dr=0.0)
    assert adv2 > 0.85
