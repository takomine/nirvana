"""One bot run: lock -> sync fills -> evaluate -> report -> (confirm) execute -> save -> journal -> notify."""
from __future__ import annotations

import fcntl
import json
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from .brokers import BinanceBroker, BrokerError, PaperBroker
from .config import Config, Plan
from .engine import OPEN_STATUSES, Action, Decision, Engine, Result
from .marketdata import Market
from .notify import telegram
from .state import State
from .timeutil import fmt_manila, now_utc

TERMINAL = ("FILLED", "CANCELED", "EXPIRED", "REJECTED", "EXPIRED_IN_MATCH")


class RunError(RuntimeError):
    pass


@contextmanager
def run_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "w")
    import time as _t
    for _ in range(120):  # wait up to ~2 min (e.g. while the auto-updater swaps code)
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            _t.sleep(1)
    else:
        f.close()
        raise RunError("another run or an update is in progress (lock held for 2 min)")
    try:
        yield
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def state_file(base: Path, mode: str, cfg: Config) -> Path:
    if mode == "paper":
        return base / "state" / "state.paper.json"
    name = "state.testnet.json" if cfg.venue == "binance_testnet" else "state.live.json"
    return base / "state" / name


def make_broker(mode: str, cfg: Config, state: State, market: Market, now):
    if mode == "paper":
        return PaperBroker(state, market, cfg.fee, cfg.fee_in_base, now)
    if mode == "live" and not cfg.is_manual:
        return BinanceBroker(os.environ.get("BINANCE_API_KEY", ""), os.environ.get("BINANCE_API_SECRET", ""),
                             testnet=cfg.venue == "binance_testnet")
    return None


def preflight_live(broker: BinanceBroker, out) -> None:
    r = broker.key_restrictions()
    if r is None:
        out("testnet: skipping API key permission check")
        return
    if r.get("enableWithdrawals"):
        raise RunError("REFUSING TO RUN: this API key can WITHDRAW. Disable withdrawals on the key.")
    if not r.get("enableSpotAndMarginTrading"):
        raise RunError("API key has no spot trading permission")
    if not r.get("ipRestrict"):
        out("WARNING: API key is not IP-restricted. Restrict it to this VM's IP in Binance API Management.")
    for flag in ("enableFutures", "enableMargin", "enableVanillaOptions"):
        if r.get(flag):
            out(f"WARNING: API key has {flag} on. This bot is spot-only; turn it off.")


# ------------------------------------------------------------------ fills

def apply_order_update(state: State, cfg: Config, rec: dict, fresh: dict | None, now_s: str, out) -> None:
    if fresh is None:
        return
    prev_q, prev_quote = float(rec.get("executed_qty", 0)), float(rec.get("quote_qty", 0))
    new_q, new_quote = float(fresh.get("executed_qty") or 0), float(fresh.get("quote_qty") or 0)
    dq, dquote = new_q - prev_q, new_quote - prev_quote
    coin = rec["coin"]
    if dq > 1e-15:
        if rec["side"] == "BUY":
            net = dq * (1 - cfg.fee) if cfg.fee_in_base else dq
            state.apply_buy(coin, net, dquote, now_s, rec.get("wrong_if"))
            if rec.get("tranche_key"):
                t = state.data["tranches"].setdefault(rec["tranche_key"], {"status": "pending", "filled_qty": 0.0,
                                                                          "filled_cost": 0.0, "attempts": 0})
                t["filled_qty"] = t.get("filled_qty", 0.0) + net
                t["filled_cost"] = t.get("filled_cost", 0.0) + dquote
            out(f"FILL  BUY  {coin} {dq:.8g} for {dquote:.2f} USDT ({rec['client_id']})")
        else:
            proceeds = dquote * (1 - cfg.fee)
            pnl = state.apply_sell(coin, dq, proceeds)
            out(f"FILL  SELL {coin} {dq:.8g} for {proceeds:.2f} USDT, realized {pnl:+.2f} USDT ({rec['client_id']})")
    rec["executed_qty"], rec["quote_qty"] = str(new_q), str(new_quote)
    rec["status"] = fresh.get("status") or rec.get("status")
    if rec["side"] == "BUY" and rec.get("tranche_key") and rec["status"] in TERMINAL:
        t = state.data["tranches"].get(rec["tranche_key"])
        if t and t.get("status") != "expired":
            t["status"] = "filled" if rec["status"] == "FILLED" else "pending"


