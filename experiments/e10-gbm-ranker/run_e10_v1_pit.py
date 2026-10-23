"""e10-survivorship: GBM ranker on point-in-time S&P 500 membership (see SPEC.md addendum)."""
import json, os, sys, time
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from harness.data import CACHE
from harness.evaluator import log_trial
FEATS = ["mom21", "mom63", "mom126", "rev5", "vol21", "volz", "hi63_dist", "mkt21"]
H, SIDE_BPS, N_RAND, SEED = 5, 10.0, 200, 0   # 5bps fee + 5bps slippage per side

def load():
    px = pd.read_csv(os.path.join(CACHE, "sp500pit.csv"), index_col=0, parse_dates=True)
    vol = px[[c for c in px if c.startswith("VOL__")]].rename(columns=lambda c: c[5:])
    px = px[[c for c in px if not c.startswith("VOL__")]]
    mem = json.load(open(os.path.join(HERE, "sp500_membership.json")))
    md = sorted(mem)
    ms = {d: {t.replace(".", "-") for t in v} for d, v in mem.items()}
    return px, vol, ms, md

def member_on(ms, md, d):
    s = d.strftime("%Y-%m-%d"); import bisect
    i = bisect.bisect_right(md, s) - 1
    return ms[md[i]] if i >= 0 else set()

def panel(px, vol, ms, md):
    spy = px["SPY"]; rows = []
    cover = {}
    for t in px.columns:
        if t == "SPY": continue
        c = px[t]; v = vol[t] if t in vol else None
        r = c.pct_change()
        f = pd.DataFrame({"mom21": c.pct_change(21), "mom63": c.pct_change(63), "mom126": c.pct_change(126),
            "rev5": -c.pct_change(5), "vol21": r.rolling(21).std(),
            "volz": (r.rolling(5).mean() * 21 ** .5) / r.rolling(63).std(),
            "hi63_dist": c / c.rolling(63).max() - 1})
        f["mkt21"] = spy.pct_change(21)
        last = c.ffill()   # exit at last available price if name disappears (acquisition-style)
        fwd = last.shift(-H) / c - 1
        f["ret"] = fwd; f["lab"] = fwd - (spy.shift(-H) / spy - 1)
        f["ticker"] = t
        f = f[c.notna()]
        rows.append(f)
    df = pd.concat(rows).reset_index().rename(columns={"index": "date", "Date": "date"})
    df = df.dropna(subset=FEATS + ["lab", "ret"])
    df = df[df.date >= "2012-06-01"]
    # point-in-time membership filter
    keep = []
    for d, g in df.groupby("date"):
        m = member_on(ms, md, d); keep.append(g[g.ticker.isin(m)])
    return pd.concat(keep)

def sharpe(x, per=252 / H): return float(x.mean() / x.std() * per ** .5) if x.std() > 0 else 0.0
def cagr(x, per=252 / H): return float((1 + x).prod() ** (per / len(x)) - 1)

