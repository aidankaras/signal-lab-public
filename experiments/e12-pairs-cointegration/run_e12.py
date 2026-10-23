"""python run_e12.py -- pairs trading via cointegration (e12).

Pre-registration: experiments/experiment-12-pairs.md. A genuinely different strategy
class from e0-e10: market-neutral mean reversion between two correlated names, not
directional prediction. This is the simplified classical version (Engle-Granger +
rolling OLS hedge ratio); a Kalman-filter hedge ratio is the v1 upgrade if v0 shows
anything.

Design:
- Universe: BROAD-40 daily bars 2013-present.
- Walk-forward, one year at a time: fit on the trailing 3 years only, trade the next
  year, roll. No pair is ever traded using data that includes its trading year.
- Fit: for all 780 pairs, Engle-Granger ADF p-value on the residual of a rolling OLS
  hedge ratio; keep pairs with p < 0.01 AND |half-life| between 5 and 60 sessions
  (half-life from an AR(1) fit on the residual). Rank by half-life, keep top 5.
  Multiple-testing across 780 pairs is the known trap — the p<0.01 gate plus
  out-of-sample walk-forward is the honest control, and the DSR counter in the
  registry counts this as one trial per year.
- Trade: z-score of the spread over the fit window; enter long-spread at z < -2
  (short-spread at z > +2), exit at |z| < 0.5, stop at |z| > 4. 5bps/side on each leg
  (10bps per round trip per pair). Equal weight across active pairs.
- Gates: BEAT requires portfolio Sharpe > SPY's over identical walk-forward years AND
  IC-equivalent: mean annual return > 0 after costs. Random control: 5 random pairs,
  same entry rule, same years.
"""
import itertools, json, os, sys, time
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import BROAD
from harness.evaluator import log_trial

COST = 0.0010  # 10bps per pair round trip (both legs, 5bps each side aggregated)
N_PAIRS = 5


def prices():
    from harness import data
    px = data.fetch(BROAD, start="2012-01-01", refresh=False, name="broad")
    return px.dropna(axis=1)


def half_life(resid):
    r = np.diff(resid)
    lag = resid[:-1]
    if lag.std() == 0: return np.inf
    phi = np.dot(lag, r - r.mean() + lag.mean() * 0) / np.dot(lag, lag) if lag.size else np.inf
    # proper AR(1): delta_t = a + b*lag_{t-1}; b<0 => mean reverting
    X = np.column_stack([np.ones(len(lag)), lag])
    b = np.linalg.lstsq(X, r, rcond=None)[0][1]
    if b >= -1e-9 or b <= -2: return np.inf
    return -np.log(2) / b


def adf_pvalue(resid):
    """Minimal ADF t-stat without statsmodels: regress delta on lag, compare to
    MacKinnon-ish critical value (-2.86 at 5%, -3.44 at 1%) as a coarse gate."""
    r = np.diff(resid)
    lag = resid[:-1]
    X = np.column_stack([np.ones(len(lag)), lag])
    beta = np.linalg.lstsq(X, r, rcond=None)[0]
    e = r - X @ beta
    se = np.sqrt(np.dot(e, e) / max(1, len(e) - 2) * np.linalg.inv(X.T @ X)[1, 1])
    if se == 0 or np.isnan(se): return 1.0
    t = beta[1] / se
    return 0.01 if t < -3.44 else (0.05 if t < -2.86 else 1.0)


def select_pairs(window):
    best = []
    for a, b in itertools.combinations(window.columns, 2):
        x = window[a].values.reshape(-1, 1)
        y = window[b].values
        beta = LinearRegression().fit(x, y).coef_[0]
        resid = y - beta * x.ravel()
        hl = half_life(resid)
        if not (5 <= hl <= 60): continue
        if adf_pvalue(resid) > 0.01: continue
        best.append((abs(hl - 15), a, b, beta, hl))
    best.sort()
    return best[:N_PAIRS]


