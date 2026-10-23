"""python experiments/e14-thirdparty-etf-rules/run_e14.py -- see SPEC.md."""
import json, os, sys, time
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.experiment import simulate
from harness.evaluator import metrics, evaluate, log_trial

TICK = ["SPY", "QQQ", "IWM", "GLD", "TLT", "BTC-USD", "ETH-USD"]
COST = 10.0
IS0, OOS0 = "2015-01-01", "2021-01-01"
HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    px = data.fetch(TICK, start="2013-01-01", refresh="--refresh" in sys.argv, name="e14_etf_crypto")
    px = px[px["SPY"].notna()]  # equity calendar
    return px.ffill(limit=3)


def sig_trend(px):
    s50, s200 = px.rolling(50).mean(), px.rolling(200).mean()
    return ((px > s200) & (s50 > s200)).astype(float)

def sig_voltrend(px):
    vol = px.pct_change().rolling(20).std() * np.sqrt(252)
    return sig_trend(px) * (0.10 / vol).clip(upper=1.0).fillna(0)

def sig_breakout(px):
    hi, lo = px.rolling(20).max().shift(1), px.rolling(10).min().shift(1)
    out = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for c in px:
        pos = 0.0; v = []
        for p, h, l in zip(px[c].values, hi[c].values, lo[c].values):
            if np.isnan(p) or np.isnan(h): pos = 0.0
            elif pos == 0 and p > h: pos = 1.0
            elif pos == 1 and p < l: pos = 0.0
            v.append(pos)
        out[c] = v
    return out

def sig_dip(px):
    up = px > px.rolling(200).mean(); r = px.diff()
    entry = up & (r < 0) & (r.shift(1) < 0)
    out = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for c in px:
        pos, age, v = 0, 0, []
        for e, ri in zip(entry[c].values, r[c].values):
            if pos:
                age += 1
                if ri > 0 or age >= 5: pos, age = 0, 0
            elif e: pos, age = 1, 0
            v.append(float(pos))
        out[c] = v
    return out

def sig_mom12(px):
    me = px.groupby(px.index.to_period("M")).tail(1).index
    s = (px / px.shift(252) - 1 > 0).astype(float)
    return s.where(pd.Series(s.index.isin(me), index=s.index), axis=0).ffill().fillna(0)

STRATS = {"trend": sig_trend, "voltrend": sig_voltrend, "breakout": sig_breakout, "dip": sig_dip, "mom12": sig_mom12}

V1 = "--v1" in sys.argv
def v1_voltrend(px):
    vol = px.pct_change().rolling(20).std() * np.sqrt(252)
    return sig_trend(px) * (0.15 / vol).clip(upper=1.0).fillna(0)

def v1_breakout(px):
    """20d high entry, 10d low exit, 2xATR(14) stop. Close-only data: ATR proxied by mean |close diff| (flagged)."""
    hi, lo = px.rolling(20).max().shift(1), px.rolling(10).min().shift(1)
    atr = px.diff().abs().rolling(14).mean()
    out = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for c in px:
        pos, stop, v = 0.0, 0.0, []
        for p, h, l, a in zip(px[c].values, hi[c].values, lo[c].values, atr[c].values):
            if np.isnan(p) or np.isnan(h) or np.isnan(a): pos = 0.0
            elif pos == 0 and p > h: pos, stop = 1.0, p - 2 * a
            elif pos == 1 and (p < l or p < stop): pos = 0.0
            v.append(pos)
        out[c] = v
    return out

def v1_dip(px):
    d = px.diff(); g = d.clip(lower=0).ewm(alpha=0.5).mean(); L = (-d.clip(upper=0)).ewm(alpha=0.5).mean()
    rsi = 100 - 100 / (1 + g / L)
    entry = (px > px.rolling(200).mean()) & (rsi < 10); sma5 = px.rolling(5).mean()
    out = pd.DataFrame(0.0, index=px.index, columns=px.columns)
    for c in px:
        if c.endswith("-USD"): continue  # stocks only per the shared bot
        pos, age, v = 0, 0, []
        for e, p, m in zip(entry[c].values, px[c].values, sma5[c].values):
            if pos:
                age += 1
                if p > m or age >= 10: pos, age = 0, 0
            elif e: pos, age = 1, 0
            v.append(float(pos))
        out[c] = v
    return out

def v1_mom(px):
    s = (px / px.shift(252) - 1 > 0).astype(float)
    k = pd.Series(np.arange(len(px)) % 21 == 0, index=px.index)
    return s.where(k, axis=0).ffill().fillna(0)

if V1:
    STRATS = {"trend": sig_trend, "voltrend": v1_voltrend, "breakout": v1_breakout, "dip": v1_dip, "mom12": v1_mom}


def trades(w, px):
    """per-trade net returns per asset sleeve (position held as of signal shift)."""
    ret = px.pct_change().fillna(0); w = w.shift(1).fillna(0); out = []
    for c in w:
        cur = None
        for wi, ri in zip(w[c].values, ret[c].values):
            if wi > 0:
                cur = (cur if cur is not None else -2 * COST / 1e4) + ri
            elif cur is not None:
                out.append(cur); cur = None
        if cur is not None: out.append(cur)
    return np.array(out)


