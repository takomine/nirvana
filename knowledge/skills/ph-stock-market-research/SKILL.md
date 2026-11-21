---
name: ph-stock-market-research
description: >-
  Use whenever you need PSE data, such as live quotes, disclosures, dividends,
  news, DragonFi Before the Bell, macro, or X sentiment, for a market brief, a
  stock deep-dive, or a journal check. It says which source to use for what, the
  exact endpoints, freshness checks, and how to cite.
---
# PH stock market research (data pipeline)

This skill collects facts. Rules and calendar: `ph-market-playbook`. Turning facts into a call: `ph-stock-verdict`. Writing it up: `plain-language-market-brief`.

## 1. Which source for what
| Need | First choice | Cross-check / fallback |
|---|---|---|
| Live or last price | phisix API (below) | stockanalysis.com/quote/pse/<SYM>/, the user's broker screenshot |
| **PSEi index level** | **PSE Daily Quotation Report (DQR)** for closes (§2) | DragonFi, BusinessWorld, @itradeph / @starallsec noon and close posts for intraday. **Not on phisix** (PSEI.json 404). Never infer the index |
| Net foreign, block sales, per-stock value traded | DQR (§2) | pseye.site/foreign-flow (Tier C) |
| Watchlist liquidity / flow / relative-strength scan | `pse-watchlist-rebalance` scan.py (uses the DQR) | — |
| Dividends (amount, ex, record, pay) | **PSE Edge** disclosure (edge.pse.com.ph, §2) | pseye.site/calendar (best lead list, sourced from PSE Edge), DragonFi headlines ("reported"), stockanalysis …/dividend/, filgit (leads only) |
| Valuation (P/E, P/B, yield, debt) | stockanalysis …/statistics/ | Company report on PSE Edge |
| Earnings | PSE Edge 17-Q/17-A, company press release | DragonFi Weekly Wrap-Up, BusinessWorld, Manila Times, Inquirer |
| Analyst / broker views | Philstar stock commentary (AB Capital), DragonFi Before the Bell | BusinessWorld |
| Morning overview | DragonFi Before the Bell API (below) | — |
| Week recap (results, macro) | DragonFi Weekly Wrap-Up (Fridays, ~3 PM) | BusinessWorld |
| Index changes | PSE memos (pse.com.ph), MSCI/FTSE press releases | News |
| Macro | BSP (rates, decisions), PSA (CPI, GDP), PAGASA ENSO advisories | News |
| Sentiment | Tracked X accounts (list in memory) via the `x` tools | FB pages (login-walled: skip unless a session exists) |

## 2. Exact endpoints (re-verified 2026-11-13, weekly review)
**Quotes (phisix):**
```bash
curl -s https://phisix-api3.appspot.com/stocks/AREIT.json
# -> {"stocks":[{"name":..,"price":{"amount":35.70},"percentChange":0.00,"volume":..,"symbol":"AREIT"}],"as_of":"2026-11-13T00:00:00+08:00"}
curl -s https://phisix-api3.appspot.com/stocks.json   # all stocks; no index rows
```
- Check `as_of` against today's date. It's often the last or current session, not tick-live. Say "as of HH:MM" or "last". After 3:15 PM on a trading day, treat it as the close.

**DragonFi blogs** (public, no login; the API version is **v2**, and v1 errors out):
```bash
B=https://api.dragonfi.ph/api/v2/Blogs
curl -s "$B/GetBeforeTheBellBanner"                                # latest editions: id, title, publishedDate, subCategory (29 Before the Bell, 30 Weekly Wrap-Up)
curl -s "$B/GetBlogsPagedList?SubCategoryIds=29&PageNumber=1&PageSize=3"   # 30 for Weekly Wrap-Up
curl -s "$B/GetInvestorsCornerList"                                 # featuredStory etc.
curl -s "$B/GetBlog?id=<id>"                                        # content (HTML), shortDescription, stockCodes, publishedDate
```
- Before the Bell sections: Today's Play, What to Watch (volume buzz, momentum, breakouts, support/resistance lists), Local Headlines.
- Article link: `https://dragonfi.ph/investors-corner/Pulse/<id>/<slug>`. Take the slug from the list or page if it's there; otherwise give the Investors' Corner link [U slug rule].
- Usually posts 8:15–9:00 AM Manila; some editions post in the afternoon (e.g. 2026-11-06 15:05), and some days have none (none Nov 16-17, 2026). **Only call it "today's" if `publishedDate` is today.** If there's none, don't promise it: the brief runs on the DQR + press, and the 9:05 add-on sends one "not out yet" line at most. Strip the HTML and never fill gaps.
- facebook.com/DragonFiHQ is login-walled. Use the API.

