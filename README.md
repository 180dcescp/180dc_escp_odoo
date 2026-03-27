# Student Consultancy Odoo

This repository is a free, Community-first student consultancy addon suite for
self-hosted Odoo 18 instances.

## Layout

- `addons/product/`: reusable `student_consultancy_*` addons
- `addons/distributions/`: distribution overlays such as `student_consultancy_180dc_escp`
- `docs/`: install, architecture, publishing, dependency, and upgrade docs
- `ops/`: operational tooling, templates, examples, compose files, and validation scripts
- `backups/`: ignored local-only database dumps and restore inputs

## Installable Product Modules

- `student_consultancy_meta`
- `student_consultancy_core`
- `student_consultancy_contacts`
- `student_consultancy_cycles`
- `student_consultancy_hr`
- `student_consultancy_recruitment`
- `student_consultancy_projects`
- `student_consultancy_reviews`
- `student_consultancy_website`
- `student_consultancy_180dc_escp`

## Local Validation

```bash
python3 ops/scripts/validate_repo.py
```

## Local Odoo

Bootstrap local runtime files:

```bash
python3 ops/scripts/setup_local_dev.py
```

Start the local stack:

```bash
bash ops/scripts/local_up.sh
```

The Odoo config templates now expose all addon roots:

- `/mnt/extra-addons/product`
- `/mnt/extra-addons/distributions`

## Runtime Secrets

Do not commit runtime secrets.

The live server keeps these untracked files outside the deployment tree:

- `/etc/180dc/odoo/.env`
- `/etc/180dc/odoo/odoo.conf`

Use `ops/examples/env.example` and `ops/templates/odoo.conf.template` as tracked references.

## Deployment

Required GitHub Actions secret:

- `DEPLOY_SSH_KEY`

Required GitHub Actions variables:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PORT`
- `DEPLOY_PATH`

Manual deploy:

```bash
DEPLOY_HOST=example \
DEPLOY_USER=deploy \
DEPLOY_PORT=22 \
DEPLOY_PATH=/opt/180dc/apps/odoo \
DEPLOY_SSH_IDENTITY_FILE=~/.ssh/your_deploy_key \
bash ops/scripts/deploy.sh
```

See the docs for the final product packaging direction:

- `docs/architecture.md`
- `docs/install.md`
- `docs/publishing.md`
- `docs/dependency_matrix.md`
- `docs/upgrades.md`
