#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST is required}"
DEPLOY_USER="${DEPLOY_USER:?DEPLOY_USER is required}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"
DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"

CUSTOM_MODULES="$(python3 "$ROOT_DIR/scripts/custom_modules.py" --addons-dir "$ROOT_DIR/addons" --csv)"
SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
RSYNC_SSH="ssh -p ${DEPLOY_PORT}"

rsync -az --delete \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  -e "$RSYNC_SSH" \
  "$ROOT_DIR/addons/" \
  "$SSH_TARGET:$DEPLOY_PATH/addons/"

rsync -az \
  -e "$RSYNC_SSH" \
  "$ROOT_DIR/docker-compose.yml" \
  "$ROOT_DIR/.env.example" \
  "$ROOT_DIR/odoo.conf.template" \
  "$ROOT_DIR/README.md" \
  "$SSH_TARGET:$DEPLOY_PATH/"

rsync -az --delete \
  -e "$RSYNC_SSH" \
  "$ROOT_DIR/scripts/" \
  "$SSH_TARGET:$DEPLOY_PATH/scripts/"

rsync -az --delete \
  -e "$RSYNC_SSH" \
  "$ROOT_DIR/migration_templates/" \
  "$SSH_TARGET:$DEPLOY_PATH/migration_templates/"

rsync -az --delete \
  -e "$RSYNC_SSH" \
  "$ROOT_DIR/migrations/" \
  "$SSH_TARGET:$DEPLOY_PATH/migrations/"

ssh -p "$DEPLOY_PORT" "$SSH_TARGET" "bash -s" <<EOF
set -euo pipefail
cd "$DEPLOY_PATH"
test -f .env
test -f odoo.conf
docker compose up -d odoo-db odoo
docker exec odoo odoo -c /etc/odoo/odoo.conf -d odoo -u "$CUSTOM_MODULES" --stop-after-init
docker restart odoo >/dev/null
sleep 5
test "\$(docker inspect odoo --format '{{.State.Health.Status}}')" = "healthy"
EOF
