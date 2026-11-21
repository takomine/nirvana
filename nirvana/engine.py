"""The decision engine. Pure logic: reads plan + state + market data, returns decisions and actions.

It never talks to an exchange's order endpoints. The runner executes actions (with your YES).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .config import CoinPlan, Config, Plan, Tranche
from .indicators import atr_pct, avg_quote_volume, prior_high_close, true_ranges
from .marketdata import DataError, SymbolInfo
from .regime import Regime, compute_regime
from .risk import size_for_risk, stop_width, worst_loss_for_buy, worst_loss_for_position
from .state import State
from .timeutil import age_hours, manila_date

OPEN_STATUSES = ("NEW", "PARTIALLY_FILLED")
IOC_PAD = 1.003  # marketable buys: IOC limit at most 0.3% over the ask (never above max_price)


@dataclass
class Decision:
    kind: str          # HOLD | INFO | WARN | ALERT | BLOCK | SKIP | ACTION
    coin: str
    msg: str
    tranche: str | None = None


@dataclass
class Action:
    kind: str          # buy | sell | cancel
    coin: str
    symbol: str
    client_id: str
    reason: str
    side: str | None = None
    tif: str | None = None
    price: Decimal | None = None
    qty: Decimal | None = None
    tranche_key: str | None = None
    notional: float = 0.0
    risk: float = 0.0
    risk_reducing: bool = False
    human_only: bool = False   # never executed unattended, even if risk-reducing

    def describe(self) -> str:
        if self.kind == "cancel":
            return f"CANCEL {self.client_id} ({self.coin}) - {self.reason}"
        return (f"{self.side} {self.coin} qty={self.qty} @ {self.price} {self.tif} "
                f"(~{self.notional:.2f} USDT) [{self.client_id}] - {self.reason}")


@dataclass
class CoinData:
    coin: str
    candles: list
    close: float | None = None
    atr: float | None = None        # ATR14 as fraction of close
    bid: float | None = None
    ask: float | None = None
    info: SymbolInfo | None = None
    avg_qv: float | None = None
    tier: str | None = None         # core | satellite | bench
    error: str | None = None


@dataclass
class Result:
    regime: Regime
    decisions: list[Decision]
    actions: list[Action]
    summary: dict = field(default_factory=dict)


def plan_hash(plan_id: str) -> str:
    return hashlib.sha1(plan_id.encode()).hexdigest()[:6]


class Engine:
    def __init__(self, cfg: Config, plan: Plan, state: State, market, now: datetime,
                 mode: str = "dry", free_quote: float | None = None):
        self.cfg, self.plan, self.state, self.market, self.now = cfg, plan, state, market, now
        self.mode = mode
        self.free_quote = free_quote
        self.today = manila_date(now)
        self.decisions: list[Decision] = []
        self.actions: list[Action] = []
        self.data: dict[str, CoinData] = {}
        self.budget = cfg.budget_php / plan.php_per_usdt
        self.r = cfg.risk

    # ------------------------------------------------------------ utils
    def d(self, kind, coin, msg, tranche=None):
        self.decisions.append(Decision(kind, coin, msg, tranche))

    def php(self, usdt: float) -> str:
        return f"₱{usdt * self.plan.php_per_usdt:,.0f}"

    def eff_wrong_if(self, coin: str) -> float | None:
        cp = self.plan.coins.get(coin)
        plan_w = cp.wrong_if if cp else None
        floor = self.state.data["wrong_if_floor"].get(coin)
        vals = [v for v in (plan_w, floor) if v is not None]
        return max(vals) if vals else None

    def open_orders(self, coin: str | None = None, side: str | None = None) -> list[tuple[str, dict]]:
        out = []
        for cid, o in self.state.data["orders"].items():
            if o.get("status") in OPEN_STATUSES and (coin is None or o["coin"] == coin) \
                    and (side is None or o["side"] == side):
                out.append((cid, o))
        return out

    @staticmethod
    def order_remaining_notional(o: dict) -> float:
        rem = float(o["orig_qty"]) - float(o.get("executed_qty", 0))
        return max(0.0, rem * float(o["price"]))

    # ------------------------------------------------------------ data
    def load_coin(self, coin: str) -> CoinData:
        cd = CoinData(coin=coin, candles=[])
        try:
            cd.candles = self.market.candles(coin)
            if cd.candles:
                cd.close = cd.candles[-1].close
                cd.atr = atr_pct(cd.candles, 14)
                cd.avg_qv = avg_quote_volume(cd.candles, 7)
            cd.info = self.market.info(coin)
            cd.bid, cd.ask = self.market.book(coin)
        except (DataError, Exception) as e:  # noqa: BLE001 - any data failure blocks buys for the coin
            cd.error = f"market data failed: {e}"
        if cd.avg_qv is not None:
            if cd.avg_qv >= self.cfg.liquidity["core_min"]:
                cd.tier = "core"
            elif cd.avg_qv >= self.cfg.liquidity["satellite_min"]:
                cd.tier = "satellite"
            else:
                cd.tier = "bench"
        self.data[coin] = cd
        return cd

    # ------------------------------------------------------------ main
    def run(self) -> Result:
        btc = self.load_coin("BTC")
        if btc.error or not btc.candles:
            raise DataError(f"BTC data unavailable, cannot compute regime: {btc.error}")
        regime = compute_regime(btc.candles, self.market.fear_greed(), self.plan.etf_outflows,
                                self.plan.etf_outflows_updated, self.cfg.regime, self.now)
        self.regime = regime
        for n in regime.notes:
            self.d("WARN", "REGIME", n)

        coins = [c for c, cp in self.plan.coins.items() if cp.status != "off"]
        for c in list(self.state.positions) + [o["coin"] for _, o in self.open_orders()]:
            if c not in coins:
                coins.append(c)
        for c in coins:
            if c not in self.data:
                self.load_coin(c)

        # global buy blockers
        self.global_block: list[str] = []
        fx_age_d = age_hours(self.plan.php_per_usdt_updated, self.now) / 24
        if fx_age_d > self.cfg.data["fx_block_days"]:
            self.global_block.append(f"php_per_usdt is {fx_age_d:.0f} days old: update plan.yaml")
        elif fx_age_d > self.cfg.data["fx_warn_days"]:
            self.d("WARN", "PLAN", f"php_per_usdt is {fx_age_d:.1f} days old")
        if self.now >= self.plan.valid_until:
            self.global_block.append("plan expired: write a new plan (stops still run)")
        if self.now < self.plan.created:
            self.global_block.append("plan 'created' is in the future")
        for gb in self.global_block:
            self.d("BLOCK", "PLAN", gb)
        for coin, ws in self.plan.warnings.items():
            for w in ws:
                self.d("WARN", coin, w)
        for coin, es in self.plan.errors.items():
            for e in es:
                self.d("BLOCK", coin, f"plan error: {e}")

        # A) held positions: stops, exits, alerts
        for coin in list(self.state.positions):
            self.check_position(coin)

        # B) re-validate open buy orders
        self.revalidate_open_orders()

        # C) new buys + watch reports
        for coin, cp in self.plan.coins.items():
            if cp.status == "active":
                self.evaluate_active(cp)
            elif cp.status == "watch":
                self.report_watch(cp)

        if regime.values.get("fng") is not None and regime.values["fng"] > self.cfg.regime["fng_greed"]:
            self.d("ALERT", "MARKET", f"Fear & Greed {regime.values['fng']} > {self.cfg.regime['fng_greed']:.0f}: trim winners")

        summ = self.portfolio_now()
        summary = {
            "budget_usdt": self.budget, "deployed_usdt": summ["deployed"], "risk_usdt": summ["risk"],
            "deployed_pct": summ["deployed"] / self.budget, "risk_pct": summ["risk"] / self.budget,
            "max_deployed_pct": self.r["max_deployed"][regime.name],
        }
        return Result(regime, self.decisions, self.actions, summary)

    # ------------------------------------------------------------ portfolio accounting
    def portfolio_now(self) -> dict:
        """Deployed + risk from positions, open buy orders, and actions already approved this run."""
        deployed = risk = 0.0
        per_coin_dep: dict[str, float] = {}
        per_coin_risk: dict[str, float] = {}
        cancelled = {a.client_id for a in self.actions if a.kind == "cancel"}
        selling = {a.coin for a in self.actions if a.kind == "sell"}
        for coin, pos in self.state.positions.items():
            if coin in selling:
                continue
            cd = self.data.get(coin)
            mark = cd.close if cd and cd.close else 0.0
            val = max(pos["cost_usdt"], pos["qty"] * mark)
            w = self.eff_wrong_if(coin)
            rk = worst_loss_for_position(pos["qty"], pos["cost_usdt"], mark, w, self.r["gap"], self.cfg.fee) \
                if w is not None else val
            per_coin_dep[coin] = per_coin_dep.get(coin, 0) + val
            per_coin_risk[coin] = per_coin_risk.get(coin, 0) + rk
        for cid, o in self.open_orders(side="BUY"):
            if cid in cancelled:
                continue
            n = self.order_remaining_notional(o)
            w = self.eff_wrong_if(o["coin"])
            rk = worst_loss_for_buy(n, float(o["price"]), w, self.r["gap"], self.cfg.fee) if w else n
            per_coin_dep[o["coin"]] = per_coin_dep.get(o["coin"], 0) + n
            per_coin_risk[o["coin"]] = per_coin_risk.get(o["coin"], 0) + rk
        for a in self.actions:
            if a.kind == "buy":
                per_coin_dep[a.coin] = per_coin_dep.get(a.coin, 0) + a.notional
                per_coin_risk[a.coin] = per_coin_risk.get(a.coin, 0) + a.risk
        deployed = sum(per_coin_dep.values())
        risk = sum(per_coin_risk.values())
        return {"deployed": deployed, "risk": risk, "per_coin_dep": per_coin_dep, "per_coin_risk": per_coin_risk}

    # ------------------------------------------------------------ A) positions
    def check_position(self, coin: str) -> None:
        pos = self.state.positions[coin]
        cd = self.data.get(coin)
        cp = self.plan.coins.get(coin)
        w = self.eff_wrong_if(coin)
        if cd is None or cd.error or cd.close is None:
            self.d("ALERT", coin, f"HOLDING {pos['qty']:.8g} but {cd.error if cd else 'no data'}: "
                                  "stop cannot be checked, check it by hand!")
            return
        if cp and cp.wrong_if is not None and w is not None and cp.wrong_if < w:
            self.d("BLOCK", coin, f"plan lowers wrong-if {w} -> {cp.wrong_if}: not allowed while holding; keeping {w}")
        if w is None:
            self.d("ALERT", coin, "holding a position with NO wrong-if: add one to plan.yaml")
            return
        mark = cd.close
        gain = (pos["qty"] * mark) / pos["cost_usdt"] - 1 if pos["cost_usdt"] > 0 else 0.0
        last_day = cd.candles[-1].open_time.date().isoformat()

        if mark < w:
            self.stop_out(coin, cd, f"daily close {mark:g} ({last_day} UTC) < wrong-if {w:g}")
            return
        if cp and cp.exit_now:
            self.sell_all(coin, cd, f"exit_now: {cp.exit_reason}", prefix="nvx", human_only=True)
            return

        msg = f"hold {pos['qty']:.8g} cost {pos['cost_usdt']:.2f} USDT, close {mark:g}, P/L {gain:+.1%}, wrong-if {w:g}"
        self.d("HOLD", coin, msg)
        if cd.atr and mark < w * (1 + cd.atr):
            self.d("ALERT", coin, f"close is within 1 ATR of the wrong-if ({w:g})")
        if gain >= 0.40:
            self.d("ALERT", coin, f"up {gain:.0%}: playbook says take 25-50% off into strength")
        for lvl in (cp.take_profit_levels if cp else []):
            if mark >= lvl:
                self.d("ALERT", coin, f"close {mark:g} >= take-profit level {lvl:g}: consider trimming 25-50%")
        ph = prior_high_close(cd.candles, 50)
        if ph is not None and mark > ph:
            self.d("ALERT", coin, f"ADD signal: close above prior 50-day high close {ph:g} (backtested; you decide)")

    def stop_out(self, coin: str, cd: CoinData, why: str) -> None:
        for cid, o in self.open_orders(coin=coin, side="BUY"):
            self.actions.append(Action("cancel", coin, self.market.symbol(coin), cid,
                                       "stop triggered: cancel open buys", risk_reducing=True))
        self.sell_all(coin, cd, f"WRONG-IF STOP: {why}", prefix="nvs", human_only=False)

    def sell_all(self, coin: str, cd: CoinData, why: str, prefix: str, human_only: bool) -> None:
        qty = self.state.qty(coin)
        if cd.bid is None or cd.info is None:
            self.d("ALERT", coin, f"{why} but no order book / symbol info: SELL BY HAND")
            return
        price = cd.info.round_price_down(cd.bid * (1 - self.r["stop_sell_slippage"]))
        q = cd.info.round_qty_down(qty)
        notional = float(q * price)
        if q <= 0 or Decimal(str(notional)) < cd.info.min_notional:
            self.d("ALERT", coin, f"{why}; remaining {qty:.8g} is dust below the exchange minimum: closing the record")
            self.actions.append(Action("sell", coin, self.market.symbol(coin), "dust", why, side="SELL",
                                       qty=Decimal(0), price=price, risk_reducing=True))
            return
        n = sum(1 for k in self.state.data["orders"] if k.startswith(f"{prefix}-{coin}-{self.today:%Y%m%d}"))
        cid = f"{prefix}-{coin}-{self.today:%Y%m%d}-{n}"
        self.actions.append(Action("sell", coin, self.market.symbol(coin), cid, why, side="SELL", tif="IOC",
                                   price=price, qty=q, notional=notional,
                                   risk_reducing=True, human_only=human_only))
        self.d("ACTION", coin, f"SELL ALL {q} @ >= {price} IOC - {why}")

    # ------------------------------------------------------------ B) open orders
    def revalidate_open_orders(self) -> None:
        for cid, o in self.open_orders(side="BUY"):
            coin = o["coin"]
            reason = self.open_order_problem(cid, o)
            if reason:
                self.actions.append(Action("cancel", coin, self.market.symbol(coin), cid, reason, risk_reducing=True))
                self.d("ACTION", coin, f"cancel resting buy {cid}: {reason}", o.get("tranche_id"))
            else:
                self.d("INFO", coin, f"resting buy {cid} @ {o['price']} still valid", o.get("tranche_id"))

    def open_order_problem(self, cid: str, o: dict) -> str | None:
        coin = o["coin"]
        if any(a.kind == "cancel" and a.client_id == cid for a in self.actions):
            return None  # already being cancelled (stop)
        cp = self.plan.coins.get(coin)
        if o.get("plan_id") != self.plan.plan_id:
            return "order belongs to an older plan"
        if self.global_block:
            return self.global_block[0]
        if cp is None or cp.status != "active":
            return "coin is no longer active in the plan"
        if coin in self.plan.errors:
            return "plan has errors for this coin"
        if self.is_stopped(coin):
            return "coin was stopped out under this plan"
        bo = self.blackout(coin)
        if bo:
            return f"blackout: {bo}"
        if self.past_deadline(cp):
            return "past fill_by deadline"
        cd = self.data.get(coin)
        w = self.eff_wrong_if(coin)
        if cd and cd.atr and w:
            sw = stop_width(float(o["price"]), w)
            if sw < self.r["min_stop_atr_mult"] * cd.atr:
                return (f"stop room {sw:.1%} is now < {self.r['min_stop_atr_mult']}x ATR "
                        f"({self.r['min_stop_atr_mult'] * cd.atr:.1%})")
        return None

    # ------------------------------------------------------------ C) new buys
    def is_stopped(self, coin: str) -> bool:
        s = self.state.data["stopped"].get(coin)
        return bool(s and s.get("plan_id") == self.plan.plan_id)

    def blackout(self, coin: str) -> str | None:
        for b in self.plan.blackouts:
            if b.covers(coin, self.today):
                return f"{b.name} ({b.start}..{b.end})"
        return None

    def deadline(self, cp: CoinPlan):
        return cp.fill_by or manila_date(self.plan.valid_until)

    def past_deadline(self, cp: CoinPlan) -> bool:
        return self.today > self.deadline(cp)

    def tranche_remaining(self, cp: CoinPlan, t: Tranche) -> float:
        st = self.state.tranche(self.plan.plan_id, t.id)
        if st["status"] in ("filled", "expired"):
            return 0.0
        rem = t.notional_usdt(self.plan.php_per_usdt) - st.get("filled_cost", 0.0)
        cd = self.data.get(cp.coin)
        min_n = float(cd.info.min_notional) if cd and cd.info else 5.0
        return rem if rem >= min_n else 0.0

    def has_open_order(self, key: str) -> bool:
        return any(o.get("tranche_key") == key for _, o in self.open_orders())

    def condition_met(self, cd: CoinData, when: dict) -> tuple[bool, str]:
        """{any: [...]} and/or {all: [...]}; every mode given must hold."""
        verdicts, notes = [], []
        for mode, items in when.items():
            results = [self.one_condition(cd, k, v) for it in items for k, v in it.items()]
            agg = any if mode == "any" else all
            verdicts.append(agg(ok for ok, _ in results))
            notes += [n for _, n in results]
        return all(verdicts), "; ".join(notes)

    def one_condition(self, cd: CoinData, k: str, v) -> tuple[bool, str]:
        if k == "close_above":
            ok = cd.close > float(v)
            return ok, f"close {cd.close:g} {'>' if ok else '<='} {v}"
        if k == "close_below":
            ok = cd.close < float(v)
            return ok, f"close {cd.close:g} {'<' if ok else '>='} {v}"
        if k == "breakout_50d":
            ph = prior_high_close(cd.candles, 50)
            ok = ph is not None and cd.close > ph
            return ok, f"50d-high breakout {'yes' if ok else 'no'}"
        if k == "calm_days":
            n = int(v.get("n", 2))
            floor = float(v["floor"])
            mult = float(v.get("max_tr_atr", 1.0))
            trs = true_ranges(cd.candles)[-n:]
            atr_abs = (cd.atr or 0) * cd.close
            last = cd.candles[-n:]
            ok = (len(last) == n and atr_abs > 0 and all(c.close > floor for c in last)
                  and all(tr <= mult * atr_abs for tr in trs))
            return ok, f"{n} calm days (closes > {floor:g}, range <= {mult}x ATR) {'yes' if ok else 'no'}"
        return False, f"unknown condition {k}"

    def evaluate_active(self, cp: CoinPlan) -> None:
        coin = cp.coin
        cd = self.data[coin]
        w = self.eff_wrong_if(coin)
        sym = self.market.symbol(coin)

        # coin-level blockers
        block = None
        if self.global_block:
            block = self.global_block[0]
        elif coin in self.plan.errors:
            block = "plan errors (see above)"
        elif cd.error:
            block = cd.error
        elif cd.info is None or cd.info.status != "TRADING":
            block = f"{sym} is not TRADING on the exchange"
        elif len(cd.candles) < self.cfg.data["min_history"] or cd.atr is None:
            block = f"only {len(cd.candles)} closed daily candles (< {self.cfg.data['min_history']}): too little history"
        elif cd.tier == "bench":
            block = f"7d avg volume ${cd.avg_qv / 1e6:.1f}M < ${self.cfg.liquidity['satellite_min'] / 1e6:.0f}M: bench only"
        elif self.is_stopped(coin):
            block = "stopped out under this plan: write a new plan (new plan_id) to re-enter"
        elif cp.meme and self.mode == "live" and not cp.paper_tested:
            block = "memecoin: paper-trade first (set paper_tested: true)"
        elif w is None:
            block = "no wrong-if"
        elif cd.close is not None and cd.close <= w:
            block = f"close {cd.close:g} is at/below the wrong-if {w:g}"
        elif cp.wrong_if is not None and cp.wrong_if < w:
            block = f"plan wrong-if {cp.wrong_if:g} is below the held floor {w:g} (never lower a wrong-if)"
        bo = self.blackout(coin)

        info_line = (f"close {cd.close:g}, ATR14 {cd.atr:.1%}, {self.r['min_stop_atr_mult']}xATR stop room "
                     f"{self.r['min_stop_atr_mult'] * cd.atr:.1%}, tier {cd.tier}") if cd.atr and cd.close else ""
        if info_line:
            self.d("INFO", coin, info_line)

        # deadline handling
        if self.past_deadline(cp):
            rest = [(t, self.tranche_remaining(cp, t)) for t in cp.tranches]
            rest = [(t, r) for t, r in rest if r > 0 and not self.has_open_order(f"{self.plan.plan_id}:{t.id}")]
            if not rest:
                return
            if cp.on_deadline == "buy_rest" and cp.deadline_max_price and not block and not bo:
                total = sum(r for _, r in rest)
                t0 = rest[0][0]
                synth = Tranche(id=f"{t0.id}", type="marketable", max_price=cp.deadline_max_price, price=None,
                                php=None, usdt=total, when=None)
                for t, _ in rest[1:]:
                    self.state.tranche(self.plan.plan_id, t.id)["status"] = "expired"
                self.d("INFO", coin, f"fill_by {self.deadline(cp)} passed: buying the rest ({total:.2f} USDT)")
                self.try_buy(cp, cd, synth, w, total)
            else:
                for t, _ in rest:
                    self.state.tranche(self.plan.plan_id, t.id)["status"] = "expired"
                    self.d("SKIP", coin, f"fill_by {self.deadline(cp)} passed: tranche expired", t.id)
            return

        if block:
            self.d("BLOCK", coin, f"no new buys: {block}")
            return
        if bo:
            self.d("BLOCK", coin, f"no new buys: blackout {bo}")
            return

        # plan-level per-coin caps (all remaining tranches + holdings + open orders)
        port = self.portfolio_now()
        planned = [(t, self.tranche_remaining(cp, t)) for t in cp.tranches]
        planned = [(t, r) for t, r in planned if r > 0 and not self.has_open_order(f"{self.plan.plan_id}:{t.id}")]
        planned_risk = sum(worst_loss_for_buy(r, t.entry_price, w, self.r["gap"], self.cfg.fee) for t, r in planned)
        planned_dep = sum(r for _, r in planned)
        coin_risk = port["per_coin_risk"].get(coin, 0) + planned_risk
        cap_risk = self.r["max_risk_per_coin"] * self.budget
        coin_dep = port["per_coin_dep"].get(coin, 0) + planned_dep
        cap_dep = min(self.r["max_coin"], cp.max_pct or 1.0) * self.budget
        self.d("INFO", coin, f"plan worst case {self.php(coin_risk)} vs cap {self.php(cap_risk)} "
                             f"({coin_risk / self.budget:.2%} of budget, incl. {self.r['gap']:.0%} gap + fees); "
                             f"exposure {self.php(coin_dep)} vs cap {self.php(cap_dep)}")
        diagnose = False
        if coin_risk > cap_risk + 1e-9:
            scale = (cap_risk - port["per_coin_risk"].get(coin, 0)) / planned_risk if planned_risk else 0
            self.d("BLOCK", coin, f"plan risk {self.php(coin_risk)} exceeds the {self.r['max_risk_per_coin']:.0%} cap "
                                  f"{self.php(cap_risk)}: shrink remaining tranches to ~{max(scale, 0):.0%} of size. "
                                  "No buys for this coin; per-tranche checks below are for information")
            diagnose = True
        if coin_dep > cap_dep + 1e-9:
            self.d("BLOCK", coin, f"plan exposure {self.php(coin_dep)} exceeds the per-coin cap {self.php(cap_dep)}. "
                                  "No buys for this coin")
            diagnose = True

        for t in cp.tranches:
            st = self.state.tranche(self.plan.plan_id, t.id)
            n = t.notional_usdt(self.plan.php_per_usdt)
            min_n = float(cd.info.min_notional)
            if st.get("filled_cost", 0) == 0 and st["status"] == "pending" and n < min_n:
                self.d("WARN", coin, f"tranche is {n:.2f} {self.cfg.quote} ({self.php(n)}), below the exchange minimum "
                                     f"{min_n:g} {self.cfg.quote} (~{self.php(min_n)}): it will never be placed", t.id)

        first_entry = cp.tranches[0].entry_price if cp.tranches else None
        for t, rem in planned:
            if first_entry and (first_entry - t.entry_price) / first_entry > self.r["max_ladder_depth"]:
                self.d("WARN", coin, f"tranche is {(first_entry - t.entry_price) / first_entry:.0%} below the first: "
                                     "deep ladder parts rarely fill (backtest)", t.id)
            if t.type == "conditional":
                met, why = self.condition_met(cd, t.when)
                if not met:
                    self.d("SKIP", coin, f"condition not met: {why}", t.id)
                    continue
                self.d("INFO", coin, f"condition met: {why}", t.id)
            self.try_buy(cp, cd, t, w, rem, diagnose=diagnose)

    def try_buy(self, cp: CoinPlan, cd: CoinData, t: Tranche, w: float, notional: float,
                diagnose: bool = False) -> None:
        coin, info = cp.coin, cd.info
        key = f"{self.plan.plan_id}:{t.id}"
        ask = cd.ask

        # what kind of order would this actually be?
        if t.type == "limit" and t.price < ask:
            marketable, price = False, t.price
        else:
            cap = t.max_price if t.type != "limit" else t.price
            if ask > cap:
                self.d("SKIP", coin, f"ask {ask:g} above cap {cap:g}: do not chase", t.id)
                return
            marketable, price = True, min(cap, ask * IOC_PAD)

        if marketable and self.regime.name == "risk_off" and not t.allow_in_risk_off:
            self.d("BLOCK", coin, "Risk-off: only resting limit buys at pre-set levels, no buying at market "
                                  "(set allow_in_risk_off + override_reason to override)", t.id)
            return
        if marketable and cd.tier == "satellite":
            self.d("BLOCK", coin, "satellite liquidity tier: resting limits only", t.id)
            return
        if t.allow_in_risk_off and self.regime.name == "risk_off" and marketable:
            self.d("WARN", coin, f"risk-off override used: {t.override_reason}", t.id)

        entry = t.entry_price  # worst case: the limit price or the cap
        if entry <= w:
            self.d("BLOCK", coin, f"entry {entry:g} at/below wrong-if {w:g}", t.id)
            return
        sw = stop_width(entry, w)
        need = self.r["min_stop_atr_mult"] * cd.atr
        if sw < need:
            max_w = entry * (1 - need)
            min_entry = w / (1 - need)
            self.d("BLOCK", coin, f"stop room {sw:.1%} < {self.r['min_stop_atr_mult']}x ATR ({need:.1%}): noise would "
                                  f"likely stop it out. Needs wrong-if <= {max_w:.6g} or entry >= {min_entry:.6g}", t.id)
            return

        risk = worst_loss_for_buy(notional, entry, w, self.r["gap"], self.cfg.fee)
        if diagnose:
            self.d("INFO", coin, f"tranche itself passes the stop-room and regime checks "
                                 f"(stop room {sw:.1%} = {sw / cd.atr:.1f}x ATR, worst case {self.php(risk)})", t.id)
            return
        port = self.portfolio_now()
        cap_dep = self.r["max_deployed"][self.regime.name] * self.budget
        if port["deployed"] + notional > cap_dep + 1e-9:
            self.d("BLOCK", coin, f"would deploy {self.php(port['deployed'] + notional)} > "
                                  f"{self.r['max_deployed'][self.regime.name]:.0%} cap {self.php(cap_dep)} in {self.regime.label()}", t.id)
            return
        cap_total = self.r["max_total_risk"] * self.budget
        if port["risk"] + risk > cap_total + 1e-9:
            self.d("BLOCK", coin, f"total portfolio risk would be {self.php(port['risk'] + risk)} > cap {self.php(cap_total)}", t.id)
            return
        if cp.meme:
            meme_dep = sum(v for c, v in port["per_coin_dep"].items()
                           if self.plan.coins.get(c) and self.plan.coins[c].meme)
            if meme_dep + notional > self.r["meme_max"] * self.budget:
                self.d("BLOCK", coin, "memecoin cap reached", t.id)
                return
        holding = {c for c, v in port["per_coin_dep"].items() if v > 0}
        if coin not in holding:
            if len(holding) >= self.r["max_active"]:
                self.d("BLOCK", coin, f"already {len(holding)} active coins (max {self.r['max_active']})", t.id)
                return
            if cp.narrative:
                same = [c for c in holding if self.plan.coins.get(c) and self.plan.coins[c].narrative == cp.narrative]
                if len(same) >= self.r["narrative_max"]:
                    self.d("BLOCK", coin, f"narrative '{cp.narrative}' already has {', '.join(same)}", t.id)
                    return
        if self.free_quote is not None:
            spent = sum(a.notional for a in self.actions if a.kind == "buy")
            if spent + notional > self.free_quote:
                self.d("BLOCK", coin, f"not enough free {self.cfg.quote}: {self.free_quote - spent:.2f} left", t.id)
                return

        p = info.round_price_down(price)
        q = info.round_qty_down(notional / float(p))
        if q < info.min_qty or q * p < info.min_notional:
            self.d("SKIP", coin, f"order {float(q * p):.2f} {self.cfg.quote} is below the exchange minimum "
                                 f"({info.min_notional})", t.id)
            return
        st = self.state.tranche(self.plan.plan_id, t.id)
        cid = f"nv{plan_hash(self.plan.plan_id)}-{t.id}-{st.get('attempts', 0)}"
        tif = "IOC" if marketable else "GTC"
        reason = (f"{'marketable' if marketable else 'resting limit'} tranche; stop room {sw:.1%} "
                  f"({sw / cd.atr:.1f}x ATR); worst case {self.php(risk)}")
        self.actions.append(Action("buy", coin, self.market.symbol(coin), cid, reason, side="BUY", tif=tif,
                                   price=p, qty=q, tranche_key=key, notional=float(q * p), risk=risk))
        self.d("ACTION", coin, f"BUY {q} @ {p} {tif} (~{float(q * p):.2f} USDT / {self.php(float(q * p))}) - {reason}", t.id)

    # ------------------------------------------------------------ watch coins
    def report_watch(self, cp: CoinPlan) -> None:
        coin, cd = cp.coin, self.data[cp.coin]
        if cd.error or cd.close is None:
            self.d("WARN", coin, cd.error or "no data")
            return
        parts = [f"watch: close {cd.close:g} ({cd.candles[-1].open_time.date()} UTC)"]
        if cd.atr:
            stop = cd.close * (1 - 3 * cd.atr)
            size = size_for_risk(self.budget, self.r["risk_pct_target"], cd.close, stop, self.r["gap"], self.cfg.fee)
            parts.append(f"ATR14 {cd.atr:.1%}, 3xATR stop ~{stop:.6g}, size at "
                         f"{self.r['risk_pct_target']:.1%} risk ~{self.php(size)}")
        if cd.tier:
            parts.append(f"tier {cd.tier}")
        if len(cd.candles) < 200:
            parts.append(f"only {len(cd.candles)}d history")
        self.d("HOLD", coin, ", ".join(parts))
        if cp.alert_below and cd.close < cp.alert_below:
            self.d("ALERT", coin, f"closed {cd.close:g} below your level {cp.alert_below:g}: review")
        if cp.alert_above and cd.close > cp.alert_above:
            self.d("ALERT", coin, f"closed {cd.close:g} above your level {cp.alert_above:g}: review")
        ph = prior_high_close(cd.candles, 50)
        if ph is not None and cd.close > ph:
            self.d("ALERT", coin, f"close above prior 50-day high close {ph:g} (backtested strength signal)")
