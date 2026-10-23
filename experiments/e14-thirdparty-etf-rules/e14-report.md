# e14 — third-party ETF/crypto rules, v0 (2026-10-20)

IS 2015-2020, OOS 2021-present, 7 assets 1/7 sleeves, 10bps/side. Gate = the bot's own + 200 random bots (95th pct).

| rule | OOS CAGR | OOS Sharpe | MaxDD IS/OOS | trades | PF | EW B&H Sharpe | SPY Sharpe | rand p95 | gate | vs SPY |
|---|---|---|---|---|---|---|---|---|---|---|
| trend | 0.1193 | 0.803 | 0.1523/0.2275 | 113 | 2.98 | 0.809 | 0.916 | 1.066 | FAIL: maxdd,beats_bh,beats_random95 | LOSE |
| voltrend | 0.0344 | 0.7217 | 0.0493/0.0914 | 113 | 2.98 | 0.809 | 0.916 | 1.014 | FAIL: beats_bh,beats_random95 | LOSE |
| breakout | 0.1084 | 0.8938 | 0.1145/0.1687 | 243 | 1.85 | 0.809 | 0.916 | 1.009 | FAIL: beats_random95 | LOSE |
| dip | 0.0473 | 0.695 | 0.1205/0.0812 | 751 | 1.39 | 0.809 | 0.916 | 0.292 | FAIL: beats_bh | LOSE |
| mom12 | 0.1563 | 0.8998 | 0.2652/0.267 | 26 | 7.92 | 0.809 | 0.916 | 1.072 | FAIL: trades,maxdd,beats_random95 | LOSE |

v0 uses the bot's default parameters; v1 re-runs with the exact parameters when the author shares them.