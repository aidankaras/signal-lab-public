"""Smoke + causality tests. Run: python -m tests.smoke (needs network + venv deps)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from harness import data
from harness.benchmark import spy_returns
from harness.evaluator import evaluate
from harness.strategies.hmm_regime import E1
from harness.strategies.ma_baseline import E0
from harness.strategies.random_control import RandomControl

close = data.fetch().dropna()
cut = len(close) - 300
for exp, p in [(E0(), {"fast": 20, "slow": 50}), (E1(), {"states": 2, "lookback": 252}),
               (RandomControl(), {"k": 3, "seed": 1})]:
    full = exp.run(close, p)
    part = exp.run(close.iloc[:cut], p)
    diff = float(np.abs(full.iloc[:cut - 1].values - part.iloc[:cut - 1].values).max())
    assert diff < 1e-12, f"{exp.id} uses future data (diff {diff})"      # causality
    assert not full.isna().any(), f"{exp.id} NaNs"
    ev = evaluate(full, spy_returns(close))
    assert ev["verdict"] in ("BEAT", "LOSE")
    print("ok", exp.id, "causal; verdict", ev["verdict"])
