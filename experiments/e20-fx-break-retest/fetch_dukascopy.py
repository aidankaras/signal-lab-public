"""Fetch Dukascopy free hourly candles (BID) for e20 pairs, 2015-01 .. latest.
Downloads monthly BID_candles_hour_1.bi5 via curl (urllib gets reset), parses
24-byte records (t_offset_sec, open, close, low, high, volume), writes one CSV
per pair under $E20_HOME/data/ (default: this folder). UTC timestamps.
"""
import lzma, struct, subprocess, sys, os, time
import pandas as pd

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD",
         "NZDUSD", "GBPJPY", "GBPCHF", "AUDCAD"]
START = (2015, 1)
END = (2026, 10)  # current month; later months 404 and are skipped
HOME = os.environ.get("E20_HOME", os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HOME, "data")
CACHE = os.path.join(HOME, "cache")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)


def fetch_month(pair, y, m):
    """Return DataFrame or None if missing."""
    fn = f"{CACHE}/{pair}_{y}_{m:02d}.bi5"
    if not os.path.exists(fn):
        url = f"https://datafeed.dukascopy.com/datafeed/{pair}/{y}/{m-1:02d}/BID_candles_hour_1.bi5"
        # serial + polite: the feed returns 503 when hammered in parallel
        for attempt in range(6):
            r = subprocess.run(["curl", "-s", "-o", fn, "-w", "%{http_code}",
                                "--max-time", "60", "-A", "Mozilla/5.0", url],
                               capture_output=True, text=True)
            code = r.stdout.strip()
            if code == "200" and os.path.getsize(fn) > 0:
                break
            if os.path.exists(fn):
                os.remove(fn)
            if code == "404":
                return None
            time.sleep(min(60, 5 * 2 ** attempt))
        else:
            return None
        time.sleep(1.5)
    if not os.path.exists(fn) or os.path.getsize(fn) == 0:
        return None
    try:
        dec = lzma.LZMADecompressor().decompress(open(fn, "rb").read())
    except Exception:
        os.remove(fn)
        return None
    if len(dec) % 24 != 0 or len(dec) == 0:
        return None
    pt = 1000.0 if "JPY" in pair else 100000.0
    base = pd.Timestamp(f"{y}-{m:02d}-01", tz="UTC")
    # records are interleaved: 5 big-endian int32 (t, o, c, l, h) + 1 float32 vol
    rows = []
    for t, o, c, l, h, v in struct.iter_unpack(">5if", dec):
        if h == 0 and l == 0:
            continue
        rows.append((base + pd.Timedelta(seconds=t), o / pt, c / pt, l / pt, h / pt, v))
    df = pd.DataFrame(rows, columns=["time", "open", "close", "low", "high", "vol"])
    return df


def main():
    report = {}
    for pair in PAIRS:
        frames, missing = [], []
        y, m = START
        while (y, m) <= END:
            df = fetch_month(pair, y, m)
            if df is None:
                missing.append(f"{y}-{m:02d}")
            else:
                frames.append(df)
            m += 1
            if m > 12:
                y, m = y + 1, 1
        if not frames:
            report[pair] = "NO DATA"
            continue
        full = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
        full.to_csv(f"{OUT}/{pair}_h1.csv", index=False)
        report[pair] = dict(rows=len(full), first=str(full.time.iloc[0]), last=str(full.time.iloc[-1]),
                            missing_months=len(missing), missing=missing[:6])
        print(pair, report[pair], flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
