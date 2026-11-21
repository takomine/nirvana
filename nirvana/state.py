"""Persistent bot state (positions, tranche progress, stop floors). Atomic writes, one file per mode."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

EMPTY = {
    "version": 1,
    "positions": {},       # coin -> {qty, cost_usdt, opened, realized_usdt}
    "tranches": {},        # "<plan_id>:<tranche_id>" -> {status, client_id, filled_qty, filled_cost, attempts, coin}
    "orders": {},          # client_id -> {coin, side, kind, tranche_key, status, executed_qty, quote_qty}
    "wrong_if_floor": {},  # coin -> highest wrong-if ever used while holding (never lowered)
    "stopped": {},         # coin -> {plan_id, at}
    "paper": {"balances": {}, "orders": {}},
    "last_run": None,
}


class State:
    def __init__(self, path: Path, data: dict):
        self.path = Path(path)
        self.data = data

    @classmethod
    def load(cls, path: str | Path, paper_usdt: float | None = None) -> "State":
        p = Path(path)
        if p.exists():
            data = json.loads(p.read_text())
            for k, v in EMPTY.items():
                data.setdefault(k, copy.deepcopy(v))
        else:
            data = copy.deepcopy(EMPTY)
            if paper_usdt is not None:
                data["paper"]["balances"]["USDT"] = paper_usdt
        return cls(p, data)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state-", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(self.data, f, indent=2, sort_keys=True, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    # ---------------- helpers
    @property
    def positions(self) -> dict:
        return self.data["positions"]

    def qty(self, coin: str) -> float:
        return float(self.positions.get(coin, {}).get("qty", 0.0))

    def tranche(self, plan_id: str, tid: str) -> dict:
        return self.data["tranches"].setdefault(
            f"{plan_id}:{tid}", {"status": "pending", "filled_qty": 0.0, "filled_cost": 0.0, "attempts": 0})

    def apply_buy(self, coin: str, qty: float, cost: float, when: str, wrong_if: float | None) -> None:
        pos = self.positions.setdefault(coin, {"qty": 0.0, "cost_usdt": 0.0, "opened": when, "realized_usdt": 0.0})
        pos["qty"] += qty
        pos["cost_usdt"] += cost
        if wrong_if is not None:
            floor = self.data["wrong_if_floor"].get(coin)
            self.data["wrong_if_floor"][coin] = wrong_if if floor is None else max(floor, wrong_if)

    def apply_sell(self, coin: str, qty: float, proceeds: float, dust_qty: float = 0.0) -> float:
        pos = self.positions.get(coin)
        if not pos or pos["qty"] <= 0:
            return 0.0
        qty = min(qty, pos["qty"])
        frac = qty / pos["qty"]
        cost_part = pos["cost_usdt"] * frac
        pnl = proceeds - cost_part
        pos["qty"] -= qty
        pos["cost_usdt"] -= cost_part
        pos["realized_usdt"] = pos.get("realized_usdt", 0.0) + pnl
        if pos["qty"] <= dust_qty:
            self.close_position(coin)
        return pnl

    def close_position(self, coin: str) -> None:
        self.positions.pop(coin, None)
        self.data["wrong_if_floor"].pop(coin, None)
