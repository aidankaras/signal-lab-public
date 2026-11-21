# E6 — sec filings

**Verdict: LOSE — IC 0.017, t 0.11 (17 scored days; see errata below)**

Contents: `run_e6.py` (native rebuild of the companion `aidankaras/sec-filings-e6` baseline),
`SPEC.md`, reports. No cost model and no random control: the gate is IC-only.

Errata (November 2026): the first run entered at the close of the filing date (Form 4s are often
filed after the close), used a 5-day embargo where the docstring pre-registered 10, and computed
the IC t-stat as if overlapping 5-day labels were independent. The runner now enters at the next
close, uses the 10-day embargo and a Newey-West t-stat. With 17 scored days and t = 0.11 the
LOSE is very unlikely to change; the committed numbers are from the earlier code.

See the repo root README for the results table, the errata and the harness design.
