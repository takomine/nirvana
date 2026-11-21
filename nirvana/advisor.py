"""Optional daily review by Claude. Read-only: it writes a report, it can never place or change orders.

Hard monthly spend cap: a call is skipped if its worst-case cost could push the month over the cap.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from .timeutil import fmt_manila, now_utc

SYSTEM = """You are the risk reviewer for a small, rule-based, spot-only crypto bot (no leverage).
You cannot place, change or cancel orders. Your job is to protect the account and catch mistakes.

The rules: regime filter (BTC vs SMA200, Fear & Greed < 15, ETF outflows; 2 of 3 = risk-off; unknown
inputs count against buying). Buys are pre-planned limit tranches; no chasing above max_price; no
market buys in risk-off. Every coin has a wrong-if; a UTC daily CLOSE below it sells everything; it is
never lowered. Each buy must sit >= ~3x ATR14 above the wrong-if. Worst-case loss per coin <= 2% of
budget (incl. gap buffer and fees), total <= 6%. Max 30% per coin, deployment caps by regime.
Blackouts before unlocks / FOMC. Indicators are timing aids only. Exits/take-profits are human calls.

Write a short review (max ~350 words, plain language, Markdown):
1. Anything that looks wrong: a bug, a rule violation, a stale input, a contradiction in the plan.
2. The biggest risk right now, in one or two sentences.
3. Decisions the human must make (numbered, concrete).
Do not predict prices. Do not recommend new coins. If everything is fine, say so briefly."""


class AdvisorError(RuntimeError):
    pass


def _ledger_path(base: Path) -> Path:
    return base / "state" / "claude_spend.json"


def month_spend(base: Path, month: str) -> float:
    p = _ledger_path(base)
    if not p.exists():
        return 0.0
    return float(json.loads(p.read_text()).get(month, 0.0))


def _add_spend(base: Path, month: str, usd: float) -> float:
    p = _ledger_path(base)
    data = json.loads(p.read_text()) if p.exists() else {}
    data[month] = float(data.get(month, 0.0)) + usd
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return data[month]


def review(base: Path, advisor_cfg: dict, plan_text: str, last_run: dict, state: dict,
           session: requests.Session | None = None, model: str | None = None) -> tuple[str, dict]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise AdvisorError("ANTHROPIC_API_KEY is not set")
    model = model or advisor_cfg.get("model", "claude-sonnet-5-5")
    prices = (advisor_cfg.get("prices_per_mtok") or {}).get(model)
    if not prices:
        raise AdvisorError(f"no price for {model} in advisor.prices_per_mtok: refusing to call without a cost estimate")
    p_in, p_out = float(prices[0]) / 1e6, float(prices[1]) / 1e6
    cap = float(advisor_cfg.get("monthly_cap_usd", 80))
    max_out = int(advisor_cfg.get("max_output_tokens", 2500))

    user = ("Latest bot run (JSON):\n" + json.dumps(last_run, default=str)[:60000] +
            "\n\nBot state (JSON):\n" + json.dumps({k: state.get(k) for k in
                                                    ("positions", "wrong_if_floor", "stopped", "tranches")},
                                                   default=str)[:20000] +
            "\n\nCurrent plan.yaml:\n" + plan_text[:20000])
    est_in = (len(SYSTEM) + len(user)) / 3.0  # conservative chars-per-token
    worst = est_in * p_in + max_out * p_out
    now = now_utc()
    month = now.strftime("%Y-%m")
    spent = month_spend(base, month)
    if spent + worst > cap:
        raise AdvisorError(f"skipped: month spend ${spent:.2f} + worst case ${worst:.2f} would exceed the ${cap:.0f} cap")

    s = session or requests.Session()
    r = s.post("https://api.anthropic.com/v1/messages", timeout=120, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": max_out, "system": SYSTEM,
              "messages": [{"role": "user", "content": user}]})
    if r.status_code != 200:
        raise AdvisorError(f"Claude API HTTP {r.status_code}: {r.text[:300]}")
    body = r.json()
    usage = body.get("usage", {})
    cost = usage.get("input_tokens", 0) * p_in + usage.get("output_tokens", 0) * p_out
    total = _add_spend(base, month, cost)
    text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    header = f"# Claude review - {fmt_manila(now)} ({model}, ${cost:.3f}; month ${total:.2f} of ${cap:.0f})\n\n"
    report = header + text
    out = base / "reports" / f"review-{now.strftime('%Y%m%d-%H%M')}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    return report, {"cost": cost, "month_total": total, "path": str(out)}
