# e14 — third-party ETF/crypto rules, v1 (shared params) (2026-10-20)

IS 2015-2020, OOS 2021-present, 7 assets 1/7 sleeves, 10bps/side. Gate = the bot's own + 200 random bots (95th pct).

| rule | OOS CAGR | OOS Sharpe | MaxDD IS/OOS | trades | PF | EW B&H Sharpe | SPY Sharpe | rand p95 | gate | vs SPY |
|---|---|---|---|---|---|---|---|---|---|---|
| trend | 0.1193 | 0.803 | 0.1523/0.2275 | 113 | 2.98 | 0.809 | 0.916 | 1.066 | FAIL: maxdd,beats_bh,beats_random95 | LOSE |
| voltrend | 0.0493 | 0.7512 | 0.0581/0.125 | 113 | 2.98 | 0.809 | 0.916 | 1.035 | FAIL: beats_bh,beats_random95 | LOSE |
| breakout | 0.1083 | 0.9086 | 0.1142/0.1634 | 261 | 1.86 | 0.809 | 0.916 | 0.974 | FAIL: beats_random95 | LOSE |
| dip | 0.0188 | 0.7343 | 0.0634/0.029 | 216 | 1.75 | 0.809 | 0.916 | 0.425 | FAIL: beats_bh | LOSE |
| mom12 | 0.1614 | 0.9223 | 0.2665/0.2402 | 24 | 8.65 | 0.809 | 0.916 | 1.073 | FAIL: trades,maxdd,beats_random95 | LOSE |

v0 uses the bot's default parameters; v1 re-runs with the exact parameters when the author shares them.