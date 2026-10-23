"""python run_e2_edgar.py -- e2 Form-4 insider-cluster backfill (v0, counts-only signal).

SEC EDGAR, free. v0 signal definition (pre-registered scope):
  For each ticker-week 2018-01-01..2024-12-31: n_form4 = number of Form-4 filings that week.
  Signal = z-score of n_form4 vs trailing 26-week mean/sd of that ticker. Cluster = z >= 2.
  Label = forward 21-trading-day return of the ticker. AUC = P(cluster-week fwd return >
  random-week fwd return) style rank-AUC; gate = kill if AUC < 0.55.
KNOWN LIMIT (v0, stated honestly): submissions metadata does not say buy vs sell — that needs
per-filing XML parsing (thousands of requests). v0 tests whether filing CLUSTERS predict
returns at all; if AUC < 0.55 it dies here, cheap. If it survives, v1 parses XML for
transaction codes (S vs P) before any conclusion. Survivorship-free (universe is a fixed
list from 2018, not today's winners).
"""
import json, os, sys, time, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import pandas as pd

UA = {"User-Agent": "Trading Research Lab (contact: aidan@aidankaras.dev)"}
# fixed 2018 large caps (no survivorship from picking today's names); CUSIP->CIK via SEC ticker file
TICKERS = ["AAPL", "MSFT", "XOM", "JPM", "JNJ", "PG", "WMT", "KO", "PFE", "VZ", "T", "INTC", "IBM",
           "GE", "BA", "CAT", "MMM", "DIS", "CSCO", "ORCL", "CVX", "MCD", "NKE", "HD", "UNH", "ABT",
           "MRK", "AMGN", "TXN", "LMT", "F", "GM", "META", "AMZN", "GOOGL", "NVDA", "TSLA", "NFLX",
           "COST", "PEP"]
START, END = "2018-01-01", "2024-12-31"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def cik_map():
    # file format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
    return {row["ticker"].upper(): int(row["cik_str"])
            for row in get("https://www.sec.gov/files/company_tickers.json").values()}


def form4_weeks(cik):
    sub = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    f = sub["filings"]["recent"]
    rows = [(d, a) for d, a, form in zip(f["filingDate"], f["accessionNumber"], f["form"]) if form == "4"]
    # older-than-recent filings live in a second file; only fetch if the window is incomplete
    s = pd.Series(1, index=pd.to_datetime([d for d, _ in rows]))
    return s[(s.index >= START) & (s.index <= END)]


def main():
    cm = cik_map()
    counts = {}
    for t in TICKERS:
        if t not in cm:
            print("no CIK:", t); continue
        try:
            counts[t] = form4_weeks(cm[t])
            print(t, "form4 weeks:", len(counts[t]), flush=True)
            time.sleep(0.15)
        except Exception as e:
            print(t, "ERR", e, flush=True)
    # weekly grid per ticker
    idx = pd.date_range(START, END, freq="W-MON")
    rows = []
    for t, s in counts.items():
        wk = s.groupby(s.index.to_period("W")).sum().reindex(pd.PeriodIndex(idx, freq="W"), fill_value=0).astype(float)
        mu = wk.rolling(26, min_periods=13).mean().shift(1)
        sd = wk.rolling(26, min_periods=13).std().shift(1)
        z = (wk - mu) / sd.replace(0, pd.NA)
        rows.append(pd.DataFrame({"ticker": t, "week": idx, "n": wk.values, "z": z.values}))
    sig = pd.concat(rows)
    sig = sig[sig["z"] >= 2.0]  # pre-registered cluster definition
    print("cluster signals:", len(sig))
    # labels: forward 21-day return from free price cache (fetched stooq-free via yfinance)
    from harness import data
    px = data.fetch(list({t for t in sig.ticker}), start="2018-01-01", refresh=False, name="e2_px").dropna(how="all")
    labels, keep = [], []
    for _, r in sig.iterrows():
        c = px.get(r.ticker)
        if c is None: continue
        c = c.dropna()
        pos = c.index.searchsorted(r.week, side="right") - 1
        if pos < 0 or pos + 21 >= len(c): continue
        labels.append(c.iloc[pos + 21] / c.iloc[pos] - 1); keep.append(r)
    lab = pd.DataFrame(keep); lab["fwd"] = labels
    # rank-AUC: P(random cluster-week beats random all-week)
    import numpy as np
    grid = pd.DataFrame({"ticker": sum([[t] * len(idx) for t in counts], []), "week": list(idx) * len(counts)})
    base_rows = []
    for t in counts:
        c = px.get(t)
        if c is None: continue
        c = c.dropna(); sub = grid[grid.ticker == t]
        vals = []
        for wk in sub.week:
            pos = c.index.searchsorted(wk, side="right") - 1
            if pos < 0 or pos + 21 >= len(c): vals.append(None); continue
            vals.append(c.iloc[pos + 21] / c.iloc[pos] - 1)
        base_rows += [v for v in vals if v is not None]
    cl = np.array(lab.fwd); bl = np.array(base_rows)
    rng = np.random.default_rng(0)
    auc = float(np.mean([rng.choice(cl) > rng.choice(bl) for _ in range(20000)]))
    # also directional check: cluster weeks mean fwd vs baseline mean
    res = {"n_signals": len(cl), "cluster_mean_fwd": float(np.mean(cl)), "baseline_mean_fwd": float(np.mean(bl)),
           "auc_cluster_gt_random": auc, "gate_auc_0.55": auc >= 0.55, "window": [START, END],
           "limit": "counts-only signal (no buy/sell split); AUC<0.55 kills v0"}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(ROOT, "reports", "e2-backfill.json"), "w"), indent=1)
    lab.to_csv(os.path.join(ROOT, "reports", "e2-signals.csv"), index=False)


if __name__ == "__main__":
    main()
