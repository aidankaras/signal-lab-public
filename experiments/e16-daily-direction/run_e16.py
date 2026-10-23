"""python experiments/e16-daily-direction/run_e16.py -- see SPEC.md (pre-registered). Run once."""
import json, os, sys, time
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.evaluator import metrics, evaluate, log_trial
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
RT = 20.0 / 1e4          # 5bps/side + 5bps slippage/side = 20 bps round trip
OOS0, STEP, EMB = "2010-01-01", 63, 1
START = "2004-06-01"


def fetch_ohlc(t):
    import yfinance as yf
    d = yf.download(t, start=START, auto_adjust=True, progress=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d.index = pd.to_datetime(d.index).tz_localize(None)
    return d.dropna(how="all").sort_index()


def load():
    path = os.path.join(data.CACHE, "e16_px.pkl")
    os.makedirs(data.CACHE, exist_ok=True)
    if os.path.exists(path):
        return pd.read_pickle(path)
    out = {t: fetch_ohlc(t) for t in ["SPY", "^VIX", "^N225", "^GDAXI"]}
    pd.to_pickle(out, path)
    return out


def build(px):
    s = px["SPY"][["Open", "High", "Low", "Close"]].dropna()
    o, h, l, c = s.Open, s.High, s.Low, s.Close
    f = pd.DataFrame(index=s.index)
    c1 = c.shift(1)
    f["gap"] = o / c1 - 1
    f["ret1"] = c1 / c.shift(2) - 1
    f["oc1"] = (c / o).shift(1) - 1
    f["on1"] = (o / c.shift(1)).shift(1) - 1
    f["ret5"] = c1 / c.shift(6) - 1
    f["ret20"] = c1 / c.shift(21) - 1
    f["vol20"] = c.pct_change().rolling(20).std().shift(1)
    v = px["^VIX"].Close.reindex(s.index).ffill()
    f["vix"] = np.log(v.shift(1)); f["vixchg1"] = v.shift(1) / v.shift(2) - 1; f["vixchg5"] = v.shift(1) / v.shift(6) - 1
    n = px["^N225"].Close.pct_change()
    f["nik"] = n.reindex(s.index).fillna(0.0)  # same-date Nikkei close precedes US open
    g = px["^GDAXI"].Close.pct_change()
    f["dax1"] = g.reindex(s.index).ffill().shift(1)  # prior US session's DAX return (conservative)
    f["dow"] = s.index.dayofweek
    y = (c > o).astype(int)
    return f, y, s


def model(kind):
    if kind == "logit":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
    return HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, l2_regularization=1.0, random_state=16)


def walk(f, y, kind):
    X = f.dropna(); yy = y.loc[X.index]; idx = X.index
    oos = np.where(idx >= OOS0)[0]; p = pd.Series(np.nan, index=idx)
    for b in range(0, len(oos), STEP):
        blk = oos[b:b + STEP]; tr_end = blk[0] - EMB  # exclusive; 1-day embargo
        m = model(kind).fit(X.values[:tr_end], yy.values[:tr_end])
        p.iloc[blk] = m.predict_proba(X.values[blk])[:, 1]
    return p.dropna()


def shp(x):
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252)) if x.std(ddof=1) > 0 else 0.0


def overlay(s, tp, sl):
    o, h, l, c = s.Open, s.High, s.Low, s.Close
    r = c / o - 1
    r = r.where(~(h / o - 1 >= tp), tp)
    r = r.where(~(l / o - 1 <= -sl), -sl)  # applied last: stop wins ties
    return r


def stats(ret, pos, y_true=None, p=None, base=None):
    """ret = daily net return series (0 when flat)."""
    m = metrics(ret); m["exposure"] = round(float(pos.mean()), 3); m["trades"] = int(pos.sum())
    if p is not None:
        pred = (pos > 0).astype(int)
        m["acc"] = round(float((pred == y_true).mean()), 4); m["base_rate_up"] = round(float(y_true.mean()), 4)
        m["auc"] = round(float(roc_auc_score(y_true, p)), 4)
    return m


