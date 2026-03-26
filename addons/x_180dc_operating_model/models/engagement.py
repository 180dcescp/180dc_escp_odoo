from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCEngagement(models.Model):
    _inherit = "x_180dc.engagement"

    x_consulting_reviewer_id = fields.Many2one(
        "hr.employee",
        string="Consulting Reviewer",
        tracking=True,
        ondelete="restrict",
    )
    x_available_consulting_reviewer_ids = fields.Many2many(
        "hr.employee",
        compute="_compute_available_consulting_reviewers",
        string="Available Consulting Reviewers",
    )

    @api.depends("member_ids")
    def _compute_available_consulting_reviewers(self):
        reviewers = self._x_180dc_current_consulting_members()
        for engagement in self:
            engagement.x_available_consulting_reviewer_ids = reviewers

    def _x_180dc_employee_matches_reviewer_policy(self, employee, pool_scope=None):
        contract = employee.current_membership_contract_id
        if not contract:
            return False
        policies = self.env["x_180dc.consulting_reviewer_policy"].sudo()._x_180dc_active_policies(pool_scope=pool_scope)
        return any(policy._x_180dc_matches_contract(contract) for policy in policies)

    def _x_180dc_ranked_reviewers(self, employees, pool_scope):
        policies = self.env["x_180dc.consulting_reviewer_policy"].sudo()._x_180dc_active_policies(pool_scope=pool_scope)
        ranked = []
        seen_ids = set()
        for policy in policies:
            matching_employees = employees.filtered(
                lambda employee: employee.id not in seen_ids
                and policy._x_180dc_matches_contract(employee.current_membership_contract_id)
            )
            for employee in matching_employees.sorted(key=lambda candidate: candidate.id):
                ranked.append(employee)
                seen_ids.add(employee.id)
        return self.env["hr.employee"].browse([employee.id for employee in ranked])

    def _x_180dc_current_consulting_members(self):
        employees = self.env["hr.employee"].search([("active", "=", True)])
        return employees.filtered(lambda employee: self._x_180dc_employee_matches_reviewer_policy(employee))

    def _x_180dc_default_consulting_reviewer(self):
        reviewers = self._x_180dc_ranked_reviewers(
            self.env["hr.employee"].search([("active", "=", True)]),
            pool_scope="global",
        )
        return reviewers[:1]

    def _x_180dc_pick_consulting_reviewer(self):
        self.ensure_one()
        if self.x_consulting_reviewer_id and self._x_180dc_is_valid_consulting_reviewer(self.x_consulting_reviewer_id):
            return self.x_consulting_reviewer_id
        engagement_member_reviewers = self._x_180dc_ranked_reviewers(
            self.member_ids.filtered(lambda employee: employee.active),
            pool_scope="engagement_members",
        )
        if engagement_member_reviewers:
            return engagement_member_reviewers[0]
        return self._x_180dc_default_consulting_reviewer()

    def _x_180dc_is_valid_consulting_reviewer(self, employee):
        self.ensure_one()
        if not employee or not employee.active:
            return False
        if employee in self.member_ids and self._x_180dc_employee_matches_reviewer_policy(
            employee, pool_scope="engagement_members"
        ):
            return True
        return self._x_180dc_employee_matches_reviewer_policy(employee, pool_scope="global")

    @api.constrains("x_consulting_reviewer_id")
    def _check_consulting_reviewer(self):
        for engagement in self:
            if not engagement.active:
                continue
            if not engagement.x_consulting_reviewer_id:
                raise ValidationError("Every active engagement must have a Consulting reviewer assigned.")
            if not engagement._x_180dc_is_valid_consulting_reviewer(engagement.x_consulting_reviewer_id):
                raise ValidationError("The Consulting reviewer must satisfy the configured reviewer policy.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("x_consulting_reviewer_id"):
                default_reviewer = self._x_180dc_default_consulting_reviewer()
                if default_reviewer:
                    vals["x_consulting_reviewer_id"] = default_reviewer.id
        return super().create(vals_list)

    def write(self, vals):
        needs_per_record_write = bool("x_consulting_reviewer_id" in vals)
        if not needs_per_record_write and any(not engagement.x_consulting_reviewer_id for engagement in self):
            needs_per_record_write = True

        if needs_per_record_write:
            for engagement in self:
                engagement_vals = dict(vals)
                if not engagement_vals.get("x_consulting_reviewer_id"):
                    fallback = engagement._x_180dc_pick_consulting_reviewer()
                    if fallback:
                        engagement_vals["x_consulting_reviewer_id"] = fallback.id
                super(X180DCEngagement, engagement).write(engagement_vals)
            return True
        return super().write(vals)

    def _x_180dc_backfill_consulting_reviewers(self):
        for engagement in self:
            reviewer = engagement._x_180dc_pick_consulting_reviewer()
            if reviewer and engagement.x_consulting_reviewer_id != reviewer:
                engagement.with_context(mail_create_nolog=True, tracking_disable=True).write(
                    {"x_consulting_reviewer_id": reviewer.id}
                )
