# e10 — gradient-boosted cross-sectional ranking 2026-10-19

> **Errata (November 2026).** These v0 numbers are mostly a return-math error, not only
> survivorship. The runner recorded the top decile's *5-day* forward return on *every* day,
> compounded those overlapping returns daily and annualized with sqrt(252), so each day's return
> was counted about five times. The returns were also *abnormal* (stock minus SPY) but were
> compared with SPY's total return, no costs were charged, and the IC t-stat treated overlapping
> daily ICs as independent. A rough correction from the committed numbers (not a re-run):
> Sharpe ~2.08/sqrt(5) = 0.93 and IC t ~4.63/sqrt(5) = 2.07; the 8,689x total corresponds to
> roughly 14.7%/yr of pre-cost abnormal return (ln(8,689.9)/13.27 years/5), against SPY's 14.5%/yr
> total return. The verdict is INVALID; `run_e10_v0.py` now rebalances every 5 sessions, charges
> 5bps/side, holds total returns, and uses a Newey-West t-stat. The November 2026 re-run is in
> `e10-v0-gbm-rerun-2026-11.md`: IC t 2.03, net Sharpe 1.07 vs SPY 0.97, SUSPECT, not promoted.

Window 2013-07-03 -> 2026-10-09, BROAD-40, weekly-ish blocks (63 sessions), 5-day embargo.

- Daily Spearman IC: **0.0162** (t = 4.63, 3150 scored days)
- Top-decile long portfolio: Sharpe **2.08**, total 8688.888 (before 5bps/side costs in this v0; costs gate the verdict next version)
- SPY same window: Sharpe 0.89, total 5.035
- Verdict: **BEAT** (gate: IC t > 2 AND portfolio Sharpe > SPY)

This replicates the standard quant-fintech baseline (GBM cross-sectional ranking).

Known v0 simplification, flagged: costs not yet charged to the portfolio return;
the IC gate is unaffected (IC is cost-free by nature), the Sharpe comparison is
generous to the strategy by ~turnover*7bps/yr. If IC fails the gate, costs are moot.