# Knowledge (imported from Loot / Grok, 2026-11-21)

This is the research brain behind the plans. Nirvana's code doesn't read it; Claude does, when researching or writing `plan.yaml`.

| Folder | What |
|---|---|
| `skills/` | 18 playbooks: crypto-trader-playbook, quant-lab (backtest keep/caution/drop rules), ph-market-playbook, ph-stock-verdict, watchlist rebalancers (PSE/US/crypto), call-scorecard, daily-quant-loop, research and writing skills |
| `data/` | crypto/PSE/US watchlists, `scorecard.jsonl` (every logged call) + summary |
| `quant/` | backtest kit: `backtests/run_all.py`, `sizing.py`, `FINDINGS.md`, `COVERAGE.md`. `prices.db` is NOT in git (29 MB); rebuild with `python3 knowledge/quant/update_prices.py --full` |
| `archive/` | Grok's crypto rulebook (superseded by Nirvana; kept for history) |

Notes from the export:
- HYPE wrong-if is **$45** (the $48 said once on Nov 21 is superseded).
- `us_watchlist.json` predates the ETF core (VOO 50 / QQQM 25 / SCHD 15 / SMH 10).
- `pse_watchlist.json` still has some old wrong-ifs.
- Binance only lists HYPEUSDT since 2026-09-24. Full HYPE history (from Dec 2024) comes from Hyperliquid, in prices.db.
- Skills were written for Grok. Paths are fixed to `knowledge/quant/`; tool names inside may not match Claude's.
