# Loot quant lab
- `python3 update_prices.py` : append new daily bars (crypto, US, PSE, Fear & Greed). `--full` refetches everything.
- `python3 pse_dividends.py [SYM ...]` : refresh PSE cash dividends from PSE Edge disclosures (~2 years reach).
- `python3 coverage.py` : rewrite COVERAGE.md.
- `cd backtests && python3 run_all.py && python3 sizing.py` : rerun all tests -> results.json, sizing.json.
- FINDINGS.md : keep / caution / drop verdicts and proposed rule changes.
