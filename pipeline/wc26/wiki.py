"""Fixtures and results from Wikipedia group-page wikitext.

This is the zero-credential data source: Wikipedia group pages are updated
within minutes of full time. When an API_FOOTBALL_KEY is configured the
pipeline prefers API-Football for results and adds lineups/injuries; Wikipedia
remains the fallback.

Parsed from {{football box}} templates via the MediaWiki API.
"""
import json
import re
import requests
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import data

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "worldcup-odds/1.0 (tournament probability model)"}
CACHE = data.DATA / "cache_fixtures.json"
KNOCKOUT_CACHE = data.DATA / "cache_knockout.json"
DISCIPLINE_CACHE = data.DATA / "cache_discipline.json"
THIRD_TABLE_PATH = data.DATA / "third_place_table.json"

GROUPS = "ABCDEFGHIJKL"

STADIUM_ALIASES = {
    "estadio azteca": "azteca", "azteca": "azteca",
    "estadio akron": "akron", "akron": "akron",
    "estadio bbva": "bbva", "bbva": "bbva",
    "bmo field": "bmo",
    "bc place": "bcplace",
    "sofi stadium": "sofi",
    "levi's stadium": "levis", "levis stadium": "levis",
    "lumen field": "lumen",
    "at&t stadium": "att",
    "nrg stadium": "nrg",
    "arrowhead stadium": "arrowhead",
    "mercedes-benz stadium": "mercedesbenz",
    "hard rock stadium": "hardrock",
    "metlife stadium": "metlife",
    "lincoln financial field": "lincoln",
    "gillette stadium": "gillette",
}

_TEAM_RE = re.compile(
    r"\{\{(?:#invoke:flag\|)?fb[a-z\-]*\|([A-Za-z]{3})[}|]")
_SCORE_RE = re.compile(r"(\d+)\s*[–\-—]\s*(\d+)")
_START_DATE_RE = re.compile(r"\{\{[Ss]tart date\|(\d{4})\|(\d{1,2})\|(\d{1,2})")
_FIELD_RES = {f: re.compile(r"^\s*\|\s*" + f + r"\s*=\s*(.*)$", re.M)
              for f in ("date", "team1", "team2", "score", "stadium", "time")}
_BOX_SPLIT_RE = re.compile(r"\{\{(?:#invoke:)?football box")
_KICKOFF_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
# Captures optional AM/PM suffix (handles "6:00 p.m." Wikipedia format, after
# &nbsp;/NBSP entities are stripped -- see _parse_kickoff_utc_iso).
_KICKOFF_AMPM_RE = re.compile(r"(\d{1,2}):(\d{2})\s*([AaPp]\.?[Mm]\.?)?")
_LIVE_MATCH_WINDOW_MIN = 130  # 90 min + stoppage + potential AET buffer

# UTC offset (hours) for each venue — June/July 2026, DST in effect.
# Wikipedia stores times in local venue time; we convert to UTC for storage.
_VENUE_UTC_OFFSET = {
    "azteca": -6, "akron": -6, "bbva": -6,          # Mexico (no DST since 2023)
    "bmo": -4, "bcplace": -7,                         # Canada (EDT / PDT)
    "sofi": -7, "levis": -7, "lumen": -7,             # Pacific (PDT)
    "att": -5, "nrg": -5, "arrowhead": -5,            # Central (CDT)
    "mercedesbenz": -4, "hardrock": -4,               # Eastern (EDT)
    "metlife": -4, "lincoln": -4, "gillette": -4,     # Eastern (EDT)
}


def _parse_kickoff_utc_iso(time_raw, venue, match_date_str):
    """Parse Wikipedia time field and return a UTC ISO datetime string, or None.

    Wikipedia stores local venue time in 12-hour format with a p.m. suffix, e.g.
    "6:00&nbsp;p.m.".  We convert to UTC using the venue's DST-adjusted offset.
    """
    if not time_raw or not match_date_str:
        return None
    cleaned = time_raw.replace("&nbsp;", " ").replace("&#160;", " ").replace("\xa0", " ")
    tm = _KICKOFF_AMPM_RE.search(cleaned)
    if not tm:
        return None
    h, m = int(tm.group(1)), int(tm.group(2))
    ampm = (tm.group(3) or "").lower().replace(".", "").strip()
    if ampm == "pm" and h != 12:
        h += 12
    elif ampm == "am" and h == 12:
        h = 0
    offset = _VENUE_UTC_OFFSET.get(venue or "", 0)
    try:
        y, mo, d = int(match_date_str[:4]), int(match_date_str[5:7]), int(match_date_str[8:10])
        # UTC = local − offset (offset is negative for western zones)
        utc_dt = datetime(y, mo, d, h, m, tzinfo=timezone.utc) - timedelta(hours=offset)
        return utc_dt.isoformat()
    except Exception:
        return None


