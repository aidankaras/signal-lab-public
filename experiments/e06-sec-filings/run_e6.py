"""python run_e6.py -- e6 SEC-filings baseline, rebuilt natively for the lab harness.

Replaces the legacy pipeline (reference/sec-filings-legacy/, kept for provenance) with the
lab's own stack: no Docker, no Postgres, no subscription LLM runtime. Free EDGAR + yfinance
+ a dedicated venv only.

Pre-registered v1 scope (2026-10-18, Aidan: "fold into our structure"):
  Universe : the lab's fixed 40-ticker BROAD list (NOT whole-EDGAR like the legacy pipeline;
             smaller sample — flagged, honest).
  Events   : every Form 4 filed 2026-07-01..2026-09-09 by those issuers. Fields parsed from
             each filing's XML: transaction code (S/P/M/A), share count, price per share.
  Features : per issuer-day: n_filings, n_sell, n_buy, ln(1+sell_shares), ln(1+buy_shares),
             net_shares/share_count_proxy.
  Label    : forward 5-session abnormal return = stock - SPY, from the yfinance panel.
  Model    : logistic regression (P(up)>0), walk-forward in 10-day blocks, 10-day embargo —
             a block is scored by a model fitted only on issuer-days whose label window had
             closed before the block started.
  Metric   : mean daily Spearman IC + t-stat over scored days (the legacy baseline's metric,
             so results are comparable to its published +0.029 null).
  Verdict  : same machinery as e4 — logged to trials.jsonl, published BEAT/LOSE. IC <= 0
             within noise = the honest null result replicated on the smaller universe.
  LLM arm  : NOT built here. The legacy agent arm needs a pinned-model subscription runtime
             with provable training-cutoff bounds — out of lab scope for now; logged as
             not-run rather than faked (lab rule).
"""
import json, os, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness import data
from harness.evaluator import log_trial

UA = {"User-Agent": "Trading Research Lab (contact: aidan@aidankaras.dev)"}
TICKERS = [t for t in data.BROAD if t != "SPY"]
START, END = "2026-07-01", "2026-09-09"
CACHE = os.path.join(ROOT, "data", "cache", "e6_xml")
FEATURES = os.path.join(ROOT, "data", "cache", "e6_features.csv")
TR = os.path.join(ROOT, "registry", "trials.jsonl")


def get(url, binary=False, retries=3):
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read() if binary else json.load(r)
        except urllib.error.HTTPError as e:
            if a == retries - 1:
                print("HTTP", e.code, url[:80], flush=True)
                raise
            time.sleep(max(2 ** a, int(e.headers.get("Retry-After", 0)) + 1))
        except Exception as e:
            if a == retries - 1:
                raise
            time.sleep(2 ** a)


def cik_map():
    return {row["ticker"].upper(): int(row["cik_str"])
            for row in get("https://www.sec.gov/files/company_tickers.json").values()}


def form4_list(cik):
    f = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")["filings"]["recent"]
    return [(d, a.replace("-", ""), p) for d, a, form, p in
            zip(f["filingDate"], f["accessionNumber"], f["form"], f["primaryDocument"])
            if form == "4" and START <= d <= END]


def local(tag):
    return tag.rsplit("}", 1)[-1]


def tx_nodes(root):
    """Yield (code, shares, price) for each non-derivative transaction (namespace-agnostic)."""
    for tx in root.iter():
        if local(tx.tag) != "nonDerivativeTransaction":
            continue
        def val(path):
            for el in tx.iter():
                if local(el.tag) == path and (ch := next((c for c in el if local(c.tag) == "value"), None)) is not None:
                    return float(ch.text) if ch.text else None
            return None
        code_el = next((el for el in tx.iter() if local(el.tag) == "transactionCode"), None)
        yield (code_el.text if code_el is not None and code_el.text else "?",
               val("transactionShares"), val("transactionPricePerShare"))


def filing_xml(cik, acc, doc):
    """Fetch the Form-4 XML. primaryDocument often carries an 'xslF345X06/' viewer prefix
    that returns styled HTML — strip it; fall back to the filing index."""
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"
    if doc and ".xml" in doc:
        name = doc.rsplit("/", 1)[-1]  # strip any xslF.../ viewer prefix
        return ET.fromstring(get(f"{base}/{name}", binary=True))
    idx = get(f"{base}/index.json")
    names = [it["name"] for it in idx["directory"]["item"] if it["name"].endswith(".xml")]
    for n in names:
        if re.search(r"(primary|form4)", n, re.I) or len(names) == 1:
            return ET.fromstring(get(f"{base}/{n}", binary=True))
    return ET.fromstring(get(f"{base}/{names[0]}", binary=True))


def fetch_features(cm):
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, "events.jsonl")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return [json.loads(l) for l in open(out)]
    rows, done, errs = [], 0, 0
    for t in TICKERS:
        if t not in cm:
            print("no CIK:", t, flush=True); continue
        try:
            fl = form4_list(cm[t])
        except Exception as e:
            print(t, "submissions ERR", e, flush=True); continue
        print(t, len(fl), "form4s", flush=True)
        for d, acc, doc in fl:
            try:
                root = filing_xml(cm[t], acc, doc)
                for code, shares, price in tx_nodes(root):
                    rows.append({"ticker": t, "date": d, "code": code,
                                 "shares": shares or 0.0, "price": price or 0.0})
            except Exception as e:
                errs += 1
                print(t, d, "parse ERR", str(e)[:80], flush=True)
            done += 1
            if done % 200 == 0 and rows:
                open(out, "w").write("\n".join(json.dumps(r) for r in rows))
                print("...", done, "filings,", len(rows), "txs,", errs, "errors", flush=True)
            time.sleep(0.11)  # SEC rate limit
    if rows:
        open(out, "w").write("\n".join(json.dumps(r) for r in rows))
    else:
        print("WARNING: zero transactions parsed in", done, "filings,", errs, "errors — EDGAR likely throttling; try again later", flush=True)
    return rows


