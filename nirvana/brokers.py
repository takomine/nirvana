"""Order execution: real Binance spot (signed REST), and a paper broker using live public prices.

Orders are always LIMIT (GTC for resting buys, IOC for marketable buys and stop sells). No market orders.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

import requests

from .marketdata import dec_str
from .timeutil import UTC, now_utc


class BrokerError(RuntimeError):
    """`definite` = the exchange certainly did NOT accept the request (a clean 4xx rejection).
    Anything else (timeout, 5xx, clock skew, rate limit) is ambiguous: the order may exist."""

    def __init__(self, msg: str, status: int | None = None, code: int | None = None, definite: bool = False):
        super().__init__(msg)
        self.status, self.code, self.definite = status, code, definite


AMBIGUOUS_CODES = {-1000, -1001, -1003, -1006, -1007, -1008, -1021}


def norm_order(raw: dict) -> dict:
    """Binance order JSON -> the fields we use."""
    commissions: dict[str, float] = {}
    for f in raw.get("fills") or []:
        a = f.get("commissionAsset")
        if a:
            commissions[a] = commissions.get(a, 0.0) + float(f.get("commission", 0))
    return {
        "commissions": commissions if raw.get("fills") is not None else None,
        "client_id": raw.get("origClientOrderId") or raw.get("clientOrderId"),
        "status": raw.get("status"),
        "side": raw.get("side"),
        "price": raw.get("price"),
        "orig_qty": raw.get("origQty"),
        "executed_qty": raw.get("executedQty", "0"),
        "quote_qty": raw.get("cummulativeQuoteQty", "0"),
    }


class BinanceBroker:
    MAINNET = "https://api.binance.com"
    TESTNET = "https://testnet.binance.vision"

    def __init__(self, key: str, secret: str, testnet: bool = False,
                 session: requests.Session | None = None, recv_window: int = 5000, timeout: float = 15):
        if not key or not secret:
            raise BrokerError("BINANCE_API_KEY / BINANCE_API_SECRET env vars are not set")
        self.key, self.secret = key, secret.encode()
        self.base = self.TESTNET if testnet else self.MAINNET
        self.testnet = testnet
        self.s = session or requests.Session()
        self.recv_window, self.timeout = recv_window, timeout
        self._offset_ms = 0
        self._sync_time()

    def _sync_time(self):
        try:
            r = self.s.get(self.base + "/api/v3/time", timeout=self.timeout)
            self._offset_ms = int(r.json()["serverTime"]) - int(time.time() * 1000)
        except Exception:
            self._offset_ms = 0

    def _signed(self, method: str, path: str, params: dict | None = None, _retry: bool = True):
        base_params = dict(params or {})
        params = dict(base_params)
        params["timestamp"] = int(time.time() * 1000) + self._offset_ms
        params["recvWindow"] = self.recv_window
        qs = urlencode(params)
        sig = hmac.new(self.secret, qs.encode(), hashlib.sha256).hexdigest()
        url = f"{self.base}{path}?{qs}&signature={sig}"
        try:
            r = self.s.request(method, url, headers={"X-MBX-APIKEY": self.key}, timeout=self.timeout)
        except requests.RequestException as e:
            raise BrokerError(f"{method} {path}: network error {e.__class__.__name__}") from e
        try:
            body = r.json()
        except ValueError:
            body = {"msg": r.text[:200]}
        if r.status_code >= 400:
            code = body.get("code") if isinstance(body, dict) else None
            if _retry and code == -1021:            # clock drift: resync and retry once
                self._sync_time()
                return self._signed(method, path, base_params, _retry=False)
            if _retry and r.status_code in (418, 429) and method == "GET":
                time.sleep(3)
                return self._signed(method, path, base_params, _retry=False)
            definite = (400 <= r.status_code < 500 and r.status_code not in (408, 418, 429)
                        and isinstance(code, int) and code not in AMBIGUOUS_CODES)
            raise BrokerError(f"{method} {path}: HTTP {r.status_code} code={code} {body.get('msg')}",
                              status=r.status_code, code=code, definite=definite)
        return body

    # ---- safety
    def key_restrictions(self) -> dict | None:
        """Mainnet only. Returns Binance's API-key permission flags."""
        if self.testnet:
            return None
        return self._signed("GET", "/sapi/v1/account/apiRestrictions")

    # ---- reads
    def balances(self) -> dict[str, float]:
        acct = self._signed("GET", "/api/v3/account", {"omitZeroBalances": "true"})
        return {b["asset"]: float(b["free"]) + float(b["locked"]) for b in acct.get("balances", [])}

    def free(self, asset: str) -> float:
        acct = self._signed("GET", "/api/v3/account", {"omitZeroBalances": "true"})
        for b in acct.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def get_order(self, symbol: str, client_id: str) -> dict | None:
        try:
            return norm_order(self._signed("GET", "/api/v3/order", {"symbol": symbol, "origClientOrderId": client_id}))
        except BrokerError as e:
            if e.code == -2013:  # order does not exist
                return None
            raise

    # ---- writes
    def place_limit(self, symbol: str, side: str, qty: Decimal, price: Decimal, tif: str, client_id: str) -> dict:
        existing = self.get_order(symbol, client_id)
        if existing is not None:  # idempotent: never place the same order twice
            return existing
        body = self._signed("POST", "/api/v3/order", {
            "symbol": symbol, "side": side, "type": "LIMIT", "timeInForce": tif,
            "quantity": dec_str(qty), "price": dec_str(price),
            "newClientOrderId": client_id, "newOrderRespType": "FULL",
        })
        return norm_order(body)

    def cancel(self, symbol: str, client_id: str) -> dict | None:
        try:
            return norm_order(self._signed("DELETE", "/api/v3/order", {"symbol": symbol, "origClientOrderId": client_id}))
        except BrokerError as e:
            if e.code == -2011:  # unknown order / already closed
                return self.get_order(symbol, client_id)
            raise


