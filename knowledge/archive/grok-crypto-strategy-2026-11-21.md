# Loot crypto strategy: rulebook for the bot

Migrated 2026-11-21, 10:45 PM Manila (UTC+8). tako holds **no crypto positions** right now. Never assume a fill.

**Short answer to "DCA, trend/indicator, or perps? Leverage?"**
It's **spot only, with no leverage, perps, futures or margin.** It isn't plain DCA either. Each trade is a **planned buy in parts, using limit orders at set levels**. Every position has a **"wrong-if" stop based on the daily close**, set at about 3x ATR14. Position size comes from risk: 1–2% of the account ÷ stop width. A **regime filter** decides how much to deploy and how much cash to keep. Indicators only help with timing. **A human confirms every order.**

Tags used below:
- **[BACKTESTED]** has numbers from `knowledge/quant` (FINDINGS.md, results.json, sizing.json; data to 2026-11-18).
- **[JUDGMENT]** is a discretionary rule from Loot's playbook. It was never tested.
- **[PLAN]** is a level from the live plan of 2026-11-21, 9:57 PM Manila.

---

## 1. Universe
- **Funded now [PLAN]:**
  - BTC
  - HYPE
- **Watch / wait (no money allocated) [PLAN]:**
  - ETH
  - SOL
  - BNB
  - ZEC
  - NEAR (limit at $2.60, but no peso amount is set, so the bot must not place it)
- **Watchlist bench (not tradable without a new plan):** XRP, LINK, TAO, PAXG, SUI, INJ.
- **Membership rules [JUDGMENT] (crypto-watchlist-rebalance):**
  - The coin needs a spot USDT pair with status TRADING.
  - Liquidity tiers, by 7-day average quote volume:
    - Core: at least $50M/day.
    - Satellite: $15–50M/day, at half size with limits only.
    - Under $15M/day: bench only.
  - At most 10 active coins, and at most 2 per narrative.
  - Excluded:
    - Stablecoins, which are the reserve.
    - Wrapped or staked copies.
    - Coins with a hack, depeg or delisting notice.
    - Coins with a big unlock inside 2 weeks, unless the plan accounts for it.
  - BTC and ETH are anchors and stay on the list.
- **Memecoins [JUDGMENT]:** paper-trade first. Real money is capped at 10% of the budget.
- **Venue:** PDAX is preferred (PHP pairs). Binance spot is allowed. Candles come from Binance USDT pairs, and every rule uses the **Binance UTC daily close, which is 08:00 Manila**.

## 2. Regime detection (do first, every run)
**[JUDGMENT]** (playbook §2). The bot automates these checks:

| Signal | Risk-off condition | Automated? |
|---|---|---|
| BTC vs 200-day SMA (daily closes) | close < SMA200 | yes |
| Fear & Greed (alternative.me) | < 15 (extreme fear) | yes |
| BTC spot ETF flows | multi-day outflows | **manual** (`regime.etf_flows_manual`) |

- **Risk-off:** at least 2 of the 3 signals.
- **Risk-on:** close > SMA50 > SMA200 and F&G < 80.
- **Chop:** everything else.
- The playbook also reads funding, open interest, liquidations, Fed/liquidity and CT mood. These are human inputs and are not automated.

**Behaviour by regime:**
- **Risk-off:** only pre-set limit buys at deep levels, small size, and wait for calm. Cash reserve ≥ 50%.
- **Chop:** buy only at the edges of the range.
- **Risk-on:** add on retests of reclaimed levels. Cash reserve ≥ 30% always.
- F&G > 80 means trim.
- **Dry run of 2026-11-21:** the regime is Risk-off. BTC closed at 58,951 against a 200-day SMA of 72,589 and a 50-day SMA of 77,718. F&G is 12, and ETF outflows were set manually.

Fear & Greed evidence:
- **[BACKTESTED, CAUTION]** BTC after F&G ≤ 10: 15 trades since 2018, 73% won over 30 days, average +10.8% net vs +3.6% for random days. Out-of-sample (last 5 trades) it was only +1.7%, and the worst 90-day result was −30%. Treat this as weak evidence.
- **[BACKTESTED, DROP]** F&G ≤ 15 / 20 / 25 as a buy trigger has no edge: +2.0% / +2.3% / +0.9% over 30 days vs +3.6% random, and negative at 90 days.
- So extreme fear is context for the regime, not a buy signal.

## 3. Entries
- **Limit orders at levels decided in advance; never chase a green candle [JUDGMENT].** A "market" buy in the plan becomes a **marketable limit capped at `max_price`**. If the price is above the cap, skip the buy.
- **Buy in parts, 2–4 tranches [JUDGMENT].**
  - **[BACKTESTED, CAUTION]** Ladders win more often but earn less on average. For BTC in 3 parts (now / −4% / −8%, with unfilled parts bought after 30 days):
    - The ladder beats a lump-sum buy in 65% of starts.
    - The average 90-day return is 14.6% for the ladder vs 17.8% for the lump sum.
    - In falling markets the ladder adds +1.7 points; in rising markets it costs −7.0 points.
  - Deep ladders (−10% / −20%) fill completely only 22% of the time.
  - Rule: keep ladders shallow (now / −4% / −8%) and add a "buy the rest by day X" deadline.
