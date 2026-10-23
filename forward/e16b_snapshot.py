"""Print the pre-open snapshot the agent sees (JSON). Prior-day data + live overseas/futures quotes only."""
import json, re, statistics as st, datetime as dt
from common import chart, get, E17_UNIVERSE, NY
def rets(rows):
    c = [r[2] for r in rows]; d = [c[i]/c[i-1]-1 for i in range(1, len(c))]
    return {"last_close_date": rows[-1][0], "ret1": round(d[-1], 4), "ret5": round(c[-1]/c[-6]-1, 4), "ret20": round(c[-1]/c[-21]-1, 4),
            "vol20": round(st.stdev(d[-20:]), 4)}
today = dt.datetime.now(NY).date().isoformat(); out = {"asof_ny": dt.datetime.now(NY).isoformat(timespec="minutes"), "etfs": {}}
for s in E17_UNIVERSE:
    m, r = chart(s); r = [x for x in r if x[0] < today]; out["etfs"][s] = rets(r)
for s, k in [("^VIX", "vix"), ("^N225", "nikkei"), ("^GDAXI", "dax"), ("ES=F", "es_fut")]:
    try:
        m, r = chart(s, "1mo"); px, pc = m.get("regularMarketPrice"), m.get("chartPreviousClose")
        prev = [x for x in r if x[0] < today]
        out[k] = {"last": px, "chg_vs_prev_close": round(px / prev[-1][2] - 1, 4) if prev else None}
    except Exception as e: out[k] = {"error": str(e)[:80]}
try:
    x = get("https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY,QQQ,^GSPC&region=US&lang=en-US").decode("utf-8", "ignore")
    out["headlines"] = [re.sub(r"<!\[CDATA\[|\]\]>", "", t).strip() for t in re.findall(r"<item>.*?<title>(.*?)</title>", x, re.S)][:12]
except Exception as e: out["headlines"] = [f"unavailable: {str(e)[:60]}"]
print(json.dumps(out, indent=1))
