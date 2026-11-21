---
name: crypto-watchlist-rebalance
description: >-
  Use to run tako's crypto watchlist (Binance Spot, small account) like an index
  - the daily light check in the crypto briefs, the Friday full reconstitution,
  or any time tako asks to add, drop, refresh or "rebalance" coins, or asks
  about a coin that might belong on the list. Covers membership rules, Binance
  liquidity floors, scoring, buffer and caps, the BTC-linked rules, logging, the
  scan script and the card.
---
# Crypto watchlist rebalance (Binance Spot, index-style)

A small "index" of coins we would buy at our price on **Binance Spot**, run like the PSE list (`pse-watchlist-rebalance`): clear entry/exit rules, a buffer against churn, a Friday review, immediate changes only on a broken wrong-if or thesis.
Trading rules come from `crypto-trader-playbook` (spot only, wrong-if on a daily close, limits in parts, reserve, max 30% per coin, max loss per idea ~5% of the account). Wording: `plain-language-market-brief`. Anyone's call: `ct-poster-scoring` first. Event odds: `event-pricing-check`.
The list lives in the store as `crypto_watchlist.json`. Budget, fills and positions live in memory. tako has placed no trades unless they say so: never assume a fill.

## 1. Membership rules
| Rule | Setting |
|---|---|
| Universe | `universe` in the JSON (top coins by market cap with a Binance **spot** USDT pair; add names when a real catalyst appears). Check the pair with `data-api.binance.vision/api/v3/exchangeInfo?symbol=<SYM>USDT` (status TRADING) |
| Liquidity, core | Binance spot 7-day avg quote volume ≥ **$50M/day** |
| Liquidity, satellite | **$15-50M**: half size, limits only |
| Below $15M | Bench only (e.g. PAXG ~$11M on Nov 18) |
| Size | Max **10 active**; bench up to **6** |
| Caps | Max 30% of the crypto budget per coin; memecoins max 10% total and paper-traded first; max 2 coins per narrative (L1s, exchange tokens, AI, privacy, DeFi) |
| Reserve | ≥ 30% USDT always; ≥ 50% when the regime is Risk-off |
| Excluded | Stablecoins (they're the reserve), wrapped/staked copies, tokens with a big unlock inside 2 weeks unless the plan accounts for it, anything with a hack/depeg/delisting notice |
| Anchors | BTC and ETH stay listed even with a weak score (they set the regime) |
| Positions | A coin tako holds stays listed until sold |

Every entry: `ticker, cg_id, binance, name, theme, why, status (core / starter-size / wait / on hold), price, chg_pct, price_date, last_daily_close, buy_zone[], add_trigger, rethink_close_below (the "wrong if", daily close), size_tier, added, catalyst_date, catalyst_kind ("risk" for unlocks), notes` (+ optional `anchor`, `card_label`, `card_buy`, `card_rethink`). No peso amounts.

**Locked plans (change only when tako agrees or at a Friday review with a logged reason):** read the current plans for BTC, HYPE, SOL and any other coin from memory and the JSON. As of 2026-11-18: BTC buy $60,500, wrong if daily close < $52,300 (3x ATR14, quant-lab; changed 2026-11-20 from $57,000), add on a daily close > $68,000; HYPE buy $61 / $52 / $50, add on a daily close > $72, wrong if daily close < $45, cancel the $61 limit if BTC closes a day below $60,000 (HYPE/USDT trades on Binance Spot; unlock Dec 6 2026 = risk catalyst); SOL wait for a daily close > $78, then buy the retest, wrong if it closes back below $70 after entry.

## 2. Score (0-10, from `scan_crypto.py`; a screen, not a verdict)
| Factor | Points |
|---|---|
| Trend (daily closes) | +1 above 50-day, +1 above 200-day, +1 50-day above 200-day |
| Relative strength vs BTC, 30 days | ≥ +5 pts = 2, within ±5 = 1, worse = 0 |
| Binance liquidity | core = 2, satellite = 1 |
| Dated positive catalyst within 8 weeks | 2 (upgrade, ETF decision, buyback change); unlocks are `risk` = 0 |
| Structure | 1 if the last close is ≥ 10% above its 90-day low close (not making new lows) |
Entry floor **4** (crypto scores run low in a risk-off market). Anchors exempt.

## 3. Entry, exit and buffer
**Entry** needs: score ≥ 4 (or anchor), Binance spot pair TRADING, liquidity tier met, narrative cap respected, a written wrong-if on a daily close below a real low, and limits at levels that held before (range low, 90-day low, round number).
**Exit (to bench or out):**
- A **daily close** (UTC candle, 8 AM Manila) below the wrong-if → bench now, alert. A wick is not a close.
- Thesis break: hack, depeg, team exit, delisting notice, unlock overhang not in the plan → out.
- Score ≤ 2 at the Friday review (non-anchor), or Binance volume under $15M two Fridays running.
**Buffer:** a bench/universe coin replaces an active one only if it scores **≥ 2 above the weakest active**. Max **2 swaps per week** unless a thesis breaks. Open slots fill only at score ≥ 5 with core liquidity.
**Pre-publish check (every call, daily or Friday):** the levels in the call must equal the levels in the watchlist file and the locked plans above; if a level changes, change the file, the locked-plan line and the call in the same step and log why. Count narrative caps and the reserve rule, don't eyeball them.

Regime first (playbook §2): in **Risk-off**, new names enter as `wait` with deep limits only.

## 4. Daily light check (8 AM crypto brief after the 8 AM Manila daily close; 9 PM evening check uses live prices only)
1. `python3 scan_crypto.py --write`.
2. RETHINK flags (close below wrong-if) → bench + alert. BTC-linked rules (e.g. close < $60k → "cancel the HYPE $61 limit").
3. IN BUY ZONE / near buy / ADD TRIGGER flags → one line each.
4. Unlocks, upgrades, Fed/CPI in the next 5 days for listed coins.
5. Output one line per changed coin, or "Crypto watchlist: no changes."
6. No new names on a daily check unless a dated catalyst expires before Friday ("on review").

## 5. Friday full reconstitution (with the weekly review, after the Friday 8 AM close)
1. `python3 scan_crypto.py --full` → scores, ADD / DROP candidates.
2. Shortlist the top candidates plus any coin with real news; check FDV/unlocks, funding/OI (playbook), and that the pair is on Binance Spot.
3. Apply entry, exit, buffer, caps. Expand `universe` when a new narrative has real volume.
4. Set status, limits, add trigger, wrong-if, size tier for every active coin.
5. Write `crypto_watchlist.json`, append to `change_log`, re-render the crypto card.
6. One message to tako: ADDS / DROPS / KEEPS with price, buy zone, wrong-if and one-line reason.

## 6. Logging
`change_log` entry `{date, time, type, adds, drops, reasons{}, summary, card_text}` + memory journal line:
`CRYPTO WATCHLIST <date time>: ADD <SYM> (score n, reason, price) · DROP <SYM> -> bench/out (reason, price) · KEEP n · levels changed: <SYM> $a -> $b (why)`. Month-end: did adds beat BTC over 4 weeks?

## 7. Scripts and files
- `/workspace/watchlists/scan_crypto.py` (`--write`, `--full`) + `wl_common.py`; output `scan_crypto_out.json`. Data: Binance daily klines via `data-api.binance.vision` (api.binance.com is geo-blocked from the box), CoinGecko simple/price, alternative.me Fear & Greed. Never rerun `build_initial.py`.
- Store: `/cursor/stores/store-6ac17773-f8dc-4676-b121-c4dda169579c/crypto_watchlist.json`.
- Card: `make_infographic.py <date>/brief.json --fetch --only crypto --out <date>` → gauge, 4 price tiles, BTC chart, watchlist table (chips derived: Rethink / In zone / Near buy / status), today's adds/drops, bench.

## 8. Output format (chat)
```
**Crypto watchlist <date>: <n> coins. Regime <Risk-on/Chop/Risk-off>, F&G <x>.**
ADDED: <SYM> $<price> · buy $<a>/$<b> · wrong if close < $<c> · <why>
DROPPED: <SYM> -> bench · <why>
Near buy: ... · Rules hit: ...
Cash: keep ≥<r>% in USDT.
_This is guidance, not a guarantee._
```

## 9. Never
- Leverage, futures or margin on the list. Spot only.
- Add a coin because CT is piling in, or because it pumped today.
- Move a wrong-if lower to avoid taking it.
- Put peso amounts or positions on the public card.
- Swap coins silently.

## Changelog
- v1.1 2026-11-20: BTC locked wrong-if $57,000 -> $52,300 (3x ATR14) and a pre-publish level-sync check. Why: the Nov 20 call used $52,300 while the file and this skill still said $57,000 (2026-11-20-BTC-sitrep, 2026-11-18-BTC-wl).
- v1 2026-11-18: new. Binance liquidity tiers, 10-point screen with anchors, 2-point buffer, narrative caps, BTC/HYPE/SOL plans, daily check + Friday reconstitution, scan_crypto.py, card integration. Built from the Nov 18 list (BTC, HYPE, SOL, ETH, BNB, ZEC; bench XRP, NEAR, LINK, TAO, PAXG, SUI).
