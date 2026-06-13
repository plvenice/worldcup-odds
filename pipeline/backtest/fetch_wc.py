"""Generalized World Cup results fetcher (group stage) for any year, reusing the
2022 {{Football box}} parser. Usage: python fetch_wc.py 2018

Writes results_<year>.json. Works for the 32-team era (2014/2018/2022): 8
groups A-H.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wc26 import wiki

GROUPS = "ABCDEFGH"
_BOX = re.compile(r"\{\{\s*(?:#invoke:)?[Ff]ootball box")
_TEAM = re.compile(r"fb\|([A-Z]{3})\}")


def _team(field):
    m = _TEAM.search(field)
    return m.group(1) if m else wiki._parse_team(field)


def parse(wikitext, tag):
    out, n = [], 0
    for chunk in _BOX.split(wikitext)[1:]:
        chunk = chunk[:4000]
        t1 = _team(wiki._field(chunk, "team1"))
        t2 = _team(wiki._field(chunk, "team2"))
        if not t1 or not t2:
            continue
        sm = wiki._SCORE_RE.search(wiki._field(chunk, "score"))
        if not sm:
            continue
        n += 1
        out.append({"id": f"{tag}{n}", "home": t1, "away": t2,
                    "hg": int(sm.group(1)), "ag": int(sm.group(2)),
                    "date": wiki._parse_date(wiki._field(chunk, "date")),
                    "stage": tag})
    return out


def main(year):
    titles = {f"{year} FIFA World Cup Group {g}": g for g in GROUPS}
    texts = wiki._wikitext_many(list(titles))
    matches = []
    for title, g in titles.items():
        ms = parse(texts[title], f"G{g}")
        print(f"Group {g}: {len(ms)}")
        matches.extend(ms)
    out = Path(__file__).resolve().parent / f"results_{year}.json"
    json.dump({"matches": matches}, open(out, "w", encoding="utf-8"), indent=1)
    teams = sorted({m["home"] for m in matches} | {m["away"] for m in matches})
    print(f"Total group matches: {len(matches)}  teams: {len(teams)}")
    print(" ".join(teams))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2018")
