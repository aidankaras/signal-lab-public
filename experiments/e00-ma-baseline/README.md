# E0 — ma baseline

**Verdict: informational benchmark (LOSE vs buy-and-hold, as designed)**

Contents: `run_lab.py` (runs e0 and e1 through `harness/improve.py`), reports, `latest.json`
and the data audit. The grid run is in `harness/strategies/ma_baseline.py` (fast 10/20/30 x
slow 50/100/200, 8-ticker universe); it differs from the grid in `registry/experiments.yaml`.
There is no separate e0 SPEC. (The e5 draft spec that used to sit here moved to
`experiments/e05-thesis-book/SPEC-draft-2026-10-18.md`.)

Selection is by full development-period Sharpe; the walk-forward result is reported but not
used to pick the champion. A random 3-pick control is reported alongside.

See the repo root README for the results table, the errata and the harness design.
