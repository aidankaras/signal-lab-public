"""Free data layer (yfinance) + data-quality audit."""
import os

import pandas as pd

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "XOM", "JPM", "JNJ", "PG"]
# e4 cross-section: 40 large caps across sectors + SPY. Survivor-biased (today's names) - flagged in reports.
BROAD = ["SPY", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "BRK-B", "JPM", "V", "MA", "UNH",
         "JNJ", "PFE", "MRK", "ABT", "LLY", "XOM", "CVX", "COP", "PG", "KO", "PEP", "WMT", "COST", "HD",
         "MCD", "NKE", "DIS", "CSCO", "ORCL", "INTC", "IBM", "BA", "CAT", "HON", "GE", "T", "VZ", "NEE"]
START = "2005-01-01"


def fetch(tickers=UNIVERSE, start=START, refresh=False, name="prices"):
    """Adjusted close panel, cached to data/cache/prices.csv."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name + ".csv")
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    import yfinance as yf
    d = yf.download(list(tickers), start=start, auto_adjust=True, progress=False)["Close"]
    d = d.dropna(how="all").sort_index()
    d.to_csv(path)
    return d


def audit(close: pd.DataFrame) -> dict:
    """M1 data-quality audit. Flags gaps, stale prices, jumps and the survivorship caveat."""
    rep = {"rows": len(close), "start": str(close.index[0].date()), "end": str(close.index[-1].date()),
           "tickers": {}}
    bd = pd.bdate_range(close.index[0], close.index[-1])
    rep["missing_business_days"] = int(len(bd.difference(close.index)))  # includes holidays
    for t in close.columns:
        s = close[t]
        r = s.pct_change()
        rep["tickers"][t] = {
            "first_valid": str(s.first_valid_index().date()),
            "nan_after_start": int(s.loc[s.first_valid_index():].isna().sum()),
            "max_abs_daily_move": round(float(r.abs().max()), 3),
            "n_moves_gt_20pct": int((r.abs() > 0.20).sum()),
            "stale_runs_ge5": int(((s.diff() == 0).rolling(5).sum() >= 5).sum()),
        }
    rep["survivorship_warning"] = ("Universe = today's large caps (survivors). Results on single stocks "
                                   "are biased upward; treat SPY/QQQ results as the clean ones.")
    return rep
