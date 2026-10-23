# Methodology

How Signal Lab decides a strategy "works". Every rule below exists because a past experiment
exposed the failure it prevents.

## 1. Causality
- Signals at close *t* use data up to *t* only. Fills happen at the next bar
  (`harness/experiment.py::simulate` shifts weights by one bar).
- Walk-forward blocks with embargoed labels; stop/target checks are conservative within a bar.
- `tests/test_harness.py` pins this: changing a signal at *t* never changes returns before *t+1*.

## 2. Costs
Every test charges per-side cost on turnover (default 5 bps; 10 bps for e10 v1; 20 bps round trip
for e16a) in the same simulator. Gross numbers are reported only next to net numbers.
High-turnover strategies are where results die: e10 v1 gross Sharpe 0.80 -> net 0.54.

## 3. Same-window comparison
Strategy, SPY (total-return proxy), and controls are scored on identical dates.

## 4. Controls
- **Random entry / random pick**: same rule or same position count, random selection (20+ seeds).
- **Random pairs** (e12), **equal-weight universe**, and for e05 a random-pick book.
- Strict verdict (`harness/verdict.py`): PASS requires beating SPY **and** the random-pick median
  Sharpe **and** the equal-weight universe CAGR. Beating SPY alone is meaningless: 16/20 random
  3-stock picks beat SPY on a survivor-biased universe.

## 5. Overfit accounting
`registry/trials.jsonl` is append-only; every trial (including losers) is logged.
Deflated Sharpe (Bailey & López de Prado) uses the full trial count. A champion is promoted only if
it beats the previous champion on holdout **and** SPY.

## 6. Pre-registration
Grids, gates and kill criteria go into `experiments/*/SPEC.md` and `registry/experiments.yaml`
before the run. Killed lanes stay killed (e2, e8, e9, e12).

## 7. Survivorship
Universes of today's large caps inflate results (e10 v0: 8689x total return, Sharpe 2.08 -> verdict
BEAT). Re-run on point-in-time S&P 500 membership (e10 v1) gives Sharpe 0.54 vs SPY 0.97 -> LOSE.
Any single-stock result on the BROAD-40 universe is flagged SUSPECT.

## 8. Known limits
See README "Limitations".
