from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    current_membership_contract_id = fields.Many2one(
        "hr.contract",
        compute="_compute_current_membership_contract",
        store=False,
    )
    current_season_id = fields.Many2one(
        "x_180dc.season",
        compute="_compute_current_membership_contract",
        store=False,
    )
    is_current_member = fields.Boolean(
        compute="_compute_current_membership_contract",
        store=False,
    )

    @api.model
    def _x_180dc_operating_policy(self):
        return self.env["x_180dc.operating_policy"].sudo()._x_180dc_get_policy()

    @api.depends("contract_ids.state", "contract_ids.season_id", "contract_ids.contract_type_id", "contract_ids.date_start", "contract_ids.date_end")
    def _compute_current_membership_contract(self):
        membership_type = self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")
        current_season = self.env["x_180dc.season"]._x_180dc_current_season()
        today = fields.Date.context_today(self)
        for employee in self:
            contract = self.env["hr.contract"].search(
                [
                    ("employee_id", "=", employee.id),
                    ("contract_type_id", "=", membership_type.id),
                    ("state", "=", "open"),
                    ("date_start", "<=", today),
                    "|",
                    ("date_end", "=", False),
                    ("date_end", ">=", today),
                ],
                order="date_start desc, id desc",
                limit=1,
            )
            employee.current_membership_contract_id = contract
            employee.current_season_id = current_season
            employee.is_current_member = bool(contract)

    def _x_180dc_user_login(self):
        self.ensure_one()
        email = (self.work_email or "").strip().lower()
        return email if self._x_180dc_operating_policy()._x_180dc_email_domain_allowed(email) else False

    def _x_180dc_user_create_vals(self):
        self.ensure_one()
        login = self._x_180dc_user_login()
        if not login:
            return {}
        return {
            "name": self.name or login,
            "login": login,
            "email": login,
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            "share": False,
        }

    def _x_180dc_ensure_linked_user(self):
        Users = (
            self.env["res.users"]
            .with_user(SUPERUSER_ID)
            .sudo()
            .with_context(
                no_reset_password=True,
                x_180dc_allow_user_create=True,
            )
        )
        Employee = self.with_user(SUPERUSER_ID).sudo()

        for employee in Employee:
            login = employee._x_180dc_user_login()
            if not login:
                continue

            if employee.user_id:
                vals = {}
                if employee.user_id.login != login:
                    vals["login"] = login
                if employee.user_id.email != login:
                    vals["email"] = login
                if employee.name and employee.user_id.name != employee.name:
                    vals["name"] = employee.name
                if employee.user_id.share:
                    vals["share"] = False
                if vals:
                    employee.user_id.write(vals)
                user = employee.user_id
            else:
                user = Users.search([("login", "=", login)], limit=1)
                if user:
                    other_employee = Employee.search(
                        [("user_id", "=", user.id), ("id", "!=", employee.id)],
                        limit=1,
                    )
                    if other_employee:
                        continue
                else:
                    user = Users.create(employee._x_180dc_user_create_vals())
                    if user.active:
                        user.write({"active": False})
                employee.with_context(x_180dc_skip_user_link=True).write(
                    {"user_id": user.id}
                )

            if employee.current_membership_contract_id:
                employee._x_180dc_sync_user_groups(
                    user, employee.current_membership_contract_id
                )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        employees._x_180dc_ensure_linked_user()
        return employees

    def _x_180dc_groups_for_contract(self, contract):
        rule = (
            self.env["x_180dc.role_group_rule"]
            .sudo()
            .search(
                [
                    ("active", "=", True),
                    ("department_id", "=", contract.department_id.id),
                    ("job_id", "=", contract.job_id.id),
                ],
                limit=1,
            )
        )
        if rule:
            return rule.group_ids.ids or [self.env.ref("base.group_user").id]
        return [self.env.ref("base.group_user").id]

    def _x_180dc_groups_for_alumnus(self):
        return [self.env.ref("base.group_user").id]

    def _x_180dc_sync_user_groups(self, user, contract):
        manual_group_ids = set(user.x_manual_business_group_ids.ids)
        wanted_group_ids = set(self._x_180dc_groups_for_contract(contract) if contract else [])
        wanted_group_ids |= manual_group_ids
        if set(user.groups_id.ids) != set(wanted_group_ids):
            user.write({"groups_id": [(6, 0, sorted(wanted_group_ids))]})

    def _x_180dc_sync_membership_state(self):
        membership_type = self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")
        today = fields.Date.context_today(self)
        alumni_cooldown_months = self._x_180dc_operating_policy().alumni_cooldown_months

        for employee in self.with_user(SUPERUSER_ID).sudo():
            contract = self.env["hr.contract"].sudo().search(
                [
                    ("employee_id", "=", employee.id),
                    ("contract_type_id", "=", membership_type.id),
                    ("state", "=", "open"),
                    ("date_start", "<=", today),
                    "|",
                    ("date_end", "=", False),
                    ("date_end", ">=", today),
                ],
                order="date_start desc, id desc",
                limit=1,
            )
            latest_membership = self.env["hr.contract"].sudo().search(
                [
                    ("employee_id", "=", employee.id),
                    ("contract_type_id", "=", membership_type.id),
                    ("date_end", "!=", False),
                ],
                order="date_end desc, id desc",
                limit=1,
            )
            in_alumni_cooldown = bool(
                not contract
                and latest_membership
                and latest_membership.date_end
                and latest_membership.date_end >= today - relativedelta(months=alumni_cooldown_months)
            )

            employee_should_be_active = bool(contract)
            # Keep user lifecycle decoupled from employee lifecycle: current members
            # can exist without an active user until they actually log in.
            user_should_be_active = bool(employee.user_id and employee.user_id.active)
            if not contract and not in_alumni_cooldown:
                user_should_be_active = False

            if employee.active != employee_should_be_active:
                employee.active = employee_should_be_active
            if employee.user_id:
                if employee.user_id.active != user_should_be_active:
                    employee.user_id.active = user_should_be_active
                if contract:
                    self._x_180dc_sync_user_groups(employee.user_id, contract)
                elif in_alumni_cooldown:
                    employee.user_id.write({"groups_id": [(6, 0, self._x_180dc_groups_for_alumnus())]})
                elif employee.user_id.groups_id:
                    self._x_180dc_sync_user_groups(employee.user_id, False)

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get("x_180dc_skip_user_link")
            and {"work_email", "name"} & set(vals)
        ):
            self._x_180dc_ensure_linked_user()
        if {"user_id", "active"} & set(vals):
            self._x_180dc_sync_membership_state()
        return res

    @api.model
    def _x_180dc_cron_sync_membership_state(self):
        self.search([])._x_180dc_sync_membership_state()

    @api.model
    def _x_180dc_backfill_linked_users(self):
        self.search([])._x_180dc_ensure_linked_user()
