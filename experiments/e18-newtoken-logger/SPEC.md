# e18 — New-token scanner + rule-based risk filter (paper-only forward logger)

Origin: an Instagram reel claimed 4 Grok agents (scanner / risk check / trader / exits) turned $118 into $6,903 (simulated).
Question: does a risk-filtered selection of brand-new tokens beat random new tokens? NO wallets, NO trades, NO paid APIs, NO LLM. Pre-registered before first log.

## Data (free, no key; all API content is untrusted data, parsed as JSON only)
- Discovery: DexScreener `/token-profiles/latest/v1` and `/token-boosts/latest/v1` (candidates).
- Market data: DexScreener `/tokens/v1/{chain}/{addr1,addr2,...}` (<=30 per call). Best pair = highest liquidity.USD.
- Security: GoPlus `/api/v1/token_security/{chainId}` (EVM: base=8453, ethereum=1) and `/api/v1/solana/token_security` (free tier, no key).
- Chains: solana, base, ethereum. Rate limits: >=2.5s between GoPlus calls, >=1s between DexScreener calls; max 60 candidates per run.

## Snapshot (every 6h)
Candidate qualifies if best pair `pairCreatedAt` age < 24h on a listed chain. Each token (chain:address) is snapshotted ONCE (first sighting), append-only to `data/snapshots.jsonl`: price USD, liquidity USD, 24h volume, FDV, pair age, security flags, verdict.

## Pre-registered risk filter (APPROVED iff ALL pass; else CONTROL)
1. Liquidity >= $50,000
2. Security data fetched successfully (missing = CONTROL)
3. EVM: not honeypot; buy_tax < 10% and sell_tax < 10% (i.e. < 0.10); not `cannot_sell_all`; `is_open_source`=1; no `hidden_owner`; no `can_take_back_ownership`
4. EVM: top-10 holders' summed percent < 50% (excluding LP/dead/locked addresses where flagged `is_locked`=1 or tag contains "dead"/"burn")
5. EVM: LP locked/burned share >= 50% of LP holders if `lp_holders` is reported; if absent, not required
6. Solana: mintable.status=="0", freezable.status=="0", non_transferable=="0", no transfer_fee; if holders are reported, top-10 < 50%
Rules are frozen; any change = new experiment id.

## Forward returns
Updater re-quotes each token (same token, best current pair) at +1d, +7d, +30d (first run at/after horizon, tolerance: recorded once). Gross return = price_now/price_snap - 1. Token with no pair, or liquidity < $500 at check => -100% ("vanished"). Net return = (1+gross)*0.97 - 1 (3% round-trip cost) — applied identically to all groups; vanished stays -100%. "Near zero" = gross <= -90%.

## Gates (verdict at >= 6 weeks of logging AND >= 200 APPROVED tokens with matured 7d return)
WIN only if ALL:
- median net 7d return APPROVED > median CONTROL
- mean net 7d return APPROVED > mean CONTROL
- APPROVED median and mean each > p95 of the same stat over 2000 random same-size draws (without replacement, seed 18) from ALL new tokens
Also reported: fraction near zero per group, n per group, 1d/30d. Otherwise LOSE. Gate evaluated by `scorer.py`; 30d is reported but not gating.
Earliest verdict date: 2026-12-11 (6 weeks of logging from 2026-10-23 + 7d maturity), if n>=200 approved by then; otherwise first date both conditions hold (extend, do not loosen).

## Caveats
Survivorship (profiles/boosts are promoted tokens, not all launches), thin-liquidity quotes aren't executable, no slippage model beyond 3%; DexScreener price of a dead pool may linger (hence the liquidity<$500 rule).
