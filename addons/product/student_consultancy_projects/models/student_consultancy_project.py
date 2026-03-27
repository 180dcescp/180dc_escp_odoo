from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentConsultancyProjectType(models.Model):
    _name = "student.consultancy.project.type"
    _description = "Student Consultancy Project Type"
    _order = "name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("student_consultancy_project_type_code_unique", "unique(code)", "The project type code must be unique."),
    ]


class StudentConsultancyProject(models.Model):
    _name = "student.consultancy.project"
    _description = "Student Consultancy Project"
    _order = "start_date desc, id desc"

    name = fields.Char(required=True)
    code = fields.Char()
    type_id = fields.Many2one("student.consultancy.project.type", ondelete="set null")
    client_partner_id = fields.Many2one("res.partner", ondelete="set null")
    lead_id = fields.Many2one("crm.lead", ondelete="set null")
    cycle_period_id = fields.Many2one("student.consultancy.cycle.period", ondelete="set null")
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
    )
    public_visibility = fields.Selection(
        [("hidden", "Hidden"), ("members", "Members"), ("public", "Public")],
        default="hidden",
        required=True,
    )
    summary = fields.Html()
    active = fields.Boolean(default=True)
    start_date = fields.Date(default=fields.Date.today)
    end_date = fields.Date()
    staffing_assignment_ids = fields.One2many("student.consultancy.staffing.assignment", "project_id")
    staffing_assignment_count = fields.Integer(compute="_compute_staffing_assignment_count")

    _sql_constraints = [
        (
            "student_consultancy_project_lead_unique",
            "unique(lead_id)",
            "A CRM opportunity can only create one student consultancy project.",
        ),
    ]

    def _compute_staffing_assignment_count(self):
        for project in self:
            project.staffing_assignment_count = len(project.staffing_assignment_ids)


class StudentConsultancyStaffingAssignment(models.Model):
    _name = "student.consultancy.staffing.assignment"
    _description = "Student Consultancy Staffing Assignment"
    _order = "project_id, id"

    project_id = fields.Many2one("student.consultancy.project", required=True, ondelete="cascade")
    member_id = fields.Many2one("student.consultancy.member", required=True, ondelete="cascade")
    membership_id = fields.Many2one("student.consultancy.membership", ondelete="restrict")
    role_id = fields.Many2one("student.consultancy.role", ondelete="set null")
    state = fields.Selection(
        [("proposed", "Proposed"), ("confirmed", "Confirmed"), ("released", "Released")],
        default="proposed",
        required=True,
    )
    start_date = fields.Date()
    end_date = fields.Date()
    notes = fields.Text()

    def _default_membership_for_member(self, member):
        return member.membership_ids.filtered(lambda membership: membership.eligible_for_staffing)[:1]

    @api.constrains("member_id", "membership_id", "role_id")
    def _check_membership_alignment(self):
        for assignment in self:
            membership = assignment.membership_id
            if membership and membership.member_id != assignment.member_id:
                raise ValidationError("Staffing assignment membership must belong to the selected member.")
            if membership and not membership.eligible_for_staffing:
                raise ValidationError("Only active memberships with staffing-eligible roles can be staffed on projects.")
            if assignment.role_id and not assignment.role_id.eligible_for_staffing:
                raise ValidationError("The selected project role is not eligible for staffing.")

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._normalize_assignment_vals(vals) for vals in vals_list]
        return super().create(normalized_vals_list)

    def write(self, vals):
        return super().write(self._normalize_assignment_vals(dict(vals)))

    def _normalize_assignment_vals(self, vals):
        values = dict(vals)
        member = False
        if values.get("member_id"):
            member = self.env["student.consultancy.member"].browse(values["member_id"]).exists()
        elif self and len(self) == 1:
            member = self.member_id
        if member and not values.get("membership_id"):
            membership = self._default_membership_for_member(member)
            if membership:
                values["membership_id"] = membership.id
                values.setdefault("role_id", membership.role_id.id)
            else:
                raise ValidationError("The selected member does not have an active staffing-eligible membership.")
        return values

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_release(self):
        self.write({"state": "released"})


class StudentConsultancyProjectService(models.AbstractModel):
    _name = "student.consultancy.project.service"
    _description = "Student Consultancy Project Service"

    def public_projects(self):
        return self.env["student.consultancy.project"].search(
            [("active", "=", True), ("state", "=", "active"), ("public_visibility", "=", "public")],
            order="start_date desc, id desc",
        )

    def eligible_members_for_staffing(self):
        memberships = self.env["student.consultancy.membership"].search([])
        return memberships.filtered("eligible_for_staffing").mapped("member_id")
