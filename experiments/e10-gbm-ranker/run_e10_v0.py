"""python run_e10_v0.py -- gradient-boosted cross-sectional ranking (e10 v0).

Pre-registration: experiments/e10-gbm-ranker/SPEC-v0.md. This is the algorithm class most
quant fintech firms actually run at retail-investible scale: gradient-boosted trees
ranking a cross-section of liquid names each week by predicted forward return, long the
top decile. We replicate it with sklearn's HistGradientBoostingClassifier (same family
as LightGBM/XGBoost) on free daily data, under the lab's standard anti-overfit contract.

Features (all point-in-time, computed from daily bars):
  momentum 21/63/126d, 5d reversal, 21d vol, volume z-score, distance from 63d high,
  and the market (SPY) 21d return as a regime feature.

Label: next 5-session abnormal return > 0 (stock minus SPY).
Protocol: expanding walk-forward, refit every 63 sessions, 5-session embargo, scored by
daily Spearman IC (t-stat with Newey-West lag 4, because 5-day labels overlap) and a
top-decile long portfolio rebalanced every 5 sessions (non-overlapping holding periods),
charged 5bps/side on turnover. The portfolio holds the stocks' total return, so it is
compared with SPY's total return on the same rebalance dates.
Gates: BEAT requires IC t > 2 AND portfolio Sharpe > SPY's over the identical window.

Errata (2026-11): the 2026-10-19 version appended the top decile's 5-day forward return on
EVERY day, compounded those overlapping returns daily and annualized with sqrt(252). Each
day's return was counted about five times, which inflates Sharpe by roughly sqrt(5) and the
compounded total far more. It also used ABNORMAL (stock minus SPY) returns but compared them
with SPY's total return, charged no costs, and treated overlapping daily ICs as independent.
The published "Sharpe 2.08 / 8,689x" is therefore mostly a return-math error, not only
survivorship. This file is the corrected runner; it has not been re-run yet.
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
        fwd = c.shift(-5) / c - 1
        f["fwd"] = fwd                                   # stock total return, next 5 sessions
        f["lab"] = fwd - (spy.shift(-5) / spy - 1)       # abnormal return (label)
        f["ticker"] = t
        rows.append(f.dropna())
    df = pd.concat(rows)
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "date"})
    return df


def data_fetch():
    from harness import data
    return data.fetch(BROAD, start="2012-01-01", refresh=False, name="broad")


def nw_t(x, lags=4):
    """t-stat of the mean with a Newey-West (Bartlett) long-run variance."""
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x)
    if n < 2: return 0.0
    e = x - x.mean()
    lrv = e @ e / n
    for k in range(1, lags + 1):
        lrv += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(lrv / n)) if lrv > 0 else 0.0


H, SIDE_BPS = 5, 5.0   # rebalance every 5 sessions (= label horizon), 5bps per side


def run():
    df = panel().sort_values("date").reset_index(drop=True)
    df["y"] = (df.lab > 0).astype(int)
    dates = sorted(df.date.unique())
    ics, port = [], []
    rebal = set(dates[1::H])          # non-overlapping 5-session holding periods
    prev_w = {}
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
            if d not in rebal: continue
            top = dd.nlargest(max(1, len(dd) // 10), "p")
            w = {t: 1 / len(top) for t in top.ticker}
            turnover = sum(abs(w.get(t, 0) - prev_w.get(t, 0)) for t in set(w) | set(prev_w))
            prev_w = w
            port.append((d, top.fwd.mean() - turnover * SIDE_BPS / 1e4, top.fwd.mean(), top.lab.mean()))
    ic_s = pd.Series({d: v for d, v in ics}).sort_index()
    pdf = pd.DataFrame(port, columns=["date", "net", "gross", "abn"]).set_index("date").sort_index()
    p_s = pdf.net
    per = 252 / H
    ic, n = float(ic_s.mean()), len(ic_s)
    t = nw_t(ic_s.values, lags=H - 1)
    shp = float(p_s.mean() / p_s.std() * per ** .5) if p_s.std() > 0 else 0.0
    shp_gross = float(pdf.gross.mean() / pdf.gross.std() * per ** .5) if pdf.gross.std() > 0 else 0.0
    shp_abn = float(pdf.abn.mean() / pdf.abn.std() * per ** .5) if pdf.abn.std() > 0 else 0.0
    tot = float((1 + p_s).prod() - 1)
    # SPY over identical window
    from harness import data as hd
    spy = hd.fetch(["SPY"], start=pd.Timestamp(dates[0]).strftime("%Y-%m-%d"),
                   refresh=False, name="spy_cmp")["SPY"]
    # SPY 5-session returns on the same rebalance dates as the portfolio
    spy_h = (spy.shift(-H) / spy - 1).reindex(pd.to_datetime(p_s.index)).dropna()
    spy_tot = float((1 + spy_h).prod() - 1)
    spy_shp = float(spy_h.mean() / spy_h.std() * per ** .5)
    res = {"ic_mean": round(ic, 4), "ic_t_nw": round(t, 2), "scored_days": n,
           "rebalances": len(p_s), "port_sharpe_net": round(shp, 2), "port_sharpe_gross": round(shp_gross, 2),
           "abnormal_sharpe_gross": round(shp_abn, 2), "port_total_net": round(tot, 3),
           "spy_sharpe": round(spy_shp, 2), "spy_total": round(spy_tot, 3),
           "verdict": "BEAT" if (t > 2 and shp > spy_shp) else "LOSE",
           "experiment": "e10_gbm", "window": [str(dates[0])[:10], str(dates[-1])[:10]]}
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "reports", "e10-gbm.json"), "w"), indent=1)
    lines = ["# e10 — gradient-boosted cross-sectional ranking " + time.strftime("%Y-%m-%d"), "",
             f"Window {res['window'][0]} -> {res['window'][1]}, BROAD-40, weekly-ish blocks (63 sessions), 5-day embargo.", "",
             f"- Daily Spearman IC: **{res['ic_mean']}** (Newey-West t = {res['ic_t_nw']}, {n} scored days)",
             f"- Top-decile long portfolio, rebalanced every {H} sessions, {SIDE_BPS:.0f}bps/side: net Sharpe **{res['port_sharpe_net']}** (gross {res['port_sharpe_gross']}), net total {res['port_total_net']}",
             f"- Gross Sharpe of the abnormal (vs SPY) return: {res['abnormal_sharpe_gross']}",
             f"- SPY on the same rebalance dates: Sharpe {res['spy_sharpe']}, total {res['spy_total']}",
             f"- Verdict: **{res['verdict']}** (gate: IC t > 2 AND portfolio Sharpe > SPY)", "",
             "Universe caveat: BROAD-40 is today's large caps (survivors); see e10 v1 for point-in-time membership."]
    open(os.path.join(ROOT, "reports", "e10-gbm.md"), "w").write("\n".join(lines))
    # log only after outputs are written, so a crash cannot leave an orphan trial row
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e10_gbm", "generation": 0, "stage": "holdout",
               "params": {"model": "HistGB", "depth": 3, "iters": 200, "lr": 0.06,
                          "step": 63, "embargo": 5, "rebalance": H, "side_bps": SIDE_BPS, "v": "v0-fixed"},
               "seed": 0, "ic": ic, "t": t, "n": n, "verdict": res["verdict"], "origin": "manual"})
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    run()
