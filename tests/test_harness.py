"""Unit tests for the harness on synthetic data (no network, no cache)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from harness.evaluator import evaluate, log_trial, metrics, read_trials  # noqa: E402
from harness.experiment import simulate  # noqa: E402
from harness.verdict import strict  # noqa: E402


def _close(n=10, start=100.0, step=0.01):
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({"A": start * (1 + step) ** np.arange(n)}, index=idx)


def test_fills_are_next_bar_no_lookahead():
    close = _close()
    sig = pd.DataFrame(0.0, index=close.index, columns=["A"])
    sig.iloc[3, 0] = 1.0  # decided at close of day 3
    r = simulate(close, sig, cost_bps=0.0)
    assert r.iloc[:4].abs().sum() == 0  # nothing earned on or before decision day
    assert math.isclose(r.iloc[4], 0.01, rel_tol=1e-9)  # earns day-4 return


def test_future_signal_change_does_not_alter_past_returns():
    close = _close(30)
    rng = np.random.default_rng(0)
    sig = pd.DataFrame(rng.integers(0, 2, (30, 1)).astype(float), index=close.index, columns=["A"])
    full = simulate(close, sig)
    sig2 = sig.copy()
    sig2.iloc[20:] = 1 - sig2.iloc[20:]
    alt = simulate(close, sig2)
    assert np.allclose(full.iloc[:21], alt.iloc[:21])


def test_costs_charged_on_turnover():
    close = _close(6, step=0.0)  # flat prices -> gross return 0
    sig = pd.DataFrame(0.0, index=close.index, columns=["A"])
    sig.iloc[1:3, 0] = 1.0  # decided t=1,2 -> held t=2,3; exit trade lands t=4
    r = simulate(close, sig, cost_bps=10.0)
    assert math.isclose(r.iloc[2], -10 / 1e4)
    assert math.isclose(r.iloc[4], -10 / 1e4)
    assert math.isclose(r.sum(), -20 / 1e4)
    assert simulate(close, sig, cost_bps=0.0).sum() == 0


def test_sharpe_and_maxdd_known_values():
    x = pd.Series([0.01, -0.01] * 50)
    m = metrics(x)
    exp_sr = x.mean() / x.std(ddof=1) * math.sqrt(252)
    assert math.isclose(m["sharpe"], round(exp_sr, 4), abs_tol=1e-4)
    y = pd.Series([0.1] * 20 + [-0.5] + [0.0] * 20)
    assert math.isclose(metrics(y)["maxdd"], 0.5, abs_tol=1e-4)
    assert metrics(pd.Series([0.01] * 5)).get("error") == "too short"


def test_evaluate_beat_and_lose():
    idx = pd.bdate_range("2020-01-01", periods=100)
    bench = pd.Series(0.0005, index=idx)
    assert evaluate(pd.Series(0.001, index=idx), bench)["verdict"] == "BEAT"
    assert evaluate(pd.Series(0.0, index=idx), bench)["verdict"] == "LOSE"


def _ev(beat, sharpe, cagr):
    return {"beat_sp500": beat, "strategy": {"sharpe": sharpe, "cagr": cagr}}


CTRL = {"median_sharpe": 0.5, "ew_universe": {"cagr": 0.10}}


def test_strict_verdict_gates():
    assert strict(_ev(True, 0.9, 0.15), CTRL)["strict"] == "PASS"
    r = strict(_ev(False, 0.9, 0.15), CTRL)
    assert r["strict"] == "LOSE" and "trails SPY" in r["why"]
    assert "random-pick" in strict(_ev(True, 0.4, 0.15), CTRL)["why"]
    assert "equal-weight" in strict(_ev(True, 0.9, 0.08), CTRL)["why"]
    assert strict({"error": "too short"}, CTRL)["strict"] == "n/a"


def test_trials_are_append_only(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    log_trial(p, {"experiment": "x", "sharpe": 1.0})
    first = open(p).read()
    log_trial(p, {"experiment": "y", "sharpe": 2.0})
    second = open(p).read()
    assert second.startswith(first)  # earlier records untouched
    assert len(read_trials(p)) == 2
    assert [t["experiment"] for t in read_trials(p, "x")] == ["x"]
    assert read_trials(str(tmp_path / "missing.jsonl")) == []
