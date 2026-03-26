from odoo import api, models


class HrCandidate(models.Model):
    _inherit = "hr.candidate"

    @api.model_create_multi
    def create(self, vals_list):
        candidates = super().create(vals_list)
        candidates.mapped("partner_id")._x_180dc_sync_mailing_contacts()
        return candidates

    def write(self, vals):
        res = super().write(vals)
        if {"partner_id", "email_from", "partner_name", "active"} & set(vals):
            self.mapped("partner_id")._x_180dc_sync_mailing_contacts()
        return res
