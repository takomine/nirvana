"""Minimal backtest metrics for a daily long/flat signal. No leverage by default.
Usage: python3 bt_metrics.py <okx instId e.g. HYPE-USDT|BTC-USDT> [fee_per_side=0.001]
Edit signal() to test an idea. Prints stats for in-sample (first 70%) and out-of-sample (last 30%).
"""
import sys, json, math, urllib.request

def okx_daily(inst, n=1000):
    rows, after = [], ""
    while len(rows) < n:
        url = f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1Dutc&limit=100{after}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))["data"]
        if not d: break
        rows += d; after = f"&after={d[-1][0]}"
    rows = sorted(rows, key=lambda r: int(r[0]))  # oldest first; drop the still-open candle
    return [(int(r[0]), float(r[4])) for r in rows if r[8] == "1"]

def signal(closes, i):
    """Example: long if close above its 20-day average. Uses only data up to day i (no look-ahead)."""
    if i < 20: return 0
    return 1 if closes[i] > sum(closes[i-20:i]) / 20 else 0

def stats(rets, trades, label):
    if not rets: return
    eq, peak, mdd, under, max_under = 1.0, 1.0, 0.0, 0, 0
    for r in rets:
        eq *= 1 + r; peak = max(peak, eq); mdd = min(mdd, eq / peak - 1)
        under = 0 if eq >= peak else under + 1; max_under = max(max_under, under)
    mu = sum(rets) / len(rets); sd = (sum((r - mu) ** 2 for r in rets) / max(1, len(rets) - 1)) ** 0.5
    sharpe = mu / sd * math.sqrt(365) if sd else 0
    print(f"{label}: days={len(rets)} total={eq-1:+.1%} maxDD={mdd:.1%} "
          f"longest_underwater={max_under}d sharpe~{sharpe:.2f} worst_day={min(rets):.1%}")

def run(inst, fee=0.001):
    px = okx_daily(inst); closes = [c for _, c in px]
    pos, rets, trades, bh = 0, [], 0, []
    for i in range(1, len(closes)):
        r = closes[i] / closes[i-1] - 1
        rets.append(pos * r); bh.append(r)
        new = signal(closes, i)               # decided at today's close, applied from tomorrow
        if new != pos: rets[-1] -= fee; trades += 1
        pos = new
    cut = int(len(rets) * 0.7)
    print(f"{inst}: {len(closes)} daily closes, fee/side {fee:.2%}, no leverage")
    stats(rets[:cut], None, "IN-SAMPLE "); stats(rets[cut:], None, "OUT-SAMPLE")
    stats(bh, 0, "BUY&HOLD  ")
    print(f"total trades={trades}  (<30 trades = too few to trust)")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT", float(sys.argv[2]) if len(sys.argv) > 2 else 0.001)
