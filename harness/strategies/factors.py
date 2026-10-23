"""e4 factor suite: long-only top-N cross-sectional factors, monthly rebalance, equal weight.
Universe = today's large caps (survivorship-biased, see data audit) so every factor is ALSO scored
against the equal-weight universe (the honest null), not just SPY.
Factors (all use data <= rebalance day; simulate() shifts execution one day):
  momentum  : total return over `lookback` months, skipping the most recent month (12-1)
  reversal  : NEGATIVE return over last `lookback` weeks (buy recent losers)
  lowvol    : lowest realized vol over `lookback` months
  trend     : absolute momentum — hold top-N by momentum only if its own return > 0, else cash
Value+profitability and Alpha158/meta-labeling are NOT here: they need point-in-time fundamentals,
which free sources don't give without lookahead. Logged as not-testable-free rather than faked."""
import pandas as pd

from harness.experiment import Experiment, simulate


def _month_ends(idx):
    p = idx.to_period("M")
    return [i for i in range(len(idx) - 1) if p[i] != p[i + 1]]


class _Factor(Experiment):
    factor = ""
    grid = {"lookback": [6, 12], "top_n": [5, 8]}

    def score(self, c, i, lb):  # return Series of scores at row i, higher = buy
        raise NotImplementedError

    def run(self, close, params, cost_bps=5.0):
        c = close.drop(columns=["SPY"], errors="ignore") if close.shape[1] > 12 else close
        sig = pd.DataFrame(0.0, index=c.index, columns=c.columns)
        ends = _month_ends(c.index)
        for k, i in enumerate(ends):
            if i < 21 * (params["lookback"] + 1):
                continue
            s = self.score(c, i, params["lookback"]).dropna()
            if len(s) < params["top_n"]:
                continue
            pick = s.nlargest(params["top_n"])
            if self.factor == "trend":
                pick = pick[pick > 0]
            j = ends[k + 1] if k + 1 < len(ends) else len(c) - 1
            sig.iloc[i + 1:j + 1, [c.columns.get_loc(t) for t in pick.index]] = 1.0 / params["top_n"]
        # weights decided at close of month-end row i are applied from i+1; simulate() adds one more
        # day of lag, which is conservative (never lookahead).
        return simulate(c, sig, cost_bps)


class E4Momentum(_Factor):
    id, factor = "e4_momentum", "momentum"

    def score(self, c, i, lb):
        return c.iloc[i - 21] / c.iloc[i - 21 * lb - 21] - 1


class E4Reversal(_Factor):
    id, factor = "e4_reversal", "reversal"
    grid = {"lookback": [1, 2], "top_n": [5, 8]}  # lookback in MONTHS of 21d here

    def score(self, c, i, lb):
        return -(c.iloc[i] / c.iloc[i - 21 * lb] - 1)


class E4LowVol(_Factor):
    id, factor = "e4_lowvol", "lowvol"

    def score(self, c, i, lb):
        return -c.pct_change().iloc[i - 21 * lb:i + 1].std()


class E4Trend(_Factor):
    id, factor = "e4_trend", "trend"

    def score(self, c, i, lb):
        return c.iloc[i] / c.iloc[i - 21 * lb] - 1


FACTORS = [E4Momentum, E4Reversal, E4LowVol, E4Trend]
