"""Orchestrates a full forecast run:

  fetch fixtures/results -> update live Elo from real results ->
  per-fixture factor adjustments -> Monte Carlo -> aggregate ->
  out/forecast.json + out/history.csv
"""
import csv
import json
import numpy as np
from datetime import date, datetime, timezone
from pathlib import Path

from . import data, factors, wiki, weather, odds
from .matchmodel import elo_update, outcome_probs, blend_outcome
from . import standings as st
from .mc import simulate

OUT = data.ROOT / "out"
WEATHER_LOOKAHEAD_DAYS = 8


def build_state(nsims_note=None, fetch_weather=True, h2h=None):
    by_id, ids = data.teams()
    venues = data.venues()
    groups = data.groups()
    overrides = data.availability()
    fixtures, source = wiki.fetch_group_fixtures()
    fixtures.sort(key=lambda f: (f["date"] or "9999", f["id"]))

    # --- live Elo: replay real results chronologically from seeds ---
    elo = {t: float(by_id[t]["elo_seed"]) for t in ids}
    last_played = {}   # team -> (date, venue_id)
    for fx in fixtures:
        if not fx["played"]:
            continue
        v = venues.get(fx["venue"]) or {}
        h_host = by_id[fx["home"]].get("host") and v.get("country") == fx["home"]
        a_host = by_id[fx["away"]].get("host") and v.get("country") == fx["away"]
        dr_extra = factors.HOST_ADV * (1 if h_host else 0) - factors.HOST_ADV * (1 if a_host else 0)
        new_h = elo_update(elo[fx["home"]], elo[fx["away"]], fx["hg"], fx["ag"], dr_extra)
        new_a = elo_update(elo[fx["away"]], elo[fx["home"]], fx["ag"], fx["hg"], -dr_extra)
        elo[fx["home"]], elo[fx["away"]] = new_h, new_a
        for t in (fx["home"], fx["away"]):
            last_played[t] = (fx["date"], fx["venue"])

    # --- per-fixture adjustments for unplayed fixtures ---
    today = date.today()
    attributions = {}
    for fx in fixtures:
        if fx["played"]:
            continue
        v = venues.get(fx["venue"])
        if v is None:
            fx["dr"] = elo[fx["home"]] - elo[fx["away"]]
            fx["total_factor"] = 1.0
            continue
        ctx = {"overrides": overrides, "on_date": today}
        rest, prev = [], []
        for t in (fx["home"], fx["away"]):
            lp = last_played.get(t)
            if lp and lp[0] and fx["date"]:
                rest.append((date.fromisoformat(fx["date"]) - date.fromisoformat(lp[0])).days)
                prev.append(venues.get(lp[1]))
            else:
                rest.append(None)
                prev.append(None)
        ctx["rest_days"] = tuple(rest)
        ctx["prev_venue"] = tuple(prev)
        if fetch_weather and fx["date"]:
            days_out = (date.fromisoformat(fx["date"]) - today).days
            if 0 <= days_out <= WEATHER_LOOKAHEAD_DAYS:
                ctx["heat_index_c"] = weather.fixture_heat_index(v, fx["date"])
        dr_adj, total_factor, hot, att = factors.match_adjustments(
            by_id[fx["home"]], by_id[fx["away"]], v, ctx)
        fx["dr"] = (elo[fx["home"]] - elo[fx["away"]]) + dr_adj
        fx["total_factor"] = total_factor
        attributions[fx["id"]] = att

    # --- market blend: fold bookmaker match odds into each priced fixture ---
    market_by_pair = {}
    if h2h:
        for m in h2h.get("matches", []):
            market_by_pair[frozenset((m["home"], m["away"]))] = m
    n_blended = 0
    for fx in fixtures:
        if fx["played"]:
            continue
        model = outcome_probs(fx["dr"], fx.get("total_factor", 1.0))
        fx["model_probs"] = [round(x, 4) for x in model]
        mp = market_by_pair.get(frozenset((fx["home"], fx["away"])))
        if not mp:
            continue
        # orient market to this fixture's home/away
        if mp["home"] == fx["home"]:
            market = (mp["ph"], mp["pd"], mp["pa"])
        else:
            market = (mp["pa"], mp["pd"], mp["ph"])
        blend = blend_outcome(model, market, odds.MARKET_BLEND_WEIGHT)
        fx["market_probs"] = [round(x, 4) for x in market]
        fx["blend_probs"] = [round(x, 4) for x in blend]
        n_blended += 1

    state = {
        "ids": ids,
        "ratings": np.array([elo[t] for t in ids]),
        "groups": groups,
        "fixtures": fixtures,
        "bracket_def": data.bracket(),
        "venues": venues,
        "hosts": {t: t for t in ids if by_id[t].get("host")},
        "elo": elo,
        "source": source,
        "attributions": attributions,
        "n_blended": n_blended,
    }
    return state


