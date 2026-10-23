import numpy as np
import pandas as pd

from harness.experiment import Experiment, simulate


class E1(Experiment):
    """Volatility-regime model on SPY. NOTE: hmmlearn not installed in this env (py3.14, no
    compiler), so this uses a Gaussian mixture on [return, 20d vol] as a causal HMM substitute
    (no state-transition smoothing). Refit every 63d on trailing `lookback` days only; each day
    classify using that day's features. Flat when in the highest-volatility cluster, else long."""
    id = "e1_hmm_regime"
    grid = {"states": [2, 3], "lookback": [252, 504, 756]}

    def run(self, close, params, cost_bps=5.0):
        from sklearn.mixture import GaussianMixture
        px = close[["SPY"]]
        r = px["SPY"].pct_change().fillna(0.0)
        vol = r.rolling(20).std().bfill()
        F = np.column_stack([r.values * 10, vol.values * 100])
        n, L, k = len(r), params["lookback"], params["states"]
        pos = np.zeros(n)
        for t0 in range(L, n, 63):
            gm = GaussianMixture(k, random_state=0, n_init=2).fit(F[t0 - L:t0])
            risk_off = int(np.argmax(gm.means_[:, 1]))
            lab = gm.predict(F[t0:min(t0 + 63, n)])
            pos[t0:t0 + len(lab)] = (lab != risk_off).astype(float)
        return simulate(px, pd.DataFrame({"SPY": pos}, index=px.index), cost_bps)
