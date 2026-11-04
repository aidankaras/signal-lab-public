# e22 report — cross-asset vol-targeted time-series momentum

**Verdict: LOSE.** No variant beats SPY (holdout Sharpe 0.80) or 60/40 (0.67) on the 2015-01 → 2026-11 holdout.

| variant | Sharpe dev (2001–2014) | Sharpe holdout | CAGR holdout | maxDD holdout | t (monthly) | verdict |
|--|--|--|--|--|--|--|
| core_ls_12_1 | 0.60 | -0.07 | -0.7% | -20.4% | -0.31 | LOSE |
| core_btc_ls_12_1 | 0.60 | 0.04 | 0.1% | -16.4% | 0.17 | LOSE |
| core_longonly_12_1 | 0.97 | 0.52 | 3.0% | -8.1% | 2.33 | LOSE |
| core_ls_6_1 | 0.27 | 0.11 | 0.6% | -19.3% | 0.46 | LOSE |

Random-sign control (1000 draws): mean holdout Sharpe -0.28, p95 0.09. Lookahead test passed. Data audit in `results/results.json`.

Takeaway: the classic 12-1 TSMOM edge (dev Sharpe 0.60, t 2.59) vanished after 2014, matching published evidence of post-2009 trend-following decay. Long-only beats the control but not buy-and-hold.

Disclosure: a bug in the lookahead test (not the strategy) was fixed before any result was read.
Caveat (unverified): the BTC variant's daily series includes BTC weekend days, so its annualised Sharpe/t (×√252) is approximate. The three ETF-only variants, including the best (long-only 0.52), are not affected, and no variant would change verdict.
