# E5 — thesis book (paper)

**Verdict: none — discontinued when the repo was archived (November 2026).** The book was seeded
2026-10-20; only the day-0 snapshot is committed (0% everywhere by construction), so the
2-quarter demotion rule was never evaluated.

Run: `python experiments/e05-thesis-book/run_e5.py` (add `--seed` only to re-initialise;
it overwrites state). State is written to `registry/e5-portfolio.json`.
Report: `e5-thesis-book.md` (latest snapshot; `run_e5.py` regenerates it as `e5-report.md`). See `SPEC.md`. Day-0 "percentile vs random" prints 1.0 from float ties — ignore until prices move.