def sync(state: State, cfg: Config, broker, market: Market, now_s: str, out) -> list[str]:
    alerts = []
    for cid, rec in list(state.data["orders"].items()):
        if rec.get("status") not in OPEN_STATUSES:
            continue
        try:
            fresh = broker.get_order(market.symbol(rec["coin"]), cid)
        except BrokerError as e:
            alerts.append(f"could not refresh order {cid}: {e}")
            continue
        if fresh is None:
            alerts.append(f"order {cid} not found on the exchange; marking it closed")
            rec["status"] = "CANCELED"
            continue
        apply_order_update(state, cfg, rec, fresh, now_s, out)

    if isinstance(broker, BinanceBroker):
        try:
            bal = broker.balances()
        except BrokerError as e:
            alerts.append(f"could not read balances: {e}")
            return alerts
        for coin, pos in list(state.positions.items()):
            have = bal.get(coin, 0.0)
            if have < pos["qty"] * 0.999:
                alerts.append(f"{coin}: exchange balance {have:.8g} < tracked {pos['qty']:.8g} "
                              "(sold or moved outside the bot?) - tracking the lower amount")
                if have <= 0:
                    state.close_position(coin)
                else:
                    pos["cost_usdt"] *= have / pos["qty"]
                    pos["qty"] = have
    return alerts


# ------------------------------------------------------------------ report

def format_report(res: Result, plan: Plan, mode: str, venue: str, now) -> str:
    rg = res.regime
    v = rg.values
    lines = [f"Nirvana | {fmt_manila(now)} | mode={mode} venue={venue} | plan {plan.plan_id}"]
    sig = ", ".join(f"{k}={'?' if x is None else x}" for k, x in rg.signals.items())
    lines.append(f"Regime: {rg.label()} | {sig} | BTC close {v['btc_close']:g} ({v['btc_close_date']} UTC), "
                 f"SMA50 {v['sma50'] or 0:.0f}, SMA200 {v['sma200'] or 0:.0f}, F&G {v['fng']}")
    s = res.summary
    lines.append(f"Budget {s['budget_usdt']:.2f} USDT | deployed {s['deployed_pct']:.1%} "
                 f"(cap {s['max_deployed_pct']:.0%}) | worst-case risk {s['risk_pct']:.2%}")
    lines.append("")
    order = ["PLAN", "REGIME", "MARKET"] + list(plan.coins)
    coins = order + sorted({d.coin for d in res.decisions} - set(order))
    for c in coins:
        ds = [d for d in res.decisions if d.coin == c]
        if not ds:
            continue
        lines.append(f"{c}:")
        for d in ds:
            tag = f" {d.tranche}" if d.tranche else ""
            lines.append(f"  [{d.kind:6}]{tag} {d.msg}")
    lines.append("")
    if res.actions:
        lines.append(f"Actions ({len(res.actions)}):")
        for a in res.actions:
            lines.append("  - " + a.describe())
    else:
        lines.append("Actions: none")
    return "\n".join(lines)


def short_summary(res: Result, plan: Plan, mode: str) -> str:
    keep = [d for d in res.decisions if d.kind in ("ALERT", "ACTION", "BLOCK")]
    lines = [f"Nirvana ({mode}) - {res.regime.label()} - plan {plan.plan_id}"]
    for d in keep[:25]:
        lines.append(f"[{d.kind}] {d.coin}{' ' + d.tranche if d.tranche else ''}: {d.msg}")
    if res.actions and mode != "live":
        lines.append(f"{len(res.actions)} action(s) pending. To execute: python -m nirvana run --mode live")
    return "\n".join(lines)


# ------------------------------------------------------------------ execute

def confirm_tty(a: Action) -> bool:
    print("\n>>> " + a.describe())
    try:
        return input("Type YES to send this order, anything else to skip: ").strip() == "YES"
    except EOFError:
        return False


