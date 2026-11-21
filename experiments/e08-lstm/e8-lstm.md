# e8 - LSTM price model 2026-10-19

> **Errata (November 2026).** The t-stat below treats overlapping 5-day labels as independent;
> roughly corrected (t / sqrt(5)) it is about -0.9, so the IC is not distinguishable from zero.
> The early-stopping split also shared dates with training. See `README.md`.

- Daily Spearman IC: **-0.0082** (t = -2.06, 3024 scored days)
- Verdict: **LOSE** (gate: IC t > 2)
- Model: 2-layer LSTM(32) on 20-session sequences, walk-forward refit yearly,
  5-session embargo, early stopping on the fit window's own holdout.
- Caveat: survivorship-biased universe; see experiments/e08-lstm/SPEC.md
