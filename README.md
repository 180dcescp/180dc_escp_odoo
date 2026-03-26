# 180DC ESCP Odoo

This repository is the source of truth for the 180DC ESCP Odoo custom code and deployment assets.

## Layout

- `addons/`: custom Odoo modules deployed on the live instance
- `backups/`: ignored local-only database dumps and restore inputs
- `migration_templates/`: CSV templates used for data migration work
- `migrations/`: database migration scripts and notes
- `ops/caddy/`: shared reverse-proxy config currently fronting the Odoo service
- `scripts/`: local validation and deployment helpers
- `scripts/server/`: tracked server-side helpers that must be installed outside the repo checkout
- `docker-compose.yml`: runtime stack definition used on the server
- `odoo.conf.template`: tracked template for the runtime Odoo config

## Runtime Secrets

Do not commit runtime secrets.

The live server keeps these untracked files outside the deployment tree:

- `/etc/180dc/odoo/.env`
- `/etc/180dc/odoo/odoo.conf`

Use `.env.example` and `odoo.conf.template` as tracked references.

## Local Validation

```bash
python3 scripts/validate_repo.py
```

## Local Odoo Only

This repository includes a local stack for testing Odoo itself without SMTP, Authentik, or Caddy.

Bootstrap local runtime files:

```bash
python3 scripts/setup_local_dev.py
```

Start the local stack:

```bash
docker compose -f docker-compose.local.yml up -d
```

Restore a local database dump from the ignored `backups/` directory:

```bash
bash scripts/local_restore.sh backups/your_dump.sql.gz
```

The local stack uses:

- `docker-compose.local.yml`
- `.env.local.example`
- `odoo.conf.local.template`
- ignored runtime files under `.local/`

The Authentik login override is disabled locally via `AUTHENTIK_OAUTH_BRIDGE_DISABLED=1`, so normal Odoo password login works against a restored production dump.

## Deployment

The deployment workflow syncs this repository to the server path and upgrades all custom modules.

Required GitHub Actions secret:

- `DEPLOY_SSH_KEY`

Required GitHub Actions variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PORT`
- `DEPLOY_PATH`

The target host must already contain valid untracked runtime files:

- `/etc/180dc/odoo/.env`
- `/etc/180dc/odoo/odoo.conf`

The target host must also provide a root-owned deploy wrapper:

- `/usr/local/bin/odoo-deploy-apply`

The tracked source for that wrapper lives at:

- `scripts/server/odoo-deploy-apply`

Install or refresh it on the host with:

```bash
sudo install -m 0755 scripts/server/odoo-deploy-apply /usr/local/bin/odoo-deploy-apply
```

The shared public entrypoint currently also depends on the tracked Caddy config at:

- `ops/caddy/Caddyfile`

That file is not pushed by `scripts/deploy.sh` yet because the live Caddy instance serves other applications besides Odoo.

Manual deploy:

```bash
DEPLOY_HOST=example \
DEPLOY_USER=deploy \
DEPLOY_PORT=22 \
DEPLOY_PATH=/opt/180dc/apps/odoo \
DEPLOY_SSH_IDENTITY_FILE=~/.ssh/your_deploy_key \
bash scripts/deploy.sh
```
