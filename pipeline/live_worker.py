"""Always-on live worker (Railway).

Polls API-Football on an adaptive cadence — fast (~3x/min) only while World Cup
matches are live, a 30-minute heartbeat otherwise, and it wakes ~2 min before
each scheduled kickoff. Computes in-match win probabilities and serves them as
JSON for the dashboard to poll.

Endpoints:
  GET /live.json  -> {updated_at, live: bool, matches: [...]}
  GET /health     -> {ok: true}

Env:
  API_FOOTBALL_KEY   (required for live data; without it serves an empty feed)
  PORT               (Railway sets this; default 8080)
  LIVE_INTERVAL      seconds between polls while live (default 20)
  IDLE_INTERVAL      seconds between heartbeats when idle (default 1800)
  FORECAST_URL       pre-match lambdas source (default: repo data branch)
  ALLOW_ORIGIN       CORS origin (default *)
"""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26 import apifootball
from wc26.live import live_outcome

LIVE_INTERVAL = int(os.environ.get("LIVE_INTERVAL", "20"))
IDLE_INTERVAL = int(os.environ.get("IDLE_INTERVAL", "1800"))
FORECAST_URL = os.environ.get(
    "FORECAST_URL",
    "https://raw.githubusercontent.com/plvenice/worldcup-odds/data/forecast.json")
ALLOW_ORIGIN = os.environ.get("ALLOW_ORIGIN", "*")
FORECAST_REFRESH = 900  # re-pull pre-match lambdas every 15 min

_LOCK = threading.Lock()
_STATE = {"updated_at": None, "live": False, "matches": [], "title_updates": {}}
_LAMBDAS = {}          # frozenset({home,away}) -> {"home": code, "lh":, "la":, "group":}
_LEVERAGE = {}         # frozenset({home,away}) -> {team_id: [p_title_h, p_title_d, p_title_a]}
_LAMBDAS_AT = 0.0


def refresh_lambdas(force=False):
    global _LAMBDAS, _LEVERAGE, _LAMBDAS_AT
    if not force and time.time() - _LAMBDAS_AT < FORECAST_REFRESH:
        return
    try:
        fc = requests.get(FORECAST_URL, timeout=15).json()
        m = {}
        lev = {}
        for mt in fc.get("matches", []):
            lam = mt.get("lambdas")
            if mt.get("played") or not lam:
                continue
            key = frozenset((mt["home"], mt["away"]))
            m[key] = {
                "home": mt["home"], "lh": lam[0], "la": lam[1], "group": mt.get("group")}
            if mt.get("leverage"):
                lev[key] = {
                    l["team"]: l["p_title_by_outcome"]
                    for l in mt["leverage"]
                    if l.get("p_title_by_outcome")
                }
        if m:
            _LAMBDAS = m
        if lev:
            _LEVERAGE = lev
        _LAMBDAS_AT = time.time()
    except Exception:
        pass


def compute_live(fixtures):
    """Returns (matches, title_updates).

    title_updates: {team_id: conditional_p_title} for all teams whose group has
    a live match. Uses the pre-computed leverage table from forecast.json so no
    extra MC calls are needed — it's a weighted sum over match outcomes.
    Leverage outcomes are indexed 0=home_wins, 1=draw, 2=away_wins relative to
    the fixture's home/away assignment in forecast.json.
    """
    out = []
    title_updates = {}
    for fx in fixtures:
        rec = {k: fx[k] for k in ("home", "away", "hg", "ag", "minute", "status")}
        ref = _LAMBDAS.get(frozenset((fx["home"], fx["away"])))
        if ref:
            # orient pre-match lambdas to the live match's home/away
            if ref["home"] == fx["home"]:
                lh, la = ref["lh"], ref["la"]
            else:
                lh, la = ref["la"], ref["lh"]
            ph, pd, pa = live_outcome(lh, la, fx["hg"], fx["ag"], fx["minute"])
            rec["p_home"] = round(ph, 4)
            rec["p_draw"] = round(pd, 4)
            rec["p_away"] = round(pa, 4)
            rec["group"] = ref.get("group")

            # Conditional title odds via leverage: w = [p_h, p_d, p_a] oriented
            # to the fixture (index 0=home_wins, 1=draw, 2=away_wins).
            lev_key = frozenset((fx["home"], fx["away"]))
            lev = _LEVERAGE.get(lev_key)
            if lev:
                w = [ph, pd, pa] if ref["home"] == fx["home"] else [pa, pd, ph]
                for team, by_outcome in lev.items():
                    title_updates[team] = round(
                        sum(w[k] * by_outcome[k] for k in range(3)), 4)
        out.append(rec)
    return out, title_updates


def poll_loop():
    refresh_lambdas(force=True)
    while True:
        refresh_lambdas()
        fixtures = apifootball.fetch_live()
        matches, title_updates = compute_live(fixtures)
        with _LOCK:
            _STATE["updated_at"] = datetime.now(timezone.utc).isoformat()
            _STATE["live"] = len(matches) > 0
            _STATE["matches"] = matches
            _STATE["title_updates"] = title_updates
        if matches:
            time.sleep(LIVE_INTERVAL)
        else:
            time.sleep(_idle_sleep())


def _idle_sleep():
    """Sleep until ~2 min before the next kickoff, capped at IDLE_INTERVAL."""
    try:
        now = datetime.now(timezone.utc)
        future = [k for k in apifootball.fetch_today_kickoffs() if k > now]
        if future:
            secs = (future[0] - now).total_seconds() - 120
            return max(15, min(IDLE_INTERVAL, int(secs)))
    except Exception:
        pass
    return IDLE_INTERVAL


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, code=200):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._send({"ok": True})
        if self.path.startswith("/live"):
            with _LOCK:
                return self._send(dict(_STATE))
        self._send({"error": "not found"}, 404)

    def log_message(self, *args):
        pass  # quiet


def main():
    threading.Thread(target=poll_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"live worker serving on :{port} "
          f"(live={LIVE_INTERVAL}s / idle={IDLE_INTERVAL}s)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
