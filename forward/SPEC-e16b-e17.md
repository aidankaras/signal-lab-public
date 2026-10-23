# e16b + e17 — forward-only AI daily calls (PRE-REGISTRATION)

Written 2026-10-23, before any call is recorded. Frozen; changes = new version + new clock.

## Protocol
- Each NYSE trading day, an agent runs `e16b_snapshot.py` (prior closes for 14 ETFs, VIX, Nikkei, DAX, ES futures, headlines) and records ONE call via `e16b_record.py` before 09:25 ET. Script refuses late or duplicate calls; log is append-only (`e16b_calls.jsonl`).
- e16b: SPY LONG or FLAT for that day's open->close, plus p_up.
- e17: one pick from SPY QQQ IWM DIA XLK XLF XLE XLV XLY XLI XLP XLU TLT GLD, or NONE.
- Paper plumbing only: LONG -> Alpaca PAPER buy 15 SPY at the open (OPG); no-agent job sells MOC. Scoring uses public open/close prices, not fills.
- Cost assumption: 0.20% round trip per traded day.

## Gates (scored by `e16b_score.py`, verdict only at n >= 60 scored days)
e16b BEAT requires ALL: Sharpe > always-long Sharpe; Sharpe > p95 of 2000 random coin-flip long/flat Sharpes; hit rate > base rate of up days.
e17 BEAT requires ALL: mean daily net > SPY open->close net mean; > p95 of 2000 random-pick means; > 0.
Otherwise LOSE; lane closed, no re-tuning on the same data. Missed days are skipped, not filled.

## Caps
Paper only. No real money without gates cleared AND Aidan's explicit approval.
