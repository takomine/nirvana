---
name: ph-market-playbook
description: >-
  Use as the reference for PSE rules, fees, taxes, board lots, the market
  calendar, the sector map (including weather and index-rebalance effects),
  source reliability and lessons learned. Check it before any PH market brief,
  verdict, order, or beginner explanation.
---
# PH market playbook (living reference)

Facts only. Each fact gets a status: **[V]** means verified from a primary source, with the date checked. **[U]** means unverified or inferred, so re-check it before stating it as fact.
How to collect data: `ph-stock-market-research`. How to decide: `ph-stock-verdict`. How to update this file: `ph-advisor-self-review`.

## 1. Trading session (Manila time, UTC+8)
| Time | Phase | Note |
|---|---|---|
| 9:00–9:30 | Pre-open | Orders are queued and the opening price is set by auction |
| 9:30–12:00 | Morning session | |
| 12:00–1:00 | Lunch break | No matching |
| 1:00–2:50 | Afternoon session | |
| 2:50–3:15 | Run-off / closing phase | Orders here trade only at the closing price under the new engine [V PSE forum deck]. Exact sub-phase times [U] |
| 3:15 | Close | Place day orders by ~2:45 |
- Times as used Nov 2026 [U]. Re-check on pse.com.ph after the new trading engine goes live.
- Settlement is T+2 [V CN-2023-0031]. Cash from a sale arrives 2 trading days later.
- Circuit breaker: if the PSEi falls 10%, 15% or 20%, the whole market halts for 15, 30 or 60 minutes [V CN-2020-0044]. The lower static price band was 30% in 2020; check the current one [U].

## 2. Lots and orders
- **New trading engine:** the standard lot becomes **1 share** and the odd-lot board goes away [V PSE new-engine FAQ]. Only **limit orders** work on day 1 [V FAQ]. Go-live date is **Mon Nov 23, 2026**, big-bang cutover with no parallel run [V pse.com.ph/pse-new-trading-engine + PSE FAQ, checked 2026-11-17]. Avoid placing important orders on go-live day itself; if a dividend own-by date falls on Nov 23, buy by Fri Nov 20 instead.
- **Before go-live, board lots by price band** (standard PSE table) [U: confirm on the broker ticket]:

| Price (₱) | Board lot |
|---|---|
| 0.50–4.99 | 1,000 |
| 5.00–49.95 | 100 |
| 50.00–999.50 | 10 |
| 1,000+ | 5 |
- The broker rejects any order that doesn't match the lot size or the price tick. Always use a **limit** order, never chase with market orders.

## 3. Costs and taxes (DragonFi-type online broker)
| Item | Rate | Status |
|---|---|---|
| Broker commission | 0.25% + 12% VAT | as used Nov 2026 [U: re-check the broker fee page] |
| PSE fee + SCCP fee | ~0.005% + 0.01% | [U] |
| Stock transaction tax (sell side only) | 0.1% | as used Nov 2026 [U: confirm current rate] |
| All-in buy | ~0.30% | derived |
| All-in sell | ~0.40% | derived |
| **Round trip** | **~0.69%** | derived. A trade must gain more than ~0.7% just to break even |
| Cash-dividend tax (final, withheld) | 10% | as used Nov 2026 [U: confirm current rate] |
- Minimum commission per trade: [U] check the broker. For tiny orders it can wipe out the gain.

## 4. Dividends: dates that matter
- Ex-date = 1 trading day **before** the record date [V CN-2023-0031].
- **To get the dividend you must own the stock by the close of the trading day before the ex-date.** Buying on the ex-date is too late.
- Expect the price to drop by about the dividend on the ex-date. Capturing the dividend isn't free money.
- Treat a dividend as **confirmed only after it's on PSE Edge or in a company disclosure**. Aggregators (filgit, stockanalysis) are leads, not proof. A Tier B report quoting the record and pay dates upgrades it to "reported", still not "confirmed".
- Yield = annualised declared DPS ÷ price. State whether it's before or after the 10% tax.

