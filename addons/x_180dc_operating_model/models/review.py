from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCReviewTemplate(models.Model):
    _name = "x_180dc.review.template"
    _description = "180DC Review Template"
    _order = "name"

    name = fields.Char(required=True)
    review_scope = fields.Selection(
        [
            ("overall_experience", "180 Overall Experience"),
            ("executive", "Associate Director"),
            ("project_leader", "Project Leader"),
            ("consultant", "Consultant / Senior Consultant"),
        ],
        required=True,
    )
    survey_id = fields.Many2one("survey.survey", required=True, ondelete="restrict")
    active = fields.Boolean(default=True)
    rule_ids = fields.One2many("x_180dc.review.rule", "template_id", string="Review Rules")

    @api.model
    def _x_180dc_ensure_default_templates(self):
        survey_by_key = {
            survey.x_180dc_template_key: survey
            for survey in self.env["survey.survey"].sudo().search([("x_180dc_template_key", "like", "180dc_%")])
        }
        specs = [
            ("180 Overall Experience", "overall_experience", "180dc_review_overall_experience"),
            ("Associate Director Feedback", "executive", "180dc_review_executive"),
            ("Project Leader Feedback", "project_leader", "180dc_review_project_leader"),
            ("Consultant / Senior Consultant Review", "consultant", "180dc_review_consultant"),
        ]
        for name, scope, survey_key in specs:
            survey = survey_by_key.get(survey_key)
            if not survey:
                continue
            template = self.search([("review_scope", "=", scope)], limit=1)
            values = {"name": name, "review_scope": scope, "survey_id": survey.id, "active": True}
            if template:
                template.write(values)
            else:
                self.create(values)


class X180DCReviewAssignment(models.Model):
    _name = "x_180dc.review.assignment"
    _description = "180DC Review Assignment"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    template_id = fields.Many2one("x_180dc.review.template", required=True, ondelete="restrict")
    review_scope = fields.Selection(related="template_id.review_scope", store=True)
    season_id = fields.Many2one(
        "x_180dc.season",
        required=True,
        ondelete="restrict",
        default=lambda self: self.env["x_180dc.season"]._x_180dc_current_season().id,
    )
    subject_employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    reviewer_employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    reviewer_user_id = fields.Many2one(related="reviewer_employee_id.user_id", store=True)
    engagement_id = fields.Many2one("x_180dc.engagement", ondelete="set null")
    survey_user_input_id = fields.Many2one("survey.user_input", ondelete="set null")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    survey_url = fields.Char(compute="_compute_survey_url")

    @api.depends("survey_user_input_id.access_token", "survey_user_input_id.survey_id")
    def _compute_survey_url(self):
        for assignment in self:
            assignment.survey_url = assignment.survey_user_input_id.get_start_url() if assignment.survey_user_input_id else False

    def _x_180dc_applicable_rules(self):
        self.ensure_one()
        return self.template_id.rule_ids.filtered("active")

    def _x_180dc_validate_scope(self):
        for assignment in self:
            rules = assignment._x_180dc_applicable_rules()
            if not rules:
                raise ValidationError("No active review rule is configured for the selected review template.")
            last_error = ValidationError("The selected subject and reviewer do not match the configured review rules.")
            for rule in rules:
                try:
                    rule._x_180dc_validate_assignment(assignment)
                    last_error = False
                    break
                except ValidationError as error:
                    last_error = error
            if last_error:
                raise last_error
            if not assignment.reviewer_user_id:
                raise ValidationError("The reviewer must have an active linked Odoo user.")

    def _x_180dc_ensure_user_input(self):
        for assignment in self:
            if assignment.survey_user_input_id:
                continue
            answer = assignment.template_id.survey_id.sudo()._create_answer(
                user=assignment.reviewer_user_id,
                partner=assignment.reviewer_employee_id.user_partner_id,
                email=assignment.reviewer_employee_id.work_email or assignment.reviewer_employee_id.private_email,
            )[:1]
            assignment.survey_user_input_id = answer

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super().create(vals_list)
        assignments._x_180dc_validate_scope()
        assignments._x_180dc_ensure_user_input()
        assignments.write({"state": "sent"})
        return assignments

    def write(self, vals):
        res = super().write(vals)
        self._x_180dc_validate_scope()
        if "template_id" in vals or "reviewer_employee_id" in vals:
            self.sudo().write({"survey_user_input_id": False, "state": "draft"})
            self._x_180dc_ensure_user_input()
            self.sudo().write({"state": "sent"})
        return res

    def action_mark_cancelled(self):
        self.write({"state": "cancelled"})