def _is_complete(match_date_str, time_str):
    """Return False if the match is likely still in progress.

    Wikipedia editors update the score template during live matches, so a
    score appearing on the page doesn't mean the match has finished.  We
    guard against that by refusing to treat a match as played if we're still
    inside the expected duration window on match day.
    """
    if not match_date_str:
        return True
    try:
        match_date = date.fromisoformat(match_date_str)
    except ValueError:
        return True
    today = datetime.now(timezone.utc).date()
    if match_date < today:
        return True
    if match_date > today:
        return False
    # Same calendar day: check whether kickoff + window has elapsed.
    tm = _KICKOFF_TIME_RE.search(time_str or "")
    if tm:
        kickoff = datetime(match_date.year, match_date.month, match_date.day,
                           int(tm.group(1)), int(tm.group(2)), tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= kickoff + timedelta(minutes=_LIVE_MATCH_WINDOW_MIN)
    # Today but no parseable kickoff time — assume complete to avoid stalling.
    return True


def _api_get(params, retries=3):
    import time
    for attempt in range(retries):
        r = requests.get(API, params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def _wikitext(title):
    return _wikitext_many([title])[title]


def _wikitext_many(titles):
    """Batched fetch — MediaWiki allows up to 50 titles per request."""
    out = {}
    j = _api_get({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "format": "json", "titles": "|".join(titles),
    })
    for page in j["query"]["pages"].values():
        if "revisions" in page:
            out[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
    missing = [t for t in titles if t not in out]
    if missing:
        raise ValueError(f"No wikitext for: {missing}")
    return out


def _field(chunk, name):
    m = _FIELD_RES[name].search(chunk)
    return m.group(1).strip() if m else ""


def _parse_team(raw):
    m = _TEAM_RE.search(raw)
    return m.group(1).upper() if m else None


def _parse_date(raw):
    m = _START_DATE_RE.search(raw)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    raw = re.sub(r"\[\[|\]\]|\{\{.*?\}\}", "", raw).strip()
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw)
    if not m:
        return None
    try:
        return datetime.strptime(" ".join(m.groups()), "%d %B %Y").date().isoformat()
    except ValueError:
        return None


def _parse_stadium(raw):
    link = re.search(r"\[\[([^\]|]+)", raw)
    name = (link.group(1) if link else raw).strip().lower()
    return STADIUM_ALIASES.get(name)


def parse_group_page(wikitext, group):
    """Returns list of fixture dicts for one group page."""
    out = []
    chunks = _BOX_SPLIT_RE.split(wikitext)[1:]
    n = 0
    for chunk in chunks:
        chunk = chunk[:4000]
        t1 = _parse_team(_field(chunk, "team1"))
        t2 = _parse_team(_field(chunk, "team2"))
        if not t1 or not t2:
            continue
        n += 1
        score = _field(chunk, "score")
        sm = _SCORE_RE.search(score)
        match_date = _parse_date(_field(chunk, "date"))
        time_raw = _field(chunk, "time")
        venue = _parse_stadium(_field(chunk, "stadium"))
        fx = {
            "id": f"{group}{n}",
            "group": group,
            "home": t1,
            "away": t2,
            "date": match_date,
            "time_utc": _parse_kickoff_utc_iso(time_raw, venue, match_date),
            "venue": venue,
            "played": sm is not None and _is_complete(match_date, time_raw),
            "hg": int(sm.group(1)) if sm else None,
            "ag": int(sm.group(2)) if sm else None,
        }
        out.append(fx)
    return out


def fetch_group_fixtures(use_cache_on_error=True):
    """All 72 group fixtures from the 12 Wikipedia group pages.
    Caches to data/cache_fixtures.json; falls back to cache on network error."""
    by_id, _ = data.teams()
    valid_ids = set(by_id)
    fixtures = []
    try:
        titles = {f"2026 FIFA World Cup Group {g}": g for g in GROUPS}
        texts = _wikitext_many(list(titles))
        for title, g in titles.items():
            parsed = parse_group_page(texts[title], g)
            good = [f for f in parsed if f["home"] in valid_ids and f["away"] in valid_ids]
            if len(good) != 6:
                raise ValueError(
                    f"Group {g}: parsed {len(good)} valid fixtures (expected 6); "
                    f"raw teams: {[(f['home'], f['away']) for f in parsed]}")
            fixtures.extend(good)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": datetime.utcnow().isoformat(),
                       "fixtures": fixtures}, f, indent=1)
        return fixtures, "wikipedia"
    except Exception as e:
        if use_cache_on_error and CACHE.exists():
            with open(CACHE, encoding="utf-8") as f:
                cached = json.load(f)
            return cached["fixtures"], f"cache ({e})"
        raise