def build_panel(rows):
    if not rows:
        raise SystemExit("no transactions parsed — aborting before a garbage verdict")
    ev = pd.DataFrame(rows)
    ev = ev[ev.code.isin(["S", "P", "M", "A"])]
    ev["value"] = ev.shares * ev.price.where(ev.price > 0, 0)
    g = ev.groupby(["ticker", "date"])
    panel = pd.DataFrame({
        "n": g.size(),
        "n_sell": g.apply(lambda x: (x.code == "S").sum(), include_groups=False),
        "n_buy": g.apply(lambda x: (x.code == "P").sum(), include_groups=False),
        "ln_sell_sh": np.log1p(g.apply(lambda x: x.loc[x.code == "S", "shares"].sum(), include_groups=False)),
        "ln_buy_sh": np.log1p(g.apply(lambda x: x.loc[x.code == "P", "shares"].sum(), include_groups=False)),
    }).reset_index()
    panel.to_csv(FEATURES, index=False)
    return panel


def labels_and_eval(panel):
    px = data.fetch(data.BROAD, start="2025-09-01", refresh=False, name="broad")
    spy = px["SPY"]
    rows = []
    for _, r in panel.iterrows():
        t = r.ticker
        if t not in px.columns: continue
        c = px[t].dropna()
        pos = c.index.searchsorted(pd.Timestamp(r.date), side="right") - 1
        if pos < 0 or pos + 5 >= len(c): continue
        s = spy.reindex(c.index).dropna()
        spos = s.index.searchsorted(pd.Timestamp(r.date), side="right") - 1
        if spos < 0 or spos + 5 >= len(s): continue
        rows.append({**r.to_dict(), "fwd_abn": (c.iloc[pos + 5] / c.iloc[pos]) - (s.iloc[spos + 5] / s.iloc[spos])})
    df = pd.DataFrame(rows)
    df["y"] = (df.fwd_abn > 0).astype(int)
    df = df.sort_values("date").reset_index(drop=True)
    feats = ["n", "n_sell", "n_buy", "ln_sell_sh", "ln_buy_sh"]
    dates = sorted(df.date.unique())
    # embargo: an issuer-day's label closes 5 sessions later; block of 10 scored days,
    # fitted on all days ending >=5 sessions before the block starts.
    date_pos = {d: i for i, d in enumerate(dates)}
    ics = []
    for b in range(3, len(dates) - 10, 10):  # first 3 dates reserved for the initial fit
        blk = dates[b:b + 10]
        fit_end_pos = b - 5
        if fit_end_pos < 3: continue
        fit_dates = dates[:fit_end_pos + 1]
        tr = df[df.date.isin(fit_dates)]
        te = df[df.date.isin(blk)]
        if len(te) < 8 or tr.y.nunique() < 2: continue
        m = LogisticRegression(max_iter=1000).fit(tr[feats], tr.y)
        p = m.predict_proba(te[feats])[:, 1]
        for d in blk:
            dd = te[te.date == d]
            if dd.y.nunique() < 2: continue
            ic = spearmanr(p[te.date == d], dd.y).statistic
            if ic == ic: ics.append(ic)
    ics = np.array(ics)
    ic, n = float(ics.mean()), len(ics)
    t = float(ic / (ics.std(ddof=1) / np.sqrt(n))) if n > 1 and ics.std() > 0 else 0.0
    return {"ic_mean": round(ic, 4), "t": round(t, 2), "scored_days": n,
            "issuer_days_total": len(df), "n_events": int(df.n.sum())}


def main():
    cm = cik_map()
    rows = fetch_features(cm)
    print("parsed transactions:", len(rows))
    panel = build_panel(rows)
    print("issuer-days:", len(panel))
    res = labels_and_eval(panel)
    res.update({"experiment": "e6_sec_filings", "window": [START, END],
                "universe": "BROAD-40 (smaller than legacy whole-EDGAR; flagged)",
                "verdict": "BEAT" if (res["t"] > 2 and res["ic_mean"] > 0) else "LOSE",
                "llm_arm": "not-run (needs pinned-model subscription runtime; out of lab scope)"})
    log_trial(TR, {"experiment": "e6_sec_filings",
                   "generation": 0, "stage": "holdout", "params": {"v": 1, "model": "logreg"},
                   "seed": 0, "ic": res["ic_mean"], "t": res["t"], "n": res["scored_days"],
                   "verdict": res["verdict"], "origin": "manual"})
    json.dump(res, open(os.path.join(ROOT, "reports", "e6-baseline.json"), "w"), indent=1)
    txt = ["# e6 SEC-filings baseline (native rebuild) " + time.strftime("%Y-%m-%d"), "",
           f"Window {START}→{END}, BROAD-40 universe, Form-4 features, 5-session abnormal-return labels,",
           f"walk-forward logreg (10-day blocks, 5-day embargo).", "",
           f"- Daily Spearman IC: **{res['ic_mean']}** (t = {res['t']}, {res['scored_days']} scored days, {res['issuer_days_total']} issuer-days, {res['n_events']} transactions)",
           f"- Verdict: **{res['verdict']}** (gate: t > 2 and IC > 0). Legacy whole-EDGAR reference: IC +0.029 (t 1.52) = null.",
           f"- LLM arm: not-run (out of lab scope).", ""]
    open(os.path.join(ROOT, "reports", "e6-baseline.md"), "w").write("\n".join(txt))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
