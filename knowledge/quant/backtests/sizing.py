#!/usr/bin/env python3
"""Vol-based stop widths + equal-risk position sizes, and a check of our current plan's wrong-if levels."""
import json, os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import load, atr_pct
OUT = os.path.dirname(os.path.abspath(__file__)); R = json.load(open(f'{OUT}/results.json'))
def hitprob(sym, width, W, since='2023-11-19', HH=None):
    df = load(sym); c = df.close.values; idx = np.where(df.index >= since)[0]; idx = idx[idx < len(c) - W]
    mins = np.array([c[i + 1:i + 1 + W].min() / c[i] - 1 for i in idx]); return round(float((mins <= -width).mean()) * 100, 1)
rows = []
for s, v in R['vol'].items():
    m = v['market']; W = 30 if m == 'crypto' else 21
    stop = round(3 * v['atr14'], 1)  # 3 x current ATR14 (%)
    p = hitprob(s, stop / 100, W)
    rows.append(dict(sym=s, market=m, last=v['last'], vol20=v['vol20'], vol60=v['vol60'], atr14=v['atr14'], stop_3atr=stop, stop_price=round(v['last'] * (1 - stop / 100), 4 if v['last'] < 10 else 2),
                     noise_hit_30d=p, size_risk1pct_per_10k=round(100 / (stop / 100)), size_risk2pct_per_10k=round(200 / (stop / 100))))
# crypto: P5,000 account
for r in rows:
    if r['market'] == 'crypto':
        r['php5k_risk1pct'] = min(5000, round(50 / (r['stop_3atr'] / 100))); r['php5k_risk2pct'] = min(5000, round(100 / (r['stop_3atr'] / 100)))
plan = [  # (name, sym, entry, wrong_if close) from the current plan (parent summary, Nov 19)
    ('BTC buy 60,500 / wrong < 57,000', 'BTC', 60500, 57000), ('HYPE buy 61 / wrong < 45', 'HYPE', 61, 45), ('HYPE buy 52 / wrong < 45', 'HYPE', 52, 45),
    ('HYPE buy 50 / wrong < 45', 'HYPE', 50, 45), ('JFC buy 150 / rethink < 145', 'JFC', 150, 145), ('MER buy 395 / wrong < 370', 'MER', 395, 370)]
pc = []
for name, s, e, w in plan:
    width = 1 - w / e; m = R['vol'][s]['market']; W = 30 if m == 'crypto' else 21
    pc.append(dict(plan=name, sym=s, width_pct=round(width * 100, 1), atr_multiple=round(width * 100 / R['vol'][s]['atr14'], 1), noise_hit_30d=hitprob(s, width, W)))
json.dump(dict(table=rows, plan_check=pc), open(f'{OUT}/sizing.json', 'w'), indent=1)
print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(pc).to_string())
