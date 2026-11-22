# 2026-11-22: switch from dip-buying to trend-following

Decision by tako: trend-follow; HYPE only during the paper test (tako picks every coin Nirvana trades).
Paper budget stays ₱10,000 (config) because at ₱5,000 a HYPE position can't satisfy 2% risk, a 2.7x ATR stop
and Binance's 5 USDT minimum at the same time (max ₱390 allowed vs ₱526 needed to stay sellable).
Re-size before any real deposit.

## Backtest (Binance spot daily candles 2024-06-06 -> 2026-11-22, 900 days; fees 0.1%/side; next-open fills; stops on intraday low)
| Strategy | SOL return / max DD | BTC return / max DD |
|---|---|---|
| Buy and hold | -58.6% / -76.3% | -14.9% / -53.0% |
| Weekly DCA | -43.9% | -25.5% |
| Hold only while close > SMA50 | -30.0% / -59.9% (29 trades) | +42.4% / -25.5% (29 trades) |
| SMA20 > SMA100 | -53.5% / -60.6% | -19.2% / -39.8% |
| Buy RSI<30, sell RSI>55, 2xATR stop | -64.5% / -72.4% (12 trades) | -33.5% / -50.0% (14 trades) |

HYPE has only ~60 daily candles on Binance (listed late Sep 2026): too short to test; the 4h version
(Oct 11 -> Nov 22) had buy-and-hold -27.6%, SMA50 filter -2.6%, RSI dip -8.4%.
Caveats: one mostly bearish regime, ~29 trades, no out-of-sample split. Consistent with FINDINGS.md #3
(50-day-high breakouts kept an out-of-sample edge).

## What changed in the bot
- New buy condition `above_sma: N` / `below_sma: N` for conditional tranches.
- New coin key `trend_exit_sma: N`: while holding, a daily close below SMA-N proposes SELL ALL
  (client id `nvt-`, human_only: asks YES in live, never runs unattended; paper executes it). The wrong-if stays
  as the automatic disaster stop.
- Plan 2026-11-22-hype-trend: HYPE buys only on a daily close above its SMA50 (today 61.5 vs 78.5 -> cash),
  capped at 82, ₱730, wrong-if 62, exits on a close below SMA50. Replaces the $57.5 dip limit.
- Known limit: a filled tranche doesn't re-arm under the same plan_id; re-entry after a trend exit needs a new plan.
