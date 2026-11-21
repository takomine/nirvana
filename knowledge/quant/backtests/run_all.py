#!/usr/bin/env python3
"""Loot quant lab backtests v1. Run: python3 run_all.py  -> results.json + results.md in this folder."""
import json, sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
OUT = os.path.dirname(os.path.abspath(__file__)); R = {}
CRYPTO = ['BTC', 'ETH', 'SOL', 'BNB', 'HYPE', 'ZEC']
US = ['SPY', 'QQQ', 'VOO', 'NVDA', 'AVGO', 'MSFT', 'AMZN', 'AAPL', 'LLY', 'COST', 'WMT', 'BRK-B', 'V', 'XOM', 'SMH', 'XLV', 'SCHD', 'XLE', 'GLD']
PSE = ['JFC', 'URC', 'MONDE', 'PGOLD', 'BDO', 'CBC', 'SM', 'ICT', 'AREIT', 'BPI', 'MER', 'PNB', 'AC', 'TEL']
MKT = {**{s: 'crypto' for s in CRYPTO}, **{s: 'us' for s in US}, **{s: 'pse' for s in PSE}}
H = {'crypto': (7, 30, 90), 'us': (5, 21, 63), 'pse': (5, 21, 63)}  # bars: crypto trades 7 days/week
DATA = {s: load(s) for s in MKT}
def pct(x, d=2): return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x) * 100, d)

# ---------- a. BTC after extreme fear ----------
btc = DATA['BTC']; f = fng().reindex(btc.index + pd.Timedelta(days=1)); f.index = btc.index  # FNG for day D is known at close of D-1
c = btc.close; a = {'base': {}, 'rules': {}}
for h in (7, 30, 90):
    fr = fwd(c, h)[f.notna()]; a['base'][h] = dict(mean=pct(fr.mean()), median=pct(fr.median()), pos=pct((fr > 0).mean(), 1), n=int(fr.notna().sum()))
for T in (10, 15, 20, 25):
    m = (f <= T); rr = {}
    for h in (7, 30, 90):
        fr = fwd(c, h)[m].dropna(); rr[h] = dict(days=int(len(fr)), mean=pct(fr.mean()), median=pct(fr.median()), pos=pct((fr > 0).mean(), 1))
    ep = episodes(m.fillna(False), 30); rets = {}; 
    for venue in ('binance', 'pdax'):
        fee = FEES[venue]
        r30 = [(c.iloc[i + 30] * (1 - fee)) / (c.iloc[i] * (1 + fee)) - 1 for i in ep if i + 30 < len(c)]
        d30 = [c.index[i] for i in ep if i + 30 < len(c)]
        rets[venue] = dict(stats=trade_stats(r30, d30), oos=oos(r30, d30))
    r90 = [c.iloc[i + 90] / c.iloc[i] - 1 for i in ep if i + 90 < len(c)]
    rr['episodes'] = len(ep); rr['episode_dates'] = [str(c.index[i].date()) for i in ep]
    rr['trades_hold30'] = rets; rr['episodes_90d'] = trade_stats(r90, [c.index[i] for i in ep if i + 90 < len(c)])
    a['rules'][T] = rr
a['buy_hold_btc_since_fng_start'] = pct(c.iloc[-1] / c[f.notna()].iloc[0] - 1, 1)
a['random_entry_30d_net_binance'] = pct(((c.shift(-30) * 0.999) / (c * 1.001) - 1)[f.notna()].mean())
a['fng_today'] = int(fng().iloc[-1]); a['last_date'] = str(c.index[-1].date())
R['a_fng'] = a