def fetch_knockout_fixtures(use_cache_on_error=True):
    """Played knockout fixtures from the Wikipedia knockout stage page.

    Returns a list of fixture dicts (same schema as group fixtures) for
    completed knockout matches only. Returns [] silently if the page
    doesn't exist yet (before the knockout stage begins Jun 28).
    """
    by_id, _ = data.teams()
    valid_ids = set(by_id)
    try:
        texts = _wikitext_many(["2026 FIFA World Cup knockout stage"])
        wikitext = texts.get("2026 FIFA World Cup knockout stage", "")
        fixtures = []
        chunks = _BOX_SPLIT_RE.split(wikitext)[1:]
        for n_chunk, chunk in enumerate(chunks, 1):
            chunk = chunk[:4000]
            t1 = _parse_team(_field(chunk, "team1"))
            t2 = _parse_team(_field(chunk, "team2"))
            if not t1 or not t2 or t1 not in valid_ids or t2 not in valid_ids:
                continue
            score = _field(chunk, "score")
            sm = _SCORE_RE.search(score)
            if not sm:
                continue  # upcoming match — skip
            fixtures.append({
                "id":     f"KO{n_chunk}",
                "group":  None,
                "home":   t1,
                "away":   t2,
                "date":   _parse_date(_field(chunk, "date")),
                "venue":  _parse_stadium(_field(chunk, "stadium")),
                "played": True,
                "hg":     int(sm.group(1)),
                "ag":     int(sm.group(2)),
            })
        with open(KNOCKOUT_CACHE, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": datetime.utcnow().isoformat(),
                       "fixtures": fixtures}, f, indent=1)
        return fixtures
    except Exception:
        if use_cache_on_error and KNOCKOUT_CACHE.exists():
            try:
                with open(KNOCKOUT_CACHE, encoding="utf-8") as f:
                    return json.load(f)["fixtures"]
            except Exception:
                pass
        return []


_DISCIPLINE_SECTION_RE = re.compile(r"==\s*Discipline\s*==(.*?)(?:\n==|\Z)", re.S)
_FAIRPLAY_SCORE_RE = re.compile(r'!\s*style="[^"]*"\s*\|\s*([−–—+-]?\d+)')
_DASH_RE = re.compile(r"[−–—]")


def parse_group_discipline(wikitext, valid_ids):
    """Parse a group page's '==Discipline==' wikitable into
    {team_id: fairplay_score}.

    Wikipedia editors already compute and publish each team's cumulative
    conduct score (yellow=-1, 2nd yellow=-3, red=-4, yellow+red=-5, FIFA
    regulations Art. 13.7) as the table's final column -- we read that total
    directly rather than re-deriving it from the per-match card sub-columns.
    A team absent from the result (no cards yet, or section not published
    yet) should be treated as 0 by the caller, not as missing data.
    """
    sec = _DISCIPLINE_SECTION_RE.search(wikitext)
    if not sec:
        return {}
    out = {}
    for block in sec.group(1).split("|-"):
        t = _parse_team(block)
        if not t or t not in valid_ids:
            continue
        m = _FAIRPLAY_SCORE_RE.search(block)
        if m:
            out[t] = int(_DASH_RE.sub("-", m.group(1)))
    return out


