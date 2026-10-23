"""Self-improvement loop.

Data is split once: DEV (first 75%) for walk-forward + selection, HOLDOUT (last 25%) touched only
by promotion tests. Generation g+1 candidates = mutations (neighbour values) of champion g.
Promotion needs: candidate Sharpe > champion Sharpe on HOLDOUT AND candidate beats SPY on HOLDOUT.
Every trial (dev and holdout) is appended to trials.jsonl; DSR uses the full trial count.
Honest caveat: holdout is re-used once per generation, so it degrades; generations are capped.
"""
import itertools

import numpy as np
import pandas as pd

from harness.evaluator import deflated_sharpe, evaluate, log_trial, metrics, read_trials


def combos(grid):
    keys = sorted(grid)
    for vals in itertools.product(*(grid[k] for k in keys)):
        yield dict(zip(keys, vals))


def mutate(champion: dict, grid: dict, k: int, rng):
    """Neighbour values in the (sorted) grid axes, plus random single-axis perturbations."""
    out, seen = [], {tuple(sorted(champion.items()))}
    keys = sorted(grid)
    for _ in range(50):
        if len(out) >= k:
            break
        p = dict(champion)
        key = keys[rng.integers(len(keys))]
        vals = sorted(grid[key])
        i = vals.index(champion[key]) if champion[key] in vals else 0
        j = min(max(i + int(rng.choice([-1, 1])), 0), len(vals) - 1)
        p[key] = vals[j]
        t = tuple(sorted(p.items()))
        if t not in seen:
            seen.add(t)
            out.append(p)
    return out


def walk_forward(series_by_combo: dict, bench: pd.Series, train=252, test=63):
    """For each fold choose the combo with best TRAIN Sharpe, take its TEST returns. Strictly OOS."""
    idx = bench.index
    parts, picks = [], []
    for s in range(train, len(idx) - 1, test):
        tr, te = idx[s - train:s], idx[s:s + test]
        best, bs = next(iter(series_by_combo)), -9
        for key, r in series_by_combo.items():
            x = r.reindex(tr)
            sd = x.std()
            sh = x.mean() / sd if sd and sd > 0 else -9
            if sh > bs:
                best, bs = key, sh
        parts.append(series_by_combo[best].reindex(te))
        picks.append(best)
    return pd.concat(parts), picks


def run_experiment(exp, close, bench, trials_path, generations=3, mutate_k=3, seed=0, cost_bps=5.0):
    rng = np.random.default_rng(seed)
    cut = int(len(close) * 0.75)
    dev_idx, ho_idx = close.index[:cut], close.index[cut:]
    cache = {}

    def get(params):
        key = tuple(sorted(params.items()))
        if key not in cache:
            cache[key] = exp.run(close, params, cost_bps)
        return cache[key]

    def sharpe(r):
        sd = r.std()
        return float(r.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0

    # --- generation 0: full grid, walk-forward on DEV
    cands = list(combos(exp.grid))
    history, champion, champ_gen = [], None, 0
    for g in range(generations):
        series = {tuple(sorted(p.items())): get(p) for p in cands}
        dev_series = {k: v.reindex(dev_idx) for k, v in series.items()}
        wf, picks = walk_forward(dev_series, bench.reindex(dev_idx))
        wf_ev = evaluate(wf, bench)
        best_key = max(dev_series, key=lambda k: sharpe(dev_series[k].dropna()))
        for k, v in dev_series.items():
            log_trial(trials_path, {"experiment": exp.id, "generation": g, "stage": "dev",
                                    "params": dict(k), "seed": seed,
                                    "sharpe": metrics(v)["sharpe"], "n": len(v), "origin": "grid" if g == 0 else "mutation"})
        cand = dict(best_key)
        ho = series[best_key].reindex(ho_idx)
        ho_ev = evaluate(ho, bench)
        promoted, reason = False, ""
        if champion is None:
            champion, promoted, reason = cand, True, "initial champion"
            champ_ho = ho
        else:
            ch = sharpe(ho) > sharpe(champ_ho) and ho_ev.get("beat_sp500", False)
            promoted = bool(ch)
            reason = "beats champion on holdout and SPY" if ch else "did not beat champion+SPY on holdout; champion stands"
            if promoted:
                champion, champ_ho, champ_gen = cand, ho, g
        log_trial(trials_path, {"experiment": exp.id, "generation": g, "stage": "holdout", "params": cand,
                                "seed": seed, "sharpe": ho_ev.get("strategy", {}).get("sharpe"),
                                "verdict": ho_ev.get("verdict"), "promoted": promoted, "reason": reason})
        history.append({"generation": g, "candidate": cand, "dev_walkforward": wf_ev,
                        "holdout": ho_ev, "promoted": promoted, "reason": reason, "n_candidates": len(cands)})
        cands = mutate(champion, exp.grid, mutate_k, rng) or []
        if not cands:
            break
    # overfit accounting over ALL trials logged for this experiment
    trials = [t["sharpe"] / np.sqrt(252) for t in read_trials(trials_path, exp.id)
              if t.get("stage") == "dev" and t.get("sharpe") is not None]
    ch_ho = get(champion).reindex(ho_idx)
    m = metrics(ch_ho)
    dsr = deflated_sharpe(m["sharpe"] / np.sqrt(252), m["n_days"], trials) if "error" not in m else None
    return {"experiment": exp.id, "champion": champion, "champion_generation": champ_gen,
            "champion_holdout": evaluate(ch_ho, bench), "deflated_sharpe_prob": dsr,
            "trials_logged": len(trials), "history": history}
