# e16 — Daily SPY direction (pre-registration, written BEFORE the run)

Question: can a walk-forward trained model, using only information known at 09:25 ET, call SPY open->close direction well enough to beat (a) always-long open->close, (b) a random coin-flip control, net of costs? Context baseline: overnight-only (close->next open) long.

## e16a — trained-model arm (backtest) — this run
**Decision**: each trading day t at 09:25 ET, LONG SPY open_t -> close_t, or FLAT. Open price = decision/fill price (the pre-open auction price is treated as obtainable; optimistic, flagged).
**Target**: y_t = 1 if close_t > open_t.
**Data**: yfinance daily OHLC (auto-adjusted), free only. SPY, ^VIX, ^N225, ^GDAXI. Fetched from 2004-06-01.

**Features (all known before the open of day t)**
- SPY prior-day close-close return, prior-day open-close return, prior-day overnight return; 5d and 20d close-close return (through t-1); 20d realized vol (through t-1)
- Overnight gap: open_t / close_{t-1} - 1 (known at the open)
- VIX prior close (log), prior-day VIX change, 5d VIX change
- ^N225 same-day (date t) close-to-close return — Tokyo closes ~02:00 ET, before the US open (0 on Japanese holidays)
- ^GDAXI prior-day (t-1) return only — Europe is open at 09:30 ET, so same-day close is lookahead and is excluded
- Day-of-week (numeric 0-4)
**Excluded, noted**: ES=F (daily bars give only the 17:00 ET settle; a 09:25 value is not recoverable without lookahead; the gap feature is the proxy; minute data needed). FOMC/CPI/NFP dates: no verified free machine-readable source wired in -> skipped.

**Models** (sklearn; features standardized for logit)
- Logistic regression (C=0.1, L2)
- HistGradientBoostingClassifier (max_depth=3, max_iter=150, learning_rate=0.05, l2_regularization=1.0, random_state=16)
Walk-forward: OOS starts 2010-01-01; expanding training window from 2004-06; retrain every 63 trading days; **embargo 1 trading day** (training rows end one trading day before the test block starts). No tuning after seeing OOS; hyper-parameters above are fixed.

**Variants (exactly 4, each logged as a trial)**
| id | model | rule |
|---|---|---|
| V1 | logit | long if p > 0.50 |
| V2 | logit | long if p > 0.55 |
| V3 | HGB | long if p > 0.50 |
| V4 | HGB | long if p > 0.55 |

**Intraday TP/SL overlays (fixed pairs, no search)**: TP +1.0% / SL -1.0%, and TP +0.5% / SL -0.5%, measured from the open, using daily high/low. Conservative ordering: if low breaches SL, stop is assumed hit first (even if the high also hit TP); else if high reaches TP, TP; else the close. Fills at the exact level (no slippage beyond costs). Applied to: always-long, V1, V3 (the p>0.5 variants) -> 6 overlay trials, labelled `overlay`, not counted among the 4 variants and not part of the gate. Daily bars cannot resolve intrabar order; minute bars would be needed for precision.

**Costs**: 5 bps/side commission + 5 bps/side slippage = 20 bps per round trip, charged on every day a position is opened and closed intraday. Overnight-only baseline is charged the same 20 bps/day (buy at close, sell at open). SPY B&H charged one round trip. Gross numbers also reported for context.

**Baselines, identical OOS window**
1. Always long open->close (net)
2. Random coin-flip long/flat, 500 sims (seed 16), same costs; report median and p95 net Sharpe
3. SPY buy & hold close->close (also via harness `evaluate`)
4. Overnight-only close->next-open long (important context: most SPY return historically accrues overnight)

**Metrics (OOS, net)**: hit rate (directional accuracy) vs base rate of up days, AUC, Sharpe, CAGR, maxDD, exposure, number of trades.

**Gate (per variant)**: BEAT requires ALL of: net Sharpe > always-long open->close net Sharpe; net Sharpe > random p95; OOS AUC > 0.52. vs SPY B&H is reported (Sharpe/CAGR/`evaluate` verdict) but not part of the gate. Experiment verdict: BEAT iff at least one variant passes the gate (4 variants, uncorrected for multiplicity — noted); otherwise LOSE. Published either way. Run once.

## e16 agent arm (forward only) — NOT BUILT NOW
An LLM "morning call": before 09:25 ET each trading day, the agent is given the same pre-open feature snapshot (plus headlines) and emits LONG/FLAT with a probability, appended with a UTC timestamp to a jsonl (`forward/e16_calls.jsonl`, append-only, one line per day, written before the open). Scored after 60 trading days against open->close outcomes with the same gate (vs always-long, vs random p95, hit rate vs base rate, net of 20 bps). No backfilled calls count (LLM knowledge-cutoff leakage), so this arm is forward-only.

## e16b — single daily pick — LATER PHASE, NOT BUILT
Each day pick one ticker/ETF from a fixed small universe for open->close; control is random pick; same cost/gate logic. Designed after e16a/agent-arm results.
