# e13 — "CIO framework" decomposition

Pre-registered 2026-10-20. Source: a popular LLM-prompt genre — a five-stage
institutional decision framework (macro check → fundamental deep-dive → catalyst
sentiment → Kelly sizing → portfolio table). Pre-registered as a decomposition and
test of its mechanically testable components, NOT run as a live persona.

## Component decomposition and testability

1. Macro/sector rotation (Stage 1): regime-conditional sector tilts. Variation on
   e4's factor engine, which LOSE'd. Test only if a new regime definition is used.
2. Quality/secular-growth tilt (Stage 2): margin stability, revenue consistency,
   low D/E. e4-adjacent; the "deep research / intrinsic value" portion is not
   backtestable on a free-data budget and is not claimed.
3. Catalyst sentiment (Stage 3): requires timestamped news with historical depth.
   Free feeds are delayed and outcome-biased. NOT testable on this budget — the
   framework's most-quoted stage is exactly the one we cannot honestly evaluate.
4. Sizing (Stage 4): position caps and Kelly-style scaling. Sizing rescales an
   existing signal; it cannot create edge. Tested only as a modifier on a signal
   that first cleared a gate.
5. Output table (Stage 5): presentation.

## Gate

- e13 passes only if quality-tilt + regime filter + capped sizing produces a
  walk-forward Sharpe above SPY's on identical dates AND above the e4 version's.
- Expected result given e4: LOSE. Run is cheap (reuses e4 machinery) and closes the
  "have you tried the institutional framework?" question with data instead of opinion.

## Status
Pre-registered; not built.
