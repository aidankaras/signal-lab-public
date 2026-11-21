# E10 — gbm ranker

**Verdicts:**
- **v1 (point-in-time membership): LOSE** — see `README-v1.md` and `e10-v1-survivorship.md`.
- **v0 (BROAD-40): INVALID** — the 2026-10-19 run compounded overlapping 5-day returns daily
  (Sharpe inflated by about sqrt(5)) on a survivor-biased universe, pre-cost. Runner corrected,
  re-run pending. See the errata in `e10-v0-gbm.md`.

Each experiment folder is self-contained: runner code, its report (markdown + JSON),
and `SPEC.md` — the pre-registration written before the run (grids, gates, kill criteria).
Verdicts come from the shared harness: walk-forward evaluation, costs in every trade,
same-window comparison vs SPY and a random-entry control, append-only trial registry.

See the repo root README for the master results table and the harness design.