- **Entry types allowed [JUDGMENT]:**
  - Range-low retest.
  - Swing-failure / flush: buy the second test.
  - Reclaim: a daily close back above a lost level, then buy the retest.
  - Panic nuke: F&G < 15, negative funding and big liquidations, then deploy a pre-set slice of the reserve. This one always needs a human.
- **Never place a buy at or below the wrong-if.**
- **Indicators are timing aids only, with a mild edge at best [JUDGMENT]:** CCI turning up from below −100, and the Trend Pressure blue triangle. They can never override a level or the size.

## 4. Sizing formula
```
stop_width   = (entry − wrong_if) / entry          # wrong_if ≈ entry × (1 − 3 × ATR14%)
position_php = budget_php × risk_pct / stop_width  # risk_pct = 1% to 2%
```
- **[BACKTESTED]** basis: the 3x ATR14 stop width (see §5). Sizing from risk, rather than round peso amounts, comes from quant-lab v1.
- ATR14 is the simple mean of the true range over 14 days ÷ the last close. This matches `quant-lab/backtests/lib.py`.
- Caps:
  - Max **2% account risk per coin idea** (quant-lab). This is stricter than the playbook's ~5%; the bot uses 2%.
  - Max **30% of the budget per coin**.
  - Half-Kelly ceiling, and assume zero edge, so slices stay small.
- **Check of the current plan (₱10k budget):**
  - BTC: worst case to $52,300 is about ₱204, which is 2.0% of the budget.
  - HYPE: worst case to $48 is about ₱145, which is 1.5%.
  - Deployed: ₱2,600. Reserve: 74%.

## 5. Wrong-if / stop logic (daily close only)
- **Trigger:** a **UTC daily close** below the wrong-if means sell the whole position and cancel any open buys for that coin. A wick through the level is not a stop. Only closed candles count.
- **[BACKTESTED] Width = about 3x ATR14:**
  - Normal noise hits a 3x ATR14 stop only about 18–27% of the time in crypto.
  - Within 30 days, a 5% drop follows 54% of random BTC entries and 73% of HYPE entries (last 3 years).
  - Fixed 5–8% stops get hit by noise about 50% of the time. The old BTC plan (60,500 / 57,000 = 5.8%, 1.3x ATR) had a 49% noise-hit rate, so it was rejected.
  - 3x ATR14 per coin on 2026-11-18 (sizing.json):

    | Coin | 3x ATR14 stop | Noise-hit rate (30 days) |
    |---|---|---|
    | BTC | 13.6% | 17.5% |
    | ETH | 19.0% | 22.4% |
    | SOL | 19.3% | 27.2% |
    | BNB | 13.0% | 19.4% |
    | HYPE | 23.9% | 20.2% |
    | ZEC | 36.2% | 10.0% |
- **Never move a wrong-if lower to avoid taking it. Never average down below it.**
- **Thesis break [JUDGMENT]:** exit even above the wrong-if if the reason for buying is gone, for example a hack, a delisting, a team exit, or an unplanned unlock overhang. This is a human decision; the bot can only flag it.

## 6. Adds
- **[BACKTESTED, KEEP]** Add on a **daily close above the prior 50-day high close** (pooled BTC/ETH/SOL/BNB/HYPE):
  - Average 30-day net return +18.4% vs +7.2% for random days (130 trades).
  - Out-of-sample: +7.1% vs +2.4% (42 trades). Win rate 63%.
  - The 20-day version is weaker: out-of-sample +3.7% vs +1.9%.
  - The bot flags this signal; a human decides.
- **[PLAN / JUDGMENT]** Fixed triggers in tonight's plan:
  - BTC tranche 3 goes in after 2–3 calm days, or on a daily close above $62,000.
  - BTC daily close above $68,000 counts as strength and unlocks part of the cash.
- **"Calm days" in the bot [JUDGMENT, my definition]:** the last 2 closed daily candles each closed above $55,632 (the low of 2026-11-21) and had a true range ≤ 1.0x ATR14.
- Add to winners and cut losers, never the reverse [JUDGMENT, GCR].

## 7. Exits / take-profit [JUDGMENT, playbook §3; none of this is backtested]
- Take 25–50% off into the next major level, or after a +40–100% gain (Pentoshi).
- Exit fully on the wrong-if close.
- Exit on a thesis break.
- Rotate out when the coin becomes the dominant narrative and everyone is posting about it (Cobie).
- The bot should alert on these and not act on them.

## 8. Cash rules
- Tonight's plan keeps a ₱7,000 reserve as cash or USDT.
- **Deploy it only on:**
  - Strength: BTC daily close > $68,000.
  - A clean base: weeks of sideways BTC action.
