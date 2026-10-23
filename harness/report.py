import time


def line(res):
    ho = res["champion_holdout"]
    if "error" in ho:
        return f"{res['experiment']}: n/a"
    s, b = ho["strategy"], ho["benchmark_sp500"]
    d = res["deflated_sharpe_prob"]
    return (f"{res['experiment']} [{ho['verdict']}] gen {res['champion_generation']} {res['champion']} | "
            f"holdout {ho['window'][0]}→{ho['window'][1]}: CAGR {s['cagr']:.1%} vs SPY {b['cagr']:.1%}, "
            f"Sharpe {s['sharpe']} vs {b['sharpe']}, maxDD {s['maxdd']:.1%} | trials {res['trials_logged']}, "
            f"DSR p={'n/a' if d is None or d != d else round(d, 2)}")


def write(results, controls, path):
    out = [f"# Trading Lab report {time.strftime('%Y-%m-%d')}", "",
           "Paper only. Every row scored vs S&P 500 (SPY total return) on the same holdout window.", ""]
    out += ["- " + line(r) for r in results]
    if controls:
        out += ["", "## Random-pick control (k=3 of universe, 20 seeds, holdout)", controls]
    open(path, "w").write("\n".join(out) + "\n")
    return "\n".join(out)
