#!/usr/bin/env python3
"""Liquidity / foreign-flow / relative-strength scan from PSE Daily Quotation Reports.
Usage: python3 scan.py [N]   (N = number of trading-day reports to use, default 10)"""
import datetime, json, os, re, subprocess, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
def num(s):
    s = s.strip()
    if s in ('-', ''): return 0.0
    neg = s.startswith('(')
    return (-1 if neg else 1) * float(s.strip('()').replace(',', ''))
def fetch(d):
    name = d.strftime('%B') + '%20' + str(d.day) + ',%20' + str(d.year)
    pdf = f'/tmp/dqr_{d:%Y%m%d}.pdf'; txt = pdf[:-4] + '.txt'
    if not os.path.exists(txt):
        code = subprocess.run(['curl', '-s', '-o', pdf, '-w', '%{http_code}',
            f'https://documents.pse.com.ph/market_report/{name}-EOD.pdf'], capture_output=True, text=True).stdout
        if code != '200': return None
        subprocess.run(['pdftotext', '-layout', pdf, txt])
    return open(txt).read()
def parse(t):
    rows, psei, blocks, inblk = {}, None, [], False
    for line in t.splitlines():
        if line.startswith('PSEi '):
            psei = num(line.split()[4])
        if line.startswith('BLOCK SALES'): inblk = True; continue
        if inblk and 'PRICE, USD' in line: inblk = False
        if inblk:
            m = re.match(r'^([A-Z0-9]+)\s+([\d,.]+)\s+([\d,]+)\s+([\d,.]+)$', line.strip())
            if m: blocks.append((m.group(1), num(m.group(2)), num(m.group(4))))
            continue
        m = re.match(r'^(.{20,26}?)\s+([A-Z0-9]{1,6})\s+(.*)$', line.rstrip())
        if not m: continue
        tk = m.group(3).split()
        if len(tk) < 9: continue
        try: rows[m.group(2)] = dict(close=num(tk[5]), val=num(tk[7]), nf=num(tk[8]))
        except ValueError: pass
    return rows, psei, blocks
days, d = [], datetime.date.today()
while len(days) < N and (datetime.date.today() - d).days < 45:
    if d.weekday() < 5:
        t = fetch(d)
        if t: days.append((d, *parse(t)))
    d -= datetime.timedelta(days=1)
days.reverse()
if not days: sys.exit('no DQR found')
first, last = days[0], days[-1]
idx = (last[2] / first[2] - 1) * 100 if first[2] and last[2] else 0
out = []
for s in set().union(*[set(x[1]) for x in days]):
    vals = [x[1].get(s, {}).get('val', 0) for x in days]
    c0, c1 = first[1].get(s, {}).get('close'), last[1].get(s, {}).get('close')
    rs = ((c1 / c0 - 1) * 100 - idx) if c0 and c1 else None
    out.append(dict(sym=s, avg_val_m=round(sum(vals) / len(vals) / 1e6, 1),
        nf_m=round(sum(x[1].get(s, {}).get('nf', 0) for x in days) / 1e6, 1),
        close=c1, rel_strength_pts=None if rs is None else round(rs, 1),
        blocks=[(str(x[0]), p, round(v / 1e6, 1)) for x in days for (b, p, v) in x[3] if b == s]))
out.sort(key=lambda r: -r['avg_val_m'])
print(f"DQR sessions: {[str(x[0]) for x in days]}  PSEi {first[2]} -> {last[2]} ({idx:+.1f}%)")
print('sym      avg_val(₱M)  net_foreign(₱M)  close   RS_vs_PSEi(pts)  tier')
for r in out[:60]:
    tier = 'core' if r['avg_val_m'] >= 20 else 'satellite' if r['avg_val_m'] >= 10 else '-'
    print(f"{r['sym']:<8} {r['avg_val_m']:>10} {r['nf_m']:>15} {r['close']!s:>8} {r['rel_strength_pts']!s:>12}  {tier}")
json.dump(out, open('scan_out.json', 'w'), indent=1)