- Either way, a human writes a new plan first. `bot_may_deploy_reserve: false`.
- Route part of every win back into stablecoins (Pentoshi's "army") [JUDGMENT].

## 9. Risk caps (summary)

| Cap | Value | Source |
|---|---|---|
| Leverage | 1x, spot only | playbook hard rule |
| Max per coin | 30% of budget | playbook, watchlist |
| Max risk per coin idea | 2% of budget (1% to 2% target) | quant-lab [BACKTESTED stop width] |
| Max total deployed | 70% normally, 50% in Risk-off (the plan uses 26%) | reserve rule |
| Memecoins | 10% of budget, paper first | playbook |
| ZEC | max 10% of budget | watchlist note |
| Narratives | max 2 coins each | watchlist |

## 10. Event blackouts [JUDGMENT]
No new buys during these windows. Existing wrong-ifs keep running.
- **HYPE token unlock 2026-12-06:** HYPE buys pause Dec 5–7.
- **Fed decision Dec 8–9 US time (about 3 AM Manila Dec 10; hike priced ~95% per the watchlist):** all buys pause Dec 8–10.
- Other dates to watch, which are context and not blackouts: MSCI Nov 27, BSP Dec 17.

## 11. Fees and execution
- Fees per side: Binance 0.10%; **PDAX 0.40% (reported, NOT confirmed)**. PDAX spreads are wider, so use limit orders.
- Binance minimum order is about 5 USDT (not verified). ₱500 is about 7.8 USDT at ₱63.94/USDT.
- PDAX has no ccxt support, so `PdaxAdapter` is a stub. For now, PDAX orders are placed by hand from the bot's dry-run intents.

## 12. What NOT to do
- No leverage, perps, futures, margin, or lending/earn products used as collateral.
- No market orders that chase, and no buying above `max_price`.
- No order without a human typing YES. Never run live mode from cron.
- No hard-coded API keys. Keys come from env vars only, with withdrawals disabled on the key.
- Don't act on intraday wicks for stops. Use closed daily candles only.
- Don't lower a wrong-if, and don't average down below it.
- Don't add a coin because CT is piling in or because it pumped today.
- Don't treat F&G 15–25 as a buy signal (backtested: no edge).
- Don't assume fills. Positions come from the exchange balance (live) or `state.json` (paper).
- Never share a seed phrase, never use custodial Telegram bots, and flag paid groups or referral links.

## 13. Conflicts found between the skills/files and the 2026-11-21 plan (need tako or Loot to resolve)
1. **HYPE wrong-if: the plan says $48, but `crypto_watchlist.json` and the watchlist skill's locked plan say $45.** The config uses $48 (the plan).
   - The $52 tranche to $48 is a 7.7% stop, about 0.9x of today's ATR (8.7%). That is far tighter than the 3x ATR rule.
   - FINDINGS.md already warned that a $52 buy against $45 (13.5% room, 1.7x ATR) has about a 47% noise-hit rate. It suggested either a wrong-if near $39.5 for that part or skipping it.
2. **The legacy rule "cancel the HYPE $61 limit if BTC closes a day below $60,000" has fired.** BTC's 2026-11-20 UTC close was $58,951.51, yet the plan buys HYPE at about $60 now. The config sets it to warn-only.
3. **HYPE buy levels changed:** the watchlist has $61 / $52 / $50 plus an add on a close above $72. The plan has ~$60 / $52 and no add trigger.
4. **BTC $57,000 tranche:** the stop width to $52,300 is 8.2%, about 1.7x ATR. That is below the 3x rule on its own, though the blended position is about 2.7x.
   - Today's 3x ATR14 from the $58,951 close is about $50,339 (ATR widened to 4.9%).
   - $52,300 was computed on Nov 19 (ATR 4.52%). The rule says never lower a wrong-if, so the bot keeps $52,300.
5. **Risk cap:** the playbook allows about 5% account loss per idea, while quant-lab caps it at about 2%. The plan fits 2%, and the bot enforces 2%.
6. **Ladder depth:** quant-lab says keep ladders shallow (now / −4% / −8%) with a "fill by day X" rule. The HYPE $52 tranche is about −13%, and no fill-by date is set.
7. **SOL closed at $68.88** (2026-11-20), below its $70 level. That level applies after entry, and tonight's plan says wait, so there is no action. **ZEC closed at $760.30**, sitting right on its $760 wrong-if. That level was never funded.
8. **Fed date:** the watchlist key_dates say Dec 9. The plan says Dec 8–9. The blackout covers Dec 8–10 Manila.
9. **Venue:** the watchlist skill is written for Binance Spot, but tonight's plan is all on PDAX. The levels are USDT prices, so PHP pairs on PDAX need converting.

## Sources
- Skills: crypto-trader-playbook v1.1, quant-lab v1, crypto-watchlist-rebalance v1.1, call-scorecard v1.1.
- Files:
  - `knowledge/quant/FINDINGS.md`
  - `knowledge/quant/backtests/{results,sizing}.json`
  - `knowledge/quant/backtests/lib.py`
  - `crypto_watchlist.json` (as of 2026-11-20 5:27 PM Manila)
  - `scorecard.jsonl` (crypto lines through 2026-11-21-crypto-overview)
