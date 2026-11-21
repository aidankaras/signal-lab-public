# E10 — gbm ranker

**Verdicts:**
- **v1 (point-in-time membership): LOSE** — see `README-v1.md` and `e10-v1-survivorship.md`.
- **v0 (BROAD-40): INVALID** — the 2026-10-19 run compounded overlapping 5-day returns daily
  (Sharpe inflated by about sqrt(5)) on a survivor-biased universe, pre-cost. Runner corrected,
  re-run pending. See the errata in `e10-v0-gbm.md`.

Contents: v0 (`run_e10_v0.py`, `SPEC-v0.md`, `e10-v0-gbm.*`) on BROAD-40 and v1
(`fetch_membership.py`, `fetch_prices_v1.py`, `run_e10_v1_pit.py`, `SPEC-v1.md`, `README-v1.md`,
`e10-v1-survivorship.*`) on point-in-time S&P 500 membership. v0 has no random control and was
pre-cost; v1 has both.

See the repo root README for the results table, the errata and the harness design.
