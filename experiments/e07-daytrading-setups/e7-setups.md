# e7 — claimed day-trading setups, tested as stated 2026-10-19

> **Errata (November 2026).** e7a ORB is INVALID: the short leg was simulated as a long, so every
> short breakout was booked as a win. That is where the +0.519% expectancy and 68.6% win rate on a
> 2R target come from. e7c VWAP fade always shorted, even when price was stretched below VWAP.
> The "BEAT" verdict below came from the ORB bug. `run_e7.py` is fixed; the November 2026
> re-run (`e7-setups-rerun-2026-11.md`) has ORB at -0.133% and fade at -0.111% per trade, LOSE.
> e7b (reclaim, long-only) is not affected. e7d enters the day after the gap, not at the
> gap-day open as claimed (see `run_e7.py`).

Window: 2026-07-01..now (5m data limited to 60d). BROAD-40. Costs 14bps/round trip. Rules as claimed, untuned.

- **e7a_orb**: 2241 trades, expectancy 0.00519, win rate 0.686
- **e7b_vwap_reclaim**: 756 trades, expectancy -0.00141, win rate 0.3
- **e7c_vwap_fade**: 169 trades, expectancy -0.00173, win rate 0.296
- **e7d_gap_and_go**: 3 trades, expectancy 0.00945, win rate 0.667
- **random_control**: 2241 trades, expectancy -0.00136, win rate 0.32

SPY buy-and-hold over the window: 0.026
Verdict: **BEAT** — expectancy after 14bps round-trip costs is what the claims never publish.

Caveat: 5m history is ~60 days (platform limit) — a single regime sample; a PASS promotes to paper-forward only.