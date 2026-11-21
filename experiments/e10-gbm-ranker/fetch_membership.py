#!/usr/bin/env python3
"""Regenerate sp500_membership.json (about 3 MB, gitignored).

Source: the point-in-time S&P 500 membership dataset on GitHub, fja05680/sp500, file
"S&P 500 Historical Components & Changes (Updated).csv". Each row is a date on which the
index changed, with the full comma-separated ticker list from that date on.
run_e10_v1_pit.py looks up the latest row on or before each trading day.

The "(Updated)" file is revised by its maintainer, so a fresh download may differ slightly
from the copy used for the 2026-10 e10 v1 run. Pass a commit hash to pin it:
    python fetch_membership.py [git-ref]          # default: master
Writes sp500_membership.json next to this script.
"""
import csv, io, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sp500_membership.json")
FILE = "S&P 500 Historical Components & Changes (Updated).csv"
SINCE = "2011-06-01"   # keep the membership in force on this date and every change after it


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "master"
    url = f"https://raw.githubusercontent.com/fja05680/sp500/{ref}/" + urllib.parse.quote(FILE)
    raw = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
    mem = {}
    for row in csv.DictReader(io.StringIO(raw)):
        mem[row["date"][:10]] = sorted({t.strip() for t in row["tickers"].split(",") if t.strip()})
    if not mem:
        sys.exit("no rows parsed from " + url)
    first = max((d for d in mem if d <= SINCE), default=min(mem))
    mem = {d: v for d, v in mem.items() if d >= first}
    with open(OUT, "w") as f:
        json.dump(mem, f)
    n = len({t for v in mem.values() for t in v})
    print("wrote", OUT, len(mem), "change dates", min(mem), "->", max(mem), n, "distinct tickers")


if __name__ == "__main__":
    main()
