import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import wiki

# Trimmed real structure (see Wikipedia "2026 FIFA World Cup Group B"):
# minus sign (U+2212), en dash (U+2013), and plain ASCII hyphen all appear
# in the wild across different group pages/rows for the same "Score" column.
_DISCIPLINE_WIKITEXT = """
Some intro text.

==Discipline==
The team conduct ("fair play") score will be used as a tiebreaker.
*yellow card: −1 point;

{| class="wikitable sortable" style="text-align:center;"
|-
!rowspan=2|Team
!colspan=4 style="border-left:3px solid gray"|Match 1
!rowspan=2 style="border-left:3px solid gray"|Score
|-
!style="border-left:3px solid gray"|{{yel}}
|-
|align=left|{{#invoke:flag|fb|SUI}}
|style="border-left:3px solid gray"| 1 ||  ||  ||
!style="border-left:3px solid gray"| −2
|-
|align=left|{{#invoke:flag|fb|CZE}}
|style="border-left:3px solid gray"|  ||  ||  ||
!style="border-left:3px solid gray"| –1
|-
|align=left|{{#invoke:flag|fb|CAN}}
|style="border-left:3px solid gray"|  ||  ||  ||
!style="border-left:3px solid gray"| -3
|-
|align=left|{{#invoke:flag|fb|QAT}}
|style="border-left:3px solid gray"|  ||  ||  ||
!style="border-left:3px solid gray"| 0
|}

==References==
{{reflist}}
"""


def test_parses_minus_sign():
    # U+2212 MINUS SIGN, the "correct" character
    out = wiki.parse_group_discipline(_DISCIPLINE_WIKITEXT, {"SUI", "CZE", "CAN", "QAT"})
    assert out["SUI"] == -2


def test_parses_en_dash_variant():
    # Regression test: some Wikipedia rows use U+2013 EN DASH instead of the
    # minus sign for the same column (confirmed live on Group A's CZE row
    # and all of Group G) -- this silently dropped those teams before the
    # _DASH_RE fix, which is exactly the kind of partial-data bug that's
    # worse than an honest "no data" because it looks complete.
    out = wiki.parse_group_discipline(_DISCIPLINE_WIKITEXT, {"SUI", "CZE", "CAN", "QAT"})
    assert out["CZE"] == -1


def test_parses_ascii_hyphen_and_zero():
    out = wiki.parse_group_discipline(_DISCIPLINE_WIKITEXT, {"SUI", "CZE", "CAN", "QAT"})
    assert out["CAN"] == -3
    assert out["QAT"] == 0


def test_unknown_team_filtered():
    # valid_ids restricts to real tournament teams -- garbage flag codes
    # (typos, navbox noise elsewhere on the page) shouldn't leak through.
    out = wiki.parse_group_discipline(_DISCIPLINE_WIKITEXT, {"SUI"})
    assert set(out) == {"SUI"}


def test_missing_section_returns_empty():
    assert wiki.parse_group_discipline("no discipline section here", {"SUI"}) == {}
