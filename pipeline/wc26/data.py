"""Static data loaders. All paths relative to repo root."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def load_json(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def teams():
    """Returns dict id -> team record, plus ordered list of ids."""
    raw = load_json("teams.json")["teams"]
    by_id = {t["id"]: t for t in raw}
    ids = [t["id"] for t in raw]
    return by_id, ids


def venues():
    raw = load_json("venues.json")["venues"]
    return {v["id"]: v for v in raw}


def bracket():
    return load_json("bracket.json")


def availability():
    return load_json("availability_overrides.json")["out"]


def groups():
    """group letter -> list of team ids, in teams.json order."""
    by_id, ids = teams()
    out = {}
    for tid in ids:
        out.setdefault(by_id[tid]["group"], []).append(tid)
    return out
