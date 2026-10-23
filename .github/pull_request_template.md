## What changed

## Experiment impact
- [ ] No lookahead (signals use data <= t, fills at next bar)
- [ ] Costs charged; controls run on the same window
- [ ] Spec/gates written before the run; trials appended, not rewritten
- [ ] Failures are reported, not dropped

## Tests
- [ ] `python -m pytest -q` and `ruff check` pass
