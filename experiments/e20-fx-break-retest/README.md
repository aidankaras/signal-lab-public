# e20 — FX break → retest → engulfing setup

Tests a popular retail FX day-trading setup (trend filter, round-number level,
4H break, retest, engulfing trigger, day vetoes) on 10 major/cross pairs,
2015–2026, with a once-scored 2022+ holdout.

**Verdict: LOSE** — holdout mean -0.04R per trade, t -0.29, n 152.
Follow-up (Nov 2026): the best development-period ablation (no engulfing trigger) was
pre-registered and tested out of sample twice and also failed; FX lane closed.
Full write-up: [`REPORT.md`](REPORT.md). Pre-registration: [`SPEC.md`](SPEC.md).

| file | purpose |
|--|--|
| `fetch_dukascopy.py` | download + decode Dukascopy hourly candles → `data/` |
| `fetch_curl.sh` | curl fallback to fill `cache/` when the Python fetch times out |
| `run_e20.py` | rules, simulator, controls, gates → `results/` |
| `results/results.json` | every variant, gate and control statistic |
| `results/trades_*.csv` | trade lists per variant |
