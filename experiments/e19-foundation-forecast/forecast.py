"""e19 forecast generator (runs offline). usage: forecast.py {kronos|timesfm} OUT.csv  -- see SPEC.md"""
import sys, os, numpy as np, pandas as pd, torch
MODEL, OUT = sys.argv[1], sys.argv[2]
SH, NSH = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 1)
SRC = os.path.expanduser("~/tlab/e19")
TICK = "SPY QQQ IWM DIA XLK XLF XLE XLV XLY XLI XLP XLU TLT GLD".split()
T0 = pd.Timestamp("2024-07-01"); CTX = 512; H = 5
torch.manual_seed(19); np.random.seed(19)
px = pd.read_pickle(os.path.join(SRC, "px.pkl"))   # dict ticker -> OHLCV df
dates = px["SPY"].index[px["SPY"].index >= T0]
dates = dates[SH::NSH]
done = set()
if os.path.exists(OUT):
    done = set(pd.read_csv(OUT)["date"])
else:
    open(OUT, "w").write("date,ticker,f1,f5\n")
if MODEL == "kronos":
    sys.path.insert(0, os.path.join(SRC, "kronos_src"))
    from model import Kronos, KronosTokenizer, KronosPredictor
    tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    mdl = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    pred = KronosPredictor(mdl, tok, device="cpu", max_context=CTX)
else:
    import timesfm
    m = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
    m.compile(timesfm.ForecastConfig(max_context=CTX, max_horizon=H, normalize_inputs=True,
              use_continuous_quantile_head=True, force_flip_invariance=True, infer_is_positive=True, fix_quantile_crossing=True))
for i, d in enumerate(dates):
    ds = str(d.date())
    if ds in done: continue
    torch.manual_seed(19 + int(d.strftime("%Y%m%d")))
    hist = {t: px[t].loc[:d].iloc[-CTX:] for t in TICK}   # bars <= d only
    last = {t: float(hist[t].Close.iloc[-1]) for t in TICK}
    if MODEL == "kronos":
        dfs, xts, yts = [], [], []
        for t in TICK:
            h = hist[t]
            df = pd.DataFrame({"open": h.Open.values, "high": h.High.values, "low": h.Low.values, "close": h.Close.values,
                               "volume": h.Volume.values, "amount": (h.Volume * h.Close).values})
            dfs.append(df); xts.append(pd.Series(h.index)); yts.append(pd.Series(pd.bdate_range(d + pd.Timedelta(days=1), periods=H)))
        outs = pred.predict_batch(dfs, xts, yts, pred_len=H, T=1.0, top_p=0.9, sample_count=5, verbose=False)
        fc = {t: outs[k]["close"].values for k, t in enumerate(TICK)}
    else:
        pf, _ = m.forecast(horizon=H, inputs=[hist[t].Close.values.astype(float) for t in TICK])
        fc = {t: pf[k] for k, t in enumerate(TICK)}
    with open(OUT, "a") as f:
        for t in TICK:
            f.write(f"{ds},{t},{fc[t][0]/last[t]-1:.8f},{fc[t][H-1]/last[t]-1:.8f}\n")
    if i % 20 == 0: print(MODEL, i, len(dates), ds, flush=True)
print("DONE", MODEL, flush=True)
