from odoo import models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _x_180dc_engagement_vals(self):
        vals = super()._x_180dc_engagement_vals()
        basis_date = self.date_closed or self.create_date
        vals["season_id"] = self.env["x_180dc.season"]._x_180dc_season_for_date(basis_date).id
        return vals
