"""e18 shared helpers. Stdlib only."""
import json, os, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
SNAP = os.path.join(DATA, "snapshots.jsonl"); FWD = os.path.join(DATA, "forward.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (Trading Research Lab e18)"}
EVM = {"base": "8453", "ethereum": "1"}
CHAINS = {"solana", "base", "ethereum"}
_last = {}
def get(url, gap=1.0, tries=2):
    host = url.split("/")[2]
    for i in range(tries):
        w = _last.get(host, 0) + gap - time.time()
        if w > 0: time.sleep(w)
        _last[host] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as f:
                return json.loads(f.read())
        except Exception as e:
            err = e; time.sleep(5)
    print("fetch fail", url[:90], err); return None
def rows(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def append(p, rec):
    with open(p, "a") as f: f.write(json.dumps(rec) + "\n")
def fnum(x, d=None):
    try: return float(x)
    except Exception: return d
def best_pairs(chain, addrs):
    """{addr_lower: best pair dict} via DexScreener, batches of 30."""
    out = {}
    for i in range(0, len(addrs), 30):
        b = addrs[i:i+30]
        j = get(f"https://api.dexscreener.com/tokens/v1/{chain}/{','.join(b)}", 1.0)
        for p in (j or []):
            a = (p.get("baseToken") or {}).get("address", "").lower()
            liq = fnum((p.get("liquidity") or {}).get("usd"), 0)
            if a and (a not in out or liq > fnum((out[a].get("liquidity") or {}).get("usd"), 0)): out[a] = p
    return out
