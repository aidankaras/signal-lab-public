"""e22: vol-targeted 12-1 TSMOM (see SPEC.md). Usage: python run_e22.py <datadir> <outdir>
Fetches Yahoo adjusted closes via yfinance if CSVs not in datadir."""
import json, os, sys
import numpy as np
import pandas as pd

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
CORE = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "UUP"]
EXTRA = ["BTC-USD", "AGG"]
TARGET, CAP, VOLWIN = 0.12, 3.0, 60
COST, BORROW = 0.0007, 0.005
HO = pd.Timestamp("2015-01-01")
os.makedirs(DATA, exist_ok=True); os.makedirs(OUT, exist_ok=True)


def get(t):
    fn = f"{DATA}/{t}.csv"
    if not os.path.exists(fn):
        import yfinance as yf
        d = yf.download(t, start="2000-01-01", auto_adjust=True, progress=False)
        d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
        d[["Close"]].to_csv(fn)
    s = pd.read_csv(fn, index_col=0, parse_dates=True)["Close"].dropna()
    return s[~s.index.duplicated()].sort_index()


px = pd.DataFrame({t: get(t) for t in CORE + EXTRA})

# ---- audit
audit = {}
bd = pd.bdate_range(px.index[0], px.index[-1])
for t in px:
    s = px[t].dropna()
    r = s.pct_change().dropna()
    gaps = s.index.to_series().diff().dt.days
    nb = len(pd.bdate_range(s.index[0], s.index[-1]))
    z = (r == 0).astype(int)
    runs = (z.groupby((z != z.shift()).cumsum()).cumsum() * z).max()
    audit[t] = dict(first=str(s.index[0].date()), last=str(s.index[-1].date()), n=len(s),
                    missing_bdays_pct=round(100 * (1 - len(s) / nb), 2) if t != "BTC-USD" else None,
                    max_gap_days=int(gaps.max()), nonpos=int((s <= 0).sum()),
                    big_moves_20pct=int((r.abs() > .2).sum()), max_zero_run=int(runs))
print(json.dumps(audit, indent=1), flush=True)

ret = px.pct_change(fill_method=None)
# month-end trading days (equity calendar from SPY; BTC values asof)
cal = px["SPY"].dropna().index
me = pd.Series(cal, index=cal).groupby([cal.year, cal.month]).last().values
me = pd.DatetimeIndex(me)


def weights(cols, lb, skip=1, longonly=False, signs=None, rng=None):
    """Weights at each month-end (index me). All inputs <= t."""
    W = {}
    P = px[cols].ffill()
    for i, t in enumerate(me):
        if i < lb:
            continue
        # prices at month-ends lb months back and skip months back (asof)
        pa, pb = P.loc[:me[i - skip]].iloc[-1], P.loc[:me[i - lb]].iloc[-1]
        first = px[cols].apply(lambda s: s.first_valid_index())
        valid = [c for c in cols if first[c] <= me[i - lb] and not np.isnan(pa[c]) and not np.isnan(pb[c])]
        if not valid:
            continue
        r = ret.loc[:t, valid].iloc[-VOLWIN:]
        vol = r.std() * np.sqrt(252)
        sig = np.sign(pa[valid] / pb[valid] - 1)
        if signs is not None:
            sig = pd.Series(rng.choice([-1.0, 1.0], len(valid)), index=valid)
        if longonly:
            sig = sig.clip(lower=0)
        w = sig * np.minimum(TARGET / vol, CAP) / len(valid)
        W[t] = w.reindex(cols).fillna(0.0)
    return pd.DataFrame(W).T


def run(Wm, cols):
    """Daily returns: weight set at month-end t applies to days after t."""
    idx = ret.index[ret.index > Wm.index[0]]
    Wd = Wm.reindex(idx.union(Wm.index)).ffill().shift(1).reindex(idx)
    Wd = Wd.reindex(columns=cols)
    gross = (Wd * ret.loc[idx, cols].fillna(0)).sum(axis=1)
    dW = Wm.diff().abs().fillna(Wm.abs()).sum(axis=1)  # turnover at month-end
    # apply the cost on the first day after rebalance
    cst = pd.Series(0.0, index=idx)
    for t, v in dW.items():
        nxt = idx[idx > t]
        if len(nxt):
            cst[nxt[0]] += v * COST
    short = (Wd.clip(upper=0).abs().sum(axis=1)) * BORROW / 252
    return (gross - cst - short)


def stats(r, label=""):
    r = r.dropna()
    if len(r) < 30:
        return dict(n_days=len(r))
    m = (1 + r).resample("ME").prod() - 1
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return dict(n_days=len(r), n_months=len(m), start=str(r.index[0].date()), end=str(r.index[-1].date()),
                sharpe=float(r.mean() / r.std() * np.sqrt(252)), cagr=float(eq.iloc[-1] ** (1 / yrs) - 1),
                maxdd=float((eq / eq.cummax() - 1).min()), vol=float(r.std() * np.sqrt(252)),
                t_month=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))), mean_month=float(m.mean()))


# ---- lookahead test: signals at month i unchanged if future data removed
def lookahead_test():
    global px, ret
    px0, ret0 = px, ret
    W_full = weights(CORE, 12)
    k = len(me) // 2
    cut = me[k]
    px = px0.loc[:cut]; ret = ret0.loc[:cut]
    W_cut = weights(CORE, 12)
    W_cut = W_cut[W_cut.index <= cut]
    px, ret = px0, ret0
    a = W_full.loc[W_cut.index]
    return bool(np.allclose(a.values, W_cut.values, equal_nan=True)), len(W_cut)


ok, nm = lookahead_test()
print("lookahead test", ok, nm, flush=True)
assert ok

variants = {
    "core_ls_12_1": dict(cols=CORE, lb=12),
    "core_btc_ls_12_1": dict(cols=CORE + ["BTC-USD"], lb=12),
    "core_longonly_12_1": dict(cols=CORE, lb=12, longonly=True),
    "core_ls_6_1": dict(cols=CORE, lb=6),
}
rets = {}
for k, v in variants.items():
    rets[k] = run(weights(v["cols"], v["lb"], longonly=v.get("longonly", False)), v["cols"])

# benchmarks
spy = ret["SPY"]
agg = ret["AGG"]
# 60/40 monthly rebalanced: constant weight each day approximates daily-rebal; use month-start drift
b6040 = pd.Series(0.0, index=ret.index)
for _, g in ret[["SPY", "AGG"]].groupby([ret.index.year, ret.index.month]):
    v = np.array([0.6, 0.4]); out = []
    for row in g.fillna(0).values:
        out.append(float((v * row).sum() / v.sum())); v = v * (1 + row)
    b6040.loc[g.index] = out

res = {"audit": audit, "lookahead_ok": ok}
rng = np.random.default_rng(22)
# random sign control (core, 12-1 structure) on holdout
N_CTRL = 1000
ctrl = []
base_cols = CORE
Wref = weights(base_cols, 12)
# faster control: reuse vol-scale from Wref (|w| = scale/N) with random signs
absW = Wref.abs()
for s in range(N_CTRL):
    sg = pd.DataFrame(rng.choice([-1.0, 1.0], absW.shape), index=absW.index, columns=absW.columns)
    Wr = absW * sg
    Wr[absW == 0] = 0.0
    r = run(Wr, base_cols)
    ctrl.append(stats(r[r.index >= HO])["sharpe"])
ctrl = np.array(ctrl)
res["ctrl"] = dict(mean=float(ctrl.mean()), p95=float(np.percentile(ctrl, 95)), n=N_CTRL)

for k, r in rets.items():
    start = r.index[0]
    dev = r[r.index < HO]
    ho = r[r.index >= HO]
    spy_ho, b_ho = spy.reindex(ho.index), b6040.reindex(ho.index)
    st = dict(dev=stats(dev), ho=stats(ho), spy_ho=stats(spy_ho), b6040_ho=stats(b_ho),
              spy_dev=stats(spy.reindex(dev.index)), b6040_dev=stats(b6040.reindex(dev.index)))
    h = st["ho"]
    g = dict(G1=bool(h["sharpe"] > st["spy_ho"]["sharpe"] and h["sharpe"] > st["b6040_ho"]["sharpe"]),
             G2=bool(h["t_month"] >= 2.5 and h["mean_month"] > 0),
             G3=bool(h["sharpe"] > res["ctrl"]["p95"]),
             G4=bool(st["dev"].get("sharpe", -1) > 0))
    st["gates"] = g
    st["verdict"] = "INSUFFICIENT" if h["n_months"] < 60 else ("BEAT" if all(g.values()) else "LOSE")
    res[k] = st
    print(k, json.dumps(st, indent=1), flush=True)
    r.to_csv(f"{OUT}/ret_{k}.csv")
print("CTRL", res["ctrl"])
json.dump(res, open(f"{OUT}/results.json", "w"), indent=1, default=str)
