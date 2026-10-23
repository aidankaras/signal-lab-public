"""Trading Research Lab harness core.

Contracts:
- Experiment.run(prices: pd.DataFrame) -> pd.DataFrame of strategy returns (daily, net of costs).
- evaluator.evaluate(returns, bench_returns) -> dict incl. verdict vs S&P 500.
- improve.run(experiment, grid, ...) -> self-improvement loop, append-only trial log,
  promotion only if new champion beats previous OOS AND beats SPY.
"""
