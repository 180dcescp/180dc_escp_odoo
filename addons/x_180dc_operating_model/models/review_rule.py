from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCReviewRule(models.Model):
    _name = "x_180dc.review.rule"
    _description = "180DC Review Rule"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "template_id, id"
    _rec_name = "display_name"

    active = fields.Boolean(default=True)
    rule_key = fields.Char(required=True)
    template_id = fields.Many2one("x_180dc.review.template", required=True, ondelete="cascade")
    subject_job_ids = fields.Many2many(
        "hr.job",
        "x_180dc_review_rule_subject_job_rel",
        "rule_id",
        "job_id",
        string="Allowed Subject Jobs",
    )
    subject_department_ids = fields.Many2many(
        "hr.department",
        "x_180dc_review_rule_subject_department_rel",
        "rule_id",
        "department_id",
        string="Allowed Subject Departments",
    )
    reviewer_job_ids = fields.Many2many(
        "hr.job",
        "x_180dc_review_rule_reviewer_job_rel",
        "rule_id",
        "job_id",
        string="Allowed Reviewer Jobs",
    )
    reviewer_department_ids = fields.Many2many(
        "hr.department",
        "x_180dc_review_rule_reviewer_department_rel",
        "rule_id",
        "department_id",
        string="Allowed Reviewer Departments",
    )
    reviewer_same_department = fields.Boolean(string="Reviewer Must Match Subject Department")
    requires_engagement = fields.Boolean()
    subject_must_belong_to_engagement = fields.Boolean()
    reviewer_must_belong_to_engagement = fields.Boolean()
    reviewer_must_match_engagement_consulting_reviewer = fields.Boolean()
    self_review_only = fields.Boolean()
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _sql_constraints = [
        ("x_180dc_review_rule_key_uniq", "unique(rule_key)", "Review rule keys must be unique."),
    ]

    @api.depends("template_id.name", "rule_key")
    def _compute_display_name(self):
        for rule in self:
            label = rule.template_id.name or "Review Rule"
            rule.display_name = f"{label}: {rule.rule_key}" if rule.rule_key else label

    def _x_180dc_contract_matches_scope(self, contract, job_ids, department_ids):
        if not job_ids and not department_ids:
            return True
        if not contract:
            return False
        if job_ids and contract.job_id not in job_ids:
            return False
        if department_ids and contract.department_id not in department_ids:
            return False
        return True

    def _x_180dc_validate_assignment(self, assignment):
        self.ensure_one()
        subject_contract = assignment.subject_employee_id.current_membership_contract_id
        reviewer_contract = assignment.reviewer_employee_id.current_membership_contract_id

        if self.self_review_only and assignment.subject_employee_id != assignment.reviewer_employee_id:
            raise ValidationError("This review must be self-submitted.")

        if not self._x_180dc_contract_matches_scope(
            subject_contract,
            self.subject_job_ids,
            self.subject_department_ids,
        ):
            raise ValidationError("The selected subject does not match the configured review rule.")

        if not self._x_180dc_contract_matches_scope(
            reviewer_contract,
            self.reviewer_job_ids,
            self.reviewer_department_ids,
        ):
            raise ValidationError("The selected reviewer does not match the configured review rule.")

        if self.reviewer_same_department:
            subject_department = subject_contract.department_id if subject_contract else self.env["hr.department"]
            reviewer_department = reviewer_contract.department_id if reviewer_contract else self.env["hr.department"]
            if not subject_department or not reviewer_department or subject_department != reviewer_department:
                raise ValidationError("The reviewer must belong to the same department as the subject.")

        if self.requires_engagement and not assignment.engagement_id:
            raise ValidationError("This review requires an engagement.")
        if (
            self.subject_must_belong_to_engagement
            and (not assignment.engagement_id or assignment.subject_employee_id not in assignment.engagement_id.member_ids)
        ):
            raise ValidationError("The review subject must belong to the selected engagement.")
        if (
            self.reviewer_must_belong_to_engagement
            and (not assignment.engagement_id or assignment.reviewer_employee_id not in assignment.engagement_id.member_ids)
        ):
            raise ValidationError("The reviewer must belong to the selected engagement.")
        if (
            self.reviewer_must_match_engagement_consulting_reviewer
            and (
                not assignment.engagement_id
                or assignment.reviewer_employee_id != assignment.engagement_id.x_consulting_reviewer_id
            )
        ):
            raise ValidationError("The reviewer must match the engagement's Consulting reviewer.")

    @api.model
    def _x_180dc_default_rule_specs(self):
        return [
            {
                "rule_key": "overall_experience_associate_director_self",
                "template_scope": "overall_experience",
                "subject_jobs": ["Associate Director"],
                "self_review_only": True,
            },
            {
                "rule_key": "overall_experience_consultant_self",
                "template_scope": "overall_experience",
                "subject_jobs": ["Consultant", "Senior Consultant"],
                "subject_departments": ["Consultants"],
                "self_review_only": True,
            },
            {
                "rule_key": "executive_same_department_head",
                "template_scope": "executive",
                "subject_jobs": ["Associate Director"],
                "reviewer_jobs": ["Head of"],
                "reviewer_same_department": True,
            },
            {
                "rule_key": "project_leader_consulting_reviewer",
                "template_scope": "project_leader",
                "subject_jobs": ["Project Leader"],
                "reviewer_jobs": ["Head of", "Associate Director"],
                "reviewer_departments": ["Consulting"],
                "requires_engagement": True,
                "subject_must_belong_to_engagement": True,
                "reviewer_must_match_engagement_consulting_reviewer": True,
            },
            {
                "rule_key": "consultant_project_leader",
                "template_scope": "consultant",
                "subject_jobs": ["Consultant", "Senior Consultant"],
                "subject_departments": ["Consultants"],
                "reviewer_jobs": ["Project Leader"],
                "requires_engagement": True,
                "subject_must_belong_to_engagement": True,
                "reviewer_must_belong_to_engagement": True,
            },
        ]

    @api.model
    def _x_180dc_seed_default_rules(self):
        Template = self.env["x_180dc.review.template"].sudo()
        Job = self.env["hr.job"].sudo()
        Department = self.env["hr.department"].sudo()
        Rules = self.sudo()

        for spec in self._x_180dc_default_rule_specs():
            template = Template.search([("review_scope", "=", spec["template_scope"])], limit=1)
            if not template:
                continue

            subject_jobs = Job.search([("name", "in", spec.get("subject_jobs", []))])
            reviewer_jobs = Job.search([("name", "in", spec.get("reviewer_jobs", []))])
            subject_departments = Department.search([("name", "in", spec.get("subject_departments", []))])
            reviewer_departments = Department.search([("name", "in", spec.get("reviewer_departments", []))])

            vals = {
                "rule_key": spec["rule_key"],
                "template_id": template.id,
                "subject_job_ids": [(6, 0, subject_jobs.ids)],
                "subject_department_ids": [(6, 0, subject_departments.ids)],
                "reviewer_job_ids": [(6, 0, reviewer_jobs.ids)],
                "reviewer_department_ids": [(6, 0, reviewer_departments.ids)],
                "reviewer_same_department": bool(spec.get("reviewer_same_department")),
                "requires_engagement": bool(spec.get("requires_engagement")),
                "subject_must_belong_to_engagement": bool(spec.get("subject_must_belong_to_engagement")),
                "reviewer_must_belong_to_engagement": bool(spec.get("reviewer_must_belong_to_engagement")),
                "reviewer_must_match_engagement_consulting_reviewer": bool(
                    spec.get("reviewer_must_match_engagement_consulting_reviewer")
                ),
                "self_review_only": bool(spec.get("self_review_only")),
                "active": True,
            }

            rule = Rules.search([("rule_key", "=", spec["rule_key"])], limit=1)
            if rule:
                rule.write(vals)
            else:
                Rules.create(vals)
