#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/ops/compose/docker-compose.local.yml"
COMPOSE_ARGS=(--project-directory "$ROOT_DIR" -f "$COMPOSE_FILE")
LOCAL_ENV="$ROOT_DIR/.local/odoo.env"
STATE_DIR="$ROOT_DIR/.local"
LAST_RESTORED_PATH="$STATE_DIR/last_restored_dump"
LAST_LOGIN_PATH="$STATE_DIR/last_local_login"

latest_dump() {
  find "$ROOT_DIR/backups" -maxdepth 1 -type f -name '*.sql.gz' -print0 \
    | xargs -0 ls -1t 2>/dev/null \
    | head -n 1
}

DUMP_PATH="${1:-$(latest_dump)}"

if [ ! -f "$LOCAL_ENV" ]; then
  echo "Missing $LOCAL_ENV. Run: python3 ops/scripts/setup_local_dev.py" >&2
  exit 1
fi

if [ -z "$DUMP_PATH" ]; then
  echo "No .sql.gz dump found under $ROOT_DIR/backups" >&2
  exit 1
fi

if [ ! -f "$DUMP_PATH" ]; then
  echo "Dump not found: $DUMP_PATH" >&2
  exit 1
fi

set -a
. "$LOCAL_ENV"
set +a

docker compose "${COMPOSE_ARGS[@]}" up -d odoo-db

for attempt in $(seq 1 24); do
  status="$(docker inspect odoo-local-db --format '{{.State.Health.Status}}')"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 5
done

test "$(docker inspect odoo-local-db --format '{{.State.Health.Status}}')" = "healthy"

docker compose "${COMPOSE_ARGS[@]}" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" >/dev/null
docker compose "${COMPOSE_ARGS[@]}" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" >/dev/null
docker compose "${COMPOSE_ARGS[@]}" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\";" >/dev/null

gunzip -c "$DUMP_PATH" | docker compose "${COMPOSE_ARGS[@]}" exec -T odoo-db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

LOCAL_LOGIN="$(
docker compose "${COMPOSE_ARGS[@]}" run --rm --no-deps -T odoo odoo shell -c /etc/odoo/odoo.conf -d "$POSTGRES_DB" <<PY | tail -n 1
user = env['res.users'].sudo().search([('active', '=', True), ('share', '=', False)], order='id asc', limit=1)
if not user:
    user = env['res.users'].sudo().browse(1)
if not user.exists():
    raise SystemExit("No local login user available after restore.")
user.password = "$ODOO_ADMIN_PASSWORD"
env.cr.commit()
print(user.login)
PY
)"

docker compose "${COMPOSE_ARGS[@]}" up -d odoo

mkdir -p "$STATE_DIR"
printf '%s\n' "$DUMP_PATH" > "$LAST_RESTORED_PATH"
printf '%s\n' "$LOCAL_LOGIN" > "$LAST_LOGIN_PATH"

echo "Restored $DUMP_PATH into $POSTGRES_DB"
echo "Local login: $LOCAL_LOGIN"
echo "Local password: $ODOO_ADMIN_PASSWORD"
