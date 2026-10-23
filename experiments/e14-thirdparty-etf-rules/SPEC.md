# e14 — third-party multi-strategy ETF/crypto bot (pre-registration, v0)

Source: a third-party paper-trading bot shared on social media, summarized 2026-10-20.
Claim relayed: "$200 today on a $1,500 account" — paper (fake money), day 1 of forward test,
0 round trips, no strategy has passed its own gate. That claim is not evidence; this tests the RULES.

## Universe / data
SPY QQQ IWM GLD TLT BTC-USD ETH-USD, daily adjusted closes (yfinance, free). Equity trading calendar
(crypto sampled on equity days). ETFs, so no single-stock survivorship bias. ETH starts 2017-11.

## Rules (v0 = the bot's default parameters; exact parameters unknown -> v1 re-run when supplied)
1. trend: long if close>SMA200 and SMA50>SMA200.
2. voltrend: trend x min(1, 10% / 20d realized vol).
3. breakout: enter close > prior 20d high, exit close < prior 10d low.
4. dip: in uptrend (close>SMA200) after 2 down closes; exit first up close or 5 days.
5. mom12: month-end rebalance, hold if trailing 252d return > 0.
Each asset sleeve = 1/7 of capital, long/flat only. Signal at close t, fill t+1 (harness simulate).
Costs: 5bps/side + 5bps slippage = 10bps/side.

## Split
In-sample 2015-01-01..2020-12-31; out-of-sample 2021-01-01..present. No parameter tuned on OOS.

## Gate (the bot's own, all required, judged per strategy)
- >=100 trades, or >=3 years with >=30 trades (OOS)
- MaxDD < 20% IS and OOS
- Profit factor (per-trade) >= 1.2 OOS
- Sharpe > equal-weight buy-and-hold of same 7 assets (OOS)
- Sharpe > 95th pct of 200 random bots (same per-asset entry/exit hazard = same exposure & trade count)
- Not "too good": OOS Sharpe < 3
Plus lab contract: OOS vs SPY same window -> BEAT/LOSE published.

## Not in v0 (needs the bot's specifics)
Exact lookbacks/vol target, stop rule, cross-strategy sizing, 10% DD halt mechanics, random-bot design,
the 33 logged variants. Forward paper (Alpaca, 60d) only if a rule passes — needs owner approval for account.
