"""Offline fakes: synthetic candles shaped like the 2026-11-21 market."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from nirvana.indicators import Candle
from nirvana.marketdata import SymbolInfo
from nirvana.timeutil import UTC

NOW = datetime(2026, 11, 21, 14, 45, tzinfo=UTC)  # 22:45 Manila


def series(start: float, end: float, days: int, range_pct: float, last_day: datetime | None = None,
           shape: str = "linear") -> list[Candle]:
    """Daily candles from start to end; each candle's high-low range ~ range_pct of close."""
    last_day = last_day or (NOW.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1))
    out = []
    for i in range(days):
        f = i / (days - 1)
        if shape == "hump":   # up then down (gives SMA50 > SMA200 > close, like tonight)
            mid = start * 1.35
            close = start + (mid - start) * (f / 0.75) if f < 0.75 else mid + (end - mid) * ((f - 0.75) / 0.25)
        else:
            close = start + (end - start) * f
        prev = out[-1].close if out else close
        hi = max(close, prev) * (1 + range_pct / 2)
        lo = min(close, prev) * (1 - range_pct / 2)
        out.append(Candle(last_day - timedelta(days=days - 1 - i), prev, hi, lo, close, 1.0, 200e6))
    return out


def info(sym: str, tick="0.01", step="0.00001", min_notional="5") -> SymbolInfo:
    return SymbolInfo(sym, "TRADING", sym[:-4], "USDT", Decimal(tick), Decimal(step), Decimal(step), Decimal(min_notional))


class FakeMarket:
    quote = "USDT"

    def __init__(self, candles: dict, books: dict, infos: dict | None = None, fng=(12, NOW)):
        self._c, self._b = candles, books
        self._i = infos or {c: info(f"{c}USDT") for c in candles}
        self._fng = fng

    def symbol(self, coin):
        return f"{coin}USDT"

    def candles(self, coin, days=400):
        return self._c[coin]

    def book(self, coin):
        return self._b[coin]

    def info(self, coin):
        return self._i.get(coin)

    def fear_greed(self):
        return self._fng


def tonight_market(**over) -> FakeMarket:
    c = {
        "BTC": series(62000, 58951.51, 260, 0.05, shape="hump"),
        "HYPE": series(40, 61.07, 120, 0.09),
        "ETH": series(2500, 1623.09, 260, 0.07),
        "SOL": series(150, 68.88, 260, 0.07),
        "BNB": series(700, 540.84, 260, 0.05),
        "ZEC": series(300, 760.3, 260, 0.14),
        "NEAR": series(4, 2.851, 260, 0.11),
    }
    b = {"BTC": (59950.0, 59960.0), "HYPE": (61.1, 61.18), "ETH": (1620, 1621), "SOL": (68.8, 68.9),
         "BNB": (540, 541), "ZEC": (759, 760), "NEAR": (2.85, 2.851)}
    c.update(over.get("candles", {}))
    b.update(over.get("books", {}))
    return FakeMarket(c, b, fng=over.get("fng", (12, NOW)))
