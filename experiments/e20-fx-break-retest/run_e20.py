"""e20 runner: fxalexg break-retest-engulfing backtest (see SPEC.md).

Usage: python run_e20.py [outdir]
Reads $E20_HOME/data/{PAIR}_h1.csv (UTC hourly, Dukascopy; default E20_HOME = this folder).
Writes out/results.json, out/trades_<variant>.csv.
All logic causal: signals on closed bars, entry at next 1H open.
"""
import json, os, sys
import numpy as np
import pandas as pd

HOME = os.environ.get("E20_HOME", os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HOME, "data")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
         "NZDUSD", "GBPJPY", "GBPCHF", "AUDCAD"]
SPREAD = {"EURUSD": 0.8, "USDJPY": 1.0, "GBPUSD": 1.0, "USDCHF": 1.0,
          "USDCAD": 1.0, "AUDUSD": 1.2, "NZDUSD": 1.2,
          "GBPJPY": 2.5, "GBPCHF": 2.5, "AUDCAD": 2.5}
SLIP = 0.5
DEV_END = pd.Timestamp("2022-01-01", tz="UTC")


def pipval(p):
    return 0.01 if "JPY" in p else 0.0001


def roundstep(p):
    return 0.5 if "JPY" in p else 0.005


def load(pair):
    df = pd.read_csv(f"{DATA}/{pair}_h1.csv")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    df["ldate"] = df.time.dt.tz_convert("Europe/London").dt.date
    # drop dead weekend bars (zero range and zero volume)
    alive = ~(((df.high == df.low) & (df.open == df.close)) & (df.vol <= 0))
    df = df[alive].reset_index(drop=True)
    return df


def build_context(pair, df, use_round=True):
    """Daily/weekly bias + AOI levels, all causal."""
    pip = pipval(pair)
    g = df.groupby("ldate")
    daily = g.agg(o=("open", "first"), h=("high", "max"), l=("low", "min"),
                  c=("close", "last"), nd=("close", "size"))
    daily = daily[daily.nd >= 12].copy()
    daily["ema50"] = daily.c.ewm(span=50, adjust=False).mean()
    wkkey = pd.to_datetime(daily.index) - pd.to_timedelta(
        pd.to_datetime(daily.index).dayofweek, unit="D")
    wk = pd.DataFrame({"c": daily.c.values, "wk": wkkey}).groupby("wk").agg(
        c=("c", "last"), nd=("c", "size"))
    wk = wk[wk.nd >= 3]
    wk["ema20"] = wk.c.ewm(span=20, adjust=False).mean()
    wkmap = {k: (c < e, c > e) for k, c, e in zip(wk.index, wk.c, wk.ema20)}
    bias = {}
    for dte, row in daily.iterrows():
        k = wkkey[list(daily.index).index(dte)]
        wdn, wup = wkmap.get(k, (False, False))
        bias[dte] = (bool(row.c < row.ema50) and wdn, bool(row.c > row.ema50) and wup)
    # 5-bar fractal swings on daily, confirmed 2 bars after the swing bar
    dts = list(daily.index)
    h, l = daily.h.values, daily.l.values
    n = len(daily)
    swings = []  # (confirm_date, swing_date, level, side)
    for i in range(2, n - 2):
        j = i - 2  # swing bar
        if h[j] > h[j - 1] and h[j] > h[j - 2] and h[j] > h[i - 1] and h[j] > h[i]:
            swings.append((dts[i], dts[j], h[j], "short"))
        if l[j] < l[j - 1] and l[j] < l[j - 2] and l[j] < l[i - 1] and l[j] < l[i]:
            swings.append((dts[i], dts[j], l[j], "long"))
    # AOI levels per confirmation date, expire 120 trading days later
    aois = {}
    for cd, sd, lvl, side in swings:
        idx = dts.index(cd)
        expiry = dts[idx + 120] if idx + 120 < n else dts[-1] + pd.Timedelta(days=7)
        if not use_round:  # ablation: the raw swing level itself is the AOI
            aois.setdefault(cd, []).append((float(lvl), side, expiry))
            continue
        step = roundstep(pair)
        k0 = np.floor((lvl - 15 * pip) / step)
        cands = [round(k0 * step + m * step, 8)
                 for m in range(int(np.ceil(30 * pip / step)) + 2)]
        for L in cands:
            if abs(L - lvl) <= 15 * pip + 1e-12:
                aois.setdefault(cd, []).append((L, side, expiry))
    return daily, bias, aois


