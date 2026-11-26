# e10 — gradient-boosted cross-sectional ranking 2026-11-25

Window 2012-07-03 -> 2026-11-18, BROAD-40, weekly-ish blocks (63 sessions), 5-day embargo.

- Daily Spearman IC: **0.01** (Newey-West t = 2.03, 3465 scored days)
- Top-decile long portfolio, rebalanced every 5 sessions, 5bps/side: net Sharpe **1.07** (gross 1.2), net total 24.431
- Gross Sharpe of the abnormal (vs SPY) return: 0.89
- SPY on the same rebalance dates: Sharpe 0.97, total 5.499
- Verdict: **BEAT** (gate: IC t > 2 AND portfolio Sharpe > SPY)

Universe caveat: BROAD-40 is today's large caps (survivors); see e10 v1 for point-in-time membership.

## Reading this result (added with the re-run, November 2026)

This is the corrected `run_e10_v0.py` (5-session rebalances, 5 bps/side, total returns, Newey-West
t), run once on yfinance data downloaded 2026-11-25, with the SPEC-v0 parameters unchanged. It
replaces the INVALID 2026-10-19 numbers in `e10-v0-gbm.md` (Sharpe 2.08, 8,689x), which stay in the
repo for the record.

- **Label: SUSPECT, not promoted.** The run passes its pre-registered gate, but only just
  (IC t 2.03 against a threshold of 2), and on BROAD-40, a list of today's large caps chosen with
  hindsight. The lab flags any BROAD-40 stock-selection pass as SUSPECT. The same model on
  point-in-time S&P 500 membership with 10 bps/side (e10 v1) is net Sharpe 0.54 vs SPY 0.97, LOSE.
- **Fragile.** The trial registry has two rows for this re-run. The first attempt's download of
  META failed (a yfinance cache error), so it ran on 39 names: IC t 2.04, net Sharpe 0.89 vs SPY
  0.97, LOSE. After re-downloading the full panel the result above (40 names) was produced. Both rows
  are kept, since the registry is append-only. One stock moving the verdict is itself a reason not
  to trust it.
- **Survivorship check.** The rough correction in the errata (Sharpe about 0.93 pre-cost on abnormal
  returns) was close: the abnormal-return gross Sharpe here is 0.89.