def aggregate(state, res, nsims):
    by_id, ids = data.teams()
    tidx = {t: i for i, t in enumerate(ids)}
    n = float(nsims)

    champ_count = np.bincount(res.champion, minlength=len(ids))
    final_p = res.reach["final"].mean(axis=0)
    advance = (res.group_pos <= 2) | res.third_advanced

    teams_out = []
    for t in ids:
        i = tidx[t]
        teams_out.append({
            "id": t, "name": by_id[t]["name"], "group": by_id[t]["group"],
            "elo": round(state["elo"][t], 1),
            "elo_seed": by_id[t]["elo_seed"],
            "p_title": champ_count[i] / n,
            "p_final": float(final_p[i]),
            "p_sf": float(res.reach["sf"][:, i].mean()),
            "p_qf": float(res.reach["qf"][:, i].mean()),
            "p_r16": float(res.reach["r16"][:, i].mean()),
            "p_r32": float(res.reach["r32"][:, i].mean()),
            "p_group_win": float((res.group_pos[:, i] == 1).mean()),
            "p_group_second": float((res.group_pos[:, i] == 2).mean()),
            "p_third_advance": float(res.third_advanced[:, i].mean()),
            "p_advance": float(advance[:, i].mean()),
        })

    # --- actual standings ---
    groups_out = {}
    for g, members in state["groups"].items():
        played = [(f["home"], f["away"], f["hg"], f["ag"])
                  for f in state["fixtures"] if f["group"] == g and f["played"]]
        rows = {r["team"]: r for r in st.table(members, played)}
        order = st.rank(members, played)
        groups_out[g] = [rows[t] for t in order]

    # --- matches with probs + leverage ---
    title_mask = np.zeros((nsims, len(ids)), dtype=bool)
    title_mask[np.arange(nsims), res.champion] = True
    matches_out = []
    for fx in state["fixtures"]:
        rec = {k: fx.get(k) for k in
               ("id", "group", "home", "away", "date", "venue", "played", "hg", "ag")}
        if not fx["played"]:
            # headline probs = blended (market + model) when the match is priced,
            # else the calibrated model
            eff = fx.get("blend_probs") or fx.get("model_probs") \
                or [round(x, 4) for x in outcome_probs(fx["dr"], fx["total_factor"])]
            rec["probs"] = {"home": eff[0], "draw": eff[1], "away": eff[2]}
            if fx.get("market_probs"):
                mo = fx["model_probs"]
                mk = fx["market_probs"]
                rec["model_probs"] = {"home": mo[0], "draw": mo[1], "away": mo[2]}
                rec["market_probs"] = {"home": mk[0], "draw": mk[1], "away": mk[2]}
            rec["attribution"] = state["attributions"].get(fx["id"], {})
            out = res.fixture_outcome[fx["id"]]
            lev = []
            lev_index = 0.0
            for t in state["groups"][fx["group"]]:
                i = tidx[t]
                cond_title = [float(title_mask[out == k, i].mean()) if (out == k).any() else 0.0
                              for k in (0, 1, 2)]
                cond_adv = [float(advance[out == k, i].mean()) if (out == k).any() else 0.0
                            for k in (0, 1, 2)]
                swing_t = max(cond_title) - min(cond_title)
                swing_a = max(cond_adv) - min(cond_adv)
                lev_index += swing_t
                lev.append({"team": t,
                            "p_title_by_outcome": [round(x, 4) for x in cond_title],
                            "p_advance_by_outcome": [round(x, 4) for x in cond_adv],
                            "title_swing": round(swing_t, 4),
                            "advance_swing": round(swing_a, 4)})
            rec["leverage"] = lev
            rec["leverage_index"] = round(lev_index, 4)
        matches_out.append(rec)

    # --- bracket slot occupant distributions (top 6 per side) ---
    def top_dist(arr, k=6):
        counts = np.bincount(arr, minlength=len(ids)) / n
        order = np.argsort(-counts)[:k]
        return [{"team": ids[i], "p": round(float(counts[i]), 4)}
                for i in order if counts[i] > 0.001]

    bracket_out = {"r32": []}
    bdef = state["bracket_def"]
    for m in bdef["r32"]:
        h, a = res.r32_slots[m["match"]]
        bracket_out["r32"].append({
            "match": m["match"], "date": m["date"], "venue": m["venue"],
            "home_slot": m["home"], "away_slot": m["away"],
            "home_dist": top_dist(h), "away_dist": top_dist(a),
            "winner_dist": top_dist(res.ko_winners[m["match"]]),
        })
    for rnd in ("r16", "qf", "sf"):
        bracket_out[rnd] = [{
            "match": m["match"], "date": m["date"], "venue": m["venue"],
            "feeders": [m["home"], m["away"]],
            "winner_dist": top_dist(res.ko_winners[m["match"]]),
        } for m in bdef[rnd]]
    bracket_out["final"] = {
        "match": 104, "date": bdef["final"]["date"], "venue": bdef["final"]["venue"],
        "winner_dist": top_dist(res.champion, k=12),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nsims": nsims,
        "results_source": state["source"],
        "teams": sorted(teams_out, key=lambda x: -x["p_title"]),
        "groups": groups_out,
        "matches": matches_out,
        "bracket": bracket_out,
    }