## 5. Calendar (update weekly; rolled 2026-11-13 to late Dec)
| Date | Event | Status |
|---|---|---|
| Nov 16–18, 2026 | Regular trading days despite the ASEAN summit | [V CN-2026-0051] |
| Nov 18, 2026 (~5 AM Manila) | Nvidia earnings (global risk mood; CEO change Nov 12 adds volatility) | [U] |
| Nov 18, 2026 | GCASH (Mynt) IPO price-stabilization window closes | [V PSE Edge, Mynt disclosure 17-Nov] |
| Nov 20, 2026 (Fri) | Own-by date for JFC ₱2.11 (ex Nov 23, record Nov 24, pay Dec 16) | [V PSE Edge C08010-2026] |
| Nov 23, 2026 | New trading engine (PSETradeX), one-share lots, odd-lot board ends | [V PSE new-engine page] |
| Nov 23, 2026 | Own-by date for MONDE ₱0.26 (ex Nov 24, record Nov 25, pay Dec 23); same day as engine go-live, so buy by Nov 20 | [V PSE Edge, MONDE 4-Nov] |
| Nov 24–25, 2026 | Cluster of REIT ex-dates (e.g. RCR ex Nov 24; AREIT record Nov 26 → ex Nov 25, pay Dec 11) | AREIT dates reported by DragonFi 13-Nov [U: confirm PSE Edge]; RCR [U] |
| Nov 27, 2026 (Fri) | Likely PH execution day for the MSCI Nov review (MER and TEL out of MSCI Philippines Standard; TEL and GLO in Small Cap; PLUS, MEG, SCC out of Small Cap). MSCI's official effective time is the **close of Nov 30**; because the PSE is closed Nov 30, PH trades happen at the **Nov 27 close**. Say "MSCI trade day Nov 27 (effective Nov 30)", never just one date | effective date [V MSCI 11-Nov-2026 release]; PSE closed Nov 30 [V]; Nov 27 execution [likely, standard MSCI practice] |
| Nov 30, 2026 | PSE holiday (Bonifacio Day), trading resumes Dec 1 | [V pse.com.ph holiday page, checked 2026-11-17] |
| Early Dec 2026 | PH Nov CPI release (Oct CPI was 7.8%, Q3 GDP 2.1%: stagflation risk) | Oct/Q3 figures per DragonFi wrap 13-Nov, PSA source [U: confirm PSA]; release date [U] |
| Dec 4, 2026 | FTSE Dec review final files | [V schedule] |
| Dec 8–9, 2026 | US Fed meeting (market expects hikes; UST 10Y ~5.1%) | [U] |
| Dec 10, 2026 | CREIT ex-date | [U] |
| Dec 17, 2026 | BSP Monetary Board rate decision (hike vs hold debated) | [U] |
| Dec 24–25 & Dec 30–31, 2026 | Likely PSE holidays / no trading | [U: confirm PSE holiday list] |
| Feb 9 / Mar 1, 2027 | MSCI Feb review announced / effective | [V MSCI schedule] |
| Mid-Feb & mid-Aug | PSE index reviews (PSEi, DivY, MidCap); results ≥5 trading days before | [V CN-2026-0033] |

## 6. Sector map: what moves what
| Driver | Winners | Losers / risks |
|---|---|---|
| BSP cuts, falling yields | REITs, property, banks' bond books | — |
| BSP stays tight or hikes (sticky inflation) | Banks' margins (mild) | REITs, property, high-debt names |
| Strong peso / falling oil | Importers, consumer, power costs | Exporters, remittance-linked consumption |
| **El Niño** (PAGASA: strong, into H1 2027 [V PAGASA outlook Nov 2026]) | Power gencos: demand up, spot prices up. AP is the cleanest per AB Capital; also ACEN, MER, SCC | Water utilities (MYNLD: supply-cut headlines), food, and hydro-heavy gencos. Food inflation keeps the BSP tight, which hurts REITs |
| Government price caps on WESM | — | Gencos' upside is capped |
| **Index deletion (MSCI/FTSE/PSEi)** | Buyers after the forced sell | The deleted stock sells off into the effective-date close. Wait until after it |
| Index inclusion | The added stock, before the effective date | Fades after |
| IPO price-stabilization ends (greenshoe) | — | Support only existed below the offer price; if the stock trades above it, the end date matters less. Lock-up expiry (months later) is the bigger supply event |
| Company buyback active (daily PSE Edge filings) | Price floor-ish near the buyback prices | Stops when the program is used up |
| Tender offer / delisting talk | Speculative pop | Trading halts, rule risk. Avoid as a beginner |
- REITs pay out ≥90% of distributable income, so they trade like bonds: sensitive to rates.
- Sponsor quality matters for REITs. The asset pipeline and infusion price tell you what the sponsor thinks the REIT is worth.