def run():
    px, vol, ms, md = load()
    df = panel(px, vol, ms, md).sort_values("date").reset_index(drop=True)
    df["y"] = (df.lab > 0).astype(int)
    dates = sorted(df.date.unique()); step, emb = 63, 5
    # coverage: share of true members per year with price data
    cov = {}
    for d in dates[::126]:
        m = member_on(ms, md, pd.Timestamp(d)); have = {t for t in m if t in px.columns and pd.notna(px[t].get(pd.Timestamp(d)))}
        cov[str(d)[:10]] = round(len(have) / max(1, len(m)), 3)
    rebal = dates[1::H]
    rb = set(rebal)
    rng = np.random.default_rng(SEED)
    ics, strat, ew, rnd = [], [], [], []
    prev = set(); prev_r = [set() for _ in range(N_RAND)]
    pos = {d: i for i, d in enumerate(dates)}
    for b in range(1, len(dates) - step, step):
        blk = dates[b:b + step]; tr = df[df.date <= dates[b - emb - 1]]
        if len(tr) < 5000 or tr.y.nunique() < 2: continue
        m = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.06, random_state=0).fit(tr[FEATS], tr.y)
        te = df[df.date.isin([d for d in blk if d in rb])].copy()
        te["p"] = m.predict_proba(te[FEATS])[:, 1]
        for d, dd in te.groupby("date"):
            if len(dd) < 50 or dd.y.nunique() < 2: continue
            ic = spearmanr(dd.p, dd.lab).statistic
            if ic == ic: ics.append((d, ic))
            k = max(1, len(dd) // 10)
            top = dd.nlargest(k, "p"); names = set(top.ticker)
            cost = (2 * (1 - len(names & prev) / len(names)) if prev else 2) * SIDE_BPS / 1e4 / 1 * 1.0
            strat.append((d, top.ret.mean() - cost, top.ret.mean(), 1 - len(names & prev) / len(names) if prev else 1.0)); prev = names
            ew.append((d, dd.ret.mean()))
            rr = []
            for j in range(N_RAND):
                pick = set(rng.choice(dd.ticker.values, k, replace=False))
                to = 1 - len(pick & prev_r[j]) / k if prev_r[j] else 1.0
                rr.append(dd.set_index("ticker").loc[list(pick), "ret"].mean() - 2 * to * SIDE_BPS / 1e4); prev_r[j] = pick
            rnd.append((d, rr))
    ic_s = pd.Series(dict(ics)).sort_index()
    s = pd.DataFrame(strat, columns=["d", "net", "gross", "turn"]).set_index("d")
    e = pd.Series(dict(ew)).sort_index()
    R = pd.DataFrame([r for _, r in rnd], index=[d for d, _ in rnd])
    spy = px["SPY"]; idx = s.index
    spyr = pd.Series([spy.shift(-H).loc[d] / spy.loc[d] - 1 for d in idx], index=idx)
    t = float(ic_s.mean() / ic_s.std() * len(ic_s) ** .5)
    rsh = R.apply(sharpe); rcg = R.apply(cagr)
    res = {"universe": "S&P500 point-in-time (fja05680), yfinance-available names", "coverage_by_date": cov,
           "window": [str(idx[0])[:10], str(idx[-1])[:10]], "n_rebalances": len(idx),
           "ic_mean": round(float(ic_s.mean()), 4), "ic_t_weekly": round(t, 2),
           "strat_net_sharpe": round(sharpe(s.net), 2), "strat_net_cagr": round(cagr(s.net), 4),
           "strat_gross_sharpe": round(sharpe(s.gross), 2), "strat_gross_cagr": round(cagr(s.gross), 4),
           "avg_turnover_per_rebal": round(float(s.turn.mean()), 3),
           "spy_sharpe": round(sharpe(spyr), 2), "spy_cagr": round(cagr(spyr), 4),
           "ew_members_sharpe": round(sharpe(e), 2), "ew_members_cagr": round(cagr(e), 4),
           "random_median_sharpe": round(float(rsh.median()), 2), "random_p95_sharpe": round(float(rsh.quantile(.95)), 2),
           "random_median_cagr": round(float(rcg.median()), 4), "cost_bps_per_side": SIDE_BPS}
    res["beat_spy"] = res["strat_net_sharpe"] > res["spy_sharpe"] and res["strat_net_cagr"] > res["spy_cagr"]
    res["beat_random"] = res["strat_net_sharpe"] > res["random_p95_sharpe"]
    res["verdict"] = "BEAT" if (t > 2 and res["beat_spy"] and res["beat_random"]) else "LOSE"
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
        {"experiment": "e10_survivorship", "generation": 1, "stage": "holdout",
         "params": {"model": "HistGB", "depth": 3, "iters": 200, "lr": 0.06, "step": 63, "embargo": 5, "hold": H, "cost_bps_side": SIDE_BPS, "universe": "sp500_pit"},
         "seed": SEED, "ic": res["ic_mean"], "t": res["ic_t_weekly"], "n": len(ic_s), "sharpe": res["strat_net_sharpe"],
         "verdict": res["verdict"], "vs_spy": "BEAT" if res["beat_spy"] else "LOSE", "origin": "manual"})
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "reports", "e10-survivorship.json"), "w"), indent=1)
    open(os.path.join(ROOT, "reports", "e10-survivorship.md"), "w").write(
        "# e10-survivorship " + time.strftime("%Y-%m-%d") + "\n\n```json\n" + json.dumps(res, indent=1) + "\n```\n")
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    run()
