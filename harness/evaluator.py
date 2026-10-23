"""Evaluator: metrics, S&P 500 verdict, Deflated Sharpe, append-only trial log."""
import json
import math
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

ND = NormalDist()


def _r(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def metrics(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    if n < 30:
        return {"error": "too short", "n": n}
    tot = float((1 + x).prod())
    cagr = tot ** (252 / n) - 1 if tot > 0 else -1.0
    sd = float(x.std(ddof=1))
    down = x[x < 0].std(ddof=1)
    eq = (1 + x).cumprod()
    return {"cagr": _r(cagr), "sharpe": _r(x.mean() / sd * math.sqrt(252) if sd > 0 else 0.0),
            "sortino": _r(x.mean() / down * math.sqrt(252) if down and down > 0 else 0.0),
            "maxdd": _r(float((1 - eq / eq.cummax()).max())), "total_return": _r(tot - 1),
            "hit_rate": _r(float((x > 0).sum() / max((x != 0).sum(), 1))), "n_days": n}


def evaluate(strat: pd.Series, bench: pd.Series) -> dict:
    """Same-window comparison vs S&P 500 (SPY buy-and-hold as the ^GSPC proxy, total return)."""
    df = pd.concat([strat, bench], axis=1, join="inner").dropna()
    df.columns = ["s", "b"]
    s, b = metrics(df.s), metrics(df.b)
    if "error" in s:
        return s
    ex = df.s - df.b
    beat = bool((1 + ex).prod() > 1)
    return {"strategy": s, "benchmark_sp500": b, "alpha_annualized": _r(ex.mean() * 252),
            "tracking_diff_total": _r(s["total_return"] - b["total_return"]),
            "beat_sp500": beat, "verdict": "BEAT" if beat else "LOSE",
            "window": [str(df.index[0].date()), str(df.index[-1].date())]}


def deflated_sharpe(sr_daily: float, n_obs: int, trial_srs_daily, skew=0.0, kurt=3.0) -> float:
    """Bailey & Lopez de Prado DSR: prob. true Sharpe > 0 after N trials. Simple version."""
    N = max(len(trial_srs_daily), 1)
    if N < 2 or n_obs < 30:
        return float("nan")
    v = float(np.var(trial_srs_daily, ddof=1))
    g = 0.5772156649
    sr0 = math.sqrt(v) * ((1 - g) * ND.inv_cdf(1 - 1 / N) + g * ND.inv_cdf(1 - 1 / (N * math.e)))
    denom = math.sqrt(max(1 - skew * sr_daily + (kurt - 1) / 4 * sr_daily ** 2, 1e-9))
    return ND.cdf((sr_daily - sr0) * math.sqrt(n_obs - 1) / denom)


def log_trial(path: str, record: dict) -> None:
    """Append-only. Never rewrite."""
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_trials(path: str, experiment: str = None):
    try:
        rows = [json.loads(l) for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []
    return [r for r in rows if experiment is None or r.get("experiment") == experiment]
