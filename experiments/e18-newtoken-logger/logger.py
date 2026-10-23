"""e18 snapshot logger: discover new tokens, fetch security, apply frozen filter, append once per token."""
import time, datetime as dt
from common import *
MAXC = 60
def top10(holders):
    s = 0.0
    for h in (holders or [])[:10]:
        t = (h.get("tag") or "").lower()
        if h.get("is_locked") in (1, "1") or "dead" in t or "burn" in t: continue
        s += fnum(h.get("percent"), 0)
    return s
def eval_evm(s):
    f = {"honeypot": s.get("is_honeypot"), "buy_tax": fnum(s.get("buy_tax"), 0), "sell_tax": fnum(s.get("sell_tax"), 0),
         "open_source": s.get("is_open_source"), "hidden_owner": s.get("hidden_owner"),
         "takeback": s.get("can_take_back_ownership"), "cannot_sell_all": s.get("cannot_sell_all"),
         "top10": round(top10(s.get("holders")), 4), "holder_count": s.get("holder_count")}
    lp = s.get("lp_holders") or []
    if lp:
        f["lp_locked_frac"] = round(sum(fnum(h.get("percent"), 0) for h in lp if h.get("is_locked") in (1, "1") or "dead" in (h.get("tag") or "").lower()), 4)
    why = []
    if f["honeypot"] != "0": why.append("honeypot")
    if not (f["buy_tax"] < 0.10 and f["sell_tax"] < 0.10): why.append("tax")
    if f["cannot_sell_all"] == "1": why.append("cannot_sell_all")
    if f["open_source"] != "1": why.append("not_open_source")
    if f["hidden_owner"] == "1" or f["takeback"] == "1": why.append("owner_risk")
    if f["top10"] >= 0.50: why.append("top10")
    if "lp_locked_frac" in f and f["lp_locked_frac"] < 0.50: why.append("lp_unlocked")
    return f, why
def eval_sol(s):
    st = lambda k: (s.get(k) or {}).get("status")
    f = {"mintable": st("mintable"), "freezable": st("freezable"), "non_transferable": s.get("non_transferable"),
         "transfer_fee": bool(s.get("transfer_fee")), "top10": round(top10(s.get("holders")), 4) if s.get("holders") else None}
    why = []
    if f["mintable"] != "0": why.append("mintable")
    if f["freezable"] != "0": why.append("freezable")
    if f["non_transferable"] != "0": why.append("non_transferable")
    if f["transfer_fee"]: why.append("transfer_fee")
    if f["top10"] is not None and f["top10"] >= 0.50: why.append("top10")
    return f, why
def main():
    seen = {r["id"] for r in rows(SNAP)}
    cand = {}
    for u in ("https://api.dexscreener.com/token-profiles/latest/v1", "https://api.dexscreener.com/token-boosts/latest/v1"):
        for c in (get(u, 1.0) or []):
            if c.get("chainId") in CHAINS and c.get("tokenAddress"):
                cand.setdefault(c["chainId"], set()).add(c["tokenAddress"])
    now = time.time(); n_ok = n_app = 0; new = []
    for ch, addrs in cand.items():
        addrs = [a for a in addrs if f"{ch}:{a.lower()}" not in seen][:MAXC]
        bp = best_pairs(ch, addrs) if addrs else {}
        for a in addrs:
            p = bp.get(a.lower())
            if not p or not p.get("pairCreatedAt"): continue
            age_h = (now - p["pairCreatedAt"] / 1000) / 3600
            if not (0 <= age_h < 24): continue
            new.append((ch, a, p, age_h))
    for ch, a, p, age_h in new[:MAXC]:
        liq = fnum((p.get("liquidity") or {}).get("usd"), 0)
        if ch in EVM: url = f"https://api.gopluslabs.io/api/v1/token_security/{EVM[ch]}?contract_addresses={a.lower()}"
        else: url = f"https://api.gopluslabs.io/api/v1/solana/token_security?contract_addresses={a}"
        j = get(url, 2.5); res = ((j or {}).get("result") or {})
        s = res.get(a.lower()) or res.get(a)
        if not s: flags, why = {}, ["no_security_data"]
        else: flags, why = (eval_evm if ch in EVM else eval_sol)(s)
        if liq < 50000: why.insert(0, "liquidity<50k")
        ok = not why
        append(SNAP, {"id": f"{ch}:{a.lower()}", "chain": ch, "address": a, "symbol": (p.get("baseToken") or {}).get("symbol"),
            "ts": int(now), "iso": dt.datetime.now(dt.timezone.utc).isoformat(), "pair": p.get("pairAddress"), "dex": p.get("dexId"),
            "age_h": round(age_h, 2), "price_usd": fnum(p.get("priceUsd")), "liq_usd": liq,
            "vol24": fnum((p.get("volume") or {}).get("h24")), "fdv": fnum(p.get("fdv")), "flags": flags,
            "group": "APPROVED" if ok else "CONTROL", "fail": why})
        n_ok += 1; n_app += ok
    print(f"candidates={sum(len(v) for v in cand.values())} new_in_24h={len(new)} logged={n_ok} approved={n_app} control={n_ok-n_app}")
if __name__ == "__main__": main()
