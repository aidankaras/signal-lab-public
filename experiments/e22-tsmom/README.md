# e22 — cross-asset vol-targeted time-series momentum

Classic 12-1 TSMOM (Moskowitz, Ooi, Pedersen 2012) on 8 liquid ETFs (SPY EFA EEM TLT IEF GLD DBC UUP),
each scaled to 12% ex-ante vol, monthly rebalance, 7 bps/side plus short borrow.
Dev period to 2014, holdout 2015+ scored once; 4 pre-registered variants, random-sign control.

**Verdict: LOSE** — best holdout Sharpe 0.52 (long-only variant) vs SPY 0.80 and 60/40 0.67.
The long/short variants are ~0. See [`REPORT.md`](REPORT.md); pre-registration in [`SPEC.md`](SPEC.md).

Run: `python experiments/e22-tsmom/run_e22.py data out` (downloads prices via yfinance; writes `out/`).
Committed output: `results/results.json`.
