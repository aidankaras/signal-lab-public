# e8 — deep learning price model

Pre-registered 2026-10-18. Question: does a sequence model extract return predictability
that linear factor/feature models (e4, e6) did not, once overfitting is priced in?

## Design

- Model: 2-layer LSTM (hidden 32) on per-ticker sequences of daily returns + volume +
  the e4 factor scores; ~20k parameters — small on purpose, matching the data budget.
- Target: next-5-session abnormal return vs SPY (same labels as e6).
- Data: BROAD-40 daily bars, 2010-present (survivorship caveat carried from the data audit).
- Protocol: expanding walk-forward, refit yearly, 10-day embargo; early stopping on the
  last year of the fit window only.
- Metric: daily Spearman IC + a long-short decile spread scored through the causal
  simulator (5bps/side + slippage).

## Gates

- Same as e4/e6: score vs SPY and the random-pick control on identical windows; DSR
  accounting across all e8 trials (the registry counts retries).
- Kill: 3 losing generations (same rule as e4). An IC near zero with a good in-sample
  fit is published as the overfitting demonstration, not buried.

## Why the small net

The data budget (40 tickers, ~4000 daily observations) supports a model that can only
learn coarse structure. A transformer or anything larger is not pre-registered — it
would fit noise and the honest result would be unfalsifiable from the fit itself.

## Status
Not run. Needs torch (sklearn-only today); one `pip install` away, gated
on e7 completion to keep the trials registry honest about how many ideas are burning.
