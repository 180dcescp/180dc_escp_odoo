from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = "hr.contract"

    season_id = fields.Many2one("x_180dc.season", string="Season", tracking=True, index=True)
    x_valid_until_season_id = fields.Many2one("x_180dc.season", string="Valid Through Season", tracking=True, index=True)
    x_contract_sent_at = fields.Datetime(string="Contract Sent At", tracking=True)
    x_nda_acknowledged = fields.Boolean(string="NDA Acknowledged", tracking=True)
    x_statement_acknowledged = fields.Boolean(string="Statement of Commitment Acknowledged", tracking=True)
    x_is_project_staffable = fields.Boolean(
        string="Project Staffable",
        compute="_compute_x_is_project_staffable",
        store=True,
    )
    x_staffing_status = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("staffable", "Project Staffable"),
            ("summer_break", "Summer Break"),
        ],
        string="Project Staffing Status",
        default="not_applicable",
        tracking=True,
    )

    @api.depends("department_id", "job_id")
    def _compute_x_is_project_staffable(self):
        Rule = self.env["x_180dc.role_group_rule"].sudo()
        for contract in self:
            rule = Rule._x_180dc_rule_for_role(contract.department_id, contract.job_id)
            contract.x_is_project_staffable = bool(rule.x_project_staffable)

    @api.model
    def _x_180dc_membership_contract_type(self):
        return self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")

    def _x_180dc_is_membership_contract(self):
        membership_type = self._x_180dc_membership_contract_type()
        return self.filtered(lambda contract: contract.contract_type_id == membership_type)

    def _x_180dc_assign_season_vals(self, vals, current_contract=None):
        membership_type = self._x_180dc_membership_contract_type()
        contract_type_id = vals.get("contract_type_id") or (current_contract.contract_type_id.id if current_contract else False)
        if contract_type_id != membership_type.id:
            return

        season = False
        if vals.get("season_id"):
            season = self.env["x_180dc.season"].browse(vals["season_id"])
        elif current_contract and current_contract.season_id:
            season = current_contract.season_id
        elif vals.get("date_start"):
            season = self.env["x_180dc.season"]._x_180dc_season_for_date(vals["date_start"])
        else:
            season = self.env["x_180dc.season"]._x_180dc_current_season()

        if season:
            vals["season_id"] = season.id
            if not vals.get("date_start"):
                vals["date_start"] = current_contract.date_start if current_contract else season.date_start
            valid_until_season = self._x_180dc_valid_until_season(vals, season, current_contract=current_contract)
            vals["x_valid_until_season_id"] = valid_until_season.id
            if not vals.get("date_end"):
                vals["date_end"] = valid_until_season.date_end
            vals.setdefault("state", "open")
        self._x_180dc_assign_staffing_vals(vals, current_contract=current_contract)

    def _x_180dc_valid_until_season(self, vals, season, current_contract=None):
        if vals.get("x_valid_until_season_id"):
            return self.env["x_180dc.season"].browse(vals["x_valid_until_season_id"])
        if vals.get("date_end"):
            return self.env["x_180dc.season"]._x_180dc_season_for_date(vals["date_end"])
        if current_contract and current_contract.x_valid_until_season_id:
            return current_contract.x_valid_until_season_id
        start_date = fields.Date.to_date(vals.get("date_start") or season.date_start)
        if start_date > season.date_start:
            return self.env["x_180dc.season"]._x_180dc_next_season(season)
        return season

    def _x_180dc_current_membership_contract(self, employee):
        self.ensure_one()
        today = fields.Date.context_today(self)
        membership_type = self._x_180dc_membership_contract_type()
        return employee.contract_ids.filtered(
            lambda contract: contract.contract_type_id == membership_type
            and contract.state == "open"
            and contract.date_start
            and contract.date_start <= today
            and (not contract.date_end or contract.date_end >= today)
        )[:1]

    def _x_180dc_contract_cover_seasons(self, start_date):
        start_date = fields.Date.to_date(start_date)
        start_season = self.env["x_180dc.season"]._x_180dc_season_for_date(start_date)
        if start_date > start_season.date_start:
            return start_season, self.env["x_180dc.season"]._x_180dc_next_season(start_season)
        return start_season, start_season

    def _x_180dc_retrigger_membership_contract(self, values):
        self.ensure_one()
        if self.contract_type_id != self._x_180dc_membership_contract_type():
            raise ValidationError("Only membership contracts can be retriggered.")

        start_date = fields.Date.context_today(self)
        start_season, valid_until_season = self._x_180dc_contract_cover_seasons(start_date)
        close_date = start_date - timedelta(days=1)
        if self.date_start and close_date < self.date_start:
            close_date = self.date_start

        self.with_context(x_180dc_allow_direct_role_update=True).write(
            {
                "state": "close",
                "date_end": close_date,
                "x_valid_until_season_id": self.env["x_180dc.season"]._x_180dc_season_for_date(close_date).id,
            }
        )

        department = self.env["hr.department"].browse(values.get("department_id", self.department_id.id))
        job = self.env["hr.job"].browse(values.get("job_id", self.job_id.id))
        rule = self.env["x_180dc.role_group_rule"].sudo()._x_180dc_rule_for_role(department, job)
        is_project_staffable = bool(rule.x_project_staffable)

        new_vals = {
            "name": values.get("name") or f"{self.employee_id.name} Membership {start_season.name}",
            "employee_id": self.employee_id.id,
            "contract_type_id": self.contract_type_id.id,
            "department_id": values.get("department_id", self.department_id.id),
            "job_id": values.get("job_id", self.job_id.id),
            "x_work_location_id": values.get("x_work_location_id", self.x_work_location_id.id),
            "season_id": start_season.id,
            "x_valid_until_season_id": valid_until_season.id,
            "date_start": start_date,
            "date_end": valid_until_season.date_end,
            "state": "open",
            "x_staffing_status": values.get("x_staffing_status", "staffable" if is_project_staffable else "not_applicable"),
        }
        return self.create(new_vals)

    def _x_180dc_assign_staffing_vals(self, vals, current_contract=None):
        department = False
        if vals.get("department_id"):
            department = self.env["hr.department"].browse(vals["department_id"])
        elif current_contract:
            department = current_contract.department_id

        job = False
        if vals.get("job_id"):
            job = self.env["hr.job"].browse(vals["job_id"])
        elif current_contract:
            job = current_contract.job_id

        season = False
        if vals.get("season_id"):
            season = self.env["x_180dc.season"].browse(vals["season_id"])
        elif current_contract:
            season = current_contract.season_id

        rule = self.env["x_180dc.role_group_rule"].sudo()._x_180dc_rule_for_role(department, job)
        is_project_staffable = bool(rule.x_project_staffable)

        if not is_project_staffable:
            vals["x_staffing_status"] = "not_applicable"
            return

        current_status = vals.get("x_staffing_status")
        if current_status == "summer_break" and season and season.cycle != "summer":
            vals["x_staffing_status"] = "staffable"
            return

        if not current_status:
            vals["x_staffing_status"] = (
                current_contract.x_staffing_status
                if current_contract and current_contract.x_staffing_status in {"staffable", "summer_break"}
                else "staffable"
            )
        if season and season.cycle != "summer" and vals.get("x_staffing_status") == "summer_break":
            vals["x_staffing_status"] = "staffable"

    @api.constrains("contract_type_id", "season_id", "x_valid_until_season_id")
    def _check_membership_season(self):
        membership_type = self._x_180dc_membership_contract_type()
        for contract in self:
            if contract.contract_type_id == membership_type and not contract.season_id:
                raise ValidationError("Membership contracts must have a season.")
            if contract.contract_type_id == membership_type and not contract.x_valid_until_season_id:
                raise ValidationError("Membership contracts must define their validity horizon.")
            if (
                contract.contract_type_id == membership_type
                and contract.season_id
                and contract.x_valid_until_season_id
                and contract.x_valid_until_season_id.date_end < contract.season_id.date_start
            ):
                raise ValidationError("Valid-through season cannot end before the start season.")

    @api.constrains("x_staffing_status", "season_id", "x_is_project_staffable")
    def _check_staffing_status(self):
        for contract in self:
            if not contract.x_is_project_staffable and contract.x_staffing_status != "not_applicable":
                raise ValidationError("Only project-staffable members can have a staffing status.")
            if contract.x_staffing_status == "summer_break" and contract.season_id.cycle != "summer":
                raise ValidationError("Summer break can only be selected on summer contracts.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._x_180dc_assign_season_vals(vals)
        contracts = super().create(vals_list)
        contracts.mapped("employee_id")._x_180dc_sync_membership_state()
        return contracts

    def write(self, vals):
        sync_employees = self.mapped("employee_id")
        today = fields.Date.context_today(self)
        role_change_fields = {"department_id", "job_id", "x_work_location_id"}
        if role_change_fields & set(vals) and not self.env.context.get("x_180dc_allow_direct_role_update"):
            membership_contracts = self._x_180dc_is_membership_contract().filtered(
                lambda contract: contract.state == "open"
                and contract.date_start
                and contract.date_start <= today
                and (not contract.date_end or contract.date_end >= today)
            )
            if membership_contracts:
                for contract in membership_contracts:
                    successor_vals = {
                        "department_id": vals.get("department_id", contract.department_id.id),
                        "job_id": vals.get("job_id", contract.job_id.id),
                        "x_work_location_id": vals.get("x_work_location_id", contract.x_work_location_id.id),
                        "x_staffing_status": vals.get("x_staffing_status", contract.x_staffing_status),
                    }
                    contract._x_180dc_retrigger_membership_contract(successor_vals)
                sync_employees._x_180dc_sync_membership_state()
                return True
        if {"season_id", "contract_type_id", "date_start", "department_id", "job_id", "x_staffing_status"} & set(vals):
            for contract in self:
                contract_vals = dict(vals)
                self._x_180dc_assign_season_vals(contract_vals, current_contract=contract)
                super(HrContract, contract).write(contract_vals)
            sync_employees._x_180dc_sync_membership_state()
            return True

        res = super().write(vals)
        if {"state", "employee_id", "active", "date_end", "department_id", "job_id", "x_valid_until_season_id"} & set(vals):
            (sync_employees | self.mapped("employee_id"))._x_180dc_sync_membership_state()
        return res

    def action_mark_contract_sent(self):
        self.write({"x_contract_sent_at": fields.Datetime.now()})

    def unlink(self):
        employees = self.mapped("employee_id")
        res = super().unlink()
        employees._x_180dc_sync_membership_state()
        return res

    def _x_180dc_backfill_membership_seasons(self):
        membership_type = self._x_180dc_membership_contract_type()
        current_season = self.env["x_180dc.season"]._x_180dc_current_season()
        contracts = self.filtered(
            lambda contract: contract.contract_type_id == membership_type and (not contract.season_id or not contract.x_valid_until_season_id)
        )
        for contract in contracts:
            if contract.season_id:
                season = contract.season_id
            elif contract.state == "open" and contract.employee_id.active:
                season = current_season
            else:
                season = self.env["x_180dc.season"]._x_180dc_season_for_date(contract.date_start or fields.Date.context_today(self))
            valid_until = self.env["x_180dc.season"]._x_180dc_season_for_date(contract.date_end or season.date_end)
            contract.write(
                {
                    "season_id": season.id,
                    "x_valid_until_season_id": valid_until.id,
                    "date_start": contract.date_start or season.date_start,
                    "date_end": contract.date_end or valid_until.date_end,
                }
            )
