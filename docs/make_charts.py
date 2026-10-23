"""Regenerate docs/img/*.png from the committed experiment report JSONs (no network).
usage: python docs/make_charts.py [outdir]"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)


def J(p):
    return json.load(open(os.path.join(ROOT, "experiments", p)))


rows = []  # (label, strategy sharpe, spy sharpe, biased?)
for r in J("e00-ma-baseline/latest.json"):
    h = r["champion_holdout"]
    rows.append((r["experiment"].split("_", 1)[0] + " " + r["experiment"].split("_", 1)[1], h["strategy"]["sharpe"],
                 h["benchmark_sp500"]["sharpe"], False))
for r in J("e04-factor-tilts/e4-latest.json"):
    h = r["champion_holdout"]
    rows.append((r["experiment"].replace("_", " "), h["strategy"]["sharpe"], h["benchmark_sp500"]["sharpe"], True))
v0 = J("e10-gbm-ranker/e10-v0-gbm.json")
rows.append(("e10 v0 (survivor universe)", v0["port_sharpe"], v0["spy_sharpe"], True))
v1 = J("e10-gbm-ranker/e10-v1-survivorship.json")
rows.append(("e10 v1 (point-in-time)", v1["strat_net_sharpe"], v1["spy_sharpe"], False))
e13 = J("e13-cio-framework/e13-cio.json")
rows.append(("e13 CIO framework", e13["sharpe_strategy"], e13["sharpe_spy"], False))
for k, v in J("e14-thirdparty-etf-rules/e14-results.json").items():
    rows.append(("e14 " + k, v["oos"]["sharpe"], v["oos"]["spy_sharpe"], False))

fig, ax = plt.subplots(figsize=(10, 0.38 * len(rows) + 1.5))
ys = range(len(rows))
ax.barh([y + 0.2 for y in ys], [r[1] for r in rows], 0.4, label="strategy (net of costs)",
        color=["#c0392b" if r[3] else "#2c7fb8" for r in rows])
ax.barh([y - 0.2 for y in ys], [r[2] for r in rows], 0.4, label="SPY, same window", color="#999999")
ax.set_yticks(list(ys))
ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("Out-of-sample Sharpe")
ax.set_title("Signal Lab: out-of-sample Sharpe vs SPY (red = survivor-biased universe)")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "oos_sharpe_vs_spy.png"), dpi=130)

# e10: survivorship + cost drag (all from report JSONs)
fig, ax = plt.subplots(figsize=(7, 4))
labels = ["v0 survivor\nuniverse", "v1 point-in-time\ngross", "v1 point-in-time\nnet (10bps)", "SPY"]
vals = [v0["port_sharpe"], v1["strat_gross_sharpe"], v1["strat_net_sharpe"], v1["spy_sharpe"]]
ax.bar(labels, vals, color=["#c0392b", "#7fb3d5", "#2c7fb8", "#999999"])
for i, v in enumerate(vals):
    ax.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=9)
ax.set_ylabel("Sharpe")
ax.set_title("e10: same GBM ranker. Survivorship and costs erase the edge\n"
             f"(v0 total return {v0['port_total']:.0f}x, verdict BEAT -> v1 LOSE)", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "e10_survivorship_costs.png"), dpi=130)
print("wrote", OUT)
