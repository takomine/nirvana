"""Each test pins down one bug/gap from the Grok version, or one safety rule."""
from __future__ import annotations

import textwrap
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from nirvana.advisor import AdvisorError, _add_spend, review
from nirvana.config import ConfigError, load_config, load_plan
from nirvana.regime import compute_regime
from nirvana.risk import worst_loss_for_buy
from nirvana.runner import RunError, preflight_live, run_once
from nirvana.state import State
from tests.fakes import NOW, series, tonight_market

ROOT = Path(__file__).resolve().parents[1]


def cfg(**risk):
    c = load_config(ROOT / "config.yaml")
    c.risk.update(risk)
    return c


def write_plan(tmp: Path, coins_yaml: str, extra: str = "", etf_updated="2026-11-21T22:00:00+08:00") -> Path:
    p = tmp / "plan.yaml"
    p.write_text(textwrap.dedent(f"""
        plan_id: test-1
        created: 2026-11-21T21:00:00+08:00
        valid_until: 2026-12-05T08:00:00+08:00
        manual_inputs:
          etf_outflows: true
          etf_outflows_updated: {etf_updated}
          php_per_usdt: 64
          php_per_usdt_updated: 2026-11-21T22:00:00+08:00
        {extra}
        coins:
    """) + textwrap.indent(textwrap.dedent(coins_yaml), "  "))
    return p


def run(tmp, plan_path, mode="dry", market=None, now=NOW, c=None, **kw):
    lines = []
    res = run_once(tmp, c or cfg(), load_plan(plan_path), mode, market=market or tonight_market(),
                   now=now, notify=False, out=lines.append, **kw)
    return res, "\n".join(lines)


def kinds(res, coin, tranche=None):
    return [d.kind for d in res.decisions if d.coin == coin and (tranche is None or d.tranche == tranche)]


# ------------------------------------------------------------------ shipped files

def test_shipped_config_and_plan_load():
    c = load_config(ROOT / "config.yaml")
    p = load_plan(ROOT / "plan.yaml")
    assert c.venue == "binance" and "BTC" in p.coins and p.coins["BTC"].wrong_if == 52300


def test_shipped_plan_is_blocked_for_the_right_reasons(tmp_path):
    res, text = run(tmp_path, ROOT / "plan.yaml")
    assert res.regime.name == "risk_off"
    assert res.actions == []
    assert "exceeds the 2% cap" in text                 # BTC plan risk with gap + fees
    assert "stop room 13.5%" in text                    # HYPE-2 at 52 vs wrong-if 45
    assert "below the exchange minimum" in text         # HYPE-1 ₱300 < 5 USDT
    assert "Risk-off: only resting limit" in text       # BTC-1 marketable


# ------------------------------------------------------------------ bug 1: cap check

def test_cap_is_strict_and_includes_gap_and_fees():
    # Grok said "₱204 vs cap ₱200 -> OK". Our worst-case is always >= plain loss-to-stop.
    plain = 600 / 64 * (60338.1 - 52300) / 60338.1
    ours = worst_loss_for_buy(600 / 64, 60338.1, 52300, 0.03, 0.001)
    assert ours > plain


def test_over_cap_blocks_whole_coin(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-12-04
          tranches:
            - {id: B1, type: limit, price: 56000, php: 9000}
    """)
    res, text = run(tmp_path, p)
    assert "exceeds the 2% cap" in text and not res.actions


# ------------------------------------------------------------------ bug 2: stop width enforced, not warned

def test_tight_stop_is_blocked_and_wide_stop_passes(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-12-04
          tranches:
            - {id: TIGHT, type: limit, price: 49000, php: 400}
            - {id: WIDE, type: limit, price: 56000, php: 700}
    """)
    res, _ = run(tmp_path, p)
    assert "BLOCK" in kinds(res, "BTC", "TIGHT")
    assert [a.tranche_key for a in res.actions] == ["test-1:WIDE"]
    assert res.actions[0].tif == "GTC"


