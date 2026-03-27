from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentConsultancyPosition(models.Model):
    _name = "student.consultancy.position"
    _description = "Student Consultancy Position"
    _order = "application_deadline asc, id desc"

    name = fields.Char(required=True)
    code = fields.Char()
    department_id = fields.Many2one("student.consultancy.department", ondelete="set null")
    target_role_id = fields.Many2one("student.consultancy.role", ondelete="set null")
    cycle_period_id = fields.Many2one("student.consultancy.cycle.period", ondelete="set null")
    description = fields.Html()
    active = fields.Boolean(default=True)
    is_public = fields.Boolean(default=True)
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("closed", "Closed"), ("filled", "Filled")],
        default="draft",
        required=True,
    )
    application_deadline = fields.Date()
    openings_count = fields.Integer(default=1)
    application_ids = fields.One2many("student.consultancy.application", "position_id")
    application_count = fields.Integer(compute="_compute_application_count")

    def _compute_application_count(self):
        for position in self:
            position.application_count = len(position.application_ids)


class StudentConsultancyApplication(models.Model):
    _name = "student.consultancy.application"
    _description = "Student Consultancy Application"
    _order = "create_date desc, id desc"
    _inherits = {"res.partner": "partner_id"}
    _rec_name = "partner_id"

    position_id = fields.Many2one("student.consultancy.position", required=True, ondelete="cascade")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    applicant_name = fields.Char(string="Applicant Name", related="partner_id.name", store=True, readonly=False)
    applicant_email = fields.Char(string="Applicant Email", related="partner_id.email", store=True, readonly=False)
    motivation = fields.Text()
    source = fields.Selection(
        [("website", "Website"), ("manual", "Manual"), ("referral", "Referral")],
        default="website",
        required=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("reviewing", "Reviewing"),
            ("interview", "Interview"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("withdrawn", "Withdrawn"),
        ],
        string="Application State",
        default="new",
        required=True,
    )
    decision_note = fields.Text()
    converted_member_id = fields.Many2one("student.consultancy.member", readonly=True, ondelete="set null")
    converted_membership_id = fields.Many2one("student.consultancy.membership", readonly=True, ondelete="set null")
    cycle_period_id = fields.Many2one(related="position_id.cycle_period_id", store=True, readonly=True)

    _sql_constraints = [
        (
            "student_consultancy_application_position_partner_unique",
            "unique(position_id, partner_id)",
            "A partner can only have one application per position.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = [self._normalize_application_vals(vals) for vals in vals_list]
        applications = super().create(normalized_vals_list)
        applications._sync_partner_flags()
        return applications

    def write(self, vals):
        result = super().write(self._normalize_application_vals(dict(vals)))
        self._sync_partner_flags()
        return result

    def _find_partner_for_application(self, applicant_email):
        if not applicant_email:
            return self.env["res.partner"]
        return self.env["res.partner"].search([("email", "=", applicant_email)], limit=1)

    def _prepare_partner_values(self, values):
        applicant_name = (values.get("applicant_name") or values.get("name") or "").strip()
        applicant_email = (values.get("applicant_email") or values.get("email") or "").strip().lower()
        partner_values = {}
        if applicant_name:
            partner_values["name"] = applicant_name
        if applicant_email:
            partner_values["email"] = applicant_email
        return partner_values

    def _ensure_partner_for_values(self, values):
        partner_model = self.env["res.partner"]
        partner_values = self._prepare_partner_values(values)
        partner = partner_model.browse(values["partner_id"]).exists() if values.get("partner_id") else partner_model
        if not partner and len(self) == 1:
            partner = self.partner_id

        if not partner and partner_values.get("email"):
            partner = self._find_partner_for_application(partner_values["email"])
        if not partner and partner_values:
            partner = partner_model.create(partner_values)
        elif partner and partner_values:
            partner.write(partner_values)

        if partner:
            values["partner_id"] = partner.id
        return values

    def _normalize_application_vals(self, vals):
        values = dict(vals)
        values = self._ensure_partner_for_values(values)
        applicant_name = (values.get("applicant_name") or values.get("name") or "").strip()
        applicant_email = (values.get("applicant_email") or values.get("email") or "").strip().lower()
        if applicant_name:
            values["applicant_name"] = applicant_name
            values["name"] = applicant_name
        if applicant_email:
            values["applicant_email"] = applicant_email
            values["email"] = applicant_email
        return values

    @api.constrains("partner_id")
    def _check_partner_identity(self):
        for application in self:
            if not application.partner_id.name:
                raise ValidationError("Applications require an applicant name.")
            if not application.partner_id.email:
                raise ValidationError("Applications require an applicant email.")

    def _sync_partner_flags(self):
        for application in self:
            if application.partner_id:
                application.partner_id.student_consultancy_mark_contact(is_applicant=application.state != "accepted")

    def action_mark_reviewing(self):
        self.write({"state": "reviewing"})

    def action_mark_interview(self):
        self.write({"state": "interview"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_withdraw(self):
        self.write({"state": "withdrawn"})

    def action_accept(self):
        cycle_service = self.env["student.consultancy.cycle.service"]
        today = fields.Date.to_date(fields.Date.context_today(self))
        for application in self:
            if not application.position_id.target_role_id:
                raise ValidationError("Accepted applications require a target role on the position.")
            partner = application.partner_id
            partner.student_consultancy_mark_contact(is_applicant=False, is_member=True)

            member = self.env["student.consultancy.member"].search([("partner_id", "=", partner.id)], limit=1)
            if not member:
                member = self.env["student.consultancy.member"].create({"partner_id": partner.id})

            cycle_period = application.position_id.cycle_period_id or cycle_service.get_current_cycle()
            membership_values = {
                "member_id": member.id,
                "role_id": application.position_id.target_role_id.id,
                "department_id": application.position_id.department_id.id,
                "state": "active",
            }
            if cycle_period:
                membership_values["start_cycle_period_id"] = cycle_period.id
                membership_values["valid_through_cycle_period_id"] = cycle_period.id
                if cycle_period.start_date and cycle_period.start_date > today:
                    membership_values["state"] = "incoming"
            else:
                membership_values["start_date"] = today
            membership = self.env["student.consultancy.membership"].create(membership_values)

            application.write(
                {
                    "partner_id": partner.id,
                    "state": "accepted",
                    "converted_member_id": member.id,
                    "converted_membership_id": membership.id,
                }
            )
            application.position_id.state = "filled"
        return True
