"""Fetch yfinance prices for every ticker ever in S&P 500 since 2011-06 (membership: fja05680/sp500 Updated csv)."""
import json, os, sys
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import CACHE
import yfinance as yf
mem = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sp500_membership.json")))
tk = sorted({x for v in mem.values() for x in v} | {"SPY"})
yt = [t.replace(".", "-") for t in tk]
frames, bad = [], []
for i in range(0, len(yt), 100):
    d = yf.download(yt[i:i+100], start="2011-01-01", auto_adjust=True, progress=False, threads=True)
    frames += [d["Close"], ]
    vol = d["Volume"]; frames.append(vol.add_prefix("VOL__"))
px = pd.concat(frames, axis=1).dropna(how="all", axis=1).sort_index()
os.makedirs(CACHE, exist_ok=True)
px.to_csv(os.path.join(CACHE, "sp500pit.csv"))
have = {c for c in px.columns if not c.startswith("VOL__")}
miss = [t for t in yt if t not in have]
print("tickers requested", len(yt), "with data", len(have), "missing", len(miss))
print("missing sample", miss[:60])