class PaperBroker:
    """Simulated fills against live public prices. Buy fees come out of the coin, like Binance."""

    def __init__(self, state, market, fee: float, fee_in_base: bool = True, now: datetime | None = None):
        self.p = state.data["paper"]
        self.p.setdefault("balances", {})
        self.p.setdefault("orders", {})
        self.market, self.fee, self.fee_in_base = market, fee, fee_in_base
        self.now = now or now_utc()

    def _bal(self, asset: str) -> float:
        return float(self.p["balances"].get(asset, 0.0))

    def _add(self, asset: str, amt: float):
        self.p["balances"][asset] = self._bal(asset) + amt

    def balances(self) -> dict[str, float]:
        return {k: v for k, v in self.p["balances"].items() if v}

    def free(self, asset: str) -> float:
        locked = sum(float(o["orig_qty"]) * float(o["price"]) - float(o["quote_qty"])
                     for o in self.p["orders"].values()
                     if o["status"] in ("NEW", "PARTIALLY_FILLED") and o["side"] == "BUY")
        return self._bal(asset) - locked if asset == "USDT" else self._bal(asset)

    def _coin(self, symbol: str) -> str:
        return symbol[:-len(self.market.quote)]

    def _fill(self, o: dict, price: float):
        qty = float(o["orig_qty"]) - float(o["executed_qty"])
        coin = self._coin(o["symbol"])
        if o["side"] == "BUY":
            self._add("USDT", -qty * price)
            self._add(coin, qty * (1 - self.fee) if self.fee_in_base else qty)
        else:
            self._add(coin, -qty)
            self._add("USDT", qty * price * (1 - self.fee))
        o["executed_qty"] = str(float(o["executed_qty"]) + qty)
        o["quote_qty"] = str(float(o["quote_qty"]) + qty * price)
        o["status"] = "FILLED"

    def get_order(self, symbol: str, client_id: str) -> dict | None:
        o = self.p["orders"].get(client_id)
        if o is None:
            return None
        if o["status"] in ("NEW", "PARTIALLY_FILLED") and o["side"] == "BUY":
            # resting buy fills if any closed candle after placement traded at/below the price, or the ask is there now
            placed = datetime.fromisoformat(o["placed"])
            price = float(o["price"])
            hit = any(c.low <= price for c in self.market.candles(self._coin(symbol)) if c.close_time > placed)
            _, ask = self.market.book(self._coin(symbol))
            if hit or ask <= price:
                self._fill(o, price if hit else ask)
        return {k: o[k] for k in ("client_id", "status", "side", "price", "orig_qty", "executed_qty", "quote_qty")}

    def place_limit(self, symbol: str, side: str, qty: Decimal, price: Decimal, tif: str, client_id: str) -> dict:
        if client_id in self.p["orders"]:
            return self.get_order(symbol, client_id)
        coin = self._coin(symbol)
        bid, ask = self.market.book(coin)
        q, px = float(qty), float(price)
        if side == "BUY" and q * px > self.free("USDT") + 1e-9:
            raise BrokerError(f"paper: insufficient USDT ({self.free('USDT'):.2f} free)", 400, -2010, True)
        if side == "SELL" and q > self._bal(coin) + 1e-12:
            raise BrokerError(f"paper: insufficient {coin}", 400, -2010, True)
        o = {"client_id": client_id, "symbol": symbol, "side": side, "price": str(price), "orig_qty": str(qty),
             "executed_qty": "0", "quote_qty": "0", "status": "NEW", "tif": tif,
             "placed": self.now.astimezone(UTC).isoformat()}
        self.p["orders"][client_id] = o
        if side == "BUY" and ask <= px:
            self._fill(o, ask)
        elif side == "SELL" and bid >= px:
            self._fill(o, bid)
        elif tif == "IOC":
            o["status"] = "EXPIRED"
        return self.get_order(symbol, client_id)

    def cancel(self, symbol: str, client_id: str) -> dict | None:
        o = self.p["orders"].get(client_id)
        if o and o["status"] in ("NEW", "PARTIALLY_FILLED"):
            o["status"] = "CANCELED"
        return self.get_order(symbol, client_id)
