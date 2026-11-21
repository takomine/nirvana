"""Risk math. Worst-case loss includes the stop gap buffer and fees on BOTH sides."""
from __future__ import annotations


def stop_width(entry: float, wrong_if: float) -> float:
    return (entry - wrong_if) / entry


def worst_loss_for_buy(notional: float, entry: float, wrong_if: float, gap: float, fee: float) -> float:
    """Loss if we buy `notional` USDT at `entry`, then the stop sells at wrong_if minus the gap buffer."""
    qty = notional / entry * (1 - fee)
    exit_value = qty * wrong_if * (1 - gap) * (1 - fee)
    return max(0.0, notional - exit_value)


def worst_loss_for_position(qty: float, cost_usdt: float, mark: float, wrong_if: float,
                            gap: float, fee: float) -> float:
    """Open risk of a held position, measured from the higher of cost basis and current value."""
    basis = max(cost_usdt, qty * mark)
    exit_value = qty * wrong_if * (1 - gap) * (1 - fee)
    return max(0.0, basis - exit_value)


def size_for_risk(budget: float, risk_pct: float, entry: float, wrong_if: float,
                  gap: float, fee: float) -> float:
    """Notional (USDT) such that worst-case loss == budget * risk_pct."""
    per_unit = worst_loss_for_buy(1.0, entry, wrong_if, gap, fee)
    return 0.0 if per_unit <= 0 else budget * risk_pct / per_unit
