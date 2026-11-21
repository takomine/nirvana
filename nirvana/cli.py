"""Command line: python -m nirvana <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config, load_plan
from .marketdata import DataError, Market
from .runner import RunError, run_lock, run_once, state_file
from .state import State
from .timeutil import now_utc


def _load(args):
    base = Path(args.dir).resolve()
    cfg = load_config(Path(args.config) if args.config else base / "config.yaml")
    plan = load_plan(Path(args.plan) if args.plan else base / "plan.yaml")
    return base, cfg, plan


def cmd_run(args) -> int:
    base, cfg, plan = _load(args)
    mode = "dry" if args.cmd == "check" else args.mode
    try:
        run_once(base, cfg, plan, mode, unattended=getattr(args, "unattended", False), notify=not args.quiet,
                 lock=False)
        if args.cmd == "check" and cfg.daily_paper:
            print("\n" + "=" * 30 + " PAPER TRADING (fake money, real prices) " + "=" * 30)
            mode = "paper"
            run_once(base, cfg, plan, "paper", notify=not args.quiet, lock=False)
    except Exception as e:  # noqa: BLE001 - any failure must reach the phone
        if cfg.notify and not args.quiet:  # a silent cron failure would mean stops go unchecked
            from .notify import send
            send(f"{e.__class__.__name__}: {e}\nStops may NOT have been checked. Look at your positions.",
                 title=f"Nirvana run FAILED ({mode})", urgent=True)
        raise
    return 0


def cmd_status(args) -> int:
    base, cfg, plan = _load(args)
    for mode in ("live", "paper"):
        p = state_file(base, mode, cfg)
        if not p.exists():
            continue
        st = State.load(p).data
        print(f"== {mode} ({p.name}) last run {st.get('last_run')}")
        for c, pos in st["positions"].items():
            print(f"  {c}: qty {pos['qty']:.8g}, cost {pos['cost_usdt']:.2f} USDT, "
                  f"wrong-if floor {st['wrong_if_floor'].get(c)}, realized {pos.get('realized_usdt', 0):+.2f}")
        opens = [(k, o) for k, o in st["orders"].items() if o.get("status") in ("NEW", "PARTIALLY_FILLED")]
        for k, o in opens:
            print(f"  open {o['side']} {o['coin']} {o['orig_qty']} @ {o['price']} [{k}]")
        for c, s in st["stopped"].items():
            print(f"  stopped: {c} under plan {s['plan_id']} ({s.get('why', '')})")
        if mode == "paper":
            bal = st["paper"].get("balances", {})
            print(f"  paper balances: {bal}")
            try:
                m = Market(quote=cfg.quote)
                equity = bal.get(cfg.quote, 0.0) + sum(q * m.book(c)[0] for c, q in bal.items() if c != cfg.quote and q)
                start = cfg.budget_php / plan.php_per_usdt
                print(f"  paper equity {equity:.2f} USDT vs start {start:.2f} ({equity / start - 1:+.2%}); "
                      f"= ₱{equity * plan.php_per_usdt:,.0f}")
            except Exception as e:  # noqa: BLE001
                print(f"  (could not price paper holdings: {e})")
            fills = [o for o in st["paper"].get("orders", {}).values() if float(o.get("executed_qty", 0)) > 0]
            for o in fills:
                print(f"  paper fill: {o['side']} {o['symbol']} {float(o['executed_qty']):.6g} @ "
                      f"{float(o['quote_qty']) / float(o['executed_qty']):.6g} ({o['placed'][:10]})")
    from .advisor import month_spend
    print(f"Claude spend this month: ${month_spend(base, now_utc().strftime('%Y-%m')):.2f}")
    return 0


def cmd_record_fill(args) -> int:
    base, cfg, plan = _load(args)
    st = State.load(state_file(base, "live", cfg))
    coin = next((c for c, cp in plan.coins.items() if any(t.id == args.tranche for t in cp.tranches)), None)
    if coin is None:
        print(f"no tranche {args.tranche} in plan {plan.plan_id}")
        return 2
    cp = plan.coins[coin]
    t = next(t for t in cp.tranches if t.id == args.tranche)
    cost = args.qty * args.price
    net = args.qty * (1 - cfg.fee) if args.fee_in_coin else args.qty
    floor = st.data["wrong_if_floor"].get(coin)
    levels = [x for x in (cp.wrong_if, floor) if x is not None]
    if not levels:
        print(f"{coin} has no wrong-if in the plan: add one before recording fills")
        return 2
    w = max(levels)
    now_s = now_utc().isoformat()
    st.apply_buy(coin, net, cost, now_s, w)
    tr = st.tranche(plan.plan_id, t.id)
    tr["filled_qty"] = tr.get("filled_qty", 0) + net
    tr["filled_cost"] = tr.get("filled_cost", 0) + cost
    if args.complete or tr["filled_cost"] >= 0.98 * t.notional_usdt(plan.php_per_usdt):
        tr["status"] = "filled"
    st.save()
    print(f"recorded BUY {coin} {net:.8g} for {cost:.2f} USDT; tranche {t.id} {tr['status']}; wrong-if {w}")
    return 0


def cmd_record_sell(args) -> int:
    base, cfg, plan = _load(args)
    st = State.load(state_file(base, "live", cfg))
    coin = args.coin.upper()
    if st.qty(coin) <= 0:
        print(f"no tracked {coin} position")
        return 2
    pnl = st.apply_sell(coin, args.qty, args.qty * args.price * (1 - cfg.fee))
    if args.stop:
        st.data["stopped"][coin] = {"plan_id": plan.plan_id, "at": now_utc().isoformat(), "why": "manual stop"}
    st.save()
    print(f"recorded SELL {coin} {args.qty:.8g} @ {args.price}; realized {pnl:+.2f} USDT")
    return 0


def cmd_review(args) -> int:
    from .advisor import AdvisorError, review
    base, cfg, plan = _load(args)
    if not cfg.advisor.get("enabled", False):
        print("advisor disabled in config.yaml")
        return 0
    log = base / "logs" / "decisions.jsonl"
    if not log.exists():
        print("no runs logged yet; run the bot first")
        return 2
    last = json.loads(log.read_text().strip().splitlines()[-1])
    st = State.load(state_file(base, last.get("mode") if last.get("mode") == "paper" else "live", cfg)).data
    plan_path = Path(args.plan) if args.plan else base / "plan.yaml"
    try:
        report, meta = review(base, cfg.advisor, plan_path.read_text(), last, st, model=args.model)
    except AdvisorError as e:
        print(f"review: {e}")
        return 1
    print(report)
    print(f"\n(saved {meta['path']})")
    if cfg.notify and not args.quiet:
        from .notify import send
        send(report[:3800], title="Nirvana: Claude review")
    return 0


def cmd_research(args) -> int:
    from .research import report
    m = Market()
    for coin in args.coins:
        try:
            print(report(coin.upper(), m.public.daily_candles(f"{coin.upper()}USDT", args.days)))
        except DataError as e:
            print(f"{coin}: {e}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nirvana", description="Rule-based Binance spot bot (human-confirmed).")
    p.add_argument("--dir", default=".", help="bot folder (config.yaml, plan.yaml, state/, logs/)")
    p.add_argument("--config")
    p.add_argument("--plan")
    p.add_argument("--quiet", action="store_true", help="no phone notification")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="dry run: validate the plan against live data, send nothing").set_defaults(fn=cmd_run)
    r = sub.add_parser("run", help="run once")
    r.add_argument("--mode", choices=("dry", "paper", "live"), default="dry")
    r.add_argument("--unattended", action="store_true",
                   help="live only: no prompts; executes ONLY stop sells/cancels, and only if config allows")
    r.set_defaults(fn=cmd_run)
    sub.add_parser("status", help="positions, open orders, stops, spend").set_defaults(fn=cmd_status)

    f = sub.add_parser("record-fill", help="manual venue: record a buy you placed by hand")
    f.add_argument("tranche")
    f.add_argument("--qty", type=float, required=True, help="coin quantity bought")
    f.add_argument("--price", type=float, required=True, help="average price in USDT")
    f.add_argument("--fee-in-coin", action="store_true", help="fee was deducted from the coin")
    f.add_argument("--complete", action="store_true", help="mark the tranche fully filled")
    f.set_defaults(fn=cmd_record_fill)
    s = sub.add_parser("record-sell", help="manual venue: record a sell you placed by hand")
    s.add_argument("coin")
    s.add_argument("--qty", type=float, required=True)
    s.add_argument("--price", type=float, required=True)
    s.add_argument("--stop", action="store_true", help="it was a wrong-if stop (blocks re-entry under this plan)")
    s.set_defaults(fn=cmd_record_sell)

    v = sub.add_parser("review", help="ask Claude to review the latest run (costs API credits, capped)")
    v.add_argument("--model", help="override advisor.model, e.g. claude-opus-5-5 for a weekly deep review")
    v.set_defaults(fn=cmd_review)
    rs = sub.add_parser("research", help="re-check stop noise rates and the 50d breakout on real data")
    rs.add_argument("coins", nargs="+")
    rs.add_argument("--days", type=int, default=1500)
    rs.set_defaults(fn=cmd_research)
    return p


STATEFUL = {"check", "run", "record-fill", "record-sell"}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd in STATEFUL:
            # lock BEFORE reading config/plan, so the auto-updater can't swap files mid-run
            with run_lock(Path(args.dir).resolve() / "state" / ".lock"):
                return args.fn(args)
        return args.fn(args)
    except (ConfigError, RunError, DataError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