# ------------------------------------------------------------------ bug 3: risk-off rules actually enforced

def test_risk_off_blocks_marketable_but_override_works(tmp_path):
    coins = """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-12-04
          tranches:
            - {{id: M1, type: marketable, max_price: 60500, php: 700{extra}}}
    """
    res, _ = run(tmp_path, write_plan(tmp_path, coins.format(extra="")))
    assert "BLOCK" in kinds(res, "BTC", "M1") and not res.actions
    res, _ = run(tmp_path, write_plan(tmp_path, coins.format(
        extra=", allow_in_risk_off: true, override_reason: panic nuke slice")))
    assert len(res.actions) == 1 and res.actions[0].tif == "IOC"
    assert float(res.actions[0].price) <= 60500


def test_no_chasing_above_cap(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-12-04
          tranches:
            - {id: M1, type: marketable, max_price: 59000, php: 500, allow_in_risk_off: true, override_reason: x}
    """)
    res, text = run(tmp_path, p)
    assert "do not chase" in text and not res.actions


# ------------------------------------------------------------------ bug 4: stale manual inputs

def test_stale_etf_input_is_unknown_and_resolves_cautious():
    btc = series(62000, 58951, 260, 0.05, shape="hump")
    rc = cfg().regime
    r = compute_regime(btc, None, True, NOW - timedelta(days=5), rc, NOW)
    assert r.signals["etf_outflows"] is None and r.signals["extreme_fear"] is None
    assert r.name == "risk_off" and r.assumed  # 1 true + 2 unknown -> cautious


def test_risk_on_needs_fresh_fng():
    up = series(30000, 90000, 260, 0.03)
    rc = cfg().regime
    assert compute_regime(up, (50, NOW), False, NOW, rc, NOW).name == "risk_on"
    assert compute_regime(up, None, False, NOW, rc, NOW).name == "chop"


# ------------------------------------------------------------------ bug 5: short history

def test_short_history_blocks_buys(tmp_path):
    m = tonight_market(candles={"HYPE": series(50, 61, 20, 0.09)})
    p = write_plan(tmp_path, """
        BTC: {status: watch}
        HYPE:
          status: active
          wrong_if: 40
          fill_by: 2026-12-04
          tranches:
            - {id: H1, type: limit, price: 58, php: 400}
    """)
    res, text = run(tmp_path, p, market=m)
    assert "too little history" in text and not res.actions


# ------------------------------------------------------------------ stops, never-lower, re-entry

def _held_state(tmp: Path, coin="BTC", qty=0.0003, cost=17.7, floor=52300):
    st = State.load(tmp / "state" / "state.paper.json")
    st.data["paper"]["balances"] = {"USDT": 140.0, coin: qty}
    st.apply_buy(coin, qty, cost, NOW.isoformat(), floor)
    st.save()
    return st


def test_daily_close_below_wrong_if_sells_everything_and_blocks_reentry(tmp_path):
    _held_state(tmp_path)
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 60000
          fill_by: 2026-12-04
          tranches:
            - {id: B1, type: limit, price: 75000, php: 800}
    """)
    res, _ = run(tmp_path, p, mode="paper")
    sells = [a for a in res.actions if a.kind == "sell"]
    assert len(sells) == 1 and sells[0].risk_reducing and not sells[0].human_only
    st = State.load(tmp_path / "state" / "state.paper.json")
    assert st.qty("BTC") == 0 and st.data["stopped"]["BTC"]["plan_id"] == "test-1"
    res2, text2 = run(tmp_path, p, mode="paper")
    assert "stopped out under this plan" in text2 and not [a for a in res2.actions if a.kind == "buy"]


