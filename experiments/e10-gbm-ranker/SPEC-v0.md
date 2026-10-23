# e10 — gradient-boosted cross-sectional ranking

Pre-registered 2026-10-18. The algorithm class most quant fintech firms actually deploy
at this data scale: gradient-boosted trees ranking a cross-section of liquid names by
predicted forward return, long the top decile. Implemented with sklearn's
HistGradientBoostingClassifier (same family as LightGBM/XGBoost) on free daily data.

## Design (in code: run_e10_v0.py)

- Features, all point-in-time: momentum 21/63/126d, 5d reversal, 21d volatility,
  volume z-score, distance from the 63d high, market 21d return as a regime feature.
- Label: next-5-session abnormal return vs SPY (same labels as e6/e8).
- Protocol: expanding walk-forward, refit every 63 sessions, 5-session embargo,
  daily Spearman IC + top-decile long portfolio.
- Gate: BEAT requires IC t > 2 AND portfolio Sharpe > SPY's over the identical window.

## Known v0 simplification (flagged in the report)

Portfolio return is pre-cost; the IC gate is unaffected. If IC passes the gate, the
next generation charges 5bps/side through the causal simulator before any promotion.

## Fintech-ML algorithm map (what firms use, what the lab can replicate on free data)

| Algorithm | Used for | Lab status |
|---|---|---|
| Gradient-boosted trees (XGBoost/LightGBM/HistGB) | cross-sectional ranking, this experiment | e10 (built) |
| Logistic / linear factor models | baseline arms | e4, e6 (built; both LOSE) |
| LSTM / sequence models | price prediction | e8 (pre-registered) |
| Meta-labeling (López de Prado) | sizing ML on top of a primary signal | candidate e11 — needs a primary signal that passes first |
| HMM / regime models | regime switching | e1 (built) |
| Kalman filters / cointegration | pairs & stat-arb | candidate e12 — feasible on daily data, CPU only |
| Online portfolio selection | allocation | candidate e13 |
| Reinforcement learning (cost-aware) | execution | out of scope: needs order-book data the free tier doesn't provide |
| Fine-tuned small LLM | text/feature analyst | e9 (pre-registered, GPU-gated) |

## Status
Built. Expected outcome given every daily-frequency lane so far: LOSE —
the point is replicating the industry-standard method honestly, not assuming it prints.

## v0 result (2026-10-19) — BEAT, SUSPECT, DO NOT PROMOTE

IC 0.0162 (t=4.63, 3150 scored days), top-decile portfolio Sharpe 2.08 vs SPY 0.89,
total 8689x over 2013-2026. The gate passed, but the result fails the smell test at
~87%/yr compounded with zero costs on daily rebalancing, and the universe is fatally
survivorship-biased: BROAD-40 is *today's* 40 mega-caps, so momentum features partially
"predict" the known winners of 2013-2026. A fixed current-members list cannot test
cross-sectional momentum honestly.

To call this real we need: (1) a point-in-time universe (index membership as of each
date, with delisted names — not available on free data; a proxy is to randomize
universe entry/exit, which weakens but does not remove the bias), and (2) turnover
costs through the causal simulator. Until both, e10's BEAT is recorded as an artifact
demonstration — it shows exactly how a naive GBM replication "prints" in a backtest,
which is itself a finding worth having on the record.


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
