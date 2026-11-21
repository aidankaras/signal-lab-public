# E4 — factor tilts

**Verdict: SUSPECT, not promoted** — reversal and trend pass the strict gate on both holdout splits, but on a survivor-biased universe with holdout-selected champions.

Contents: `run_e4.py` (four long-only factor tilts on BROAD-40 through `harness/improve.py`),
the 2023-05 to 2026-10 holdout report and `e4-latest.json`. There is no SPEC; the original
registry entry lists factors that were not built (see `registry/experiments.yaml`). The second
split (2020-09 to 2023-04) is in `experiments/e01-hmm-regime/`.

How to read it (corrected November 2026): on the strict gate (beat SPY, the random-pick median
Sharpe and the equal-weight universe CAGR), reversal and trend PASS on both splits, and momentum
passes the 2023+ split only. That is not a usable edge, for three reasons: the universe is
today's 40 large caps (survivor-biased), the champion parameters differ between the splits
(top_n 5 vs 8), and the champions were promoted using the same holdout they are scored on
(`harness/improve.py`). Hence SUSPECT, not promoted. The earlier label "LOSE — no factor passes
both regime splits" was wrong.

See the repo root README for the results table, the errata and the harness design.
