"""Kickoff weather via Open-Meteo (free, no key). Failures are silent —
the heat factor simply doesn't apply when no forecast is available."""
import requests


def heat_index_c(temp_c, rh):
    """NOAA heat index, converted to Celsius. Valid above ~27C."""
    if temp_c is None or rh is None:
        return None
    t = temp_c * 9 / 5 + 32
    if t < 80:
        return temp_c
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh
          - 6.83783e-3 * t * t - 5.481717e-2 * rh * rh + 1.22874e-3 * t * t * rh
          + 8.5282e-4 * t * rh * rh - 1.99e-6 * t * t * rh * rh)
    return (hi - 32) * 5 / 9


def fixture_heat_index(venue, iso_date):
    """Approximate match-time heat index at a venue on a date (uses 15:00
    local as proxy until kickoff times are wired in). None on any failure."""
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": venue["lat"], "longitude": venue["lon"],
            "hourly": "temperature_2m,relative_humidity_2m",
            "start_date": iso_date, "end_date": iso_date,
            "timezone": venue["tz"],
        }, timeout=15)
        r.raise_for_status()
        h = r.json()["hourly"]
        i = h["time"].index(f"{iso_date}T15:00")
        return heat_index_c(h["temperature_2m"][i], h["relative_humidity_2m"][i])
    except Exception:
        return None
