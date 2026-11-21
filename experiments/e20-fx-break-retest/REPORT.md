# e20 report — FX break → retest → engulfing setup

**Verdict: LOSE.** The primary variant (3R target, one open position) averaged
**-0.04R per trade** on the 2022–2026 holdout (n = 152, t = -0.29,
win rate 26%) after spread and slippage. Development-period mean was
+0.16R, so the edge did not survive out of sample.

> **Errata (November 2026): look-ahead inside the 4H break candle.** `resample("4h")` labels
> bars by their start time, and the runner started the retest/trigger scan at that start, so
> it could enter while the break candle was still open; its invalidation check also read the
> close of a 4H bar that had not closed yet. In the committed trade lists, 29–31% of trades in
> every gated variant (and 54% of `abl_no_trigger`) have `entry_time` earlier than
> `break_time + 4h`. Across the ten committed trade lists those trades average +0.10R to +0.44R;
> the remaining trades average −0.07R to +0.09R (+0.19R for `abl_no_trigger`).
> The 80% truncation test below cannot detect this kind of within-bar leak.
>
> What this changes, computed from the committed CSVs by simply dropping the affected trades
> (an approximation; a corrected re-run would also find some later entries):
>
> | variant | holdout n (all) | holdout mean R (all) | holdout n (clean) | holdout mean R (clean) | t (clean) |
> |--|--|--|--|--|--|
> | primary_3R_1pos | 152 | -0.04 | 111 | -0.12 | -0.72 |
> | tp2R_1pos | 166 | +0.05 | 123 | -0.02 | -0.12 |
> | tp4R_1pos | 144 | +0.01 | 104 | -0.15 | -0.76 |
> | tp3R_perpair | 202 | -0.14 | 153 | -0.22 | -1.67 |
> | tp2R_perpair | 207 | -0.05 | 158 | -0.14 | -1.21 |
> | tp4R_perpair | 198 | -0.12 | 150 | -0.23 | -1.51 |
>
> Development period, `abl_no_trigger`: all 1,063 trades +0.30R (t 5.10); the 493 clean trades
> +0.19R (t 2.27). So the ablation that motivated the follow-up was inflated by the leak, and
> the follow-up tests (2003–14 and 2022+) ran on the same code and are tainted too.
> **The LOSE verdict stands** (the leak favoured the strategy, and every variant is lower without
> it). `run_e20.py` is fixed (scan starts at the break candle's close; invalidation uses only
> closed 4H bars); the numbers in this report are from the earlier code, pending a re-run.

## Setup
- Claim: a retail FX educator's "break, retest, engulfing candle" setup with
  trend filter, round-number areas of interest and day-of-week vetoes
  (rules coded exactly as pre-registered in `SPEC.md`; discretionary parts excluded).
- Data: Dukascopy free hourly BID candles, 10 pairs, 2015-01-01 → 2026-09-30
  (USDCHF, AUDCAD to 2026-08-31). 10–13 months per pair absent from the feed
  are recorded in `results/results.json` (`ranges`) and the fetch log.
- Split: development 2015–2021 (inspectable), holdout 2022-01-01 → end, scored once.
- Costs: per-pair spread (0.8–2.5 pips) + 0.5 pip slippage per side; 1% risk per trade.
- No-lookahead test: truncating the input at 80% reproduces the identical trade
  list up to the cut (78/78 trades) — passed. This test does not catch look-ahead inside a
  4H bar; see the errata above.

## Gates (holdout, primary variant; all must pass for BEAT)
| gate | requirement | result | pass |
|--|--|--|--|
| G1 | mean R > 0 and t ≥ 2 | -0.04R, t -0.29 | no |
| G2 | mean R > p95 of 2000 random-entry strategies | p95 +0.62R (control mean -0.11R; pre-fix control, see bug 5) | no |
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
5. **Random-entry control sizing** (found 2026-11-04 during the follow-up,
   e20v3) — `random_control` counted draws, not accepted trades, and silently
   skipped non-eligible draws (trigger hours 07–17, Mon–Wed), so each random
   strategy resolved far fewer trades than nominal and the G2 p95 (+0.62R) was
   inflated. Fixed to draw until exactly `n_per` trades resolve. This gate
   FAILED for the primary either way (the strategy mean is negative), so the
   LOSE verdict is unchanged; if anything the corrected control is a *lower*
   bar, making the LOSE more decisive.

## Follow-up (Nov 2026): the promising ablation was tested and failed
The `abl_no_trigger` variant (enter on retest touch, no engulfing candle) was
subsequently pre-registered and tested out-of-sample in two rounds:
untouched 2003–2014 data (n=624, +0.25R, t=3.34, but failed the pre-registered
gate and decays to ~0 by 2012–14) and 2022+ (n=296, +0.11R, t=1.01, LOSE vs
buy-and-hold S&P; ~0R in 2025–26). **The edge does not survive; FX lane
closed.** Details in the private lab registry, not published here. Note: these follow-up
runs used the runner with the within-bar look-ahead described in the errata, which favours
the strategy; the conclusion (no edge) is if anything stronger, but the follow-up numbers are
not reliable.

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
