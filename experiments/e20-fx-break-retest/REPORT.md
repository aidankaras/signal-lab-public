# e20 report — FX break → retest → engulfing setup

**Verdict: LOSE.** The primary variant (3R target, one open position) averaged
**-0.04R per trade** on the 2022–2026 holdout (n = 152, t = -0.29,
win rate 26%) after spread and slippage. Development-period mean was
+0.16R, so the edge did not survive out of sample.

## Setup
- Claim: a retail FX educator's "break, retest, engulfing candle" setup with
  trend filter, round-number areas of interest and day-of-week vetoes
  (rules coded exactly as pre-registered in `SPEC.md`; discretionary parts excluded).
- Data: Dukascopy free hourly BID candles, 10 pairs, 2015-01-01 → 2026-09-30
  (USDCHF, AUDCAD to 2026-08-31). 10–13 months per pair absent from the feed
  are recorded in `results/results.json` (`ranges`) and the fetch log.
- Split: development 2015–2021 (inspectable), holdout 2022-01-01 → end, scored once.
- Costs: per-pair spread (0.8–3 pips) + 0.5 pip slippage per side; 1% risk per trade.
- No-lookahead test: truncating the input at 80% reproduces the identical trade
  list up to the cut (78/78 trades) — passed.

## Gates (holdout, primary variant; all must pass for BEAT)
| gate | requirement | result | pass |
|--|--|--|--|
| G1 | mean R > 0 and t ≥ 2 | -0.04R, t -0.29 | no |
| G2 | mean R > p95 of 2000 random-entry strategies | p95 +0.62R (control mean -0.11R) | no |
| G3 | ret/vol > MA20/100 trend-follow baseline | -0.18 vs -0.85 | yes (baseline also loses money) |
| G4 | ≥ 60 holdout trades | 152 | yes |

## All variants (pre-registered: 3 targets × 2 position rules)
| variant | n dev | mean R dev | n holdout | mean R holdout | t holdout | win holdout |
|--|--|--|--|--|--|--|
| primary_3R_1pos | 209 | +0.16 | 152 | -0.04 | -0.29 | 26% |
| tp2R_1pos | 220 | +0.05 | 166 | +0.05 | +0.40 | 38% |
| tp4R_1pos | 190 | +0.33 | 144 | +0.01 | +0.04 | 22% |
| tp3R_perpair | 266 | +0.19 | 202 | -0.14 | -1.16 | 24% |
| tp2R_perpair | 267 | +0.04 | 207 | -0.05 | -0.46 | 35% |
| tp4R_perpair | 258 | +0.29 | 198 | -0.12 | -0.82 | 20% |

No variant reaches t ≥ 2 on the holdout; 4 of 6 are negative. With 10 trials
(Bonferroni α ≈ 0.0045) even a single nominal pass would not have been enough.

## Ablations (development period only — reported, not gated)
| ablation | n | mean R | Sharpe |
|--|--|--|--|
| abl_no_round | 798 | +0.12 | 0.70 |
| abl_no_trigger | 1063 | +0.30 | 1.94 |
| abl_no_trend | 1869 | +0.03 | 0.32 |
| abl_no_vetoes | 756 | +0.16 | 0.92 |

Removing the engulfing trigger (enter on the retest touch) looks strongest on
the development data (Sharpe 1.94). It is one of several post-hoc variants on
in-sample data and is **not** a finding; it would need its own pre-registered
out-of-sample test.

## Bugs found and fixed before trusting the numbers
Disclosed because the fixes touched the runner after pre-registration. None
changes a trading rule; the primary trade list is byte-identical before/after.
1. **Timezone crash** — tz-naive numpy timestamps were passed to `tz_convert`
   under pandas 3; now localized to UTC explicitly.
2. **Random-entry control** pooled stop distances in raw price units across
   JPY and non-JPY pairs (a ~100× scale mismatch), producing an implausible
   −2.05R control mean. Distances are now sampled in pips. Control mean
   −0.11R, p95 +0.62R.
3. **Trend-follow baseline** grouped the concatenated series by pair instead of
   by date, yielding ten "days" and a −100%/yr figure. Now averaged across
   pairs per date: −2.4%/yr at 2.8% vol.
4. **G3** compared the full-period strategy curve against a holdout-only
   baseline; now both use the holdout, as the SPEC requires.

## Caveats
- 152 holdout trades is enough to reject a strong edge but not a small one
  (±0.28R 95% interval around the mean).
- Hourly bars: when stop and target are hit in the same bar, the stop is
  assumed first (conservative).
- Discretionary elements of the original method were not tested.

## Reproduce
```
pip install -r ../../requirements.txt
python fetch_dukascopy.py      # or ./fetch_curl.sh first if the feed times out
python run_e20.py results
```