**PSE Edge** (curl works with a browser User-Agent; verified 2026-11-17):
```bash
UA="Mozilla/5.0"; E=https://edge.pse.com.ph
curl -s -A "$UA" "$E/autoComplete/searchCompanyNameSymbol.ax?term=JFC"        # -> cmpyId (JFC=86, MONDE=682)
curl -s -A "$UA" "$E/companyDisclosures/search.ax?keyword=<cmpyId>&sortType=date&dateSortType=DESC&pageNo=1"   # newest disclosures; rows carry openPopup('<edge_no>')
curl -s -A "$UA" "$E/openDiscViewer.do?edge_no=<edge_no>"                     # page has an iframe src=/downloadHtml.do?file_id=...; fetch that for the text
```
- The date filters on search.ax are ignored; filter rows by the announce date yourself.
- Link to disclosures as `https://edge.pse.com.ph/openDiscViewer.do?edge_no=<edge_no>`.
- Add `&tmplNm=Declaration+of+Cash+Dividends` (no keyword) for the market-wide dividend list.

**PSE Daily Quotation Report (DQR)**: PSEi OHLC, sector indices, per-stock value and net foreign, block sales. Recipe in `ph-legends-edge` §3a. Some dates 404 (e.g. Nov 2-6, 9, 13 when checked Nov 17): use the latest available and say its date.

**stockanalysis.com** blocks curl (a ~5 KB stub). Use WebFetch on `/quote/pse/<SYM>/statistics/` for P/E, P/B, yield, ROE, 20-day volume.

## 3. Freshness and verification checks
- [ ] Every number has a source and a timestamp (Manila time).
- [ ] The price came from this turn, not memory.
- [ ] Dividend dates are on PSE Edge; otherwise label them "reported (source)" or "unconfirmed (source)".
- [ ] Two independent sources agree before a number drives an order. If they differ, show both.
- [ ] Is today a trading day? Check the holiday list in `ph-market-playbook` §5.
- [ ] If a skill fails to load, say so and continue from the playbook drafts or memory.

## 4. X sentiment method
1. Read the `x-api-mcp-guide` skill before any X call.
2. Pull recent posts (24–72h) from the tracked accounts, then search `$<SYM>`, `<company name>`, `PSEi`.
3. For each account, log: tickers mentioned, stance (bull/bear/neutral), any levels (entry/target/stop), and the date. Keep these in the memory journal so the weekly review can grade sources.
4. Summarize consensus, disagreements, and crowding (many accounts piling into one ticker means caution).
5. Sentiment is Tier D: it never overrides Tier A facts. Note where the crowd disagrees with the news.

## 5. Market brief recipe (pre-market or midday)
1. Is it a trading day? Check the session phase.
2. Global overnight: US indices, US yields, oil, peso.
3. Before the Bell (today's edition, or the latest clearly dated).
4. PSEi level and change (from a cited source, see §1), foreign net flow, top movers and the reason for each (news or disclosure).
5. Macro and calendar items for the next 2–4 weeks (playbook §5).
6. X buzz summary.
7. Watchlist light check (`pse-watchlist-rebalance` §4).
8. Hand off to `ph-stock-verdict` for any calls, then write with `plain-language-market-brief`.

## 6. Single-stock deep-dive recipe
1. Quote, 52-week range, YTD move.
2. Business and moat (who the sponsor or owner is, what they own, contract length).
3. Latest results vs last year (revenue, profit, one-offs).
4. Valuation: P/E, P/B, yield vs peers and its own history; debt.
5. Dividend history, the next dates (PSE Edge), payout trend.
6. Catalysts and risks: index events, weather, rates, regulation, dilution (asset infusions, placements).
7. Sentiment (X, Before the Bell, analyst targets).
→ Feed the result into the `ph-stock-verdict` checklist.

## 7. Citing
- Inline links to the article or disclosure, with the date. Prefer Tier A, then B.
- Separate **facts**, **what the crowd says**, and **our view**.
- Never invent a price, date, target or dividend. If you can't find it, say "not found".
- For tables or long reports, write a Page (read the `canvas` skill first).

## Changelog
- v4 2026-11-17: DQR is now the PSEi/net-foreign/block source; verified PSE Edge per-company curl recipe; pseye calendar as the dividend lead list; stockanalysis via WebFetch; Before the Bell gap rule; watchlist light check step in the brief recipe.
- v3 2026-11-13: weekly review. PSEi is not on phisix (lesson 2026-11-13) → added an index-level row; added DragonFi Weekly Wrap-Up (subcategory 30) and Before the Bell section layout; "reported" dividend label; log X calls for source grading.
- v2 2026-11-13: turned into a pure data pipeline. Added the verified phisix and DragonFi v2 endpoints, the source map, freshness checks and the X method. Fixed the session hours (close 3:15, now in the playbook). Moved the verdict logic to `ph-stock-verdict`.
- v1 2026-11-12: first version (sources, brief steps, single-stock steps, rules).
