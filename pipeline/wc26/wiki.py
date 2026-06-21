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


def _wikitext_many(titles, require_all=True):
    """Batched fetch — MediaWiki allows up to 50 titles per request.

    If require_all is False, a title the API didn't return (page move,
    redirect, transient edge case) is simply omitted from the result instead
    of failing the whole batch. Callers that can isolate per-title failures
    (fetch_group_fixtures) should pass False; single-title callers want the
    default strict behavior since there's nothing left to partially return.
    """
    out = {}
    j = _api_get({
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "format": "json", "titles": "|".join(titles),
    })
    for page in j["query"]["pages"].values():
        if "revisions" in page:
            out[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
    if require_all:
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

    Each group's box count (expect 6) is validated independently. Wikipedia
    group pages are edited live during match windows, so a single page can
    transiently show the wrong box count mid-edit -- that used to make the
    whole fetch raise and fall back to a stale cache for all 12 groups. Now
    a group that fails validation gets one short retry, and only that group
    (not the other 11) falls back to its own cached fixtures.
    Caches to data/cache_fixtures.json; falls back to cache on network error.
    """
    import time as _time

    by_id, _ = data.teams()
    valid_ids = set(by_id)
    cached_by_group = {}
    if CACHE.exists():
        with open(CACHE, encoding="utf-8") as f:
            for fx in json.load(f).get("fixtures", []):
                cached_by_group.setdefault(fx["group"], []).append(fx)

    titles = {f"2026 FIFA World Cup Group {g}": g for g in GROUPS}
    try:
        # require_all=False: a single missing title (page rename/redirect)
        # must not nuke the other 11 groups' freshly fetched text either --
        # it's handled the same as a bad box count, per group, below.
        texts = _wikitext_many(list(titles), require_all=False)
    except Exception as e:
        if use_cache_on_error and cached_by_group:
            all_cached = [fx for fxs in cached_by_group.values() for fx in fxs]
            return all_cached, f"cache (fetch failed: {e})", {g: str(e) for g in GROUPS}
        raise

    fixtures = []
    stale = {}
    for title, g in titles.items():
        page_text = texts.get(title)
        good = []
        if page_text is not None:
            good = [f for f in parse_group_page(page_text, g)
                    if f["home"] in valid_ids and f["away"] in valid_ids]
        if len(good) != 6:
            # Missing page or wrong box count -- likely mid-edit (live
            # tournament pages are edited constantly). One short, isolated
            # retry before falling back to this group's own cache. The
            # retry itself must not raise past this point -- a timeout or
            # genuinely-gone page here should degrade to this one group's
            # cache fallback, not blow up the other 11 groups' results.
            _time.sleep(8)
            try:
                retried = parse_group_page(_wikitext(title), g)
                good = [f for f in retried if f["home"] in valid_ids and f["away"] in valid_ids]
            except Exception:
                good = []
        if len(good) == 6:
            fixtures.extend(good)
            continue
        err = (f"parsed {len(good)} valid fixtures (expected 6); "
               f"raw teams: {[(f['home'], f['away']) for f in good]}")
        if g in cached_by_group:
            fixtures.extend(cached_by_group[g])
            stale[g] = err
        else:
            raise ValueError(f"Group {g}: {err}")

    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.utcnow().isoformat(),
                   "fixtures": fixtures}, f, indent=1)
    source = "wikipedia" if not stale else f"wikipedia (stale: {', '.join(stale)})"
    return fixtures, source, stale


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
