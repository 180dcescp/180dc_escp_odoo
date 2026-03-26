from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCSeason(models.Model):
    _name = "x_180dc.season"
    _description = "180DC Season"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    year = fields.Integer(required=True, index=True)
    cycle_id = fields.Many2one("x_180dc.engagement.cycle", required=True, index=True, ondelete="restrict")
    cycle = fields.Char(
        string="Cycle Code",
        required=True,
        index=True,
        compute="_compute_cycle_code",
        inverse="_inverse_cycle_code",
        store=True,
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("x_180dc_season_code_uniq", "unique(code)", "Season code must be unique."),
    ]

    @api.constrains("date_start", "date_end")
    def _check_date_bounds(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("Season end date cannot be before its start date.")

    @api.model
    def _x_180dc_cycle_bounds(self, cycle, year):
        cycle_record = cycle if getattr(cycle, "_name", False) == "x_180dc.engagement.cycle" else False
        if cycle and not cycle_record:
            cycle_record = self.env["x_180dc.engagement.cycle"].sudo().search([("code", "=", cycle)], limit=1)
        if cycle_record:
            return cycle_record._x_180dc_bounds_for_year(year)
        return date(year, 1, 1), date(year, 12, 31)

    @api.depends("cycle_id.code")
    def _compute_cycle_code(self):
        for record in self:
            record.cycle = record.cycle_id.code if record.cycle_id else False

    def _inverse_cycle_code(self):
        Cycle = self.env["x_180dc.engagement.cycle"].sudo()
        for record in self:
            cycle = Cycle.search([("code", "=", record.cycle)], limit=1)
            if cycle:
                record.cycle_id = cycle

    @api.model
    def _x_180dc_cycle_for_date(self, target_date):
        cycle = self.env["x_180dc.engagement.cycle"].sudo()._x_180dc_cycle_for_date(target_date)
        return cycle.code if cycle else False

    @classmethod
    def _x_180dc_code_for(cls, cycle, year):
        code = cycle.code if getattr(cycle, "code", False) else cycle
        return f"{code}_{year}"

    @api.model
    def _x_180dc_build_vals(self, cycle, year):
        start, end = self._x_180dc_cycle_bounds(cycle, year)
        cycle_record = cycle if getattr(cycle, "_name", False) == "x_180dc.engagement.cycle" else False
        if cycle and not cycle_record:
            cycle_record = self.env["x_180dc.engagement.cycle"].sudo().search([("code", "=", cycle)], limit=1)
        return {
            "name": f"{(cycle_record.name if cycle_record else str(cycle).title())} {year}",
            "code": self._x_180dc_code_for(cycle, year),
            "year": year,
            "cycle_id": cycle_record.id if cycle_record else False,
            "date_start": start,
            "date_end": end,
            "active": True,
        }

    @api.model
    def _x_180dc_ensure_season(self, cycle, year):
        season = self.search([("code", "=", self._x_180dc_code_for(cycle, year))], limit=1)
        if season:
            return season
        return self.create(self._x_180dc_build_vals(cycle, year))

    @api.model
    def _x_180dc_season_for_date(self, target_date):
        target_date = fields.Date.to_date(target_date)
        season = self.search(
            [("date_start", "<=", target_date), ("date_end", ">=", target_date)],
            order="date_start desc, id desc",
            limit=1,
        )
        if season:
            return season
        return self._x_180dc_ensure_season(self._x_180dc_cycle_for_date(target_date), target_date.year)

    @api.model
    def _x_180dc_current_season(self):
        return self._x_180dc_season_for_date(fields.Date.context_today(self))

    @api.model
    def _x_180dc_next_season(self, season=None):
        season = season or self._x_180dc_current_season()
        cycle_order = self.env["x_180dc.engagement.cycle"].sudo().search([("active", "=", True)], order="sequence asc, id asc")
        cycle_codes = cycle_order.mapped("code")
        current_index = cycle_codes.index(season.cycle)
        next_index = (current_index + 1) % len(cycle_codes)
        next_year = season.year + (1 if next_index == 0 else 0)
        return self._x_180dc_ensure_season(cycle_order[next_index], next_year)

    @api.model
    def _x_180dc_seed_from_existing_data(self):
        season_keys = set()
        contracts = self.env["hr.contract"].sudo().search([])
        for contract in contracts:
            basis = fields.Date.to_date(contract.date_start) or fields.Date.context_today(self)
            season_keys.add((self._x_180dc_cycle_for_date(basis), basis.year))

        engagements = self.env["x_180dc.engagement"].sudo().search([])
        for engagement in engagements:
            if engagement.cycle and engagement.cycle_year:
                season_keys.add((engagement.cycle, int(engagement.cycle_year)))
            elif engagement.date_start:
                basis = fields.Date.to_date(engagement.date_start)
                season_keys.add((self._x_180dc_cycle_for_date(basis), basis.year))

        today = fields.Date.context_today(self)
        for year in range(today.year - 1, today.year + 2):
            for cycle in self.env["x_180dc.engagement.cycle"].sudo().search([("active", "=", True)], order="sequence asc, id asc"):
                season_keys.add((cycle.code, year))

        for cycle, year in sorted(season_keys):
            self._x_180dc_ensure_season(cycle, year)

    @api.model
    def _x_180dc_backfill_cycle_links(self):
        Cycle = self.env["x_180dc.engagement.cycle"].sudo()
        for season in self.sudo().search([]):
            if season.cycle_id:
                continue
            cycle = Cycle.search([("code", "=", season.cycle)], limit=1)
            if cycle:
                season.write({"cycle_id": cycle.id})

    def write(self, vals):
        res = super().write(vals)
        if {"date_start", "date_end", "cycle", "year", "active"} & set(vals):
            self.env["hr.employee"].search([])._x_180dc_sync_membership_state()
        return res
