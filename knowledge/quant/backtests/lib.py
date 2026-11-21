"""Shared helpers for Loot backtests. Data: knowledge/quant/prices.db"""
import sqlite3, numpy as np, pandas as pd, os
import os
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prices.db')
FEES = {  # per-side cost as a fraction (assumptions documented in FINDINGS.md)
    'binance': 0.001, 'pdax': 0.004, 'pse_buy': 0.0030, 'pse_sell': 0.0040, 'gotrade': 0.0015}
def con(): return sqlite3.connect(DB)
def load(sym):
    df = pd.read_sql('select date,open,high,low,close,adj_close,market from prices where symbol=? order by date', con(), params=(sym,), parse_dates=['date']).set_index('date')
    if df.market.iloc[0] == 'us':  # use split/dividend-adjusted OHLC
        f = df.adj_close / df.close
        for k in ['open', 'high', 'low', 'close']: df[k] = df[k] * f
    return df[['open', 'high', 'low', 'close']].astype(float).dropna(subset=['close'])
def fng():
    return pd.read_sql('select date,value from fng', con(), parse_dates=['date']).set_index('date').value.sort_index()
def side_fee(market, venue=None):
    if market == 'crypto': return FEES[venue or 'binance'], FEES[venue or 'binance']
    if market == 'pse': return FEES['pse_buy'], FEES['pse_sell']
    return FEES['gotrade'], FEES['gotrade']
def fwd(close, n): return close.shift(-n) / close - 1
def episodes(mask, cooldown):
    """first signal day after `cooldown` bars without a taken signal -> non-overlapping trades"""
    out, last = [], -10**9
    idx = np.where(mask.values)[0]
    for i in idx:
        if i - last >= cooldown: out.append(i); last = i
    return out
def trade_stats(rets, dates=None, label=''):
    r = pd.Series(rets, index=dates).dropna()
    n = len(r)
    if n == 0: return dict(n=0)
    w, l = r[r > 0], r[r <= 0]
    eq = (1 + r).cumprod(); dd = (eq / eq.cummax() - 1).min()
    return dict(n=n, win_rate=round(float((r > 0).mean()) * 100, 1), avg_win=round(float(w.mean()) * 100, 2) if len(w) else None,
                avg_loss=round(float(l.mean()) * 100, 2) if len(l) else None, expectancy=round(float(r.mean()) * 100, 2),
                median=round(float(r.median()) * 100, 2), worst=round(float(r.min()) * 100, 2), max_dd=round(float(dd) * 100, 1),
                weak=n < 20)
def oos(rets, dates):
    r = pd.Series(rets, index=dates).dropna().sort_index()
    if len(r) < 4: return None
    k = int(len(r) * 0.7)
    return dict(is_n=k, is_exp=round(float(r.iloc[:k].mean()) * 100, 2), is_win=round(float((r.iloc[:k] > 0).mean()) * 100, 1),
                oos_n=len(r) - k, oos_exp=round(float(r.iloc[k:].mean()) * 100, 2), oos_win=round(float((r.iloc[k:] > 0).mean()) * 100, 1),
                split_date=str(r.index[k].date()))
def atr_pct(df, n=14):
    pc = df.close.shift(1)
    tr = pd.concat([df.high - df.low, (df.high - pc).abs(), (df.low - pc).abs()], axis=1).max(axis=1)
    return (tr.rolling(n).mean() / df.close)
