# E10 — gbm ranker

**Verdicts:**
- **v1 (point-in-time membership): LOSE** — see `README-v1.md` and `e10-v1-survivorship.md`.
- **v0 (BROAD-40): SUSPECT, not promoted** — the corrected runner was re-run in November 2026
  (`e10-v0-gbm-rerun-2026-11.md`): IC 0.010 (Newey-West t 2.03), top-decile net Sharpe 1.07 vs
  SPY 0.97 at 5 bps/side. That passes the pre-registered gate by a hair, on a survivor-biased
  universe, and a first attempt missing one stock (META) failed it. The point-in-time version (v1)
  loses. The original 2026-10-19 v0 numbers (`e10-v0-gbm.*`, Sharpe 2.08, 8,689x) are INVALID:
  overlapping 5-day returns compounded daily, pre-cost.

Contents: v0 (`run_e10_v0.py`, `SPEC-v0.md`, `e10-v0-gbm.*` from the invalid first run,
`e10-v0-gbm-rerun-2026-11.*` from the corrected runner) on BROAD-40 and v1
(`fetch_membership.py`, `fetch_prices_v1.py`, `run_e10_v1_pit.py`, `SPEC-v1.md`, `README-v1.md`,
`e10-v1-survivorship.*`) on point-in-time S&P 500 membership. v0 has no random control; v1 has one.

See the repo root README for the results table, the errata and the harness design.
