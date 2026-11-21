---
name: us-watchlist-rebalance
description: >-
  Use to run tako's US watchlists (stocks and ETFs, bought on Gotrade) like an
  index - the daily light check in the US pre-open brief, the Friday full
  reconstitution, or any time tako asks to add, drop, refresh or "rebalance" US
  names, or asks about a US stock or ETF that might belong on the list. Covers
  membership rules, liquidity floors, scoring, buffer and caps, logging adds and
  drops, the scan script and the card.
---
# US watchlist rebalance (stocks + ETFs, index-style)

Two small "indexes" of US names we would buy at our price: **Stocks** and **ETFs**. Like the PSE list (`pse-watchlist-rebalance`): clear entry and exit rules, a buffer so names don't flip in and out, a scheduled Friday review, and immediate changes only when a thesis or a rethink level breaks.
The list lives in the bot store as `us_watchlist.json`. tako's budget, positions and fills live in memory, never in the list. tako has placed no trades unless they say so: never assume a fill.
Wording follows `plain-language-market-brief`. Scheduled-event reads (Fed, CPI, earnings) use `event-pricing-check`. Anyone's stock call (X posts, screenshots) goes through `ct-poster-scoring` first.

tako is a beginner trading on **Gotrade** (fractional shares, so share price does not matter). Before suggesting an order, note "verify the ticker is in Gotrade" for anything new or niche (thin ETFs especially).

