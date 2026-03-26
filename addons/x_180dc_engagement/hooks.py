from odoo import SUPERUSER_ID, api


def post_init_hook(cr_or_env, registry=None):
    env = cr_or_env if hasattr(cr_or_env, "registry") else api.Environment(cr_or_env, SUPERUSER_ID, {})
    env["x_180dc.engagement"].search([])._x_180dc_backfill_cycle_ids()
    env.cr.commit()
