# e5 — Thesis-research buy-and-hold book (the paper portfolio)

Pre-registered 2026-10-18. Spec is binding: changes require a dated addendum below and
Aidan's sign-off. Paper only — never a real order.

## Question
Can weekly automated research (news, EDGAR Form-4 clusters, arXiv/sector theses) produce a
10-position long-horizon book that beats S&P 500 AND the random-pick control, at a holding
period that fits a small ($1k) account?

## Why this lane exists
The only lane whose holding period (weeks–quarters, not minutes) fits a $100–1k account and
~0 human hours/day. Doubles as the weekly digest product for the public content angle.

## Rules of construction
- Paper notional $1,000. Max 10 positions, equal weight (~10% each), min $25/position.
- Universe: US-listed, >$2B market cap, >$1M ADV, no leverage/inverse products, no crypto.
- Entry: a thesis must state (a) why now, (b) the edge source, (c) WHY IT WOULD BE WRONG —
  the falsifier (observable, dated, e.g. "two consecutive Form-4 cluster sells by officers",
  "guidance cut in next earnings"). No falsifier, no entry.
- Exit: falsifier hit → exit at next weekly pass, recorded regardless of P&L. Thesis intact
  after 2 quarters → review, not auto-hold. Hard stop: −25% position → mandatory falsifier
  review.
- Benchmarks (identical window, published either way): ^GSPC buy-and-hold, EW S&P,
  and the random-pick control (e_control_random, 10 names from the same universe, same dates).
- Costs: 5bps/side + slippage; entries/exits only at weekly pass boundaries (no intraweek).

## State & logging
- `registry/e5-portfolio.json`: positions {ticker, thesis, falsifier, entry_date, entry_px,
  shares, status}, decision log (one entry per weekly pass).
- `registry/trials.jsonl`: one append per weekly pass (stage "paper", origin "e5-thesis")
  so the trial-count overfit accounting applies to this lane too.
- Weekly cron `955fdb31f7de` (Sun 16:00Z): research → falsifier evaluation → decisions →
  digest to Telegram. Digest MUST report performance vs S&P and vs random-pick, and MUST
  state plainly if behind the random control (publish LOSEs).

## Gates
- Paper only until the book beats ^GSPC AND the random-pick control over 2 full quarters.
- Kill criterion: after 2 quarters behind the random-pick control, demote to thematic ETF
  allocation and stop stock-picking (per pre-registered demotion rule).
- Integrity drift (overstating results, survivorship in reporting) = kill criterion.

## Honest limits
Weekly research digest is a weak signal source; Form-4 free data has filing lag; $1k spread
over 10 names means per-position fees matter more than for institutions. Expected verdict —
matches e4's: the deliverable is the falsifiable process and the digest, not promised alpha.

## Addenda
(none yet)
