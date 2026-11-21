"""Regime: risk_off / chop / risk_on. Unknown inputs resolve to the MORE cautious regime."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .indicators import Candle, closes, sma
from .timeutil import age_hours


@dataclass
class Regime:
    name: str                      # risk_off | chop | risk_on
    signals: dict                  # name -> True / False / None (unknown)
    values: dict
    notes: list[str] = field(default_factory=list)
    assumed: bool = False          # True if unknown inputs pushed us to the cautious side

    def label(self) -> str:
        return {"risk_off": "Risk-off", "chop": "Chop", "risk_on": "Risk-on"}[self.name] + (
            " (assumed: some inputs unknown)" if self.assumed else "")


def compute_regime(btc: list[Candle], fng, etf_value: bool | None, etf_updated: datetime | None,
                   cfg_regime: dict, now: datetime) -> Regime:
    notes: list[str] = []
    cl = closes(btc)
    close = cl[-1] if cl else None
    s50, s200 = sma(cl, 50), sma(cl, 200)

    # 1) BTC below SMA200
    below = None if (close is None or s200 is None) else close < s200
    if s200 is None:
        notes.append(f"only {len(cl)} BTC closes, SMA200 unknown")

    # 2) extreme fear
    fng_val = None
    if fng is None:
        notes.append("Fear & Greed unavailable")
    else:
        v, ts = fng
        if age_hours(ts, now) > cfg_regime["fng_max_age_h"]:
            notes.append(f"Fear & Greed is {age_hours(ts, now):.0f}h old, treated as unknown")
        else:
            fng_val = v
    fear = None if fng_val is None else fng_val < cfg_regime["fng_fear"]

    # 3) ETF outflows (manual)
    etf = None
    if etf_value is None or etf_updated is None:
        notes.append("ETF flows not set")
    elif age_hours(etf_updated, now) > cfg_regime["manual_max_age_h"]:
        notes.append(f"ETF flows input is {age_hours(etf_updated, now):.0f}h old, treated as unknown: update plan.yaml")
    else:
        etf = etf_value

    signals = {"btc_below_sma200": below, "extreme_fear": fear, "etf_outflows": etf}
    true_n = sum(1 for v in signals.values() if v is True)
    unknown_n = sum(1 for v in signals.values() if v is None)

    assumed = False
    if true_n >= 2:
        name = "risk_off"
    elif true_n + unknown_n >= 2:
        name, assumed = "risk_off", True
    else:
        risk_on = (close is not None and s50 is not None and s200 is not None
                   and close > s50 > s200 and fng_val is not None and fng_val < cfg_regime["fng_greed"])
        name = "risk_on" if risk_on else "chop"

    return Regime(
        name=name, signals=signals, assumed=assumed, notes=notes,
        values={"btc_close": close, "sma50": s50, "sma200": s200, "fng": fng_val,
                "btc_close_date": btc[-1].open_time.date().isoformat() if btc else None},
    )
