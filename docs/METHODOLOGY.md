# Methodology

How Signal Lab decides a strategy "works", and where the implementation falls short of the
rules. Every rule below exists because a past experiment exposed the failure it prevents. See
the README errata (November 2026) for the experiments where these rules were broken.

## 1. Causality
- Signals at close *t* use data up to *t* only. `harness/experiment.py::simulate` shifts weights
  by one bar, so a weight decided at close *t* earns the close *t* to close *t+1* return. That is
  a fill at the signal bar's close (a market-on-close assumption), not at the next bar's open.
  On a gap day the two differ.
- `tests/test_harness.py` pins this: changing a signal at *t* never changes returns before *t+1*.
- Runners that do not use `simulate` handle timing themselves. Three of them got it wrong (e12
  booked P&L against the new position, e13 earned the decision day's return, e20 traded inside an
  unfinished 4H bar); see the errata.
- Labels on multi-day horizons overlap from day to day. IC t-stats for e6, e8 and e10 v0 now use
  a Newey-West correction (`harness.evaluator.newey_west_t`); the committed numbers predate it.

## 2. Costs
Most backtests charge a per-side cost on turnover (default 5 bps; 10 bps for e10 v1; 20 bps round
trip for e16a, which is conservative for SPY, see the e16a cost table). Not all do: e2 v0, e6, e8
and e9 are scored on IC or accuracy only, and the e10 v0 run was pre-cost. Gross numbers are
reported next to net numbers where both exist.

## 3. Same-window comparison
Strategy, SPY (total-return proxy), and controls are scored on identical dates.

## 4. Controls
- **Random entry / random pick**: same rule or same position count, random selection.
- **Random pairs** (e12), **equal-weight universe**, and for e05 a random-pick book.
- Strict verdict (`harness/verdict.py`, used by e0, e1 and e4): PASS requires beating SPY on total
  return **and** the random-pick median Sharpe **and** the equal-weight universe CAGR. On a
  survivor-biased universe most random 3-stock picks beat SPY (16 of 20 seeds in the e0 report),
  so beating SPY alone means little. (That count used the pre-November-2026 BEAT formula, see
  errata; it may shift slightly on a re-run.)
- Not every experiment has a control: e06, e08, e09 and the e10 v0 run have none.

## 5. Overfit accounting
`registry/trials.jsonl` is append-only and holds the trials that were logged. It is not complete:
e2 v0, e3 and e18 were not logged, the e20 follow-up trials are in a private registry, some runs
were logged more than once (e9 five times, e7 twice), and one block of rows is out of
chronological order. Deflated Sharpe (Bailey & López de Prado) is computed only for e0, e1 and
e4, over all logged dev trials for that experiment (duplicates included). PBO is not implemented.

Champion selection in `harness/improve.py` picks the best full development-period Sharpe; the
walk-forward result is reported but does not drive selection. A champion is promoted only if it
beats the previous champion on the holdout **and** beats SPY there, so the holdout is reused for
selection once per generation and is not a clean out-of-sample test.

## 6. Pre-registration
Grids, gates and kill criteria go into `experiments/*/SPEC*.md` before the run. In practice:
`registry/experiments.yaml` covers e0-e5 only and its grids differ from what ran; e1, e3 and e4
have no SPEC; and e2 was reopened twice after its kill gate (disclosed in its SPEC files).

## 7. Survivorship
Universes of today's large caps inflate results. The e10 v0 run on BROAD-40 is INVALID for a
separate reason (overlapping returns compounded daily, see errata), so it does not measure the
survivorship effect cleanly. The point-in-time rebuild (e10 v1) gives net Sharpe 0.54 vs SPY 0.97,
LOSE. Any single-stock result on the BROAD-40 universe is flagged SUSPECT.

## 8. Known limits
See README "Limitations".
