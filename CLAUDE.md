# Nirvana: notes for Claude

Nirvana is tako's spot-only Binance bot. It runs on tako's Ubuntu VM and **deploys itself from `main`**
(deploy/update.sh runs every 10 min, tests the new commit, then switches). Anything pushed to `main` is live
within about 10 minutes, so treat every push as a production deploy.

## Who does what
- **tako + Claude (in chat):** research, decide what to trade, write `plan.yaml`.
- **Nirvana (on the VM):** checks every rule daily at 08:05 Manila and proposes orders. tako confirms each buy with YES.
  Unattended runs may only execute stop sells and cancels.

## Hard rules: never weaken these, even if asked casually
- Spot only. No leverage, margin, futures or market orders.
- A buy is never sent without a human typing YES (`run --mode live` needs a TTY).
- Live mode refuses API keys that can withdraw.
- Never lower a held coin's wrong-if (the engine enforces a floor, so don't work around it).
- Never commit secrets (.env, keys). `state/`, `logs/`, `reports/` are gitignored and stay that way.
If tako wants one of these changed, explain the risk and get explicit confirmation first.

## Before every push
1. `python3 -m pytest -q`: all tests must pass (the VM refuses to deploy otherwise).
2. If you change `plan.yaml`: run a dry check if data is reachable. Otherwise verify by hand:
   - each tranche's stop room `(entry - wrong_if)/entry` >= 2.7 x ATR14 for that coin
   - worst-case loss per coin (incl. 3% gap + fees) <= 2% of the budget
   - each tranche >= ~₱350 (Binance minimum is 5 USDT)
   - fresh `manual_inputs` timestamps (ETF flows go stale after 36h, FX after 7 days)
   - a new `plan_id` when starting a fresh plan (it resets stopped coins and cancels old-plan orders)
3. Commit messages say what changed for trading, e.g. `plan: HYPE ladder 58/54, wrong-if 41`.

## Layout
- `nirvana/engine.py`: all rules (pure logic; returns decisions + actions)
- `nirvana/runner.py`: sync fills, confirm, execute, state, journal
- `nirvana/brokers.py`: Binance REST (signed) and the paper broker
- `config.yaml`: standing risk parameters. `plan.yaml`: current levels.
- `deploy/`: systemd units and the auto-updater
