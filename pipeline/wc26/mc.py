"""Vectorized Monte Carlo of the remaining tournament.

Design notes:
- Ratings are updated from *real* results between pipeline runs, but held
  static within a simulation (standard practice; within-tournament Elo drift
  is second-order).
- Group ranking is fully vectorized (lexsort on pts/gd/gf with a pairwise
  head-to-head term that is exact for two-way ties and a mini-table-points
  approximation for 3+ way ties; jitter stands in for drawing of lots).
- Knockout situational factors (rest, travel, altitude, surface, host) are
  deterministic per bracket slot, so they're precomputed as slot constants.
- Leverage comes free: each sim samples every remaining fixture, so
  P(outcome | fixture result) is a conditional mean over sim subsets.
- When forecast.py computes DC attack/defense ratings, it stores lh_dc/la_dc
  on each fixture. sample_remaining_fixtures uses those directly instead of
  the Elo-based lambdas() call, giving asymmetric team profiles (high attack
  vs. strong defence) that Elo alone cannot express.
"""
import numpy as np
from datetime import date

from . import bracket as bracket_mod
from . import factors
from .matchmodel import score_matrix, lambdas, advance_prob_vec, reweight_to_outcome

JITTER = 1e-6


class SimResult:
    def __init__(self, nsims, nteams):
        self.nsims = nsims
        self.champion = np.full(nsims, -1, dtype=np.int16)
        self.runner_up = np.full(nsims, -1, dtype=np.int16)
        self.reach = {r: np.zeros((nsims, nteams), dtype=bool)
                      for r in ("r32", "r16", "qf", "sf", "final")}
        self.group_pos = None        # (nsims, nteams) 1..4
        self.third_advanced = None   # (nsims, nteams) bool
        self.fixture_outcome = {}    # fixture_id -> (nsims,) int8 0=H,1=D,2=A
        self.r32_slots = {}          # match_no -> (home_arr, away_arr) team idx
        self.ko_winners = {}         # match_no -> (nsims,) winning team idx


