#!/usr/bin/env python3
"""Regenerate sp500_membership.json (3 MB, too big to commit).

Source: the point-in-time S&P 500 membership dataset `fja05680/sp500`
(Hugging Face datasets) — daily membership of the index.
Usage: python fetch_membership.py
Writes sp500_membership.json next to this script (gitignored).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sp500_membership.json")

try:
    from huggingface_hub import hf_hub_download  # pip install huggingface_hub
except ImportError:
    sys.exit("pip install huggingface_hub pandas first")

# Dataset file listing varies; the parquet export is the stable path.
import pandas as pd
path = hf_hub_download(repo_id="fja05680/sp500", repo_type="dataset",
                       filename="sp500.parquet")
df = pd.read_parquet(path)
# expect columns: date, symbol (adjust if the schema changes)
mem = {}
for d, g in df.groupby(df["date"].astype(str).str[:10]):
    mem[d] = sorted(g["symbol"].unique().tolist())
with open(OUT, "w") as f:
    json.dump(mem, f)
print("wrote", OUT, len(mem), "dates")
