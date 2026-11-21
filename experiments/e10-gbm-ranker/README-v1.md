# e10-survivorship — GBM ranker on a point-in-time S&P 500 universe

**Verdict: LOSE vs SPY** (net Sharpe 0.54 vs 0.97; CAGR 10.5% vs 15.4%, 2012-06 → 2026-09, 719 weekly rebalances).
Beats the random-pick control (Sharpe 0.54 vs random median 0.33 / p95 0.42, same costs) but not equal-weight members (0.85 / 14.4%). Weekly IC 0.0116, t = 1.98 (gate: >2). Gross (pre-cost) Sharpe 0.80 / CAGR 17.7% — still below SPY Sharpe; costs (63% weekly turnover, 10 bps/side) take ~7 pts CAGR.

The earlier "8689x" e10 v0 result was mostly a return-math error (overlapping 5-day returns compounded daily, pre-cost, abnormal returns compared with SPY's total return) on top of the survivor-biased universe; see the errata in `e10-v0-gbm.md`. v1 rebalances every 5 sessions and does not have that error, so the v0 -> v1 gap is not a clean measure of survivorship alone.

Data: fja05680/sp500 point-in-time membership (change-date list) + yfinance. **Coverage gap:** 638/826 ever-members have yfinance data; 68% of true members at 2012 → 99% by 2026. Missing names are mostly acquired/bankrupt (precisely the losers/deletions), so bias is reduced not removed and is still favorable to the strategy; the LOSE verdict is therefore if anything generous. Names vanishing mid-hold exit at last price (bankruptcy losses lost). Pre-registration: `SPEC-v1.md`. Run: `python fetch_membership.py`, then `python fetch_prices_v1.py`, then `python run_e10_v1_pit.py`. Single run, no tuning.

**Note:** `sp500_membership.json` (~3.5 MB) is gitignored; regenerate with `python fetch_membership.py` (downloads the fja05680/sp500 GitHub CSV; the maintainer updates it, so pin a commit for an exact rebuild) before running `run_e10_v1_pit.py` (results are in `e10-v1-survivorship.{json,md}`).
