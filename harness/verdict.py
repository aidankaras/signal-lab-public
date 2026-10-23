"""Strict verdict: an experiment only PASSes if it beats SPY AND the random-pick control median
(Sharpe) AND the equal-weight universe (CAGR) on the same holdout window. Otherwise it is published
as LOSE with the reason. Born from the first report: 16/20 random 3-picks beat SPY, so beating SPY
alone proves nothing on a survivor-biased universe."""
import numpy as np
import pandas as pd

from harness.evaluator import evaluate, metrics
from harness.strategies.random_control import RandomControl


def control_stats(universe_close: pd.DataFrame, k: int, bench: pd.Series, cut: int, seeds=20, cost_bps=5.0):
    rc, sh, cg, beats = RandomControl(), [], [], 0
    for s in range(seeds):
        ev = evaluate(rc.run(universe_close, {"k": k, "seed": s}, cost_bps).iloc[cut:], bench.iloc[cut:])
        sh.append(ev["strategy"]["sharpe"]); cg.append(ev["strategy"]["cagr"]); beats += ev["beat_sp500"]
    ew = universe_close.pct_change().fillna(0.0).mean(axis=1).iloc[cut:]
    return {"k": k, "seeds": seeds, "median_sharpe": float(np.median(sh)), "median_cagr": float(np.median(cg)),
            "beat_spy": int(beats), "ew_universe": metrics(ew)}


def strict(ho_ev: dict, ctrl: dict) -> dict:
    if "error" in ho_ev:
        return {"strict": "n/a", "why": ho_ev["error"]}
    s = ho_ev["strategy"]
    fails = []
    if not ho_ev["beat_sp500"]:
        fails.append("trails SPY")
    if s["sharpe"] <= ctrl["median_sharpe"]:
        fails.append(f"Sharpe {s['sharpe']} <= random-pick median {ctrl['median_sharpe']:.2f}")
    if s["cagr"] <= ctrl["ew_universe"]["cagr"]:
        fails.append(f"CAGR {s['cagr']:.1%} <= equal-weight universe {ctrl['ew_universe']['cagr']:.1%}")
    return {"strict": "PASS" if not fails else "LOSE", "why": "; ".join(fails) or "beats SPY, control median, EW universe"}
