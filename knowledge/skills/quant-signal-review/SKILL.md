---
name: quant-signal-review
description: >-
  Use when testing a trading idea or indicator, reviewing someone's strategy or
  backtest, cleaning market data, or deciding if a pattern is a real edge or
  luck: Simons-style signal-vs-noise checks, backtest review (drawdown,
  leverage, tail risk, overfitting, sample size, out-of-sample, fees/slippage).
---
# Quant signal review (is it an edge or luck?)

Default answer is **"luck until proven otherwise."** Most ideas fail; say so fast.
Helper: `bt_metrics.py` in this folder (daily long/flat backtest on OKX data, in/out-of-sample split, fees, max drawdown). Verified running Nov 15 2026.

## Mindset (what transfers from the legends)
- **Simons/Renaissance:** collect and clean data obsessively; test everything, expect most tests to fail; trust a model only after rules are fixed; edges are small and need many trades. Even Renaissance profits on "barely more than 50 percent" of trades (Zuckerman). So: many small edges + strict sizing, not one magic signal. Simons: "If you make money, you feel like a genius. If you lose, you're a dope." — outcomes fool you; check the process.
- **Bailey & López de Prado:** the more variants you try, the better the best one looks by chance (backtest overfitting). Count your trials; deflate the result.
- **Thorp/Kelly:** size from the edge you can *prove*. Overbetting can turn a winning edge into ruin; half-Kelly keeps ~75% of growth with far less drawdown.
- **Taleb:** the worst day matters more than the average day. Avoid strategies that win small often and lose huge rarely (short volatility, martingale/averaging down, high leverage).
- **Cobie/Light:** think in scenarios and process, journal decisions, review afterwards.

## 1. Idea intake (before any test)
- [ ] One-sentence hypothesis with a **reason** someone else loses (forced sellers, index funds, funding payers, retail FOMO). No reason → likely noise.
- [ ] Exact rules: entry, exit, size, timeframe, universe. Written **before** looking at results.
- [ ] Data needed and its source. Instruments we can actually trade (spot crypto on Binance, PSE via DragonFi).

## 2. Data hygiene (clean before testing)
| Check | Why |
|---|---|
| Time zone and candle close | OKX `1D` = UTC+8, `1Dutc` = Binance close; PSE closes 3:15 PM Manila. Mixing them shifts signals a day |
| Drop the still-open candle (OKX column 9 = "1" means confirmed) | Avoid using unfinished data |
| Look-ahead bias | Decide on today's close, trade tomorrow. Never use future highs/lows, revised data, or post-event index lists |
| Survivorship bias | Dead coins / delisted PSE names vanish from today's lists. Test on what existed at the time |
| Corporate actions (PSE) | Adjust for splits, stock dividends, rights; cash dividends drop price on ex-date |
| Gaps, zeros, duplicates, outliers | Check missing days, zero volume, fat-finger wicks; decide and document the fix |
| Liquidity | Can ₱ size actually trade at that price? PSE illiquid names: wide spreads, board lots |

