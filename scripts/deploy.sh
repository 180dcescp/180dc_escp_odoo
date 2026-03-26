#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST is required}"
DEPLOY_USER="${DEPLOY_USER:?DEPLOY_USER is required}"
DEPLOY_PORT="${DEPLOY_PORT:-22}"
DEPLOY_PATH="${DEPLOY_PATH:?DEPLOY_PATH is required}"
REMOTE_SECRETS_DIR="${REMOTE_SECRETS_DIR:-/etc/180dc/odoo}"
DEPLOY_SSH_IDENTITY_FILE="${DEPLOY_SSH_IDENTITY_FILE:-}"

CUSTOM_MODULES="$(python3 "$ROOT_DIR/scripts/custom_modules.py" --addons-dir "$ROOT_DIR/addons" --csv)"
SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
SSH_OPTS=(-p "${DEPLOY_PORT}")
if [ -n "$DEPLOY_SSH_IDENTITY_FILE" ]; then
  SSH_OPTS+=(-i "$DEPLOY_SSH_IDENTITY_FILE" -o IdentitiesOnly=yes)
fi
RSYNC_SSH="ssh ${SSH_OPTS[*]}"

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "\
  test -f '$REMOTE_SECRETS_DIR/.env' && \
  test -f '$REMOTE_SECRETS_DIR/odoo.conf' && \
  test -x /usr/local/bin/odoo-deploy-apply"

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

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "sudo /usr/local/bin/odoo-deploy-apply '$CUSTOM_MODULES'"
