# E8 — lstm

**Verdict: LOSE — no skill (IC -0.0082; overlap-corrected t about -0.9)**

Contents: `run_e8.py`, `SPEC.md`, reports. No cost model and no random control: the gate is
IC-only.

Errata (November 2026): the early-stopping split took the last 25% of training rows, but rows
were ordered by ticker, so it held out the last ~10 tickers over all dates and shared dates with
training. The IC t-stat also treated overlapping 5-day labels as independent; a rough correction
(t / sqrt(5)) puts the published t = -2.06 near -0.9, so the IC is not distinguishable from zero.
"Anti-predictive" was not supported; the honest reading is "no skill". The runner now splits by
date with a 5-session gap and reports a Newey-West t; re-run pending.

See the repo root README for the results table, the errata and the harness design.
