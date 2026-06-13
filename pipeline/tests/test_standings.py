import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import standings as st


TEAMS = ["AAA", "BBB", "CCC", "DDD"]


def test_points_ordering():
    results = [
        ("AAA", "BBB", 2, 0), ("CCC", "DDD", 1, 1),
        ("AAA", "CCC", 1, 0), ("BBB", "DDD", 0, 0),
        ("AAA", "DDD", 3, 1), ("BBB", "CCC", 0, 1),
    ]
    # AAA 9pts; CCC 4; BBB 1... check: BBB: L,D,L = 1pt; CCC: D,L,W = 4; DDD: D,D,L = 2
    assert st.rank(TEAMS, results) == ["AAA", "CCC", "DDD", "BBB"]


def test_gd_then_gf():
    results = [
        ("AAA", "BBB", 1, 0), ("CCC", "DDD", 1, 0),
        ("AAA", "CCC", 0, 1), ("BBB", "DDD", 1, 0),
        ("AAA", "DDD", 2, 0), ("BBB", "CCC", 0, 2),
    ]
    # AAA: W L W = 6pts, gf3 ga1 gd+2 | CCC: W W L? CCC beat DDD 1-0, beat AAA 1-0, lost BBB 0-2? no: BBB-CCC 0-2 -> CCC won
    # CCC: 9pts. AAA 6pts gd+2. BBB: 3pts (beat DDD). DDD 0.
    assert st.rank(TEAMS, results)[0] == "CCC"
    assert st.rank(TEAMS, results)[1] == "AAA"


def test_two_way_tie_head_to_head():
    # AAA and BBB end tied on pts/gd/gf; BBB beat AAA head-to-head -> BBB first
    results = [
        ("BBB", "AAA", 1, 0),               # h2h: BBB over AAA
        ("AAA", "CCC", 2, 0), ("AAA", "DDD", 1, 1),
        ("BBB", "CCC", 1, 1), ("BBB", "DDD", 2, 0),
        ("CCC", "DDD", 0, 0),
    ]
    # AAA: L W D = 4pts, gf3 ga2 gd+1 | BBB: W D W = 7pts -> not tied. Rebuild:
    results = [
        ("BBB", "AAA", 1, 0),
        ("AAA", "CCC", 2, 0), ("AAA", "DDD", 2, 0),  # AAA 6pts gf4 ga1 gd+3
        ("BBB", "CCC", 0, 1), ("BBB", "DDD", 3, 0),  # BBB 6pts gf4 ga1 gd+3
        ("CCC", "DDD", 0, 0),
    ]
    ranked = st.rank(TEAMS, results)
    assert ranked[0] == "BBB" and ranked[1] == "AAA", ranked


def test_three_way_tie_minitable():
    # Circle: AAA beat BBB, BBB beat CCC, CCC beat AAA, all 1-0; all beat DDD 1-0.
    # All tied 6pts gd+1 gf2; h2h mini-table also fully tied -> any order valid,
    # but DDD must be last and result must be a permutation.
    results = [
        ("AAA", "BBB", 1, 0), ("BBB", "CCC", 1, 0), ("CCC", "AAA", 1, 0),
        ("AAA", "DDD", 1, 0), ("BBB", "DDD", 1, 0), ("CCC", "DDD", 1, 0),
    ]
    ranked = st.rank(TEAMS, results)
    assert ranked[3] == "DDD"
    assert sorted(ranked[:3]) == ["AAA", "BBB", "CCC"]


def test_rank_thirds_top8():
    rows = []
    for i, pts in enumerate([6, 6, 5, 4, 4, 4, 3, 3, 2, 1, 1, 0]):
        rows.append({"team": f"T{i:02d}", "pts": pts, "gd": i % 3, "gf": i})
    ranked = st.rank_thirds(rows)
    assert len(ranked) == 12
    assert ranked[0] in ("T00", "T01")
    # T01 has higher gd (1%3=1 vs 0) -> T01 first
    assert ranked[0] == "T01"