# ---------- b. ladders vs lump sum ----------
def ladder(sym, steps, W, Hh, every):
    df = DATA[sym]; c, lo = df.close.values, df.low.values; res = []
    for i in range(0, len(c) - Hh - 1, every):
        p0 = c[i]; parts = [p0]; filled = 1; chase = [p0]
        for s in steps:
            lim = p0 * (1 - s); j = np.where(lo[i + 1:i + 1 + W] <= lim)[0]
            if len(j): parts.append(lim); chase.append(lim); filled += 1
            else: chase.append(c[i + W])
        n = len(steps) + 1
        end = c[i + Hh]
        lump = end / p0 - 1
        cash_kept = (sum(end / p for p in parts) + (n - len(parts))) / n - 1   # unfilled parts stay as cash (0%)
        chased = sum(end / p for p in chase) / n - 1                                  # unfilled parts bought at day-W close
        avgp_chase = n / sum(1 / p for p in chase)
        res.append((lump, cash_kept, chased, avgp_chase / p0 - 1, filled == n, len(parts) - 1, df.index[i]))
    d = pd.DataFrame(res, columns=['lump', 'cash', 'chase', 'avgp', 'allfill', 'nfill', 'date'])
    up = d[d.lump > 0]; dn = d[d.lump <= 0]
    return dict(starts=len(d), fill_all_pct=pct(d.allfill.mean(), 1), avg_parts_filled=round(float(d.nfill.mean()), 2),
                lump_mean=pct(d.lump.mean()), ladder_cash_mean=pct(d.cash.mean()), ladder_chase_mean=pct(d.chase.mean()),
                ladder_chase_beats_lump_pct=pct((d.chase > d.lump).mean(), 1), ladder_cash_beats_lump_pct=pct((d.cash > d.lump).mean(), 1),
                avg_price_vs_day0_chase=pct(d.avgp.mean()), in_down_markets_chase_minus_lump=pct((dn.chase - dn.lump).mean()),
                in_up_markets_chase_minus_lump=pct((up.chase - up.lump).mean()), since=str(d.date.min().date()))
b = {}
for s in ['BTC', 'ETH', 'SOL', 'BNB', 'HYPE']:
    for st in [(0.04, 0.08), (0.08, 0.15), (0.10, 0.20)]:
        b[f'{s} -{int(st[0]*100)}%/-{int(st[1]*100)}%'] = ladder(s, st, 30, 90, 7)
for s in ['SPY', 'QQQ', 'NVDA', 'XOM', 'JFC', 'URC', 'BDO', 'SM', 'ICT', 'MER']:
    for st in [(0.03, 0.06), (0.05, 0.10)]:
        b[f'{s} -{int(st[0]*100)}%/-{int(st[1]*100)}%'] = ladder(s, st, 21, 63, 5)
R['b_ladder'] = b

# ---------- c. stop-hit frequency (last 3 years) + ATR stops ----------
cs = {}; cutoff = pd.Timestamp('2023-11-19')
for s, m in MKT.items():
    df = DATA[s]; atr = atr_pct(df); W = 30 if m == 'crypto' else 21; HH = 90 if m == 'crypto' else 63
    c = df.close.values; idx = np.where(df.index >= cutoff)[0]; idx = idx[idx < len(c) - HH]
    if len(idx) < 100: continue
    mins = np.array([c[i + 1:i + 1 + W].min() / c[i] - 1 for i in idx]); endr = np.array([c[i + HH] / c[i] - 1 for i in idx])
    a_at = atr.values[idx]
    row = {'entries': int(len(idx)), 'atr14_median_pct': pct(np.nanmedian(a_at))}
    for X in (0.05, 0.08, 0.10, 0.15, 0.20, 0.25):
        hit = mins <= -X; row[f'hit_{int(X*100)}'] = pct(hit.mean(), 1)
        row[f'false_{int(X*100)}'] = pct((endr[hit] >= 0).mean(), 1) if hit.sum() else None  # hit, but price back above entry at end horizon
    for k in (2, 3, 4):
        hit = mins <= -k * a_at; row[f'hit_{k}atr'] = pct(np.nanmean(hit), 1)
    row['width_hit_25pct'] = pct(-np.quantile(mins, 0.25), 1)   # stop width that normal noise reaches only 25% of the time within W bars
    cs[s] = row
R['c_stops'] = cs

# ---------- d. breakouts ----------
d = {}
for s, m in MKT.items():
    df = DATA[s]; c = df.close
    if m == 'crypto' and s != 'BTC': pass
    hz = H[m]; hold = hz[1]; bf, sf = side_fee(m)
    for N in (20, 50):
        sig = c > c.shift(1).rolling(N).max()
        if m == 'pse' or m == 'us': sig = sig & (c.index >= pd.Timestamp('2010-01-01'))
        ep = episodes(sig.fillna(False), N); key = f'{s}_{N}d'
        r = [(c.iloc[i + hold] * (1 - sf)) / (c.iloc[i] * (1 + bf)) - 1 for i in ep if i + hold < len(c)]
        dts = [c.index[i] for i in ep if i + hold < len(c)]
        base = ((c.shift(-hold) * (1 - sf)) / (c * (1 + bf)) - 1)
        base = base[base.index >= (dts[0] if dts else c.index[0])].mean()
        fw = {h: pct(fwd(c, h)[sig].mean()) for h in hz}; fb = {h: pct(fwd(c, h).mean()) for h in hz}
        o = oos(r, dts); ob = None
        if o:
            bb = ((c.shift(-hold) * (1 - sf)) / (c * (1 + bf)) - 1); ob = pct(bb[bb.index >= pd.Timestamp(o['split_date'])].mean())
        d[key] = dict(market=m, stats=trade_stats(r, dts), oos=o, oos_base=ob, base_hold_net=pct(base), fwd_signal=fw, fwd_base=fb)
