"""Fetch all 64 matches of the 2022 World Cup (Qatar) from Wikipedia, reusing
the same {{football box}} parser the live pipeline uses. Writes
pipeline/backtest/results_2022.json.

2022 format: 8 groups (A-H) of 4, then Round of 16 -> QF -> SF -> 3rd place -> Final.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wc26 import wiki

OUT = Path(__file__).resolve().parent / "results_2022.json"
GROUPS = "ABCDEFGH"

# Wikipedia uses full country names in 2022 fb templates for some teams; the
# {{nft}}/{{fb}} flag templates carry 3-letter codes we already map. The 2022
# squad codes match FIFA codes; a few need normalising to our scheme.
CODE_FIX = {
    "KSA": "KSA", "CRC": "CRC", "SRB": "SRB", "GHA": "GHA", "URU": "URU",
    "POR": "POR", "SUI": "SUI", "CMR": "CMR", "KOR": "KOR", "GER": "GER",
    "JPN": "JPN", "ESP": "ESP", "CRO": "CRO", "MAR": "MAR", "BEL": "BEL",
    "CAN": "CAN", "BRA": "BRA", "SRB2": "SRB", "ARG": "ARG", "MEX": "MEX",
    "POL": "POL", "FRA": "FRA", "DEN": "DEN", "TUN": "TUN", "AUS": "AUS",
    "ENG": "ENG", "IRN": "IRN", "USA": "USA", "WAL": "WAL", "NED": "NED",
    "SEN": "SEN", "ECU": "ECU", "QAT": "QAT",
}


# 2022 pages use "{{Football box" (capital F) and flag templates of the form
# {{#invoke:flagg|main|unpre|avar=fb|QAT}} — the 3-letter code is the last
# |XXX before the close. These regexes are tailored to that format.
_BOX_2022 = re.compile(r"\{\{\s*(?:#invoke:)?[Ff]ootball box")
_TEAM_2022 = re.compile(r"fb\|([A-Z]{3})\}")


def _team_2022(field):
    m = _TEAM_2022.search(field)
    if m:
        return m.group(1)
    return wiki._parse_team(field)  # fallback to 2026-style


def parse_matches(wikitext, tag):
    out = []
    chunks = _BOX_2022.split(wikitext)[1:]
    n = 0
    for chunk in chunks:
        chunk = chunk[:4000]
        t1 = _team_2022(wiki._field(chunk, "team1"))
        t2 = _team_2022(wiki._field(chunk, "team2"))
        if not t1 or not t2:
            continue
        score = wiki._field(chunk, "score")
        sm = wiki._SCORE_RE.search(score)
        if not sm:
            continue
        n += 1
        out.append({
            "id": f"{tag}{n}",
            "home": CODE_FIX.get(t1, t1),
            "away": CODE_FIX.get(t2, t2),
            "hg": int(sm.group(1)),
            "ag": int(sm.group(2)),
            "date": wiki._parse_date(wiki._field(chunk, "date")),
            "stage": tag,
        })
    return out


def main():
    matches = []
    # group pages
    titles = {f"2022 FIFA World Cup Group {g}": g for g in GROUPS}
    texts = wiki._wikitext_many(list(titles))
    for title, g in titles.items():
        ms = parse_matches(texts[title], f"G{g}")
        print(f"Group {g}: {len(ms)} matches")
        matches.extend(ms)
    # knockout page
    ko = wiki._wikitext_many(["2022 FIFA World Cup knockout stage"])
    ko_matches = parse_matches(ko["2022 FIFA World Cup knockout stage"], "KO")
    print(f"Knockout: {len(ko_matches)} matches")
    matches.extend(ko_matches)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"matches": matches}, f, indent=1)
    print(f"\nTotal: {len(matches)} matches -> {OUT.name}")
    teams = sorted({m["home"] for m in matches} | {m["away"] for m in matches})
    print(f"Teams ({len(teams)}): {' '.join(teams)}")


if __name__ == "__main__":
    main()