def random_bot(w, rng):
    """same per-asset entry/exit hazard as the strategy -> similar exposure & trade count, random timing."""
    b = (w > 0).astype(int); out = pd.DataFrame(0.0, index=w.index, columns=w.columns)
    for c in w:
        x = b[c].values; on = x[1:][x[:-1] == 0].mean() if (x[:-1] == 0).any() else 0
        off = 1 - x[1:][x[:-1] == 1].mean() if (x[:-1] == 1).any() else 1
        size = w[c][w[c] > 0].mean() if (w[c] > 0).any() else 0
        valid = w.index >= w[c].ne(0).idxmax() if (w[c] != 0).any() else np.zeros(len(w), bool)
        s, v = 0, np.zeros(len(x))
        u = rng.random(len(x))
        for i in range(len(x)):
            if valid[i]: s = (1 if u[i] < on else 0) if s == 0 else (0 if u[i] < off else 1)
            v[i] = s
        out[c] = v * size
    return out


def sharpe(x):
    x = x.dropna(); return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else 0.0


def main():
    px = load()
    avail = px.notna().astype(float)
    n = len(TICK)
    rets = px.pct_change().fillna(0)
    ew_bh = (avail.shift(1).fillna(0) * rets).sum(axis=1) / n
    spy = rets["SPY"]
    rng = np.random.default_rng(14)
    res = {}
    for name, fn in STRATS.items():
        w = fn(px).fillna(0) * avail / n
        net = simulate(px.fillna(0), w, cost_bps=COST)
        row = {}
        for tag, a, b in [("is", IS0, OOS0), ("oos", OOS0, None)]:
            m = (net.index >= a) & ((net.index < b) if b else True)
            pw = w[m]; tr = trades(pw * n, px[m])
            yrs = pd.Series(1, index=pw.index[(pw.diff().fillna(0) > 0).any(axis=1)]).groupby(lambda d: d.year).size()
            row[tag] = {**metrics(net[m]), "trades": int(len(tr)),
                        "pf": round(float(tr[tr > 0].sum() / -tr[tr < 0].sum()), 2) if (tr < 0).any() else None,
                        "years_30plus": int((((pw > 0) & ~(pw.shift().fillna(0) > 0)).sum(axis=1).groupby(lambda d: d.year).sum() >= 30).sum()),
                        "ew_bh_sharpe": round(sharpe(ew_bh[m]), 3), "spy_sharpe": round(sharpe(spy[m]), 3)}
        m = net.index >= OOS0
        rnd = [sharpe(simulate(px.fillna(0), random_bot(w, rng), cost_bps=COST)[m]) for _ in range(200)]
        p95 = float(np.percentile(rnd, 95)); o = row["oos"]
        g = {"trades": o["trades"] >= 100 or o["years_30plus"] >= 3,
             "maxdd": row["is"]["maxdd"] < 0.20 and o["maxdd"] < 0.20,
             "pf": (o["pf"] or 0) >= 1.2,
             "beats_bh": o["sharpe"] > o["ew_bh_sharpe"],
             "beats_random95": o["sharpe"] > p95,
             "not_too_good": o["sharpe"] < 3}
        ev = evaluate(net[m], spy[m])
        row.update({"random_p95_sharpe": round(p95, 3), "random_median_sharpe": round(float(np.median(rnd)), 3),
                    "gate": g, "gate_pass": all(g.values()), "vs_spy": ev["verdict"]})
        res[name] = row
        log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
                  {"experiment": "e14_etfbot", "generation": 0, "stage": "oos", "params": {"rule": name, "v": "v1-shared-params" if V1 else "v0-defaults"},
                   "seed": 14, "sharpe": o["sharpe"], "verdict": "PASS" if row["gate_pass"] else "FAIL", "vs_spy": ev["verdict"], "origin": "manual"})
        print(name, json.dumps({"oos": o, "gate": g, "p95": p95, "vs_spy": ev["verdict"]}), flush=True)
    json.dump(res, open(os.path.join(HERE, "e14-results-v1.json" if V1 else "e14-results.json"), "w"), indent=1)
    L = [f"# e14 — third-party ETF/crypto rules, {'v1 (shared params)' if V1 else 'v0'} ({time.strftime('%Y-%m-%d')})", "",
         f"IS {IS0[:4]}-2020, OOS {OOS0[:4]}-present, 7 assets 1/7 sleeves, 10bps/side. Gate = the bot's own + 200 random bots (95th pct).", "",
         "| rule | OOS CAGR | OOS Sharpe | MaxDD IS/OOS | trades | PF | EW B&H Sharpe | SPY Sharpe | rand p95 | gate | vs SPY |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        o = r["oos"]
        L.append(f"| {k} | {o['cagr']} | {o['sharpe']} | {r['is']['maxdd']}/{o['maxdd']} | {o['trades']} | {o['pf']} | {o['ew_bh_sharpe']} | {o['spy_sharpe']} | {r['random_p95_sharpe']} | {'PASS' if r['gate_pass'] else 'FAIL: ' + ','.join(x for x, v in r['gate'].items() if not v)} | {r['vs_spy']} |")
    L += ["", "v0 uses the bot's default parameters; v1 re-runs with the exact parameters when the author shares them."]
    open(os.path.join(HERE, "e14-report-v1.md" if V1 else "e14-report.md"), "w").write("\n".join(L))


if __name__ == "__main__":
    main()
