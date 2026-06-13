"""Shared scoring harness for World Cup calibration backtests.

Replays a tournament's group stage through the deployed match model at a given
temperature and returns (predicted H/D/A, actual) pairs plus Brier/log-loss.
Used by backtest_2022.py and calibrate.py.
"""
import json
import math
from pathlib import Path

from wc26.matchmodel import outcome_probs, elo_update
from wc26.factors import HOST_ADV

HERE = Path(__file__).resolve().parent

# World Football Elo, end of the year before each tournament (eloratings.net
# yearly snapshot), keyed by FIFA code. Conservative pre-tournament priors.
ELO_PRIOR = {
    2022: {
        "ARG": 2101, "AUS": 1734, "BEL": 2074, "BRA": 2149, "CAN": 1784,
        "CMR": 1607, "CRC": 1617, "CRO": 1858, "DEN": 1937, "ECU": 1848,
        "ENG": 2031, "ESP": 2037, "FRA": 2114, "GER": 1962, "GHA": 1600,
        "IRN": 1837, "JPN": 1760, "KOR": 1788, "KSA": 1629, "MAR": 1764,
        "MEX": 1839, "NED": 1929, "POL": 1769, "POR": 1972, "QAT": 1663,
        "SEN": 1702, "SRB": 1847, "SUI": 1933, "TUN": 1638, "URU": 1847,
        "USA": 1858, "WAL": 1836,
    },
    2018: {
        "RUS": 1697, "GER": 2108, "BRA": 2113, "POR": 1994, "ARG": 1983,
        "BEL": 1926, "POL": 1841, "FRA": 1988, "ESP": 2030, "PER": 1881,
        "SUI": 1865, "ENG": 1932, "COL": 1926, "MEX": 1847, "URU": 1866,
        "CRO": 1856, "DEN": 1840, "ISL": 1811, "CRC": 1744, "SWE": 1823,
        "TUN": 1618, "EGY": 1650, "SEN": 1747, "IRN": 1800, "SRB": 1783,
        "NGA": 1696, "AUS": 1729, "JPN": 1706, "MAR": 1688, "PAN": 1670,
        "KOR": 1760, "KSA": 1570,
    },
}
HOST = {2018: "RUS", 2022: "QAT"}
CODE_NORM = {"SPA": "ESP"}


def _load(year):
    data = json.load(open(HERE / f"results_{year}.json", encoding="utf-8"))
    ms = [m for m in data["matches"] if m["stage"].startswith("G")]
    for m in ms:
        m["home"] = CODE_NORM.get(m["home"], m["home"])
        m["away"] = CODE_NORM.get(m["away"], m["away"])
    ms.sort(key=lambda m: (m.get("date") or "9999", m["id"]))
    return ms


def replay(year, temperature):
    """Returns list of (probs_tuple, actual_idx). actual: 0=H 1=D 2=A.
    Elo updates after each match exactly as the live engine does."""
    elo = dict(ELO_PRIOR[year])
    host = HOST[year]
    preds = []
    for m in _load(year):
        h, a = m["home"], m["away"]
        if h not in elo or a not in elo:
            continue
        dr = elo[h] - elo[a]
        dr += HOST_ADV if h == host else 0
        dr -= HOST_ADV if a == host else 0
        preds.append((outcome_probs(dr, temperature=temperature),
                      0 if m["hg"] > m["ag"] else (1 if m["hg"] == m["ag"] else 2)))
        dx = (HOST_ADV if h == host else 0) - (HOST_ADV if a == host else 0)
        nh = elo_update(elo[h], elo[a], m["hg"], m["ag"], dx)
        na = elo_update(elo[a], elo[h], m["ag"], m["hg"], -dx)
        elo[h], elo[a] = nh, na
    return preds


def brier(preds):
    return sum(sum((p[k] - (1.0 if k == o else 0.0)) ** 2 for k in range(3))
               for p, o in preds) / len(preds)


def logloss(preds):
    return sum(-math.log(min(max(p[o], 1e-6), 1.0)) for p, o in preds) / len(preds)


def reliability(preds, bins=None):
    bins = bins or [(0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .7), (.7, 1.01)]
    rows = []
    for lo, hi in bins:
        ps, ys = [], []
        for p, o in preds:
            for k in range(3):
                if lo <= p[k] < hi:
                    ps.append(p[k]); ys.append(1.0 if k == o else 0.0)
        if ps:
            rows.append((lo, hi, len(ps), sum(ps) / len(ps), sum(ys) / len(ys)))
    return rows


def ece(preds):
    rows = reliability(preds)
    tot = sum(r[2] for r in rows)
    return sum(r[2] * abs(r[3] - r[4]) for r in rows) / tot if tot else 0.0
