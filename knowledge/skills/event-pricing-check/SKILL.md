---
name: event-pricing-check
description: >-
  Use before taking a view on any scheduled event (Fed/BSP decision, CPI,
  earnings, token unlock, ETF decision, index rebalance, election) or when asked
  "is it priced in?": reads what futures, options, prediction markets and
  positioning already expect, then says what would surprise.
---
# Event pricing check ("what is the market already pricing?")

Rule (Druckenmiller/Soros spirit): you only make money on the **gap between the outcome and what was priced**, not on being "right" about the news. GCR: how price *reacts* to news tells you more than the news.

## 1. Steps
1. **Name the event, date and time in Manila** (US events usually land 2-4 AM Manila; FOMC statement 2:00 PM ET = 3:00 AM Manila next day in US winter, 2:00 AM in US summer).
2. **Read the odds** (section 2). Write "market expects X with ~Y%".
3. **Read the expected size of the move** (section 3).
4. **Read positioning**: funding, OI, long/short ratio, F&G (crypto); foreign flows and block sales (PSE). Crowded one way = asymmetric reaction to a surprise.
5. **Scenario table**: expected outcome / dovish (good) surprise / hawkish (bad) surprise → likely reaction and our action. Cobie-style: give each a rough probability.
6. **Decide**: pre-event orders only at levels that make sense in the bad scenario; keep reserve for after. Never bet the account on a binary event.
7. **After the event**: log outcome vs priced odds and the actual move vs implied move (feeds the weekly review).

## 2. Odds sources (verified Nov 15 2026 unless marked)
| Event | Source | How |
|---|---|---|
| Fed decision | **Kalshi** (works from the box) | `curl -s "https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker=KXFEDDECISION-26DEC"` → `yes_bid_dollars`/`last_price_dollars` = probability. Series `KXFEDDECISION-<YY><MON>` |
| Fed decision | CME FedWatch (fed funds futures) | https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html — curl blocked from the box; use the browser or press quotes. Method: futures price → implied average rate → hike/cut odds in 25 bp steps |
| Fed path, CPI, crypto prices, politics | **Polymarket** gamma API | `curl -s "https://gamma-api.polymarket.com/public-search?q=fed%20december&limit_per_type=3"` → `outcomePrices` (JSON string) aligned with `outcomes`. Check liquidity/volume; thin markets mislead |
| BTC/ETH price ranges by date | Polymarket/Kalshi price-bucket markets; Deribit options | as above |
| BSP decision | No futures. Use economist polls (BusinessWorld/Reuters/Bloomberg), BSP governor guidance, PH T-bill auction yields | Tier B press. Label "analyst consensus", not market odds |
| PSE earnings | No listed options. Use the stock's own average move on the last 4-8 results days (phisix/stockanalysis history) | Label "historical, not implied" |
| Token unlocks | Project docs / unlock trackers (e.g. Tokenomist) [U endpoint] | Size vs daily volume; who receives (team/VC = sell risk) |
| Index rebalance | MSCI/FTSE/PSE announcements (`ph-market-playbook` §5) | Passive selling/buying happens into the effective-date close |

Example (Nov 15 2026, 9 PM Manila): Kalshi Dec FOMC: hike 25 bp 0.86-0.88, hike >25 bp 0.09, hold 0.04 → **~95% some hike is priced.** A hold would be the big (bullish) surprise; a 25 bp hike is "as expected".

## 3. Expected move (how big a swing is priced)
- **From implied vol:** move (1 standard deviation, ~68% of outcomes) = spot × IV × √(days ÷ 365).
  - BTC/ETH IV: Deribit DVOL `curl -s "https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=3600&start_timestamp=<ms>&end_timestamp=<ms>"` (last value, %).
  - Example: BTC $65,500, DVOL 43.5 → 7 days: 65,500 × 0.435 × √(7/365) ≈ **±$3,950 (~6%)**.
- **From an at-the-money straddle** (call + put same strike/expiry, nearest after the event): straddle price ≈ 0.8 × the 1-SD move; use straddle × 1.25 for 1 SD. Deribit chain: `public/get_book_summary_by_currency?currency=BTC&kind=option` (prices in BTC; × index price).
- **HYPE/alts:** no deep options. Use realized vol (last 30 daily returns stdev × √365) as a proxy and say so.
- Compare: if implied move is small but positioning crowded → surprise risk underpriced. If implied huge and everyone hedged → "sell the news"/relief likely (GCR's inverse sell-the-news).

## 4. Positioning (who gets hurt by a surprise?)
- Crypto: OKX funding/OI/long-short and liquidations, Hyperliquid `metaAndAssetCtxs` (see `crypto-trader-playbook` §4).
- PSE: daily net foreign + block sales from the PSE Daily Quotation Report (`ph-legends-edge` §3).
- Sentiment: F&G; CT consensus from scored posters (`ct-poster-scoring`).

## 5. Output template
```
**<Event>, <date time> Manila: market expects <X> (~Y%).**
- Priced move: <asset> ±<n> (~<p>%) by <date> (<source>)
- Positioning: <crowded long/short/neutral, 1 line>
- If as expected: <reaction> → <our action>
- If good surprise (<what>, ~<p>%): <reaction> → <action>
- If bad surprise (<what>, ~<p>%): <reaction> → <action>
What this means for you: <1-2 lines tied to open orders/wrong-if>
```

## Sources
- CME FedWatch methodology: https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html
- Polymarket API docs: https://docs.polymarket.com/api-reference/markets/list-markets , https://docs.polymarket.com/market-data/market-details
- Kalshi API (public market data): https://api.elections.kalshi.com/trade-api/v2/markets
- Deribit DVOL endpoint: https://docs.deribit.com/api-reference/market-data/public-get_volatility_index_data ; book summary: https://docs.deribit.com/api-reference/market-data/public-get_book_summary_by_currency
- Expected-move math: https://optionsmovement.com/blog/how-to-calculate-expected-move-from-a-straddle , https://julianrsterling.com/articles/how-to-calculate-expected-move-from-implied-volatility/
- Druckenmiller, New Market Wizards (1992) on payoff vs being right: https://chian.io/projects/stanley-druckenmiller/sources/new-market-wizards-1992
- GCR on market reaction and inverse sell-the-news: https://www.techflowpost.com/en-US/article/11871

## Changelog
- v1 2026-11-15: first draft; Kalshi, Polymarket, Deribit endpoints verified from the box; FedWatch curl blocked.
