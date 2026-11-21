"""Load and validate config.yaml and plan.yaml. Bad input fails loudly, never silently."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml

from .timeutil import parse_date, parse_dt


class ConfigError(ValueError):
    pass


ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
COIN_RE = re.compile(r"^[A-Z0-9]{2,12}$")
TRANCHE_TYPES = ("limit", "marketable", "conditional")


PLAN_KEYS = {"plan_id", "created", "valid_until", "manual_inputs", "blackouts", "coins"}
MANUAL_KEYS = {"etf_outflows", "etf_outflows_updated", "php_per_usdt", "php_per_usdt_updated"}
BLACKOUT_KEYS = {"name", "coins", "start", "end"}
COIN_KEYS = {"status", "narrative", "wrong_if", "tranches", "fill_by", "on_deadline", "deadline_max_price",
             "take_profit_levels", "alert_below", "alert_above", "max_pct", "meme", "paper_tested",
             "exit_now", "exit_reason", "notes"}
TRANCHE_KEYS = {"id", "type", "price", "max_price", "php", "usdt", "when", "allow_in_risk_off",
                "override_reason", "notes"}


def _known(d, allowed: set, where: str) -> None:
    """Typos like `wrongif:` must fail loudly instead of being silently ignored."""
    if not isinstance(d, dict):
        raise ConfigError(f"{where}: expected a mapping, got {type(d).__name__}")
    extra = set(d) - allowed
    if extra:
        raise ConfigError(f"{where}: unknown key(s) {sorted(extra)}; allowed: {sorted(allowed)}")


def _req(d: dict, key: str, where: str):
    if key not in d or d[key] is None:
        raise ConfigError(f"{where}: missing '{key}'")
    return d[key]


def _num(v, where: str, positive: bool = True) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ConfigError(f"{where}: expected a number, got {v!r}")
    if positive and x <= 0:
        raise ConfigError(f"{where}: must be > 0, got {v!r}")
    return x


# ---------------------------------------------------------------- config

@dataclass
class Config:
    raw: dict
    budget_php: float
    quote: str
    venue: str
    fee: float
    fee_in_base: bool
    risk: dict
    liquidity: dict
    regime: dict
    data: dict
    unattended_risk_reducing: bool
    notify: bool
    daily_paper: bool
    advisor: dict

    @property
    def is_manual(self) -> bool:
        return self.venue == "manual"


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    acct = raw.get("account", {})
    venue = raw.get("venue", {})
    risk = raw.get("risk", {})
    name = venue.get("name", "binance")
    if name not in ("binance", "binance_testnet", "manual"):
        raise ConfigError(f"venue.name must be binance | binance_testnet | manual, got {name!r}")
    cfg = Config(
        raw=raw,
        budget_php=_num(_req(acct, "budget_php", "account"), "account.budget_php"),
        quote=acct.get("quote", "USDT"),
        venue=name,
        fee=_num(venue.get("fee_pct", 0.1), "venue.fee_pct") / 100,
        fee_in_base=bool(venue.get("fee_in_base", True)),
        risk={
            "risk_pct_target": _num(risk.get("risk_pct_target", 1.5), "risk.risk_pct_target") / 100,
            "max_risk_per_coin": _num(risk.get("max_risk_pct_per_coin", 2.0), "risk.max_risk_pct_per_coin") / 100,
            "max_total_risk": _num(risk.get("max_total_risk_pct", 6.0), "risk.max_total_risk_pct") / 100,
            "max_coin": _num(risk.get("max_coin_pct", 30), "risk.max_coin_pct") / 100,
            "max_deployed": {k: _num(v, f"risk.max_deployed_pct.{k}") / 100
                             for k, v in (risk.get("max_deployed_pct") or
                                          {"risk_on": 70, "chop": 70, "risk_off": 50}).items()},
            "min_stop_atr_mult": _num(risk.get("min_stop_atr_mult", 2.7), "risk.min_stop_atr_mult"),
            "gap": _num(risk.get("stop_gap_buffer_pct", 3.0), "risk.stop_gap_buffer_pct", False) / 100,
            "stop_sell_slippage": _num(risk.get("stop_sell_slippage_pct", 2.0), "risk.stop_sell_slippage_pct") / 100,
            "max_ladder_depth": _num(risk.get("max_ladder_depth_pct", 8), "risk.max_ladder_depth_pct") / 100,
            "meme_max": _num(risk.get("memecoin_max_pct", 10), "risk.memecoin_max_pct") / 100,
            "narrative_max": int(risk.get("narrative_max_coins", 2)),
            "max_active": int(risk.get("max_active_coins", 10)),
        },
        liquidity={
            "core_min": _num(raw.get("liquidity", {}).get("core_min", 50e6), "liquidity.core_min"),
            "satellite_min": _num(raw.get("liquidity", {}).get("satellite_min", 15e6), "liquidity.satellite_min"),
        },
        regime={
            "fng_fear": float(raw.get("regime", {}).get("fng_extreme_fear", 15)),
            "fng_greed": float(raw.get("regime", {}).get("fng_greed_trim", 80)),
            "fng_max_age_h": float(raw.get("regime", {}).get("fng_max_age_hours", 48)),
            "manual_max_age_h": float(raw.get("regime", {}).get("manual_max_age_hours", 36)),
        },
        data={
            "min_history": int(raw.get("data", {}).get("min_history_days", 30)),
            "fx_warn_days": float(raw.get("data", {}).get("fx_warn_days", 14)),
            "fx_block_days": float(raw.get("data", {}).get("fx_block_days", 45)),
        },
        unattended_risk_reducing=bool(raw.get("execution", {}).get("unattended_risk_reducing", False)),
        notify=bool((raw.get("notify") or {}).get("enabled", (raw.get("notify") or {}).get("telegram", True))),
        advisor=raw.get("advisor", {}) or {},
        daily_paper=bool((raw.get("daily") or {}).get("paper_trading", False)),
    )
    for k in ("risk_on", "chop", "risk_off"):
        if k not in cfg.risk["max_deployed"]:
            raise ConfigError(f"risk.max_deployed_pct needs '{k}'")
    if cfg.risk["max_risk_per_coin"] > 0.05:
        raise ConfigError("risk.max_risk_pct_per_coin above 5% is not allowed")
    return cfg


# ---------------------------------------------------------------- plan

@dataclass
class Tranche:
    id: str
    type: str
    price: float | None        # resting limit price (type=limit)
    max_price: float | None    # cap for marketable / conditional
    php: float | None
    usdt: float | None
    when: dict | None
    allow_in_risk_off: bool = False
    override_reason: str | None = None

    @property
    def entry_price(self) -> float:
        """Worst (highest) price this tranche can buy at."""
        return self.price if self.type == "limit" else self.max_price

    def notional_usdt(self, php_per_usdt: float) -> float:
        return self.usdt if self.usdt is not None else self.php / php_per_usdt


@dataclass
class CoinPlan:
    coin: str
    status: str
    narrative: str | None
    wrong_if: float | None
    tranches: list[Tranche]
    fill_by: date | None
    on_deadline: str
    deadline_max_price: float | None
    take_profit_levels: list[float]
    alert_below: float | None
    alert_above: float | None
    max_pct: float | None
    meme: bool
    paper_tested: bool
    exit_now: bool
    exit_reason: str | None


@dataclass
class Blackout:
    name: str
    coins: list[str] | None   # None = all
    start: date
    end: date

    def covers(self, coin: str, day: date) -> bool:
        return self.start <= day <= self.end and (self.coins is None or coin in self.coins)


@dataclass
class Plan:
    plan_id: str
    created: datetime
    valid_until: datetime
    etf_outflows: bool | None
    etf_outflows_updated: datetime | None
    php_per_usdt: float
    php_per_usdt_updated: datetime
    blackouts: list[Blackout]
    coins: dict[str, CoinPlan]
    errors: dict[str, list[str]] = field(default_factory=dict)    # per-coin: these BLOCK buys
    warnings: dict[str, list[str]] = field(default_factory=dict)  # per-coin: informational


def _parse_condition(when, where: str) -> dict:
    if not isinstance(when, dict) or not (set(when) <= {"any", "all"}) or not when:
        raise ConfigError(f"{where}.when must be {{any: [...]}} or {{all: [...]}}")
    for mode, items in when.items():
        if not isinstance(items, list) or not items:
            raise ConfigError(f"{where}.when.{mode} must be a non-empty list")
        for it in items:
            if not isinstance(it, dict) or len(it) != 1:
                raise ConfigError(f"{where}.when: each condition is one key, got {it!r}")
            (k, v), = it.items()
            if k == "close_above" or k == "close_below":
                _num(v, f"{where}.when.{k}")
            elif k == "calm_days":
                if not isinstance(v, dict):
                    raise ConfigError(f"{where}.when.calm_days needs n, floor, max_tr_atr")
                int(_num(v.get("n", 2), f"{where}.calm_days.n"))
                _num(_req(v, "floor", f"{where}.calm_days"), f"{where}.calm_days.floor")
                _num(v.get("max_tr_atr", 1.0), f"{where}.calm_days.max_tr_atr")
            elif k == "breakout_50d":
                pass
            else:
                raise ConfigError(f"{where}.when: unknown condition '{k}'")
    return when


def load_plan(path: str | Path) -> Plan:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    _known(raw, PLAN_KEYS, "plan")
    _known(raw.get("manual_inputs") or {}, MANUAL_KEYS, "manual_inputs")
    pid = str(_req(raw, "plan_id", "plan"))
    if not re.match(r"^[A-Za-z0-9._-]{1,40}$", pid):
        raise ConfigError("plan_id: letters, digits, . _ - only (max 40)")
    mi = raw.get("manual_inputs", {}) or {}
    etf = mi.get("etf_outflows")
    plan = Plan(
        plan_id=pid,
        created=parse_dt(_req(raw, "created", "plan")),
        valid_until=parse_dt(_req(raw, "valid_until", "plan")),
        etf_outflows=None if etf is None else bool(etf),
        etf_outflows_updated=parse_dt(mi["etf_outflows_updated"]) if mi.get("etf_outflows_updated") else None,
        php_per_usdt=_num(_req(mi, "php_per_usdt", "manual_inputs"), "manual_inputs.php_per_usdt"),
        php_per_usdt_updated=parse_dt(_req(mi, "php_per_usdt_updated", "manual_inputs")),
        blackouts=[],
        coins={},
    )
    if plan.valid_until <= plan.created:
        raise ConfigError("plan.valid_until must be after plan.created")

    for i, b in enumerate(raw.get("blackouts") or []):
        where = f"blackouts[{i}]"
        _known(b, BLACKOUT_KEYS, where)
        coins = b.get("coins", "all")
        if coins != "all" and not (isinstance(coins, list) and coins):
            raise ConfigError(f"{where}.coins must be `all` or a list like [HYPE]")
        bo = Blackout(
            name=str(b.get("name", where)),
            coins=None if coins == "all" else [str(c).upper() for c in coins],
            start=parse_date(_req(b, "start", where)),
            end=parse_date(_req(b, "end", where)),
        )
        if bo.end < bo.start:
            raise ConfigError(f"{where}: end before start")
        plan.blackouts.append(bo)

    seen_ids = set()
    for coin, c in (raw.get("coins") or {}).items():
        coin = str(coin).upper()
        where = f"coins.{coin}"
        if not COIN_RE.match(coin):
            raise ConfigError(f"{where}: bad coin symbol")
        c = c or {}
        _known(c, COIN_KEYS, where)
        status = c.get("status", "watch")
        if status not in ("active", "watch", "off"):
            raise ConfigError(f"{where}.status must be active | watch | off")
        errs: list[str] = []
        warns: list[str] = []
        tranches = []
        for j, t in enumerate(c.get("tranches") or []):
            tw = f"{where}.tranches[{j}]"
            _known(t, TRANCHE_KEYS, tw)
            tid = str(_req(t, "id", tw))
            if not ID_RE.match(tid):
                raise ConfigError(f"{tw}.id: 1-16 chars of A-Z a-z 0-9 _ -")
            if tid in seen_ids:
                raise ConfigError(f"{tw}.id '{tid}' is used twice")
            seen_ids.add(tid)
            ttype = t.get("type", "limit")
            if ttype not in TRANCHE_TYPES:
                raise ConfigError(f"{tw}.type must be one of {TRANCHE_TYPES}")
            if ("php" in t) == ("usdt" in t):
                raise ConfigError(f"{tw}: give exactly one of php: or usdt:")
            tr = Tranche(
                id=tid, type=ttype,
                price=_num(_req(t, "price", tw), f"{tw}.price") if ttype == "limit" else None,
                max_price=_num(_req(t, "max_price", tw), f"{tw}.max_price") if ttype != "limit" else None,
                php=_num(t["php"], f"{tw}.php") if "php" in t else None,
                usdt=_num(t["usdt"], f"{tw}.usdt") if "usdt" in t else None,
                when=_parse_condition(_req(t, "when", tw), tw) if ttype == "conditional" else None,
                allow_in_risk_off=bool(t.get("allow_in_risk_off", False)),
                override_reason=t.get("override_reason"),
            )
            if tr.allow_in_risk_off and not tr.override_reason:
                raise ConfigError(f"{tw}: allow_in_risk_off needs an override_reason")
            tranches.append(tr)

        wrong_if = c.get("wrong_if")
        wrong_if = _num(wrong_if, f"{where}.wrong_if") if wrong_if is not None else None
        if status == "active" and tranches and wrong_if is None:
            errs.append("active coin with tranches has no wrong_if: no buys allowed")
        if wrong_if is not None:
            for tr in tranches:
                if tr.entry_price <= wrong_if:
                    errs.append(f"{tr.id}: buy price {tr.entry_price} is at/below wrong_if {wrong_if}")
        on_deadline = c.get("on_deadline", "cancel")
        if on_deadline not in ("cancel", "buy_rest"):
            raise ConfigError(f"{where}.on_deadline must be cancel | buy_rest")
        dmp = c.get("deadline_max_price")
        if on_deadline == "buy_rest" and dmp is None:
            warns.append("on_deadline: buy_rest needs deadline_max_price, so it is treated as cancel")
        if status == "active" and tranches and not c.get("fill_by"):
            warns.append("no fill_by date: ladders need a deadline (using valid_until)")
        if c.get("exit_now") and not c.get("exit_reason"):
            raise ConfigError(f"{where}: exit_now needs exit_reason")
        plan.coins[coin] = CoinPlan(
            coin=coin, status=status, narrative=c.get("narrative"),
            wrong_if=wrong_if, tranches=tranches,
            fill_by=parse_date(c["fill_by"]) if c.get("fill_by") else None,
            on_deadline=on_deadline,
            deadline_max_price=_num(dmp, f"{where}.deadline_max_price") if dmp is not None else None,
            take_profit_levels=[_num(x, f"{where}.take_profit_levels") for x in c.get("take_profit_levels") or []],
            alert_below=_num(c["alert_below"], f"{where}.alert_below") if c.get("alert_below") else None,
            alert_above=_num(c["alert_above"], f"{where}.alert_above") if c.get("alert_above") else None,
            max_pct=_num(c["max_pct"], f"{where}.max_pct") / 100 if c.get("max_pct") else None,
            meme=bool(c.get("meme", False)),
            paper_tested=bool(c.get("paper_tested", False)),
            exit_now=bool(c.get("exit_now", False)),
            exit_reason=c.get("exit_reason"),
        )
        if errs:
            plan.errors[coin] = errs
        if warns:
            plan.warnings[coin] = warns
    if "BTC" not in plan.coins:
        raise ConfigError("plan must include BTC (the regime is computed from it); status: watch is fine")
    return plan