def run(nsims=50000, seed=None, fetch_weather=True):
    OUT.mkdir(exist_ok=True)

    # market match odds (h2h): fresh pull if budget allows, else last snapshot
    # (carried on the data branch across runs). Feeds the blend in build_state.
    h2h = odds.fetch_h2h()
    h2h_file = OUT / "market_h2h.json"
    if h2h:
        h2h_file.write_text(json.dumps(h2h), encoding="utf-8")
    elif h2h_file.exists():
        h2h = json.loads(h2h_file.read_text(encoding="utf-8"))

    state = build_state(fetch_weather=fetch_weather, h2h=h2h)
    res = simulate(state, nsims=nsims, seed=seed)
    fc = aggregate(state, res, nsims)

    # outright title market (display line on the title race chart)
    market = odds.fetch_outrights()
    mfile = OUT / "market.json"
    if market:
        mfile.write_text(json.dumps(market), encoding="utf-8")
    elif mfile.exists():
        market = json.loads(mfile.read_text(encoding="utf-8"))
    fc["market"] = market
    fc["blend"] = {
        "n_matches": state.get("n_blended", 0),
        "weight": odds.MARKET_BLEND_WEIGHT,
        "fetched_at": h2h.get("fetched_at") if h2h else None,
    }
    with open(OUT / "forecast.json", "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=1)

    hist = OUT / "history.csv"
    new = not hist.exists()
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "team", "p_title", "p_final", "p_sf", "p_qf", "p_advance", "elo"])
        for t in fc["teams"]:
            w.writerow([fc["generated_at"], t["id"], f"{t['p_title']:.5f}",
                        f"{t['p_final']:.5f}", f"{t['p_sf']:.5f}", f"{t['p_qf']:.5f}",
                        f"{t['p_advance']:.5f}", t["elo"]])
    return fc