## 7. Source reliability tiers
| Tier | Sources | Use for |
|---|---|---|
| A (primary) | PSE Edge disclosures, PSE memos, **PSE Daily Quotation Report (DQR)**, BSP, PSA, PAGASA, MSCI/FTSE releases, company IR | Dates, dividends, results: the only basis for "confirmed" |
| B (quality press/broker) | BusinessWorld, Philstar stock commentary (AB Capital), Manila Times, Inquirer Business, DragonFi Before the Bell & Weekly Wrap-Up | Context, analyst views, movers |
| C (aggregators) | phisix API, stockanalysis.com, filgit, pseye.site (dividend calendar, foreign flow; built from PSE Edge/DQR) | Quick numbers. Cross-check before they drive a decision |
| D (crowd) | Tracked X accounts, FB investing pages | Sentiment only, never facts |
**Source track record** (graded by `ph-advisor-self-review`; judge over a month+):
| Source | Record so far | Note |
|---|---|---|
| DragonFi Before the Bell | 1 useful, 0 wrong (wk Nov 9–13). **Gaps:** no edition Nov 16 or 17 as of 12:40 PM Nov 17 (latest Nov 13) | 13-Nov: reported AREIT ₱0.679 DPS with record/pay dates (matched the filgit lead); "stay defensive, no rush to buy dips" held as power/telco names fell. Index-level calls ungraded (no PSEi close source) |
| Tracked X accounts | Ungraded | No dated calls logged yet. Log ticker, stance, level, date when used |
| FB investing pages | Ungraded | Login-walled; no calls logged yet; not cited in any graded call wk Nov 16-20 |
| DragonFi Before the Bell (wk Nov 16-20) | 2 credits, 1 soft debit | Nov 19 "stay defensive, keep cash" -> PSEi -3.1% next day (credit); "SCC Avoid" ₱9.15 -> ₱8.34 (credit); "MER slowly accumulate ~₱400" -> ₱378 (debit, open) |
| PSE DQR | Matched phisix on all names checked Nov 20 | Keep as index/flow source |
| Insider-buying posts (X, e.g. Smart Insider data) | Unproven | Information, not a call with a level; grade only when a level is given |

## 8. Glossary (beginner words)
- **Board lot:** the minimum share bundle you can trade.
- **Ex-date:** the first day a buyer no longer gets the dividend.
- **P/B (price-to-book):** what you pay for ₱1 of assets.
- **WALE:** the average years left on a REIT's leases.
- **Yield:** the dividend as a percentage of the price.
- **T+2:** the trade settles two trading days later.
- **Foreign net selling:** foreigners sold more than they bought.
- **MSCI/FTSE rebalance:** when global index funds must buy or sell to match an index change.
- **Stagflation:** slow growth plus high inflation at the same time.
- **Block sale:** a big pre-arranged trade done outside the normal order book.
- **Form 23-B:** the filing insiders (directors, officers, 10% owners) make when they buy or sell.
- **Buyback:** the company buying its own shares on the market.
- **Stabilization (greenshoe):** a bank's right to buy an IPO stock below the offer price for ~30 days after listing.
- **Relative strength:** how a stock did compared with the PSEi over the same days.

## 9. Lessons learned (newest first; added by `ph-advisor-self-review`)
- 2026-11-17: The MSCI date was quoted as both "Nov 27" and "Nov 30". Rule: say "MSCI trade day Nov 27 (effective close Nov 30; PSE closed Nov 30)". → §5
- 2026-11-17: DragonFi Before the Bell skipped Nov 16-17. Rule: never promise it; if `publishedDate` isn't today, use the DQR + press and say so in one line. → `ph-stock-market-research` §2
- 2026-11-17: DQR PDFs 404 for some dates (Nov 2-6, 9, 13 checked Nov 17). Rule: use the latest available and name its date. → `ph-stock-market-research` §2
- 2026-11-17: stockanalysis.com blocks curl (returns a ~5 KB stub). Use WebFetch for its statistics pages. → `ph-stock-market-research` §2
- 2026-11-13: Verdicts for the same names were revised three times in one afternoon (sizes changed each time). Rule: after a revision, resend one full replacement plan and say the earlier one is void. One-off so far; promote to `ph-stock-verdict` §6 if it repeats. → `ph-stock-verdict` §6
- 2026-11-13: phisix has no PSEi index quote (PSEI.json 404). Rule: get the index level from DragonFi/press and cite it; never infer it. → `ph-stock-market-research` §2
- 2026-11-13: A dividend was called "confirmed" when only filgit had it. Rule: Tier C alone means "likely". → §4
- 2026-11-13: An executor found 3 of 4 skills missing on disk. Rule: if a skill fails to load, say so and use the drafts or memory, and flag it to be restored. → `ph-advisor-self-review`
- 2026-11-13: The old research skill said the close was 3:00 PM. The session now ends 3:15. Always check hours here, not from memory.

## Changelog
- v4.1 2026-11-20: source track record from the first weekly scorecard (DragonFi credits/debit, DQR, insider-buying posts).
- v4 2026-11-17: watchlist rebalance day. New engine Nov 23 verified; Nov 30 holiday verified; MSCI wording fixed (trade day Nov 27, effective Nov 30); JFC, MONDE own-by dates and GCASH stabilization end added; DQR to Tier A, pseye to Tier C; stabilization and buyback rows in the sector map; 5 glossary terms; 4 lessons.
- v3 2026-11-13: weekly review. Calendar rolled to late Dec (REIT ex-date cluster, CPI, CREIT ex, year-end holidays [U]); added DragonFi Weekly Wrap-Up to Tier B; added source track-record table; "reported" dividend status; stagflation glossary; 2 lessons (PSEi source, verdict churn).
- v2 2026-11-13: rebuilt from the Nov 12–13 sessions: session table, new engine, fees, ex-date rule, calendar, El Niño and rebalance map, source tiers, lessons.
