---
name: pse-watchlist-rebalance
description: >-
  Use to run the PSE watchlist like an index: the daily light check (pre-market
  and 3:30 PM close recap), the Friday full reconstitution, or any time the user
  asks to add, drop, refresh or "rebalance" PSE watchlist names. Covers
  membership rules, liquidity floors, scoring, entry/exit and buffer rules,
  caps, logging adds and drops, and the scan script.
---
# PSE watchlist rebalance (index-style)

The watchlist is a small "index" of PSE names we would buy, with membership rules like MSCI's: clear entry and exit rules, a buffer so names don't flip in and out, a scheduled full review, and immediate changes only when a thesis breaks.
Facts come from `ph-stock-market-research`. Rules, lots and the calendar come from `ph-market-playbook`. Each name's label, limit and rethink level come from `ph-stock-verdict`. Changes are logged with `ph-trade-journal`. Wording follows `plain-language-market-brief`. The user's budget and positions live in memory, never here.

## 1. Membership rules
| Rule | Setting |
|---|---|
| Universe | Every common stock in `phisix-api3.appspot.com/stocks.json` (exclude preferreds, warrants, ETFs, PDRs, dollar lines) |
| Liquidity, core | Avg daily value ≥ **₱20M** over the last 5-10 DQR sessions (`scan.py`) |
| Liquidity, satellite | ₱10-20M: allowed at **half size**, limit orders only |
| Price floor | Skip stocks under ₱1 ("basura") and anything halted, under tender/delisting talk, or flagged by the Exchange |
| Size | **Max 10 active** names; **up to 6 bench** names (watched, no orders) |
| Concentration | Max 3 per sector; max 2 per conglomerate group (e.g. SM: SM, SMPH, BDO, CBC) |
| New listings | Half size until 3 months after listing; know the stabilization end date and lock-up expiry |
| Positions | A name the user holds stays on the list until sold, even if it would be dropped (it moves to "Hold/Trim" logic in `ph-stock-verdict`) |

## 2. Score (0-24; refresh weekly, and for any name with news)
Use the 9 factors of `ph-stock-verdict` §2 (0-18) plus three flow factors (0-2 each):
| Flow factor | 2 | 0 |
|---|---|---|
| Net foreign, 8-10 sessions | Net buying and price holding | Heavy net selling (top 5 seller) |
| Relative strength vs PSEi, ~15 sessions | Beat the PSEi by ≥5 points | Lagged by ≥5 points |
| Company or insider buying | Active buyback or several insider open-market buys | Insider selling or discounted blocks |

## 3. Entry, exit and buffer
**Pre-publish rule check (every daily check, Friday review and on-demand take):** count names per sector and per conglomerate group against the §1 caps; confirm the watchlist file holds exactly ONE regime rule for the index (no second level that says the opposite); confirm each call's limit and rethink level equal the file. Fix the file or the call before sending.

**Entry (to active)** needs all of:
- Score ≥ 15/24, and liquidity tier met.
- A dated catalyst within ~8 weeks (results, dividend own-by date, index inclusion, buyback, BSP/peso effect) **or** clear relative strength with foreign buying.
- No pending index deletion or other forced selling before its effective date.

**Exit (to bench or out)** on any of:
- A **close** below the rethink level → bench immediately, alert (`ph-trade-journal` §3).
- Thesis broken: results miss, dividend cut, placement or dilution, tender talk, halt → out immediately.
- Score < 12 at the Friday review, or liquidity under ₱10M for two straight reviews.
- Catalyst passed (e.g. after the ex-date) and nothing new → bench at Friday's review.
- Index deletion announced → bench until the day after the effective-date close.

**Buffer (anti-churn, like MSCI's 'migration buffer'):** a bench or new name replaces an active name at the Friday review only if it scores **at least 2 points higher** than the weakest active name. Max 3 swaps per week unless a thesis breaks.

## 4. Daily light check (in the 8:05 AM report and the 3:30 PM close recap)
1. Closes for all active and bench names (phisix, check `as_of`).
2. Any close below a rethink level → move to bench now and alert.
3. PSE Edge disclosures since the last check for active and bench names (results, dividends, buybacks, 23-B, placements, tender, halt).
4. Yesterday's DQR: net foreign and block sales for each name.
5. Own-by dates in the next 5 trading days (and new-engine or holiday effects).
6. Output: one line per **changed** name only, e.g. "MONDE: own by Mon Nov 23 for ₱0.26; buy by Fri to avoid go-live day." If nothing changed: "Watchlist: no changes."
7. Do **not** add new names on a daily check unless a dated catalyst would expire before Friday (e.g. an own-by date this week). Flag "on review" instead.

## 5. Friday full reconstitution (with the weekly review, after the 3:15 close)
1. Run `scan.py` (below) for the liquidity table, 8-10 session net foreign and relative strength.
2. Shortlist: top 25 by liquidity plus any name with a dividend own-by date in the next 4 weeks (PSEye calendar as a lead, PSE Edge to confirm), a buyback, an index change, or a fresh results beat.
3. Score shortlist and current names (§2). Apply entry, exit and buffer (§3) and caps (§1).
4. For every active name set: label, limit(s), max price, rethink level, weight (% of PSE budget), board lot / per-₱10k share counts (`ph-stock-verdict` §4-5).
5. Write the result to the bot's store as `pse_watchlist.json` (fields in §7) and log the change entry (§6).
6. Send tako one message: ADDS / DROPS / KEEPS table with prices, limits, rethink levels and the one-line reason for each change.

## 6. Logging (memory journal, via `ph-trade-journal`)
`WATCHLIST <date time>: ADD <SYM> (score n, reason) · DROP <SYM> -> bench/out (reason) · KEEP n names · limits changed: <SYM> ₱a -> ₱b (why)`
Every add and drop carries the price and date so the Friday review can grade it: did added names beat the PSEi over the next 4 weeks, and did dropped names lag?

## 7. Watchlist file fields
`as_of, active[ticker, name, sector, price, price_time, status, verdict, limits[], max_price, rethink_close_below, weight_pct, catalyst, risks, dividend{dps, ex, record, pay, own_by, status}, avg_daily_value_mPHP, net_foreign_8d_mPHP, board_lot_before_nov23, per_10k_budget, sources[]], adds[], drops[], bench[], key_dates{}`

## 8. scan.py
`python3 scan.py [N]` downloads the last N available PSE Daily Quotation Reports (default 10; some dates 404, it skips them), then prints per stock: avg daily value, net foreign sum, % change vs the PSEi, and block sales. It writes `scan_out.json`. Copy it to /workspace first; it needs `pdftotext` (poppler-utils).

## 9. Never
- Present a watchlist name as a buy instruction. The list is "names we'd buy at our price"; orders still need `ph-stock-verdict` and the budget.
- Add a name because X accounts are piling in (crowding is a caution sign).
- Call a dividend "confirmed" unless it is on PSE Edge.
- Swap names silently. Every change is logged and told.

## Changelog
- v1.1 2026-11-20: pre-publish rule check. Why: one conglomerate group had 3 active names vs a cap of 2 for 4 days (2026-11-17-CBC-wl, 2026-11-17-SM-wl, 2026-11-17-BDO-wl); two contradictory PSEi regime rules were both live at the Nov 20 close (2026-11-18-PSE-mostly-cash).
- v1 2026-11-17: new. Index-style rules (liquidity tiers, 24-point score, entry/exit, 2-point buffer, caps), daily light check, Friday reconstitution, logging, scan script. Built from the Nov 17 rebalance (adds MONDE, CBC, SM; drops BPI, AREIT to bench).
