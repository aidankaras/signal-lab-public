# e19 — Zero-shot time-series foundation models on SPY + 14 ETFs (pre-registration, written BEFORE any model output)

Question: do free open-source TSFMs (Kronos, TimesFM), used zero-shot with no fine-tuning, forecast daily ETF returns well enough to beat simple baselines net of costs? Paper/research only.

## Universe & data
SPY QQQ IWM DIA XLK XLF XLE XLV XLY XLI XLP XLU TLT GLD. Daily OHLCV, yfinance, auto_adjust=True, fetched from 2018-01-01. Context uses only bars with date <= decision date t.

## Models (zero-shot, fixed settings, no tuning after seeing output)
- **Kronos**: shiyu-coder/Kronos, `NeoQuasar/Kronos-small` + `Kronos-Tokenizer-base`, max_context 512, inputs open/high/low/close/volume/amount(=volume*close), T=1.0, top_p=0.9, sample_count=5 (mean path), torch seed fixed (19). One 5-step path per (ETF, date); forecast return at horizon h = pred_close[h]/close_t - 1.
- **TimesFM**: google-research/timesfm, `google/timesfm-2.5-200m-pytorch` (smallest current checkpoint, 200M), max_context 512 of close prices, point forecast, default ForecastConfig as in model card. Forecast return at h = fc[h]/close_t - 1.
Code/weights are untrusted: run in a separate sandboxed directory.

## Test window (after training cutoffs)
- TimesFM: pretraining = GiftEvalPretrain, Wikimedia pageviews (cutoff Nov 2023), Google Trends (cutoff EoY 2022), synthetic. No explicit price-data cutoff stated; Kronos: corpus of 45 exchanges, **no cutoff date stated** in card/paper (paper posted 2025-08-02). Per rule for unclear cutoffs: **primary test window = 2024-07-01 through last available bar** for both models. Caveat: Kronos may have seen part of this window; a descriptive-only sub-window 2025-08-01+ (after Kronos paper release) is also reported but carries NO verdict.

## Protocol
Walk-forward, decision at close of day t using bars <= t. Horizons h=1 and h=5 trading days. Position taken at close t, held to close t+h (close-to-close). h=1: rebalance every day; h=5: rebalance every 5th trading day (non-overlapping), starting at the first test date. Daily return series = weight * next-day ETF return.

## Strategies (per model x horizon)
- **A (SPY long/flat)**: long SPY if forecast SPY return > 0 else cash (0 return).
- **B1**: hold the top-1 ETF by forecast return (100%). **B3**: hold the top-3 equal weight (long-only, fully invested; forecasts are ranked across the 14 ETFs even if all negative).
Costs: 10 bps per side on turnover (cost = 0.001 * sum|w_new - w_old| at each rebalance, incl. initial entry). 

## Baselines (same window, same cost model, same rebalance schedule)
1. Buy-and-hold SPY (10 bps entry), annualised Sharpe (daily, sqrt252).
2. Random control, 2000 sims, seed 19: A -> random long/flat (p=0.5 per period); B1/B3 -> random pick of 1/3 of 14 ETFs per period. Gate threshold = p95 Sharpe.
3. Simple 20-day momentum rule: A -> long SPY if 20d return > 0; B1/B3 -> top-1/top-3 ETFs by trailing 20d return.

## Gates — ALL must pass for BEAT, else LOSE
G1 Sharpe(strategy net) > Sharpe(SPY buy-and-hold).
G2 Sharpe > p95 of 2000 random strategies.
G3 Sharpe > Sharpe of 20d momentum rule.
G4 Directional hit rate > base rate with one-sided exact binomial p < 0.05. A: hit = (forecast>0) == (realized SPY h-period return>0), base rate = fraction of test periods in which SPY rose (hit rate of always-long). B1/B3: hit = chosen ETF's realized h-period return >0, base rate = share of positive ETF-period returns across the universe; picks treated as independent (optimistic; flagged).

## Trials / multiple testing
Verdicts: 2 models x 2 horizons x 3 strategies = **12 trials**, each logged to registry/trials.jsonl (experiment e19_foundation_forecast). Bonferroni: per-trial alpha 0.05/12 = 0.0042 for G4; the registered gate remains p<0.05, but any BEAT is reported with whether it survives Bonferroni. Extra descriptive stats (IC, AUC, 2025-08+ subwindow) are not trials and carry no verdict. No parameter changes after seeing outputs; if a run fails technically it is fixed without looking at performance and rerun identically.
