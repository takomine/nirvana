---
name: daily-quant-loop
description: >-
  Use when running or changing the daily research routines (pre-market intel,
  contrarian view, morning report, PSE close recap, crypto evening check,
  alerts on flows/broken theses, weekly review), or when asked "what's the
  play today?": the step-by-step loop one bot runs for crypto and PSE.
---
# Daily quant loop (one bot, many passes)

One bot runs every pass; heavy research can go to a subagent that returns a short result. tako only talks to this bot. Every message follows `plain-language-market-brief`. Before creating or changing routines, read the `routines` skill; check cost with `usage-review` if adding frequent runs.

## 1. Schedule (Manila time; adjust existing routines rather than duplicating)
| Time | Pass | Days | Notes |
|---|---|---|---|
| **8:05 AM** | Morning report: crypto + PSE pre-market | Daily (PSE part weekdays) | 8:05 not 8:00: the Binance/UTC daily candle closes at 8:00 AM, so wrong-if checks use a *confirmed* close. US stocks closed at 5 AM (US winter) |
| 9:05 AM | DragonFi Before the Bell add-on | Weekdays | Existing routine. If `publishedDate` isn't today: stay silent, or one "not out yet" line if the morning report promised it |
| 3:30 PM | PSE close recap | Weekdays | After the 3:15 close |
| 9:00 PM | Crypto evening check | Daily | Before the US open (10:30 PM Manila in US winter); only message if something changed |
| Event-driven | Alerts | Any | Section 5; mention in the next pass if no alert routine exists |
| Fri 5:00 PM | Weekly review + **PSE watchlist reconstitution** | Fridays | Existing; also grades crypto calls and the poster scoreboard, and runs `pse-watchlist-rebalance` §5 |

## 2. Morning report pass (the main one)
**Step A — Intel (facts only, Tier A/B first):**
1. Is today a PSE trading day? (`ph-market-playbook` §5)
2. Crypto: BTC, ETH, SOL, watchlist coins: price, 24h, UTC daily close vs key levels and wrong-ifs; funding, OI, liquidations, F&G (`crypto-trader-playbook` §4).
3. Global overnight: S&P/Nasdaq close, US 10Y, DXY, oil, USD/PHP (`https://open.er-api.com/v6/latest/USD`, verified).
4. PSE: yesterday's PSEi close, net foreign, block sales from the PSE Daily Quotation Report (`ph-legends-edge` §3); disclosures on PSE Edge for watchlist names (results, dividends, buybacks, 23-B insider deals, placements); then the watchlist light check (`pse-watchlist-rebalance` §4). Read the active list from the bot's store `pse_watchlist.json`, never from an old message.
5. Calendar: events in the next 14 days + what's priced (`event-pricing-check`).
6. X scan: scored posters (`ct-poster-scoring`) + cashtags for watchlist names; split confirmed news vs rumour.
**Step B — Contrarian pass (write before the report):**
- What is the consensus today? What would make it wrong? Who is crowded (funding, foreign flow, CT mood)?
- Take the *opposite* side of our own plan for 3 lines. If it's convincing, lower size or wait.
**Step C — Report (≤2 phone screens):** bottom line → what moved and why → what this means for you (open orders, positions, cash) → what to do (exact orders) → watch next → sources.
**Step D — Log:** every call, level and wrong-if in the journal (memory) with time and price, so it can be graded.

## 3. PSE close recap pass (3:30 PM)
1. Close prices for the active watchlist, bench and positions (phisix; `as_of` check), from the current `pse_watchlist.json`.
2. Did any limit fill-zone trade? (Ask tako to confirm fills; never assume.)
3. Big movers on watchlist + reason (disclosure/news) or "no news found".
4. Any close below a wrong-if → alert format.
5. Tomorrow's items (ex-dates, own-by dates, index events).
6. Watchlist light check (`pse-watchlist-rebalance` §4): rethink-level closes move to bench; one line per changed name, or "Watchlist: no changes".
Keep it to 5-8 lines. If nothing changed: one line.

## 4. Crypto evening pass (9:00 PM)
1. Price vs this morning; distance to open limits and wrong-ifs.
2. Positioning shift (funding flip, OI jump, liquidation spike).
3. US session events tonight (CPI, FOMC, big earnings).
4. Message only if: a limit is within ~3%, a wrong-if is at risk, an event tonight matters, or the regime changed. Otherwise stay silent and log "no change".

## 5. Alerts (send unprompted when a routine runs; otherwise raise next pass)
| Trigger | Message |
|---|---|
| Price within ~3% of an open limit | "<COIN> $X, your $Y order is close. No action needed." |
| Daily close below a wrong-if (crypto UTC close / PSE 3:15 close) | "Rethink <X>: closed $A below $B. What changed: … Plan: …" |
| Thesis broken (unlock, hack, delisting, results miss, placement, tender, halt) | 2 lines + whether the plan changes |
| Big institutional flow | PSE: net foreign >₱1B either way in a day, or a block sale in a watchlist name; crypto: ETF flow >$500M/day or liquidations >$500M/day [thresholds U, tune in review] |
| Regime flip (`crypto-trader-playbook` §2) | "Mood changed from <A> to <B> because …" |
| Unfilled order and price runs past max | "Don't chase. Keep or cancel?" |
| Event in <24h that affects positions | Scenario table from `event-pricing-check` |
| A scored A/B poster changes view on a coin we hold | Link + 1-line take |
Charts: when an alert needs one, plot the last 60 daily closes with levels (matplotlib, OKX/phisix data), save to /workspace, and attach it.

## 6. Weekly review additions (Fridays)
- Grade every logged call: hit / miss / open, vs plan levels; hit rate and average win/loss in ₱.
- Grade posters' new live calls; update the scoreboard tiers.
- Re-run `quant-signal-review` on any rule we used 10+ times.
- One lesson per mistake → the right skill's changelog (as `ph-advisor-self-review` does).
- Check alert thresholds: too noisy or missed something?
- PSE watchlist reconstitution (`pse-watchlist-rebalance` §5): scan, score, apply entry/exit/buffer, write `pse_watchlist.json`, log, send one ADDS/DROPS/KEEPS message.
- Grade last month's watchlist adds and drops against the PSEi.

## 7. Optional helpers (only if one bot gets overloaded)
Sub-bots or subagents may do Step A research or the contrarian pass, but must return ≤15 lines with links, and only the main bot messages tako. Start with one bot; add helpers only when a pass regularly runs out of time.

## 8. Never
- Assume a fill. Send a plain-text reply outside the delivery tool. Flood tako with "no change" messages. Present a rumour as news. Change a plan silently.

## Sources
- Binance/UTC daily candle vs Manila (OKX `1Dutc` check, verified Nov 15 2026): https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1Dutc
- PSE Daily Quotation Report (PSEi, net foreign, block sales): https://documents.pse.com.ph/market_report/November%2012,%202026-EOD.pdf
- Pentoshi on reserves for monthly panic dips: https://threadreaderapp.com/thread/1676235702105776128.html
- Existing PH skills this loop calls: ph-stock-market-research, ph-stock-verdict, ph-trade-journal, ph-advisor-self-review (in /home/box/agent-data/workflows)

## Changelog
- v2 2026-11-17: PSE watchlist light check in the morning report and close recap; Friday reconstitution; the active list is read from `pse_watchlist.json`; Before the Bell "no edition" rule.
- v1 2026-11-15: first draft.
