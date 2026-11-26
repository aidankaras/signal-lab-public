# E7 — daytrading setups

**Verdict: LOSE** (corrected runner, re-run November 2026, `e7-setups-rerun-2026-11.md`). After
14 bps round-trip costs, on 60 sessions of 5-minute bars (2026-09-02 to 2026-11-25):
ORB -0.133% per trade (n 2,248), VWAP fade -0.111% (n 221), VWAP reclaim -0.145% (n 736),
random-entry control -0.165%. Gap-and-go had 4 trades, untestable.

The first run's ORB result (+0.519% per trade, 68.6% win rate) was a bug: the short leg was
scored as a long and every short booked as a win. That run and its fade numbers (direction bug)
are INVALID and kept in `e7-setups.md` with the errata.

Limitation: yfinance keeps only ~60 days of 5-minute bars, so each run is a single short regime
sample and the two runs cover different windows.

Contents: `run_e7.py`, `SPEC.md`, reports.

See the repo root README for the results table, the errata and the harness design.
