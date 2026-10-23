# e9 — local LLM market analyst (zero-shot arm first)

Pre-registered 2026-10-18, revised 2026-10-19 after the GPU feasibility check:
the laptop's GPU is an integrated Radeon 840M/860M (Krackan) — adequate for local
inference via llama.cpp's Vulkan backend (Mesa RADV driver already present), not
practical for LoRA fine-tuning. Plan revised accordingly:

## Phase 1 — zero-shot small-LLM analyst (runs on the laptop)

- Model: Qwen2.5-1.5B-Instruct, 4-bit GGUF, llama.cpp Vulkan build.
- Task: for each (ticker, week) in the holdout window, the model receives a
  point-in-time summary (trailing returns, volatility, volume trend, e6 Form-4
  counts — all stamped as of the decision date) and outputs UP/DOWN for the next
  5 sessions' abnormal return vs SPY.
- Scoring: direction accuracy and Spearman IC vs the 50/50 baseline through the
  standard machinery. The question is not whether the model sounds smart — it is
  whether its direction calls carry measurable signal.
- Contamination, stated honestly: a zero-shot 1.5B model has opaque pretraining, so
  leakage is bounded by the vendor's cutoff claim (Qwen2.5 predates the 2026 holdout
  window) and noted in the report rather than claimed away.

## Phase 2 — fine-tuned arm (gated)

LoRA fine-tune needs either a cloud GPU spot rental (inside the $275/90d cap, needs
approval) or a multi-day CPU run. Deferred until Phase 1 shows the zero-shot arm is
worth improving; if Phase 1 scores at chance, fine-tuning on the same weak features
is not expected to change that, and the lane closes.

## Gates

- Phase 1 BEAT: direction accuracy > 55% AND IC t > 2 over the holdout window.
- Kill: accuracy within noise of 50% closes the LLM-analyst lane (consistent with the
  retired project's agent arm, which was never run).

## Status
Phase 1 in setup: llama.cpp Vulkan build + Qwen GGUF download on the laptop.
