---
name: ph-stock-verdict
description: >-
  Use when asked whether to buy, sell, hold or how much to put into a PSE stock
  or REIT, to compare stocks, or to make a portfolio or order plan. It holds the
  scoring checklist, sizing for small budgets, order construction, verification
  gates and the output template.
---
# PH stock verdict (decision framework)

Inputs come from `ph-stock-market-research` (fresh this turn). Rules, fees and calendar come from `ph-market-playbook`. Wording follows `plain-language-market-brief`. Log every verdict with `ph-trade-journal`.
User-specific budget, broker, positions and risk level live in **memory**, never in this file.

## 1. Verdict labels (use exactly one)
| Label | Meaning |
|---|---|
| **Buy** | Good business, fair or cheap price, no near-term event against it |
| **Buy in parts** | Good, but split the entry (e.g. half now, half on a dip or after an event) |
| **Wait for ₱X** | Good business, price or timing not right. Name the price or event |
| **Avoid** | Weak thesis, untradeable risk (halt, tender talk, forced selling), or not suited to a beginner |
| Hold / Trim / Sell | For existing positions only |

## 2. Scoring checklist (score each 0–2; show the weak ones)
| Factor | 2 = strong | Check |
|---|---|---|
| Business quality / moat | Monopoly or franchise, prime assets, strong sponsor | Who owns it, what's hard to copy |
| Earnings trend | Growing YoY, not one-off | Latest quarter and 9M vs last year |
| Balance sheet | Low debt / net cash | Debt-to-equity, gearing for REITs |
| Valuation | Below peers and its own history | P/E, P/B, yield vs peers |
| Dividend | Declared on PSE Edge, growing, covered | Amount, ex/record/pay dates |
| Catalysts (next 1–8 weeks) | Positive event ahead | Ex-date, results, index adds |
| Event risk | None | Index deletion, rate decision, weather, regulation, dilution |
| Sentiment | Not crowded, improving | X, Before the Bell, analysts. Also owner activity: a running company buyback or several insider open-market buys = +; insider selling or repeated discounted block sales = − |
| Liquidity | Easy to buy and sell small size | Avg daily value (DQR): ≥₱20M = 2, ₱10–20M = 1 (half size), <₱10M = 0 |
- 14+ of 18 → Buy. 10–13 → Buy in parts or Wait. Under 10 or any red-flag event → Avoid. The score supports judgment; it doesn't replace it. Explain any override.

## 3. Comparison playbooks
**REIT vs REIT:** sponsor and pipeline · asset quality and location · occupancy · WALE · P/B (price ÷ NAV/book) · yield on declared DPS · DPS growth · gearing · dilution (infusion price vs market price) · next ex-date.
- When one is *quality* (premium P/B, best assets) and one is *value* (deep discount, faster growth), and both score well, **split equal pesos** rather than forcing a winner.

**El Niño / weather:** prefer gencos with merchant exposure and reliable plants (playbook §6). Treat water utilities as "Buy small, add on scare dips" if the thesis is intact. Remember the second-order effect: tight BSP → REIT headwind.

**Index deletion:** say **Wait** or **Avoid until after the effective-date close** (for PH, the last PSE trading day on or before MSCI's effective date). Revisit the next day.

**New listings / IPOs:** half size for the first 3 months; rethink level = the IPO price; note the stabilization end date and lock-up expiry.

**Dividend own-by dates:** if the own-by day is a risky day (new-engine go-live, holiday eve), buy one trading day earlier. Remember the ex-date drop.

**Bank vs bank (rate-hike cycle):** prefer the bank with profit growth, falling bad-loan ratio and NPL coverage ≥100% over the cheaper one with rising provisions.

## 4. Sizing for small beginner budgets
- Keep **30–50% cash** when known catalysts are within ~3 weeks (rebalances, BSP/Fed, ex-dates). Name the catalyst the cash is for.
- Watchlist names carry a **weight (% of PSE budget)** from `pse-watchlist-rebalance`; when the budget is unknown, show weights and "shares per ₱10k" (before and after the one-share-lot switch) instead of peso totals.
- Use 2–4 names max. Spread across different sponsors or sectors. Keep any single name ≤40% of invested pesos.
- Give the plan for **each budget tier** the user mentioned (e.g. low and high end), in shares and pesos.
- Avoid speculative names (halts, tender rumours, penny stocks) for first trades.
- Account for fees: with a ~0.69% round trip, no short-term flips on small sizes.

## 5. Order construction (every Buy / Buy in parts)
| Field | Rule |
|---|---|
| Shares | Board-lot multiple before the new engine; any whole number after (playbook §2) |
| **Limit** | At or slightly below the current bid/last. Never a market order |
| **Max price** | The highest price you'll ever pay. Don't chase above it |
| **Wrong if close below** | The level that breaks the thesis. Re-assess on a *close*, not intraday |
| Cost | shares × limit × ~1.003 (fees), rounded |
| Timing | Place by ~2:45 PM for same-day; mind the lunch break |
| Dividend timing | Must own by the close of the trading day **before** the ex-date |
- If the price falls through the limit, the order fills. Don't raise a limit when the market is already below it.

## 6. Verification gates (all must pass before sending)
- [ ] Price fetched this turn, with source and time.
- [ ] Dividends called "confirmed" **only** if on PSE Edge or a company disclosure. Otherwise "likely (source)".
- [ ] Dates checked against the playbook calendar and the holiday list.
- [ ] Lot size and fees applied; the peso totals add up and fit the budget.
- [ ] Every non-trivial claim has a link. Unverified items are marked.
- [ ] If you changed a previous call, say so plainly and why.
- [ ] Dividend-capture buys only when the cash yield is >= 2.5% and the name is already in its buy zone (quant-lab findings). Below that, say "no dividend trade".
- [ ] The call does not contradict a written rule (caps, regime rule, levels in the watchlist file).

## 7. Output template
```
**<TICKER> (₱price, as of time): <Label>.** <one-line why>
- Why it's good: … (2–3 bullets, numbers with sources)
- The catch: … (1–2 bullets)
- Play: buy <n> at ₱<limit> (≈₱cost). Never above ₱<max>. Rethink if it closes below ₱<wrong-if>.
**Orders by budget:** <tier>: … | <tier>: … (cash left ₱…)
Sources: …
_This is guidance, not a guarantee._
```
Then log each verdict with `ph-trade-journal`.

## Changelog
- v3.1 2026-11-20: dividend-yield floor and rule-consistency gates. Why: a dividend buy was suggested at a 1.41% yield, below the 2.5% backtest floor (2026-11-20-JFC-midday); 4 calls broke written rules in week 1.
- v3 2026-11-17: owner/insider activity in the Sentiment factor; liquidity scoring tiers; IPO, own-by-day and bank-vs-bank rules; watchlist weights when the budget is unknown.
- v2 2026-11-13: rebuilt from the Nov 13 session: labels, 9-factor score, REIT/quality-vs-value rule, El Niño and index-deletion rules, cash reserve, order fields, verification gates, template.
- v1: original file missing on disk at review time (2026-11-13); contents unknown.
