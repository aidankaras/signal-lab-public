# e16a — daily SPY direction, trained models (2026-10-20)

OOS 2010-01-04..2026-10-20 (4225 days), base rate up 0.5425. 20 bps round trip. Verdict: **LOSE**

| strategy | net Sharpe | CAGR | maxDD | exposure | acc | AUC | gate |
|---|---|---|---|---|---|---|---|
| V1 logit p>0.5 | -3.5067 | -0.3422 | 0.9991 | 0.923 | 0.5399 | 0.4948 | FAIL |
| V2 logit p>0.55 | -1.5683 | -0.1122 | 0.8643 | 0.273 | 0.4847 | 0.4948 | FAIL |
| V3 hgb p>0.5 | -2.9277 | -0.2697 | 0.995 | 0.697 | 0.5245 | 0.5199 | FAIL |
| V4 hgb p>0.55 | -1.7215 | -0.1367 | 0.9166 | 0.392 | 0.5181 | 0.5199 | FAIL |
| always long open->close | -3.4855 | -0.3667 | 0.9995 | | | | |
| overnight-only (net) | -3.8116 | -0.3428 | 0.9991 | | | | |
| SPY B&H close->close | 0.8646 | 0.1419 | 0.3372 | | | | |
| overnight-only gross | 0.8352 | 0.0883 | 0.2941 | | | | |

Random coin-flip (500 sims) net Sharpe median -2.442, p95 -2.147.

## TP/SL overlays (daily OHLC, stop-first)

| overlay | Sharpe | CAGR | maxDD |
|---|---|---|---|
| always_long_TP1_SL1 | -5.0138 | -0.3958 | 0.9998 |
| always_long_TP0.5_SL0.5 | -9.4069 | -0.4733 | 1.0 |
| V1_TP1_SL1 | -4.9089 | -0.3702 | 0.9996 |
| V1_TP0.5_SL0.5 | -8.8134 | -0.4399 | 0.9999 |
| V3_TP1_SL1 | -4.2306 | -0.2978 | 0.9974 |
| V3_TP0.5_SL0.5 | -7.2429 | -0.3507 | 0.9993 |

**Cost sensitivity (added November 2026).** The 20 bps round trip above is the pre-registered,
deliberately conservative assumption; SPY's quoted spread is well under 1 bp and commissions are
near zero, so it overstates costs for SPY. Net Sharpe at lower costs, rescaled linearly from the
committed gross (0 bps) and net (20 bps) Sharpe. This is exact for always-long (traded every day)
and a close approximation for the variants (it assumes the cost does not change the return
volatility):

| strategy | gross | 1 bp | 2 bps | 5 bps | 10 bps | 20 bps |
|---|---|---|---|---|---|---|
| always long open->close | 0.43 | 0.24 | 0.04 | -0.55 | -1.53 | -3.49 |
| V1 logit p>0.5 | 0.46 | 0.26 | 0.06 | -0.53 | -1.52 | -3.51 |
| V2 logit p>0.55 | 0.29 | 0.20 | 0.10 | -0.17 | -0.64 | -1.57 |
| V3 hgb p>0.5 | 0.41 | 0.24 | 0.07 | -0.43 | -1.26 | -2.93 |
| V4 hgb p>0.55 | 0.65 | 0.54 | 0.42 | 0.06 | -0.53 | -1.72 |

Even at 1 bp no variant reaches SPY buy-and-hold (0.86), and no model passes the AUC > 0.52 gate,
so the LOSE verdict does not depend on the cost assumption. The -1.6 to -3.5 range quoted
elsewhere is a product of the 20 bps assumption. Exact figures: `E16_RT_BPS=2 python run_e16.py`.
