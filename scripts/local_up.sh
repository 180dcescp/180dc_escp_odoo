#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.local.yml"
LOCAL_ENV="$ROOT_DIR/.local/odoo.env"
LAST_RESTORED_PATH="$ROOT_DIR/.local/last_restored_dump"
LAST_LOGIN_PATH="$ROOT_DIR/.local/last_local_login"
FORCE_RESTORE=0

latest_dump() {
  find "$ROOT_DIR/backups" -maxdepth 1 -type f -name '*.sql.gz' -print0 \
    | xargs -0 ls -1t 2>/dev/null \
    | head -n 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --force-restore)
      FORCE_RESTORE=1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: bash scripts/local_up.sh [--force-restore]" >&2
      exit 1
      ;;
  esac
  shift
done

python3 "$ROOT_DIR/scripts/setup_local_dev.py"

if [ ! -f "$LOCAL_ENV" ]; then
  echo "Missing $LOCAL_ENV after setup." >&2
  exit 1
fi

set -a
. "$LOCAL_ENV"
set +a

LATEST_DUMP="$(latest_dump)"
PREVIOUS_DUMP=""
if [ -f "$LAST_RESTORED_PATH" ]; then
  PREVIOUS_DUMP="$(cat "$LAST_RESTORED_PATH")"
fi

docker compose -f "$COMPOSE_FILE" up -d odoo-db

if [ -n "$LATEST_DUMP" ]; then
  if [ "$FORCE_RESTORE" -eq 1 ] || [ "$LATEST_DUMP" != "$PREVIOUS_DUMP" ]; then
    bash "$ROOT_DIR/scripts/local_restore.sh" "$LATEST_DUMP"
  else
    docker compose -f "$COMPOSE_FILE" up -d odoo
    echo "Local DB already matches latest dump: $LATEST_DUMP"
    if [ -f "$LAST_LOGIN_PATH" ]; then
      echo "Local login: $(cat "$LAST_LOGIN_PATH")"
      echo "Local password: $ODOO_ADMIN_PASSWORD"
    fi
  fi
else
  docker compose -f "$COMPOSE_FILE" up -d odoo
  echo "No dump found in $ROOT_DIR/backups; started local Odoo without restore."
fi
