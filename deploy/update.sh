#!/usr/bin/env bash
# Nirvana auto-updater. Run by nirvana-update.timer every 10 minutes.
#  1. fetch origin/main; exit if nothing new
#  2. test the new commit in a throwaway worktree (unit tests + config/plan must load)
#  3. wait for any running bot (shares state/.lock), then switch to the new commit
# Never touches state/, logs/, reports/ or .env (untracked). Tracked files (incl. plan.yaml)
# always follow GitHub: change them in the repo, not on the VM.
set -euo pipefail
APP="${APP:-$HOME/nirvana}"
BRANCH="${BRANCH:-main}"
PY="$APP/.venv/bin/python"
cd "$APP"
[ -f .env ] && { set -a; . ./.env; set +a; }

notify() {
  echo "$1"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -s -m 15 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=Nirvana: $1" >/dev/null || true
  fi
}

git fetch --quiet origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0
SHORT=$(git rev-parse --short "$REMOTE")
MSG=$(git log -1 --format=%s "$REMOTE")

TMP=$(mktemp -d)
cleanup() { git worktree remove --force "$TMP" >/dev/null 2>&1 || rm -rf "$TMP"; }
trap cleanup EXIT
git worktree add --quiet --detach "$TMP" "$REMOTE"

if ! git diff --quiet "$LOCAL" "$REMOTE" -- requirements.txt requirements-dev.txt; then
  "$APP/.venv/bin/pip" install -q -r "$TMP/requirements-dev.txt"
fi
if ! (cd "$TMP" && "$PY" -m pytest -q -p no:cacheprovider >/tmp/nirvana-update-test.log 2>&1); then
  notify "update $SHORT ($MSG) FAILED its tests - still running the old version. Log: /tmp/nirvana-update-test.log"
  exit 1
fi
if ! (cd "$TMP" && "$PY" -c "from nirvana.config import load_config, load_plan; load_config('config.yaml'); load_plan('plan.yaml')" >/tmp/nirvana-update-cfg.log 2>&1); then
  notify "update $SHORT has an invalid config.yaml/plan.yaml - not deployed. $(tail -1 /tmp/nirvana-update-cfg.log)"
  exit 1
fi

mkdir -p state
exec 9>state/.lock
flock 9                       # waits here while a bot run is in progress
git reset --quiet --hard "$REMOTE"
flock -u 9
notify "updated to $SHORT: $MSG"
