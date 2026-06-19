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
_LIVE_MATCH_WINDOW_MIN = 130  # 90 min + stoppage + potential AET buffer


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
        tm = _KICKOFF_TIME_RE.search(time_raw or "")
        fx = {
            "id": f"{group}{n}",
            "group": group,
            "home": t1,
            "away": t2,
            "date": match_date,
            "time_utc": f"{int(tm.group(1)):02d}:{tm.group(2)}" if tm else None,
            "venue": _parse_stadium(_field(chunk, "stadium")),
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
