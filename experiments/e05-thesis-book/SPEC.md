# e5 — Thesis-research paper book (pre-registered 2026-10-20)

Source spec: `../experiment-5-thesis-research.md` (Aidan, 2026-10-18). Paper only, never real orders.

- Book: 10 positions, 10% each, equal-weight entry on 2026-10-20 close, rebalance quarterly,
  every pick carries a written thesis and falsifier (in `registry/e5-portfolio.json`).
  Falsifier hit => exit proposed and logged regardless.
- Benchmarks: S&P 500 (SPY, ^GSPC proxy) and QTUM (thematic ETF). Notional $1,000.
- Mandatory control: 500 random 10-name draws from the SAME 38-name candidate pool (fixed seed 5),
  same entry date, equal weight. Book must beat the random median, else the picking layer is dead.
- Demote rule: after 2 quarters (>=182 days) if book trails SPY by >10pp -> index the theme (ETF);
  pipeline survives only as the weekly digest.
- Verdict PENDING until 2 full quarters. Costs ignored at entry (buy-and-hold, 5bps/side negligible).
- Known bias: picks and pool were chosen by the author knowing the hot themes; control shares that bias.
- Not built: automated weekly thesis radar/candidate tree (cron 955fdb31f7de does the web pass).
