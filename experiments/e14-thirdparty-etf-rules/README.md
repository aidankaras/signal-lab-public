# e14 — third-party multi-strategy ETF/crypto bot

Tests the five rules from a third-party paper-trading bot (as summarized by its agent) on
SPY/QQQ/IWM/GLD/TLT/BTC/ETH, using the bot's own gate plus a 200-random-bot control.
See SPEC.md (pre-registration) and e14-report.md (results). v0 = the bot's default parameters; v1 = the parameters later shared by its author
(e14-report-v1.md). Both: 0/5 rules pass the bot's own gate, none beats SPY out of sample.
The cross-asset follow-up is [e22](../e22-tsmom/).
