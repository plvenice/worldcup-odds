"""Situational factor adjustments, expressed in Elo points (or total-goals
scaling for heat). Every contribution is returned in an attribution dict so
the dashboard can show *why* a number moved.

Sign convention: positive = helps the 'home' (first-listed) team.
"""
import math
from datetime import date

HOST_ADV = 60.0            # host nation playing in own country
REST_PER_DAY = 8.0         # Elo per extra full rest day
REST_CAP = 25.0
TRAVEL_PER_KM = 1.0 / 250  # Elo per km beyond 500km since last venue
TRAVEL_CAP = 20.0
TZ_PER_HOUR = 5.0          # Elo per timezone-hour shifted beyond 1
TZ_CAP = 15.0
ALT_PER_250M = 4.0         # Elo per 250m above 1000m vs unadapted opponent
ALT_ADAPTED = {"MEX", "ECU", "COL"}  # high-altitude home leagues / capitals
HEAT_INDEX_THRESHOLD_C = 32.0
SURFACE_DR_SHRINK = 0.5    # dr *= 1 - (1-quality)*SHRINK  (equalizer)
AUTO_INJURY_WEIGHT = 25.0  # flat Elo dock for API-detected injuries with unknown
                           # player tier; manual entries in availability_overrides.json
                           # take precedence and use the documented 45/30/15 tiers


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def availability_penalty(team_id, overrides, on_date=None):
    """Sum of Elo docks for unavailable key players (manual override file)."""
    total = 0.0
    names = []
    for o in overrides:
        if o["team"] != team_id:
            continue
        until = o.get("until")
        if until and on_date and date.fromisoformat(until) < on_date:
            continue
        total += float(o["weight"])
        names.append(o.get("player", "?"))
    return total, names


def match_adjustments(home, away, venue, ctx):
    """Compute (dr_adjust, total_factor, attribution).

    home/away: team dicts. venue: venue dict. ctx: dict with optional keys
      rest_days: (home_days, away_days)
      prev_venue: (home_prev_venue_dict_or_None, away_prev_venue_dict_or_None)
      heat_index_c: float or None  (kickoff forecast; ignored if roof/AC)
      on_date: datetime.date
      overrides: availability override list
    """
    att_home, att_away = {}, {}
    dr = 0.0

    # Host advantage (true home country only)
    for team, sign, att in ((home, +1, att_home), (away, -1, att_away)):
        if team.get("host") and team["id"] == _host_of(venue["country"]):
            dr += sign * HOST_ADV
            att["host"] = sign * HOST_ADV * sign  # always positive for that team

    # Rest differential
    rest = ctx.get("rest_days")
    if rest and rest[0] is not None and rest[1] is not None:
        diff = max(min((rest[0] - rest[1]) * REST_PER_DAY, REST_CAP), -REST_CAP)
        if diff:
            dr += diff
            att_home["rest"] = diff
            att_away["rest"] = -diff

    # Travel + timezone since previous match
    prev = ctx.get("prev_venue") or (None, None)
    for team_prev, sign, att in ((prev[0], +1, att_home), (prev[1], -1, att_away)):
        if not team_prev:
            continue
        km = haversine_km(team_prev["lat"], team_prev["lon"], venue["lat"], venue["lon"])
        pen = min(max(km - 500.0, 0.0) * TRAVEL_PER_KM, TRAVEL_CAP)
        tz_h = abs(_tz_offset_hours(team_prev["tz"]) - _tz_offset_hours(venue["tz"]))
        pen += min(max(tz_h - 1.0, 0.0) * TZ_PER_HOUR, TZ_CAP)
        if pen:
            dr -= sign * pen          # penalty hurts that team
            att["travel"] = -pen

    # Altitude (vs unadapted teams)
    if venue["altitude_m"] > 1000:
        steps = (venue["altitude_m"] - 1000.0) / 250.0
        for team, sign, att in ((home, +1, att_home), (away, -1, att_away)):
            if team["id"] not in ALT_ADAPTED:
                pen = steps * ALT_PER_250M
                dr -= sign * pen
                att["altitude"] = -pen

    # Availability (injuries/suspensions)
    overrides = ctx.get("overrides", [])
    for team, sign, att in ((home, +1, att_home), (away, -1, att_away)):
        pen, names = availability_penalty(team["id"], overrides, ctx.get("on_date"))
        if pen:
            dr -= sign * pen
            att["availability"] = -pen
            att["availability_players"] = names

    # Heat: open-air + hot -> compress dr (underdog boost) and fewer goals
    total_factor = 1.0
    hot = False
    hi = ctx.get("heat_index_c")
    if hi is not None and not venue["climate_controlled"] and hi >= HEAT_INDEX_THRESHOLD_C:
        hot = True
        dr *= 0.9
        total_factor = 0.95
        att_home["heat"] = "dr x0.9, goals x0.95"
        att_away["heat"] = "dr x0.9, goals x0.95"

    # Surface: temporary grass -> mild equalizer
    q = venue.get("surface_quality", 1.0)
    if q < 1.0:
        shrink = 1.0 - (1.0 - q) * SURFACE_DR_SHRINK
        dr *= shrink
        att_home["surface"] = f"dr x{shrink:.3f}"
        att_away["surface"] = f"dr x{shrink:.3f}"

    return dr, total_factor, hot, {"home": att_home, "away": att_away}


def _host_of(country):
    return {"MEX": "MEX", "USA": "USA", "CAN": "CAN"}.get(country)


_TZ_OFFSETS = {
    "America/Mexico_City": -6, "America/Monterrey": -6, "America/Toronto": -4,
    "America/Vancouver": -7, "America/Los_Angeles": -7, "America/Chicago": -5,
    "America/New_York": -4,
}


def _tz_offset_hours(tz):
    return _TZ_OFFSETS.get(tz, -5)
