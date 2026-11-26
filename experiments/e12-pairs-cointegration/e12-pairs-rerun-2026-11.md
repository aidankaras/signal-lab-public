# e12 — pairs trading via cointegration 2026-11-25

Walk-forward years 2016-2026, fit on trailing 3y, top-5 pairs, z=+-2/0.5/4, 10bps/pair round trip.

- Mean annual return: **-0.0293** (annual Sharpe proxy -0.54, 11 yearly points)
- SPY mean annual: 0.1503
- Random-pairs control (same rule, random pairs): -0.0384
- Verdict: **LOSE**

Note: scanning up to 780 pairs a year is heavy multiple testing; the walk-forward control
and the random-pair comparison are the honest referees. A Kalman hedge ratio
is the v1 upgrade only if v0 clears the gate.

## Reading this result (added with the re-run, November 2026)

Corrected `run_e12.py`, run once on yfinance data downloaded 2026-11-25, rules and gate as in
`SPEC.md` (with the Engle-Granger -3.90 critical value noted there). It replaces the INVALID
2026-10-19 numbers in `e12-pairs.md`, which stay in the repo for the record.

- **Verdict: LOSE.** Mean annual return -2.9% (2016-2026) vs SPY +15.0% over the same years. The
  selected cointegrated pairs made money in 3 of 11 years and lost in each of the last five.
- **No better than random pairs.** Five random pairs per year through the same rule averaged
  -3.8%, so cointegration selection added about one point a year over chance, well inside the
  year-to-year noise (annual returns range from +5.1% to -12.3%).
- 2026 is a partial year (to 2026-11-25).
- One further runner fix went in with this re-run: `prices()` still dropped any name with a
  missing value anywhere since 2012 (META, listed in May 2012) from every year, contradicting the
  per-year universe described in the docstring. The global drop was removed; each year already
  keeps only names with full history over its fit and trading window. All 40 names (780 pairs)
  are scanned every year.
