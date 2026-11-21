---
name: ticker-debate-memo
description: >-
  Use when asked about one ticker or coin in depth ("should I buy X?", "debate
  X", "bull vs bear on X", a memo, or comparing 2-3 names), for crypto or PSE:
  runs fundamentals, technicals, flows and news, a bull vs bear debate, then one
  plain buy/hold/sell memo with exact orders.
---
# Ticker debate → one memo (crypto or PSE)

PSE names: also apply `ph-stock-verdict` (scoring, labels, order fields) and its verification gates; this skill adds the debate and the PM memo. Crypto: rules from `crypto-trader-playbook`. Writing: `plain-language-market-brief`. Log every memo in the journal (memory).

## 1. Gather (fresh this turn, every number with source + Manila time)
| Pillar | Crypto | PSE |
|---|---|---|
| **Fundamentals** (Buffett/Munger: understand it, moat, owner-operator, price vs value) | What it does; revenue/fees and buybacks (e.g. DefiLlama); market cap vs FDV; unlock schedule (Cobie); holder concentration; competitors | 17-Q/17-A results on PSE Edge; P/E, P/B, yield vs peers and own history; debt; sponsor/owner; dividend record |
| **Insiders/owners** (insider *buying* is the stronger signal; sales have many reasons — idea commonly attributed to Peter Lynch [U]) | Team/VC wallet moves, treasury sales, unlock recipients | SEC Form 23-B / PSE director-dealing disclosures (`ph-legends-edge` §3); buybacks; placements (dilution) |
| **Technicals** (Hsaka/DonAlt) | Daily/weekly structure, key levels, distance to wrong-if | Same on daily/weekly; volume on breakouts; board lot/tick |
| **Flows/positioning** | Funding, OI, liquidations, exchange/ETF flows | Net foreign buying/selling for the stock, block sales, index events (MSCI/FTSE/PSEi) |
| **News/catalysts** | Listings, upgrades, unlocks, regulatory, macro (Fed) | Disclosures, ex-dates, BSP, peso, index reviews |
| **Sentiment** | CT from scored posters only (`ct-poster-scoring`); label confirmed vs rumour | Tracked PH X accounts, DragonFi Before the Bell |
| **What's priced** | `event-pricing-check` for any event inside the holding window | same |

## 2. The debate (write both sides honestly; the bear case is mandatory)
- **Bull (3 bullets max):** the strongest facts, each with a number and a link.
- **Bear (3 bullets max):** the strongest facts against. Ask: who is selling and why? What would make this −50%?
- **Contrarian check (GCR/Soros):** what does the crowd believe? Where is the consensus most likely wrong? Is this a reflexive boom (price → story → price) late in its cycle?
- **Pre-mortem (Light/Su Zhu):** "It's 3 months later and this lost 30%. Most likely why?" That reason becomes the thesis-wrong-if.
- **Judge:** which side has more *verified* facts (Tier A/B)? Rumours count zero.

## 3. Scenario math (Cobie's probabilistic thinking)
| Scenario | Probability | Price target | Return |
|---|---|---|---|
| Bull | p1 | | |
| Base | p2 | | |
| Bear (exit at wrong-if) | p3 | wrong-if level | |
Expected value = Σ p × return. **Only Buy if EV > 0 and the bear-case loss in ₱ fits the risk limit** (crypto ~5% of account per idea; PSE per `ph-stock-verdict` §4).

## 4. Memo labels (one only)
**Buy** · **Buy in parts** · **Wait for <price/event>** · **Hold** · **Trim** · **Sell** · **Avoid**.
Long-only by default (no shorting for tako). "Avoid" includes good stories at bad prices.

## 5. Memo template (fits ~1.5 phone screens)
```
**<TICKER> <price> (<time> Manila): <Label>.** <one-line thesis>
Bull: • … • …
Bear: • … • …
Crowd vs us: <what CT/PH X thinks; where we differ>
Priced in: <event odds / implied move, if relevant>
Odds: bull <p1>% → <target> | base <p2>% → … | bear <p3>% → exit at <wrong-if>. EV ≈ <+/-x%>.
Play: <orders: size, limit, max price>; add only if <confirmation>. Wrong if: <daily close level> or <thesis break>.
Max loss ≈ ₱<n>. Cash left ₱<r>.
Sources: <links>
_This is guidance, not a guarantee._
```

## 6. Comparing 2-3 names
Same pillars in a compact table (one row per name: price, valuation, catalyst, flow, risk, label). Pick one or split equal pesos if both pass (per `ph-stock-verdict` §3). Never pick by story alone.

## 7. Quality gates (all must pass)
- [ ] Prices fetched this turn; two sources for anything that drives an order.
- [ ] Bear case has at least one real fact, not a strawman.
- [ ] Every claim linked; unverified marked [U]; rumours labelled.
- [ ] Orders respect lots/ticks (PSE), min notional (Binance), and the risk limits.
- [ ] If this changes an earlier call, say "I've changed my mind" and why.

## Sources
- Buffett "Rule No. 1: never lose money", moats, margin of safety: https://www.cnbc.com/2013/08/30/ten-pieces-of-investment-advice-from-americas-greatest-investor.html
- Soros reflexivity boom/bust sequence: https://www.tandfonline.com/doi/full/10.1080/1350178X.2013.859415
- Cobie, scenarios and unlocks: https://cobie.substack.com/p/probabilistic-thinking , https://cobie.substack.com/p/on-the-meme-of-market-caps-and-unlocks
- Su Zhu / Light on invalidation and process: https://uncommoncore.co/transcript-for-13-light-and-su-zhu-on-the-art-of-trading/
- GCR contrarian notes: https://www.gate.com/learn/articles/gcr-the-most-famous-crypto-trader/2640
- PSE insider filings (Form 23-B examples on PSE Edge): https://edge.pse.com.ph/openDiscViewer.do?edge_no=67ac5c5f28956b10ec6e1601ccee8f59

## Changelog
- v1 2026-11-15: first draft.