pool = {}
for m in ('crypto', 'us', 'pse'):
    for N in (20, 50):
        ks = [k for k, v in d.items() if v['market'] == m and k.endswith(f'_{N}d') and v['stats'].get('n')]
        n = sum(d[k]['stats']['n'] for k in ks)
        pool[f'{m}_{N}d'] = dict(names=len(ks), trades=n, exp_wavg=round(sum(d[k]['stats']['expectancy'] * d[k]['stats']['n'] for k in ks) / n, 2),
                                 base_wavg=round(sum((d[k]['base_hold_net'] or 0) * d[k]['stats']['n'] for k in ks) / n, 2),
                                 win_wavg=round(sum(d[k]['stats']['win_rate'] * d[k]['stats']['n'] for k in ks) / n, 1),
                                 oos_base_wavg=round(sum((d[k]['oos_base'] or 0) * (d[k]['oos'] or {}).get('oos_n', 0) for k in ks) / max(1, sum((d[k]['oos'] or {}).get('oos_n', 0) for k in ks)), 2),
                                 oos_exp_wavg=round(sum((d[k]['oos'] or {}).get('oos_exp', 0) * (d[k]['oos'] or {}).get('oos_n', 0) for k in ks) / max(1, sum((d[k]['oos'] or {}).get('oos_n', 0) for k in ks)), 2))
R['d_breakout'] = d; R['d_breakout_pooled'] = pool

# ---------- e. PSE dividend capture ----------
dv = pd.read_sql("select symbol,ex_date,sum(amount) amount from dividends where market='pse' and amount is not null group by symbol,ex_date", con(), parse_dates=['ex_date'])  # regular+special on same ex-date = one event
ev = []
for r in dv.itertuples():
    if r.symbol not in DATA: continue
    df = DATA[r.symbol]; c = df.close
    if r.ex_date > c.index[-1]: continue
    pos = c.index.searchsorted(r.ex_date)
    if pos >= len(c) or c.index[pos] != r.ex_date or pos < 5: continue
    pb = c.iloc[pos - 5]; net_div = 0.9 * r.amount
    row = dict(sym=r.symbol, ex=str(r.ex_date.date()), div=r.amount, yld=pct(r.amount / c.iloc[pos - 1]),
               gap_vs_div=round(float((c.iloc[pos - 1] - df.open.iloc[pos]) / r.amount), 2))
    for k, lab in ((0, 'sell_ex'), (5, 'sell_ex5'), (10, 'sell_ex10')):
        if pos + k < len(c): row[lab] = pct((c.iloc[pos + k] * (1 - FEES['pse_sell']) + net_div) / (pb * (1 + FEES['pse_buy'])) - 1)
    row['no_div_same_days'] = pct(c.iloc[pos] / pb - 1)  # price-only move over the same 5 days
    ev.append(row)
E = pd.DataFrame(ev)
base5 = np.mean([((DATA[s].close.shift(-5) * (1 - FEES['pse_sell'])) / (DATA[s].close * (1 + FEES['pse_buy'])) - 1)[DATA[s].index >= '2024-12-01'].mean() for s in PSE if s in E.sym.values])
R['e_divcap'] = dict(events=ev, summary={lab: dict(trade_stats(E[lab].dropna() / 100), oos=oos((E.sort_values('ex')[lab] / 100).values, pd.to_datetime(E.sort_values('ex').ex)))
                                          for lab in ('sell_ex', 'sell_ex5', 'sell_ex10')},
                     avg_gap_vs_div=round(float(E.gap_vs_div.median()), 2), base_5d_net=pct(base5), n=len(E))