def test_wick_below_wrong_if_does_not_stop(tmp_path):
    btc = series(62000, 58951.51, 260, 0.05, shape="hump")
    last = btc[-1]
    btc[-1] = type(last)(last.open_time, last.open, last.high, 50000.0, last.close, 1, 2e8)  # wick to 50k
    _held_state(tmp_path)
    p = write_plan(tmp_path, """
        BTC: {status: active, wrong_if: 52300, fill_by: 2026-12-04, tranches: []}
    """)
    res, _ = run(tmp_path, p, mode="paper", market=tonight_market(candles={"BTC": btc}))
    assert not [a for a in res.actions if a.kind == "sell"]


def test_wrong_if_can_never_be_lowered(tmp_path):
    _held_state(tmp_path, floor=52300)
    p = write_plan(tmp_path, """
        BTC: {status: active, wrong_if: 50000, fill_by: 2026-12-04, tranches: []}
    """)
    res, text = run(tmp_path, p, mode="paper")
    assert "lowers wrong-if" in text
    # stop logic uses the floor: a close between 50000 and 52300 must stop out
    btc = series(62000, 51000, 260, 0.05, shape="hump")
    res, _ = run(tmp_path, p, mode="paper", market=tonight_market(candles={"BTC": btc}, books={"BTC": (51000, 51010)}))
    assert [a for a in res.actions if a.kind == "sell"]


# ------------------------------------------------------------------ open orders: blackout, plan change, idempotency

GOOD = """
    BTC:
      status: active
      wrong_if: 46000
      fill_by: 2026-12-04
      tranches:
        - {id: B1, type: limit, price: 56000, php: 800}
"""


def test_resting_order_placed_once_then_cancelled_in_blackout(tmp_path):
    p = write_plan(tmp_path, GOOD)
    res, _ = run(tmp_path, p, mode="paper")
    assert len([a for a in res.actions if a.kind == "buy"]) == 1
    res, _ = run(tmp_path, p, mode="paper")                       # same day again: no duplicate
    assert not [a for a in res.actions if a.kind == "buy"]
    p = write_plan(tmp_path, GOOD, extra="blackouts: [{name: FOMC, coins: all, start: 2026-11-21, end: 2026-11-22}]")
    res, _ = run(tmp_path, p, mode="paper")
    assert [a.kind for a in res.actions] == ["cancel"]


def test_new_plan_id_cancels_old_orders(tmp_path):
    run(tmp_path, write_plan(tmp_path, GOOD), mode="paper")
    p = write_plan(tmp_path, GOOD)
    p.write_text(p.read_text().replace("plan_id: test-1", "plan_id: test-2"))
    res, _ = run(tmp_path, p, mode="paper")
    assert any(a.kind == "cancel" and "older plan" in a.reason for a in res.actions)


def test_paper_resting_fill_creates_position_with_floor(tmp_path):
    p = write_plan(tmp_path, GOOD)
    run(tmp_path, p, mode="paper")
    later = NOW + timedelta(days=2)
    btc = series(62000, 57000, 262, 0.05, shape="hump", last_day=(later - timedelta(days=1)).replace(hour=0, minute=0))
    btc[-1] = type(btc[-1])(btc[-1].open_time, 57500, 58000, 55500, 57000, 1, 2e8)
    run(tmp_path, p, mode="paper", now=later, market=tonight_market(candles={"BTC": btc}, books={"BTC": (57000, 57010)}))
    st = State.load(tmp_path / "state" / "state.paper.json")
    assert st.qty("BTC") > 0 and st.data["wrong_if_floor"]["BTC"] == 46000
    assert st.data["tranches"]["test-1:B1"]["status"] == "filled"


def test_deadline_expires_unfilled_tranches(tmp_path):
    p = write_plan(tmp_path, GOOD)
    res, text = run(tmp_path, p, now=NOW + timedelta(days=14))
    assert "tranche expired" in text and not res.actions


# ------------------------------------------------------------------ live safety

class FakeLive:
    def __init__(self, withdrawals):
        self.w = withdrawals

    def key_restrictions(self):
        return {"enableWithdrawals": self.w, "enableSpotAndMarginTrading": True, "ipRestrict": True}


