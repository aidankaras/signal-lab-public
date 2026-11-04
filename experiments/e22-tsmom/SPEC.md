# e22 — cross-asset vol-targeted time-series momentum (follow-up to e14)

Pre-registered before any e22 backtest was run. Replaces the e14 third-party
breakout rules (OOS 2021+ Sharpe 0.89 vs SPY 0.92, LOSE) with the classic
Moskowitz–Ooi–Pedersen (2012) 12-1 TSMOM on a diversified universe.

## Hypothesis
Sign of the past 12-month return (skipping the most recent month) predicts the
next month's sign across asset classes; with each asset scaled to a constant
ex-ante vol, the equal-weight portfolio delivers a higher Sharpe than SPY
buy&hold and than 60/40 on 2015+, net of costs. H0: no better than random
signs with the same sizing and costs.

## Data
- Yahoo Finance daily ADJUSTED close (dividends/splits included), free, via
  yfinance. Universe (core 8): SPY EFA EEM TLT IEF GLD DBC UUP.
  Optional (variant only): BTC-USD. Benchmark helper: AGG (for 60/40).
- Dev period: start of data .. 2014-12-31 (may be inspected/iterated on).
  Holdout: 2015-01-01 .. latest, scored ONCE by the final run.
  Assets enter the portfolio when they have >=13 months of history
  (DBC 2006-02, UUP 2007-03, BTC-USD 2014-09 -> signal from ~2015-10).
- Audit before trusting: per-ticker first/last date, #obs, gaps > 5 business
  days, zero/negative prices, daily |return| > 20% flagged, stale (zero-return
  runs >= 10 days) flagged. Survivorship caveat: universe is ex-post a set of
  large ETFs that exist today; no delisted ETFs. UUP/DBC inception limit the
  dev window. Disclosed in report.

## Rules (exact)
- Month-end t (last trading day of the month): signal_i = sign(P_i[t-1m] /
  P_i[t-12m] - 1), where t-1m and t-12m are the last trading days of the
  calendar months 1 and 12 months earlier (skip-month 12-1). All data <= t.
- Ex-ante vol sigma_i = stdev of last 60 daily returns up to t, * sqrt(252).
- Weight_i = signal_i * min(TARGET/sigma_i, 3.0) / N_t, TARGET = 12% annual,
  N_t = number of assets with valid signal at t (equal-risk average across
  assets). Weights held constant over the next month (applied from t+1 close
  returns, i.e. day t+1 return uses the weight set at t close).
- Costs: 5 bps per side commission + 2 bps slippage = 7 bps x |delta weight|
  at each monthly rebalance; plus short borrow 50 bps/yr on short notional;
  no financing credit/charge on leverage or cash (returns treated as excess
  returns; SPY/60-40 benchmarks scored on the same basis, rf = 0).
- Benchmarks over IDENTICAL window/dates: SPY buy&hold; 60/40 = 60% SPY /
  40% AGG, monthly rebalanced, same 0 rf.

## Variants (n_trials = 4, all declared now)
 V1 `core_ls_12_1` PRIMARY: 8 ETFs, long/short, 12-1.
 V2 `core_btc_ls_12_1`: V1 + BTC-USD.
 V3 `core_longonly_12_1`: V1 but weight = max(signal,0) (flat otherwise).
 V4 `core_ls_6_1`: V1 with 6-1 lookback.
No other variants, no parameter tuning (TARGET, lookback, vol window, cap fixed).

## Metrics
Daily portfolio returns -> Sharpe (mean/sd*sqrt(252)), CAGR, maxDD, vol,
t-stat of mean MONTHLY return (n months). Reported for dev, holdout, per variant
and benchmarks.

## Gates (per variant, holdout 2015+)
 G1: holdout Sharpe > SPY holdout Sharpe AND > 60/40 holdout Sharpe.
 G2: holdout monthly-return t-stat >= 2.5 (Bonferroni: alpha 0.05 / 4 trials,
     two-sided ~ t 2.5) and mean > 0.
 G3: holdout Sharpe > p95 of random-sign control (2000 draws; each month each
     asset gets random sign +-1 with the same vol scaling, N, cost model;
     seeded; same window).
 G4: dev (<=2014) Sharpe > 0.
 BEAT only if all four pass; else LOSE. Verdict written either way.
 If holdout has < 60 months: INSUFFICIENT.

## Kill criteria
- Lookahead test (signals at month m computed from data truncated at m must
  equal those from full data) fails -> abort.
- Data audit finding for any core ticker: > 5% missing business days after
  inception -> drop that ticker, documented before looking at P&L.
- Yahoo data not obtainable -> report blocker, do not substitute.
All 4 trials appended to registry/trials.jsonl.
