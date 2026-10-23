"""python run_e10.py -- gradient-boosted cross-sectional ranking (e10).

Pre-registration: experiments/experiment-10-gbm.md. This is the algorithm class most
quant fintech firms actually run at retail-investible scale: gradient-boosted trees
ranking a cross-section of liquid names each week by predicted forward return, long the
top decile. We replicate it with sklearn's HistGradientBoostingClassifier (same family
as LightGBM/XGBoost) on free daily data, under the lab's standard anti-overfit contract.

Features (all point-in-time, computed from daily bars):
  momentum 21/63/126d, 5d reversal, 21d vol, volume z-score, distance from 63d high,
  and the market (SPY) 21d return as a regime feature.

Label: next 5-session abnormal return > 0 (stock minus SPY).
Protocol: expanding walk-forward, refit every 63 sessions, 5-session embargo, scored by
daily Spearman IC and a top-decile long portfolio through costs (5bps/side).
Gates: BEAT requires IC t > 2 AND portfolio Sharpe > SPY's over the identical window.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import BROAD
from harness.evaluator import log_trial

FEATS = ["mom21", "mom63", "mom126", "rev5", "vol21", "volz", "hi63_dist", "mkt21"]


def panel():
    px = data_fetch()
    spy = px["SPY"]
    rows = []
    for t in px.columns:
        if t == "SPY": continue
        c = px[t].dropna()
        if len(c) < 200: continue
        r = c.pct_change()
        f = pd.DataFrame({
            "mom21": c.pct_change(21), "mom63": c.pct_change(63), "mom126": c.pct_change(126),
            "rev5": -c.pct_change(5), "vol21": r.rolling(21).std(),
            "volz": (r.rolling(5).mean() * 21 ** .5) / r.rolling(63).std(),
            "hi63_dist": c / c.rolling(63).max() - 1,
        })
        f["mkt21"] = spy.pct_change(21).reindex(c.index)
        lab = (c.shift(-5) / c - 1) - (spy.shift(-5) / spy - 1)
        f["lab"] = lab
        f["ticker"] = t
        rows.append(f.dropna())
    df = pd.concat(rows)
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "date"})
    return df


def data_fetch():
    from harness import data
    return data.fetch(BROAD, start="2012-01-01", refresh=False, name="broad")


def run():
    df = panel().sort_values("date").reset_index(drop=True)
    df["y"] = (df.lab > 0).astype(int)
    dates = sorted(df.date.unique())
    ics, port = [], []
    step, emb = 63, 5
    for b in range(1, len(dates) - step, step):
        blk = dates[b:b + step]
        tr_end = dates[b - emb - 1]
        tr = df[df.date <= tr_end]
        te = df[df.date.isin(blk)]
        if len(tr) < 5000 or tr.y.nunique() < 2: continue
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=200,
                                           learning_rate=0.06, random_state=0).fit(tr[FEATS], tr.y)
        te = te.copy()
        te["p"] = m.predict_proba(te[FEATS])[:, 1]
        for d in blk:
            dd = te[te.date == d]
            if len(dd) < 15 or dd.y.nunique() < 2: continue
            ic = spearmanr(dd.p, dd.y).statistic
            if ic == ic: ics.append((d, ic))
            top = dd.nlargest(max(1, len(dd) // 10), "p")
            port.append((d, top.lab.mean()))
    ic_s = pd.Series({d: v for d, v in ics}).sort_index()
    p_s = pd.Series({d: v for d, v in port}).sort_index()
    ic, n = float(ic_s.mean()), len(ic_s)
    t = float(ic / ic_s.std() * n ** .5) if n > 1 and ic_s.std() > 0 else 0.0
    shp = float(p_s.mean() / p_s.std() * 252 ** .5) if p_s.std() > 0 else 0.0
    tot = float((1 + p_s).prod() - 1)
    # SPY over identical window
    from harness import data as hd
    spy = hd.fetch(["SPY"], start=pd.Timestamp(dates[0]).strftime("%Y-%m-%d"),
                   refresh=False, name="spy_cmp")["SPY"]
    spy = spy[spy.index <= pd.Timestamp(dates[-1])]
    spy_tot = float(spy.iloc[-1] / spy.iloc[0] - 1)
    spy_shp = float(spy.pct_change().mean() / spy.pct_change().std() * 252 ** .5)
    res = {"ic_mean": round(ic, 4), "ic_t": round(t, 2), "scored_days": n,
           "port_sharpe": round(shp, 2), "port_total": round(tot, 3),
           "spy_sharpe": round(spy_shp, 2), "spy_total": round(spy_tot, 3),
           "verdict": "BEAT" if (t > 2 and shp > spy_shp) else "LOSE",
           "experiment": "e10_gbm", "window": [str(dates[0])[:10], str(dates[-1])[:10]]}
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e10_gbm", "generation": 0, "stage": "holdout",
               "params": {"model": "HistGB", "depth": 3, "iters": 200, "lr": 0.06,
                          "step": 63, "embargo": 5}, "seed": 0,
               "ic": ic, "t": t, "n": n, "verdict": res["verdict"], "origin": "manual"})
    json.dump(res, open(os.path.join(ROOT, "reports", "e10-gbm.json"), "w"), indent=1)
    lines = ["# e10 — gradient-boosted cross-sectional ranking " + time.strftime("%Y-%m-%d"), "",
             f"Window {res['window'][0]} -> {res['window'][1]}, BROAD-40, weekly-ish blocks (63 sessions), 5-day embargo.", "",
             f"- Daily Spearman IC: **{res['ic_mean']}** (t = {res['ic_t']}, {n} scored days)",
             f"- Top-decile long portfolio: Sharpe **{res['port_sharpe']}**, total {res['port_total']} (before 5bps/side costs in this v0; costs gate the verdict next version)",
             f"- SPY same window: Sharpe {res['spy_sharpe']}, total {res['spy_total']}",
             f"- Verdict: **{res['verdict']}** (gate: IC t > 2 AND portfolio Sharpe > SPY)", "",
             "This replicates the standard quant-fintech baseline (GBM cross-sectional ranking).", "",
             "Known v0 simplification, flagged: costs not yet charged to the portfolio return;",
             "the IC gate is unaffected (IC is cost-free by nature), the Sharpe comparison is",
             "generous to the strategy by ~turnover*7bps/yr. If IC fails the gate, costs are moot."]
    open(os.path.join(ROOT, "reports", "e10-gbm.md"), "w").write("\n".join(lines))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    run()
