"""Score e16b (SPY long/flat open->close) and e17 (single ETF pick) per SPEC-e16b-e17.md. Run any time; verdict only at n>=60."""
import json, random, statistics as st, math
from common import CALLS, chart, rows, E17_UNIVERSE
RT, N_MIN, SIMS = 0.002, 60, 2000
calls = rows(CALLS); px = {s: {d: (o, c) for d, o, c in chart(s, "1y")[1] if o} for s in E17_UNIVERSE}
oc = lambda s, d: px[s][d][1] / px[s][d][0] - 1 if d in px[s] else None
done = [c for c in calls if oc("SPY", c["date"]) is not None]
shp = lambda x: (st.mean(x) / st.stdev(x) * math.sqrt(252)) if len(x) > 2 and st.stdev(x) > 0 else 0.0
b = [(oc("SPY", c["date"]) - RT) if c["e16b_spy"] == "LONG" else 0.0 for c in done]
al = [oc("SPY", c["date"]) - RT for c in done]; rnd = random.Random(16)
r16 = [shp([(oc("SPY", c["date"]) - RT) if rnd.random() < .5 else 0.0 for c in done]) for _ in range(SIMS)]
hit = [(c["e16b_spy"] == "LONG") == (oc("SPY", c["date"]) > 0) for c in done]
e17 = [(oc(c["e17_pick"], c["date"]) - RT) if c["e17_pick"] != "NONE" else 0.0 for c in done]
r17 = [st.mean([oc(rnd.choice(E17_UNIVERSE), c["date"]) - RT for c in done]) for _ in range(SIMS)] if done else [0]
p95 = lambda v: sorted(v)[int(.95 * len(v)) - 1]
n = len(done); out = {"n_scored": n, "n_needed": N_MIN,
  "e16b": {"sharpe": round(shp(b), 3), "always_long_sharpe": round(shp(al), 3), "random_p95": round(p95(r16), 3), "hit": round(sum(hit) / n, 3) if n else None,
           "base_up": round(sum(oc("SPY", c["date"]) > 0 for c in done) / n, 3) if n else None},
  "e17": {"mean": round(st.mean(e17), 5) if n else None, "spy_oc_net_mean": round(st.mean(al), 5) if n else None, "random_pick_mean_p95": round(p95(r17), 5)}}
if n >= N_MIN:
    e = out["e16b"]; out["e16b"]["verdict"] = "BEAT" if e["sharpe"] > e["always_long_sharpe"] and e["sharpe"] > e["random_p95"] and e["hit"] > e["base_up"] else "LOSE"
    f = out["e17"]; out["e17"]["verdict"] = "BEAT" if f["mean"] > f["spy_oc_net_mean"] and f["mean"] > f["random_pick_mean_p95"] and f["mean"] > 0 else "LOSE"
else: out["verdict"] = f"PENDING ({n}/{N_MIN} days)"
print(json.dumps(out, indent=1))
