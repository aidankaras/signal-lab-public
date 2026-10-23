"""python run_e9_phase1.py -- e9 Phase 1 data prep (offline).

Builds point-in-time weekly summaries for the 2026 holdout window and their labels:
one JSONL row per (ticker, decision_date) with the summary text the LLM will see and
the realized 5-session abnormal-return label. The LLM never sees the label; scoring
compares its UP/DOWN call against it. Summaries use only data available at the
decision date (no lookahead: all features end at decision_date).
"""
import json, os, sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import BROAD

OUT = os.path.join(ROOT, "data", "cache", "e9_summaries.jsonl")


def main():
    from harness import data
    px = data.fetch(BROAD, start="2025-01-01", refresh=False, name="broad")
    spy = px["SPY"]
    # form-4 events from e6 cache, if present
    f4 = os.path.join(ROOT, "data", "cache", "e6_xml", "events.jsonl")
    insider = {}
    if os.path.exists(f4):
        for l in open(f4):
            r = json.loads(l)
            insider.setdefault(r["ticker"], []).append(r["date"])
    rows = []
    for t in px.columns:
        if t == "SPY": continue
        c = px[t].dropna()
        pos = c.index.searchsorted(pd.Timestamp("2026-01-01"))
        decision_dates = c.index[pos::5]  # weekly-ish, every 5th session in 2026
        for d in decision_dates:
            if d < pd.Timestamp("2026-01-01") or d > pd.Timestamp("2026-09-01"): continue
            i = c.index.get_loc(d)
            if i < 63 or i + 5 >= len(c): continue
            r21, r63 = c.pct_change(21).iloc[i], c.pct_change(63).iloc[i]
            vol = c.pct_change().rolling(21).std().iloc[i] * np.sqrt(252)
            vma = c.pct_change().rolling(5).mean().iloc[i]
            n_f4 = sum(1 for x in insider.get(t, []) if pd.Timestamp(x) > d - pd.Timedelta(days=30))
            lab = float((c.iloc[i + 5] / c.iloc[i] - 1) - spy_retn(spy, c.index[i], 5))
            rows.append({
                "ticker": t, "date": str(d)[:10], "label": lab,
                "summary": (
                    f"You are a markets analyst. As of {d.date()}, here is {t}: "
                    f"21-day return {r21:+.1%}, 63-day return {r63:+.1%}, "
                    f"annualized volatility {vol:.0%}, 5-day average daily move {vma:+.2%}, "
                    f"{n_f4} insider Form-4 transactions in the last 30 days. "
                    f"Will {t} outperform the S&P 500 over the next 5 trading sessions? "
                    f"Answer with exactly one word: UP or DOWN."
                ),
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows), "summaries ->", OUT)


def spy_retn(spy, date, n):
    s = spy.dropna()
    i = s.index.get_loc(s.index[s.index.searchsorted(date)])
    if i + n >= len(s): return np.nan
    return s.iloc[i + n] / s.iloc[i] - 1


if __name__ == "__main__":
    main()
