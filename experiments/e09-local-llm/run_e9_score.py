"""Score e9 Phase 1: local-LLM direction calls vs realized 5-session abnormal returns.
Executed after e9_infer.py completes. Writes reports/e9-llm-analyst.{json,md}."""
import json, os, sys, time
import numpy as np
from scipy.stats import binomtest, spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.evaluator import log_trial

C = os.path.join(ROOT, "data", "cache")

S = {f'{r["ticker"]}|{r["date"]}': r
     for r in map(json.loads, open(os.path.join(C, "e9_summaries.jsonl")))}
P = {r["key"]: r["pred"] for r in map(json.loads, open(os.path.join(C, "e9_predictions.jsonl")))}

keys = [k for k in P if k in S and S[k]["label"] == S[k]["label"]]
print("DEBUG len(S)=%d len(P)=%d keys=%d" % (len(S), len(P), len(keys)), flush=True)
hits = [(S[k]["label"] > 0) == (P[k] == "UP") for k in keys]
pr_up = [P[k] == "UP" for k in keys]
acc = float(np.mean(hits))
base = float(np.mean([S[k]["label"] > 0 for k in keys]))   # base rate of UP labels
bias = float(np.mean(pr_up))                               # model's UP rate
bt = binomtest(int(sum(hits)), len(keys), 0.5).pvalue
lab = np.array([S[k]["label"] for k in keys])
sig = np.array([1.0 if P[k] == "UP" else -1.0 for k in keys])
ic = float(spearmanr(sig, lab).statistic)
n = len(keys)
t_ic = ic / (np.sqrt((1 - ic * ic) / max(1, n - 1)))
verdict = "BEAT" if acc > 0.55 and bt < 0.01 else "LOSE"

res = {"experiment": "e9_llm_analyst_phase1", "model": "Qwen2.5-1.5B-Instruct (q4, llama.cpp CPU)",
       "n": n, "accuracy": round(acc, 4), "up_base_rate": round(base, 4),
       "model_up_rate": round(bias, 4), "binom_p_vs_50": round(bt, 4),
       "ic": round(ic, 4), "ic_t": round(float(t_ic), 2), "verdict": verdict}
log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
          {"experiment": "e9_llm_analyst_phase1", "generation": 0, "stage": "holdout",
           "params": {"model": "qwen2.5-1.5b q4", "temp": 0}, "seed": 0,
           "accuracy": acc, "n": n, "verdict": verdict, "origin": "manual"})
json.dump(res, open(os.path.join(ROOT, "reports", "e9-llm-analyst.json"), "w"), indent=1)
open(os.path.join(ROOT, "reports", "e9-llm-analyst.md"), "w").write(
    "# e9 Phase 1 — local LLM analyst " + time.strftime("%Y-%m-%d") + "\n\n"
    f"Zero-shot Qwen2.5-1.5B (4-bit, llama.cpp CPU) called UP/DOWN on {n} (ticker, week)\n"
    "point-in-time summaries for the 2026 holdout window.\n\n"
    f"- Direction accuracy: **{acc:.1%}** (UP base rate {base:.1%}; binomial p vs 50/50 = {bt:.3f})\n"
    f"- Signed Spearman IC: {ic:.4f} (t = {t_ic:.2f})\n"
    f"- Model UP bias: {bias:.1%}\n"
    f"- Verdict: **{verdict}** (gate: accuracy > 55% AND p < 0.01)\n\n"
    "Contamination note: Qwen2.5 predates the 2026 holdout window, so pretraining leakage\n"
    "is bounded by the vendor cutoff claim. Fine-tuned arm (Phase 2) is gated: not run\n"
    "unless the zero-shot arm clears its gate.\n")
print(json.dumps(res, indent=1))