def fetch_group_discipline(use_cache_on_error=True):
    """Fair-play conduct scores from the same 12 Wikipedia group pages
    fetch_group_fixtures() reads. Separate request (not threaded through
    fetch_group_fixtures) so a parsing issue here can't affect the fixtures
    path. Caches to data/cache_discipline.json; falls back to cache on
    network error, same pattern as fetch_group_fixtures."""
    by_id, _ = data.teams()
    valid_ids = set(by_id)
    try:
        titles = {f"2026 FIFA World Cup Group {g}": g for g in GROUPS}
        texts = _wikitext_many(list(titles))
        scores = {}
        for title in titles:
            scores.update(parse_group_discipline(texts[title], valid_ids))
        with open(DISCIPLINE_CACHE, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": datetime.utcnow().isoformat(),
                       "scores": scores}, f, indent=1)
        return scores
    except Exception as e:
        if use_cache_on_error and DISCIPLINE_CACHE.exists():
            with open(DISCIPLINE_CACHE, encoding="utf-8") as f:
                return json.load(f)["scores"]
        raise


_THIRD_TABLE_ROW_RE = re.compile(
    r'!\s*scope="row"\s*\|\s*(\d+)\s*\n(.*?)(?=\n\|-|\n\|\}|\Z)', re.S)
_BOLD_GROUP_RE = re.compile(r"^'''([A-L])'''$")


def parse_third_place_table(wikitext, bracket_def):
    """Parse FIFA's Annex C table (published on Wikipedia as
    'Template:2026 FIFA World Cup third-place table') into
    {sorted_8_group_string: {match_no_str: group_letter}}.

    Column order is derived from bracket_def (the host group of each T-slot
    match, alphabetically) rather than hardcoded, so it can't silently drift
    from the actual bracket structure. Row 1 has a one-time rowspan spacer
    cell ('! rowspan="495" |') splitting its data across two '|'-prefixed
    lines instead of one; every other row is a single line. Splitting per
    line and dropping any '!'-led line handles both shapes uniformly.
    """
    t_matches = [m for m in bracket_def["r32"] if m["away"]["type"] == "T"]
    col_to_match = {m["home"]["group"]: m["match"] for m in t_matches}
    col_order = sorted(col_to_match)  # e.g. ['A','B','D','E','G','I','K','L']
    if len(col_order) != 8:
        raise ValueError(f"Expected 8 third-place slots, found {len(col_order)}")

    out = {}
    for m in _THIRD_TABLE_ROW_RE.finditer(wikitext):
        row_no, body = m.group(1), m.group(2)
        cells = []
        for line in body.split("\n"):
            line = line.strip()
            if not line or line.startswith("!"):
                continue
            if line.startswith("|"):
                line = line[1:]
            cells.extend(c.strip() for c in line.split("||"))
        if len(cells) != 20:
            raise ValueError(f"Row {row_no}: expected 20 cells, got {len(cells)}: {cells}")

        group_cells, assign_cells = cells[:12], cells[12:]
        qualifying = [g for g, c in zip(GROUPS, group_cells) if _BOLD_GROUP_RE.match(c)]
        if len(qualifying) != 8:
            raise ValueError(f"Row {row_no}: expected 8 qualifying groups, got {qualifying}")

        slot_map = {}
        for col, cell in zip(col_order, assign_cells):
            if not re.fullmatch(r"3[A-L]", cell):
                raise ValueError(f"Row {row_no}, col 1{col}: bad assignment cell {cell!r}")
            slot_map[str(col_to_match[col])] = cell[1:]
        if set(slot_map.values()) != set(qualifying):
            raise ValueError(f"Row {row_no}: assignment groups {sorted(slot_map.values())} "
                              f"!= qualifying groups {sorted(qualifying)}")

        key = "".join(sorted(qualifying))
        if key in out:
            raise ValueError(f"Row {row_no}: duplicate combination {key}")
        out[key] = slot_map

    if len(out) != 495:
        raise ValueError(f"Expected 495 combinations, parsed {len(out)}")
    return out


def fetch_third_place_table():
    """One-time fetch: parse Annex C from Wikipedia and write
    data/third_place_table.json. Static regulation data fixed before the
    tournament started -- not part of the recurring refresh pipeline."""
    wikitext = _wikitext("Template:2026 FIFA World Cup third-place table")
    table = parse_third_place_table(wikitext, data.bracket())
    with open(THIRD_TABLE_PATH, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=1, sort_keys=True)
    return table
