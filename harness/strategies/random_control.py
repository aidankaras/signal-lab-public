import numpy as np
import pandas as pd

from harness.experiment import Experiment, simulate


class RandomControl(Experiment):
    """Random equal-weight k-pick, monthly rebalance. The null any picker must beat."""
    id = "e_control_random"
    grid = {"k": [3], "seed": list(range(20))}

    def run(self, close, params, cost_bps=5.0):
        rng = np.random.default_rng(params["seed"])
        cols = [c for c in close.columns]
        sig = pd.DataFrame(0.0, index=close.index, columns=cols)
        month = close.index.to_period("M")
        starts = [i for i in range(len(close)) if i == 0 or month[i] != month[i - 1]]
        for i, s in enumerate(starts):
            e = starts[i + 1] if i + 1 < len(starts) else len(close)
            pick = rng.choice(cols, size=params["k"], replace=False)
            sig.iloc[s:e, [cols.index(p) for p in pick]] = 1.0 / params["k"]
        return simulate(close, sig, cost_bps)