def test_live_refuses_key_with_withdrawals():
    with pytest.raises(RunError, match="WITHDRAW"):
        preflight_live(FakeLive(True), print)
    preflight_live(FakeLive(False), print)


def test_live_needs_terminal(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(RunError, match="terminal"):
        run(tmp_path, write_plan(tmp_path, GOOD), mode="live")


def test_unattended_executes_only_risk_reducing(tmp_path):
    from nirvana.engine import Action, Result
    from nirvana.regime import Regime
    from nirvana.runner import execute
    st = State.load(tmp_path / "s.json")
    c = cfg()
    c.unattended_risk_reducing = True
    sent = []

    class B:
        def place_limit(self, *a):
            sent.append(a[-1])
            return {"status": "NEW", "executed_qty": "0", "quote_qty": "0"}

        def cancel(self, *a):
            sent.append(a[-1])
            return None

        def free(self, asset):
            return 10.0

    acts = [Action("buy", "BTC", "BTCUSDT", "nvx-buy", "b", side="BUY", tif="GTC", price=Decimal(1), qty=Decimal(1),
                   tranche_key="test-1:B1"),
            Action("sell", "BTC", "BTCUSDT", "nvs-BTC-1", "stop", side="SELL", tif="IOC", price=Decimal(1),
                   qty=Decimal(1), risk_reducing=True),
            Action("sell", "BTC", "BTCUSDT", "nvx-BTC-1", "exit", side="SELL", tif="IOC", price=Decimal(1),
                   qty=Decimal(1), risk_reducing=True, human_only=True)]
    res = Result(Regime("chop", {}, {}), [], acts)
    execute(res, B(), st, c, load_plan(write_plan(tmp_path, GOOD)), tonight_market(), "live", True, NOW.isoformat(), print)
    assert sent == ["nvs-BTC-1"]


# ------------------------------------------------------------------ plan validation

def test_plan_rejects_buy_below_wrong_if_and_duplicate_ids(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 60000
          fill_by: 2026-12-04
          tranches:
            - {id: B1, type: limit, price: 56000, php: 800}
    """)
    plan = load_plan(p)
    assert any("at/below wrong_if" in e for e in plan.errors["BTC"])
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 50000
          tranches:
            - {id: B1, type: limit, price: 56000, php: 800}
            - {id: B1, type: limit, price: 57000, php: 800}
    """)
    with pytest.raises(ConfigError, match="used twice"):
        load_plan(p)


def test_stale_fx_blocks_buys(tmp_path):
    p = write_plan(tmp_path, GOOD)
    res, text = run(tmp_path, p, now=NOW + timedelta(days=9))
    assert "php_per_usdt is 9 days old" in text and not res.actions


# ------------------------------------------------------------------ advisor budget

def test_advisor_respects_monthly_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    _add_spend(tmp_path, __import__("nirvana.timeutil", fromlist=["now_utc"]).now_utc().strftime("%Y-%m"), 79.99)
    with pytest.raises(AdvisorError, match="cap"):
        review(tmp_path, cfg().advisor, "plan", {"a": 1}, {}, session=object())


# ================================================================== Fable review regressions

from nirvana.brokers import BrokerError  # noqa: E402
from nirvana.engine import Action, Engine, Result  # noqa: E402
from nirvana.regime import Regime  # noqa: E402
from nirvana.runner import execute, sync  # noqa: E402


class FlakyBroker:
    """Times out on the first placement (order actually reaches the exchange), works afterwards."""

    def __init__(self, definite=False):
        self.orders, self.calls, self.definite = {}, 0, definite

    def place_limit(self, symbol, side, qty, price, tif, cid):
        self.calls += 1
        if self.calls == 1:
            if not self.definite:
                self.orders[cid] = {"status": "NEW", "executed_qty": "0", "quote_qty": "0"}
            raise BrokerError("timeout", None, None, definite=self.definite)
        self.orders[cid] = {"status": "NEW", "executed_qty": "0", "quote_qty": "0"}
        return self.orders[cid]

    def get_order(self, symbol, cid):
        return self.orders.get(cid)

    def free(self, asset):
        return 1000.0


def _buy_action():
    return Action("buy", "BTC", "BTCUSDT", "nvX-B1-0", "b", side="BUY", tif="GTC", price=Decimal("56000"),
                  qty=Decimal("0.0002"), tranche_key="test-1:B1", notional=11.2)


def test_timeout_on_send_keeps_order_tracked_and_never_duplicates(tmp_path):
    plan = load_plan(write_plan(tmp_path, GOOD))
    st = State.load(tmp_path / "s.json")
    b = FlakyBroker(definite=False)
    res = Result(Regime("chop", {}, {}), [], [_buy_action()])
    execute(res, b, st, cfg(), plan, tonight_market(), "paper", False, NOW.isoformat(), print)
    assert st.data["orders"]["nvX-B1-0"]["status"] == "NEW"          # still tracked as possibly live
    assert st.data["tranches"]["test-1:B1"]["status"] == "open"
    sync(st, cfg(), b, tonight_market(), NOW.isoformat(), print)    # next run finds it by client id
    e = Engine(cfg(), plan, st, tonight_market(), NOW)
    e.run()
    assert not [a for a in e.actions if a.kind == "buy"]            # no second order


def test_definite_rejection_frees_the_tranche(tmp_path):
    plan = load_plan(write_plan(tmp_path, GOOD))
    st = State.load(tmp_path / "s.json")
    execute(Result(Regime("chop", {}, {}), [], [_buy_action()]), FlakyBroker(definite=True), st, cfg(), plan,
            tonight_market(), "paper", False, NOW.isoformat(), print)
    assert st.data["orders"]["nvX-B1-0"]["status"] == "REJECTED"
    assert st.data["tranches"]["test-1:B1"]["status"] == "pending"


def test_unstoppably_small_buy_is_blocked(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-12-04
          tranches:
            - {id: B1, type: limit, price: 56000, php: 420}
    """)
    res, text = run(tmp_path, p)
    assert "too small to stop-sell" in text and not res.actions


def test_unsellable_position_is_kept_and_flagged_not_dropped(tmp_path):
    _held_state(tmp_path, coin="BTC", qty=0.00008, cost=4.9)   # ~4.7 USDT at the stop: below 5 USDT minimum
    p = write_plan(tmp_path, "BTC: {status: active, wrong_if: 60000, fill_by: 2026-12-04, tranches: []}\n")
    res, text = run(tmp_path, p, mode="paper")
    assert "SELL BY HAND" in text
    assert State.load(tmp_path / "state" / "state.paper.json").qty("BTC") > 0


def test_buy_rest_respects_per_coin_cap(tmp_path):
    p = write_plan(tmp_path, """
        BTC:
          status: active
          wrong_if: 46000
          fill_by: 2026-11-20
          on_deadline: buy_rest
          deadline_max_price: 60500
          tranches:
            - {id: B1, type: limit, price: 56000, php: 700}
            - {id: B2, type: limit, price: 55000, php: 700}
            - {id: B3, type: limit, price: 54000, php: 700}
    """)
    res, text = run(tmp_path, p)
    assert "exceeds the 2% cap" in text and not res.actions


def test_missed_stop_day_is_still_acted_on(tmp_path):
    btc = series(62000, 58951.51, 260, 0.05, shape="hump")
    c = btc[-2]
    btc[-2] = type(c)(c.open_time, c.open, c.high, 50000, 51000, 1, 2e8)   # yesterday closed below 52300
    st = _held_state(tmp_path)
    st.positions["BTC"]["opened"] = (NOW - timedelta(days=5)).isoformat()
    st.save()
    p = write_plan(tmp_path, "BTC: {status: active, wrong_if: 52300, fill_by: 2026-12-04, tranches: []}\n")
    res, text = run(tmp_path, p, mode="paper", market=tonight_market(candles={"BTC": btc}))
    assert "missed on an earlier day" in text and [a for a in res.actions if a.kind == "sell"]


def test_stale_candles_block_buys(tmp_path):
    res, text = run(tmp_path, write_plan(tmp_path, GOOD), now=NOW + timedelta(days=3))
    assert "data is stale" in text and not res.actions


def test_btc_data_failure_still_checks_stops(tmp_path):
    class Broken(type(tonight_market())):
        def candles(self, coin, days=400):
            if coin == "BTC":
                raise RuntimeError("down")
            return super().candles(coin, days)
    m = tonight_market()
    m.__class__ = Broken
    m._c["HYPE"] = series(60, 45, 120, 0.09)
    _held_state(tmp_path, coin="HYPE", qty=0.5, cost=30)
    p = write_plan(tmp_path, "BTC: {status: watch}\nHYPE: {status: active, wrong_if: 48, fill_by: 2026-12-04, tranches: []}\n")
    res, text = run(tmp_path, p, mode="paper", market=m)
    assert res.regime.name == "risk_off" and [a for a in res.actions if a.kind == "sell" and a.coin == "HYPE"]


def test_raised_wrong_if_becomes_the_floor(tmp_path):
    _held_state(tmp_path, floor=52300)
    run(tmp_path, write_plan(tmp_path, "BTC: {status: active, wrong_if: 57000, fill_by: 2026-12-04, tranches: []}\n"),
        mode="paper")
    res, text = run(tmp_path, write_plan(tmp_path, "BTC: {status: active, wrong_if: 53000, fill_by: 2026-12-04, tranches: []}\n"),
                    mode="paper")
    assert "lowers wrong-if 57000" in text


def test_preflight_fails_closed_and_refuses_transfers():
    class K:
        def __init__(self, r):
            self.r = r

        def key_restrictions(self):
            return self.r
    with pytest.raises(RunError):
        preflight_live(K({"enableSpotAndMarginTrading": True}), print)          # field missing
    with pytest.raises(RunError, match="permitsUniversalTransfer"):
        preflight_live(K({"enableWithdrawals": False, "enableSpotAndMarginTrading": True,
                          "permitsUniversalTransfer": True}), print)


def test_plan_typos_and_scalar_blackout_coins_fail_loudly(tmp_path):
    with pytest.raises(ConfigError, match="unknown key"):
        load_plan(write_plan(tmp_path, "BTC: {status: watch, wrongif: 50000}\n"))
    with pytest.raises(ConfigError, match="list like"):
        load_plan(write_plan(tmp_path, "BTC: {status: watch}\n",
                             extra="blackouts: [{name: x, coins: BTC, start: 2026-12-01, end: 2026-12-02}]"))


def test_stop_sell_retries_with_fresh_quote(tmp_path):
    plan = load_plan(write_plan(tmp_path, GOOD))
    st = State.load(tmp_path / "s.json")
    st.apply_buy("BTC", 0.0003, 17.7, NOW.isoformat(), 52300)
    sent = []

    class B:
        def place_limit(self, symbol, side, qty, price, tif, cid):
            sent.append(cid)
            if len(sent) == 1:
                return {"status": "EXPIRED", "executed_qty": "0", "quote_qty": "0"}
            return {"status": "FILLED", "executed_qty": str(qty), "quote_qty": str(qty * price)}

        def free(self, asset):
            return 0.0003
    a = Action("sell", "BTC", "BTCUSDT", "nvs-BTC-20261121-0", "stop", side="SELL", tif="IOC",
               price=Decimal("58000"), qty=Decimal("0.0003"), risk_reducing=True)
    execute(Result(Regime("chop", {}, {}), [], [a]), B(), st, cfg(), plan, tonight_market(), "paper", False,
            NOW.isoformat(), print)
    assert sent == ["nvs-BTC-20261121-0", "nvs-BTC-20261121-0-r1"] and st.qty("BTC") == 0
