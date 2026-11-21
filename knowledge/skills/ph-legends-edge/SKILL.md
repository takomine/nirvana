---
name: ph-legends-edge
description: >-
  Use alongside the ph-* skills for any PSE call, brief or idea scan when you
  need Filipino investors' philosophies (Henry Sy, Truly Rich Club, Marvin
  Germo, PH educators, tracked PH X accounts) or PSE-specific edges not covered
  there: the Daily Quotation Report (PSEi, net foreign, block sales), insider
  23-B filings, flow and rebalance plays, BSP/peso links.
---
# PH legends and PSE edges (add-on to the ph-* skills)

Does **not** repeat what's already in `ph-market-playbook` (hours, lots, fees, taxes, ex-date rule, calendar, sector map, source tiers), `ph-stock-market-research` (phisix, DragonFi, PSE Edge), `ph-stock-verdict` (scoring, sizing, orders) or `ph-trade-journal`. Proposed patches to those files are in section 6.

## 1. Filipino investor philosophies (what transfers to a small DragonFi account)
| Who | Approach (paraphrased) | Use it as | Caution |
|---|---|---|---|
| **Henry Sy** (SM founder) | Long horizon (SM plans ~5 years out); buy land/assets cheaply in crises; stay in businesses you understand and aim to lead them; keep cash ready so you can move fast; "think big, start small, move fast." Philstar headline: "No such thing as overnight success or easy money" | Buy quality market leaders (SM, SMPH, BDO-type franchises) on panic dips; keep a cash reserve for crises | He bought businesses, not tickers; patience measured in years |
| **Truly Rich Club / Bo Sanchez** | "Strategic Averaging Method": only big "giant" companies, 5-15% max per stock, buy only below a "buy-below price" (≈15% under a target price), sell at target. ~₱997/month Gold membership | The discipline is fine: blue chips, position caps, pre-set buy prices | **Flag hype:** paid subscription; many reviews online are affiliate links (e.g. Smart Pinoy Investor discloses affiliate status); critics say targets can be wrong and the method can mean averaging down in long declines. Never pay for picks on a ₱-small budget |
| **Marvin Germo** (Stock Smarts) | Fundamentals to pick, technicals to time; don't buy a stock while it's falling — wait for a reversal; follow written rules, not emotion; cut losses without hesitation; size so a 5-10% loss is tolerable | Matches our "wrong if close below" rule; good for trend timing on PSE blue chips | Also sells seminars; judge rules, not marketing |
| **MoneyWise Engineer PH** | Dividend investing in stable, growing payers (check payout ratio and fundamentals), sometimes growth names with a margin of safety | REIT/dividend sleeve logic (yield must be covered and growing) | Dividend ≠ free money: price drops on ex-date |
| **Average Joe Investing** | Not verified this round (no primary page found) [U] | — | Re-check before citing |
| **Index option** | FMETF tracks the PSEi: one-ticket diversification | Default for "I just want PH exposure" | PSEi has lagged for years; check the trend before promising anything |

## 2. Tracked PH X accounts (verified profiles Nov 15 2026; Tier D sentiment until scored)
| Handle | Followers | Bio says | Treat as |
|---|---|---|---|
| @kirito600m | ~3.2k | Full-time trader, "posts are not recommendations", public journal | Trader sentiment; score live calls |
| @starallsec | ~0.8k | Star Alliance Securities, a PSE trading participant | Broker commentary (Tier B-/C) |
| @InsiderPHdotcom | ~4.6k | PH business news and analysis | News lead; confirm on PSE Edge |
| @itradeph | ~27.9k | Bonds, property, stocks, metals, PE, crypto | Macro/allocation views |
| @bn_trader | ~2.8k | Trader, automation; journal for offshore trades | Mostly non-PSE; low weight for PSE |
| @MerkadoBarkada | ~13.5k | Casual market analysis, memes, commentary | Daily color; confirm facts |
| @wmcabangon | ~5.5k | President, AAA Equities (a broker) | Broker/industry view |
| @mokongboy | ~1.9k | "Speculating about the weather" | Weather → power/water names (El Niño plays) |
Score each with `ct-poster-scoring` (live calls with dated levels). Until 10+ live calls are logged: sentiment only.

