# Loot quant lab: backtests v1 (Thu Nov 19, 2026, Manila)
Data: knowledge/quant/prices.db (see COVERAGE.md). Code: update_prices.py, pse_dividends.py, backtests/run_all.py, backtests/sizing.py.
Raw results: backtests/results.json, backtests/sizing.json. Fees: Binance 0.10%/side, PDAX 0.40%/side (reported, unconfirmed), PSE 0.30% buy + 0.40% sell (+10% div tax), Gotrade 0.15%/side (ASSUMED spread, not published).
Samples under 20 trades are flagged weak. Out-of-sample (OOS) = last 30% of trades by date.

## KEEP (holds up, incl. out-of-sample)
1. **US: buy SPY/QQQ when VIX closes > 25 (better > 30).** SPY after VIX>30 (56 episodes since 2000): +4.4% avg over next 63 trading days vs +2.3% for a random day; 75% win; OOS +6.9% (17 trades). QQQ after VIX>30: +7.2% / 63 days, 75% win, OOS +8.4%. VIX>25: SPY +3.9% vs +2.3% (100 trades). Caveat: worst trade -26%; drawdowns while holding are real. VIX now 22.6 (Nov 19) -> not triggered.
2. **Volatility-based wrong-if levels.** Fixed % stops are wrong per asset. Within 30 days, a 5% drop happens after 54% of random BTC entries, 73% of HYPE entries, 48% of JFC entries (last 3 years). A stop at 3x ATR14 gets hit by normal noise ~18-27% of the time in crypto. Use 3x ATR14 as the default width.
3. **Crypto breakouts (close above the 50-day high), BTC/ETH/SOL/BNB/HYPE pooled:** +18.4% avg 30-day net return vs +7.2% random (130 trades), OOS +7.1% vs +2.4% (42 trades), 63% win. 20-day version weaker (OOS +3.7% vs +1.9%). Keep "add on a daily close above the recent high" for crypto, prefer the 50-day high.

## CAUTION (some edge, weak sample or fading)
4. **BTC after Fear & Greed <= 10:** 15 trades since 2018, 73% won over 30 days, +10.8% avg net (random entry +3.6%). But OOS (last 5) only +1.7%, and the 90-day result is noisy (worst -30%). F&G <= 15 / <= 20 / <= 25 show NO edge at 30 days (+2.0%, +2.3%, +0.9% vs +3.6% random) and are negative at 90 days. "Extreme fear = buy" only works at the very extreme, and it is weak evidence. F&G today = 10.
5. **Buy-in-parts ladders vs buying at once:** ladders win more often but lose on average. BTC 3 parts (now, -4%, -8%, unfilled parts bought after 30 days): beats lump-sum in 65% of starts, but average 90-day return 14.6% vs 17.8% lump. In falling markets the ladder adds +1.7 pts; in rising markets it costs -7.0 pts. Deep ladders fill rarely (BTC -10%/-20%: all parts filled only 22% of the time). US/PSE: SPY -3%/-6% beats lump only 45% of the time. Ladders are a regret/risk tool, not a return edge; keep them shallow and always set a "fill the rest by day X" rule.
6. **PSE dividend capture (buy 5 days before ex-date, sell at ex-date close), 56 events Dec 2024-Nov 2026, 14 names:** +0.70% avg net after fees and 10% tax, 61% win, OOS +0.60% (17). PSE stocks fell on average in this window (random 5-day net -0.68%). Price dropped only ~41% of the dividend at the ex-date open (median). Holding 5-10 days past ex-date added nothing (+0.5%/+0.7%, <50% win). Only ~2 years of dividend history -> caution; worth it only for yields >= 2.5% and with the stock in our buy zone anyway.
7. **PSE MSCI rebalance window (equal-weight basket of 14 watchlist names; dates DERIVED from MSCI's rule = last PSE trading day of Feb/May/Aug/Nov, 47 events 2015-2026):** 5 days before: -0.51% avg (32% up) vs +0.08% normal (t = -1.9); MSCI day: -0.21% (34% up; t = -1.3); 5 days after: +0.55% (62% up; t = +1.5). Supports "wait until after MSCI day" but not statistically strong; PSEi itself has no free history so this is a basket proxy.

## DROP
8. **Breakout "add" rule on PSE stocks:** 20-day-high breakouts across 14 PSE names: +0.16% avg per 21 days, 48% win, OOS -0.6% (vs -0.2% random). No edge after 0.7% round-trip costs. Do not use breakouts as an add trigger on PSE; use valuation/dividend/flow reasons.
9. **Breakout "add" rule on US stocks/ETFs:** +1.3% per 21 days vs +1.4% random entry (2,419 trades). No edge; buying breakouts is fine but not better than buying any day.
10. **F&G <= 15 / 20 / 25 as buy triggers for BTC:** no edge (see 4).

## Concrete changes to levels and sizing
- **BTC:** current plan buy 60,500 / wrong-if close < 57,000 is a 5.8% stop = 1.3x ATR; noise hits it within 30 days 49% of the time. Change: wrong-if ~3x ATR14 below entry (13.6% now -> ~52,300 from a 60,500 fill), and size down so the peso risk is the same: at 2% risk of P5,000 (P100), position ~P735; at 1% (P50), ~P368.
- **HYPE:** buy 61 / wrong 45 = 26% (3.3x ATR, ok, 16% noise-hit). Buys at 52 and 50 have only 13.5% / 10% room (1.7x / 1.3x ATR; 47% / 58% noise-hit). Either lower the wrong-if for those parts (~3x ATR = 24% -> ~39.5 from 52) or skip the 52/50 parts. The three limit parts (P1,500) risk about P250 to the 45 stop, about 5% of a P5,000 account, plus the P500 breakout add above 72 (37% above 45). Too much for one coin: cap HYPE at ~P209-418 per idea (1-2% risk at a 24% stop).
- **JFC:** buy 150 / rethink < 145 = 3.3% (1.1x ATR): noise hits it 62% of the time in 21 days. For a dividend trade, accept it as a "review" level, not a sell; if holding past ex-date, use ~9% (3x ATR -> ~136).
- **MER:** 395 / 370 = 6.3% (1.5x ATR), 23.5% noise-hit. Acceptable; MER's stop hits historically were rarely false (only ~12% recovered within 63 days).
- **Default rule:** wrong-if = 3x ATR14 (from sizing.json); position = (account x 1-2%) / stop width. Crypto at P5,000: BTC P368-735, ETH P263-526, SOL P259-518, BNB P385-769, HYPE P209-418, ZEC P138-276.
- **US:** keep VIX>25/30 as a "buy SPY/QQQ/VOO" trigger with Gotrade dollar orders; VIX now 22.6.
- **PSE:** drop breakout adds; keep "wait until after MSCI day" (caution); dividend capture only when yield >= 2.5% and the name is already a buy.

## Caveats
- Past results, small samples (esp. F&G <= 10, HYPE, PSE dividends), regime changes. Crypto 2018-2026 includes a huge bull market that flatters "buy" rules; we compare to random entry over the same period to correct for that.
- PSE prices are unadjusted closes from PSE Edge; one 59-day hole in 2020 (Edge data gap). No PSEi index history.
- Gotrade spread is an assumption (0.15%/side). PDAX fee 0.40% is reported, not published.
- MSCI dates are derived from MSCI's published rule, not a sourced list of each event.
