from harness.experiment import Experiment, simulate


class E0(Experiment):
    """Ray Fu MA crossover, long/flat per ticker, equal weight across universe."""
    id = "e0_rayfu_ma"
    grid = {"fast": [10, 20, 30], "slow": [50, 100, 200]}
    universe = ["SPY", "QQQ", "AAPL", "MSFT"]

    def run(self, close, params, cost_bps=5.0):
        c = close[self.universe]
        if params["fast"] >= params["slow"]:
            return simulate(c, c * 0, cost_bps)
        sig = (c.rolling(params["fast"]).mean() > c.rolling(params["slow"]).mean()).astype(float)
        return simulate(c, sig / c.shape[1], cost_bps)
