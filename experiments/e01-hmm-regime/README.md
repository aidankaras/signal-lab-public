# E1 — regime filter (Gaussian mixture)

**Verdict: LOSE** (e1 champion trails SPY on the 2021-05 to 2026-10 holdout; see `experiments/e00-ma-baseline/latest.json`)

Despite the folder name, e1's own run lives in `experiments/e00-ma-baseline/` (`run_lab.py`,
`latest.json`). e1 is a Gaussian-mixture volatility-regime filter
(`harness/strategies/hmm_regime.py`), not a hidden Markov model, and has no SPEC.

This folder holds a different check: `run_e4_regime.py`, the e4 factor suite re-scored on a
pre-2023 holdout (2020-09 to 2023-04). See `experiments/e04-factor-tilts/README.md` for how the
two e4 splits are read together.

See the repo root README for the results table, the errata and the harness design.