## 3. PSE edges (data and how to use them)
**a) PSE Daily Quotation Report (DQR) — free, official, one PDF a day (verified):**
```bash
D="November%2012,%202026"   # full month name, day without leading zero, year
curl -s -o dqr.pdf "https://documents.pse.com.ph/market_report/${D}-EOD.pdf" && pdftotext -layout dqr.pdf dqr.txt
grep -n -E "^PSEi|NET FOREIGN|FOREIGN BUYING|FOREIGN SELLING|BLOCK SALE" dqr.txt   # index OHLC, foreign totals, block sales
```
- Gives **PSEi open/high/low/close** (fills the "PSEi not on phisix" gap), sector indices, net foreign total, per-stock "Net Foreign" column, block sales list (security, price, volume, value).
- Posting time is not fixed: Nov 13's report was still 404 on Sun Nov 15 evening [U]. If 404, use the latest available and say its date. Example Nov 12 2026: PSEi 5,660.55 (−0.57%), net foreign +₱328.6M, block sales ₱814M (AC ₱315M, ICT ₱307M, MEG 65M shares ₱144M).
- Aggregator: pseye.site/foreign-flow (built from the DQR; showed +₱356M for Nov 12 vs DQR +₱328.6M — prefer the DQR; Tier C).
**b) Net foreign flows:** foreigners trade the big index names. Use **5-day and 20-day sums**, not one day. Sustained selling + weak peso = headwind for PSEi heavyweights; turning to buying after a long selling streak = early sign of a bottom. Per-stock: a name with steady foreign buying while the index falls = relative strength (Hsaka's "compare the exceptions").
**c) Block sales:** large negotiated trades outside the order book. Repeated blocks at a discount to the close = an owner or fund exiting (overhang); at a premium = someone paying up for size. Check the price vs that day's close and whether a disclosure explains it (placement, MSCI selling, crossing between related parties).
**d) Insider filings (SEC Form 23-B on PSE Edge):** directors, officers and 10%+ owners file changes; SRC Rule 23 = within 10 days after the end of the month of the change; PSE rules also require director/principal-officer dealings to be disclosed within 5 trading days (company insider-trading policies, e.g. Meralco, Nickel Asia). Search PSE Edge disclosures for "Statement of Changes in Beneficial Ownership". Read: open-market **buys** by several insiders = strongest signal; sales, option exercises and inter-family transfers mean less. Note blackout periods around results.
**e) Index rebalances (MSCI/FTSE/PSEi):** forced passive trades at the effective-date close. Deletions sell off into that close, often recover after; additions run up before, fade after. Watch the DQR block sales and closing-auction volume on that day. (Dates: playbook §5.)
**f) BSP and peso:** BSP hikes/hawkish holds hurt REITs, property, high-debt names; cuts help them. A weak peso (USD/PHP up; ₱63.8 on Nov 15 2026 per open.er-api.com) usually comes with foreign selling; strong peso the reverse. Check BSP decision dates in the playbook; use economist polls (no futures) via `event-pricing-check`.
**g) Earnings season:** 17-Q due ~45 days after quarter end; results days are where PSE names gap. Compare to consensus if a press source gives one; otherwise vs last year.

## 4. A PH routine (fits `daily-quant-loop`)
- Morning: yesterday's DQR (PSEi close, net foreign, blocks) + PSE Edge disclosures for watchlist (results, dividends, 23-B, placements) + DragonFi + PH X scan.
- 3:30 PM: closes, movers with reasons, wrong-if closes.
- Weekly: 5-day net foreign sum, top foreign buys/sells, insider buys found, block-sale overhangs, upcoming ex-dates and index events.