def bearish_engulf(o, c, k):
    if k < 1:
        return False
    return (c[k] < o[k] and c[k - 1] > o[k - 1] and
            o[k] >= c[k - 1] and c[k] <= o[k - 1])


def bullish_engulf(o, c, k):
    if k < 1:
        return False
    return (c[k] > o[k] and c[k - 1] < o[k - 1] and
            o[k] <= c[k - 1] and c[k] >= o[k - 1])


def gen_trades(pair, df, use_round=True, use_trigger=True, use_trend=True,
               use_vetoes=True):
    """Return list of trade dicts for one pair."""
    pip = pipval(pair)
    daily, bias, aois = build_context(pair, df, use_round)
    h4 = df.set_index("time").resample("4h").agg(
        o=("open", "first"), h=("high", "max"), l=("low", "min"),
        c=("close", "last")).dropna()
    h4t = h4.index.values
    h4c, h4h = h4.c.values, h4.h.values

    t = df.time.values
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    n = len(df)
    trades = []
    for brk_k in range(1, len(h4)):
        T4 = h4t[brk_k]
        # which London date does this 4H close belong to (for bias/AOI)?
        ld = pd.Timestamp(T4, tz="UTC").tz_convert("Europe/London").date()
        # bias as of previous completed daily bar
        dts = list(daily.index)
        prev_days = [d for d in dts if d < ld]
        if not prev_days:
            continue
        bd, bu = bias[prev_days[-1]] if use_trend else (True, True)
        # active AOI levels
        active = []
        for cd, lst in aois.items():
            for L, side, expiry in lst:
                if cd <= prev_days[-1] <= expiry:
                    active.append((L, side))
        for L, side in active:
            if side == "short" and not bd:
                continue
            if side == "long" and not bu:
                continue
            broke = (side == "short" and h4c[brk_k] < L) or \
                    (side == "long" and h4c[brk_k] > L)
            if not broke:
                continue
            # avoid re-using the same break: require previous 4H close NOT beyond
            prev_broke = (side == "short" and h4c[brk_k - 1] < L) or \
                         (side == "long" and h4c[brk_k - 1] > L)
            if prev_broke:
                continue
            tr = simulate_setup(pair, df, h4, h4t, h4c, brk_k, L, side,
                                use_trigger, use_vetoes)
            if tr:
                trades.append(tr)
    return trades