## 3. Backtest review checklist (score each Pass/Fail; any Fail in bold rows = reject)
| # | Check | Pass rule |
|---|---|---|
| **1** | **Sample size** | ≥30 trades minimum, prefer 100+; covers ≥1 bull and ≥1 bear/chop regime |
| **2** | **Out-of-sample** | Rules frozen, then tested on later unseen data (last 30%) or walk-forward; OOS keeps most of the in-sample edge |
| **3** | **Costs** | Fees both sides (Binance spot ~0.1%/side [U]; PSE ~0.69% round trip per `ph-market-playbook`) + slippage (≥0.1% liquid, ≥0.5% small caps) |
| **4** | **Beats the simple benchmark** | Beats buy-and-hold or a 50/50 cash mix on return per unit of drawdown, not just total return |
| 5 | Max drawdown | Would tako survive it emotionally and financially? Report % and ₱ on the real budget |
| 6 | Time under water | Longest days below a previous peak; >6 months = most people quit |
| 7 | Tail risk | Worst day, worst week, worst month; gap risk through stops (crypto weekends, PSE trading halts) |
| 8 | Leverage | Re-run at 1x. If it only works with leverage, it's a leverage bet, not an edge. At 2x, check liquidation distance vs worst historical move |
| **9** | **Overfitting** | Few parameters (≤3); neighbors of the chosen parameter also work (e.g. 18/20/22-day all fine); number of variants tried is stated |
| 10 | Stability | Works in sub-periods and on similar assets (BTC and ETH, or 3+ PSE blue chips) |
| 11 | Trade concentration | Profit not from 1-2 trades; remove the best 2 trades and re-check |
| 12 | Capacity/execution | Orders realistic: limit fills not assumed at the exact low; PSE lunch break and closing auction |
| 13 | Deflated result | If you tried N variants, expect the best Sharpe to be inflated; require OOS confirmation, ideally a Deflated Sharpe/PBO check for N ≥ 20 |

## 4. Verdicts (use one)
- **Real edge (small size):** passes all bold rows + most others. Start at ¼ of normal size, track live for 20+ trades.
- **Maybe → paper trade:** promising but fails sample size or OOS. Paper-trade 4-8 weeks in the journal.
- **Luck → reject:** fails a bold row. Say why in one line. Log it (rejected ideas are knowledge too).

## 5. Sizing from a verified edge
- Kelly fraction f* ≈ edge ÷ odds (for win prob p and payoff b: f* = p − (1−p)/b). Use **≤ ½ Kelly**, and cap by the playbook limits (max 30% per coin, ~5% account loss per idea).
- Unknown edge = assume zero: tiny fixed slices only.

## 6. Strategy/claim review (someone else's backtest or "95% win rate" bot)
Red flags: no costs, no drawdown shown, only a chart of equity going up, win rate without payoff ratio, leverage hidden, start date cherry-picked after a crash, "AI" with no rules, paid access. Ask for: trade list, dates, fees, max DD, OOS period. Missing → treat as marketing.

## 7. Output template
```
**Idea: <one line>. Verdict: <Real edge (small) / Paper trade / Luck — reject>.**
- Test: <asset, dates, trades n, fees>
- In-sample vs out-of-sample: <+x% / +y%>, max DD <z%> (≈₱<n> on your budget), worst day <w%>
- vs buy-and-hold: <better/worse per unit of drawdown>
- Why it might be luck: <tried N variants / few trades / one regime>
- What to do: <size, or paper-trade for N weeks, or drop>
```

## Sources
- Zuckerman, *The Man Who Solved the Market* (notes): https://novelinvestor.com/notes/the-man-who-solved-the-market-by-gregory-zuckerman/ ; Mercer "50.75%" attribution: https://www.buildalpha.com/jim-simons-the-man-who-solved-the-market/
- Bailey, Borwein, López de Prado, Zhu, *The Probability of Backtest Overfitting*: https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Bailey & López de Prado, *The Deflated Sharpe Ratio*: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Thorp, *The Kelly Criterion in Blackjack, Sports Betting and the Stock Market*: https://web.williams.edu/Mathematics/sjmiller/public_html/341Fa09/handouts/Thorpe_KellyCriterion2007.pdf ; simulations: https://edwardothorp.com/wp-content/uploads/2016/11/KellySimulationsNew.pdf
- Taleb barbell / antifragile: https://www.tandfonline.com/doi/full/10.1080/14697688.2013.829244
- Cobie, probabilistic thinking: https://cobie.substack.com/p/probabilistic-thinking
- OKX candles API (verified): https://www.okx.com/api/v5/market/history-candles

## Changelog
- v1 2026-11-15: first draft + bt_metrics.py helper (tested on BTC-USDT and HYPE-USDT).
