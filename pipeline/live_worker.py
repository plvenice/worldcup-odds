"""Always-on live worker (Railway).

Polls API-Football on an adaptive cadence -- fast (~3x/min) only while World Cup
matches are live, a 30-minute heartbeat otherwise, and it wakes ~2 min before
each scheduled kickoff. Computes in-match win probabilities and serves them as
JSON for the dashboard to poll.

Also triggers the GitHub Actions refresh workflow every 15 minutes via
workflow_dispatch, bypassing GitHub's unreliable cron scheduler.

Also runs a live re-simulation (5k paths) every poll cycle while a match is live,
propagating the current scoreline through group standings and bracket odds.

Endpoints:
  GET /live.json          -> {updated_at, live, matches, title_updates}
  GET /live_forecast.json -> {available, teams, groups_affected, ...}
  GET /health             -> {ok: true}

Env:
  API_FOOTBALL_KEY   (required for live data)
  GH_DISPATCH_TOKEN  (GitHub PAT with workflow scope; enables 15-min dispatch)
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

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc26 import apifootball, data as wc_data
from wc26.live import live_outcome
from wc26.mc import simulate as mc_simulate

LIVE_INTERVAL = int(os.environ.get("LIVE_INTERVAL", "20"))
IDLE_INTERVAL = int(os.environ.get("IDLE_INTERVAL", "1800"))
FORECAST_URL = os.environ.get(
    "FORECAST_URL",
    "https://raw.githubusercontent.com/plvenice/worldcup-odds/data/forecast.json")
ALLOW_ORIGIN = os.environ.get("ALLOW_ORIGIN", "*")
FORECAST_REFRESH = 900

GH_DISPATCH_TOKEN = os.environ.get("GH_DISPATCH_TOKEN", "")
GH_REPO = "plvenice/worldcup-odds"
GH_WORKFLOW = "refresh.yml"
DISPATCH_INTERVAL = 900

RESIM_NSIMS = 5000
WC2026_HOSTS = {"USA", "CAN", "MEX"}


def dispatch_loop():
    """Fires workflow_dispatch on the refresh workflow every 15 min."""
    if not GH_DISPATCH_TOKEN:
        print("GH_DISPATCH_TOKEN not set -- pipeline dispatch disabled", flush=True)
        return
    time.sleep(60)
    while True:
        try:
            r = requests.post(
                f"https://api.github.com/repos/{GH_REPO}/actions/workflows/{GH_WORKFLOW}/dispatches",
                headers={
                    "Authorization": f"Bearer {GH_DISPATCH_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={"ref": "master"},
                timeout=15,
            )
            if r.status_code == 204:
                print(f"dispatch ok ({datetime.now(timezone.utc).isoformat()})", flush=True)
            else:
                print(f"dispatch {r.status_code}: {r.text[:120]}", flush=True)
        except Exception as e:
            print(f"dispatch error: {e}", flush=True)
        time.sleep(DISPATCH_INTERVAL)


_LOCK = threading.Lock()
_STATE = {"updated_at": None, "live": False, "matches": [], "title_updates": {}}
_LAMBDAS = {}
_LEVERAGE = {}
_LAMBDAS_AT = 0.0
_FORECAST_RAW = {}

_LIVE_FORECAST_LOCK = threading.Lock()
_LIVE_FORECAST = {"available": False}
_RESIM_RUNNING = threading.Event()
_WC_DATA_LOCK = threading.Lock()
_WC_BRACKET = None
_WC_VENUES = None

# Post-match linger: hold last conditioned values for this many seconds after
# all live matches end, so the dashboard doesn't snap back to stale forecast.json
# while the pipeline is still catching up (15-min refresh cycle).
_LINGER_SECS = 1200
_LINGER_UNTIL = 0.0
_LAST_LIVE_TITLE_UPDATES = {}


def _get_wc_data():
    global _WC_BRACKET, _WC_VENUES
    with _WC_DATA_LOCK:
        if _WC_BRACKET is None:
            _WC_BRACKET = wc_data.bracket()
            _WC_VENUES = wc_data.venues()
    return _WC_BRACKET, _WC_VENUES


def refresh_lambdas(force=False):
    global _LAMBDAS, _LEVERAGE, _LAMBDAS_AT, _FORECAST_RAW
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
        _FORECAST_RAW = fc
        _LAMBDAS_AT = time.time()
    except Exception:
        pass


def rebuild_state_from_forecast(fc, live_win_probs):
    """Reconstruct a simulation state from forecast.json.

    live_win_probs: {frozenset({home, away}): (p_home, p_draw, p_away)}
    Overrides blend_probs for live fixtures with current in-match win probs.
    For all other unplayed fixtures, uses the blended probs from forecast.json.
    dr=0/total_factor=1 are dummy values -- blend_probs overrides W/D/L outcome.
    """
    teams = fc["teams"]
    ids = [t["id"] for t in teams]
    ratings = np.array([t["elo"] for t in teams], dtype=float)

    groups = {g: [row["team"] for row in rows] for g, rows in fc["groups"].items()}

    fixtures = []
    for m in fc.get("matches", []):
        if not m.get("group"):
            continue
        key = frozenset((m["home"], m["away"]))
        is_live = key in live_win_probs
        fx = {
            "id": m["id"],
            "group": m["group"],
            "home": m["home"],
            "away": m["away"],
            # If the match is currently live, treat it as unplayed so the
            # simulation uses live_win_probs rather than a stale partial score
            # that wiki.py may have ingested mid-game.
            "played": m.get("played", False) and not is_live,
            "hg": m.get("hg") or 0,
            "ag": m.get("ag") or 0,
            "dr": 0.0,
            "total_factor": 1.0,
        }
        if not fx["played"]:
            if is_live:
                ph, pd, pa = live_win_probs[key]
                fx["blend_probs"] = [float(ph), float(pd), float(pa)]
            elif m.get("probs"):
                p = m["probs"]
                fx["blend_probs"] = [p["home"], p["draw"], p["away"]]
        fixtures.append(fx)

    bracket_def, venues = _get_wc_data()

    return {
        "ids": ids,
        "ratings": ratings,
        "groups": groups,
        "fixtures": fixtures,
        "bracket_def": bracket_def,
        "venues": venues,
        "hosts": {t: t for t in ids if t in WC2026_HOSTS},
        "elo": {t["id"]: t["elo"] for t in teams},
        "source": "live-resim",
        "attributions": {},
    }


def slim_aggregate(state, res, nsims):
    """Extract per-team advancement probabilities from sim result."""
    ids = state["ids"]
    n = float(nsims)
    advance = (res.group_pos <= 2) | res.third_advanced
    champ = np.bincount(res.champion, minlength=len(ids))

    out = {}
    for i, t in enumerate(ids):
        out[t] = {
            "p_title": round(float(champ[i] / n), 4),
            "p_final": round(float(res.reach["final"][:, i].mean()), 4),
            "p_sf": round(float(res.reach["sf"][:, i].mean()), 4),
            "p_qf": round(float(res.reach["qf"][:, i].mean()), 4),
            "p_r16": round(float(res.reach["r16"][:, i].mean()), 4),
            "p_r32": round(float(res.reach["r32"][:, i].mean()), 4),
            "p_group_win": round(float((res.group_pos[:, i] == 1).mean()), 4),
            "p_group_second": round(float((res.group_pos[:, i] == 2).mean()), 4),
            "p_third_advance": round(float(res.third_advanced[:, i].mean()), 4),
            "p_advance": round(float(advance[:, i].mean()), 4),
        }
    return out


def run_live_resim():
    """5k-path re-sim conditioned on current live scores. Skips if already running."""
    if _RESIM_RUNNING.is_set():
        return
    _RESIM_RUNNING.set()
    try:
        with _LOCK:
            fc = dict(_FORECAST_RAW)
            matches = list(_STATE["matches"])

        if not fc or not matches:
            return

        live_win_probs = {}
        groups_affected = set()
        live_teams = []
        for m in matches:
            if "p_home" not in m:
                continue
            key = frozenset((m["home"], m["away"]))
            live_win_probs[key] = (m["p_home"], m.get("p_draw", 0.0), m["p_away"])
            if m.get("group"):
                groups_affected.add(m["group"])
            live_teams += [m["home"], m["away"]]

        if not live_win_probs:
            return

        t0 = time.time()
        state = rebuild_state_from_forecast(fc, live_win_probs)
        res = mc_simulate(state, nsims=RESIM_NSIMS)
        teams_out = slim_aggregate(state, res, RESIM_NSIMS)
        elapsed = round(time.time() - t0, 2)

        with _LIVE_FORECAST_LOCK:
            _LIVE_FORECAST.update({
                "available": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "nsims": RESIM_NSIMS,
                "teams": teams_out,
                "live_teams": list(set(live_teams)),
                "groups_affected": list(groups_affected),
                "elapsed_s": elapsed,
            })
        print(f"resim {elapsed}s ({RESIM_NSIMS} paths, groups {groups_affected})", flush=True)
    except Exception as e:
        print(f"resim error: {e}", flush=True)
    finally:
        _RESIM_RUNNING.clear()


def compute_live(fixtures):
    """Returns (matches, title_updates) from live API-Football data."""
    out = []
    title_updates = {}
    for fx in fixtures:
        rec = {k: fx[k] for k in ("home", "away", "hg", "ag", "minute", "status")}
        ref = _LAMBDAS.get(frozenset((fx["home"], fx["away"])))
        if ref:
            if ref["home"] == fx["home"]:
                lh, la = ref["lh"], ref["la"]
            else:
                lh, la = ref["la"], ref["lh"]
            ph, pd, pa = live_outcome(lh, la, fx["hg"], fx["ag"], fx["minute"])
            rec["p_home"] = round(ph, 4)
            rec["p_draw"] = round(pd, 4)
            rec["p_away"] = round(pa, 4)
            rec["group"] = ref.get("group")

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
    global _LINGER_UNTIL, _LAST_LIVE_TITLE_UPDATES
    refresh_lambdas(force=True)
    while True:
        refresh_lambdas()
        fixtures = apifootball.fetch_live()
        matches, title_updates = compute_live(fixtures)
        now = time.time()
        is_live = len(matches) > 0
        with _LOCK:
            _STATE["updated_at"] = datetime.now(timezone.utc).isoformat()
            _STATE["live"] = is_live
            _STATE["matches"] = matches
            if is_live:
                _STATE["title_updates"] = title_updates
                _LAST_LIVE_TITLE_UPDATES = dict(title_updates)
                _LINGER_UNTIL = now + _LINGER_SECS
            elif now < _LINGER_UNTIL:
                # Hold last known conditioned values — pipeline hasn't caught up yet
                _STATE["title_updates"] = _LAST_LIVE_TITLE_UPDATES
            else:
                _STATE["title_updates"] = {}
                _LAST_LIVE_TITLE_UPDATES = {}
        if is_live:
            threading.Thread(target=run_live_resim, daemon=True).start()
            time.sleep(LIVE_INTERVAL)
        else:
            if now >= _LINGER_UNTIL:
                with _LIVE_FORECAST_LOCK:
                    _LIVE_FORECAST["available"] = False
            time.sleep(_idle_sleep())


def _idle_sleep():
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
        if self.path.startswith("/live_forecast"):
            with _LIVE_FORECAST_LOCK:
                return self._send(dict(_LIVE_FORECAST))
        if self.path.startswith("/live"):
            with _LOCK:
                return self._send(dict(_STATE))
        self._send({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


def main():
    threading.Thread(target=poll_loop, daemon=True).start()
    threading.Thread(target=dispatch_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"live worker serving on :{port} "
          f"(live={LIVE_INTERVAL}s / idle={IDLE_INTERVAL}s / "
          f"dispatch={'on' if GH_DISPATCH_TOKEN else 'off'} / "
          f"resim={RESIM_NSIMS}paths)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
