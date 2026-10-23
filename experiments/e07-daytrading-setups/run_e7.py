"""python run_e7.py -- claimed day-trading setups, tested as stated (pre-registration:
experiments/experiment-7-claimed-setups.md). Offline-executed (needs pandas/yfinance).

Setups (no parameter tuning — rules as claimed in retail day-trading literature):
  e7a ORB 15-min breakout with VWAP-side filter
  e7b VWAP reclaim on relative volume > 1.3
  e7c VWAP-extreme mean reversion (>2x 20-bar ATR from VWAP)
  e7d gap-and-go (daily, gap > 2% on 3x RVOL, exit at close)

Data: yfinance 5-minute bars, last 60 days (platform limit — a regime sample, flagged),
BROAD-40 universe. Fills: next-bar open after trigger; stop/target intraday; forced exit
at the 15:50 bar. Costs 5bps/side + 2bps slippage = 14bps per round trip (day-trading
round trips must clear this).

Verdict: expectancy per round trip, total return vs SPY buy-and-hold and a random-entry
control with the same number of trades, over the identical window. Logged to trials.jsonl.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import BROAD
from harness.evaluator import log_trial

TICKERS = [t for t in BROAD if t != "SPY"]
COST_RT = 0.0014  # 14 bps per round trip
CACHE = os.path.join(ROOT, "data", "cache", "e7_5m")


def bars_5m(t):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, f"{t}.csv")
    if os.path.exists(f):
        return pd.read_csv(f, index_col=0, parse_dates=True)
    df = yf.download(t, interval="5m", period="60d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.to_csv(f)
    return df


def simulate(pos_price, stop, target, bars_after, side="long"):
    """Walk forward bars to first stop/target hit; forced exit at last bar.
    Returns per-trade return net of costs. side='short' inverts P&L."""
    sign = -1.0 if side == "short" else 1.0
    for _o, hi, lo, _c in bars_after.itertuples(index=False):
        if side == "long":
            if lo <= stop: return stop / pos_price - 1 - COST_RT
            if hi >= target: return target / pos_price - 1 - COST_RT
        else:
            if hi >= stop: return 1 - stop / pos_price - COST_RT
            if lo <= target: return 1 - target / pos_price - COST_RT
    last = bars_after["Close"].iloc[-1]
    return sign * (last / pos_price - 1) - COST_RT


def orb_trades(df):
    """15-min ORB with VWAP-side filter, 2R target, stop at range opposite side."""
    trades = []
    for day, d in df.groupby(df.index.date):
        d = d.between_time("09:30", "15:55")
        if len(d) < 60: continue
        rng = d.iloc[:3]  # first 15 min
        hi, lo = rng.High.max(), rng.Low.min()
        if hi <= lo: continue
        vwap = (d.Close * d.Volume).cumsum() / d.Volume.cumsum()
        after = d.iloc[3:]
        for i in range(len(after)):
            ts = after.index[i]
            if after.Close.iloc[i] > hi and after.Close.iloc[i] > vwap.iloc[3 + i]:
                risk = after.Close.iloc[i] - lo
                if risk <= 0: continue
                tail = after.iloc[i + 1:][["Open", "High", "Low", "Close"]]
                if len(tail):
                    trades.append(simulate(tail.Open.iloc[0], lo, tail.Open.iloc[0] + 2 * risk, tail))
                break
            if after.Close.iloc[i] < lo and after.Close.iloc[i] < vwap.iloc[3 + i]:
                risk = hi - after.Close.iloc[i]
                if risk <= 0: continue
                tail = after.iloc[i + 1:][["Open", "High", "Low", "Close"]]
                if len(tail):
                    trades.append(simulate(tail.Open.iloc[0], hi, tail.Open.iloc[0] - 2 * risk, tail))
                break
    return trades


def vwap_trades(df, kind):
    """kind='reclaim': long close back above VWAP after being below, RVOL>1.3.
    kind='fade': short extremes >2x ATR(20) from VWAP. Exit same bar rules simplified:
    1R stop, exit at 15:50 close or 2R target."""
    trades = []
    for day, d in df.groupby(df.index.date):
        d = d.between_time("09:30", "15:55")
        if len(d) < 60: continue
        vwap = (d.Close * d.Volume).cumsum() / d.Volume.cumsum()
        tp = d.High.rolling(20).max() - d.Low.rolling(20).min()  # ATR proxy
        rvol = d.Volume / d.Volume.expanding(min_periods=20).mean().shift(1)
        for i in range(21, len(d) - 1):
            px, vw = d.Close.iloc[i], vwap.iloc[i]
            below = d.Close.iloc[max(0, i - 6):i].values < vwap.iloc[max(0, i - 6):i].values
            if kind == "reclaim" and px > vw and below.any() and rvol.iloc[i] > 1.3:
                risk = 0.5 * tp.iloc[i]
                tail = d.iloc[i + 1:][["Open", "High", "Low", "Close"]]
                trades.append(simulate(tail.Open.iloc[0], px - risk, px + 2 * risk, tail))
                break
            if kind == "fade" and abs(px - vw) > 2 * tp.iloc[i]:
                risk = 0.5 * tp.iloc[i]
                tail = d.iloc[i + 1:][["Open", "High", "Low", "Close"]]
                trades.append(simulate(tail.Open.iloc[0], px + risk, px - 2 * risk, tail, side="short"))
                break
    return trades


def gap_and_go(bars_d):
    """Daily: gap >2% on 3x 20d RVOL, enter at open, exit at close."""
    trades = []
    for t in TICKERS:
        df = bars_d.get(t)
        if df is None: continue
        g = df.Gap > 0.02
        rv = df.Volume / df.Volume.rolling(20).mean().shift(1) > 3
        sig = df[g & rv]
        for ts, row in sig.iterrows():
            i = df.index.get_loc(ts)
            if i + 1 >= len(df): continue
            nxt = df.iloc[i + 1]
            trades.append(nxt.Close / nxt.Open - 1 - COST_RT)
    return trades


def stats(trades):
    a = np.array(trades)
    if len(a) == 0:
        return {"n": 0, "expectancy": None, "total": 0.0, "win_rate": None}
    return {"n": len(a), "expectancy": round(float(a.mean()), 5),
            "total": round(float(a.sum()), 4), "win_rate": round(float((a > 0).mean()), 3)}


def main():
    px = {}
    for t in TICKERS:
        try:
            px[t] = bars_5m(t)
        except Exception as e:
            print(t, "bars ERR", str(e)[:60], flush=True)
    spy_d = yf.download("SPY", start="2026-07-01", progress=False, auto_adjust=True)
    if isinstance(spy_d.columns, pd.MultiIndex):
        spy_d.columns = spy_d.columns.get_level_values(0)
    spy_ret = float(spy_d.Close.iloc[-1] / spy_d.Close.iloc[0] - 1)
    print("5m bars for", len(px), "tickers; SPY window return", round(spy_ret, 4), flush=True)

    daily = {t: yf.download(t, start="2026-07-01", progress=False, auto_adjust=True)
             for t in TICKERS}
    for t in daily:
        if isinstance(daily[t].columns, pd.MultiIndex):
            daily[t].columns = daily[t].columns.get_level_values(0)
        d = daily[t]
        d["Gap"] = d.Open / d.Close.shift(1) - 1
        daily[t] = d.dropna()

    res = {"window": "2026-07-01..now (5m data limited to 60d)",
           "spy_buyhold": round(spy_ret, 4), "cost_rt_bps": COST_RT * 1e4}
    for name, fn in [("e7a_orb", lambda: orb_trades(df)), ("e7b_vwap_reclaim", lambda: vwap_trades(df, "reclaim")),
                     ("e7c_vwap_fade", lambda: vwap_trades(df, "fade"))]:
        all_tr = []
        for t, df in px.items():
            try:
                all_tr += fn()
            except Exception as e:
                print(t, name, "ERR", str(e)[:60], flush=True)
        res[name] = stats(all_tr)
        print(name, res[name], flush=True)

    # random-entry control: same number of trades, random triggers from same bars
    rng = np.random.default_rng(0)
    ctrl = []
    n_target = res["e7a_orb"]["n"] or 50
    for t, df in px.items():
        for day, d in df.groupby(df.index.date):
            d = d.between_time("10:00", "15:00")
            if len(d) < 40: continue
            for _ in range(1 if rng.random() < n_target / max(1, len(px) * 55) else 0):
                i = rng.integers(20, len(d) - 1)
                tail = d.iloc[i + 1:][["Open", "High", "Low", "Close"]]
                if len(tail):
                    ctrl.append(simulate(tail.Open.iloc[0],
                                         tail.Open.iloc[0] * 0.995, tail.Open.iloc[0] * 1.01, tail))
    res["random_control"] = stats(ctrl[:n_target])
    res["e7d_gap_and_go"] = stats(gap_and_go(daily))

    res["experiment"] = "e7_claimed_setups"
    res["verdict"] = "BEAT" if any(
        (res[k]["expectancy"] or -1) > 0 and res[k]["n"] >= 30 and res[k]["total"] > res["spy_buyhold"]
        for k in ["e7a_orb", "e7b_vwap_reclaim", "e7c_vwap_fade", "e7d_gap_and_go"]) else "LOSE"
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e7_claimed_setups", "generation": 0, "stage": "holdout",
               "params": {"v": 1, "cost_rt_bps": 14}, "seed": 0,
               "expectancies": {k: res[k]["expectancy"] for k in
                                ["e7a_orb", "e7b_vwap_reclaim", "e7c_vwap_fade", "e7d_gap_and_go"]},
               "verdict": res["verdict"], "origin": "manual"})
    json.dump(res, open(os.path.join(ROOT, "reports", "e7-setups.json"), "w"), indent=1, default=str)
    lines = ["# e7 — claimed day-trading setups, tested as stated " + time.strftime("%Y-%m-%d"), "",
             f"Window: {res['window']}. BROAD-40. Costs {COST_RT*1e4:.0f}bps/round trip. Rules as claimed, untuned.", ""]
    for k in ["e7a_orb", "e7b_vwap_reclaim", "e7c_vwap_fade", "e7d_gap_and_go", "random_control"]:
        s = res[k]
        lines.append(f"- **{k}**: {s['n']} trades, expectancy {s['expectancy']}, win rate {s['win_rate']}")
    lines += ["", f"SPY buy-and-hold over the window: {res['spy_buyhold']}",
              f"Verdict: **{res['verdict']}** — expectancy after 14bps round-trip costs is what the claims never publish.",
              "", "Caveat: 5m history is ~60 days (platform limit) — a single regime sample; a PASS promotes to paper-forward only."]
    open(os.path.join(ROOT, "reports", "e7-setups.md"), "w").write("\n".join(lines))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