def execute(res: Result, broker, state: State, cfg: Config, plan: Plan, market: Market, mode: str,
            unattended: bool, now_s: str, out, confirm=confirm_tty) -> list[dict]:
    done = []
    if mode == "dry":
        return done
    if mode == "live" and cfg.is_manual:
        out("\nMANUAL VENUE: place these by hand, then record fills with `record-fill` / `record-sell`:")
        for a in res.actions:
            if a.kind != "cancel" and a.qty:
                out(f"  {a.side} {a.coin} ~{a.qty} @ {a.price} USDT  (= ₱{float(a.price) * plan.php_per_usdt:,.2f}/coin, "
                    f"~₱{a.notional * plan.php_per_usdt:,.0f} total)  [{a.client_id}]")
            elif a.kind == "cancel":
                out(f"  CANCEL your order for {a.client_id}: {a.reason}")
        return done

    for a in res.actions:
        if mode == "live":
            if unattended:
                if not (cfg.unattended_risk_reducing and a.risk_reducing and not a.human_only):
                    out(f"unattended: NOT executing (needs you): {a.describe()}")
                    continue
            elif not confirm(a):
                out(f"skipped by you: {a.client_id}")
                continue

        if a.client_id == "dust":
            state.close_position(a.coin)
            done.append({"action": "close_dust", "coin": a.coin})
            continue

        if a.kind == "cancel":
            rec = state.data["orders"].get(a.client_id)
            try:
                fresh = broker.cancel(a.symbol, a.client_id)
                if rec:
                    apply_order_update(state, cfg, rec, fresh, now_s, out)
                out(f"cancelled {a.client_id}: {a.reason}")
                done.append({"action": "cancel", "client_id": a.client_id})
            except BrokerError as e:
                out(f"ERROR cancelling {a.client_id}: {e}")
            state.save()
            continue

        kind = "stop" if a.client_id.startswith("nvs-") else "exit" if a.client_id.startswith("nvx-") else "buy"
        rec = {"client_id": a.client_id, "coin": a.coin, "side": a.side, "kind": kind, "tif": a.tif,
               "price": str(a.price), "orig_qty": str(a.qty), "executed_qty": "0", "quote_qty": "0",
               "status": "NEW", "plan_id": plan.plan_id, "tranche_key": a.tranche_key,
               "tranche_id": a.tranche_key.split(":", 1)[1] if a.tranche_key else None,
               "wrong_if": None, "created": now_s}
        if kind == "buy":
            cp = plan.coins.get(a.coin)
            floor = state.data["wrong_if_floor"].get(a.coin)
            rec["wrong_if"] = max(x for x in (cp.wrong_if if cp else None, floor) if x is not None)
            t = state.tranche(plan.plan_id, a.tranche_key.split(":", 1)[1])
            t["attempts"] = t.get("attempts", 0) + 1
            t["status"] = "open"
        else:
            state.data["stopped"][a.coin] = {"plan_id": plan.plan_id, "at": now_s, "why": a.reason}
        state.data["orders"][a.client_id] = rec
        state.save()  # record intent BEFORE sending, so a crash can't lose track of a live order
        try:
            fresh = broker.place_limit(a.symbol, a.side, a.qty, a.price, a.tif, a.client_id)
            apply_order_update(state, cfg, rec, fresh, now_s, out)
            out(f"sent {a.client_id}: status {rec['status']}")
            done.append({"action": a.kind, "client_id": a.client_id, "status": rec["status"]})
        except BrokerError as e:
            rec["status"] = "REJECTED"
            if a.tranche_key:
                state.data["tranches"][a.tranche_key]["status"] = "pending"
            out(f"ERROR sending {a.client_id}: {e}")
            done.append({"action": a.kind, "client_id": a.client_id, "error": str(e)})
        state.save()
    return done


# ------------------------------------------------------------------ journal

def journal(base: Path, entry: dict) -> None:
    p = base / "logs" / "decisions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def run_once(base: Path, cfg: Config, plan: Plan, mode: str, unattended: bool = False,
             market: Market | None = None, out=print, confirm=confirm_tty, now=None,
             paper_usdt: float | None = None, notify: bool = True) -> Result:
    if mode == "live" and not unattended and not sys.stdin.isatty():
        raise RunError("live mode needs a terminal to confirm orders (or use --unattended for stops only)")
    now = now or now_utc()
    now_s = now.isoformat()
    market = market or Market(quote=cfg.quote)
    with run_lock(base / "state" / ".lock"):
        spath = state_file(base, mode if mode != "dry" else "live", cfg)
        state = State.load(spath, paper_usdt=paper_usdt if mode == "paper" else None)
        if mode == "paper" and not state.data["paper"]["balances"]:
            state.data["paper"]["balances"]["USDT"] = cfg.budget_php / plan.php_per_usdt
        broker = make_broker(mode, cfg, state, market, now)
        alerts: list[str] = []
        free_quote = None
        if broker is not None:
            if isinstance(broker, BinanceBroker):
                preflight_live(broker, out)
            alerts = sync(state, cfg, broker, market, now_s, out)
            free_quote = broker.free(cfg.quote)

        eng = Engine(cfg, plan, state, market, now, mode=mode, free_quote=free_quote)
        res = eng.run()
        for a in alerts:
            res.decisions.insert(0, Decision("ALERT", "SYNC", a))
        out(format_report(res, plan, mode, cfg.venue, now))
        if mode == "dry":
            out("\nDRY-RUN: nothing sent, state not changed.")
        done = execute(res, broker, state, cfg, plan, market, mode, unattended, now_s, out, confirm)
        if mode != "dry":
            state.data["last_run"] = now_s
            state.save()
        run_id = uuid.uuid4().hex[:10]
        journal(base, {
            "run_id": run_id, "ts": now_s, "mode": mode, "venue": cfg.venue, "plan_id": plan.plan_id,
            "regime": res.regime.name, "regime_assumed": res.regime.assumed, "signals": res.regime.signals,
            "values": res.regime.values, "summary": res.summary,
            "decisions": [d.__dict__ for d in res.decisions],
            "actions": [{**a.__dict__, "price": str(a.price), "qty": str(a.qty)} for a in res.actions],
            "executed": done,
        })
        if notify and cfg.telegram:
            telegram(short_summary(res, plan, mode))
        return res