## 5. Beginner rules for PSE (on top of `ph-stock-verdict`)
1. Go where the outlook changed, not where the label is. Any liquid PSE name (blue chip, mid-cap, REIT, or a notable new listing/IPO) qualifies when a real catalyst improves its outlook: earnings beat or guidance up, rate cuts for banks/REITs, an index inclusion, insider or sustained foreign buying, a re-rating event. Size by quality and liquidity: blue chips/REITs full size; mid-caps or new listings half size with a tighter wrong-if. Still skip "basura"/penny stocks, thin names (low daily value traded), tender-offer rumours and halted names.
2. Buy panic, not hype (Henry Sy) — but only after the falling stops (Germo): wait for a higher low or a reclaim.
3. Never pay for stock picks; check affiliate links in "reviews".
4. Respect the ~0.69% round-trip cost: no quick flips on small orders.
5. A dividend is only "confirmed" on PSE Edge.

## 6. Patches to existing ph-* skills (applied 2026-11-17 with the watchlist-rebalance proposal, except where noted)
- `ph-stock-market-research` §1/§2: add the DQR as the **PSEi index and net foreign source** (curl recipe above); replace "PSEi not on phisix → DragonFi/press" with "DQR first, then DragonFi/press".
- `ph-market-playbook` §7 Tier A: add "PSE Daily Quotation Report"; Tier C: add pseye.site. §8 glossary: add "block sale" and "Form 23-B".
- `ph-stock-verdict` §2: add an optional "Insider/owner activity" note (insider buys = +, repeated discounted blocks = −) under Event risk / Sentiment.
- `ph-trade-journal` §3: add alert "block sale in a held name" and "net foreign >₱1B in a day".
- Status 2026-11-17: all four applied (research v4, playbook v4, verdict v3, journal v2). Glossary terms added. Watchlist membership moved to `pse-watchlist-rebalance`.

## Sources
- Henry Sy: https://business.inquirer.net/247880/henry-sy-playbook-9-lessons-phs-richest-man , https://www.philstar.com/lifestyle/business-life/2004/03/08/241793/henry-sy-145no-such-thing-overnight-success-or-easy-money146
- Truly Rich Club (affiliate-disclosed explainer): https://www.smartpinoyinvestor.com/blog/investing-in-the-philippine-stock-market-the-truly-rich-club-way/ ; critiques: https://pinoynextchapter.com/truly-rich-club-review/ , https://www.reddit.com/r/phinvest/comments/1719aro/truly_rich_club/
- Marvin Germo: https://www.linkedin.com/posts/marvin-germo-51333b8_on-cutting-losses-and-risk-management-filipino-activity-6903624294417715200-eUcF , https://www.linkedin.com/posts/marvin-germo-51333b8_fgen-ceb-agi-activity-6496033528424292352-yALr
- MoneyWise Engineer: https://dragonfi.ph/investors-corner/Featured-Pulse/334/Inside-the-Creators-Circle-%28September-2024%29:-Featuring-The-MoneyWise-Engineer-and-Kuya-Jon-Investing
- PSE DQR: https://documents.pse.com.ph/market_report/November%2012,%202026-EOD.pdf ; PSE data products: https://www.pse.com.ph/data-products/ ; pseye: https://pseye.site/foreign-flow
- SRC Sec. 23: https://lawplayer.com/ph/article/ra-8799/s0023 ; insider policies: https://www.meralco.com.ph/uploads/documents/legacy-documents/v2/governance/fe/meralco-doc-fe828afb326e2b6e.pdf , https://nickelasia.com/assets/documents/Policy_on_Insider_Trading.pdf
- MSCI Nov 2026 PH changes: https://bilyonaryo.com/meralco-pldt-to-exit-msci-philippines-standard-index-in-november-shakeup-digiplus-semirara-to-leave-small-caps/
- FMETF/PSEi: https://www.philstar.com/business/stock-commentary/2025/06/25/2453218/it-still-profitable-invest-psei
- X profiles via the x tools (get_users_by_usernames), Nov 15 2026.

## Changelog
- v1 2026-11-15: first draft.
- v1.2 2026-11-17: §6 marked applied; rule 1's "any liquid name" now has hard numbers in `pse-watchlist-rebalance` (≥₱20M core, ₱10–20M half size).
- v1.1 2026-11-15: rule 1 changed from "blue chips first" to catalyst-driven, any liquid name, sized by quality (tako: don't ignore names like GCash, MBT, CREIT when the outlook turns good).
