"""python experiments/e05-thesis-book/run_e5.py [--seed]  -- e5 thesis book (paper only).

Spec: experiments/experiment-5-thesis-research.md (+ SPEC.md here). Marks the 10-position
paper book to market vs ^GSPC (SPY), QTUM, and a random-pick control drawn from the SAME
pre-registered candidate pool. Applies the demote rule. NEVER places orders.
State: registry/e5-portfolio.json (weekly cron 955fdb31f7de appends to decision_log).
"""
import json, os, sys, time
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from harness.evaluator import log_trial

STATE = os.path.join(ROOT, "registry", "e5-portfolio.json")
INCEPTION = "2026-10-20"
NOTIONAL = 1000.0
BENCH, THEMATIC = "SPY", "QTUM"
N_RANDOM = 500

BOOK = {  # ticker: (theme, thesis, falsifier)
 "IBM":  ("quantum", "Quantum roadmap (Heron/Starling) inside a profitable, cheap incumbent; exposure without pure-play hype.", "Quantum roadmap milestone slips >12 months, or software+consulting revenue declines 2 straight quarters."),
 "COHR": ("quantum/AI optics", "Lasers/optics supplier to quantum and AI datacenter transceivers: shovel, not pure play.", "Datacenter transceiver revenue falls 2 straight quarters or gross margin <35%."),
 "KEYS": ("quantum controls/test", "Test, measurement and quantum control electronics sold regardless of which qubit wins.", "Two straight quarters of negative organic order growth."),
 "TSM":  ("AI compute", "Sole leading-edge foundry for AI accelerators.", "Major-customer loss at N2 or sustained capex cut guidance."),
 "VRT":  ("AI power/cooling", "Datacenter power and liquid cooling shovel.", "Book-to-bill <1 for 2 quarters, or hyperscaler capex guidance cut >15%."),
 "CEG":  ("nuclear power", "Largest US nuclear fleet; long-term datacenter PPAs.", "A hyperscaler PPA cancelled/renegotiated materially lower, or major unit outage >6 months."),
 "RKLB": ("space", "Vertically integrated small-launch + spacecraft components with Neutron in development.", "Neutron first launch slips past 2027-06 or cash runway <4 quarters."),
 "LLY":  ("biotech/GLP-1", "GLP-1/obesity franchise with capacity ramp.", "Orforglipron/tirzepatide guidance cut >10% or pricing-driven revenue decline 2 quarters."),
 "LMT":  ("defense", "Defense budget tailwind, backlog visibility.", "Backlog declines 2 consecutive quarters or major program (F-35) cut."),
 "ETN":  ("electrification", "Grid and datacenter electrical equipment shovel.", "Electrical Americas orders negative YoY for 2 quarters."),
}
POOL_EXTRA = ["NVDA","AMD","AVGO","ASML","MU","SMCI","ANET","GEV","VST","OKLO","PLTR","RTX","NOC","GD","LHX","VRTX","REGN","AMGN","ISRG","FSLR","ENPH","PWR","IONQ","RGTI","QUBT","ASTS","LUNR","SNPS"]
POOL = list(BOOK) + POOL_EXTRA


def fetch(tickers, start):
    import yfinance as yf
    d = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    return d.dropna(how="all").sort_index()


def price_on_or_before(px, t, date):
    s = px[t].loc[:date].dropna()
    return float(s.iloc[-1]) if len(s) else None


