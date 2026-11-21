#!/usr/bin/env python3
"""Loot quant price DB updater. Idempotent: re-fetches from (last stored date - 7 days) and upserts.
Sources: Binance data-api (crypto USDT pairs), Hyperliquid info API (HYPE full history; Binance only lists
HYPEUSDT since 2026-09-24), CoinGecko fallback, alternative.me Fear&Greed, Yahoo chart API (US),
PSE Edge DisclosureCht.ax (PSE daily OHLC + traded value, UNADJUSTED for dividends), PSE Edge dividend list.
Usage: python3 update_prices.py [--full]
"""
import json, sqlite3, sys, time, datetime as dt, urllib.request, re, html, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prices.db')
STORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
UA = {'User-Agent': 'Mozilla/5.0'}
FULL = '--full' in sys.argv
CRYPTO = ['BTC', 'ETH', 'SOL', 'BNB', 'HYPE', 'ZEC']
PSE_IDS = {  # ticker: (cmpy_id, security_id) from edge.pse.com.ph
 'JFC': ('86', '158'), 'URC': ('124', '167'), 'MONDE': ('682', '665'), 'PGOLD': ('629', '567'),
 'BDO': ('260', '468'), 'CBC': ('184', '104'), 'GCASH': ('709', '754'), 'SM': ('599', '520'),
 'ICT': ('83', '142'), 'AREIT': ('679', '655'), 'BPI': ('234', '101'), 'MER': ('118', '137'),
 'PNB': ('139', '109'), 'AC': ('57', '180'), 'TEL': ('6', '134')}

def get(url, data=None, headers=None, tries=3):
    h = dict(UA); h.update(headers or {})
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(2 + 3 * i)

def db():
    c = sqlite3.connect(DB)
    c.executescript('''
    CREATE TABLE IF NOT EXISTS prices(symbol TEXT, market TEXT, date TEXT, open REAL, high REAL, low REAL,
      close REAL, adj_close REAL, volume REAL, value REAL, source TEXT, PRIMARY KEY(symbol, date));
    CREATE TABLE IF NOT EXISTS fng(date TEXT PRIMARY KEY, value INTEGER, classification TEXT);
    CREATE TABLE IF NOT EXISTS dividends(symbol TEXT, market TEXT, ex_date TEXT, amount REAL, raw TEXT,
      source TEXT, PRIMARY KEY(symbol, ex_date, amount));
    CREATE TABLE IF NOT EXISTS update_log(ts TEXT, symbol TEXT, rows INTEGER, note TEXT);''')
    return c

def last_date(c, sym):
    r = c.execute('SELECT max(date) FROM prices WHERE symbol=?', (sym,)).fetchone()[0]
    return None if (FULL or not r) else r

def upsert(c, rows):
    c.executemany('INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows); c.commit()

def log(c, sym, n, note=''):
    c.execute('INSERT INTO update_log VALUES (?,?,?,?)', (dt.datetime.now().isoformat(timespec='seconds'), sym, n, note)); c.commit()
    print(f'{sym:8s} {n:6d} rows {note}')

def start_ms(ld, default='2017-01-01'):
    d = dt.date.fromisoformat(ld) - dt.timedelta(days=7) if ld else dt.date.fromisoformat(default)
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)

def today_utc(): return dt.datetime.now(dt.timezone.utc).date().isoformat()

def binance(c, coin):
    sym = coin + 'USDT'; st = start_ms(last_date(c, coin)); rows = []
    while True:
        d = json.loads(get(f'https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1d&startTime={st}&limit=1000'))
        if not d: break
        for k in d:
            day = dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc).date().isoformat()
            if day >= today_utc(): continue  # skip unfinished UTC candle
            rows.append((coin, 'crypto', day, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[4]), float(k[5]), float(k[7]), 'binance'))
        if len(d) < 1000: break
        st = d[-1][0] + 86400000
    upsert(c, rows); return len(rows)

def hyperliquid(c, coin='HYPE'):
    st = start_ms(last_date(c, coin), '2024-11-01'); rows = []
    body = json.dumps({'type': 'candleSnapshot', 'req': {'coin': coin, 'interval': '1d', 'startTime': st,
                       'endTime': int(time.time() * 1000)}}).encode()
    d = json.loads(get('https://api.hyperliquid.xyz/info', body, {'Content-Type': 'application/json'}))
    for k in d:
        day = dt.datetime.fromtimestamp(k['t'] / 1000, dt.timezone.utc).date().isoformat()
        if day >= today_utc(): continue
        rows.append((coin, 'crypto', day, float(k['o']), float(k['h']), float(k['l']), float(k['c']), float(k['c']), float(k['v']), None, 'hyperliquid_perp'))
    upsert(c, rows); return len(rows)

def coingecko(c, coin, cg_id):
    d = json.loads(get(f'https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days=365&interval=daily'))
    rows = [(coin, 'crypto', dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date().isoformat(), None, None, None, p, p, None, None, 'coingecko') for t, p in d['prices']]
    upsert(c, rows); return len(rows)

def fng(c):
    d = json.loads(get('https://api.alternative.me/fng/?limit=0'))['data']
    c.executemany('INSERT OR REPLACE INTO fng VALUES (?,?,?)', [(dt.datetime.fromtimestamp(int(x['timestamp']), dt.timezone.utc).date().isoformat(), int(x['value']), x['value_classification']) for x in d])
    c.commit(); return len(d)

