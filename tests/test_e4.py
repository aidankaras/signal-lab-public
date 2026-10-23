"""e4 causality + robustness. Run: python -m tests.test_e4"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from harness import data
from harness.benchmark import spy_returns
from harness.evaluator import evaluate
from harness.strategies.factors import FACTORS

close = data.fetch(data.BROAD, start="2013-01-01", name="broad").dropna()
bench = spy_returns(close)
cut = len(close) - 300
P = {"lookback": 6, "top_n": 8}
for F in FACTORS:
    e = F(); p = dict(P) if F.factor != "reversal" else {"lookback": 2, "top_n": 5}
    full, part = e.run(close, p), e.run(close.iloc[:cut], p)
    d = float(np.abs(full.iloc[:cut - 2].values - part.iloc[:cut - 2].values).max())
    assert d < 1e-12, f"{e.id} lookahead {d}"
    print("causal ok", e.id)
# survivorship stress: drop the ex-post megawinners and re-score on the holdout
winners = ["NVDA", "TSLA", "META", "AMZN", "MSFT", "AAPL", "GOOGL", "LLY", "ORCL"]
c2 = close.drop(columns=winners)
cutf = int(len(c2) * 0.75)
for F in FACTORS:
    e = F(); p = dict(P) if F.factor != "reversal" else {"lookback": 2, "top_n": 5}
    ev = evaluate(e.run(c2, p).iloc[cutf:], bench.iloc[cutf:])
    ew = c2.drop(columns="SPY").pct_change().fillna(0).mean(axis=1).iloc[cutf:]
    print(f"no-winners {e.id}: CAGR {ev['strategy']['cagr']:.1%} Sharpe {ev['strategy']['sharpe']} vs SPY {ev['benchmark_sp500']['cagr']:.1%} | EW {(1+ew).prod()**(252/len(ew))-1:.1%}")
