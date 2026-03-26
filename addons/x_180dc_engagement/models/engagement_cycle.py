from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCEngagementCycle(models.Model):
    _name = "x_180dc.engagement.cycle"
    _description = "180DC Engagement Cycle"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    date_start_month = fields.Integer(required=True)
    date_start_day = fields.Integer(required=True)
    date_end_month = fields.Integer(required=True)
    date_end_day = fields.Integer(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("x_180dc_engagement_cycle_code_uniq", "unique(code)", "Cycle code must be unique."),
    ]

    @api.constrains("date_start_month", "date_start_day", "date_end_month", "date_end_day")
    def _check_date_parts(self):
        for record in self:
            try:
                start = date(2024, int(record.date_start_month), int(record.date_start_day))
                end = date(2024, int(record.date_end_month), int(record.date_end_day))
            except ValueError as error:
                raise ValidationError(f"Invalid cycle date parts: {error}") from error
            if end < start:
                raise ValidationError("Cycle end must be on or after cycle start within the reference year.")

    def _x_180dc_bounds_for_year(self, year):
        self.ensure_one()
        return (
            date(int(year), int(self.date_start_month), int(self.date_start_day)),
            date(int(year), int(self.date_end_month), int(self.date_end_day)),
        )

    @api.model
    def _x_180dc_cycle_for_date(self, target_date):
        target_date = fields.Date.to_date(target_date)
        for cycle in self.search([("active", "=", True)], order="sequence asc, id asc"):
            start, end = cycle._x_180dc_bounds_for_year(target_date.year)
            if start <= target_date <= end:
                return cycle
        return self.search([("active", "=", True)], order="sequence asc, id asc", limit=1)

    @api.model
    def _x_180dc_current_cycle(self):
        return self._x_180dc_cycle_for_date(fields.Date.context_today(self))

