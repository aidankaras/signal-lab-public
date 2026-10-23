# e19 — foundation-model forecast experiment

Zero-shot Kronos-small and TimesFM-2.5-200m on 14 ETFs vs SPY buy-and-hold.
**Verdict: 0 BEAT / 12 LOSE** — see `REPORT.md`.

## Data (not committed)

- `data/px.pkl` — daily OHLCV via `fetch.py` (yfinance).
- `data/fc_kronos.csv`, `data/fc_timesfm.csv` — model forecast outputs, each ~300 KB,
  gitignored. Regenerate with:
  `python forecast.py kronos data/fc_kronos.csv` and
  `python forecast.py timesfm data/fc_timesfm.csv`
  (needs the Kronos / TimesFM packages and a model checkpoint; run offline).

Then: `python analyze.py data/px.pkl data/fc_kronos.csv data/fc_timesfm.csv e19.json`
