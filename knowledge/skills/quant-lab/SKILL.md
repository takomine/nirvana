---
name: quant-lab
description: >-
  Use before setting any entry, wrong-if level, position size or trigger, or
  when testing a trading rule: points to the local price database and backtest
  scripts and holds the backtest-verified rules (keep / caution / drop) that
  override gut-feel levels.
---
# Quant lab

Local research kit on the box at knowledge/quant/ (see README.md, COVERAGE.md, FINDINGS.md).
- prices.db: SQLite daily OHLCV (crypto from Binance/Hyperliquid, US from Yahoo, PSE from Yahoo .PS) plus Fear & Greed history. Refresh first: `python3 knowledge/quant/update_prices.py`.
- backtests/run_all.py (all rule tests, writes results.json), backtests/sizing.py (ATR/vol sizing, writes sizing.json), pse_dividends.py.
- Every number quoted must come from these files or a fresh download. Check out-of-sample (last 30%) and sample size (<20 = weak) before trusting a rule.

## Verified rules v1 (2026-11-19, data to 2026-11-18)
**Levels and sizing (apply to every call)**
- Wrong-if = about 3x ATR14 below entry (normal noise hits it only ~18-27% of the time in crypto). Fixed 5-8% stops in crypto get hit by noise ~50% of the time within 30 days: too tight.
- Position size = (1-2% of account) / stop width. Size from risk, not from a round peso amount. Cap any single coin idea at ~2% account risk.
- Ladders: keep shallow (now / -4% / -8%), with a 'buy the rest by day X' rule. Deep ladders (-10/-20%) rarely fill fully (~22%). Ladders win more often but average slightly less than buying at once.

**Keep**
- SPY/QQQ after VIX closes > 25 or > 30: better 3-month returns than random days, holds out-of-sample.
- Crypto: add on a daily close above the 50-day high (beats random days out-of-sample).

**Caution (small size, no conviction boost)**
- BTC when Fear & Greed <= 10: positive but small sample and fading recently. F&G 15-25 is NOT a buy signal (worse than random).
- PSE dividend capture (buy ~5 days before ex, sell on ex): ~+0.7% net, thin data.
- PSE: wait until after MSCI rebalance day to buy (weak evidence).

**Drop**
- Breakout-add rules for PSE (loses after costs) and US single stocks (no edge).

## Data gaps
No free PSEi history (use equal-weight watchlist basket); PSE prices not dividend-adjusted; PSE dividends ~2 years only; HYPE history from Dec 2024; Gotrade/PDAX fees are assumptions.

## Changelog
- v1 2026-11-19: first backtests; set 3x ATR stops, risk-based sizing, keep/caution/drop list.
