"""Static data loaders. All paths relative to repo root."""
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def load_json(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


_APOSTROPHE_VARIANTS = "‘’ʼ´`"  # ' ' ʼ ´ ` -> '

def normalize_name(name):
    """Casefold + strip diacritics so 'Curaçao' / 'CURACAO' / 'Côte d'Ivoire'
    compare equal against ASCII dict keys and each other, regardless of which
    spelling a given data provider (API-Football, Odds API, Wikipedia) uses.

    Also folds curly/typographic apostrophe variants to a plain ' -- NFKD
    alone won't catch "Côte d'Ivoire" (curly quote) vs the dict's "cote
    d'ivoire" (straight quote), since they aren't diacritic-related."""
    decomposed = unicodedata.normalize("NFKD", name or "")
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    folded = stripped.translate({ord(c): "'" for c in _APOSTROPHE_VARIANTS})
    return folded.strip().casefold()


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
