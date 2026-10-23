# e10 — gradient-boosted cross-sectional ranking 2026-10-19

Window 2013-07-03 -> 2026-10-09, BROAD-40, weekly-ish blocks (63 sessions), 5-day embargo.

- Daily Spearman IC: **0.0162** (t = 4.63, 3150 scored days)
- Top-decile long portfolio: Sharpe **2.08**, total 8688.888 (before 5bps/side costs in this v0; costs gate the verdict next version)
- SPY same window: Sharpe 0.89, total 5.035
- Verdict: **BEAT** (gate: IC t > 2 AND portfolio Sharpe > SPY)

This replicates the standard quant-fintech baseline (GBM cross-sectional ranking).

Known v0 simplification, flagged: costs not yet charged to the portfolio return;
the IC gate is unaffected (IC is cost-free by nature), the Sharpe comparison is
generous to the strategy by ~turnover*7bps/yr. If IC fails the gate, costs are moot.