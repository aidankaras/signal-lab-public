# e16a — daily SPY open->close direction (trained models)
Pre-registered in SPEC.md (committed before the run). Run once: `python on experiments/e16-daily-direction/run_e16.py"`.
**Verdict: LOSE.** 0/4 variants pass the gate. Key facts (OOS 2010-01-04..2026-10-20, 4225 days, up-day base rate 54.25%):
- Logit AUC 0.495 (no skill); HGB AUC 0.520 (fails >0.52 by a hair); HGB accuracy 52.5% < always-up 54.3%.
- At 20 bps/round trip any daily-intraday strategy is crushed: always-long open->close net Sharpe -3.49 (gross +0.43); SPY B&H net Sharpe 0.86.
- Overnight-only is the important context: gross Sharpe 0.84 / CAGR 8.8% vs open->close gross 0.43 / 4.9% (but unprofitable net if traded daily).
- Random coin-flip p95 net Sharpe -2.15 (costs dominate). TP/SL overlays all worse net.
See e16a-report.md / e16a-results.json. Caveats: open price assumed fillable at decision time; daily OHLC cannot resolve intrabar order; ES=F and event dates not used.
