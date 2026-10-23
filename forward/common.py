"""Shared helpers for the e16b/e17 forward arm. Stdlib only (runs on the VPS)."""
import json, os, urllib.request, datetime as dt
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
CALLS = os.path.join(HERE, "e16b_calls.jsonl"); FILLS = os.path.join(HERE, "e16b_alpaca.jsonl")
NY = ZoneInfo("America/New_York")
E17_UNIVERSE = ["SPY","QQQ","IWM","DIA","XLK","XLF","XLE","XLV","XLY","XLI","XLP","XLU","TLT","GLD"]
UA = {"User-Agent": "Mozilla/5.0 (Trading Research Lab)"}
def get(url, headers=None, data=None, method=None):
    r = urllib.request.Request(url, headers={**UA, **(headers or {})}, data=data, method=method)
    with urllib.request.urlopen(r, timeout=20) as f: return f.read()
def chart(sym, rng="3mo"):
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?range={rng}&interval=1d"))["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    rows = [(dt.datetime.fromtimestamp(t, NY).date().isoformat(), o, c) for t, o, c in zip(j["timestamp"], q["open"], q["close"]) if c is not None]
    return j["meta"], rows
def alpaca():
    """Alpaca paper-trading credentials come from env vars only:
    APCA_API_KEY_ID / APCA_API_SECRET_KEY (and optional APCA_API_BASE_URL)."""
    e = {k: os.environ.get(k, "") for k in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "APCA_API_BASE_URL")}
    assert e["APCA_API_KEY_ID"] and e["APCA_API_SECRET_KEY"], "set APCA_API_KEY_ID / APCA_API_SECRET_KEY env vars"
    base = e.get("APCA_API_BASE_URL") or "https://paper-api.alpaca.markets"
    base = base.rstrip("/").removesuffix("/v2")
    assert "paper" in base, "refusing: not a paper endpoint"
    h = {"APCA-API-KEY-ID": e["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": e["APCA_API_SECRET_KEY"], "Content-Type": "application/json"}
    def call(path, body=None, method=None):
        return json.loads(get(base + path, h, json.dumps(body).encode() if body else None, method) or b"null")
    return call
def append(path, rec):
    with open(path, "a") as f: f.write(json.dumps(rec) + "\n")
def rows(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []
