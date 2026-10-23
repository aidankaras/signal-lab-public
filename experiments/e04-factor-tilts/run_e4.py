"""python run_e4.py [--refresh] -- e4 factor suite on the broad universe, strict verdicts, report."""
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.benchmark import spy_returns
from harness.improve import run_experiment
from harness.verdict import control_stats, strict
from harness.strategies.factors import FACTORS

TR = os.path.join(ROOT, "registry", "trials.jsonl")
close = data.fetch(data.BROAD, start="2013-01-01", refresh="--refresh" in sys.argv, name="broad").dropna()
bench = spy_returns(close)
univ = close.drop(columns=["SPY"])
cut = int(len(close) * 0.75)
out, lines = [], []
for F in FACTORS:
    exp = F(); t0 = time.time()
    res = run_experiment(exp, close, bench, TR)
    ctrl = control_stats(univ, max(res["champion"]["top_n"], 1), bench, cut)
    v = strict(res["champion_holdout"], ctrl)
    res["control"], res["strict"] = ctrl, v
    ho = res["champion_holdout"]
    if "error" in ho:
        lines.append(f"- {exp.id}: n/a ({ho['error']})"); out.append(res); continue
    s, b = ho["strategy"], ho["benchmark_sp500"]
    d = res["deflated_sharpe_prob"]
    lines.append(f"- {exp.id} [{v['strict']}] {res['champion']} | holdout {ho['window'][0]}→{ho['window'][1]}: "
                 f"CAGR {s['cagr']:.1%} vs SPY {b['cagr']:.1%} vs EW-universe {ctrl['ew_universe']['cagr']:.1%}, "
                 f"Sharpe {s['sharpe']} (SPY {b['sharpe']}, random-pick median {ctrl['median_sharpe']:.2f}), "
                 f"maxDD {s['maxdd']:.1%} | trials {res['trials_logged']}, DSR p={'n/a' if d is None or d != d else round(d,2)} | {v['why']}")
    print(lines[-1], f"({time.time()-t0:.0f}s)")
    out.append(res)
txt = ["# e4 factor suite " + time.strftime("%Y-%m-%d"), "",
       f"Universe: {univ.shape[1]} large caps, {close.index[0].date()}→{close.index[-1].date()} (survivor-biased). "
       "Strict verdict = beat SPY AND random-pick median Sharpe AND equal-weight universe CAGR. "
       "Value+profitability and Alpha158/meta-label: not testable with free point-in-time data; not run.", ""] + lines
open(os.path.join(ROOT, "reports", f"e4-{time.strftime('%Y%m%d')}.md"), "w").write("\n".join(txt) + "\n")
json.dump(out, open(os.path.join(ROOT, "reports", "e4-latest.json"), "w"), indent=1, default=str)
