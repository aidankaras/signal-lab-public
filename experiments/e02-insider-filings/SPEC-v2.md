# e2 v2 — big-dollar insider buy clusters, out-of-sample 2011–2017 (pre-registered 2026-10-22, before download/run)

Origin: unregistered hint from v1 — holdout (2023+) top-$ tercile of clusters +1.47% mean 21d abnormal (n=56, median -0.13%, outlier-driven).
Untouched data: SEC Form 3/4/5 sets 2011q1–2017q4 (never used by e2 v0/v1/e6). PIT S&P 500 membership from 2011-06-02.
Rule fixed from v1, NO tuning: v1 definition (P buys >=$10k, >=2 owners in 30d, 63d dedupe, entry next close, 21d hold,
abnormal vs SPY, 20bps cost) AND 30-day cluster buy total >= $1,262,258 (v1 holdout tercile cutoff, frozen).
Window: filing dates 2011-07-01 .. 2017-12-31 (one test window, no train split).
Gates (ALL): mean net abnormal > 0; month-clustered t > 2; mean > random-PIT-member control p95 (2000 draws); n >= 60.
Also reported: median (if mean passes but median <= 0, flag as outlier-driven in the write-up).
Fail -> insider lane stays closed permanently.
