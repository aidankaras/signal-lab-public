import pandas as pd


def spy_returns(close: pd.DataFrame) -> pd.Series:
    """S&P 500 proxy: SPY adjusted close (total return incl. dividends), no costs."""
    return close["SPY"].pct_change().fillna(0.0)
