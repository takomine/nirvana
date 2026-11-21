---
name: ph-trade-journal
description: >-
  Use when a verdict is given, an order is placed or filled, a position is sold,
  a dividend is received, or the user asks how their PSE positions are doing. It
  covers how to log verdicts and fills, track them against plan, and when to
  alert.
---
# PH trade journal

Rules: `ph-market-playbook`. Prices: `ph-stock-market-research`. Wording: `plain-language-market-brief`.
Positions and the user's budget are **user data**. Store them in memory journal entries (or the bot's store), never in skill files.

## 1. What to log (one entry per event, Manila time)
| Event | Fields |
|---|---|
| **Verdict** | date-time · ticker · label · price + source · limit · max · wrong-if · thesis (1 line) · key dates (ex/record/pay, catalysts) · confidence (low/med/high) |
| **Order placed** | ticker · shares · limit · placed time |
| **Fill** | ticker · shares · fill price (from the user's broker screen or confirm) · fees if known · cost basis/share |
| **Exit** | shares · price · reason (target, wrong-if, rebalance) · realized P/L after fees and tax |
| **Dividend** | ticker · DPS · shares · gross · 10% tax · net · pay date |
| **Plan change** | what changed and why (link to the new evidence) |
| **Watchlist change** | `WATCHLIST <date time>: ADD/DROP/KEEP` per `pse-watchlist-rebalance` §6, with price, score and reason, so adds and drops can be graded vs the PSEi 4 weeks later |
- Never log a fill the user didn't confirm. Until they do, it's "order placed (unconfirmed)".
- Record the fill price exactly as reported. Don't round.

## 2. Tracking check (on request, and in each pre-market brief when positions exist)
For each open position:
1. Last price (fresh) → unrealized P/L in ₱ and % after the ~0.40% sell cost.
2. Versus plan: above the limit? near max? below wrong-if on a **close**?
3. Upcoming dates: own-by date for the dividend, ex-date, pay date, index events.
4. Thesis still intact? (new disclosure, results, rate decision)
5. Cash left vs the planned reserve.

## 3. When to alert (send unprompted if a routine runs, otherwise mention it next time)
| Trigger | Message |
|---|---|
| Close below wrong-if | "Rethink <SYM>: closed ₱X below ₱Y. Here's what changed." Re-run `ph-stock-verdict` |
| Unfilled order and the price runs above max | "Don't chase. Cancel or keep waiting." |
| Price falls to a "Wait for ₱X" level | "<SYM> hit your buy-zone ₱X." |
| Own-by date for a dividend is tomorrow | Reminder with the exact date |
| Dividend confirmed on PSE Edge (was unconfirmed) | Upgrade the label |
| Major disclosure (results, placement, tender, halt) | 2-line summary + whether the plan changes |
| Block sale in a held or active-watchlist name (DQR) | Price vs that day's close (premium/discount) + whether a disclosure explains it |
| Net foreign > ₱1B either way in a day (DQR) | One line: who was bought/sold most |
| A watchlist name closes below its rethink level | Move to bench, tell the user in the close recap |
- No alerts for normal day-to-day noise inside the plan.

## 4. Position summary format
```
<SYM>: <n> sh @ ₱<cost> → ₱<last> (<time>) | <±₱> (<±%>) after fees | plan: max ₱… / wrong-if ₱… | next: <date event>
Cash left: ₱… (reserve target ₱…)
```

## 5. Feeding the self-review
Every verdict entry must have a price, date and label, so `ph-advisor-self-review` can grade it later. Missing fields go in the review as "ungradeable".

## Changelog
- v2 2026-11-17: watchlist-change log entry; alerts for block sales, ₱1B foreign days and watchlist rethink closes (patch from `ph-legends-edge` §6).
- v1 2026-11-13: new. Logging fields, tracking check, alert triggers, summary format.
