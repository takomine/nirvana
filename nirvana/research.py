"""Re-check the backtested claims on real data, with sample sizes, instead of trusting quoted numbers."""
from __future__ import annotations

from .indicators import Candle, atr_pct


def noise_hit_rate(candles: list[Candle], k: float = 3.0, horizon: int = 30) -> dict:
    """Share of random daily entries whose k x ATR14 stop is hit by a daily CLOSE within `horizon` days."""
    hits = n = 0
    for i in range(15, len(candles) - horizon):
        a = atr_pct(candles[: i + 1], 14)
        if not a:
            continue
        stop = candles[i].close * (1 - k * a)
        n += 1
        if any(c.close < stop for c in candles[i + 1: i + 1 + horizon]):
            hits += 1
    return {"k": k, "horizon": horizon, "samples": n, "hit_rate": hits / n if n else None}


def breakout_edge(candles: list[Candle], lookback: int = 50, horizon: int = 30, fee: float = 0.001) -> dict:
    """Forward return after a close above the prior `lookback`-day high close vs. all days. Overlapping samples."""
    fwd_all, fwd_sig = [], []
    for i in range(lookback, len(candles) - horizon):
        r = candles[i + horizon].close / candles[i].close * (1 - fee) ** 2 - 1
        fwd_all.append(r)
        if candles[i].close > max(c.close for c in candles[i - lookback:i]):
            fwd_sig.append(r)
    avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
    return {"lookback": lookback, "horizon": horizon, "signals": len(fwd_sig), "days": len(fwd_all),
            "avg_signal": avg(fwd_sig), "avg_all": avg(fwd_all),
            "win_rate_signal": (sum(r > 0 for r in fwd_sig) / len(fwd_sig)) if fwd_sig else None}


def report(coin: str, candles: list[Candle]) -> str:
    if len(candles) < 120:
        return f"{coin}: only {len(candles)} daily candles - too little history for any statistic. Treat claims as unverified."
    first, last = candles[0].open_time.date(), candles[-1].open_time.date()
    lines = [f"{coin}: {len(candles)} closed daily candles ({first} .. {last})"]
    for k in (1.5, 2.0, 3.0):
        r = noise_hit_rate(candles, k)
        lines.append(f"  {k}x ATR14 stop hit by a daily close within 30d: {r['hit_rate']:.0%} (n={r['samples']})")
    b = breakout_edge(candles)
    if b["signals"]:
        lines.append(f"  close > prior 50d high: avg 30d return {b['avg_signal']:+.1%} vs {b['avg_all']:+.1%} all days "
                     f"(signals={b['signals']}, win {b['win_rate_signal']:.0%}; overlapping, in-sample, after fees)")
    if len(candles) < 500:
        lines.append("  CAUTION: under ~500 days of history; one market regime only.")
    return "\n".join(lines)
