# E9 — local llm

**Verdict: INVALID — the "constant-UP" result was an output-parser bug; parser fixed, pending re-run.** See `e9-llm-analyst.md`.

Each experiment folder is self-contained: runner code, its report (markdown + JSON),
and `SPEC.md` — the pre-registration written before the run (grids, gates, kill criteria).
Verdicts come from the shared harness: walk-forward evaluation, costs in every trade,
same-window comparison vs SPY and a random-entry control, append-only trial registry.

See the repo root README for the master results table and the harness design.
