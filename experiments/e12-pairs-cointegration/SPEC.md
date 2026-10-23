# e12 — pairs trading via cointegration

Pre-registered 2026-10-19. A strategy class genuinely different from e0-e10:
market-neutral mean reversion between two correlated names rather than directional
prediction. Classical Engle-Granger version first; a Kalman-filter hedge ratio is the
v1 upgrade only if v0 clears the gate.

## Design (in code: run_e12.py)

- Universe: BROAD-40 daily bars, 2012-present.
- Walk-forward one year at a time: pairs selected on the trailing 3 years only,
  traded the next year, rolled. No pair is traded on data containing its trading year.
- Selection: all 780 pairs, OLS hedge ratio, residual ADF gate (t < -3.44, i.e. p<0.01
  equivalent) and AR(1) half-life between 5 and 60 sessions; keep the 5 closest to a
  15-session half-life.
- Trade: spread z-score from the fit window; enter at |z| > 2 (short the spread when
  high, long when low), exit at |z| < 0.5, stop at |z| > 4. Signals act on the next
  bar's change (one-bar delay — no lookahead). Costs: 10bps per pair round trip
  (both legs).
- Controls: SPY over the identical years, and 5 random pairs run through the same
  machinery (the random-pair control matters because scanning 780 pairs for cointegration
  is heavy multiple testing — some will look tradable by chance).

## Gates

- BEAT requires mean annual return > 0 after costs AND above SPY's mean annual return
  over the same walk-forward years. The random-pair control is reported alongside;
  if the real pairs only match random pairs, the "edge" is selection noise.
- Known v0 simplification, flagged: annual-return Sharpe proxy (yearly granularity),
  and the spread P&L is normalized by the fit-window sd (position sizing approximation).
  If v0 clears the gate, v1 charges per-leg costs through the causal simulator and
  replaces the OLS hedge ratio with a Kalman filter.

## Status
Built, running.
