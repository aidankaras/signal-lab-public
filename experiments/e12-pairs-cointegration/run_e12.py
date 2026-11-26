"""python run_e12.py -- pairs trading via cointegration (e12).

Pre-registration: experiments/e12-pairs-cointegration/SPEC.md. A genuinely different strategy
class from e0-e10: market-neutral mean reversion between two correlated names, not
directional prediction. This is the simplified classical version (Engle-Granger +
OLS hedge ratio); a Kalman-filter hedge ratio is the v1 upgrade if v0 shows anything.

Design:
- Universe: BROAD-40 daily bars 2012-present. Each fit window uses the names with full
  price history over the fit window and the trading year (late listings join when they
  qualify), so the number of pairs scanned varies by year (up to 780) and is reported.
- Walk-forward, one year at a time: fit on the trailing 3 years only, trade the next
  year, roll. No pair is ever traded using data that includes its trading year.
- Fit: OLS hedge ratio; keep pairs whose residual Engle-Granger t-stat is below the 1%
  critical value for two variables with a constant (-3.90, MacKinnon) AND whose AR(1)
  half-life is between 5 and 60 sessions. Keep the 5 closest to a 15-session half-life.
- Trade: z-score of the spread vs the fit window; enter long-spread at z < -2
  (short-spread at z > +2; no entry beyond the stop), exit at |z| < 0.5, stop at |z| > 4.
  The position decided at close t earns the spread change from t to t+1 (one-bar
  delay). Pair return = position * spread change / gross notional of both legs at entry. Costs: 10bps per pair
  round trip, half charged on entry and half on exit. Each pair gets 1/5 of capital.
- Gate (SPEC): mean annual return > 0 after costs AND > SPY's mean annual return over the
  same years. Random control: 5 random pairs per year with an OLS hedge ratio fitted on
  the same window and the same trading rule (no cointegration/half-life selection).

Errata (2026-11): the 2026-10-19 version updated the position from z_t BEFORE booking
pos * (z_t - z_{t-1}), so each entry booked the jump that triggered it against the new
position and each exit dropped the reverting move. A perfect +3 -> 0 reversion scored as
a loss. It also divided by the spread sd twice, used ADF critical values (-3.44) instead
of Engle-Granger ones, gave the random pairs a hedge ratio of 1, and dropped every name
that listed after 2012 from all years. Those results are INVALID; this file is the
corrected runner; its re-run is in e12-pairs-rerun-2026-11.*.
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
    # no global dropna(axis=1): it removed any name with a gap anywhere in 2012+ (META, listed
    # 2012-05) from every year. main() keeps, per year, the names with full fit+trade history.
    return px


def half_life(resid):
    r = np.diff(resid)
    lag = resid[:-1]
    if lag.size == 0 or lag.std() == 0: return np.inf
    # AR(1) on differences: delta_t = a + b*lag_{t-1}; b<0 => mean reverting
    X = np.column_stack([np.ones(len(lag)), lag])
    b = np.linalg.lstsq(X, r, rcond=None)[0][1]
    if b >= -1e-9 or b <= -2: return np.inf
    return -np.log(2) / b


EG_CRIT_1PCT = -3.90   # Engle-Granger, 2 variables, constant (MacKinnon 2010), large sample
EG_CRIT_5PCT = -3.34


def adf_pvalue(resid):
    """Dickey-Fuller t-stat on the OLS residual (no statsmodels), compared with Engle-Granger
    critical values. The residual comes from an estimated hedge ratio, so plain ADF values
    (-3.44 at 1%) are too lenient. Returns a coarse p bucket: 0.01, 0.05 or 1.0."""
    r = np.diff(resid)
    lag = resid[:-1]
    X = np.column_stack([np.ones(len(lag)), lag])
    beta = np.linalg.lstsq(X, r, rcond=None)[0]
    e = r - X @ beta
    se = np.sqrt(np.dot(e, e) / max(1, len(e) - 2) * np.linalg.inv(X.T @ X)[1, 1])
    if se == 0 or np.isnan(se): return 1.0
    t = beta[1] / se
    return 0.01 if t < EG_CRIT_1PCT else (0.05 if t < EG_CRIT_5PCT else 1.0)


def hedge_ratio(window, a, b):
    return float(LinearRegression().fit(window[a].values.reshape(-1, 1), window[b].values).coef_[0])


def select_pairs(window):
    best = []
    for a, b in itertools.combinations(window.columns, 2):
        beta = hedge_ratio(window, a, b)
        resid = window[b].values - beta * window[a].values
        hl = half_life(resid)
        if not (5 <= hl <= 60): continue
        if adf_pvalue(resid) > 0.01: continue
        best.append((abs(hl - 15), a, b, beta, hl))
    best.sort()
    return best[:N_PAIRS]


def pair_returns(px, year, beta, a, b):
    """Daily returns (fraction of the capital given to this pair) for one pair in one year."""
    fit_end = pd.Timestamp(f"{year}-01-01") - pd.Timedelta(days=1)
    spread = px[b] - beta * px[a]
    hist = spread[spread.index <= fit_end]
    mu, sd = hist.mean(), hist.std()
    in_year = (spread.index >= f"{year}-01-01") & (spread.index <= f"{year}-12-31")
    sp = spread[in_year]
    if sd == 0 or np.isnan(sd) or len(sp) < 2:
        return pd.Series(0.0, index=sp.index)
    z = (sp - mu) / sd
    pa, pb = px[a][in_year], px[b][in_year]
    out = np.zeros(len(sp))
    pos, notional = 0.0, np.nan
    for i in range(1, len(sp)):
        # 1) book P&L on the position held over (t-1, t], decided at close t-1
        if pos != 0:
            out[i] += pos * (sp.iloc[i] - sp.iloc[i - 1]) / notional
        # 2) decide the position at close t; it earns from t to t+1
        zt = z.iloc[i]
        if pos == 0 and abs(zt) > 2 and abs(zt) <= 4:
            pos = -np.sign(zt)                              # short the spread when z is high
            notional = abs(pb.iloc[i]) + abs(beta) * abs(pa.iloc[i])
            out[i] -= COST / 2
        elif pos != 0 and (abs(zt) < 0.5 or abs(zt) > 4):
            pos = 0.0
            out[i] -= COST / 2
    return pd.Series(out, index=sp.index)


def trade_year(px, year, pairs):
    """Equal capital (1/N_PAIRS) per selected pair; returns the daily portfolio return series."""
    days = px.index[(px.index >= f"{year}-01-01") & (px.index <= f"{year}-12-31")]
    port = pd.Series(0.0, index=days)
    for _, a, b, beta, _hl in pairs:
        port = port.add(pair_returns(px, year, beta, a, b) / N_PAIRS, fill_value=0.0)
    return port


def main():
    px_all = prices()
    spy = px_all["SPY"] if "SPY" in px_all else None
    px_all = px_all.drop(columns=["SPY"], errors="ignore")
    years = list(range(2016, 2027))
    strat, bench, rnd, used, scanned = [], [], [], [], []
    rng = np.random.default_rng(0)
    for yr in years:
        span = px_all[(px_all.index >= pd.Timestamp(yr - 3, 1, 1)) & (px_all.index <= pd.Timestamp(yr, 12, 31))]
        px = span.dropna(axis=1)           # names with full history over fit window + trading year
        fit = px[px.index < pd.Timestamp(yr, 1, 1)]
        if len(fit) < 400: continue
        pairs = select_pairs(fit)
        if not pairs: continue
        yr_ret = float((1 + trade_year(px, yr, pairs)).prod() - 1)
        strat.append(yr_ret); used.append(yr)
        n = px.shape[1]; scanned.append(n * (n - 1) // 2)
        # SPY same year
        if spy is not None:
            s = spy[(spy.index >= f"{yr}-01-01") & (spy.index <= f"{yr}-12-31")]
            bench.append(float(s.iloc[-1] / s.iloc[0] - 1) if len(s) > 2 else 0.0)
        # random control: 5 random pairs, hedge ratio fitted on the same window, same trading rule
        cols = list(px.columns)
        rp = []
        for _ in range(N_PAIRS):
            i, j = rng.choice(len(cols), 2, replace=False)
            rp.append((0, cols[i], cols[j], hedge_ratio(fit, cols[i], cols[j]), np.nan))
        rnd.append(float((1 + trade_year(px, yr, rp)).prod() - 1))
        print(yr, len(pairs), "pairs ->", round(yr_ret, 4), flush=True)
    arr = np.array(strat)
    spy_mean = float(np.mean(bench)) if bench else None
    beat = bool(arr.mean() > 0 and spy_mean is not None and arr.mean() > spy_mean)
    res = {"experiment": "e12_pairs", "years": used,
           "pairs_scanned_per_year": scanned,
           "annual_returns": [round(float(a), 4) for a in arr],
           "mean_annual": round(float(arr.mean()), 4),
           "annual_sharpe_proxy": round(float(arr.mean() / arr.std(ddof=1)), 2) if len(arr) > 1 and arr.std() > 0 else 0.0,
           "spy_mean_annual": round(spy_mean, 4) if spy_mean is not None else None,
           "random_mean_annual": round(float(np.mean(rnd)), 4),
           "verdict": "BEAT" if beat else "LOSE"}
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "reports", "e12-pairs.json"), "w"), indent=1)
    lines = ["# e12 — pairs trading via cointegration " + time.strftime("%Y-%m-%d"), "",
             f"Walk-forward years {years[0]}-{years[-1]}, fit on trailing 3y, top-5 pairs, z=+-2/0.5/4, 10bps/pair round trip.", "",
             f"- Mean annual return: **{res['mean_annual']}** (annual Sharpe proxy {res['annual_sharpe_proxy']}, {len(used)} yearly points)",
             f"- SPY mean annual: {res['spy_mean_annual']}",
             f"- Random-pairs control (same rule, random pairs): {res['random_mean_annual']}",
             f"- Verdict: **{res['verdict']}**", "",
             f"Note: scanning up to {max(scanned) if scanned else 0} pairs a year is heavy multiple testing; the walk-forward control",
             "and the random-pair comparison are the honest referees. A Kalman hedge ratio",
             "is the v1 upgrade only if v0 clears the gate."]
    open(os.path.join(ROOT, "reports", "e12-pairs.md"), "w").write("\n".join(lines))
    # log only after outputs are written, so a crash cannot leave an orphan trial row
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e12_pairs", "generation": 0, "stage": "holdout",
               "params": {"gate": "EG t<-3.90, HL 5-60, top5", "entry_z": 2, "exit_z": 0.5, "v": 2},
               "seed": 0, "verdict": res["verdict"], "origin": "manual"})
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
