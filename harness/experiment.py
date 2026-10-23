"""Experiment interface + shared simulation helper (costs applied via turnover)."""
import pandas as pd


def simulate(close: pd.DataFrame, signal: pd.DataFrame, cost_bps: float = 5.0) -> pd.Series:
    """signal = target weights decided at close t (uses data <= t). Executed next day (shift 1).
    Net return = sum(w*ret) - cost_bps/1e4 * turnover (per side). Equal capital across columns
    is the caller's job (weights should sum <= 1)."""
    w = signal.shift(1).fillna(0.0)
    ret = close.pct_change().fillna(0.0)
    gross = (w * ret).sum(axis=1)
    turnover = w.diff().abs().sum(axis=1).fillna(0.0)
    return gross - turnover * cost_bps / 1e4


class Experiment:
    id = "base"
    grid: dict = {}

    def run(self, close: pd.DataFrame, params: dict, cost_bps: float = 5.0) -> pd.Series:
        """Return daily NET returns, strictly causal."""
        raise NotImplementedError
