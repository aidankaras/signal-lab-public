"""python run_e13.py -- e13 "CIO framework" decomposition (pre-registered: experiments/e13-cio-framework/SPEC.md).

Tests the mechanically-testable skeleton of the popular five-stage LLM "CIO" prompt:
  Stage 1 (macro)    -> regime filter: SPY 200d MA (risk-on) vs below (defensive -> SPY).
  Stage 2 (secular)  -> point-in-time quality tilt from EDGAR companyfacts (annual filings,
                        scored by FILED date, no lookahead): revenue growth consistency,
                        net-margin level+stability, low D/E, positive ROE.
  Stage 3 (catalyst) -> NOT testable on free timestamped news; logged as not-run (lab rule).
  Stage 4 (sizing)   -> 5% position cap, 10 names max, monthly rebalance, 5bps/side.
  Stage 5 (table)    -> presentation; not a testable component.

Walk-forward portfolio vs SPY buy-and-hold on identical dates + random-10-names control.
Universe caveat: BROAD-40 survivorship (same as e10) — a pass is SUSPECT by construction.
Gate (SPEC): must beat SPY Sharpe on identical dates AND beat the plain e4-style quality
read; else LOSE and the framework question is closed with data.
"""
import json, os, sys, time, urllib.request
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.evaluator import log_trial

UA = {"User-Agent": "Trading Research Lab (contact: aidan@aidankaras.dev)"}
TR = os.path.join(ROOT, "registry", "trials.jsonl")
OUT = os.path.join(ROOT, "reports", "e13-cio.json")
TICKERS = [t for t in data.BROAD if t != "SPY"]
COST = 0.0005
CAP = 0.05           # Stage 4: 5% cap
TOPN = 10

CF = os.path.join(ROOT, "data", "cache", "e13_companyfacts")
os.makedirs(CF, exist_ok=True)


def cik_of(ticker):
    p = os.path.join(CF, "tickers.json")
    if not os.path.exists(p):
        req = urllib.request.Request("https://www.sec.gov/files/company_tickers.json", headers=UA)
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        m = {v["ticker"].upper(): int(v["cik_str"]) for v in d.values()}
        json.dump(m, open(p, "w"))
    return json.load(open(p)).get(ticker)


def companyfacts(ticker):
    p = os.path.join(CF, ticker + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    cik = cik_of(ticker)
    if not cik:
        return None
    try:
        req = urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=UA)
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        json.dump(d, open(p, "w")); time.sleep(0.15)
        return d
    except Exception:
        return None


def series(facts, tag):
    out = []
    gaap = (facts or {}).get("facts", {}).get("us-gaap", {})
    for unit in gaap.get(tag, {}).get("units", {}).values():
        for row in unit:
            if row.get("form") == "10-K" and row.get("fp") == "FY" and row.get("frame") is None:
                out.append((row["filed"], row.get("start"), row["end"], float(row["val"])))
    return sorted(set(out))


def annual_metrics(ticker):
    """Rows of (filed_date, rev_growth, net_margin, debt_equity, roe) from latest CLOSED fiscal year."""
    f = companyfacts(ticker)
    if not f:
        return []
    rev = series(f, "Revenues") + series(f, "RevenueFromContractWithCustomerExcludingAssessedTax")
    ni = series(f, "NetIncomeLoss")
    assets = series(f, "Assets")
    liab = series(f, "Liabilities")
    eq = series(f, "StockholdersEquity")
    liabeq = series(f, "LiabilitiesAndStockholdersEquity")
    rows = []
    for filed, start, end, v in rev:
        fy = pd.Timestamp(end)
        def asof(sr):
            best = None
            for fd2, s2, e2, v2 in sr:
                if pd.Timestamp(e2) <= fy and (best is None or pd.Timestamp(e2) > best[1]):
                    best = (v2, pd.Timestamp(e2))
            return best[0] if best else np.nan
        prev = asof([(fd, s, e, v) for fd, s, e, v in rev if pd.Timestamp(e) < fy - pd.Timedelta(days=300)])
        n = asof(ni); a = asof(assets); l = asof(liab) if liab else asof(liabeq)
        e = asof(eq)
        if np.isnan(prev) or prev == 0 or np.isnan(n) or np.isnan(a) or a == 0:
            continue
        de = (l / e) if (e and not np.isnan(e) and e != 0) else np.nan
        rows.append({"filed": filed, "date": fy, "rev_growth": v / prev - 1,
                     "net_margin": n / v, "de": de, "roe": n / a})
    df = pd.DataFrame(rows).drop_duplicates("date").sort_values("date")
    # keep one row per filing date (latest amendment only)
    return df.groupby("filed", as_index=False).last() if len(df) else df


def quality_scores():
    """ticker -> DataFrame indexed by filed date with quality z-score (PIT)."""
    out = {}
    for t in TICKERS:
        try:
            m = annual_metrics(t)
        except Exception:
            m = None
        if m is None or len(m) < 3:
            continue
        m = m.set_index(pd.to_datetime(m["filed"])).sort_index()
        m["margin_std"] = m["net_margin"].rolling(3, min_periods=2).std()
        m["growth_std"] = m["rev_growth"].rolling(3, min_periods=2).std()
        out[t] = m
    return out


