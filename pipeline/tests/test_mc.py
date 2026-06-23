import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import mc


def _played(h, a, hg, ag):
    return {"home": h, "away": a, "played": True, "hg": hg, "ag": ag}


def test_rank_group_fairplay_breaks_tie():
    # W and X end up tied on points/gd/gf, and tied head-to-head (their
    # match was a 0-0 draw) -- only fair play should separate them.
    fixtures = [
        _played("W", "X", 0, 0),
        _played("W", "Y", 1, 0),
        _played("W", "Z", 1, 0),
        _played("X", "Y", 1, 0),
        _played("X", "Z", 1, 0),
        _played("Y", "Z", 0, 0),
    ]
    local_idx = {"W": 0, "X": 1, "Y": 2, "Z": 3}
    nsims = 8
    rng = np.random.default_rng(0)
    fairplay = {"W": -1, "X": -6, "Y": 0, "Z": 0}

    order, pts, gd, gf = mc.rank_group(fixtures, local_idx, {}, nsims, rng, fairplay=fairplay)

    # W (better conduct score) must rank above X in every sim, despite
    # identical points/gd/gf/h2h -- random jitter never gets a say here.
    assert (order[:, 0] == local_idx["W"]).all()
    assert (order[:, 1] == local_idx["X"]).all()


def test_rank_group_no_fairplay_is_unaffected():
    # same fixture, omit fairplay entirely -- must not raise, defaults to 0
    # for everyone (W/X tie stays unresolved by this criterion, as before).
    fixtures = [
        _played("W", "X", 0, 0),
        _played("W", "Y", 1, 0),
        _played("W", "Z", 1, 0),
        _played("X", "Y", 1, 0),
        _played("X", "Z", 1, 0),
        _played("Y", "Z", 0, 0),
    ]
    local_idx = {"W": 0, "X": 1, "Y": 2, "Z": 3}
    order, pts, gd, gf = mc.rank_group(fixtures, local_idx, {}, 8, np.random.default_rng(0))
    assert order.shape == (8, 4)
