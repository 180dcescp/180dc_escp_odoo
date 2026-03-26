from odoo import fields, models

from .utils import html_to_plaintext, slugify_name


class HrJob(models.Model):
    _inherit = "hr.job"

    x_open_for_applications = fields.Boolean(string="Open for Applications", default=False)

    def _x_180dc_slug(self):
        self.ensure_one()
        return slugify_name(self.name if isinstance(self.name, str) else self.name.get("en_US", "position"))

    def _x_180dc_public_catalog_payload(self):
        self.ensure_one()
        title = self.name if isinstance(self.name, str) else self.name.get("en_US", "Position")
        return {
            "slug": self._x_180dc_slug(),
            "title": title,
            "department": self.department_id.name or "180DC ESCP",
            "summary": html_to_plaintext(self.description or "") or title,
            "description": self.description or "",
        }

    def _x_180dc_public_opening_slug(self):
        self.ensure_one()
        title = self.name if isinstance(self.name, str) else self.name.get("en_US", "Position")
        department = self.department_id.name or "team"
        return slugify_name(f"{department}-{title}-{self.id}")

    def _x_180dc_is_publicly_open(self):
        self.ensure_one()
        return bool(self.active and self.x_open_for_applications)

    def _x_180dc_public_opening_payload(self):
        self.ensure_one()
        title = self.name if isinstance(self.name, str) else self.name.get("en_US", "Position")
        return {
            "slug": self._x_180dc_public_opening_slug(),
            "jobId": self.id,
            "title": title,
            "department": self.department_id.name or "180DC ESCP",
            "summary": html_to_plaintext(self.description or "") or title,
            "description": self.description or "",
            "locationLabel": "Multi-campus",
            "status": "open" if self._x_180dc_is_publicly_open() else "closed",
            "acceptingApplications": self._x_180dc_is_publicly_open(),
        }
