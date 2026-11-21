# e13 — 'CIO framework' decomposition 2026-10-20

> **INVALID (errata, November 2026).** This run used the wrong price data: `harness.data.fetch`
> returned the cached 8-ticker e0 panel (2005–2026) instead of BROAD-40, so most selected names
> earned 0%. The runner also left the book 50% in cash, never switched to SPY when risk-off, earned
> the decision day's own return, used ROA in place of ROE, and never rebalanced the random control.
> The numbers below are kept for the record only. `run_e13.py` is now corrected; the result is
> pending a re-run.

Mechanical skeleton of the popular five-stage LLM CIO prompt: SPY-200d-MA regime
filter, EDGAR point-in-time quality tilt (top 10, 5% cap, monthly), 5 bps/side.
Catalyst-sentiment stage: NOT testable on free data — logged not-run.

- Strategy Sharpe: **0.536** vs SPY 0.642 vs random-10 -1.216
- Total: strategy +19.5% vs SPY +846.6%
- Verdict: **LOSE** (gate: beat SPY AND random control on identical dates)
- Universe caveat: BROAD-40 survivorship — even a pass would be SUSPECT (see e10).
