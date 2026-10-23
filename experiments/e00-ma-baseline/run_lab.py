"""python run_lab.py  -- runs audit, e0, e1, random control; writes reports/ and appends trials."""
import json, os, sys, time
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data, report
from harness.benchmark import spy_returns
from harness.evaluator import metrics, evaluate
from harness.improve import run_experiment
from harness.strategies.ma_baseline import E0
from harness.strategies.hmm_regime import E1
from harness.strategies.random_control import RandomControl

TR = os.path.join(ROOT, "registry", "trials.jsonl")
close = data.fetch(refresh="--refresh" in sys.argv).dropna()
bench = spy_returns(close)
au = data.audit(close)
json.dump(au, open(os.path.join(ROOT, "reports", "data-audit.json"), "w"), indent=1)
print("audit:", au["start"], au["end"], au["rows"], "rows; moves>20%:", {t: v["n_moves_gt_20pct"] for t, v in au["tickers"].items()})
results = []
for exp in (E0(), E1()):
    t0 = time.time()
    res = run_experiment(exp, close, bench, TR)
    results.append(res)
    print(report.line(res), f"({time.time()-t0:.0f}s)")
# random control on holdout (no selection, so no train split needed)
cut = int(len(close) * 0.75)
rc = RandomControl(); sh, beats, cg = [], 0, []
for p in [{"k": 3, "seed": s} for s in range(20)]:
    ev = evaluate(rc.run(close, p).iloc[cut:], bench.iloc[cut:])
    sh.append(ev["strategy"]["sharpe"]); cg.append(ev["strategy"]["cagr"]); beats += ev["beat_sp500"]
ctrl = (f"median CAGR {np.median(cg):.1%} (range {min(cg):.1%}..{max(cg):.1%}), median Sharpe {np.median(sh):.2f}, "
        f"{beats}/20 seeds beat SPY")
print("control:", ctrl)
txt = report.write(results, ctrl, os.path.join(ROOT, "reports", f"report-{time.strftime('%Y%m%d')}.md"))
json.dump(results, open(os.path.join(ROOT, "reports", "latest.json"), "w"), indent=1, default=str)
