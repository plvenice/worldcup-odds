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
OUTRIGHT_DAILY_CAP = 8  # ~240 credits/month — well within 500 free
H2H_DAILY_CAP = 3


def _load_tuned_blend_weight(fallback=0.65, min_n=10):
    """Return calibrated blend weight if enough data exists, else fallback.

    Reads out/blend_optimum.json written by pipeline/backtest/calibrate_blend.py.
    Only kicks in once min_n completed priced matches have been scored.
    """
    p = STATE.parent / "blend_optimum.json"
    try:
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("n", 0) >= min_n:
                return float(d["weight"])
    except Exception:
        pass
    return fallback


# Weight on the betting market when blending market match odds with the
# (calibrated) model. Markets reliably beat structural models on match
# outcomes, so we lean market. Starts at the principled default (0.65);
# after MIN_SAMPLES=10 completed priced matches, calibrate_blend.py tunes
# this empirically and writes out/blend_optimum.json which overrides here.
MARKET_BLEND_WEIGHT = _load_tuned_blend_weight()

NAME_TO_ID = {
    "mexico": "MEX", "south africa": "RSA", "south korea": "KOR",
    "korea republic": "KOR", "czech republic": "CZE", "czechia": "CZE",
    "canada": "CAN", "bosnia and herzegovina": "BIH", "qatar": "QAT",
    "switzerland": "SUI", "brazil": "BRA", "morocco": "MAR", "haiti": "HAI",
    "scotland": "SCO", "usa": "USA", "united states": "USA", "paraguay": "PAR",
    "australia": "AUS", "turkey": "TUR", "turkiye": "TUR",
    "germany": "GER", "curacao": "CUW",
    "ivory coast": "CIV", "cote d'ivoire": "CIV", "ecuador": "ECU", "netherlands": "NED",
    "japan": "JPN", "sweden": "SWE", "tunisia": "TUN", "belgium": "BEL",
    "egypt": "EGY", "iran": "IRN", "new zealand": "NZL", "spain": "ESP",
    "cape verde": "CPV", "saudi arabia": "KSA", "uruguay": "URU",
    "france": "FRA", "senegal": "SEN", "iraq": "IRQ", "norway": "NOR",
    "argentina": "ARG", "algeria": "ALG", "austria": "AUT", "jordan": "JOR",
    "portugal": "POR", "dr congo": "COD", "congo dr": "COD",
    "uzbekistan": "UZB", "colombia": "COL", "england": "ENG",
    "croatia": "CRO", "ghana": "GHA", "panama": "PAN",
}


def _load_state():
    today = datetime.now(timezone.utc).date().isoformat()
    state = {"date": today}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if state.get("date") != today:
        state = {"date": today}
    return state, today


def _budget_ok(kind, cap):
    state, today = _load_state()
    if state.get(kind, 0) >= cap:
        return False, state
    return True, state


def _budget_spend(state, kind):
    state[kind] = state.get(kind, 0) + 1
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")


def _devig_three(home, draw, away):
    """Decimal odds for the three match outcomes -> vig-stripped probs."""
    raw = [1.0 / home, 1.0 / draw, 1.0 / away]
    s = sum(raw)
    return tuple(x / s for x in raw)


def fetch_outrights():
    """Returns {"fetched_at", "implied": {team_id: prob}} or None.
    Implied probabilities are vig-stripped (normalized to 1) median-of-books."""
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    ok, state = _budget_ok("outright", OUTRIGHT_DAILY_CAP)
    if not ok:
        return None
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup_winner/odds",
            params={"apiKey": key, "regions": "us,eu", "markets": "outrights",
                    "oddsFormat": "decimal"},
            timeout=20)
        _budget_spend(state, "outright")
        r.raise_for_status()
        events = r.json()
        if not events:
            return None
        # collect per-team decimal odds across bookmakers, take median
        per_team = {}
        for bm in events[0].get("bookmakers", []):
            for mk in bm.get("markets", []):
                for oc in mk.get("outcomes", []):
                    tid = NAME_TO_ID.get(data.normalize_name(oc["name"]))
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


def _median(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def fetch_h2h():
    """Per-match vig-stripped market probabilities for upcoming WC matches.

    Returns {"fetched_at", "matches": [{home, away, ph, pd, pa}, ...]} or None.
    home/away are FIFA codes oriented as the bookmaker's home/away. Uses one
    sharp region (eu) and a median across books. Bookmakers only price imminent
    matches, so this naturally covers the near term and is empty otherwise.
    """
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        return None
    ok, state = _budget_ok("h2h", H2H_DAILY_CAP)
    if not ok:
        return None
    try:
        r = requests.get(
            "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds",
            params={"apiKey": key, "regions": "eu", "markets": "h2h",
                    "oddsFormat": "decimal"},
            timeout=20)
        _budget_spend(state, "h2h")
        r.raise_for_status()
        events = r.json() or []
        out = []
        for ev in events:
            hid = NAME_TO_ID.get(data.normalize_name(ev.get("home_team", "")))
            aid = NAME_TO_ID.get(data.normalize_name(ev.get("away_team", "")))
            if not hid or not aid:
                continue
            home_o, draw_o, away_o = [], [], []
            for bm in ev.get("bookmakers", []):
                for mk in bm.get("markets", []):
                    if mk.get("key") != "h2h":
                        continue
                    price = {}
                    for oc in mk.get("outcomes", []):
                        nm = data.normalize_name(oc["name"])
                        if nm == "draw":
                            price["draw"] = float(oc["price"])
                        elif NAME_TO_ID.get(nm) == hid:
                            price["home"] = float(oc["price"])
                        elif NAME_TO_ID.get(nm) == aid:
                            price["away"] = float(oc["price"])
                    if len(price) == 3:
                        home_o.append(price["home"])
                        draw_o.append(price["draw"])
                        away_o.append(price["away"])
            if not home_o:
                continue
            ph, pd, pa = _devig_three(_median(home_o), _median(draw_o), _median(away_o))
            out.append({"home": hid, "away": aid,
                        "ph": round(ph, 4), "pd": round(pd, 4), "pa": round(pa, 4)})
        if not out:
            return None
        return {"fetched_at": datetime.now(timezone.utc).isoformat(), "matches": out}
    except Exception:
        return None
