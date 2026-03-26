from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCApprovalScope(models.Model):
    _name = "x_180dc.approval.scope"
    _description = "180DC Approval Scope"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "name, id"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    line_ids = fields.One2many("x_180dc.approval.scope.line", "scope_id", string="Approver Rules")

    _sql_constraints = [
        ("x_180dc_approval_scope_name_uniq", "unique(name)", "Approval scopes must be unique."),
    ]

    def _x_180dc_matches_approver(self, user, request):
        self.ensure_one()
        employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
        contract = employee.current_membership_contract_id
        if not contract:
            return False
        return any(line._x_180dc_matches_contract(contract, request) for line in self.line_ids.filtered("active"))

    @api.model
    def _x_180dc_default_scope_specs(self):
        return [
            {
                "name": "Presidency",
                "lines": [
                    {
                        "key": "presidency_president_vice_president",
                        "departments": ["Presidency"],
                        "jobs": ["President", "Vice-President"],
                    }
                ],
            },
            {
                "name": "Consulting or Presidency",
                "lines": [
                    {
                        "key": "consulting_or_presidency_president_vice_president",
                        "departments": ["Presidency"],
                        "jobs": ["President", "Vice-President"],
                    },
                    {
                        "key": "consulting_or_presidency_consulting_head",
                        "departments": ["Consulting"],
                        "jobs": ["Head of"],
                    },
                ],
            },
        ]

    @api.model
    def _x_180dc_seed_default_scopes(self):
        Department = self.env["hr.department"].sudo()
        Job = self.env["hr.job"].sudo()
        Line = self.env["x_180dc.approval.scope.line"].sudo()
        Scope = self.sudo()

        for spec in self._x_180dc_default_scope_specs():
            scope = Scope.search([("name", "=", spec["name"])], limit=1)
            if not scope:
                scope = Scope.create({"name": spec["name"], "active": True})
            else:
                scope.write({"active": True})

            for line_spec in spec["lines"]:
                departments = Department.search([("name", "in", line_spec.get("departments", []))])
                jobs = Job.search([("name", "in", line_spec.get("jobs", []))])
                vals = {
                    "scope_id": scope.id,
                    "rule_key": line_spec["key"],
                    "approver_department_ids": [(6, 0, departments.ids)],
                    "approver_job_ids": [(6, 0, jobs.ids)],
                    "match_requested_department": bool(line_spec.get("match_requested_department")),
                    "active": True,
                }
                line = Line.search([("rule_key", "=", line_spec["key"])], limit=1)
                if line:
                    line.write(vals)
                else:
                    Line.create(vals)


class X180DCApprovalScopeLine(models.Model):
    _name = "x_180dc.approval.scope.line"
    _description = "180DC Approval Scope Line"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "scope_id, id"
    _rec_name = "rule_key"

    active = fields.Boolean(default=True)
    scope_id = fields.Many2one("x_180dc.approval.scope", required=True, ondelete="cascade")
    rule_key = fields.Char(required=True)
    approver_department_ids = fields.Many2many(
        "hr.department",
        "x_180dc_approval_scope_line_department_rel",
        "line_id",
        "department_id",
        string="Approver Departments",
    )
    approver_job_ids = fields.Many2many(
        "hr.job",
        "x_180dc_approval_scope_line_job_rel",
        "line_id",
        "job_id",
        string="Approver Jobs",
    )
    match_requested_department = fields.Boolean(string="Approver Must Match Requested Department")

    _sql_constraints = [
        ("x_180dc_approval_scope_line_key_uniq", "unique(rule_key)", "Approval scope rule keys must be unique."),
    ]

    def _x_180dc_matches_contract(self, contract, request):
        self.ensure_one()
        if not contract:
            return False
        if self.approver_department_ids and contract.department_id not in self.approver_department_ids:
            return False
        if self.approver_job_ids and contract.job_id not in self.approver_job_ids:
            return False
        if self.match_requested_department and contract.department_id != request.requested_department_id:
            return False
        return True