## 1. Membership rules
| Rule | Stocks | ETFs |
|---|---|---|
| Universe | `universe.stocks` in the JSON (liquid US large caps; add names freely when a real catalyst appears) | `universe.etfs` (broad index, sector, theme, gold, T-bills) |
| Liquidity, core | 20-day avg dollar volume ≥ **$500M** | ≥ **$50M** |
| Liquidity, satellite | $100-500M: half size, limits only | $10-50M: half size, limits only (e.g. UFO, ARKX) |
| Size | Max **14 active**; bench up to **8** | Max **10 active**; bench up to **8** |
| Theme cap | Max **3 per theme** (AI/semis, mega-cap tech, space, healthcare, staples, financials, energy...) | One fund per exposure (don't hold VOO and VTI both) |
| Must-have sleeves | — | Broad index core (VOO) + a cash sleeve (SGOV, ~T-bill yield) always on |
| New listings | Half size until 3 months after the IPO; note lock-up expiry (SPCX listed mid-2026) | Skip funds under 6 months old |
| Positions | A name tako holds stays listed until sold, even if it would be dropped (then it's "hold / trim" logic) | same |
| Spotlight | SPCX (SpaceX) is tako's high-conviction interest: always one highlighted row with its full plan, never the whole card | — |

Every active entry carries: `ticker, name, theme, why (catalyst in plain words), status (core / starter-size / wait / on hold), price, chg_pct, price_date, buy_zone[] (1-3 limits), add_trigger ("Daily close > $X"), rethink_close_below, size_tier (full / half / starter / parking), added, catalyst_date, notes` (+ optional `spotlight`, `dont_chase_above`, `contrarian`, `card_label`, `card_buy`, `card_rethink`). No peso amounts in the file or on the card.

Status meanings: **core** = a name we'd own long-term, buy in parts at the zone. **starter-size** = small first buy only (beaten down or volatile). **wait** = no buying until price comes to the zone or a trigger closes. **on hold** = no orders until a dated event passes (e.g. earnings tomorrow).

## 2. Score (0-10, from `scan_us.py`; a screen, not a verdict)
| Factor | Points |
|---|---|
| Trend | +1 close above 50-day avg, +1 above 200-day, +1 50-day above 200-day (0-3) |
| Relative strength vs SPY, 3 months | ≥ +5 pts = 2, within ±5 = 1, worse = 0 |
| Liquidity | core floor = 2, satellite = 1, below = 0 |
| Dated catalyst within 8 weeks | 2 (earnings, product event, index add, dividend). `catalyst_kind: "risk"` (unlock, lawsuit ruling) scores 0 |
| Pullback in an uptrend | 1 if 5-25% off the 52-week high **and** above the 200-day |
Entry floor **5**. **Contrarian slots:** max **2 per section** may sit below the floor if deeply discounted with a dated catalyst and a hard rethink level (Nov 18: NVDA; SMH and GLD in ETFs). Mark them `contrarian: true`.

## 3. Entry, exit and buffer
**Entry (to active)** needs all of: score ≥ 5 (or a contrarian slot), liquidity tier met, theme cap respected, a plain-words reason tako can repeat, buy zone at a level the chart has respected (50-day/200-day average, recent low, round number), and a rethink level below the last real low.
**Exit (to bench or out)** on any of:
- A **daily close** below the rethink level → bench now, alert tako (if they hold it: "rethink" message, not an auto-sell).
- Thesis broken: earnings miss with guide cut, fraud/regulator action, dilution, CEO exit with no plan → out.
- Score ≤ 2 at the Friday review (not a contrarian slot), or liquidity under the satellite floor two Fridays running.
- Catalyst passed with nothing new and score < 5 → bench on Friday.
**Buffer (anti-churn):** a bench/universe name replaces an active one at the Friday review only if it scores **≥ 2 points above the weakest active** name. Max **3 swaps per section per week** unless a thesis breaks. Open slots fill only with names scoring ≥ 6 at the core liquidity floor.
**Limits above market:** a buy limit at or above the last close is a market buy. Label it "buy now (starter)" with a reason, or move the limit below the close. Run the same pre-publish check as the other watchlists (caps counted, call levels equal the file).

**Levels:** re-set buy zones and rethink levels only at the Friday review or after earnings, never intraday because price moved.

## 4. Daily light check (US pre-open brief, ~8-9 PM Manila; US opens 10:30 PM Manila until Mar 2027, 9:30 PM in summer)
1. `python3 scan_us.py --write` (prices into the JSON, flags).
2. Any **RETHINK** flag (close below the level) → bench now, alert.
3. **IN BUY ZONE / near buy** names → mention which limits might fill tonight.
4. **ADD TRIGGER** (close above the add level) → say "add allowed" for that name.
5. Earnings / events in the next 5 days for active and bench names (`catalyst in Nd` flag) → set `on hold` the day before if the plan says so; reset levels the day after.
6. Output: one line per **changed** name only. If nothing changed: "US watchlist: no changes."
7. Don't add new names on a daily check unless a dated catalyst expires before Friday. Flag "on review" instead.

## 5. Friday full reconstitution (after the US close = Saturday ~5-6 AM Manila; run with the Friday weekly review using Friday's data)
1. `python3 scan_us.py --full --earnings` (scores universe + bench + active, prints ADD / DROP / REVIEW candidates, pulls next earnings dates from Nasdaq).
2. Shortlist: top candidates + any name with real news (earnings beat, guidance raise, index inclusion, big buyback, new product). Sanity-check each with a 2-line why and a chart look (50/200-day, last low).
3. Apply entry, exit, buffer and caps (§1, §3). Expand the universe when a new theme appears (e.g. add a space or nuclear name to `universe.stocks`).
4. For every active name set: status, buy zone(s), add trigger, rethink level, size tier, notes.
5. Write `us_watchlist.json` and append a `change_log` entry (§6). Re-render the US card.
6. Send tako one message: **ADDS / DROPS / KEEPS** with price, buy zone, rethink and the one-line reason for each change.

## 6. Logging
Append to `change_log` in the JSON and to the memory journal:
`{date, time, type: "REBALANCE" | "DAILY" | "BUILD", adds:[..], drops:[..], reasons:{TICKER: "one line"}, summary, card_text}`
Journal line: `US WATCHLIST <date time>: ADD <SYM> (score n, reason, price) · DROP <SYM> -> bench/out (reason, price) · KEEP n · levels changed: <SYM> $a -> $b (why)`.
Grade at month-end: did adds beat SPY over the next 4 weeks, did drops lag?

## 7. Scripts and files
- `/workspace/watchlists/scan_us.py` (`--write`, `--full`, `--earnings`), helper `wl_common.py`; output `scan_us_out.json`. Data: Yahoo chart API (User-Agent header), Nasdaq earnings-date API. Never rerun `build_initial.py` (it overwrites the lists).
- Store: `/cursor/stores/store-6ac17773-f8dc-4676-b121-c4dda169579c/us_watchlist.json`.
- Card: `/workspace/infographics/make_infographic.py <date>/brief.json --fetch --only us --out <date>` reads the JSON (prices refreshed on fetch), shows Stocks + ETFs tables, today's adds/drops, bench. Chips are derived: Rethink (closed below), In zone, Near buy (within 3%), else status.

## 8. Output format (chat)
```
**US watchlist <date>: <n> stocks, <m> ETFs. <one-line market read>.**
ADDED: <SYM> (<what it is>) $<price> · buy $<a>/$<b> · rethink < $<c> · <why>
DROPPED: <SYM> -> bench · <why>
Near buy tonight: <SYM> ($x vs zone $y), ...
_This is guidance, not a guarantee._
```

## 9. Never
- Present a list name as an order. Orders need tako's budget and a size (memory).
- Add a name because X accounts are piling in, or chase above a "don't chase" level.
- Make SpaceX (or any single name) the whole card.
- Put peso amounts or tako's positions on a public card.
- Swap names silently.

## Changelog
- v1.1 2026-11-20: limits above the market must be labelled buy-now. Why: XOM and XLE limits sat above the price, filled at once and fell (-2.5%, -1.0%) (2026-11-18-XOM-wl, 2026-11-18-XLE-wl).
- v1 2026-11-18: new. Mirrors pse-watchlist-rebalance: liquidity tiers in USD, 10-point screen with contrarian slots, 2-point buffer, theme caps, daily light check + Friday reconstitution, scan_us.py, card integration. Built from the Nov 18 list (12 stocks, 8 ETFs) after tako asked for broad, constantly updated US lists instead of a SpaceX-only card.
