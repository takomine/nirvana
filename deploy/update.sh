#!/usr/bin/env bash
# Nirvana auto-updater. Run by nirvana-update.timer every 10 minutes.
#  1. fetch origin/main; exit if nothing new (or if this exact commit already failed)
#  2. test the new commit in a throwaway worktree, in a SEPARATE venv, with NO secrets in the environment
#  3. wait for any running bot (shares state/.lock), then switch; install new deps only after tests pass
# Never touches state/, logs/, reports/ or .env (untracked). Tracked files (incl. plan.yaml)
# always follow GitHub: change them in the repo, not on the VM.
set -euo pipefail
APP="${APP:-$HOME/nirvana}"
BRANCH="${BRANCH:-main}"
cd "$APP"
mkdir -p logs state

# only notification settings are read from .env; trading keys never enter this script
envval() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true; }
TG_TOKEN=$(envval TELEGRAM_BOT_TOKEN); TG_CHAT=$(envval TELEGRAM_CHAT_ID)
NTFY_TOPIC=$(envval NTFY_TOPIC); NTFY_URL=$(envval NTFY_URL); NTFY_URL=${NTFY_URL:-https://ntfy.sh}
NTFY_TOKEN=$(envval NTFY_TOKEN)
notify() {
  echo "$1"
  if [ -n "$NTFY_TOPIC" ]; then
    curl -s -m 15 -H "Title: Nirvana update" ${NTFY_TOKEN:+-H "Authorization: Bearer $NTFY_TOKEN"} \
      -d "$1" "${NTFY_URL%/}/$NTFY_TOPIC" >/dev/null || true
  fi
  if [ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ]; then
    curl -s -m 15 "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TG_CHAT}" --data-urlencode "text=Nirvana: $1" >/dev/null || true
  fi
}

git fetch --quiet origin "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0
FAILED_FILE=state/.update_failed_sha
[ -f "$FAILED_FILE" ] && [ "$(cat "$FAILED_FILE")" = "$REMOTE" ] && exit 1   # already reported
SHORT=$(git rev-parse --short "$REMOTE")
MSG=$(git log -1 --format=%s "$REMOTE")
LOG="$APP/logs/update-$SHORT.log"

TMP=$(mktemp -d)
cleanup() { git worktree remove --force "$TMP" >/dev/null 2>&1 || rm -rf "$TMP"; }
trap cleanup EXIT
git worktree add --quiet --detach "$TMP" "$REMOTE"

# separate test venv, rebuilt when requirements change; the live venv is untouched until deploy
TESTVENV="$APP/.venv-test"
REQHASH=$(sha256sum "$TMP/requirements-dev.txt" | cut -c1-16)
if [ ! -x "$TESTVENV/bin/python" ] || [ "$(cat "$TESTVENV/.reqhash" 2>/dev/null)" != "$REQHASH" ]; then
  rm -rf "$TESTVENV"
  python3 -m venv "$TESTVENV"
  "$TESTVENV/bin/pip" install -q -r "$TMP/requirements-dev.txt" >"$LOG" 2>&1
  echo "$REQHASH" > "$TESTVENV/.reqhash"
fi

fail() { echo "$REMOTE" > "$FAILED_FILE"; notify "$1"; exit 1; }
SAFE_ENV=(env -i PATH=/usr/bin:/bin HOME="$TMP" LANG=C.UTF-8)
if ! (cd "$TMP" && "${SAFE_ENV[@]}" "$TESTVENV/bin/python" -m pytest -q -p no:cacheprovider >>"$LOG" 2>&1); then
  fail "update $SHORT ($MSG) FAILED its tests - still running the old version. Log: $LOG"
fi
if ! (cd "$TMP" && "${SAFE_ENV[@]}" "$TESTVENV/bin/python" -c \
      "from nirvana.config import load_config, load_plan; load_config('config.yaml'); load_plan('plan.yaml')" >>"$LOG" 2>&1); then
  fail "update $SHORT has an invalid config.yaml/plan.yaml - not deployed. $(tail -1 "$LOG")"
fi

exec 9>state/.lock
flock 9                       # waits here while a bot run is in progress
if ! git diff --quiet "$LOCAL" "$REMOTE" -- requirements.txt; then
  "$APP/.venv/bin/pip" install -q -r "$TMP/requirements.txt" >>"$LOG" 2>&1 \
    || { flock -u 9; fail "update $SHORT: installing new dependencies failed - not deployed. Log: $LOG"; }
fi
git reset --quiet --hard "$REMOTE"
rm -f "$FAILED_FILE"
flock -u 9
notify "updated to $SHORT: $MSG"
