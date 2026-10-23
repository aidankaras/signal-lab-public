"""e2 v1: open-market insider buy clusters on PIT S&P 500. See SPEC-v1.md (pre-registered)."""
import glob, json, os, sys, zipfile, bisect
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from harness.data import CACHE
from harness.evaluator import log_trial
EDGAR = os.path.expanduser(os.environ.get("E2_EDGAR","~/tlab/edgar")); MINUSD=float(os.environ.get("E2_MINUSD","0")); VER=os.environ.get("E2_VER","v1"); H, COST, NCTRL, SEED = 21, 0.002, 2000, 0
E10 = os.path.join(ROOT, "experiments", "e10-survivorship")

def load_buys():
    out = []
    for z in sorted(glob.glob(os.path.join(EDGAR, "20??q?_form345.zip"))):
        with zipfile.ZipFile(z) as f:
            rd = lambda n, cols: pd.read_csv(f.open(n), sep="\t", usecols=cols, dtype=str, on_bad_lines="skip")
            s = rd("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERTRADINGSYMBOL"])
            o = rd("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
            t = rd("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE"])
        s = s[s.DOCUMENT_TYPE.isin(["4", "4/A"])]
        t = t[t.TRANS_CODE == "P"].copy()
        t["usd"] = pd.to_numeric(t.TRANS_SHARES, errors="coerce") * pd.to_numeric(t.TRANS_PRICEPERSHARE, errors="coerce")
        t = t.groupby("ACCESSION_NUMBER", as_index=False).usd.sum()
        o = o.drop_duplicates("ACCESSION_NUMBER")
        out.append(s.merge(t, on="ACCESSION_NUMBER").merge(o, on="ACCESSION_NUMBER"))
    b = pd.concat(out).drop_duplicates("ACCESSION_NUMBER")
    b["date"] = pd.to_datetime(b.FILING_DATE, format="%d-%b-%Y", errors="coerce")
    b["ticker"] = b.ISSUERTRADINGSYMBOL.str.upper().str.strip().str.replace(".", "-", regex=False)
    return b[(b.usd >= 1e4) & b.date.notna()][["date", "ticker", "RPTOWNERCIK", "usd"]]

def main():
    px = pd.read_csv(os.path.join(CACHE, "sp500pit.csv"), index_col=0, parse_dates=True)
    px = px[[c for c in px if not c.startswith("VOL__")]].loc[os.environ.get("E2_PXSTART","2017-12-01"):]
    mem = json.load(open(os.path.join(E10, "sp500_membership.json"))); md = sorted(mem)
    ms = {d: {x.replace(".", "-") for x in v} for d, v in mem.items()}
    member = lambda d: ms[md[bisect.bisect_right(md, d.strftime("%Y-%m-%d")) - 1]]
    idx = px.index; spy = px["SPY"]; last = px.ffill()
    def abn(t, i):  # entry at idx[i] close, exit idx[i+H]
        if i + H >= len(idx) or pd.isna(px[t].iloc[i]): return np.nan
        return last[t].iloc[i + H] / px[t].iloc[i] - 1 - (spy.iloc[i + H] / spy.iloc[i] - 1) - COST
    b = load_buys(); b = b[b.ticker.isin(px.columns)]
    print("qualifying P filings in price universe:", len(b))
    ev = {"cluster": [], "single": []}
    for t, g in b.sort_values("date").groupby("ticker"):
        lastc = lasts = -10 ** 9
        for d in g.date.unique():
            d = pd.Timestamp(d)
            if t not in member(d): continue
            i = idx.searchsorted(d, side="right")
            if i >= len(idx): continue
            w = g[(g.date > d - pd.Timedelta(days=30)) & (g.date <= d)]
            usd = float(w.usd.sum())
            if i - lasts >= H: ev["single"].append((d, t, i, usd)); lasts = i
            if w.RPTOWNERCIK.nunique() >= 2 and usd >= MINUSD and i - lastc >= 63:
                ev["cluster"].append((d, t, i, usd)); lastc = i
    rng = np.random.default_rng(SEED); res = {}
    for k, rows in ev.items():
        df = pd.DataFrame(rows, columns=["date", "ticker", "i", "usd"])
        df["abn"] = [abn(t, i) for t, i in zip(df.ticker, df.i)]; df = df.dropna(subset=["abn"])
        df["ho"] = df.date >= os.environ.get("E2_HOSTART","2023-01-01")
        tr, ho = df[~df.ho], df[df.ho]
        m = ho.groupby(ho.date.dt.to_period("M")).abn.mean()
        t_ho = float(m.mean() / m.std() * len(m) ** .5) if len(m) > 2 and m.std() > 0 else 0.0
        pools = {}
        for i in ho.i.unique():
            d = idx[i]; pools[i] = [c for c in member(d) if c in px.columns and pd.notna(px[c].iloc[i])]
        cm = []
        for _ in range(NCTRL if k == "cluster" else 300):
            v = [abn(pools[i][rng.integers(len(pools[i]))], i) for i in ho.i if pools[i]]
            cm.append(np.nanmean(v))
        p95 = float(np.nanpercentile(cm, 95)) if cm else np.nan
        r = {"n_train": len(tr), "n_ho": len(ho), "train_mean": float(tr.abn.mean()), "ho_mean": float(ho.abn.mean()), "ho_median": float(ho.abn.median()),
             "ho_t_month": t_ho, "ctrl_mean": float(np.nanmean(cm)), "ctrl_p95": p95,
             "ho_terciles": ho.groupby(pd.qcut(ho.usd, 3, labels=["lo", "mid", "hi"]), observed=True).abn.mean().round(4).to_dict()}
        r["gates"] = {"g1_train_pos": r["train_mean"] > 0 if VER=="v1" else True, "g2_ho_t2": r["ho_mean"] > 0 and t_ho > 2,
                      "g3_beat_ctrl_p95": r["ho_mean"] > p95, "g4_n": len(ho) >= (100 if VER=="v1" else 60)}
        r["verdict"] = "PASS" if all(r["gates"].values()) else "LOSE"
        res[k] = r; df.to_csv(os.path.join(HERE, f"e2{VER}-events-{k}.csv"), index=False)
    print(json.dumps(res, indent=1, default=str))
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"), {"experiment": "e2", "version": VER,
              "params": {"H": H, "cost": COST, "min_usd": 1e4, "window_d": 30, "min_owners": 2, "min_cluster_usd": MINUSD},
              "verdict": res["cluster"]["verdict"], "result": res})
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "reports", f"e2-{VER}.json"), "w"), indent=1, default=str)

if __name__ == "__main__": main()
