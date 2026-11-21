# e16a — daily SPY open->close direction (trained models)
Pre-registered in SPEC.md (committed before the run). Run once: `python experiments/e16-daily-direction/run_e16.py`.
**Verdict: LOSE.** 0/4 variants pass the gate. Key facts (OOS 2010-01-04..2026-10-20, 4225 days, up-day base rate 54.25%):
- Logit AUC 0.495 (no skill); HGB AUC 0.520 (fails >0.52 by a hair); HGB accuracy 52.5% < always-up 54.3%.
- At 20 bps/round trip any daily-intraday strategy is crushed: always-long open->close net Sharpe -3.49 (gross +0.43); SPY B&H net Sharpe 0.86.
- Overnight-only is the important context: gross Sharpe 0.84 / CAGR 8.8% vs open->close gross 0.43 / 4.9% (but unprofitable net if traded daily).
- Random coin-flip p95 net Sharpe -2.15 (costs dominate). TP/SL overlays all worse net.
See e16a-report.md / e16a-results.json. Caveats: open price assumed fillable at decision time; daily OHLC cannot resolve intrabar order; ES=F and event dates not used.

**Cost sensitivity (added November 2026).** The 20 bps round trip above is the pre-registered,
deliberately conservative assumption; SPY's quoted spread is well under 1 bp and commissions are
near zero, so it overstates costs for SPY. Net Sharpe at lower costs, rescaled linearly from the
committed gross (0 bps) and net (20 bps) Sharpe. This is exact for always-long (traded every day)
and a close approximation for the variants (it assumes the cost does not change the return
volatility):

| strategy | gross | 1 bp | 2 bps | 5 bps | 10 bps | 20 bps |
|---|---|---|---|---|---|---|
| always long open->close | 0.43 | 0.24 | 0.04 | -0.55 | -1.53 | -3.49 |
| V1 logit p>0.5 | 0.46 | 0.26 | 0.06 | -0.53 | -1.52 | -3.51 |
| V2 logit p>0.55 | 0.29 | 0.20 | 0.10 | -0.17 | -0.64 | -1.57 |
| V3 hgb p>0.5 | 0.41 | 0.24 | 0.07 | -0.43 | -1.26 | -2.93 |
| V4 hgb p>0.55 | 0.65 | 0.54 | 0.42 | 0.06 | -0.53 | -1.72 |

Even at 1 bp no variant reaches SPY buy-and-hold (0.86), and no model passes the AUC > 0.52 gate,
so the LOSE verdict does not depend on the cost assumption. The -1.6 to -3.5 range quoted
elsewhere is a product of the 20 bps assumption. Exact figures: `E16_RT_BPS=2 python run_e16.py`.