def simulate_setup(pair, df, h4, h4t, h4c, brk_k, L, side, use_trigger, use_vetoes):
    pip = pipval(pair)
    t = df.time.values
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    T4 = pd.Timestamp(h4t[brk_k], tz="UTC")
    Tend = T4 + pd.Timedelta(hours=72)
    i0 = int(np.searchsorted(t, np.datetime64(T4.tz_convert("UTC").tz_localize(None))))
    i1 = int(np.searchsorted(t, np.datetime64(Tend.tz_convert("UTC").tz_localize(None))))
    retested = False
    extreme = h[i0] if side == "short" else l[i0]
    for k in range(i0, min(i1 + 48, len(df))):  # allow trigger candle just past window edge? no: window only
        if k > i1:
            break
        tk = pd.Timestamp(t[k], tz="UTC").tz_convert("Europe/London")
        # invalidation: 4H body close back through L by > 10 pips
        kh4 = int(np.searchsorted(h4t, t[k], side="right")) - 1
        if kh4 >= 0 and pd.Timestamp(h4t[kh4], tz="UTC") >= T4:
            if (side == "short" and h4c[kh4] > L + 10 * pip) or \
               (side == "long" and h4c[kh4] < L - 10 * pip):
                return None
        if side == "short":
            extreme = max(extreme, h[k])
            if h[k] >= L - 5 * pip:
                retested = True
        else:
            extreme = min(extreme, l[k])
            if l[k] <= L + 5 * pip:
                retested = True
        if not retested:
            continue
        # vetoes apply to entry (trigger close) date
        if use_vetoes:
            if tk.weekday() in (6, 3, 4):  # Sun, Thu, Fri
                continue
            if tk.weekday() == 4 and tk.day <= 7:  # first Friday NFP (Sun/Thu/Fri veto normally covers)
                continue
        # hour gate: trigger candle closes 07:00-17:00 London
        if not (7 <= tk.hour <= 17):
            continue
        if use_trigger:
            if side == "short" and not bearish_engulf(o, c, k):
                continue
            if side == "long" and not bullish_engulf(o, c, k):
                continue
        # bias side close
        if side == "short" and c[k] >= L:
            continue
        if side == "long" and c[k] <= L:
            continue
        entry_k = k + 1
        if entry_k >= len(df):
            return None
        entry = o[entry_k]
        sl = extreme + 5 * pip if side == "short" else extreme - 5 * pip
        dist = abs(entry - sl)
        if not (15 * pip - 1e-12 <= dist <= 40 * pip + 1e-12):
            return None
        cost = (SPREAD[pair] + 2 * SLIP) * pip
        net_sl = dist + cost  # effective adverse move to stop incl costs
        return dict(pair=pair, side=side, level=L, entry_time=str(pd.Timestamp(t[entry_k], tz="UTC")),
                    entry=entry, sl=sl, dist=dist, cost=cost, entry_k=entry_k,
                    trigger_time=str(tk), break_time=str(T4))
    return None


def resolve_trade(pair, df, tr, R):
    """Walk forward 1H bars; SL priority when both touched in same bar."""
    t = df.time.values
    h, l, c = df.high.values, df.low.values, df.close.values
    k0 = tr["entry_k"]
    entry, sl = tr["entry"], tr["sl"]
    d = tr["dist"]
    tp = entry - R * d if tr["side"] == "short" else entry + R * d
    cap = np.datetime64(pd.Timestamp(t[k0]) + pd.Timedelta(days=30))
    for k in range(k0, len(df)):
        if tr["side"] == "short":
            hit_sl = h[k] >= sl
            hit_tp = l[k] <= tp
        else:
            hit_sl = l[k] <= sl
            hit_tp = h[k] >= tp
        if hit_sl:
            gross = -1.0
        elif hit_tp:
            gross = R
        elif t[k] >= cap:  # 30-day max hold: exit at this bar's close
            px = c[k]
            gross = (entry - px) / d if tr["side"] == "short" else (px - entry) / d
        else:
            continue
        net = gross - tr["cost"] / d
        tr2 = dict(tr)
        tr2.update(gross_R=gross, net_R=net, exit_time=str(pd.Timestamp(t[k], tz="UTC")), R=R)
        return tr2
    return None


def equity_curve(trades_sorted, risk=0.01):
    eq = 1.0
    curve = []
    for tr in trades_sorted:
        eq *= (1 + risk * tr["net_R"])
        curve.append((tr["entry_time"], eq))
    return curve


def annualized(trades_sorted, risk=0.01):
    if not trades_sorted:
        return 0.0, 0.0, 0.0
    curve = equity_curve(trades_sorted, risk)
    t0 = pd.Timestamp(trades_sorted[0]["entry_time"])
    t1 = pd.Timestamp(trades_sorted[-1]["exit_time"])
    years = max((t1 - t0).total_seconds() / (365.25 * 86400), 1e-9)
    ret = curve[-1][1] ** (1 / years) - 1
    rs = np.array([tr["net_R"] for tr in trades_sorted])
    # approximate trade-level vol in return space
    vol_t = np.std(risk * rs, ddof=1) if len(rs) > 1 else 0.0
    tpy = len(rs) / years
    vol_a = vol_t * np.sqrt(tpy)
    sharpe = (np.mean(risk * rs) / vol_t * np.sqrt(tpy)) if vol_t > 0 else 0.0
    return ret, vol_a, sharpe


