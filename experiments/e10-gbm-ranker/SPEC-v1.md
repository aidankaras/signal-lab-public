## Survivorship-reduced rebuild (pre-registered 2026-10-20, before first run)

Universe: point-in-time S&P 500 membership (github fja05680/sp500 "Updated" csv, daily
member lists 1996-2026-08) intersected with names yfinance still serves. A name is only
scored/traded on dates it was a member. Prices: yfinance adjusted close/volume.
Known gap (measured, reported): ~188/826 ever-members (mostly acquired/bankrupt/renamed)
have NO yfinance data; those are dropped, so survivorship bias is REDUCED, not removed
(missing names skew to deletions, which flatters the strategy if anything).
Missing exit prices: held at last available price (acquisition-style; bankruptcies lost).
Protocol: same HistGB features/label/walk-forward (refit 63 sessions, 5-day embargo) from
2012-06; rebalance every 5 sessions, equal-weight top decile of members, hold 5 sessions;
cost 5bps fee + 5bps slippage per side on actual name turnover.
Controls: SPY; equal-weight all members; 200 random decile picks per rebalance (same cost model, seed 0).
Gate (all required): weekly IC t > 2 AND net Sharpe & CAGR > SPY AND net Sharpe > random-pick p95 Sharpe.
Else LOSE. One run, no tuning after seeing results.