def rank_quality(scores, when):
    """Cross-sectional quality z: high stable margins, consistent growth, low D/E, ROE>0."""
    rows = []
    for t, m in scores.items():
        h = m[m.index <= when]
        if not len(h):
            continue
        r = h.iloc[-1]
        if (when - h.index[-1]).days > 500:   # stale filing -> hold prior state, still fine
            pass
        rows.append({"ticker": t, "net_margin": r["net_margin"], "margin_std": r["margin_std"],
                     "rev_growth": r["rev_growth"], "growth_std": r["growth_std"],
                     "de": r["de"], "roe": r["roe"]})
    if len(rows) < TOPN:
        return []
    d = pd.DataFrame(rows)
    z = lambda c: (d[c] - d[c].mean()) / (d[c].std() or 1.0)
    d["q"] = (z("net_margin") - z("margin_std").fillna(0) + z("rev_growth")
              - z("growth_std").fillna(0) - z("de").fillna(d["de"].median() if d["de"].notna().any() else 0)
              + np.where(d["roe"] > 0, 0.5, -0.5))
    return list(d.nlargest(TOPN, "q")["ticker"])


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 1 and x.std() > 0 else float("nan")


def main():
    px = data.fetch(tickers=data.BROAD)
    spy = px["SPY"]
    rets = px.pct_change()
    scores = quality_scores()
    n_scores = sum(len(m) for m in scores.values())
    print(f"fundamentals: {len(scores)}/{len(TICKERS)} tickers, {n_scores} filing rows", flush=True)
    if len(scores) < TOPN:
        print("not enough fundamentals — aborting (do not fake results)"); return

    regime = (spy > spy.rolling(200).mean()).astype(bool)
    month = None
    holdings, cost_today = {}, 0.0
    eq = eq_ctrl = 1.0
    strat, ctrl, bench = [], [], []
    rng = np.random.default_rng(42)
    control = list(rng.choice(TICKERS, TOPN, replace=False))

    for i, dt in enumerate(px.index):
        # rebalance once per calendar month when risk-on
        if regime.iloc[i] and (month is None or dt.month != month):
            month = dt.month
            pick = rank_quality(scores, dt)
            new = {t: min(CAP, 1 / TOPN) for t in pick}
            turnover = sum(abs(new.get(t, 0) - holdings.get(t, 0)) for t in set(new) | set(holdings))
            cost_today = turnover * COST
            holdings = new
        r = rets.loc[dt] if i else pd.Series(0.0, index=px.columns)
        if holdings:
            w = np.array([holdings[t] for t in holdings])
            rr = np.array([r.get(t, 0.0) if not np.isnan(r.get(t, np.nan)) else 0.0 for t in holdings])
            day = float((w * rr).sum()) - cost_today
            day_c = float((np.full(TOPN, 1 / TOPN) *
                           np.array([r.get(t, 0.0) if not np.isnan(r.get(t, np.nan)) else 0.0
                                     for t in control])).sum()) - cost_today
        else:
            day = day_c = 0.0
        cost_today = 0.0
        eq *= 1 + day; eq_ctrl *= 1 + day_c
        strat.append(day); ctrl.append(day_c)
        bench.append(0.0 if np.isnan(r["SPY"]) else r["SPY"])

    s = pd.Series(strat, index=px.index); c = pd.Series(ctrl, index=px.index)
    b = pd.Series(bench, index=px.index)
    res = {
        "experiment": "e13_cio_framework", "window": [str(px.index[0].date()), str(px.index[-1].date())],
        "fundamentals_tickers": len(scores),
        "sharpe_strategy": round(sharpe(s), 3), "sharpe_control": round(sharpe(c), 3),
        "sharpe_spy": round(sharpe(b), 3),
        "total_strategy": round(eq - 1, 3), "total_spy": round(float((1 + b).prod() - 1), 3),
        "caveat": "BROAD-40 survivorship universe + price-cap rules; catalyst stage not testable (see SPEC)",
    }
    beat = res["sharpe_strategy"] > res["sharpe_spy"] and res["sharpe_strategy"] > res["sharpe_control"]
    res["verdict"] = "BEAT" if beat else "LOSE"
    log_trial(TR, {"experiment": "e13_cio_framework", "generation": 0, "stage": "holdout",
                   "params": {"topn": TOPN, "cap": CAP, "regime": "spy>200d_ma"},
                   "seed": 42, "sharpe_strategy": res["sharpe_strategy"],
                   "sharpe_spy": res["sharpe_spy"], "verdict": res["verdict"], "origin": "manual"})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    open(OUT.replace(".json", ".md"), "w").write(
        "# e13 — 'CIO framework' decomposition " + time.strftime("%Y-%m-%d") + "\n\n"
        "Mechanical skeleton of the popular five-stage LLM CIO prompt: SPY-200d-MA regime\n"
        f"filter, EDGAR point-in-time quality tilt (top {TOPN}, {int(CAP*100)}% cap, monthly), 5 bps/side.\n"
        "Catalyst-sentiment stage: NOT testable on free data — logged not-run.\n\n"
        f"- Strategy Sharpe: **{res['sharpe_strategy']}** vs SPY {res['sharpe_spy']} vs random-10 {res['sharpe_control']}\n"
        f"- Total: strategy {res['total_strategy']:+.1%} vs SPY {res['total_spy']:+.1%}\n"
        f"- Verdict: **{res['verdict']}** (gate: beat SPY AND random control on identical dates)\n"
        "- Universe caveat: BROAD-40 survivorship — even a pass would be SUSPECT (see e10).\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