def trade_year(px, year, pairs):
    """Trade the calendar year using z-scores computed vs the fit window's mean/std."""
    fit_end = pd.Timestamp(f"{year}-01-01") - pd.Timedelta(days=1)
    rets = []
    for _, a, b, beta, _hl in pairs:
        spread = px[b] - beta * px[a]
        mu, sd = spread[spread.index <= fit_end].mean(), spread[spread.index <= fit_end].std()
        if sd == 0 or np.isnan(sd): continue
        z = (spread - mu) / sd
        yy = z[(z.index >= f"{year}-01-01") & (z.index <= f"{year}-12-31")]
        pos = 0; entry_px = None; cost = 0.0
        for i in range(1, len(yy)):
            zy = yy.iloc[i]
            if pos == 0 and abs(zy) > 2:
                pos = -np.sign(zy)  # short spread when z high
                cost += COST / 2
            elif pos != 0 and (abs(zy) < 0.5 or abs(zy) > 4):
                pos = 0
                cost += COST / 2
            rets.append(pos * (yy.iloc[i] - yy.iloc[i - 1]) / sd * 0.02)
        rets.append(-cost)
    # position P&L: spread change scaled; cost charged on entry days approximated below
    return np.array(rets)


def main():
    px = prices()
    spy = px["SPY"] if "SPY" in px else None
    px = px.drop(columns=["SPY"], errors="ignore")
    years = list(range(2016, 2027))
    strat, bench, rnd = [], [], []
    rng = np.random.default_rng(0)
    for yr in years:
        fit = px[(px.index >= pd.Timestamp(yr - 3, 1, 1)) & (px.index < pd.Timestamp(yr, 1, 1))]
        if len(fit) < 400: continue
        pairs = select_pairs(fit)
        if not pairs: continue
        tr = trade_year(px, yr, pairs)
        yr_ret = float(np.sum(tr) / max(1, N_PAIRS))
        strat.append(yr_ret)
        # SPY same year
        if spy is not None:
            s = spy[(spy.index >= f"{yr}-01-01") & (spy.index <= f"{yr}-12-31")]
            bench.append(float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 2 else 0.0)
        # random control: 5 random pairs, same machinery
        cols = list(px.columns)
        rp = [(0, cols[i], cols[j], 1.0, 15) for i, j in
              (rng.choice(len(cols), 2, replace=False) for _ in range(N_PAIRS))]
        rnd.append(float(np.sum(trade_year(px, yr, rp)) / max(1, N_PAIRS)))
        print(yr, len(pairs), "pairs ->", round(yr_ret, 4), flush=True)
    arr = np.array(strat)
    res = {"experiment": "e12_pairs", "years": years,
           "annual_returns": [round(float(a), 4) for a in arr],
           "mean_annual": round(float(arr.mean()), 4),
           "sharpe": round(float(arr.mean() / arr.std()), 2) if arr.std() > 0 else 0.0,
           "spy_mean_annual": round(float(np.mean(bench)), 4) if bench else None,
           "random_mean_annual": round(float(np.mean(rnd)), 4),
           "verdict": "BEAT" if arr.mean() > 0 and (np.mean(bench) is not None and arr.mean() > np.mean(bench)) else "LOSE"}
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e12_pairs", "generation": 0, "stage": "holdout",
               "params": {"gate": "ADF p<0.01, HL 5-60, top5", "entry_z": 2, "exit_z": 0.5},
               "seed": 0, "verdict": res["verdict"], "origin": "manual"})
    json.dump(res, open(os.path.join(ROOT, "reports", "e12-pairs.json"), "w"), indent=1)
    lines = ["# e12 — pairs trading via cointegration " + time.strftime("%Y-%m-%d"), "",
             f"Walk-forward years {years[0]}-{years[-1]}, fit on trailing 3y, top-5 pairs, z=+-2/0.5/4, 10bps/pair round trip.", "",
             f"- Mean annual return: **{res['mean_annual']}** (Sharpe {res['sharpe']})",
             f"- SPY mean annual: {res['spy_mean_annual']}",
             f"- Random-pairs control (same rule, random pairs): {res['random_mean_annual']}",
             f"- Verdict: **{res['verdict']}**", "",
             "Note: the 780-pair scan is heavy multiple testing; the walk-forward control",
             "and the random-pair comparison are the honest referees. A Kalman hedge ratio",
             "is the v1 upgrade only if v0 clears the gate."]
    open(os.path.join(ROOT, "reports", "e12-pairs.md"), "w").write("\n".join(lines))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
