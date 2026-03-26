from odoo import api, fields, models
from odoo.exceptions import ValidationError


class X180DCCommitmentAssignment(models.Model):
    _name = "x_180dc.commitment.assignment"
    _description = "180DC Commitment Assignment"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    user_id = fields.Many2one(related="employee_id.user_id", store=True)
    season_id = fields.Many2one(
        "x_180dc.season",
        required=True,
        default=lambda self: self.env["x_180dc.season"]._x_180dc_current_season().id,
    )
    next_season_id = fields.Many2one(
        "x_180dc.season",
        required=True,
        default=lambda self: self.env["x_180dc.season"]._x_180dc_next_season().id,
    )
    survey_id = fields.Many2one("survey.survey", required=True, ondelete="restrict")
    survey_user_input_id = fields.Many2one("survey.user_input", ondelete="set null")
    summer_break_allowed = fields.Boolean(compute="_compute_summer_break_allowed")
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

    _sql_constraints = [
        (
            "x_180dc_commitment_emp_next_uniq",
            "unique(employee_id, next_season_id)",
            "A commitment survey already exists for this member and next season.",
        )
    ]

    @api.depends("employee_id", "next_season_id")
    def _compute_summer_break_allowed(self):
        for assignment in self:
            assignment.summer_break_allowed = bool(
                assignment.next_season_id.cycle == "summer"
                and assignment.employee_id.current_membership_contract_id.x_is_project_staffable
            )

    @api.depends("survey_user_input_id.access_token", "survey_user_input_id.survey_id")
    def _compute_survey_url(self):
        for assignment in self:
            assignment.survey_url = assignment.survey_user_input_id.get_start_url() if assignment.survey_user_input_id else False

    def _x_180dc_validate(self):
        for assignment in self:
            if not assignment.employee_id.is_current_member:
                raise ValidationError("Commitment surveys can only be created for current members.")
            if assignment.next_season_id == assignment.season_id:
                raise ValidationError("Commitment surveys must target the next season.")
            if assignment.survey_id.x_180dc_template_key != "180dc_commitment_next_cycle":
                raise ValidationError("Commitment assignments must use the end-of-cycle commitment survey.")

    def _x_180dc_ensure_user_input(self):
        for assignment in self:
            if assignment.survey_user_input_id or not assignment.user_id:
                continue
            answer = assignment.survey_id.sudo()._create_answer(
                user=assignment.user_id,
                partner=assignment.employee_id.user_partner_id,
                email=assignment.employee_id.work_email or assignment.employee_id.private_email,
            )[:1]
            assignment.survey_user_input_id = answer

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super().create(vals_list)
        assignments._x_180dc_validate()
        assignments._x_180dc_ensure_user_input()
        assignments.write({"state": "sent"})
        return assignments

    def write(self, vals):
        res = super().write(vals)
        if {"employee_id", "season_id", "next_season_id", "survey_id"} & set(vals):
            self._x_180dc_validate()
        return res

    def action_mark_cancelled(self):
        self.write({"state": "cancelled"})

    @api.model
    def _x_180dc_generate_for_next_season(self):
        current_season = self.env["x_180dc.season"]._x_180dc_current_season()
        next_season = self.env["x_180dc.season"]._x_180dc_next_season(current_season)
        survey = self.env["survey.survey"].search([("x_180dc_template_key", "=", "180dc_commitment_next_cycle")], limit=1)
        if not survey:
            return self.browse()
        assignments = self.browse()
        for employee in self.env["hr.employee"].search([]).filtered("is_current_member"):
            existing = self.search(
                [("employee_id", "=", employee.id), ("next_season_id", "=", next_season.id)],
                limit=1,
            )
            if existing:
                assignments |= existing
                continue
            assignment = self.create(
                {
                    "name": f"{employee.name} Commitment for {next_season.name}",
                    "employee_id": employee.id,
                    "season_id": current_season.id,
                    "next_season_id": next_season.id,
                    "survey_id": survey.id,
                }
            )
            assignments |= assignment
        return assignments
