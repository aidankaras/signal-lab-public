# E2 — insider filings

**Verdict: LOSE** — v0 AUC 0.498 vs a 0.55 kill gate (pending re-run, see errata); v2 cluster events mean −1.53%, t −2.30, n=120.

Contents: `run_e2_edgar.py` (v0, Form-4 count clusters), `run_e2_v1.py` (v1/v2 dollar-weighted
clusters on point-in-time S&P 500 membership), `SPEC-v1.md`, `SPEC-v2.md`, reports and event
CSVs. v0 has no separate SPEC; its gate is in `registry/experiments.yaml`. v0 was killed by its
gate and then reopened twice (v1, v2); v2 was built on a hint found in v1 (see `SPEC-v2.md`).

Errata (November 2026): v0 counted filings over a Monday-Sunday week but entered at the close on
or before that Monday, up to about 6 days before the counted filings were public. The runner now
enters at the next Monday's close. The committed v0 AUC (0.498) is from the earlier code and is
pending a re-run. v1/v2 are not affected by this bug.

See the repo root README for the results table, the errata and the harness design.
