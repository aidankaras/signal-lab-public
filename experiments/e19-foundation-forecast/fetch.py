import pandas as pd, yfinance as yf, os
TICK = "SPY QQQ IWM DIA XLK XLF XLE XLV XLY XLI XLP XLU TLT GLD".split()
out = {}
for t in TICK:
    d = yf.download(t, start="2018-01-01", auto_adjust=True, progress=False)
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d.index = pd.to_datetime(d.index).tz_localize(None); out[t] = d.dropna(how="all").sort_index()
    print(t, len(out[t]), out[t].index[-1].date())
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")   # gitignored
os.makedirs(DATA, exist_ok=True)
pd.to_pickle(out, os.path.join(DATA, "px.pkl"))