def yahoo(c, sym):
    ld = last_date(c, sym)
    p1 = int(dt.datetime.fromisoformat(ld).replace(tzinfo=dt.timezone.utc).timestamp()) - 7 * 86400 if ld else 946684800
    q = urllib.request.quote(sym)
    d = json.loads(get(f'https://query1.finance.yahoo.com/v8/finance/chart/{q}?period1={p1}&period2={int(time.time())}&interval=1d&events=div%2Csplit'))['chart']['result'][0]
    ts = d.get('timestamp') or []; qd = d['indicators']['quote'][0]; adj = d['indicators'].get('adjclose', [{}])[0].get('adjclose', qd['close'])
    rows = []
    for i, t in enumerate(ts):
        if qd['close'][i] is None: continue
        day = dt.datetime.fromtimestamp(t + d['meta'].get('gmtoffset', 0), dt.timezone.utc).date().isoformat()
        rows.append((sym, 'us', day, qd['open'][i], qd['high'][i], qd['low'][i], qd['close'][i], adj[i], qd['volume'][i], None, 'yahoo'))
    upsert(c, rows)
    for t, ev in (d.get('events', {}).get('dividends') or {}).items():
        c.execute('INSERT OR REPLACE INTO dividends VALUES (?,?,?,?,?,?)', (sym, 'us', dt.datetime.fromtimestamp(int(t), dt.timezone.utc).date().isoformat(), ev['amount'], None, 'yahoo'))
    c.commit(); return len(rows)

def pse(c, sym):
    cid, sid = PSE_IDS[sym]; ld = last_date(c, sym)
    sd = (dt.date.fromisoformat(ld) - dt.timedelta(days=10)) if ld else dt.date(2010, 1, 1)
    body = json.dumps({'cmpy_id': cid, 'security_id': sid, 'startDate': sd.strftime('%m-%d-%Y'), 'endDate': dt.date.today().strftime('%m-%d-%Y')}).encode()
    d = json.loads(get('https://edge.pse.com.ph/common/DisclosureCht.ax', body, {'Content-Type': 'application/json', 'Referer': f'https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id={cid}'}).decode('utf8', 'ignore'))
    rows = []
    for k in d.get('chartData', []):
        day = dt.datetime.strptime(k['CHART_DATE'][:12], '%b %d, %Y').date().isoformat()
        rows.append((sym, 'pse', day, k['OPEN'], k['HIGH'], k['LOW'], k['CLOSE'], None, None, k.get('VALUE'), 'pse_edge'))
    upsert(c, rows)
    # recent dividend declarations (PSE Edge only lists the latest ones)
    t = get(f'https://edge.pse.com.ph/companyPage/dividends_and_rights_list.ax?DividendsOrRights=Dividends&cmpy_id={cid}', b'', {'Referer': 'https://edge.pse.com.ph/'}).decode('utf8', 'ignore')
    for r in re.findall(r'<tr>(.*?)</tr>', t, re.S):
        cells = [html.unescape(re.sub('<.*?>', '', x)).strip() for x in re.findall(r'<td.*?>(.*?)</td>', r, re.S)]
        if len(cells) >= 5 and cells[0] == 'COMMON' and cells[1] == 'Cash':
            m = re.search(r'([\d.]+)', cells[2].replace(',', ''))
            try: ex = dt.datetime.strptime(cells[3], '%b %d, %Y').date().isoformat()
            except Exception: continue
            c.execute('INSERT OR REPLACE INTO dividends VALUES (?,?,?,?,?,?)', (sym, 'pse', ex, float(m.group(1)) if m else None, cells[2], 'pse_edge_div_list'))
    c.commit(); return len(rows)

def watch_lists():
    u = json.load(open(f'{STORE}/us_watchlist.json'))
    us = [x['ticker'] for x in u['stocks'] + u['etfs']] + [x['ticker'] for x in u['bench']['stocks'] + u['bench']['etfs']]
    return sorted(set(us + ['SPY', 'QQQ', '^VIX']))

if __name__ == '__main__':
    c = db()
    try: log(c, 'FNG', fng(c), 'alternative.me')
    except Exception as e: log(c, 'FNG', 0, f'ERR {e}')
    for coin in CRYPTO:
        try:
            if coin == 'HYPE': log(c, coin, hyperliquid(c), 'hyperliquid')
            else: log(c, coin, binance(c, coin), 'binance')
        except Exception as e:
            try: log(c, coin, coingecko(c, coin, {'HYPE': 'hyperliquid'}.get(coin, coin.lower())), f'coingecko fallback ({e})')
            except Exception as e2: log(c, coin, 0, f'ERR {e} / {e2}')
    for s in watch_lists():
        try: log(c, s, yahoo(c, s), 'yahoo')
        except Exception as e: log(c, s, 0, f'ERR {e}')
        time.sleep(0.4)
    for s in PSE_IDS:
        try: log(c, s, pse(c, s), 'pse_edge')
        except Exception as e: log(c, s, 0, f'ERR {e}')
        time.sleep(0.8)
    print('PSEi: no free full-history source found (Yahoo PSEI.PS returns 1 row; phisix has no index history; FMETF not on Edge chart).')
