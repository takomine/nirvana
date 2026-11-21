"""Indicators on CLOSED daily candles only."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Candle:
    open_time: datetime  # UTC
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    quote_volume: float = 0.0

    @property
    def close_time(self) -> datetime:
        return self.open_time + timedelta(days=1)


def true_range(c: Candle, prev_close: float | None) -> float:
    if prev_close is None:
        return c.high - c.low
    return max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close))


def true_ranges(candles: list[Candle]) -> list[float]:
    out = []
    prev = None
    for c in candles:
        out.append(true_range(c, prev))
        prev = c.close
    return out


def atr(candles: list[Candle], n: int = 14) -> float | None:
    """Simple mean of the last n true ranges (needs n+1 candles so every TR has a prev close)."""
    if len(candles) < n + 1:
        return None
    trs = true_ranges(candles)[-n:]
    return sum(trs) / n


def atr_pct(candles: list[Candle], n: int = 14) -> float | None:
    a = atr(candles, n)
    if a is None or candles[-1].close <= 0:
        return None
    return a / candles[-1].close


def sma(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def closes(candles: list[Candle]) -> list[float]:
    return [c.close for c in candles]


def prior_high_close(candles: list[Candle], n: int) -> float | None:
    """Highest close of the n candles BEFORE the last one."""
    if len(candles) < n + 1:
        return None
    return max(c.close for c in candles[-n - 1:-1])


def avg_quote_volume(candles: list[Candle], n: int = 7) -> float | None:
    if len(candles) < n:
        return None
    return sum(c.quote_volume for c in candles[-n:]) / n