def main():
    px = load(); f, y, s = build(px)
    ocr = (s.Close / s.Open - 1); onr = (s.Open.shift(-1) / s.Close - 1)
    preds = {k: walk(f, y, k) for k in ["logit", "hgb"]}
    idx = preds["logit"].index.intersection(preds["hgb"].index)
    W = idx[idx >= OOS0]
    ocW, yW = ocr.loc[W], y.loc[W]
    onW = onr.loc[W].fillna(0.0)
    spy_cc = s.Close.pct_change().loc[W]
    res = {"window": [str(W[0].date()), str(W[-1].date())], "n_days": int(len(W)), "base_rate_up": round(float(yW.mean()), 4)}
    ones = pd.Series(1, index=W)

    def net(pos, r=None):
        r = ocW if r is None else r
        return pos * r - pos * RT

    base = {}
    al = net(ones); base["always_long_oc_net"] = stats(al, ones); base["always_long_oc_gross"] = metrics(ocW)
    base["overnight_only_net"] = {**metrics(onW - RT), "exposure": 1.0}; base["overnight_only_gross"] = metrics(onW)
    bh = spy_cc.copy(); bh.iloc[0] -= RT; base["spy_bh_cc_net"] = metrics(bh); base["spy_bh_cc_gross"] = metrics(spy_cc)
    sh_al = base["always_long_oc_net"]["sharpe"]
    rng = np.random.default_rng(16)
    rs = np.array([shp(net(pd.Series(rng.integers(0, 2, len(W)), index=W))) for _ in range(500)])
    p95, med = float(np.percentile(rs, 95)), float(np.median(rs))
    base["random_coinflip_sharpe_p95"] = round(p95, 3); base["random_coinflip_sharpe_median"] = round(med, 3)
    res["baselines"] = base

    V = [("V1", "logit", .50), ("V2", "logit", .55), ("V3", "hgb", .50), ("V4", "hgb", .55)]
    res["variants"] = {}; log = os.path.join(ROOT, "registry", "trials.jsonl")
    for vid, kind, th in V:
        p = preds[kind].loc[W]; pos = (p > th).astype(int)
        r = net(pos); st = stats(r, pos, yW, p)
        # use probability p for AUC, thresholded decision for accuracy
        ev = evaluate(r, bh)
        g = {"sharpe_gt_always_long": st["sharpe"] > sh_al, "sharpe_gt_random_p95": st["sharpe"] > p95, "auc_gt_0.52": st["auc"] > 0.52}
        ok = all(g.values())
        res["variants"][vid] = {"model": kind, "threshold": th, **st, "gross_sharpe": metrics(pos * ocW)["sharpe"],
                                "vs_spy_bh": ev["verdict"], "spy_bh_sharpe": base["spy_bh_cc_net"]["sharpe"], "gate": g, "gate_pass": ok}
        log_trial(log, {"experiment": "e16a_daily_direction", "generation": 0, "stage": "oos", "params": {"variant": vid, "model": kind, "threshold": th, "step": STEP, "embargo": EMB, "cost_rt_bps": 20},
                        "seed": 16, "sharpe": st["sharpe"], "auc": st["auc"], "verdict": "BEAT" if ok else "LOSE", "vs_spy": ev["verdict"], "origin": "manual"})
        print(vid, json.dumps(res["variants"][vid]), flush=True)

    res["overlays"] = {}
    for name, pos in [("always_long", ones), ("V1", (preds["logit"].loc[W] > .5).astype(int)), ("V3", (preds["hgb"].loc[W] > .5).astype(int))]:
        for tp, sl in [(0.01, 0.01), (0.005, 0.005)]:
            r = net(pos, overlay(s.loc[W], tp, sl)); st = stats(r, pos)
            key = f"{name}_TP{tp*100:g}_SL{sl*100:g}"; res["overlays"][key] = st
            log_trial(log, {"experiment": "e16a_daily_direction", "generation": 0, "stage": "overlay", "params": {"base": name, "tp": tp, "sl": sl, "ordering": "stop_first"},
                            "seed": 16, "sharpe": st["sharpe"], "verdict": "LOSE" if st["sharpe"] <= sh_al else "BEAT_ALWAYS_LONG_ONLY", "origin": "manual"})
            print(key, st["sharpe"], st["cagr"], st["maxdd"], flush=True)
    res["verdict"] = "BEAT" if any(v["gate_pass"] for v in res["variants"].values()) else "LOSE"
    print("BASELINES", json.dumps(base)); print("VERDICT", res["verdict"])
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    for d in (os.path.join(ROOT, "reports"), HERE):
        json.dump(res, open(os.path.join(d, "e16a-results.json"), "w"), indent=1, default=str)
    b = base
    L = [f"# e16a — daily SPY direction, trained models ({time.strftime('%Y-%m-%d')})", "",
         f"OOS {res['window'][0]}..{res['window'][1]} ({res['n_days']} days), base rate up {res['base_rate_up']}. 20 bps round trip. Verdict: **{res['verdict']}**", "",
         "| strategy | net Sharpe | CAGR | maxDD | exposure | acc | AUC | gate |", "|---|---|---|---|---|---|---|---|"]
    for k, v in res["variants"].items():
        L.append(f"| {k} {v['model']} p>{v['threshold']} | {v['sharpe']} | {v['cagr']} | {v['maxdd']} | {v['exposure']} | {v['acc']} | {v['auc']} | {'PASS' if v['gate_pass'] else 'FAIL'} |")
    for k, lab in [("always_long_oc_net", "always long open->close"), ("overnight_only_net", "overnight-only (net)"), ("spy_bh_cc_net", "SPY B&H close->close")]:
        L.append(f"| {lab} | {b[k]['sharpe']} | {b[k]['cagr']} | {b[k]['maxdd']} | | | | |")
    L.append(f"| overnight-only gross | {b['overnight_only_gross']['sharpe']} | {b['overnight_only_gross']['cagr']} | {b['overnight_only_gross']['maxdd']} | | | | |")
    L += ["", f"Random coin-flip (500 sims) net Sharpe median {b['random_coinflip_sharpe_median']}, p95 {b['random_coinflip_sharpe_p95']}.", "", "## TP/SL overlays (daily OHLC, stop-first)", "", "| overlay | Sharpe | CAGR | maxDD |", "|---|---|---|---|"]
    for k, v in res["overlays"].items():
        L.append(f"| {k} | {v['sharpe']} | {v['cagr']} | {v['maxdd']} |")
    for d in (os.path.join(ROOT, "reports"), HERE):
        open(os.path.join(d, "e16a-report.md"), "w").write("\n".join(L))


if __name__ == "__main__":
    main()