# ---------- f. MSCI rebalance week (PSE basket) ----------
rets = pd.concat({s: DATA[s].close.pct_change() for s in PSE if s != 'GCASH'}, axis=1)
bask = rets[rets.index >= '2015-01-01'].mean(axis=1, skipna=True).dropna(); lvl = (1 + bask).cumprod()
evd = []
for y in range(2015, 2027):
    for mo in (2, 5, 8, 11):
        mm = lvl[(lvl.index.year == y) & (lvl.index.month == mo)]
        if len(mm) and (y, mo) != (2026, 11): evd.append(mm.index[-1])
w = []
for e in evd:
    p = lvl.index.get_loc(e)
    if p + 5 >= len(lvl): continue
    w.append(dict(date=str(e.date()), semi=e.month in (5, 11), pre5=pct(lvl.iloc[p] / lvl.iloc[p - 5] - 1), day=pct(lvl.iloc[p] / lvl.iloc[p - 1] - 1), post5=pct(lvl.iloc[p + 5] / lvl.iloc[p] - 1)))
W_ = pd.DataFrame(w)
def tstat(x, mu): x = np.asarray(x, float); return round(float((x.mean() - mu) / (x.std(ddof=1) / np.sqrt(len(x)))), 2)
all5 = (lvl.shift(-5) / lvl - 1).dropna(); all1 = bask
R['f_msci'] = dict(events=w, n=len(W_), pre5_mean=round(W_.pre5.mean(), 2), pre5_pos=round((W_.pre5 > 0).mean() * 100, 1), day_mean=round(W_.day.mean(), 2), day_pos=round((W_.day > 0).mean() * 100, 1),
                   post5_mean=round(W_.post5.mean(), 2), post5_pos=round((W_.post5 > 0).mean() * 100, 1), base5_mean=pct(all5.mean()), base5_pos=pct((all5 > 0).mean(), 1), base1_mean=pct(all1.mean(), 3), base1_pos=pct((all1 > 0).mean(), 1),
                   t_pre5=tstat(W_.pre5, float((lvl.shift(-5) / lvl - 1).mean() * 100)), t_day=tstat(W_.day, float(bask.mean() * 100)), t_post5=tstat(W_.post5, float((lvl.shift(-5) / lvl - 1).mean() * 100)),
                   semi=dict(n=int(W_.semi.sum()), day_mean=round(W_[W_.semi].day.mean(), 2), post5_mean=round(W_[W_.semi].post5.mean(), 2), pre5_mean=round(W_[W_.semi].pre5.mean(), 2)))

# ---------- g. VIX > 25 ----------
vix = load('^VIX').close; g = {}
for s in ('SPY', 'QQQ'):
    c = DATA[s].close; v = vix.reindex(c.index).ffill()
    for T in (25, 30, 40):
        m = v > T; ep = episodes(m, 21); row = {'episodes': len(ep)}
        for h in (5, 21, 63, 126):
            fr = fwd(c, h); row[f'fwd{h}'] = pct(fr.iloc[ep].mean()); row[f'pos{h}'] = pct((fr.iloc[ep] > 0).mean(), 1); row[f'base{h}'] = pct(fr.mean())
        for hold in (21, 63):
            r = [(c.iloc[i + hold] * (1 - FEES['gotrade'])) / (c.iloc[i] * (1 + FEES['gotrade'])) - 1 for i in ep if i + hold < len(c)]
            dts = [c.index[i] for i in ep if i + hold < len(c)]; row[f'hold{hold}'] = dict(stats=trade_stats(r, dts), oos=oos(r, dts))
        g[f'{s}_vix{T}'] = row
    g[f'{s}_buyhold_total_since2000'] = pct(c.iloc[-1] / c.iloc[0] - 1, 0)
g['vix_now'] = round(float(vix.iloc[-1]), 2); g['vix_date'] = str(vix.index[-1].date())
R['g_vix'] = g

# ---------- 3. vol sizing ----------
vs = {}
for s, m in MKT.items():
    df = DATA[s]; r = df.close.pct_change()
    vs[s] = dict(market=m, last=round(float(df.close.iloc[-1]), 4), date=str(df.index[-1].date()), vol20=pct(r.iloc[-20:].std()), vol60=pct(r.iloc[-60:].std()),
                 atr14=pct(atr_pct(df).iloc[-1]), ann_vol60=pct(r.iloc[-60:].std() * np.sqrt(365 if m == 'crypto' else 252), 0))
R['vol'] = vs
json.dump(R, open(f'{OUT}/results.json', 'w'), indent=1, default=str)
print('saved', f'{OUT}/results.json')