def sample_remaining_fixtures(fixtures, nsims, rng):
    """For each unplayed fixture, sample (hg, ag) per sim from its DC matrix.
    Mutates nothing; returns dict fixture_id -> (hg_arr, ag_arr).

    Uses DC attack/defense lambdas (lh_dc, la_dc) when available; falls back
    to Elo-based lambdas() otherwise.
    """
    sampled = {}
    for fx in fixtures:
        if fx["played"]:
            continue
        # DC lambdas when available; Elo-based fallback
        if fx.get("lh_dc") is not None and fx.get("la_dc") is not None:
            lh, la = fx["lh_dc"], fx["la_dc"]
        else:
            lh, la = lambdas(fx["dr"], fx["total_factor"])
        m = score_matrix(float(lh), float(la))
        # if the match is priced, bend the scoreline distribution so its W/D/L
        # matches the blended (market + model) outcome — the blend then flows
        # into group tiebreakers and knockout sampling.
        if fx.get("blend_probs"):
            m = reweight_to_outcome(m, fx["blend_probs"])
        flat = m.ravel()
        cum = np.cumsum(flat)
        u = rng.random(nsims)
        idx = np.searchsorted(cum, u)
        idx = np.clip(idx, 0, flat.size - 1)
        n = m.shape[0]
        sampled[fx["id"]] = ((idx // n).astype(np.int8), (idx % n).astype(np.int8))
    return sampled


def goals_for_fixture(fx, sampled, nsims):
    if fx["played"]:
        return (np.full(nsims, fx["hg"], dtype=np.int8),
                np.full(nsims, fx["ag"], dtype=np.int8))
    return sampled[fx["id"]]


def rank_group(group_fixtures, local_idx, sampled, nsims, rng):
    """Returns (order, pts, gd, gf): order is (nsims, 4) of local team idx,
    position 0 = group winner."""
    pts = np.zeros((nsims, 4), dtype=np.int16)
    gf = np.zeros((nsims, 4), dtype=np.int16)
    ga = np.zeros((nsims, 4), dtype=np.int16)
    # per-pair points earned (for head-to-head): h2h_pts[a][b] = pts a earned vs b
    h2h_pts = np.zeros((nsims, 4, 4), dtype=np.int16)

    for fx in group_fixtures:
        a, b = local_idx[fx["home"]], local_idx[fx["away"]]
        hg, ag_ = goals_for_fixture(fx, sampled, nsims)
        hw = hg > ag_
        aw = ag_ > hg
        dr_ = ~hw & ~aw
        pts[:, a] += 3 * hw + dr_
        pts[:, b] += 3 * aw + dr_
        gf[:, a] += hg; ga[:, a] += ag_
        gf[:, b] += ag_; ga[:, b] += hg
        h2h_pts[:, a, b] += 3 * hw + dr_
        h2h_pts[:, b, a] += 3 * aw + dr_

    gd = gf - ga
    # pairwise tie detection on (pts, gd, gf)
    h2h = np.zeros((nsims, 4), dtype=np.float32)
    for a in range(4):
        for b in range(4):
            if a == b:
                continue
            tied = ((pts[:, a] == pts[:, b]) & (gd[:, a] == gd[:, b])
                    & (gf[:, a] == gf[:, b]))
            h2h[:, a] += tied * h2h_pts[:, a, b]
    jit = rng.random((nsims, 4)).astype(np.float32)
    order = np.lexsort((jit, -h2h, -gf, -gd, -pts), axis=1)
    return order, pts, gd, gf


def simulate(state, nsims=50000, seed=None):
    """state: dict with keys
      ids: list of 48 team ids (canonical order)
      ratings: np.array (48,) current Elo
      groups: dict letter -> [team ids]
      fixtures: list of group fixture dicts:
        {id, group, home, away, played, hg, ag, dr, total_factor}
        (dr/total_factor only used when not played)
      bracket_def: data/bracket.json dict
      venues: dict venue_id -> venue dict
      hosts: dict team_id -> country (for host bonus)
    """
    rng = np.random.default_rng(seed)
    ids = state["ids"]
    nteams = len(ids)
    tidx = {t: i for i, t in enumerate(ids)}
    ratings = state["ratings"]
    group_letters = sorted(state["groups"].keys())
    res = SimResult(nsims, nteams)

    sampled = sample_remaining_fixtures(state["fixtures"], nsims, rng)

    # record fixture outcomes for leverage
    for fx in state["fixtures"]:
        if fx["played"]:
            continue
        hg, ag = sampled[fx["id"]]
        out = np.where(hg > ag, 0, np.where(hg == ag, 1, 2)).astype(np.int8)
        res.fixture_outcome[fx["id"]] = out

    # --- group stage ---
    winners = np.zeros((nsims, 12), dtype=np.int16)
    runners = np.zeros((nsims, 12), dtype=np.int16)
    thirds = np.zeros((nsims, 12), dtype=np.int16)
    t_pts = np.zeros((nsims, 12), dtype=np.int16)
    t_gd = np.zeros((nsims, 12), dtype=np.int16)
    t_gf = np.zeros((nsims, 12), dtype=np.int16)
    res.group_pos = np.zeros((nsims, nteams), dtype=np.int8)

    for gi, g in enumerate(group_letters):
        members = state["groups"][g]
        local_idx = {t: k for k, t in enumerate(members)}
        gfx = [f for f in state["fixtures"] if f["group"] == g]
        order, pts, gd, gf = rank_group(gfx, local_idx, sampled, nsims, rng)
        glob = np.array([tidx[t] for t in members], dtype=np.int16)
        ranked = glob[order]                      # (nsims, 4) global idx by position
        winners[:, gi] = ranked[:, 0]
        runners[:, gi] = ranked[:, 1]
        thirds[:, gi] = ranked[:, 2]
        sims = np.arange(nsims)
        for pos in range(4):
            res.group_pos[sims, ranked[:, pos]] = pos + 1
        third_local = order[:, 2]
        t_pts[:, gi] = pts[sims, third_local]
        t_gd[:, gi] = gd[sims, third_local]
        t_gf[:, gi] = gf[sims, third_local]

    # --- rank thirds across groups, top 8 advance ---
    jit = rng.random((nsims, 12)).astype(np.float32)
    third_order = np.lexsort((jit, -t_gf, -t_gd, -t_pts), axis=1)  # group indices
    qual_groups = third_order[:, :8]                               # (nsims, 8)
    qual_mask = np.zeros((nsims, 12), dtype=bool)
    np.put_along_axis(qual_mask, qual_groups, True, axis=1)

    res.third_advanced = np.zeros((nsims, nteams), dtype=bool)
    sims = np.arange(nsims)
    for gi in range(12):
        adv = qual_mask[:, gi]
        res.third_advanced[sims[adv], thirds[adv, gi]] = True

    # --- third-place slot assignment per unique combination ---
    comb_bits = (qual_mask * (1 << np.arange(12))).sum(axis=1)
    slot_constraints = bracket_mod.third_slot_constraints(state["bracket_def"])
    slot_order = [m for m, _ in slot_constraints]                  # match numbers
    # slot_group[nsims, 8] = group index assigned to each third slot
    slot_group = np.zeros((nsims, 8), dtype=np.int8)
    for bits in np.unique(comb_bits):
        mask = comb_bits == bits
        groups_in = [group_letters[i] for i in range(12) if bits & (1 << i)]
        assign = bracket_mod.assign_thirds(groups_in, state["bracket_def"])
        for si, m in enumerate(slot_order):
            slot_group[mask, si] = group_letters.index(assign[m])

    # --- resolve R32 participants ---
    r32_home = {}
    r32_away = {}
    third_slot_i = {m: i for i, m in enumerate(slot_order)}
    for m in state["bracket_def"]["r32"]:
        h, a = m["home"], m["away"]
        gi_h = group_letters.index(h["group"]) if "group" in h else None
        if h["type"] == "W":
            r32_home[m["match"]] = winners[:, gi_h]
        else:
            r32_home[m["match"]] = runners[:, gi_h]
        if a["type"] == "W":
            r32_away[m["match"]] = winners[:, group_letters.index(a["group"])]
        elif a["type"] == "R":
            r32_away[m["match"]] = runners[:, group_letters.index(a["group"])]
        else:
            sg = slot_group[:, third_slot_i[m["match"]]]
            r32_away[m["match"]] = thirds[sims, sg]

    # --- knockout rounds ---
    venues = state["venues"]
    bdef = state["bracket_def"]
    match_venue = {}
    match_date = {}
    for rnd in ("r32", "r16", "qf", "sf"):
        for m in bdef[rnd]:
            match_venue[m["match"]] = m["venue"]
            match_date[m["match"]] = m["date"]
    match_venue[104] = bdef["final"]["venue"]
    match_date[104] = bdef["final"]["date"]

    host_country = {tidx[t]: c for t, c in state["hosts"].items()}
    adapted = np.array([ids[i] in factors.ALT_ADAPTED for i in range(nteams)])

    def slot_dr(home_arr, away_arr, match_no, feeder=None):
        dr = ratings[home_arr] - ratings[away_arr]
        v = venues[match_venue[match_no]]
        # host bonus
        for arr, sign in ((home_arr, +1), (away_arr, -1)):
            is_host = np.array([host_country.get(t) == v["country"] for t in arr])
            dr = dr + sign * factors.HOST_ADV * is_host
        # altitude
        if v["altitude_m"] > 1000:
            steps = (v["altitude_m"] - 1000.0) / 250.0
            dr = dr - factors.ALT_PER_250M * steps * (~adapted[home_arr])
            dr = dr + factors.ALT_PER_250M * steps * (~adapted[away_arr])
        # rest + travel from feeder slots (deterministic per slot)
        if feeder:
            fh, fa = feeder
            d = date.fromisoformat(match_date[match_no])
            rest_h = (d - date.fromisoformat(match_date[fh])).days
            rest_a = (d - date.fromisoformat(match_date[fa])).days
            rd = float(np.clip((rest_h - rest_a) * factors.REST_PER_DAY,
                               -factors.REST_CAP, factors.REST_CAP))
            dr = dr + rd
            for f, sign in ((fh, +1), (fa, -1)):
                pv = venues[match_venue[f]]
                km = factors.haversine_km(pv["lat"], pv["lon"], v["lat"], v["lon"])
                pen = min(max(km - 500.0, 0.0) * factors.TRAVEL_PER_KM,
                          factors.TRAVEL_CAP)
                dr = dr - sign * pen
        # surface equalizer
        q = v.get("surface_quality", 1.0)
        if q < 1.0:
            dr = dr * (1.0 - (1.0 - q) * factors.SURFACE_DR_SHRINK)
        return dr

    winner_of = {}

    def play(match_no, home_arr, away_arr, feeder=None):
        dr = slot_dr(home_arr, away_arr, match_no, feeder)
        p = advance_prob_vec(dr)
        u = rng.random(nsims)
        w = np.where(u < p, home_arr, away_arr).astype(np.int16)
        winner_of[match_no] = w
        return w

    for m in bdef["r32"]:
        h, a = r32_home[m["match"]], r32_away[m["match"]]
        res.r32_slots[m["match"]] = (h, a)
        res.reach["r32"][sims, h] = True
        res.reach["r32"][sims, a] = True
        play(m["match"], h, a)

    feeders = {}
    for rnd in ("r16", "qf", "sf"):
        for m in bdef[rnd]:
            feeders[m["match"]] = (m["home"], m["away"])
    feeders[104] = (bdef["sf"][0]["match"], bdef["sf"][1]["match"])

    round_reach = {"r16": "r16", "qf": "qf", "sf": "sf"}
    for rnd in ("r16", "qf", "sf"):
        for m in bdef[rnd]:
            fh, fa = feeders[m["match"]]
            h, a = winner_of[fh], winner_of[fa]
            res.reach[round_reach[rnd]][sims, h] = True
            res.reach[round_reach[rnd]][sims, a] = True
            play(m["match"], h, a, feeder=(fh, fa))

    fh, fa = feeders[104]
    h, a = winner_of[fh], winner_of[fa]
    res.reach["final"][sims, h] = True
    res.reach["final"][sims, a] = True
    champ = play(104, h, a, feeder=(fh, fa))
    res.champion = champ
    res.runner_up = np.where(champ == h, a, h).astype(np.int16)
    res.ko_winners = winner_of

    return res