def random_control(df_by_pair, sl_dists, R, n_strats=2000, seed=20, n_per=80):
    """Random entries with same eligibility, SL dist, TP, costs."""
    rng = np.random.default_rng(seed)
    pipmap = {p: pipval(p) for p in df_by_pair}
    out = []
    for s in range(n_strats):
        rs = []
        for _ in range(n_per):
            pair = PAIRS[rng.integers(len(PAIRS))]
            df = df_by_pair[pair]
            pip = pipmap[pair]
            o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
            k = int(rng.integers(600, len(df) - 2000))
            tk = pd.Timestamp(df.time.values[k], tz="UTC").tz_convert("Europe/London")
            # eligibility: trigger closes 07-17, entry days Mon/Tue/Wed
            if not (7 <= tk.hour <= 17 and tk.weekday() in (0, 1, 2)):
                continue
            side = "short" if rng.random() < 0.5 else "long"
            # SL distance sampled in PIPS from realized trades (pooling raw price
            # distances across JPY / non-JPY pairs was a bug: -2R control mean)
            dist = float(rng.choice(sl_dists)) * pip
            entry = o[k + 1]
            sl = entry + dist if side == "short" else entry - dist
            tr = dict(pair=pair, side=side, entry=entry, sl=sl, dist=dist,
                      cost=(SPREAD[pair] + 2 * SLIP) * pip, entry_k=k + 1)
            r = resolve_trade(pair, df, tr, R)
            if r:
                rs.append(r["net_R"])
        if rs:
            out.append(float(np.mean(rs)))
    return out


def baseline(df_by_pair):
    """Daily MA20/100 trend-follow, 1% risk w/ 2*ATR(20) stop, same costs."""
    eq = 1.0
    curve = []
    rets = []
    allret = {}
    for pair, df in df_by_pair.items():
        pip = pipval(pair)
        d = df.set_index("time").resample("1D").agg(
            o=("open", "first"), h=("high", "max"), l=("low", "min"),
            c=("close", "last")).dropna()
        ma20, ma100 = d.c.rolling(20).mean(), d.c.rolling(100).mean()
        tr20 = (d.h - d.l).rolling(20).mean()
        pos = np.where((d.c > ma20) & (d.c > ma100), 1,
                       np.where((d.c < ma20) & (d.c < ma100), -1, 0))
        ret = d.c.pct_change().fillna(0)
        atr = tr20 / d.c
        size = np.clip(0.01 / (2 * atr.replace(0, np.nan)), 0, 5).fillna(0)
        costd = (SPREAD[pair] + 2 * SLIP) * pip / d.c
        strat = pd.Series(pos, index=d.index).shift(1) * ret * size.shift(1) \
            - pd.Series(pos, index=d.index).diff().abs().fillna(0) * costd / 2
        allret[pair] = strat
    # level 0 = pair, level 1 = date: average across pairs per date (bug fix:
    # previously grouped by pair, giving 10 'days' and a -100% annual figure)
    port = pd.concat(allret).groupby(level=1).mean().sort_index()
    eq = (1 + port).cumprod()
    years = max((port.index[-1] - port.index[0]).days / 365.25, 1e-9)
    ann = eq.iloc[-1] ** (1 / years) - 1
    vol = port.std() * np.sqrt(len(port) / years)
    return ann, vol, float(eq.iloc[-1])


def ruin_prob(net_rs, risk, n_boot=5000, seed=42):
    rng = np.random.default_rng(seed)
    rs = np.array(net_rs)
    cnt = 0
    for _ in range(n_boot):
        sample = rng.choice(rs, size=len(rs), replace=True)
        eq = np.exp(np.cumsum(np.log1p(np.clip(risk * sample, -0.999, None))))
        if eq.min() < 0.05:
            cnt += 1
    return cnt / n_boot


