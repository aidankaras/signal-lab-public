# e7 — claimed day-trading setups, tested as stated 2026-11-25

Window: 2026-09-02..now (5m data limited to 60d; gap-and-go daily from 2026-07-01). BROAD-40. Costs 14bps/round trip. Rules as claimed, untuned.

- **e7a_orb**: 2248 trades, expectancy -0.00133, win rate 0.413
- **e7b_vwap_reclaim**: 736 trades, expectancy -0.00145, win rate 0.281
- **e7c_vwap_fade**: 221 trades, expectancy -0.00111, win rate 0.416
- **e7d_gap_and_go**: 4 trades, expectancy 0.01215, win rate 0.75
- **random_control**: 2248 trades, expectancy -0.00165, win rate 0.289

SPY buy-and-hold over the window: -0.061
Verdict: **LOSE** — expectancy after 14bps round-trip costs is what the claims never publish.

Caveat: 5m history is ~60 days (platform limit) — a single regime sample; a PASS promotes to paper-forward only.

## Reading this result (added with the re-run, November 2026)

Corrected `run_e7.py` (ORB short leg simulated as a short; VWAP fade goes long below VWAP), run
once on 2026-11-25 with the rules in `SPEC.md`, untuned. It replaces the INVALID ORB and fade
numbers in `e7-setups.md`, which stay in the repo for the record.

- **Data limit.** yfinance serves only the last ~60 days of 5-minute bars, so this is a
  different sample from the first run: 60 sessions, 2026-09-02 to 2026-11-25, 40 BROAD-40 names.
  The 2026-10-19 run covered roughly July to October. Neither window can be extended on free data,
  and a 60-day sample is a single market regime (SPY fell 6.1% over this one).
- **e7a ORB: LOSE.** 2,248 trades, -0.133% per trade after 14 bps round-trip costs, win rate
  41.3%. The earlier +0.519% / 68.6% came entirely from the short-leg bug.
- **e7c VWAP fade: LOSE.** 221 trades, -0.111% per trade, win rate 41.6%.
- **e7b VWAP reclaim: LOSE** (again). 736 trades, -0.145% per trade.
- **Random-entry control:** -0.165% per trade (2,248 trades). ORB and fade lose a little less
  than random entries, but every setup loses money after costs, so none passes the gate
  (positive expectancy, n >= 30, total above SPY).
- **e7d gap-and-go:** 4 trades (daily bars from 2026-07-01). Untestable at this size.
- The SPEC's regime-split kill rule (high-VIX vs low-VIX halves) is not implemented in the
  runner; with negative expectancy on the whole window it would not change the verdict.

Two runner fixes went in with this re-run, both before it was run:
1. Cached 5-minute bars spanning the November DST change have mixed UTC offsets; reading them
   with `parse_dates` left string timestamps, so every per-day groupby failed. The cache is now
   parsed through UTC and converted to New York time.
2. SPY buy-and-hold was measured from a fixed 2026-07-01, which no longer matched the 60-day
   5-minute window. It now starts on the first 5-minute bar's date, as the SPEC's identical-window
   rule requires.
