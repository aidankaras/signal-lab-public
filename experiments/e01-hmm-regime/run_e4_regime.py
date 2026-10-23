"""python run_e4_regime.py -- e4 pre-2023 regime check.

The e4 strict verdicts so far were earned in a holdout (2023-05 → 2026-10) that overlaps the
AI bull run. This script truncates the panel at 2023-05-01 so the holdout (last 25%) sits in
2018 → 2023-05 — a different regime (rate shock, 2020 crash, 2022 bear). Same experiment
classes, same 5bps/side costs, same strict verdict machinery, logged to trials.jsonl.
Pre-registered question: does each factor still beat SPY outside the AI-bull window?
"""
import json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.benchmark import spy_returns
from harness.improve import run_experiment
from harness.verdict import control_stats, strict
from harness.strategies.factors import FACTORS

CUTOFF = "2023-05-01"
TR = os.path.join(ROOT, "registry", "trials.jsonl")
close_all = data.fetch(data.BROAD, start="2013-01-01", refresh="--refresh" in sys.argv, name="broad").dropna()
close = close_all[close_all.index < CUTOFF]
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
    lines.append(f"- {exp.id} [{v['strict']}] {res['champion']} | PRE-2023 holdout {ho['window'][0]}→{ho['window'][1]}: "
                 f"CAGR {s['cagr']:.1%} vs SPY {b['cagr']:.1%} vs EW-universe {ctrl['ew_universe']['cagr']:.1%}, "
                 f"Sharpe {s['sharpe']} (SPY {b['sharpe']}, random-pick median {ctrl['median_sharpe']:.2f}), "
                 f"maxDD {s['maxdd']:.1%} | trials {res['trials_logged']}, DSR p={'n/a' if d is None or d != d else round(d,2)} | {v['why']}")
    print(lines[-1], f"({time.time()-t0:.0f}s)")
    out.append(res)
txt = [f"# e4 pre-2023 regime check {time.strftime('%Y-%m-%d')}", "",
       f"Panel truncated at {CUTOFF}; holdout = last 25% (pre-AI-bull regime). Survivor-biased universe still applies.",
       "Strict verdict = beat SPY AND random-pick median Sharpe AND equal-weight universe CAGR.", ""] + lines
open(os.path.join(ROOT, "reports", f"e4-regime-{time.strftime('%Y%m%d')}.md"), "w").write("\n".join(txt) + "\n")
json.dump(out, open(os.path.join(ROOT, "reports", "e4-regime-latest.json"), "w"), indent=1, default=str)
print("\n".join(txt))
