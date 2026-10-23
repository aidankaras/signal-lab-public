# e9 Phase 1 — local LLM analyst 2026-10-19

Zero-shot Qwen2.5-1.5B (4-bit, llama.cpp CPU) called UP/DOWN on 1360 (ticker, week)
point-in-time summaries for the 2026 holdout window.

- Direction accuracy: **47.7%** (UP base rate 47.7%; binomial p vs 50/50 = 0.098)
- Signed Spearman IC: nan (t = nan)
- Model UP bias: 100.0%
- Verdict: **LOSE** (gate: accuracy > 55% AND p < 0.01)

Contamination note: Qwen2.5 predates the 2026 holdout window, so pretraining leakage
is bounded by the vendor cutoff claim. Fine-tuned arm (Phase 2) is gated: not run
unless the zero-shot arm clears its gate.