class X180DCPromotionApprovalRule(models.Model):
    _name = "x_180dc.promotion_approval_rule"
    _description = "180DC Promotion Approval Rule"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "requested_job_id, requested_department_id, requested_work_location_id, id"

    active = fields.Boolean(default=True)
    rule_key = fields.Char(required=True)
    name = fields.Char(required=True)
    requested_job_id = fields.Many2one("hr.job", required=True, ondelete="cascade")
    requested_department_id = fields.Many2one("hr.department", ondelete="cascade")
    requested_work_location_id = fields.Many2one("hr.work.location", ondelete="cascade")
    approval_scope_id = fields.Many2one("x_180dc.approval.scope", required=True, ondelete="restrict")

    _sql_constraints = [
        (
            "x_180dc_promotion_approval_rule_key_uniq",
            "unique(rule_key)",
            "Promotion approval rule keys must be unique.",
        ),
    ]

    @api.model
    def _x_180dc_rule_specificity(self, rule):
        return int(bool(rule.requested_department_id)) + int(bool(rule.requested_work_location_id))

    @api.model
    def _x_180dc_rule_for_request(self, request):
        rules = self.sudo().search(
            [
                ("active", "=", True),
                ("requested_job_id", "=", request.requested_job_id.id),
                "|",
                ("requested_department_id", "=", False),
                ("requested_department_id", "=", request.requested_department_id.id),
                "|",
                ("requested_work_location_id", "=", False),
                ("requested_work_location_id", "=", request.requested_work_location_id.id),
            ]
        )
        if not rules:
            return self.browse()
        return rules.sorted(
            key=lambda rule: (self._x_180dc_rule_specificity(rule), rule.id),
            reverse=True,
        )[:1]

    @api.constrains("requested_job_id", "requested_department_id", "requested_work_location_id", "active")
    def _check_duplicate_scope(self):
        for rule in self.filtered("active"):
            duplicates = self.search(
                [
                    ("id", "!=", rule.id),
                    ("active", "=", True),
                    ("requested_job_id", "=", rule.requested_job_id.id),
                    ("requested_department_id", "=", rule.requested_department_id.id),
                    ("requested_work_location_id", "=", rule.requested_work_location_id.id),
                ],
                limit=1,
            )
            if duplicates:
                raise ValidationError("Only one active promotion approval rule is allowed per target role scope.")

    @api.model
    def _x_180dc_default_rule_scope_name(self, department_name, job_name):
        if job_name == "Head of":
            return "Presidency"
        if department_name in {"Consultants", "Consulting"} and job_name in {
            "Consultant",
            "Senior Consultant",
            "Project Leader",
            "Associate Director",
        }:
            return "Consulting or Presidency"
        return "Presidency"

    @api.model
    def _x_180dc_seed_default_rules(self):
        Job = self.env["hr.job"].sudo()
        Department = self.env["hr.department"].sudo()
        Scope = self.env["x_180dc.approval.scope"].sudo()
        Rules = self.sudo()

        all_departments = Department.search([])
        all_jobs = Job.search([])
        consulting_departments = all_departments.filtered(lambda department: department.name in {"Consulting", "Consultants"})
        target_jobs = {
            "Associate Director",
            "Project Leader",
            "Consultant",
            "Senior Consultant",
        }

        for job in all_jobs:
            generic_scope_name = self._x_180dc_default_rule_scope_name("", job.name or "")
            generic_scope = Scope.search([("name", "=", generic_scope_name)], limit=1)
            generic_rule_key = f"promotion_generic_{job.id}"
            generic_vals = {
                "rule_key": generic_rule_key,
                "name": f"{job.name} approval",
                "requested_job_id": job.id,
                "requested_department_id": False,
                "requested_work_location_id": False,
                "approval_scope_id": generic_scope.id,
                "active": True,
            }
            generic_rule = Rules.search([("rule_key", "=", generic_rule_key)], limit=1)
            if generic_rule:
                generic_rule.write(generic_vals)
            else:
                Rules.create(generic_vals)

            if (job.name or "") not in target_jobs:
                continue

            consulting_scope = Scope.search([("name", "=", "Consulting or Presidency")], limit=1)
            for department in consulting_departments:
                rule_key = f"promotion_{department.id}_{job.id}"
                vals = {
                    "rule_key": rule_key,
                    "name": f"{department.name} / {job.name} approval",
                    "requested_job_id": job.id,
                    "requested_department_id": department.id,
                    "requested_work_location_id": False,
                    "approval_scope_id": consulting_scope.id,
                    "active": True,
                }
                specific_rule = Rules.search([("rule_key", "=", rule_key)], limit=1)
                if specific_rule:
                    specific_rule.write(vals)
                else:
                    Rules.create(vals)
