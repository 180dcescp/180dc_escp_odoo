from odoo import api, fields, models


class X180DCRoleGroupRule(models.Model):
    _name = "x_180dc.role_group_rule"
    _description = "180DC Role Permission Rule"
    _order = "department_id, job_id, id"
    _rec_name = "display_name"

    active = fields.Boolean(default=True)
    department_id = fields.Many2one("hr.department", required=True, ondelete="cascade")
    job_id = fields.Many2one("hr.job", required=True, ondelete="cascade")
    group_ids = fields.Many2many(
        "res.groups",
        "x_180dc_role_group_rule_res_groups_rel",
        "rule_id",
        "group_id",
        string="Business Groups",
    )
    x_project_staffable = fields.Boolean(string="Project Staffable")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _sql_constraints = [
        (
            "x_180dc_role_group_rule_department_job_uniq",
            "unique(department_id, job_id)",
            "Only one permission rule is allowed per department and job combination.",
        ),
    ]

    @api.depends("department_id.name", "job_id.name")
    def _compute_display_name(self):
        for rule in self:
            department = rule.department_id.name or "Department"
            job = rule.job_id.name or "Job"
            rule.display_name = f"{department} / {job}"

    @api.model
    def _x_180dc_default_rule_specs(self):
        return [
            {
                "department": "Presidency",
                "job": "President",
                "groups": ["x_180dc_operating_model.group_180dc_presidency"],
            },
            {
                "department": "Presidency",
                "job": "Vice-President",
                "groups": ["x_180dc_operating_model.group_180dc_presidency"],
            },
            {
                "department": "People & Organisation",
                "job": "Head of",
                "groups": [
                    "x_180dc_operating_model.group_180dc_people_org_head",
                    "x_180dc_operating_model.group_180dc_business_development_associate_director",
                    "x_180dc_operating_model.group_180dc_marketing_associate_director",
                    "x_180dc_operating_model.group_180dc_finance_associate_director",
                ],
            },
            {
                "department": "People & Organisation",
                "job": "Associate Director",
                "groups": ["x_180dc_operating_model.group_180dc_people_org_associate_director"],
            },
            {
                "department": "Business Development",
                "job": "Head of",
                "groups": [
                    "x_180dc_operating_model.group_180dc_business_development_head",
                    "x_180dc_operating_model.group_180dc_people_org_associate_director",
                    "x_180dc_operating_model.group_180dc_marketing_associate_director",
                    "x_180dc_operating_model.group_180dc_finance_associate_director",
                ],
            },
            {
                "department": "Business Development",
                "job": "Associate Director",
                "groups": ["x_180dc_operating_model.group_180dc_business_development_associate_director"],
            },
            {
                "department": "Marketing",
                "job": "Head of",
                "groups": [
                    "x_180dc_operating_model.group_180dc_marketing_head",
                    "x_180dc_operating_model.group_180dc_people_org_associate_director",
                    "x_180dc_operating_model.group_180dc_business_development_associate_director",
                    "x_180dc_operating_model.group_180dc_finance_associate_director",
                ],
            },
            {
                "department": "Marketing",
                "job": "Associate Director",
                "groups": ["x_180dc_operating_model.group_180dc_marketing_associate_director"],
            },
            {
                "department": "Finance",
                "job": "Head of",
                "groups": [
                    "x_180dc_operating_model.group_180dc_finance_head",
                    "x_180dc_operating_model.group_180dc_people_org_associate_director",
                    "x_180dc_operating_model.group_180dc_business_development_associate_director",
                    "x_180dc_operating_model.group_180dc_marketing_associate_director",
                ],
            },
            {
                "department": "Finance",
                "job": "Associate Director",
                "groups": ["x_180dc_operating_model.group_180dc_finance_associate_director"],
            },
            {
                "department": "Operations",
                "job": "Associate Director",
                "groups": [],
            },
            {
                "department": "Consulting",
                "job": "Head of",
                "groups": [
                    "x_180dc_operating_model.group_180dc_consulting_head",
                    "x_180dc_operating_model.group_180dc_people_org_associate_director",
                    "x_180dc_operating_model.group_180dc_business_development_associate_director",
                    "x_180dc_operating_model.group_180dc_marketing_associate_director",
                    "x_180dc_operating_model.group_180dc_finance_associate_director",
                ],
            },
            {
                "department": "Consulting",
                "job": "Associate Director",
                "groups": ["x_180dc_operating_model.group_180dc_consulting_associate_director"],
            },
            {
                "department": "Consulting",
                "job": "Project Leader",
                "groups": ["x_180dc_operating_model.group_180dc_consulting_project_leader"],
                "project_staffable": True,
            },
            {
                "department": "Consultants",
                "job": "Project Leader",
                "groups": ["x_180dc_operating_model.group_180dc_consulting_project_leader"],
                "project_staffable": True,
            },
            {
                "department": "Consulting",
                "job": "Consultant",
                "groups": ["x_180dc_operating_model.group_180dc_consultant"],
            },
            {
                "department": "Consultants",
                "job": "Consultant",
                "groups": ["x_180dc_operating_model.group_180dc_consultant"],
                "project_staffable": True,
            },
            {
                "department": "Consulting",
                "job": "Senior Consultant",
                "groups": ["x_180dc_operating_model.group_180dc_consultant"],
            },
            {
                "department": "Consultants",
                "job": "Senior Consultant",
                "groups": ["x_180dc_operating_model.group_180dc_consultant"],
                "project_staffable": True,
            },
        ]

    @api.model
    def _x_180dc_seed_default_rules(self):
        Department = self.env["hr.department"].sudo()
        Job = self.env["hr.job"].sudo()
        Rules = self.sudo()

        for spec in self._x_180dc_default_rule_specs():
            department = Department.search([("name", "=", spec["department"])], limit=1)
            job = Job.search([("name", "=", spec["job"])], limit=1)
            if not department or not job:
                continue

            groups = [
                self.env.ref(xmlid, raise_if_not_found=False)
                for xmlid in spec["groups"]
            ]
            group_ids = [group.id for group in groups if group]

            rule = Rules.search(
                [("department_id", "=", department.id), ("job_id", "=", job.id)],
                limit=1,
            )
            vals = {
                "department_id": department.id,
                "job_id": job.id,
                "group_ids": [(6, 0, group_ids)],
                "x_project_staffable": bool(spec.get("project_staffable")),
                "active": True,
            }
            if rule:
                rule.write(vals)
            else:
                Rules.create(vals)

    @api.model
    def _x_180dc_rule_for_role(self, department, job):
        if not department or not job:
            return self.browse()
        return self.sudo().search(
            [("department_id", "=", department.id), ("job_id", "=", job.id), ("active", "=", True)],
            limit=1,
        )
