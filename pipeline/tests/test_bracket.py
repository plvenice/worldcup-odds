import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import bracket as bk
from wc26 import data

BDEF = data.bracket()
ALL_GROUPS = list("ABCDEFGHIJKL")


def test_slot_constraints_shape():
    cons = bk.third_slot_constraints(BDEF)
    assert len(cons) == 8
    assert [m for m, _ in cons] == [74, 77, 79, 80, 81, 82, 85, 87]


def test_every_combination_has_feasible_assignment():
    """All C(12,8)=495 possible sets of advancing thirds must be assignable."""
    cons = bk.third_slot_constraints(BDEF)
    count = 0
    for combo in combinations(ALL_GROUPS, 8):
        assign = bk.assign_thirds(combo, BDEF)
        count += 1
        # 8 distinct groups, all from the combo
        assert len(assign) == 8
        assert sorted(assign.values()) == sorted(set(assign.values()))
        assert set(assign.values()) <= set(combo)
        # every slot's group respects its allowed set
        allowed = dict(cons)
        for match_no, g in assign.items():
            assert g in allowed[match_no], (combo, match_no, g)
    assert count == 495


def test_assignment_deterministic():
    combo = list("ABCDEFGH")
    a1 = bk.assign_thirds(combo, BDEF)
    a2 = bk.assign_thirds(list(reversed(combo)), BDEF)
    assert a1 == a2


def test_resolve_r32_complete():
    winners = {g: f"W{g}" for g in ALL_GROUPS}
    runners = {g: f"R{g}" for g in ALL_GROUPS}
    thirds = {g: f"T{g}" for g in ALL_GROUPS}
    qual = list("ABCDEFGH")
    r32 = bk.resolve_r32(winners, runners, thirds, qual, BDEF)
    assert len(r32) == 16
    teams = [t for pair in r32.values() for t in pair]
    assert len(teams) == len(set(teams)) == 32
    # all 12 winners and 12 runners present, plus 8 thirds
    assert sum(1 for t in teams if t.startswith("W")) == 12
    assert sum(1 for t in teams if t.startswith("R")) == 12
    assert sum(1 for t in teams if t.startswith("T")) == 8
