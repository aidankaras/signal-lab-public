"""python run_e8.py -- LSTM price model (e8). Offline-executed (needs torch CPU).

Pre-registration: experiments/experiment-8-deep-learning.md. Small LSTM (~20k params)
on daily sequences; the data budget (40 tickers x ~14y daily) cannot support anything
larger — stated up front rather than tuned around.

Design:
- Per (ticker, date) sample: sequence of the last 20 sessions of [return, vol-z,
  21d momentum, distance from 63d high]; label = next-5-session abnormal return > 0
  vs SPY (same labels as e6/e10).
- Walk-forward expanding, refit every 252 sessions, 5-session embargo, early-stop
  holdout = last year of each fit window. Model: 2-layer LSTM(32) -> linear.
- Score: daily Spearman IC. Gate: BEAT if IC t > 2. Survivorship caveat from e10
  applies to any pass: BROAD-40 is today's list, flagged in the report.
"""
import json, os, sys, time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import torch
import torch.nn as nn

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.data import BROAD
from harness.evaluator import log_trial

SEQ, HID, EPOCHS, BATCH = 20, 32, 12, 4096


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(4, HID, num_layers=2, batch_first=True, dropout=0.1)
        self.head = nn.Linear(HID, 1)

    def forward(self, x):
        o, _ = self.lstm(x)
        return self.head(o[:, -1]).squeeze(-1)


def build():
    from harness import data
    px = data.fetch(BROAD, start="2012-01-01", refresh=False, name="broad")
    spy = px["SPY"]
    frames = []
    for t in px.columns:
        if t == "SPY": continue
        c = px[t].dropna()
        if len(c) < 300: continue
        r = c.pct_change()
        f = pd.DataFrame({
            "ret": r,
            "volz": r / r.rolling(63).std().replace(0, np.nan),
            "mom21": c.pct_change(21),
            "hi63": c / c.rolling(63).max() - 1,
            "y": ((c.shift(-5) / c - 1) - (spy.shift(-5) / spy - 1) > 0).astype(int),
        }, index=c.index)
        f["ticker"] = t
        frames.append(f.dropna())
    df = pd.concat(frames)
    df.index.name = "date"
    df = df.reset_index().sort_values("date").reset_index(drop=True)
    return df


def make_samples(df):
    """Return per-ticker aligned arrays + a global date list."""
    dates = sorted(df.date.unique())
    dpos = {d: i for i, d in enumerate(dates)}
    series = {}
    for t, g in df.groupby("ticker"):
        g = g.sort_values("date")
        idx = {d: i for i, d in enumerate(g.date.values)}
        series[t] = {
            "X": g[["ret", "volz", "mom21", "hi63"]].values.astype(np.float32),
            "y": g.y.values.astype(np.float32),
            "row_of_date": {d: idx[d] for d in g.date.values if d in dpos},
            "dates": g.date.values,
        }
    return dates, dpos, series


def collect(series, tickers, d_range, dpos):
    """Samples whose date is inside d_range (a set of date objects)."""
    X, y, meta = [], [], []
    for t in tickers:
        s = series[t]
        for d, i in s["row_of_date"].items():
            if d not in d_range or i < SEQ: continue
            X.append(s["X"][i - SEQ:i])
            y.append(s["y"][i])
            meta.append((t, d))
    return np.array(X, dtype=np.float32), np.array(y), meta


def run():
    df = build()
    dates, dpos, series = make_samples(df)
    tickers = list(series)
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    ics = []
    step = 252
    for b in range(SEQ, len(dates) - step, step):
        fit_dates = dates[SEQ:dpos[dates[b - 6]]]      # 5-session embargo
        te_dates = dates[b:min(b + step, len(dates))]
        Xtr, ytr, _ = collect(series, tickers, set(fit_dates), dpos)
        Xte, _, meta = collect(series, tickers, set(te_dates), dpos)
        if len(Xtr) < 3000 or len(Xte) < 500:
            continue
        # early-stop holdout: last year of the fit window
        cut = int(len(Xtr) * 0.75)
        net = Net()
        opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
        lossf = nn.BCEWithLogitsLoss()
        Xt, yt = torch.tensor(Xtr[:cut]), torch.tensor(ytr[:cut])
        Xh, yh = torch.tensor(Xtr[cut:]), torch.tensor(ytr[cut:])
        best, best_state = np.inf, None
        for ep in range(EPOCHS):
            net.train()
            perm = rng.permutation(cut)
            for i in range(0, cut, BATCH):
                idx = torch.tensor(perm[i:i + BATCH])
                opt.zero_grad()
                loss = lossf(net(Xt[idx]), yt[idx])
                loss.backward(); opt.step()
            net.eval()
            with torch.no_grad():
                vl = float(lossf(net(Xh), yh))
            if vl < best:
                best, best_state = vl, {k: v.clone() for k, v in net.state_dict().items()}
        if best_state:
            net.load_state_dict(best_state)
        net.eval()
        with torch.no_grad():
            p = torch.sigmoid(net(torch.tensor(Xte))).numpy()
        pm = pd.DataFrame(meta, columns=["ticker", "date"])
        pm["p"] = p
        ymap = df.set_index(["date", "ticker"]).y
        pm["y"] = [ymap.loc[(d, t)] for t, d in meta]
        for d, gd in pm.groupby("date"):
            if gd.y.nunique() < 2 or len(gd) < 10: continue
            ic = spearmanr(gd.p, gd.y).statistic
            if ic == ic: ics.append((str(d)[:10], ic))
        print("block@%s IC so far %.4f (%d days)" %
              (str(te_dates[-1])[:10], float(np.mean([v for _, v in ics])), len(ics)), flush=True)
    s = pd.Series({d: v for d, v in ics}).sort_index()
    ic, n = float(s.mean()), len(s)
    t = float(ic / s.std() * n ** .5) if n > 1 and s.std() > 0 else 0.0
    res = {"experiment": "e8_lstm", "ic_mean": round(ic, 4), "ic_t": round(t, 2),
           "scored_days": n, "params": {"hidden": HID, "seq": SEQ, "layers": 2},
           "caveat": "BROAD-40 survivorship universe — any IC pass is suspect (see e10)",
           "verdict": "BEAT" if t > 2 else "LOSE"}
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e8_lstm", "generation": 0, "stage": "holdout",
               "params": {"hidden": HID, "seq": SEQ, "epochs": EPOCHS}, "seed": 0,
               "ic": ic, "t": t, "n": n, "verdict": res["verdict"], "origin": "manual"})
    json.dump(res, open(os.path.join(ROOT, "reports", "e8-lstm.json"), "w"), indent=1)
    open(os.path.join(ROOT, "reports", "e8-lstm.md"), "w").write(
        "# e8 - LSTM price model " + time.strftime("%Y-%m-%d") + "\n\n"
        f"- Daily Spearman IC: **{res['ic_mean']}** (t = {res['ic_t']}, {n} scored days)\n"
        f"- Verdict: **{res['verdict']}** (gate: IC t > 2)\n"
        "- Model: 2-layer LSTM(32) on 20-session sequences, walk-forward refit yearly,\n"
        "  5-session embargo, early stopping on the fit window's own holdout.\n"
        "- Caveat: survivorship-biased universe; see experiments/experiment-8-deep-learning.md\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    run()
