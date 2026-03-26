from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    x_engagement_id = fields.Many2one(
        "x_180dc.engagement",
        string="180DC Engagement",
        ondelete="set null",
        index=True,
        domain="[('active', 'in', [True, False])]",
    )
