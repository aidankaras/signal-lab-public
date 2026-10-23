# e2 v1 — open-market insider BUY clusters (pre-registration, written 2026-10-22 before any run)

Why v1 despite v0 kill: v0 counted all Form-4 filings (mostly grants/sales = noise). The literature signal
(Lakonishok-Lee 2001, Cohen-Malloy-Pomorski 2012) is open-market *purchases* (code P), clustered. The SEC bulk
Form 3/4/5 data sets (2018q1–2025q4, 32 files, UA aidan@aidankaras.dev) make the buy/sell split cheap. One shot; no grid.

Data: SUBMISSION + REPORTINGOWNER + NONDERIV_TRANS. Keep DOCUMENT_TYPE 4/4A, TRANS_CODE == P, shares*price >= $10k.
Universe: point-in-time S&P 500 (experiments/e10-survivorship membership + sp500pit prices), member on FILING_DATE.

Event: on FILING_DATE d, ticker has >= 2 distinct reporting owners with qualifying P buys filed in (d-30d, d].
Dedupe: at most one event per ticker per 63 trading days. Known only after filing -> entry = close of the first
trading day strictly after d. Hold 21 trading days. Label = stock return - SPY return over same window - 20 bps cost.
Delisted names exit at last available price.

Control: for every event, a random PIT member on the same entry date (2000 resamples) -> distribution of mean
abnormal return.

Gates (ALL must hold, else LOSE and the insider lane closes):
1. Train 2018–2022 mean net abnormal > 0.
2. Holdout (filing >= 2023-01-01) mean net abnormal > 0 with t > 2 (events clustered by calendar month).
3. Holdout mean beats the random-control p95.
4. >= 100 holdout events.
Reported but not gated: all-P single-buyer events, buy $-size terciles.