def no_lookahead_test(pair="EURUSD"):
    df = load(pair)
    cut = int(len(df) * 0.8)
    t_full = gen_trades(pair, df)
    t_cut = gen_trades(pair, df.iloc[:cut].reset_index(drop=True))
    past_full = [x for x in t_full if pd.Timestamp(x["entry_time"]) <
                 pd.Timestamp(df.time.values[cut], tz="UTC")]
    key = lambda x: (x["entry_time"], x["level"], x["side"])
    ok = [key(x) for x in past_full] == [key(x) for x in t_cut]
    return ok, len(past_full), len(t_cut)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)) + "/out"
    os.makedirs(outdir, exist_ok=True)
    df_by_pair = {}
    ranges = {}
    for p in PAIRS:
        try:
            df_by_pair[p] = load(p)
            ranges[p] = (str(df_by_pair[p].time.iloc[0]), str(df_by_pair[p].time.iloc[-1]),
                         len(df_by_pair[p]))
        except FileNotFoundError:
            print("missing", p, flush=True)
    PAIRS_LIVE = [p for p in PAIRS if p in df_by_pair]
    print("pairs:", PAIRS_LIVE, ranges, flush=True)

    ok, nf, nc = no_lookahead_test("EURUSD")
    print("no-lookahead assert:", ok, nf, nc, flush=True)
    assert ok, "NO-LOOKAHEAD TEST FAILED"

    variants = {
        "primary_3R_1pos": dict(R=3.0, one_pos=True),
        "tp2R_1pos": dict(R=2.0, one_pos=True),
        "tp4R_1pos": dict(R=4.0, one_pos=True),
        "tp3R_perpair": dict(R=3.0, one_pos=False),
        "tp2R_perpair": dict(R=2.0, one_pos=False),
        "tp4R_perpair": dict(R=4.0, one_pos=False),
    }
    ablations = {
        "abl_no_round": dict(R=3.0, one_pos=True, use_round=False),
        "abl_no_trigger": dict(R=3.0, one_pos=True, use_trigger=False),
        "abl_no_trend": dict(R=3.0, one_pos=True, use_trend=False),
        "abl_no_vetoes": dict(R=3.0, one_pos=True, use_vetoes=False),
    }
    results = {"ranges": ranges, "no_lookahead": [ok, nf, nc]}
    all_trades = {}
    # ablations dev-set only
    for name, cfg in ablations.items():
        trades = []
        for p in PAIRS_LIVE:
            ts = gen_trades(p, df_by_pair[p], use_round=cfg.get("use_round", True),
                            use_trigger=cfg.get("use_trigger", True),
                            use_trend=cfg.get("use_trend", True),
                            use_vetoes=cfg.get("use_vetoes", True))
            for tr in ts:
                r = resolve_trade(p, df_by_pair[p], tr, cfg["R"])
                if r and pd.Timestamp(r["entry_time"]) < DEV_END:
                    trades.append(r)
        trades.sort(key=lambda x: x["entry_time"])
        rs = [t["net_R"] for t in trades]
        ann, vol, sh = annualized(trades)
        results[name] = dict(n=len(trades), mean_R=float(np.mean(rs)) if rs else None,
                             winrate=float(np.mean([r > 0 for r in rs])) if rs else None,
                             ann_ret=ann, ann_vol=vol, sharpe=sh)
        pd.DataFrame(trades).to_csv(f"{outdir}/trades_{name}.csv", index=False)
        print(name, results[name], flush=True)

    base_setups = {p: gen_trades(p, df_by_pair[p]) for p in PAIRS_LIVE}
    for name, cfg in variants.items():
        trades = []
        for p in PAIRS_LIVE:
            ts = base_setups[p]
            for tr in ts:
                r = resolve_trade(p, df_by_pair[p], tr, cfg["R"])
                if r:
                    trades.append(r)
        trades.sort(key=lambda x: x["entry_time"])
        if cfg["one_pos"]:
            sel, last_exit = [], None
            for tr in trades:
                et = pd.Timestamp(tr["entry_time"])
                xt = pd.Timestamp(tr["exit_time"])
                if last_exit is None or et >= last_exit:
                    sel.append(tr)
                    last_exit = xt
            trades = sel
        else:  # one open position per pair
            sel, last_exit = [], {}
            for tr in trades:
                et = pd.Timestamp(tr["entry_time"])
                if tr["pair"] not in last_exit or et >= last_exit[tr["pair"]]:
                    sel.append(tr)
                    last_exit[tr["pair"]] = pd.Timestamp(tr["exit_time"])
            trades = sel
        all_trades[name] = trades
        rs = [t["net_R"] for t in trades]
        dev = [t for t in trades if pd.Timestamp(t["entry_time"]) < DEV_END]
        hol = [t for t in trades if pd.Timestamp(t["entry_time"]) >= DEV_END]
        ann, vol, sh = annualized(trades)
        res = dict(n=len(trades), n_dev=len(dev), n_ho=len(hol),
                   mean_R_all=float(np.mean(rs)) if rs else None,
                   mean_R_dev=float(np.mean([t["net_R"] for t in dev])) if dev else None,
                   mean_R_ho=float(np.mean([t["net_R"] for t in hol])) if hol else None,
                   winrate_ho=float(np.mean([t["net_R"] > 0 for t in hol])) if hol else None,
                   ann_ret=ann, ann_vol=vol, sharpe=sh)
        # t-stat on holdout
        if len(hol) > 2:
            hr = np.array([t["net_R"] for t in hol])
            res["t_ho"] = float(hr.mean() / (hr.std(ddof=1) / np.sqrt(len(hr))))
        # ruin sims on the full-period sequence
        if rs:
            res["ruin_1pct"] = ruin_prob(rs, 0.01)
            res["ruin_50pct"] = ruin_prob(rs, 0.50)
            res["ruin_100pct"] = ruin_prob(rs, 1.00)
        results[name] = res
        pd.DataFrame(trades).to_csv(f"{outdir}/trades_{name}.csv", index=False)
        print(name, res, flush=True)

    # random-entry control for primary R, holdout window only
    prim = [t for t in all_trades["primary_3R_1pos"]
            if pd.Timestamp(t["entry_time"]) >= DEV_END]
    sl_dists = [t["dist"] / pipval(t["pair"]) for t in all_trades["primary_3R_1pos"]]
    hol_df = {p: df_by_pair[p][df_by_pair[p].time >= DEV_END].reset_index(drop=True)
              for p in PAIRS_LIVE}
    ctrl = random_control(hol_df, sl_dists, 3.0, n_strats=2000, n_per=60)
    res = results["primary_3R_1pos"]
    res["ctrl_mean"] = float(np.mean(ctrl))
    res["ctrl_p95"] = float(np.percentile(ctrl, 95))
    res["gate2"] = bool(res["mean_R_ho"] > res["ctrl_p95"]) if res["mean_R_ho"] is not None else False
    res["gate1"] = bool(res.get("t_ho", 0) >= 2.0 and (res["mean_R_ho"] or 0) > 0)
    res["gate4"] = bool(res["n_ho"] >= 60)
    # gate3 baseline
    b_ann, b_vol, b_eq = baseline(hol_df)
    res["baseline_ann"] = b_ann
    res["baseline_vol"] = b_vol
    # gate3 on HOLDOUT equity curve (SPEC: holdout only; previously full period)
    h_ann, h_vol, h_sh = annualized(prim)
    res["ho_ann_ret"], res["ho_ann_vol"] = h_ann, h_vol
    res["ho_retvol"] = h_ann / h_vol if h_vol else 0.0
    res["baseline_retvol"] = b_ann / b_vol if b_vol else 0.0
    res["gate3"] = bool(res["ho_retvol"] > res["baseline_retvol"])
    verdict = "BEAT" if all([res["gate1"], res["gate2"], res["gate3"], res["gate4"]]) else \
              ("INSUFFICIENT" if res["n_ho"] < 60 else "LOSE")
    res["verdict"] = verdict
    with open(f"{outdir}/results.json", "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("VERDICT", verdict, flush=True)


if __name__ == "__main__":
    main()
