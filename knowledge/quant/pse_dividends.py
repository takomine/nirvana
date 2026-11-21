#!/usr/bin/env python3
"""Scrape PSE Edge 'Declaration of Cash Dividends' disclosures (Edge search only reaches ~2 years back)
into prices.db dividends table (common shares only). Idempotent."""
import re, html, time, datetime as dt, urllib.request, urllib.parse, sqlite3, os
from update_prices import PSE_IDS, get, db
def text(b): t = html.unescape(re.sub(r'<[^>]+>', ' ', b.decode('utf8', 'ignore'))); return re.sub(r'\s+', ' ', t)
def run(only=None):
    c = db(); to = dt.date.today(); fr = to - dt.timedelta(days=730*2)
    for sym, (cid, _) in PSE_IDS.items():
        if only and sym not in only: continue
        c.execute("DELETE FROM dividends WHERE symbol=? AND source LIKE 'pse_edge_disclosure%'", (sym,)); n = 0
        for (a, b) in [(fr, to - dt.timedelta(days=730)), (to - dt.timedelta(days=730), to)]:
            for page in range(1, 4):
                body = urllib.parse.urlencode({'companyId': cid, 'keyword': '', 'tmplNm': 'Declaration of Cash Dividends', 'fromDate': a.strftime('%m-%d-%Y'),
                        'toDate': b.strftime('%m-%d-%Y'), 'pageNo': page, 'sortType': '', 'dateSortType': 'DESC', 'cmpySortType': 'ASC'}).encode()
                s = get('https://edge.pse.com.ph/announcements/search.ax', body, {'Referer': 'https://edge.pse.com.ph/announcements/form.do'}).decode('utf8', 'ignore')
                ids = re.findall(r"openPopup\('([0-9a-f]+)'", s)
                for e in ids:
                    v = get(f'https://edge.pse.com.ph/openDiscViewer.do?edge_no={e}').decode('utf8', 'ignore')
                    m = re.search(r'downloadHtml\.do\?file_id=(\d+)', v)
                    if not m: continue
                    t = text(get(f'https://edge.pse.com.ph/downloadHtml.do?file_id={m.group(1)}'))
                    if 'Common N/A' in t: continue  # preferred-share dividend
                    pm = re.search(r'Type of Securities Common Preferred (\S+)', t)
                    if pm and pm.group(1).upper().strip('.') not in ('N/A', 'N.A', 'NA', '-', 'OTHERS', 'NONE', 'NOT', '') and re.fullmatch(r'[A-Z0-9]{3,}', pm.group(1)): continue  # names a preferred series, e.g. JFCPB
                    if re.search(r'per share for Series|preferred shares', t[t.find('Amount of Cash'):t.find('Amount of Cash') + 160], re.I): continue
                    ex = re.search(r'Ex-Date\s*:?\s*([A-Z][a-z]{2} \d{1,2}, \d{4})', t)
                    amt = re.search(r'Amount of Cash Dividend Per Share\s*(?:PHP|PhP|Php|P|₱)?\s*([\d.,]+)', t)
                    if not ex: continue
                    exd = dt.datetime.strptime(ex.group(1), '%b %d, %Y').date().isoformat()
                    am = float(amt.group(1).replace(',', '').rstrip('.')) if amt else None
                    c.execute('DELETE FROM dividends WHERE symbol=? AND ex_date=? AND source="pse_edge_div_list"', (sym, exd))
                    c.execute('INSERT OR REPLACE INTO dividends VALUES (?,?,?,?,?,?)', (sym, 'pse', exd, am, (amt.group(0) if amt else '')[:120], f'pse_edge_disclosure:{e}'))
                    n += 1; time.sleep(0.3)
                c.commit()
                if len(ids) < 10: break
        print(sym, n)
if __name__ == '__main__':
    import sys; run(sys.argv[1:] or None)
