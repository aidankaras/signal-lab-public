# e6 — SEC-filings forecasting (folded from the retired "arbiter" project, 2026-10-18)

Pre-registered. Paper only. Source: vendored snapshot of github.com/aidankaras/arbiter
(commit at fold time; MIT) now living at `experiments/e6-sec-filings/` under the name
SecFilings. The old name is retired everywhere; its cross-family-review arm was
"arbiter-arm" and is now "review arm".

## Inherited result (verified before the fold, accepted as-is)
- Baseline arm (logistic regression on Form-4/8-K features), walk-forward, point-in-time
  content-hashed evidence packets, embargoed chronological split:
  **no measurable skill** — mean IC +0.029 (t = 1.52) over 60 OOS days / 3,909 issuer-days;
  Brier skill −0.0015 (noise). Full report: `experiments/e6-sec-filings/reports/baseline-insider.md`.
- An earlier smaller-sample result (+0.121) was withdrawn after row duplication was found —
  the withdrawal record is preserved in `reports/withdrawn/`. That honesty record is part of
  why this is worth keeping.
- The agent-arm scored run was pending at fold time (protocol: `docs/agent-arm.md`).

## Relationship to e2
e2 (insider Form-4 clusters) was killed 2026-10-18 at v0 (AUC 0.498 < 0.55) on counts alone.
e6 supersedes it: same EDGAR surface, but point-in-time packets, proper labels (5-session
abnormal returns), and a working backfill pipeline — the infrastructure e2 would have needed
had its gate passed.

## Gates (carried from the lab contract + the repo's own protocol)
- Walk-forward only, no lookahead, costs ≥5bps/side, scored vs ^GSPC and random-pick control
  over identical windows; trials logged to registry/trials.jsonl.
- Agent-arm LLM spend metered (repo has a spend ledger) — stays within the $30/mo lab LLM
  ceiling; no premium models without Aidan's approval.
- Kill: agent arm shows IC ≤ baseline (≈0) on the full scored run → the honest verdict is
  "LLM agents add nothing on SEC filings at this scale" and the experiment closes.
- Never converts to a live strategy without beating e0 AND SPY AND random-pick on holdout.

## Next actions if resumed
1. Run the pending agent-arm scored run (needs its venv/deps; Docker).
2. Merge the review-arm protocol.
3. Fold prediction-ledger outputs into lab verdict machinery.

## Name retirement
The name "arbiter" is retired (Aidan, 2026-10-18). GitHub repo RENAMED 2026-10-18 to
`aidankaras/sec-filings-e6` (github.com/aidankaras/arbiter auto-redirects). Repo description
still references the pipeline, not the old name; resume now lists the Trading Research Lab
instead of the old project name. Local vendored copy uses "SecFilings"/"review arm" only.
