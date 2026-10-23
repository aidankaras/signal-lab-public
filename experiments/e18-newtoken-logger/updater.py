"""e18 forward-return updater: record +1d/+7d/+30d once per (token, horizon), append-only."""
import time
from common import *
H = {"1d": 86400, "7d": 7*86400, "30d": 30*86400}
def main():
    snaps = rows(SNAP); done = {(r["id"], r["h"]) for r in rows(FWD)}; now = time.time()
    due = [(s, h) for s in snaps for h, sec in H.items() if (s["id"], h) not in done and now - s["ts"] >= sec]
    by = {}
    for s, h in due: by.setdefault(s["chain"], set()).add(s["address"])
    bp = {ch: best_pairs(ch, sorted(a)) for ch, a in by.items()}
    n = v = 0
    for s, h in due:
        p = bp[s["chain"]].get(s["address"].lower())
        liq = fnum(((p or {}).get("liquidity") or {}).get("usd"), 0); px = fnum((p or {}).get("priceUsd"))
        van = (not p) or px is None or liq < 500 or not s.get("price_usd")
        ret = -1.0 if van else px / s["price_usd"] - 1
        append(FWD, {"id": s["id"], "h": h, "ts": int(now), "price": px, "liq": liq, "vanished": van, "ret": ret}); n += 1; v += van
    print(f"snapshots={len(snaps)} due={len(due)} recorded={n} vanished={v}")
if __name__ == "__main__": main()
