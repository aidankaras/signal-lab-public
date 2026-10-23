# e19 report
Zero-shot Kronos-small and TimesFM-2.5-200m, 14 ETFs, 10 bps/side, decisions 2024-07-01..2026-10-21. 12 trials (Bonferroni alpha 0.0042). **0 BEAT / 12 LOSE.**

| model | h | strat | Sharpe | SPY B&H | mom20 | rand p95 | hit/base (p) | gates G1-G4 | verdict |
|--|--|--|--|--|--|--|--|--|--|
| kronos | 1 | A | -0.35 | 1.046 | 0.711 | 0.393 | 0.4879/0.5569 (0.99963) | nnnn | LOSE |
| kronos | 1 | B1 | -0.866 | 1.046 | -0.239 | -0.732 | 0.5534/0.5413 (0.29228) | nnnn | LOSE |
| kronos | 1 | B3 | -0.73 | 1.046 | 0.835 | -1.016 | 0.5402/0.5413 (0.54404) | nYnn | LOSE |
| kronos | 5 | A | 0.206 | 1.046 | 0.875 | 1.269 | 0.4138/0.6121 (0.99999) | nnnn | LOSE |
| kronos | 5 | B1 | 0.836 | 1.046 | 0.284 | 1.225 | 0.569/0.5647 (0.50162) | nnYn | LOSE |
| kronos | 5 | B3 | 0.971 | 1.046 | 1.127 | 1.127 | 0.5603/0.5647 (0.58645) | nnnn | LOSE |
| timesfm | 1 | A | 0.264 | 1.046 | 0.711 | 0.406 | 0.5034/0.5569 (0.99568) | nnnn | LOSE |
| timesfm | 1 | B1 | -0.482 | 1.046 | -0.239 | -0.805 | 0.5534/0.5413 (0.29228) | nYnn | LOSE |
| timesfm | 1 | B3 | -0.196 | 1.046 | 0.835 | -0.998 | 0.554/0.5413 (0.14807) | nYnn | LOSE |
| timesfm | 5 | A | 0.842 | 1.046 | 0.875 | 1.293 | 0.5517/0.6121 (0.92262) | nnnn | LOSE |
| timesfm | 5 | B1 | 0.708 | 1.046 | 0.284 | 1.129 | 0.5517/0.5647 (0.6472) | nnYn | LOSE |
| timesfm | 5 | B3 | 0.958 | 1.046 | 1.127 | 1.149 | 0.5805/0.5647 (0.295) | nnnn | LOSE |

No model had hit rate above base rate with p<0.05; rank IC ~0 (Kronos ±0.01, TimesFM 0.01-0.04). Long/flat A strategies had low exposure/hit rates below the (bullish) base rate. Deviations: sharded Kronos with per-date seeds. Sharpe annualised sqrt(252) on daily net series.
