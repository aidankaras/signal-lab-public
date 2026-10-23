# e10-survivorship — GBM ranker on a point-in-time S&P 500 universe

**Verdict: LOSE vs SPY** (net Sharpe 0.54 vs 0.97; CAGR 10.5% vs 15.4%, 2012-06 → 2026-09, 719 weekly rebalances).
Beats the random-pick control (Sharpe 0.54 vs random median 0.33 / p95 0.42, same costs) but not equal-weight members (0.85 / 14.4%). Weekly IC 0.0116, t = 1.98 (gate: >2). Gross (pre-cost) Sharpe 0.80 / CAGR 17.7% — still below SPY Sharpe; costs (63% weekly turnover, 10 bps/side) take ~7 pts CAGR.

The earlier "8689x" e10 v0 result was the survivorship artifact: removing it collapses 87%/yr to a sub-SPY strategy.

Data: fja05680/sp500 daily membership + yfinance. **Coverage gap:** 638/826 ever-members have yfinance data; 68% of true members at 2012 → 99% by 2026. Missing names are mostly acquired/bankrupt (precisely the losers/deletions), so bias is reduced not removed and is still favorable to the strategy; the LOSE verdict is therefore if anything generous. Names vanishing mid-hold exit at last price (bankruptcy losses lost). Pre-registration: SPEC.md. Run: `run_e10_pit.py` (after `fetch_prices.py`). Single run, no tuning.

**Note:** `sp500_membership.json` (~3 MB) is gitignored; regenerate with `python fetch_membership.py` before running `run_e10_v1_pit.py` (results are in `e10-v1-survivorship.{json,md}`).
