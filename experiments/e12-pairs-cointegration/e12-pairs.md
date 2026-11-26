# e12 — pairs trading via cointegration 2026-10-19

> **INVALID (errata, November 2026).** The P&L loop updated the position from today's z-score
> *before* booking today's spread change, so every entry booked the move that triggered it as a
> loss and every exit dropped the reverting move: a perfect z = +3 -> 0 reversion scored about -6%.
> Cointegrated (mean-reverting) pairs lose by construction under that bug, so "real pairs
> underperform random pairs" is not a finding. The P&L was also divided by the spread sd twice,
> the selection used ADF instead of Engle-Granger critical values, the random pairs used a hedge
> ratio of 1, and names listed after 2012 were dropped from every year. `run_e12.py` is
> corrected; the November 2026 re-run (`e12-pairs-rerun-2026-11.md`) is LOSE: mean annual -2.9%
> vs SPY +15.0%, random pairs -3.8%.

Walk-forward years 2016-2026, fit on trailing 3y, top-5 pairs, z=+-2/0.5/4, 10bps/pair round trip.

- Mean annual return: **-0.0208** (Sharpe -0.79)
- SPY mean annual: 0.1565
- Random-pairs control (same rule, random pairs): -0.0161
- Verdict: **LOSE**

Note: the 780-pair scan is heavy multiple testing; the walk-forward control
and the random-pair comparison are the honest referees. A Kalman hedge ratio
is the v1 upgrade only if v0 clears the gate.