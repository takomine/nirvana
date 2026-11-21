# Nirvana

A rule-based **Binance spot** bot for your Ubuntu VM. It runs once a day right after the daily close
(08:05 Manila), checks every rule, and tells you exactly what it would do and why.

- **It never buys without you typing YES.** Live mode won't even start without a terminal.
- Spot only. No leverage, margin, futures or market orders. Every order is a limit order.
- No AI in the trading loop. The rules are plain code, so they can't hallucinate and cost nothing to run.
  Claude is optional, reviews the day's run afterwards, and has a hard $80/month cap.
- It only needs `requests` and `PyYAML`, and talks to Binance's REST API directly (no ccxt).

> No bot makes money on its own. This one enforces discipline: sizing, stops and cash rules.
> Whether you profit depends on the plan you write. Start with dry runs, then paper, then small live.

---

## What I fixed from the Grok version

| # | Problem in the Grok bot | What this bot does |
|---|---|---|
| 1 | Risk check passed ₱204 against a ₱200 cap | Strict cap. Worst case also includes a 3% gap buffer (a daily-close stop sells *after* the close, often lower) and fees on both sides |
| 2 | Stops tighter than its own 3x ATR rule were only warned about | **Blocked.** The bot also tells you the wrong-if or entry price that would pass |
| 3 | Bought "now" in Risk-off, against the rulebook | In Risk-off, only resting limits. Marketable buys need `allow_in_risk_off` plus a written reason |
| 4 | A stale manual ETF input still counted as a regime signal | Inputs older than 36h count as **unknown**, and unknowns tip the regime toward caution |
| 5 | HYPE stats quoted for "3 years" with about 2 months of data | `research` re-computes stats on real data and shows sample sizes. Coins with under 30 days of history can't be traded |
| 6 | Legacy rules conflicting with the new plan | One `plan.yaml` is the only source of levels. Each plan has an id and an expiry, and orders from an old plan get cancelled |
| 7 | Resting buys could still fill during a blackout | Resting buys are **cancelled** at blackout start and re-placed after |
| 8 | After a stop, the plan's tranches could re-buy right away | A stopped coin stays blocked until you write a new plan (new `plan_id`) |
| 9 | "Never lower a wrong-if" was only a note | Enforced. The highest wrong-if used while holding becomes a floor, and stops use it even if the plan says lower |
| 10 | Ladder deadlines weren't implemented | `fill_by` plus `on_deadline: cancel` or `buy_rest` |
| 11 | Exchange minimums, tick sizes and lot sizes weren't checked | Read from Binance per symbol. Prices and quantities round **down**, and tranches below the minimum are flagged (your ₱300 HYPE-1 is under 5 USDT) |
| 12 | Live orders came from cron with no way to confirm | Cron runs a dry check and messages you. Live mode needs your YES per order. Optionally, unattended runs may execute **stop sells and cancels only** |
| 13 | A crash or re-run could duplicate orders | Deterministic client order IDs, checked before every send. The intent is saved *before* sending, and state writes are atomic |
| 14 | An API key that can withdraw was allowed | Live mode **refuses** to run if the key can withdraw, and warns if it isn't IP-restricted or has futures/margin enabled |
| 15 | No total-portfolio risk cap | 6% max worst-case loss across all coins, plus deployment caps by regime, a 30% per-coin cap, narratives, memecoins and max coins |
| 16 | Liquidity tiers were only described | Computed from 7-day volume. Satellite coins get resting limits only; bench coins are blocked |
| 17 | A failed run went silent | Telegram alert: "run FAILED, stops NOT checked" |
| 18 | Bot positions mixed with your other coins | The bot tracks only what it bought, so a stop never sells your separate holdings |

---

## Setup on the Ubuntu VM (once)

**1. Give the VM read-only access to the private repo** (a deploy key):
```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/nirvana_deploy
cat ~/.ssh/nirvana_deploy.pub
```
Paste the key into GitHub: **takomine/nirvana → Settings → Deploy keys → Add**, and leave "Allow write access" **unticked**.
Then:
```bash
cat >> ~/.ssh/config <<'CFG'
Host github-nirvana
  HostName github.com
  User git
  IdentityFile ~/.ssh/nirvana_deploy
  IdentitiesOnly yes
CFG
git clone git@github-nirvana:takomine/nirvana.git ~/nirvana
```

**2. Install:**
```bash
sudo apt update && sudo apt install -y python3-venv git curl
sudo timedatectl set-timezone Asia/Manila
cd ~/nirvana
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q            # all tests are offline
cp .env.example .env && chmod 600 .env    # fill in later
set -a; . ./.env; set +a
.venv/bin/python -m nirvana check         # dry run against live Binance data. Sends nothing.
```

