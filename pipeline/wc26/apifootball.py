"""API-Football (api-sports.io) client for live World Cup match state.

Needs API_FOOTBALL_KEY. World Cup is league 1, season 2026. Returns the
current score, minute, and status for live matches; team names are mapped to
our FIFA codes. Red cards are not pulled in the fast loop (they need a second
endpoint) — a future enhancement; the model defaults to zero.
"""
import os
from datetime import datetime, timezone

import requests

from .odds import NAME_TO_ID as _ODDS_NAMES

BASE = "https://v3.football.api-sports.io"
WC_LEAGUE = 1
SEASON = 2026

# API-Football country-name spellings that differ from the odds feed.
_EXTRA = {
    "iran": "IRN", "ir iran": "IRN", "korea republic": "KOR",
    "south korea": "KOR", "côte d'ivoire": "CIV", "cote d'ivoire": "CIV",
    "ivory coast": "CIV", "curaçao": "CUW", "curacao": "CUW",
    "türkiye": "TUR", "turkiye": "TUR", "turkey": "TUR",
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
    """UTC datetimes of today's WC kickoffs (for schedule-aware waking). []
    on failure."""
    if not os.environ.get("API_FOOTBALL_KEY"):
        return []
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        r = requests.get(f"{BASE}/fixtures",
                         params={"league": WC_LEAGUE, "season": SEASON, "date": today},
                         headers=_headers(), timeout=15)
        r.raise_for_status()
        out = []
        for it in r.json().get("response", []):
            ts = (it.get("fixture") or {}).get("timestamp")
            if ts:
                out.append(datetime.fromtimestamp(ts, tz=timezone.utc))
        return sorted(out)
    except Exception:
        return []
