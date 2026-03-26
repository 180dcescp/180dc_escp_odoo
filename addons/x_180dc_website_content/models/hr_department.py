from odoo import fields, models

from .utils import html_to_plaintext, slugify_name


class HrDepartment(models.Model):
    _inherit = "hr.department"

    x_public_description = fields.Html(string="Public Department Description")

    def _x_180dc_public_payload(self):
        self.ensure_one()
        jobs = self.env["hr.job"].sudo().search(
            [("department_id", "=", self.id), ("active", "=", True)],
            order="name asc, id asc",
        )
        return {
            "slug": slugify_name(self.name),
            "name": self.name,
            "description": self.x_public_description or "",
            "summary": html_to_plaintext(self.x_public_description),
            "positions": [job._x_180dc_public_catalog_payload() for job in jobs],
        }
