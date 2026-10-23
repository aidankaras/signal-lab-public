# e8 - LSTM price model 2026-10-19

- Daily Spearman IC: **-0.0082** (t = -2.06, 3024 scored days)
- Verdict: **LOSE** (gate: IC t > 2)
- Model: 2-layer LSTM(32) on 20-session sequences, walk-forward refit yearly,
  5-session embargo, early stopping on the fit window's own holdout.
- Caveat: survivorship-biased universe; see experiments/experiment-8-deep-learning.md
