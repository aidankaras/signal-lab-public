"""e3 Kalshi weather paper logger — stdlib only (runs on the VPS, no pandas).

Logs daily mid/bid/ask for live Kalshi weather markets to registry/e3-paper.jsonl.
PAPER ONLY: never places an order. The pre-registered live probe ($100 bankroll, maker-only,
5c min-edge gate) needs 4 weeks of paper consistency + Aidan's approval per test first.
Wire as a daily no_agent cron:  `python3 run_e3_logger.py`  (prints one summary line).

Note on the 5c gate: v0 measures spread/liquidity noise, not edge — edge estimation needs the
e5-style weather-model forecast, which is a later build. This logger's job is the consistent
paper record the gate requires.
"""
import json, os, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "registry", "e3-paper.jsonl")
API = "https://api.elections.kalshi.com/trade-api/v2"


def get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    # /series/ list endpoint returns {'series': None} as of 2026-10; use the known KX weather
    # series tickers directly (high/low temp for major cities). Unmatched series just 404/empty.
    sids = ["KXHIGHNY", "KXHIGHCHI", "KXHIGHLA", "KXHIGHMIA", "KXHIGHAUS", "KXHIGHDFW", "KXHIGHPHL",
            "KXHIGHPDX", "KXHIGHSEA", "KXHIGHTOR", "KXHIGHDC", "KXHIGHBOS", "KXHIGHATL", "KXHIGHDEN",
            "KXHIGHHOU", "KXHIGHMIN", "KXHIGHSLC", "KXHIGHMSP", "KXHIGHDET", "KXHIGHSF"]
    recs = []
    for sid in sids:
        try:
            mkts = get(f"/markets/?series_ticker={sid}&status=open&limit=100").get("markets") or []
        except Exception:
            continue
        for m in mkts:
            bid, ask = m.get("yes_bid_dollars"), m.get("yes_ask_dollars")
            if not bid or not ask:
                continue  # no live two-sided quote; the log's job is quote quality, so skip
            recs.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "ticker": m["ticker"],
                         "yes_bid": round(float(bid), 4), "yes_ask": round(float(ask), 4),
                         "mid": (float(bid) + float(ask)) / 2,
                         "spread_c": round((float(ask) - float(bid)) * 100, 2)})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    if recs:
        sp = sorted(r["spread_c"] for r in recs)
        print("e3 logged %d markets | median spread %dc | p90 %dc" % (len(recs), sp[len(sp)//2], sp[int(len(sp)*0.9)]))
    else:
        print("e3: no open weather markets retrieved (category layout may have changed)")


if __name__ == "__main__":
    main()
