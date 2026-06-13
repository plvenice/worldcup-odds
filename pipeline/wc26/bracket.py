"""Round-of-32 slot resolution, including third-place allocation.

The 8 third-place slots each accept thirds only from an allowed group set
(data/bracket.json, verified against FIFA regulations). Given which 8 groups'
thirds qualified, FIFA's annexed table fixes the exact slot assignment. If
data/third_place_table.json exists (parsed from the published table), it is
used; otherwise we fall back to the lexicographically-first feasible perfect
matching, which always respects the allowed sets but may differ from FIFA's
choice when several assignments are feasible.
"""
import json
from pathlib import Path

from . import data

_TABLE = None
_TABLE_PATH = data.DATA / "third_place_table.json"


def _load_table():
    global _TABLE
    if _TABLE is None:
        if _TABLE_PATH.exists():
            with open(_TABLE_PATH, encoding="utf-8") as f:
                # keys: sorted-group-string e.g. "EFGHIJKL" -> {match_no(str): group}
                _TABLE = json.load(f)
        else:
            _TABLE = {}
    return _TABLE


def third_slot_constraints(bracket_def):
    """[(match_no, frozenset(allowed_groups))] in match order."""
    out = []
    for m in bracket_def["r32"]:
        if m["away"]["type"] == "T":
            out.append((m["match"], frozenset(m["away"]["allowed"])))
    return out


def assign_thirds(qualified_groups, bracket_def):
    """qualified_groups: iterable of 8 group letters whose thirds advanced.
    Returns dict match_no -> group letter."""
    key = "".join(sorted(qualified_groups))
    table = _load_table()
    if key in table:
        return {int(k): v for k, v in table[key].items()}
    return _fallback_match(sorted(qualified_groups), third_slot_constraints(bracket_def))


def _fallback_match(groups, constraints):
    """Backtracking perfect matching: slots in match order, try groups
    alphabetically. Deterministic; always satisfies allowed sets."""
    slots = [(m, allowed) for m, allowed in constraints]

    def bt(i, used, acc):
        if i == len(slots):
            return acc
        match_no, allowed = slots[i]
        for g in groups:
            if g in used or g not in allowed:
                continue
            r = bt(i + 1, used | {g}, {**acc, match_no: g})
            if r is not None:
                return r
        return None

    result = bt(0, set(), {})
    if result is None:
        raise ValueError(f"No feasible third-place assignment for {groups}")
    return result


def resolve_r32(winners, runners, thirds_by_group, qualified_groups, bracket_def):
    """Map every R32 match to (home_team, away_team).

    winners/runners: dict group -> team_id
    thirds_by_group: dict group -> team_id (all 12 thirds)
    qualified_groups: the 8 groups whose thirds advanced
    """
    third_assign = assign_thirds(qualified_groups, bracket_def)
    out = {}
    for m in bracket_def["r32"]:
        h, a = m["home"], m["away"]
        home = winners[h["group"]] if h["type"] == "W" else runners[h["group"]]
        if a["type"] == "R":
            away = runners[a["group"]]
        elif a["type"] == "W":
            away = winners[a["group"]]
        else:
            away = thirds_by_group[third_assign[m["match"]]]
        out[m["match"]] = (home, away)
    return out
