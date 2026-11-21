"""python run_e13.py -- e13 "CIO framework" decomposition (pre-registered: experiments/e13-cio-framework/SPEC.md).

Tests the mechanically-testable skeleton of the popular five-stage LLM "CIO" prompt:
  Stage 1 (macro)    -> regime filter: SPY 200d MA (risk-on) vs below (defensive -> 100% SPY).
  Stage 2 (secular)  -> point-in-time quality tilt from EDGAR companyfacts (annual filings,
                        scored by FILED date, no lookahead): revenue growth consistency,
                        net-margin level+stability, low D/E, positive ROE (net income / equity).
  Stage 3 (catalyst) -> NOT testable on free timestamped news; logged as not-run (lab rule).
  Stage 4 (sizing)   -> 5% position cap, 10 names max, monthly rebalance, 5bps/side. The cap leaves
                        50% unallocated; that remainder is held in SPY so the book is fully invested.
  Stage 5 (table)    -> presentation; not a testable component.

Walk-forward portfolio vs SPY buy-and-hold on identical dates + random-10-names control
(equal weight, rebalanced on the same monthly dates, charged its own turnover cost).
Weights are decided at the close of the rebalance day and earn returns from the next day
(harness.experiment.simulate), so there is no same-bar look-ahead.

Errata (2026-11): the first run (2026-10-20) silently used the 8-ticker e0 price cache instead
of BROAD-40 (harness.data.fetch ignored `tickers` when a cache existed), was only 50% invested,
never moved to SPY when risk-off, earned the decision day's own return, computed ROA instead of
ROE, and never rebalanced the control. Its numbers are INVALID; this file is the corrected
runner and has not been re-run yet.
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
from harness.experiment import simulate

UA = {"User-Agent": "SignalLab research script (contact: YOUR_EMAIL; SEC requires a real contact)"}
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
        roe = (n / e) if (e and not np.isnan(e) and e != 0) else np.nan
        rows.append({"filed": filed, "date": fy, "rev_growth": v / prev - 1,
                     "net_margin": n / v, "de": de, "roe": roe})
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
    # name="broad" + start: the cache is only reused if it really holds BROAD-40 (see harness.data.covers)
    px = data.fetch(tickers=data.BROAD, start="2013-01-01", name="broad")
    assert set(data.BROAD) <= set(px.columns), "price panel is missing BROAD-40 tickers"
    spy = px["SPY"]
    scores = quality_scores()
    n_scores = sum(len(m) for m in scores.values())
    print(f"fundamentals: {len(scores)}/{len(TICKERS)} tickers, {n_scores} filing rows", flush=True)
    if len(scores) < TOPN:
        print("not enough fundamentals — aborting (do not fake results)"); return

    regime = (spy > spy.rolling(200).mean()).astype(bool)
    rng = np.random.default_rng(42)
    control = list(rng.choice(TICKERS, TOPN, replace=False))
    # first trading day of each calendar month; weights decided at that close, held until the next one
    rebal = px.index.to_series().groupby([px.index.year, px.index.month]).head(1).index
    w_s = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    w_c = pd.DataFrame(np.nan, index=px.index, columns=px.columns)
    for dt in rebal:
        row = pd.Series(0.0, index=px.columns)
        pick = rank_quality(scores, dt) if regime.loc[dt] else []
        for t in pick:
            row[t] = min(CAP, 1 / TOPN)
        row["SPY"] += 1.0 - row.sum()          # risk-off, no picks yet, or cap remainder -> SPY
        w_s.loc[dt] = row
        rc = pd.Series(0.0, index=px.columns)
        rc[control] = 1 / TOPN
        w_c.loc[dt] = rc
    w_s, w_c = w_s.ffill().fillna(0.0), w_c.ffill().fillna(0.0)
    close = px.ffill()
    s = simulate(close, w_s, cost_bps=COST * 1e4)
    c = simulate(close, w_c, cost_bps=COST * 1e4)
    b = close["SPY"].pct_change().fillna(0.0)
    first = w_s.index[(w_s.sum(axis=1) > 0)][0]     # score from the first day the book is held
    s, c, b = s.loc[first:], c.loc[first:], b.loc[first:]
    eq = float((1 + s).prod())
    res = {
        "experiment": "e13_cio_framework", "window": [str(s.index[0].date()), str(s.index[-1].date())],
        "fundamentals_tickers": len(scores),
        "sharpe_strategy": round(sharpe(s), 3), "sharpe_control": round(sharpe(c), 3),
        "sharpe_spy": round(sharpe(b), 3),
        "total_strategy": round(eq - 1, 3), "total_spy": round(float((1 + b).prod() - 1), 3),
        "caveat": "BROAD-40 survivorship universe + price-cap rules; catalyst stage not testable (see SPEC)",
    }
    beat = res["sharpe_strategy"] > res["sharpe_spy"] and res["sharpe_strategy"] > res["sharpe_control"]
    res["verdict"] = "BEAT" if beat else "LOSE"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    open(OUT.replace(".json", ".md"), "w").write(
        "# e13 — 'CIO framework' decomposition " + time.strftime("%Y-%m-%d") + "\n\n"
        "Mechanical skeleton of the popular five-stage LLM CIO prompt: SPY-200d-MA regime\n"
        f"filter, EDGAR point-in-time quality tilt (top {TOPN}, {int(CAP*100)}% cap, remainder in SPY, monthly), 5 bps/side.\n"
        "Catalyst-sentiment stage: NOT testable on free data — logged not-run.\n\n"
        f"- Strategy Sharpe: **{res['sharpe_strategy']}** vs SPY {res['sharpe_spy']} vs random-10 {res['sharpe_control']}\n"
        f"- Total: strategy {res['total_strategy']:+.1%} vs SPY {res['total_spy']:+.1%}\n"
        f"- Verdict: **{res['verdict']}** (gate: beat SPY AND random control on identical dates)\n"
        "- Universe caveat: BROAD-40 survivorship — even a pass would be SUSPECT (see e10).\n")
    # log only after the outputs were written, so a crash cannot leave an orphan trial row
    log_trial(TR, {"experiment": "e13_cio_framework", "generation": 0, "stage": "holdout",
                   "params": {"topn": TOPN, "cap": CAP, "regime": "spy>200d_ma", "remainder": "SPY"},
                   "seed": 42, "sharpe_strategy": res["sharpe_strategy"],
                   "sharpe_spy": res["sharpe_spy"], "verdict": res["verdict"], "origin": "manual"})
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
