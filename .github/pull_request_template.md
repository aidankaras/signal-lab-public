## What changed

## Experiment impact
- [ ] No lookahead (signals use data <= t; a weight decided at close t earns returns from t+1 on)
- [ ] Costs charged; controls run on the same window
- [ ] Spec/gates written before the run; trials appended, not rewritten
- [ ] Failures are reported, not dropped

## Tests
- [ ] `python -m pytest -q` and `ruff check` pass
