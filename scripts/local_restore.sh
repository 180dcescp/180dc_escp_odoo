#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.local.yml"
LOCAL_ENV="$ROOT_DIR/.local/odoo.env"
DUMP_PATH="${1:?path to .sql.gz dump is required}"

if [ ! -f "$LOCAL_ENV" ]; then
  echo "Missing $LOCAL_ENV. Run: python3 scripts/setup_local_dev.py" >&2
  exit 1
fi

if [ ! -f "$DUMP_PATH" ]; then
  echo "Dump not found: $DUMP_PATH" >&2
  exit 1
fi

set -a
. "$LOCAL_ENV"
set +a

docker compose -f "$COMPOSE_FILE" up -d odoo-db

for attempt in $(seq 1 24); do
  status="$(docker inspect odoo-local-db --format '{{.State.Health.Status}}')"
  if [ "$status" = "healthy" ]; then
    break
  fi
  sleep 5
done

test "$(docker inspect odoo-local-db --format '{{.State.Health.Status}}')" = "healthy"

docker compose -f "$COMPOSE_FILE" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();" >/dev/null
docker compose -f "$COMPOSE_FILE" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" >/dev/null
docker compose -f "$COMPOSE_FILE" exec -T odoo-db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$POSTGRES_DB\";" >/dev/null

gunzip -c "$DUMP_PATH" | docker compose -f "$COMPOSE_FILE" exec -T odoo-db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

docker compose -f "$COMPOSE_FILE" up -d odoo

echo "Restored $DUMP_PATH into $POSTGRES_DB"
