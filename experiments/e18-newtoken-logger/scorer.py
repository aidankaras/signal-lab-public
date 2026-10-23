"""e18 scorer: gates per SPEC.md."""
import random, statistics as st, time
from common import *
COST = 0.97
def net(r): return (1 + r) * COST - 1
def stats(x):
    return (len(x), st.median(x), st.mean(x), sum(1 for r in x if r <= -0.9) / len(x)) if x else (0, None, None, None)
def main():
    snaps = rows(SNAP); fw = {(r["id"], r["h"]): r for r in rows(FWD)}
    grp = {s["id"]: s["group"] for s in snaps}
    first = min((s["ts"] for s in snaps), default=time.time()); weeks = (time.time() - first) / 604800
    print(f"snapshots={len(snaps)} approved={sum(g=='APPROVED' for g in grp.values())} control={sum(g=='CONTROL' for g in grp.values())} weeks_logging={weeks:.2f}")
    res = {}
    for h in ("1d", "7d", "30d"):
        g = {"APPROVED": [], "CONTROL": []}; gz = {"APPROVED": [], "CONTROL": []}
        for i, gr in grp.items():
            r = fw.get((i, h))
            if r: g[gr].append(net(r["ret"])); gz[gr].append(r["ret"])
        allr = g["APPROVED"] + g["CONTROL"]
        for k in g:
            n, md, mn, z = stats(gz[k]); _, mdn, mnn, _ = stats(g[k])
            print(f"{h} {k:8s} n={n} net_median={mdn} net_mean={mnn} frac_near_zero={z}")
        res[h] = (g, allr)
    g, allr = res["7d"]; na = len(g["APPROVED"])
    ok_n = na >= 200 and weeks >= 6
    if na and allr:
        rng = random.Random(18); meds = []; means = []
        for _ in range(2000):
            d = rng.sample(allr, na); meds.append(st.median(d)); means.append(st.mean(d))
        p95md = sorted(meds)[int(.95*2000)-1]; p95mn = sorted(means)[int(.95*2000)-1]
        am, an = st.median(g["APPROVED"]), st.mean(g["APPROVED"])
        cm = st.median(g["CONTROL"]) if g["CONTROL"] else None; cn = st.mean(g["CONTROL"]) if g["CONTROL"] else None
        gates = [cm is not None and am > cm, cn is not None and an > cn, am > p95md, an > p95mn]
        print(f"7d p95 random same-size: median={p95md:.4f} mean={p95mn:.4f}; gates(med>ctrl,mean>ctrl,med>p95,mean>p95)={gates}")
        print("VERDICT:", ("WIN" if all(gates) else "LOSE") if ok_n else f"PENDING (need >=6 weeks and >=200 approved with 7d; have weeks={weeks:.2f}, n={na})")
    else: print("VERDICT: PENDING (no matured 7d data)")
if __name__ == "__main__": main()