def main():
    seed = "--seed" in sys.argv or not os.path.exists(STATE)
    px = fetch(POOL + [BENCH, THEMATIC], "2026-09-01")
    last = px.index[-1]
    last_s = str(last.date())
    if seed:
        positions = []
        for t, (th, thesis, fal) in BOOK.items():
            p = price_on_or_before(px, t, INCEPTION)
            positions.append({"ticker": t, "theme": th, "weight": 0.10, "entry_date": INCEPTION,
                              "entry_price": round(p, 4), "thesis": thesis, "falsifier": fal, "status": "open"})
        rng = np.random.default_rng(5)
        draws = [sorted(rng.choice(POOL, 10, replace=False).tolist()) for _ in range(N_RANDOM)]
        state = {"version": 1, "paper": True, "never_real_orders": True, "notional": NOTIONAL,
                 "inception": INCEPTION, "rebalance": "quarterly", "max_positions": 10, "max_weight": 0.10,
                 "benchmarks": {"sp500": BENCH, "thematic": THEMATIC},
                 "benchmark_entry": {t: round(price_on_or_before(px, t, INCEPTION), 4) for t in (BENCH, THEMATIC)},
                 "candidate_pool": POOL, "random_control": {"n_draws": N_RANDOM, "seed": 5, "draws": draws},
                 "positions": positions, "nav_history": [], "decision_log": [],
                 "demote_rule": "if book trails benchmark by >10pp after 2 quarters -> index the theme (ETF) and keep pipeline as digest only; also demote if it cannot beat random-pick median"}
    else:
        state = json.load(open(STATE))
    # mark to market
    def ret(t, entry):
        return price_on_or_before(px, t, last_s) / entry - 1
    open_pos = [p for p in state["positions"] if p["status"] == "open"]
    book_ret = float(np.mean([ret(p["ticker"], p["entry_price"]) for p in open_pos]))
    bench = {t: ret(t, state["benchmark_entry"][t]) for t in (BENCH, THEMATIC)}
    entry = {t: price_on_or_before(px, t, state["inception"]) for t in POOL}
    rr = np.array([np.mean([ret(t, entry[t]) for t in d]) for d in state["random_control"]["draws"]])
    rmed, p25, p75 = (float(np.percentile(rr, q)) for q in (50, 25, 75))
    pct_rank = float((rr < book_ret).mean())
    import datetime
    days = (last.to_pydatetime().date() - datetime.date.fromisoformat(state["inception"])).days
    quarters = days / 91.0
    gap_pp = (book_ret - bench[BENCH]) * 100
    if quarters < 2:
        demote = "NOT YET TESTABLE (%.2f of 2 quarters elapsed)" % quarters
    else:
        demote = "DEMOTE" if gap_pp < -10 else "HOLD"
    snap = {"date": last_s, "nav": round(NOTIONAL * (1 + book_ret), 2), "book_ret": round(book_ret, 5),
            "spy_ret": round(bench[BENCH], 5), "qtum_ret": round(bench[THEMATIC], 5),
            "random_median": round(rmed, 5), "random_p25_p75": [round(p25, 5), round(p75, 5)],
            "book_pctile_vs_random": round(pct_rank, 3), "gap_vs_spy_pp": round(gap_pp, 2),
            "quarters_elapsed": round(quarters, 2), "demote_status": demote}
    state["nav_history"] = [h for h in state["nav_history"] if h["date"] != last_s] + [snap]
    state["last_run"] = snap
    if seed:
        state["decision_log"].append({"date": INCEPTION, "action": "seed", "note": "10 positions entered at last close on/before inception; no trades since; paper only"})
    json.dump(state, open(STATE, "w"), indent=1)
    log_trial(os.path.join(ROOT, "registry", "trials.jsonl"),
              {"experiment": "e5_thesis_book", "generation": 0, "stage": "paper", "params": {"max_positions": 10, "max_weight": 0.10, "rebalance": "Q"},
               "seed": 5, "book_ret": snap["book_ret"], "spy_ret": snap["spy_ret"], "random_median": snap["random_median"],
               "verdict": "PENDING" if quarters < 2 else ("BEAT" if gap_pp > 0 and book_ret > rmed else "LOSE"), "origin": "manual"})
    rep = ["# e5 thesis book — " + last_s, "", "Paper only. 10 positions, 10%% each, entered %s, benchmark SPY + QTUM, random-pick control from same %d-name pool (%d draws)." % (state["inception"], len(POOL), N_RANDOM), "",
           "| Series | Return since inception |", "|---|---|",
           "| Thesis book | %.2f%% |" % (book_ret*100), "| SPY | %.2f%% |" % (bench[BENCH]*100), "| QTUM | %.2f%% |" % (bench[THEMATIC]*100),
           "| Random-pick median (IQR %.2f%%..%.2f%%) | %.2f%% |" % (p25*100, p75*100, rmed*100), "",
           "- Book percentile vs random draws: %.0f%%" % (pct_rank*100), "- Gap vs SPY: %.2f pp" % gap_pp,
           "- Quarters elapsed: %.2f; demote rule: **%s**" % (quarters, demote), "",
           "## Positions", "", "| Ticker | Theme | Entry | Last | Return |", "|---|---|---|---|---|"]
    for p in open_pos:
        l = price_on_or_before(px, p["ticker"], last_s)
        rep.append("| %s | %s | %.2f | %.2f | %.2f%% |" % (p["ticker"], p["theme"], p["entry_price"], l, (l/p["entry_price"]-1)*100))
    rep += ["", "Verdict: PENDING until 2 full quarters elapse. Pool and picks are hand-selected by the author with hindsight of the theme narratives (survivor/hype bias risk); the random control shares that bias, so beating it is the meaningful test."]
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    open(os.path.join(ROOT, "reports", "e5-thesis-book.md"), "w").write("\n".join(rep) + "\n")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e5-report.md"), "w").write("\n".join(rep) + "\n")
    json.dump(snap, open(os.path.join(ROOT, "reports", "e5-thesis-book.json"), "w"), indent=1)
    print(json.dumps(snap, indent=1))

if __name__ == "__main__":
    main()
