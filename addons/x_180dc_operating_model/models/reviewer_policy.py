from odoo import api, fields, models


class X180DCConsultingReviewerPolicy(models.Model):
    _name = "x_180dc.consulting_reviewer_policy"
    _description = "180DC Consulting Reviewer Policy"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "pool_scope, priority, id"

    active = fields.Boolean(default=True)
    rule_key = fields.Char(required=True)
    name = fields.Char(required=True)
    pool_scope = fields.Selection(
        [
            ("engagement_members", "Engagement Members"),
            ("global", "Global Fallback"),
        ],
        required=True,
        default="global",
    )
    priority = fields.Integer(default=10, required=True)
    department_ids = fields.Many2many(
        "hr.department",
        "x_180dc_consulting_reviewer_policy_department_rel",
        "policy_id",
        "department_id",
        string="Eligible Departments",
    )
    job_ids = fields.Many2many(
        "hr.job",
        "x_180dc_consulting_reviewer_policy_job_rel",
        "policy_id",
        "job_id",
        string="Eligible Jobs",
    )

    _sql_constraints = [
        (
            "x_180dc_consulting_reviewer_policy_key_uniq",
            "unique(rule_key)",
            "Consulting reviewer policy keys must be unique.",
        ),
    ]

    def _x_180dc_matches_contract(self, contract):
        self.ensure_one()
        if not contract:
            return False
        if self.department_ids and contract.department_id not in self.department_ids:
            return False
        if self.job_ids and contract.job_id not in self.job_ids:
            return False
        return True

    @api.model
    def _x_180dc_active_policies(self, pool_scope=None):
        domain = [("active", "=", True)]
        if pool_scope:
            domain.append(("pool_scope", "=", pool_scope))
        return self.sudo().search(domain, order="pool_scope, priority, id")

    @api.model
    def _x_180dc_default_policy_specs(self):
        return [
            {
                "rule_key": "engagement_member_head_of",
                "name": "Engagement member Head of reviewer",
                "pool_scope": "engagement_members",
                "priority": 0,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Head of"],
            },
            {
                "rule_key": "engagement_member_associate_director",
                "name": "Engagement member Associate Director reviewer",
                "pool_scope": "engagement_members",
                "priority": 1,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Associate Director"],
            },
            {
                "rule_key": "engagement_member_project_leader",
                "name": "Engagement member Project Leader reviewer",
                "pool_scope": "engagement_members",
                "priority": 2,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Project Leader"],
            },
            {
                "rule_key": "global_head_of",
                "name": "Global Head of reviewer fallback",
                "pool_scope": "global",
                "priority": 0,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Head of"],
            },
            {
                "rule_key": "global_associate_director",
                "name": "Global Associate Director reviewer fallback",
                "pool_scope": "global",
                "priority": 1,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Associate Director"],
            },
            {
                "rule_key": "global_project_leader",
                "name": "Global Project Leader reviewer fallback",
                "pool_scope": "global",
                "priority": 2,
                "departments": ["Consulting", "Consultants"],
                "jobs": ["Project Leader"],
            },
        ]

    @api.model
    def _x_180dc_seed_default_policies(self):
        Department = self.env["hr.department"].sudo()
        Job = self.env["hr.job"].sudo()
        Policies = self.sudo()

        for spec in self._x_180dc_default_policy_specs():
            departments = Department.search([("name", "in", spec.get("departments", []))])
            jobs = Job.search([("name", "in", spec.get("jobs", []))])
            vals = {
                "rule_key": spec["rule_key"],
                "name": spec["name"],
                "pool_scope": spec["pool_scope"],
                "priority": spec["priority"],
                "department_ids": [(6, 0, departments.ids)],
                "job_ids": [(6, 0, jobs.ids)],
                "active": True,
            }
            policy = Policies.search([("rule_key", "=", spec["rule_key"])], limit=1)
            if policy:
                policy.write(vals)
            else:
                Policies.create(vals)
