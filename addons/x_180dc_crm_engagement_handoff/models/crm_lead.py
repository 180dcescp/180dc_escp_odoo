from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def _x_180dc_should_create_engagement(self):
        self.ensure_one()
        return (
            self.type == "opportunity"
            and bool(self.stage_id)
            and bool(self.stage_id.is_won)
            and not self.env["x_180dc.engagement"].sudo().search_count([("lead_id", "=", self.id)])
        )

    def _x_180dc_engagement_vals(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id if self.partner_id else self.env["res.partner"]
        basis_date = fields.Date.to_date(self.date_closed) or fields.Date.context_today(self)
        cycle_code = self.env["x_180dc.engagement"]._x_180dc_cycle_code_for_date(basis_date)
        vals = {
            "name": self.name or self.partner_name or "New Engagement",
            "lead_id": self.id,
            "cycle": cycle_code,
            "cycle_year": basis_date.year,
        }
        if partner:
            vals["client_company_id"] = partner.id
        if self.partner_id and not self.partner_id.is_company:
            vals["client_contact_ids"] = [(6, 0, [self.partner_id.id])]
        return vals

    def _x_180dc_create_missing_engagements(self):
        Engagement = self.env["x_180dc.engagement"].sudo()
        for lead in self:
            if lead._x_180dc_should_create_engagement():
                Engagement.create(lead._x_180dc_engagement_vals())

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._x_180dc_create_missing_engagements()
        return leads

    def write(self, vals):
        res = super().write(vals)
        self._x_180dc_create_missing_engagements()
        return res
