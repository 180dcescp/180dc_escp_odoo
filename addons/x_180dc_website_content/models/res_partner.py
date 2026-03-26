from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_public_logo_url = fields.Char(string="Public Logo URL")
    x_public_sector_label = fields.Char(string="Public Sector Label")

    def _x_180dc_public_payload(self):
        self.ensure_one()
        return {
            "name": self.name,
            "logoUrl": self.x_public_logo_url or None,
            "website": self.website or None,
            "sector": self.x_public_sector_label or None,
        }
