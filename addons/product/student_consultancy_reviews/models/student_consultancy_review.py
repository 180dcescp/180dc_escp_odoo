from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentConsultancyReviewTemplate(models.Model):
    _name = "student.consultancy.review.template"
    _description = "Student Consultancy Review Template"
    _order = "name, id"

    name = fields.Char(required=True)
    scope = fields.Selection(
        [("project", "Project"), ("leadership", "Leadership"), ("membership", "Membership")],
        required=True,
    )
    prompt = fields.Text(required=True)
    active = fields.Boolean(default=True)


class StudentConsultancyReviewAssignment(models.Model):
    _name = "student.consultancy.review.assignment"
    _description = "Student Consultancy Review Assignment"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    template_id = fields.Many2one("student.consultancy.review.template", required=True, ondelete="restrict")
    subject_member_id = fields.Many2one("student.consultancy.member", required=True, ondelete="cascade")
    reviewer_member_id = fields.Many2one("student.consultancy.member", required=True, ondelete="cascade")
    project_id = fields.Many2one("student.consultancy.project", ondelete="set null")
    cycle_period_id = fields.Many2one("student.consultancy.cycle.period", ondelete="set null")
    due_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    feedback_text = fields.Text()
    completed_on = fields.Datetime(readonly=True)

    def action_mark_sent(self):
        self.write({"state": "sent"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_mark_done(self):
        self.write({"state": "done", "completed_on": fields.Datetime.now()})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.constrains("subject_member_id", "reviewer_member_id")
    def _check_distinct_people(self):
        for assignment in self:
            if assignment.subject_member_id == assignment.reviewer_member_id:
                raise ValidationError("Subject and reviewer must be different members.")
