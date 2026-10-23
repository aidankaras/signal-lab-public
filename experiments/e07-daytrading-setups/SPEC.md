# e7 — claimed day-trading setups, tested as stated

Pre-registered 2026-10-18. Sources of the claims: retail day-trading literature and
"AI trading bot" posts (ORB, VWAP reclaim, mean reversion, gap-and-go). External
baseline for sanity: Nof1's Alpha Arena 2026 — eight frontier LLMs, real money, identical
instructions: ~1/3 of capital lost, profitable in 6 of 32 runs. Claims of 87%/month are
survivorship-posted; the lab treats them as hypotheses, not evidence.

## Protocols (each scored by the standard machinery)

**e7a — Opening-range breakout (15-min ORB).** Long at a close above the first-15-minute
high (short on the low), stop at the opposite side, target 2R, VWAP-side filter as the
claimed variant. Intraday 5-min bars via yfinance (60-day rolling window per pull;
window is short — flagged). Costs 5bps/side + 2bps slippage on intraday fills.

**e7b — VWAP reclaim.** Long when price reclaims VWAP after a pullback on relative volume
> 1.3 (short mirrored). Same bar source and costs.

**e7c — VWAP-extreme mean reversion.** Fade extensions > 2x 20-bar ATR from VWAP on
low-VIX days. Same bar source and costs.

**e7d — gap-and-go.** Long gaps > 2% on 3x relative volume at the open, exit at close.
Daily bars — long history available.

## Gates (all of them, no exceptions)

- Walk-forward, refit/parameter-free (rules as claimed — no tuning pass).
- Scored vs SPY buy-and-hold AND the random-pick control over the identical windows.
- Costs >= 5bps/side intraday; day-trading strategies must clear them per round trip.
- Kill: any setup that fails both its primary window and one regime split (high-VIX vs
  low-VIX halves) is closed permanently. Failures published.
- Data caveat recorded up front: yfinance intraday history is ~60 days; results on a
  60-day window are a regime sample, and a PASS only promotes the setup to a live
  paper-forward trial, never straight to money.

## Status
Not run. Bar-fetch pipeline (run_e7.py) to follow the e6 pattern: fetch -> features ->
walk-forward -> trials.jsonl + report. Expected outcome, given every prior lane: LOSE;
the interesting output is per-setup expectancy after costs, which is what the claims
never show.

## v0 results (2026-10-19, 60 trading days, 40 tickers, 14bps/round trip)

- e7a ORB: 2241 trades, expectancy +0.519%, win rate 68.6%. Passes mechanically; recorded
  SUSPECT — single regime, random control uses different stop geometry, additive "total"
  is not comparable to buy-and-hold, and independent replications put plain ORB near
  zero expectancy. Do not promote without replication on a longer/multi-regime source.
- e7b VWAP reclaim: 756 trades, expectancy -0.141% — statistically identical to the
  random-entry control (-0.136%). LOSE, as the literature says.
- e7c VWAP fade: 169 trades, expectancy -0.173% vs control -0.136%. LOSE. (First run was
  invalid: long-only simulator scored short exits as fake wins; fixed before reporting.)
- e7d gap-and-go: 3 qualifying trades in the window — untestable at this sample size.

The two setups that survive as hypotheses for replication are logged in HANDOFF; the
central result stands: after costs, day-trading setups cluster at the random-entry
control. That is what the claims never publish.
