# 180DC ESCP Odoo

This repository is the source of truth for the 180DC ESCP Odoo custom code and deployment assets.

## Layout

- `addons/`: custom Odoo modules deployed on the live instance
- `migration_templates/`: CSV templates used for data migration work
- `migrations/`: database migration scripts and notes
- `scripts/`: local validation and deployment helpers
- `docker-compose.yml`: runtime stack definition used on the server
- `odoo.conf.template`: tracked template for the runtime Odoo config

## Runtime Secrets

Do not commit runtime secrets.

The live server keeps these untracked files in the deployment path:

- `.env`
- `odoo.conf`

Use `.env.example` and `odoo.conf.template` as tracked references.

## Local Validation

```bash
python3 scripts/validate_repo.py
```

## Deployment

The deployment workflow syncs this repository to the server path and upgrades all custom modules.

Required GitHub Actions secret:

- `DEPLOY_SSH_KEY`

Required GitHub Actions variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PORT`
- `DEPLOY_PATH`

The target path must already contain valid untracked runtime files:

- `.env`
- `odoo.conf`

Manual deploy:

```bash
DEPLOY_HOST=example \
DEPLOY_USER=root \
DEPLOY_PORT=22 \
DEPLOY_PATH=/opt/180dc/apps/odoo \
bash scripts/deploy.sh
```

