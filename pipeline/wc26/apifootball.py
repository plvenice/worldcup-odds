"""API-Football (api-sports.io) client for live World Cup match state.

Needs API_FOOTBALL_KEY. World Cup is league 1, season 2026. Returns the
current score, minute, and status for live matches; team names are mapped to
our FIFA codes. Red cards are not pulled in the fast loop (they need a second
endpoint) -- a future enhancement; the model defaults to zero.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

from .odds import NAME_TO_ID as _ODDS_NAMES

BASE = "https://v3.football.api-sports.io"
WC_LEAGUE = 1
SEASON = 2026

# API-Football country-name spellings that differ from the odds feed.
_EXTRA = {
    "iran": "IRN", "ir iran": "IRN", "korea republic": "KOR",
    "south korea": "KOR", "cote d'ivoire": "CIV",
    "ivory coast": "CIV", "curacao": "CUW",
    "turkiye": "TUR", "turkey": "TUR",
    "czechia": "CZE", "czech republic": "CZE", "usa": "USA",
    "united states": "USA", "congo dr": "COD", "dr congo": "COD",
    "cape verde islands": "CPV", "cape verde": "CPV",
}
NAME_TO_ID = {**_ODDS_NAMES, **_EXTRA}

# Statuses API-Football reports while a match is in play.
LIVE_STATUSES = {"1H", "2H", "ET", "BT", "P", "LIVE", "HT", "INT"}


def _team_id(name):
    return NAME_TO_ID.get((name or "").strip().lower())


def _headers():
    return {"x-apisports-key": os.environ.get("API_FOOTBALL_KEY", "")}


def fetch_live():
    """Currently-live WC matches: [{home, away, hg, ag, minute, status,
    fixture_id}]. home/away are FIFA codes. [] on any failure / no key."""
    if not os.environ.get("API_FOOTBALL_KEY"):
        return []
    try:
        r = requests.get(f"{BASE}/fixtures",
                         params={"league": WC_LEAGUE, "season": SEASON, "live": "all"},
                         headers=_headers(), timeout=15)
        r.raise_for_status()
        out = []
        for it in r.json().get("response", []):
            fx = it.get("fixture", {})
            status = (fx.get("status") or {})
            tg = it.get("teams", {})
            go = it.get("goals", {})
            hid = _team_id((tg.get("home") or {}).get("name"))
            aid = _team_id((tg.get("away") or {}).get("name"))
            if not hid or not aid:
                continue
            out.append({
                "fixture_id": fx.get("id"),
                "home": hid, "away": aid,
                "hg": go.get("home") or 0, "ag": go.get("away") or 0,
                "minute": status.get("elapsed") or 0,
                "status": status.get("short", ""),
            })
        return out
    except Exception:
        return []


def fetch_today_kickoffs():
    """UTC datetimes of today's + tomorrow's WC kickoffs. [] on failure.

    Fetches two UTC dates to handle the day-boundary case where a late-evening
    kickoff in the Americas falls on the following UTC date.
    """
    if not os.environ.get("API_FOOTBALL_KEY"):
        return []
    try:
        now = datetime.now(timezone.utc)
        dates = [
            now.date().isoformat(),
            (now.date() + timedelta(days=1)).isoformat(),
        ]
        out = []
        for d in dates:
            r = requests.get(f"{BASE}/fixtures",
                             params={"league": WC_LEAGUE, "season": SEASON, "date": d},
                             headers=_headers(), timeout=15)
            r.raise_for_status()
            for it in r.json().get("response", []):
                ts = (it.get("fixture") or {}).get("timestamp")
                if ts:
                    out.append(datetime.fromtimestamp(ts, tz=timezone.utc))
        return sorted(out)
    except Exception:
        return []


def fetch_season_kickoffs():
    """All future WC kickoff times for the season. Called once on startup and
    refreshed every 6h so the worker knows the full schedule without making
    per-day API calls. [] on failure / no key."""
    if not os.environ.get("API_FOOTBALL_KEY"):
        return []
    try:
        r = requests.get(f"{BASE}/fixtures",
                         params={"league": WC_LEAGUE, "season": SEASON},
                         headers=_headers(), timeout=30)
        r.raise_for_status()
        now = datetime.now(timezone.utc)
        out = []
        for it in r.json().get("response", []):
            ts = (it.get("fixture") or {}).get("timestamp")
            if ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                if dt > now - timedelta(hours=3):
                    out.append(dt)
        return sorted(out)
    except Exception:
        return []


def fetch_current_injuries():
    """Currently-reported WC injuries/unavailability: [{team, player}].
    team mapped to FIFA codes via _team_id(). [] on failure / no key."""
    if not os.environ.get("API_FOOTBALL_KEY"):
        return []
    try:
        r = requests.get(f"{BASE}/injuries",
                         params={"league": WC_LEAGUE, "season": SEASON},
                         headers=_headers(), timeout=15)
        r.raise_for_status()
        out = []
        for it in r.json().get("response", []):
            tid = _team_id((it.get("team") or {}).get("name"))
            pname = (it.get("player") or {}).get("name")
            if tid and pname:
                out.append({"team": tid, "player": pname})
        return out
    except Exception:
        return []
