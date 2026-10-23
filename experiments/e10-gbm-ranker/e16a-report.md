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