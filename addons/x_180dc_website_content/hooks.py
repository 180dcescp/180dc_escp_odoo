from odoo import SUPERUSER_ID, api


def post_init_hook(cr_or_env, registry=None):
    env = cr_or_env if hasattr(cr_or_env, "registry") else api.Environment(cr_or_env, SUPERUSER_ID, {})
    env["x_180dc.website.settings"]._x_180dc_get_settings()
    env["x_180dc.engagement.project_type"].search([])._x_180dc_seed_public_defaults()
    env.cr.commit()
