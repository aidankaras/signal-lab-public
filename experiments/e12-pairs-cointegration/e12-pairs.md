# e12 — pairs trading via cointegration 2026-10-19

Walk-forward years 2016-2026, fit on trailing 3y, top-5 pairs, z=+-2/0.5/4, 10bps/pair round trip.

- Mean annual return: **-0.0208** (Sharpe -0.79)
- SPY mean annual: 0.1565
- Random-pairs control (same rule, random pairs): -0.0161
- Verdict: **LOSE**

Note: the 780-pair scan is heavy multiple testing; the walk-forward control
and the random-pair comparison are the honest referees. A Kalman hedge ratio
is the v1 upgrade only if v0 clears the gate.