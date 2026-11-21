"""Public market data: Binance klines / book / filters, and Fear & Greed."""
from __future__ import annotations

import time as _time
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

import requests

from .indicators import Candle
from .timeutil import UTC, now_utc


class DataError(RuntimeError):
    pass


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str
    status: str
    base: str
    quote: str
    tick_size: Decimal
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal

    def round_price_down(self, price: float) -> Decimal:
        return _round_down(Decimal(str(price)), self.tick_size)

    def round_qty_down(self, qty: float) -> Decimal:
        return _round_down(Decimal(str(qty)), self.step_size)


def _round_down(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step.normalize()


def dec_str(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    return s


class BinancePublic:
    """Unsigned Binance spot endpoints. Falls back to data-api.binance.vision if api.binance.com is blocked."""

    DEFAULT_BASES = ("https://api.binance.com", "https://data-api.binance.vision")

    def __init__(self, bases=None, session: requests.Session | None = None, timeout: float = 15):
        self.bases = list(bases or self.DEFAULT_BASES)
        self.session = session or requests.Session()
        self.timeout = timeout
        self._info_cache: dict[str, SymbolInfo] = {}

    def _get(self, path: str, params: dict | None = None):
        errors = []
        for base in self.bases:
            for attempt in range(2):
                try:
                    r = self.session.get(base + path, params=params, timeout=self.timeout)
                    if r.status_code == 200:
                        return r.json()
                    if r.status_code in (418, 429):  # rate limited: back off
                        _time.sleep(2 + attempt * 3)
                        continue
                    errors.append(f"{base}: HTTP {r.status_code} {r.text[:120]}")
                    break
                except requests.RequestException as e:
                    errors.append(f"{base}: {e.__class__.__name__}")
                    _time.sleep(1)
        raise DataError(f"GET {path} failed: " + "; ".join(errors))

    def daily_candles(self, symbol: str, days: int = 400, now: datetime | None = None) -> list[Candle]:
        """Up to `days` CLOSED daily candles, oldest first. The forming candle is always dropped."""
        now = now or now_utc()
        out: list[Candle] = []
        end_ms = None
        remaining = days + 1
        while remaining > 0:
            params = {"symbol": symbol, "interval": "1d", "limit": min(1000, remaining)}
            if end_ms is not None:
                params["endTime"] = end_ms
            rows = self._get("/api/v3/klines", params)
            if not rows:
                break
            batch = [
                Candle(
                    open_time=datetime.fromtimestamp(r[0] / 1000, UTC),
                    open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
                    volume=float(r[5]), quote_volume=float(r[7]),
                )
                for r in rows
            ]
            out = batch + out
            remaining -= len(batch)
            if len(batch) < params["limit"]:
                break
            end_ms = rows[0][0] - 1
        out = [c for c in out if c.close_time <= now]
        # de-duplicate, keep order
        seen, uniq = set(), []
        for c in out:
            if c.open_time not in seen:
                seen.add(c.open_time)
                uniq.append(c)
        return uniq[-days:]

    def book(self, symbol: str) -> tuple[float, float]:
        d = self._get("/api/v3/ticker/bookTicker", {"symbol": symbol})
        return float(d["bidPrice"]), float(d["askPrice"])

    def symbol_info(self, symbol: str) -> SymbolInfo | None:
        if symbol in self._info_cache:
            return self._info_cache[symbol]
        try:
            d = self._get("/api/v3/exchangeInfo", {"symbol": symbol})
        except DataError:
            return None
        syms = d.get("symbols") or []
        if not syms:
            return None
        s = syms[0]
        f = {x["filterType"]: x for x in s.get("filters", [])}
        notional = f.get("NOTIONAL") or f.get("MIN_NOTIONAL") or {}
        info = SymbolInfo(
            symbol=s["symbol"], status=s.get("status", "UNKNOWN"),
            base=s["baseAsset"], quote=s["quoteAsset"],
            tick_size=Decimal(f.get("PRICE_FILTER", {}).get("tickSize", "0.00000001")),
            step_size=Decimal(f.get("LOT_SIZE", {}).get("stepSize", "0.00000001")),
            min_qty=Decimal(f.get("LOT_SIZE", {}).get("minQty", "0")),
            min_notional=Decimal(notional.get("minNotional", "5")),
        )
        self._info_cache[symbol] = info
        return info


def fetch_fear_greed(session: requests.Session | None = None, timeout: float = 15):
    """Latest alternative.me Fear & Greed as (value, timestamp UTC), or None if unavailable."""
    s = session or requests.Session()
    try:
        r = s.get("https://api.alternative.me/fng/", params={"limit": 1}, timeout=timeout)
        r.raise_for_status()
        row = r.json()["data"][0]
        return int(row["value"]), datetime.fromtimestamp(int(row["timestamp"]), UTC)
    except Exception:
        return None


class Market:
    """What the engine needs from the outside world. Tests replace this with a fake."""

    def __init__(self, public: BinancePublic | None = None, quote: str = "USDT"):
        self.public = public or BinancePublic()
        self.quote = quote
        self._candles: dict[str, list[Candle]] = {}
        self._fng = "unset"

    def symbol(self, coin: str) -> str:
        return f"{coin}{self.quote}"

    def candles(self, coin: str, days: int = 400) -> list[Candle]:
        if coin not in self._candles:
            self._candles[coin] = self.public.daily_candles(self.symbol(coin), days)
        return self._candles[coin]

    def book(self, coin: str) -> tuple[float, float]:
        return self.public.book(self.symbol(coin))

    def info(self, coin: str) -> SymbolInfo | None:
        return self.public.symbol_info(self.symbol(coin))

    def fear_greed(self):
        if self._fng == "unset":
            self._fng = fetch_fear_greed(self.public.session)
        return self._fng
