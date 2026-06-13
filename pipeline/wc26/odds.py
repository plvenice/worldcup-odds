"""Betting-market odds via The Odds API (free tier: 500 credits/month).

Silently no-ops without ODDS_API_KEY. Budget guard: out/odds_state.json
tracks calls per UTC day (carried across Actions runs via the data branch);
hard cap 2 pulls/day keeps us well inside free credits.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import data

STATE = data.ROOT / "out" / "odds_state.json"
DAILY_CAP = 2

NAME_TO_ID = {
    "mexico": "MEX", "south africa": "RSA", "south korea": "KOR",
    "korea republic": "KOR", "czech republic": "CZE", "czechia": "CZE",
    "canada": "CAN", "bosnia and herzegovina": "BIH", "qatar": "QAT",
    "switzerland": "SUI", "brazil": "BRA", "morocco": "MAR", "haiti": "HAI",
    "scotland": "SCO", "usa": "USA", "united states": "USA", "paraguay": "PAR",
    "australia": "AUS", "turkey": "TUR", "germany": "GER", "curacao": "CUW",
    "ivory coast": "CIV", "ecuador": "ECU", "netherlands": "NED",
    "japan": "JPN", "sweden": "SWE", "tunisia": "TUN", "belgium": "BEL",
    "egypt": "EGY", "iran": "IRN", "new zealand": "NZL", "spain": "ESP",
    "cape verde": "CPV", "saudi arabia": "KSA", "uruguay": "URU",
    "france": "FRA", "senegal": "SEN", "iraq": "IRQ", "norway": "NOR",
    "argentina": "ARG", "algeria": "ALG", "austria": "AUT", "jordan": "JOR",
    "portugal": "POR", "dr congo": "COD", "congo dr": "COD",
    "uzbekistan": "UZB", "colombia": "COL", "england": "ENG",
    "croatia": "CRO", "ghana": "GHA", "panama": "PAN",
}


def _budget_ok():
    today = datetime.now(timezone.utc).date().isoformat()
    state = {"date": today, "calls": 0}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if state.get("date") != today:
        state = {"date": today, "calls": 0}
    if state["calls"] >= DAILY_CAP:
        return False, state
    return True, state


def _budget_spend(state):
    state["calls"] = state.get("calls", 0) + 1
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")


def fetch_outrights():
    """Returns {"fetched_at", "implied": {team_id: prob}} or None.
    Implied probabilities are vig-stripped (normalized to 1) median-of-books."""
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    ok, state = _budget_ok()
    if not ok:
        return None
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup_winner/odds",
            params={"apiKey": key, "regions": "us,eu", "markets": "outrights",
                    "oddsFormat": "decimal"},
            timeout=20)
        _budget_spend(state)
        r.raise_for_status()
        events = r.json()
        if not events:
            return None
        # collect per-team decimal odds across bookmakers, take median
        per_team = {}
        for bm in events[0].get("bookmakers", []):
            for mk in bm.get("markets", []):
                for oc in mk.get("outcomes", []):
                    tid = NAME_TO_ID.get(oc["name"].strip().lower())
                    if tid and oc.get("price"):
                        per_team.setdefault(tid, []).append(float(oc["price"]))
        if not per_team:
            return None
        med = {t: sorted(v)[len(v) // 2] for t, v in per_team.items()}
        raw = {t: 1.0 / o for t, o in med.items()}
        total = sum(raw.values())
        implied = {t: p / total for t, p in raw.items()}
        return {"fetched_at": datetime.now(timezone.utc).isoformat(),
                "implied": implied}
    except Exception:
        return None
