---
name: crypto-trader-playbook
description: >-
  Use before any crypto call, entry, exit, sizing or "are we bottom?" answer for
  a small spot account: it holds the distilled rules of CT legends (Hsaka,
  Cobie, GCR, Ansem, Pentoshi, Light, CL207, DonAlt, Credible, Murad, Hayes),
  regime detection, positioning reads, sizing and the order template.
---
# Crypto trader playbook (legends distilled for a small spot account)

User data (budget, exchange, open orders, fills) lives in **memory**, never here.
Data: section 4. Wording: `plain-language-market-brief`. Logging: the journal in memory.
Event odds: `event-pricing-check`. Anyone's call: `ct-poster-scoring` first.

## 0. Hard rules (never break)
1. **Spot only by default.** No leverage for a beginner. If ever: max 2x, max 10% of the account, isolated margin, a set exit. Why: at 2x a ~50% move wipes the position (less after fees/maintenance margin); HYPE and alts move 30-50% in weeks. Spot can't be liquidated, so you get to be wrong and stay in the game.
2. **Every position has a "wrong if" on a daily close** (UTC close = 8:00 AM Manila, the Binance candle). Decide it before buying. A wick through it is not a close.
3. **Limit orders at levels decided in advance.** Never chase a green candle. If it runs without you, there's another trade.
4. **Buy in parts** (2-4 limits). Keep a stablecoin reserve (Pentoshi's "army": some attacks, some defends).
5. **Max per coin: 30% of the crypto budget. Max loss per idea (entry to wrong-if): ~5% of the account.** Size from the wrong-if distance, not from excitement.
6. **Memecoins: paper-trade first, real money max 10% of budget**, only after a written plan.
7. Never share a seed phrase/private key; no custodial Telegram bots; flag referral links and paid groups.

## 1. What the legends agree on (paraphrased; verified quotes are marked)
| Legend | Core idea that transfers to ₱5k spot | Source |
|---|---|---|
| **Hsaka** | Trade structure, not predictions: ranges, support/resistance, swing-failure (a sweep of a high/low that fails to hold). Read funding/OI as positioning: crowded longs get flushed, then rebuild. Verified: "Longs puke right before causing the dip, then rebuild immediately after funding... Observable in the OI." (Jan 17 2020) | TA thread, X |
| **Cobie** | Trading is probabilistic: list every scenario, estimate odds and payoff, buy where most scenarios pay, keep an exit for the bad one. Trade the "meta" (dominant narrative); if a trade finally "doesn't feel risky anymore," it's probably maximally risky. Check market cap vs FDV and unlocks. Verified: "95% of people reading this should probably not be actively trading" | Substack 2021 |
| **GCR** | Contrarian: bet against crowded consensus. How the market *reacts* to news matters more than whether the news is true. Add to winners, cut losers (not the reverse). Round numbers act as magnets/levels. Never short low caps. Most long-term believers do better holding BTC/ETH than trading | TechFlow/Viktor compilation, CoinDesk |
| **Ansem** | Split: ~70% conviction core, ~30% active "degen" bucket. Attention/mindshare drives memes. Be early; CT info lags. Admitted losing in 2022 partly from staring at charts all day | Cryptonews, BlockBeats |
| **Pentoshi** | Offense vs defense: route part of every win into stables to buy the monthly panic "nuke" (mean reversion). Take money off the table on big bounces. Exit on a pre-set daily close (e.g. "close below X = out"). Eliminate the "lose big" outcome and you win overall | Threadreader |
| **Light** (+ Su Zhu, same episode) | Light: optimize the process, not the result (poker EV); seek asymmetric, capped-downside payoffs; read narratives + order flow. Su Zhu: every trade needs a **price invalidation and a thesis invalidation**, plus a picture of what "right" looks like; making 3:1 half the time is a great trade. Documented mistake: Jan 2022 Light was early to a reversal and took a material drawdown, apologized publicly | Uncommon Core #13, X thread |
| **CL207** | Avoid liquidation above all (low leverage); smaller accounts often have better alpha than big ones; make your own decisions | Market Wizards ep.7 notes |
| **DonAlt** | High-timeframe (weekly/daily) charts cut noise; spot over leverage in chop; stay emotionally distant from hype | IQ.wiki, Technical Roundup |
| **Credible** | Elliott-wave targets; good 2023 BTC bottom calls, but third-party trackers grade deadline calls ~24% hit. Use as scenario map, not timing | Daily Hodl, OracleCheck |
| **Murad** | Memes = communities. Look for: 6+ months old, survived several big drawdowns, holder count rising monthly, big distribution + diamond hands | PANews |
| **Hayes** | Dollar liquidity drives BTC: Fed balance sheet up, RRP down, TGA down = bullish; reverse = bearish. Regime, not timing | cryptohayes.substack |

## 2. Regime check (do first, every brief)
| Signal | Risk-on | Risk-off |
|---|---|---|
| BTC daily structure | Higher highs/lows, reclaimed range | Lower highs, lost key level on a close |
| Dollar liquidity / Fed (Hayes) | Cuts priced, balance sheet growing | Hikes priced (check FedWatch/Polymarket), DXY at highs |
| ETF flows | Multi-day inflows | Multi-day outflows |
| Funding (OKX/Hyperliquid) | Mildly positive, rising with spot | Very positive + flat price = crowded longs; deeply negative after a dump = crowded shorts (squeeze fuel) |
| Open interest | Rising with price on spot volume | Rising into a drop (shorts piling) or collapsing (liquidations) |
| Fear & Greed | 25-75 neutral | <15 extreme fear (contrarian buy zone, not a timing signal) / >80 greed (trim) |
| CT mood (GCR/Cobie) | Mixed, skeptical | Everyone flipped one way in hours (squeeze/flush likely done) |
Label: **Risk-on / Chop / Risk-off**. Risk-off → only pre-set limit buys at deep levels, reserve ≥50%. Chop → range edges only. Risk-on → add on retests of reclaimed levels.

## 3. Entry/exit playbook (spot)
**Entries (pick one, write it down):**
- **Range low / support retest** (Hsaka): limit at a level that held 2+ times; wrong-if = daily close below the range.
- **Swing-failure / flush buy** (Hsaka, Pentoshi): after a liquidation wick under a known low that closes back above it. Buy the *second* test, not the first wick ("other cheek" double bottom).
- **Reclaim** (DonAlt): daily close back above a lost level, buy the retest; wrong-if = close back below.
- **Panic nuke** (Pentoshi): F&G <15 + funding negative + big liquidations → deploy a pre-set slice of the reserve.
**Exits:**
- Take 25-50% off into the next major level or after +40-100% (Pentoshi: remove capital on big bounces).
- Out fully on the wrong-if close. No averaging down below wrong-if.
- Thesis break (Su Zhu): the reason you bought is gone (e.g. unlock, hack, narrative dead) → exit even if price hasn't hit wrong-if.
- Rotate out when your coin becomes the meta and everyone is posting it (Cobie).

## 4. Data (all verified working Nov 15 2026 from the box; Binance/Bybit APIs blocked)
```bash
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,hyperliquid,solana&vs_currencies=usd&include_24hr_change=true"
curl -s "https://www.okx.com/api/v5/market/history-candles?instId=HYPE-USDT&bar=1Dutc&limit=30"  # UTC daily = Binance close (8 AM Manila)
curl -s "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"
curl -s "https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP"
curl -s "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=1H"
curl -s "https://www.okx.com/api/v5/public/liquidation-orders?instType=SWAP&uly=BTC-USDT&state=filled"
curl -s -X POST https://api.hyperliquid.xyz/info -H 'Content-Type: application/json' -d '{"type":"metaAndAssetCtxs"}'  # funding, OI, mark per coin
curl -s "https://api.alternative.me/fng/?limit=7"
```
- Funding is per period (OKX 8h, Hyperliquid 1h): say "longs pay shorts a little" in plain words. Annualize only for comparison.
- OKX `1D` bar is UTC+8; use `1Dutc` for the Binance-style close.

## 5. Sizing for a small spot account (example ₱5,000)
- Reserve ≥30% in USDT at all times; ≥50% in Risk-off.
- Ladder: 3 limits (e.g. ₱500 each) at structure levels, plus one "confirmation" buy only on a daily close above resistance.
- Loss check: (avg entry − wrong-if) ÷ avg entry × peso size ≤ ~₱250 (5% of ₱5k). If larger, cut size or move entries lower.
- Fees: Binance spot ~0.1% per side [U: check the fee page]; minimum order ~5 USDT [U]. ₱500 ≈ $7.8 at ₱63.8/USD (Nov 15 2026), above the minimum.
- Kelly sanity (Thorp): never size above half-Kelly; for a beginner with unknown edge, assume edge ≈ 0 → small fixed slices.

## 6. Sentiment and positioning read (5 minutes)
1. Price + 24h + distance from key levels.
2. Funding + OI change + long/short ratio + last-hour liquidations (which side got wiped?).
3. F&G. 4. ETF flow headline (Farside/press). 5. CT: 5-10 posts from scored accounts (`ct-poster-scoring`), split bulls vs bears, and note who *changed* their mind.
6. Contrarian test (GCR): what does everyone expect? What happens if they're wrong? Shorts squeezed in a 2-hour flip = relief, not proof of a bottom.

## 7. Output template
```
**<COIN> $<price> (<time> Manila): <Buy in parts / Wait for $X / Hold / Trim / Exit>.** <one-line why>
Regime: <Risk-on/Chop/Risk-off> — <2 signals>
Crowd: <who's bullish / bearish, linked>
Play: limits ₱<a> at $<x>, ₱<b> at $<y>; add ₱<c> only on a daily close above $<z>. Wrong if: daily close under $<w>. Max loss ≈ ₱<n>.
Cash left: ₱<r> USDT.
_This is guidance, not a guarantee._
```

## 8. Mistakes to avoid (from the legends' own admissions + our journal)
- Assuming a fill that the user never confirmed (our Nov 15 2026 error).
- Being early to a reversal with size (Light, Jan 2022): scale in, keep the reserve.
- Living on the charts (Ansem 2022): set alerts, close the app.
- Trusting PnL screenshots (see `ct-poster-scoring`).
- Averaging down into unlocks/high FDV (Cobie).

## Sources
- Hsaka TA lessons thread: https://en.rattibha.com/thread/1030321802403373057 ; funding posts: https://x.com/HsakaTrades/status/1218265373297872896 , https://x.com/HsakaTrades/status/1346852995481309184 ; profile summary: https://optimistfi.com/perps/traders/hsaka
- Cobie: https://cobie.substack.com/p/probabilistic-thinking , https://cobie.substack.com/p/trading-the-metagame , https://cobie.substack.com/p/on-the-meme-of-market-caps-and-unlocks , https://cobie.substack.com/p/tokens-in-the-attention-economy
- GCR: https://www.techflowpost.com/en-US/article/11871 , https://cryptonarratives.substack.com/p/compilation-of-the-best-gcr-nuggets , https://www.coindesk.com/markets/2022/02/17/how-the-big-short-dao-bet-against-the-crypto-market-and-won , https://www.theblock.co/news/markets/2022-05-09-trader-doubles-down-on-10-million-bet-against-do-kwon-by-shorting-luna-145739
- Ansem: https://cryptonews.com/exclusives/ansem-blknoiz06-on-solana-altcoins-bonk-and-2024-trading-strategies-ep-290/ , https://en.theblockbeats.news/news/54958
- Pentoshi: https://threadreaderapp.com/thread/1676235702105776128.html , https://threadreaderapp.com/thread/1478762010087092226.html
- Light: https://uncommoncore.co/transcript-for-13-light-and-su-zhu-on-the-art-of-trading/ , https://en.rattibha.com/thread/1484847981740261379
- CL207: https://wavewisdom.io/cl207-crypto-market-wizards-ep7-notes/ , https://blog.synfutures.com/master-trader-class-recap-with-trading-legend-cl207/
- DonAlt: https://iq.wiki/wiki/cryptodonalt (note: @CryptoDonAlt not found on X on Nov 15 2026 — renamed or gone)
- Credible: https://dailyhodl.com/2023/09/20/crypto-analyst-details-bitcoin-downside-targets-foresees-a-bull-market-once-btc-clears-this-level/ , https://oraclecheck.com/guru/credible-crypto-yt.html
- Murad: https://www.panews.io/articles/5mmwvodi
- Hayes: https://cryptohayes.substack.com/p/hallelujah , https://en.theblockbeats.news/news/31703
- Thorp/Kelly: https://web.williams.edu/Mathematics/sjmiller/public_html/341Fa09/handouts/Thorpe_KellyCriterion2007.pdf

## Source track record (graded weekly by call-scorecard)
| Source | Record | Note |
|---|---|---|
| Ansem (X) | Open | Nov 19 BTC bids $58k-61k; low through Nov 20 $61,290: not reached |
| Yahoo / CoinGecko data | Credit | Prices consistent across notes |

## Changelog
- v1.1 2026-11-20: added source track-record table from the first weekly scorecard.
- v1 2026-11-15: first draft from legend research; endpoints verified from the box.
