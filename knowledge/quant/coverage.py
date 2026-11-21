#!/usr/bin/env python3
"""Write COVERAGE.md: per-symbol start/end, rows, calendar gaps, suspicious jumps."""
import sqlite3, pandas as pd, os
D = os.path.dirname(os.path.abspath(__file__)); c = sqlite3.connect(f'{D}/prices.db')
df = pd.read_sql('select symbol,market,date,close,source from prices', c, parse_dates=['date'])
out = ['# Price DB coverage', f'Generated {pd.Timestamp.now():%Y-%m-%d %H:%M} Manila. DB: knowledge/quant/prices.db', '',
       '| Symbol | Market | Source | Start | End | Rows | Biggest gap (days) | Moves >40% in a day |', '|---|---|---|---|---|---|---|---|']
for (s, m), g in df.sort_values('date').groupby(['symbol', 'market']):
    gap = g.date.diff().dt.days.max(); r = g.close.pct_change().abs(); jumps = int((r > 0.4).sum())
    jd = ', '.join(g.date[r > 0.4].dt.strftime('%Y-%m-%d').tolist()[:3])
    out.append(f"| {s} | {m} | {g.source.iloc[-1]} | {g.date.min():%Y-%m-%d} | {g.date.max():%Y-%m-%d} | {len(g)} | {int(gap) if gap == gap else 0} | {jumps}{' (' + jd + ')' if jumps else ''} |")
f = pd.read_sql('select * from fng', c); out.append(f"| FNG (Fear & Greed) | crypto | alternative.me | {f.date.min()} | {f.date.max()} | {len(f)} | | |")
dv = pd.read_sql('select market,count(*) n,min(ex_date) a,max(ex_date) b from dividends group by market', c)
out += ['', '## Dividends table'] + [f'- {r.market}: {r.n} rows, {r.a} to {r.b}' for r in dv.itertuples()]
out += ['', '## Known gaps', '- PSEi index: NO free full history found (Yahoo PSEI.PS returns only the latest bar; phisix has no index history; FMETF not exposed on PSE Edge chart). PSE tests use stock-level data only.',
        '- PSE prices are PSE Edge raw closes, NOT adjusted for dividends/splits (fine for dividend capture since the ex-date drop is real; long-horizon PSE returns understate total return by the yield).',
        '- PSE dividend history: PSE Edge disclosure search only reaches ~2 years back, so dividend capture uses ~Dec 2024 onward.',
        '- HYPE: Binance only lists HYPEUSDT from 2026-09-24, so HYPE history comes from Hyperliquid perp daily candles (Nov 2024 onward).',
        '- US prices: Yahoo; adj_close is split/dividend adjusted, backtests use adj_close. SPCX and IBIT are short histories.',
        '- Crypto daily bars are UTC-midnight candles (8 AM Manila).']
open(f'{D}/COVERAGE.md', 'w').write('\n'.join(out)); print('\n'.join(out))
