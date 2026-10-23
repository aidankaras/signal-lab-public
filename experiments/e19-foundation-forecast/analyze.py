"""e19 analysis per SPEC.md. usage: analyze.py PX.pkl fc_kronos.csv fc_timesfm.csv OUT.json  (stdlib+numpy/pandas/scipy)"""
import sys, json, numpy as np, pandas as pd
from scipy.stats import binomtest
px = pd.read_pickle(sys.argv[1]); fcs = {"kronos": sys.argv[2], "timesfm": sys.argv[3]}; OUT = sys.argv[4]
TICK = "SPY QQQ IWM DIA XLK XLF XLE XLV XLY XLI XLP XLU TLT GLD".split()
C = pd.DataFrame({t: px[t].Close for t in TICK}).dropna()
COST = 0.001; NSIM = 2000; T0 = pd.Timestamp("2024-07-01")
R = C.pct_change(); MOM = C / C.shift(20) - 1
def sharpe(x): x = np.asarray(x, float); s = x.std(ddof=1); return float(x.mean() / s * np.sqrt(252)) if s > 0 else 0.0
def run(W, dates, h, rets):
    """W: array [n_dec, 14] weights set at close of decision dates; returns daily net series from day after first decision to end."""
    idx = C.index; out = []; prev = np.zeros(len(TICK)); first = idx.get_loc(dates[0])
    for k, d in enumerate(dates):
        i = idx.get_loc(d); j = idx.get_loc(dates[k + 1]) if k + 1 < len(dates) else len(idx) - 1
        if j <= i: break
        seg = rets.iloc[i + 1:j + 1].values @ W[k]
        seg = seg.copy(); seg[0] -= COST * np.abs(W[k] - prev).sum(); prev = W[k]; out.append(pd.Series(seg, index=idx[i + 1:j + 1]))
    return pd.concat(out)
def topk(score, k):
    w = np.zeros_like(score)
    for r in range(score.shape[0]):
        w[r, np.argsort(-score[r])[:k]] = 1.0 / k
    return w
res = {"window_start": str(T0.date()), "cost_per_side": COST, "n_sims": NSIM, "trials": []}
rng = np.random.default_rng(19)
for model, path in fcs.items():
    f = pd.read_csv(path, parse_dates=["date"])
    for h in (1, 5):
        P = f.pivot(index="date", columns="ticker", values=f"f{h}")[TICK].dropna()
        dates = list(P.index[::h]); P = P.loc[dates]
        end = C.index[-1]
        # realized h-period returns, only for decision dates having full horizon
        fwd = C.shift(-h) / C - 1; Fw = fwd.loc[dates]; ok = Fw.notna().all(axis=1).values
        dates = [d for d, o in zip(dates, ok) if o]; P = P.loc[dates]; Fw = Fw.loc[dates]; Pn = P.values
        for strat in ("A", "B1", "B3"):
            if strat == "A":
                W = np.zeros((len(dates), 14)); W[:, 0] = (Pn[:, 0] > 0); base_score = None
                Wm = np.zeros((len(dates), 14)); Wm[:, 0] = (MOM.loc[dates, "SPY"].values > 0)
            else:
                k = 1 if strat == "B1" else 3
                W = topk(Pn, k); Wm = topk(MOM.loc[dates].values, k)
            Wb = np.zeros((len(dates), 14)); Wb[0, 0] = 1.0
            # buy-hold SPY: weight 1 at first decision, no further turnover
            Wb = np.zeros((len(dates), 14)); Wb[:, 0] = 1.0
            s = run(W, dates, h, R); sm = run(Wm, dates, h, R); sb = run(Wb, dates, h, R)
            sh, shm, shb = sharpe(s), sharpe(sm), sharpe(sb)
            sims = []
            for _ in range(NSIM):
                if strat == "A":
                    Wr = np.zeros((len(dates), 14)); Wr[:, 0] = rng.integers(0, 2, len(dates))
                else:
                    Wr = np.zeros((len(dates), 14))
                    for r in range(len(dates)): Wr[r, rng.choice(14, k, replace=False)] = 1.0 / k
                sims.append(sharpe(run(Wr, dates, h, R)))
            p95 = float(np.percentile(sims, 95))
            # hit rate
            if strat == "A":
                hit = ((Pn[:, 0] > 0) == (Fw["SPY"].values > 0)); n = len(hit); x = int(hit.sum()); base = float((Fw["SPY"].values > 0).mean())
            else:
                top = np.argsort(-Pn, axis=1)[:, :k]; rr = np.take_along_axis(Fw.values, top, axis=1) > 0
                n = rr.size; x = int(rr.sum()); base = float((Fw.values > 0).mean())
            pv = float(binomtest(x, n, base, alternative="greater").pvalue)
            ic = float(np.nanmean([np.corrcoef(pd.Series(Pn[r]).rank(), pd.Series(Fw.values[r]).rank())[0, 1] for r in range(len(dates))])) if strat != "A" else None
            gates = {"G1_gt_spy_bh": sh > shb, "G2_gt_random_p95": sh > p95, "G3_gt_mom20": sh > shm, "G4_hit_binom_p<0.05": pv < 0.05 and x / n > base}
            ver = "BEAT" if all(gates.values()) else "LOSE"
            sub = s[s.index >= "2025-08-01"]; subb = sb[sb.index >= "2025-08-01"]
            rec = {"model": model, "h": h, "strategy": strat, "n_periods": len(dates), "first_decision": str(dates[0].date()), "last_decision": str(dates[-1].date()),
                   "sharpe": round(sh, 3), "spy_bh_sharpe": round(shb, 3), "mom20_sharpe": round(shm, 3), "random_p95": round(p95, 3), "random_median": round(float(np.median(sims)), 3),
                   "hit": x, "n_hit": n, "hit_rate": round(x / n, 4), "base_rate": round(base, 4), "binom_p": round(pv, 5), "bonferroni_sig_12": pv < 0.05 / 12,
                   "mean_rank_ic": None if ic is None else round(ic, 4), "total_return": round(float((1 + s).prod() - 1), 4), "exposure": round(float(W.sum(1).mean()), 3),
                   "sub_2025_08_sharpe": round(sharpe(sub), 3), "sub_2025_08_spy_bh": round(sharpe(subb), 3), "gates": gates, "verdict": ver}
            res["trials"].append(rec); print(json.dumps(rec), flush=True)
res["n_trials"] = len(res["trials"]); res["n_beat"] = sum(t["verdict"] == "BEAT" for t in res["trials"])
json.dump(res, open(OUT, "w"), indent=1, default=bool)
