# Roadmap

Planned, not built.

## Interactive dashboard (GitHub Pages)
Static site generated from the report JSONs under `experiments/*/`:
- sortable results table with verdict, window, net/gross Sharpe, SPY and control comparison;
- per-experiment drill-down (equity curves, drawdown, control distribution);
- trial-count / Deflated-Sharpe view from `registry/trials.jsonl`.
Build step: `docs/make_charts.py` generalised to emit JSON + HTML via a GitHub Actions Pages deploy.
No server, no live data.

## Alpaca paper trading, one book per experiment
- Each experiment that clears its gate trades its own paper book on Alpaca.
- Orders tagged with `client_order_id = "<experiment>-<date>-<n>"` so fills are attributable.
- An internal ledger (append-only, same discipline as `trials.jsonl`) reconciles Alpaca fills per
  experiment, computing P&L, costs and slippage per book rather than relying on account-level totals.
- Real-money use stays gated on owner approval (see README operating rules).

## Smaller items
- Persist daily return series per experiment so equity-curve charts (e.g. e10 v0 vs v1) can be drawn
  from committed data; today only summary metrics are stored.
- Fixture dataset to run the experiment runners offline in CI.
- Merge e16 (branch `exp/e16-daily-direction`).
