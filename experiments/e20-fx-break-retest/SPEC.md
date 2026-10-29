# e20 — fxalexg break–retest–engulfing setup, pre-registered spec

Pre-registered BEFORE any backtest output was seen. Source: digests of fxalexg
"$100 -> $1M in 90 days" (YouTube videos xAJT6cmJ5gs, hiad0PbI47o, njvjjOgiLKo). Only the explicitly codable
rules are implemented; discretionary parts ("cleanest pair", early exits,
look-left judgement) are out of scope and listed as such.

## Data
- Dukascopy public datafeed, free, no key: monthly `BID_candles_hour_1.bi5`
  LZMA files, 24-byte records (t_offset_sec, open, close, low, high, volume),
  prices int32 (1e5, 1e3 for JPY), UTC. Aggregated to 4H and daily/weekly
  resamples in the runner (all causal: label at bar close, act next bar open).
- Pairs: EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD NZDUSD GBPJPY GBPCHF AUDCAD.
  Drop list finalized after download; actual per-pair date range recorded in
  REPORT.md.
- Period: 2015-01-01 .. latest available. Development = 2015-01-01..2021-12-31
  (may be looked at), holdout = 2022-01-01..end (scored ONCE, at the end).

## Coded rules (exact)
Bias (trend filter), per pair:
- Daily bias bearish if daily close < daily EMA50 of daily closes; bullish if
  close > EMA50.
- Weekly bias bearish if weekly close < weekly EMA20; bullish if > EMA20.
- Short setups require both bearish on the most recently CLOSED daily and
  weekly bars before the signal bar. Longs symmetric.

Area of interest (AOI): level L such that BOTH:
- L is a round number: multiple of 0.00500 (JPY pairs: multiple of 0.500).
- L is within 15 pips of a daily fractal swing high (for shorts) / swing low
  (for longs): a bar whose high exceeds the highs of the 2 bars on each side
  (5-bar fractal), formed within the last 120 trading days.
Levels come from a precomputed list of round numbers near swing points;
recomputed causally each day.

Break: a 4H candle BODY closes beyond L in the bias direction
(short: 4H close < L; long: 4H close > L).

Retest: within 72h after the break, price trades back to within 5 pips of L
(short: high >= L - 5 pips; long: low <= L + 5 pips) WITHOUT a 4H candle body
closing back through L by more than 10 pips (short: 4H close > L + 10 pips
invalidates; long symmetric). Invalidation cancels the setup.

Trigger: during the retest window, a 1H bearish engulfing (shorts): body
engulfs prior body (open >= prev close, close <= prev open, strict body
containment) AND closes below L (bias side); mirror for longs. Trigger candle
must close between 07:00 and 17:00 London time (inclusive hour-of-close).
Entry: next 1H bar open after the trigger candle close.

Stop loss: beyond the retest extreme +/- 5 pips (short: retest-window max high
+ 5 pips from entry-side distance), clipped to 15..40 pips; if structure needs
> 40 pips, skip the trade. Distance = |entry - SL|.

Take profit: fixed R multiple of stop distance. Primary = 3R; variants logged
as separate trials: 2R, 4R. Trades resolve bar-by-bar on 1H data: if a bar's
range touches both SL and TP, count SL (conservative).

Vetoes (entries, not exits):
- No new entries on Sunday, Thursday, Friday (entry timestamp day-of-week;
  timestamps UTC, day taken at London date).
- Skip NFP days: first Friday of month (already covered by Friday veto; kept
  for completeness if vetoes are ablated).
- One open position per pair; primary variant: max 1 portfolio-wide open
  (his stated rule). Variant: one-per-pair (logged as separate trial).
- 3 concurrent signals: portfolio-wide variant takes the first by time.

Costs: per-pair round model — spread (EURUSD 0.8, USDJPY/GBPUSD/USDCHF/USDCAD
1.0, AUDUSD/NZDUSD 1.2, crosses GBPJPY/GBPCHF/AUDCAD 2.5 pips) + 0.5 pip
slippage per side. Expressed in pips and converted to R via stop distance
(cost_R = (spread + 2*slippage) / SL_pips). Outcome R_net = R_gross - cost_R.

Sizing for evaluation: 1% of equity per trade, fixed fractional, compounding.
Separately, on the SAME trade sequence: his stated 50% and 100% risk per
trade, 5000 bootstrap reshuffles of the trade sequence, probability that
account falls below 5% of start ("ruined").

## Gates for BEAT (ALL must pass, holdout only, primary variant 3R / 1-position)
1. Mean R per trade after costs > 0 with t-stat >= 2.0 (or bootstrap p < 0.05).
2. Mean R > p95 of 2000 random-entry strategies: same pairs, same eligible
   entry hours/days, same SL-distance distribution (sampled from realized
   trades), same TP R, same cost model.
3. Beats baseline: 20/100-day MA trend-follow (daily close > MA20 & > MA100 ->
   long, < both -> short) on same pairs, same 1% risk, same costs; compare
   annualized return / annualized vol of the equity curve (higher ret/vol
   ratio wins; also report ret//vol for each).
4. >= 60 holdout trades. If < 60, verdict = INSUFFICIENT (not BEAT, not LOSE).

Ablations (development set, reported not gating): remove round-number
requirement; remove engulfing trigger (enter on retest touch); remove trend
filter; remove day vetoes.

Multiple-testing note: every variant (3 TP x 2 position rules) + 4 ablations
count as trials in registry/trials.jsonl; Bonferroni noted against the
primary gate (effective alpha 0.05/11 ~ 0.0045).

## Integrity
- No lookahead: all indicators computed on closed bars; signal bar t ->
  execution at open of t+1. A no-lookahead assert test shifts the input data
  forward one bar and verifies signals do not change for unchanged history.
- Research only; no orders, no spending.
