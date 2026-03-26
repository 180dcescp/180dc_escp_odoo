from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    x_work_location_id = fields.Many2one(
        'hr.work.location',
        string='Campus / Work Location',
        tracking=True,
        index=True,
    )

    # Membership contracts are not payroll contracts in this setup.
    wage = fields.Monetary(default=0.0)