**3. Binance API key:** API Management → create key → enable **Reading** and **Spot & Margin Trading** only.
Withdrawals must be off. Restrict the key to your VM's IP. Better still, put the bot's money in a **sub-account**.

**4. Timers (daily run + auto-update):**
```bash
sed -i "s/YOURUSER/$USER/g" deploy/*.service
sudo cp deploy/*.service deploy/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nirvana.timer nirvana-update.timer
systemctl list-timers | grep nirvana
```

## How updates reach the VM
Changes go to GitHub `main` (from our chats, or your own edits there). Every 10 minutes the VM runs `deploy/update.sh`:
1. It fetches `main`. If nothing is new, it stops there.
2. It runs the test suite and loads `config.yaml` and `plan.yaml` from the new version, in a separate folder.
3. If anything fails, nothing changes and you get a Telegram message. The old version keeps running.
4. If everything passes, it **waits for any bot run in progress to finish** (they share a lock), switches to the new version, and messages you.

Your state (positions, orders), logs, reports and `.env` are never touched. **Don't edit files on the VM**,
because GitHub always wins: change `plan.yaml` in the repo instead.
To update by hand: `APP=~/nirvana ~/nirvana/deploy/update.sh`.

## Commands

| Command | What it does |
|---|---|
| `python -m nirvana check` | Dry run: every rule against live data. Sends nothing, changes nothing |
| `python -m nirvana run --mode paper` | Simulated fills using real prices (`state/state.paper.json`) |
| `python -m nirvana run --mode live` | Real orders. Asks **YES** for each one |
| `python -m nirvana run --mode live --unattended` | No prompts. Only stop sells and cancels, and only if `execution.unattended_risk_reducing: true` |
| `python -m nirvana status` | Positions, open orders, stops, Claude spend |
| `python -m nirvana review` | Claude reviews the last run (add `--model claude-opus-5-5` for a weekly deep review) |
| `python -m nirvana research BTC HYPE` | Stop noise-hit rates and the 50-day breakout, with sample sizes |
| `python -m nirvana record-fill BTC-1 --qty 0.0001 --price 60100` | For PDAX or manual trading: record a fill so stops track it |
| `python -m nirvana record-sell BTC --qty ... --price ... [--stop]` | Record a manual sell |

**PDAX:** set `venue.name: manual`. The bot prints order tickets with PHP prices, you place them by hand,
and you record the fills. PDAX's fees (about 0.40% per side, unconfirmed) are about 4x Binance's.

## Going live: checklist
1. A week of `check` runs that make sense to you.
2. Two to four weeks of `--mode paper`.
3. Optionally, `venue.name: binance_testnet` with testnet keys to test the order mechanics.
4. Live with a small budget. Turn on `unattended_risk_reducing` once you trust it, so stops still fire while you sleep.

## Claude costs
Daily Sonnet review: about $0.05–0.10 a run, so about $2–3 a month. A weekly Opus review adds about $1–2.
The bot keeps a spend ledger and skips any call that could push the month past `monthly_cap_usd`.
Also set a spend limit in the Claude Console.

---

## What the bot says about tonight's plan (2026-11-21)

Tested offline on synthetic data shaped like tonight's market. Run `check` on the VM for real numbers.

- **BTC: blocked.** The plan's worst case is about ₱281 against the ₱200 cap once the gap buffer and fees are counted. Shrink the tranches to about 70% of size.
- **BTC-1: blocked.** It's a marketable buy in Risk-off.
- **BTC-2 ($57k): blocked.** It has 8.2% stop room vs. the ~15% needed (2.7x ATR).
- **HYPE-2 ($52 vs a $48 wrong-if): blocked.** It has 7.7% stop room vs. the ~24% needed.
- **HYPE-1 (₱300): below Binance's 5 USDT minimum.** HYPE also has very little history on Binance.

**Your decisions:**
1. Resize BTC, or accept a lower budget per tranche.
2. Either drop the "buy now" tranches while it's Risk-off, or override them with a written reason.
3. Set the BTC wrong-if around $48k, or move BTC-2 higher.
4. Settle HYPE: either a wrong-if around $39 or skip the $52 tranche, and make HYPE-1 at least ₱350.
5. Confirm the BTC-3 cap (I used $63,000 as a placeholder).

## Known limits
- Stops act on the **daily close**. A crash during the day is taken in full until 08:00 the next morning, and the gap buffer only partly covers that.
- Paper fills are optimistic: a resting buy "fills" if the day's low touched the price.
- Fear & Greed comes from alternative.me. If it's down, it counts as unknown, which means more caution.
- Exits and take-profits are alerts only. You decide those.
