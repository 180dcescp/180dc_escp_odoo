from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentConsultancyDepartment(models.Model):
    _name = "student.consultancy.department"
    _description = "Student Consultancy Department"
    _order = "name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    lead_member_id = fields.Many2one("student.consultancy.member", ondelete="set null")

    _sql_constraints = [
        ("student_consultancy_department_code_unique", "unique(code)", "The department code must be unique."),
    ]


class StudentConsultancyRole(models.Model):
    _name = "student.consultancy.role"
    _description = "Student Consultancy Role"
    _order = "hierarchy_rank desc, name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    hierarchy_rank = fields.Integer(default=10)
    eligible_for_staffing = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
    group_ids = fields.Many2many(
        "res.groups",
        "student_consultancy_role_group_rel",
        "role_id",
        "group_id",
        string="Mapped Odoo Groups",
    )

    _sql_constraints = [
        ("student_consultancy_role_code_unique", "unique(code)", "The role code must be unique."),
    ]


class StudentConsultancyMember(models.Model):
    _name = "student.consultancy.member"
    _description = "Student Consultancy Member"
    _order = "active desc, name, id"

    active = fields.Boolean(default=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    user_id = fields.Many2one("res.users", ondelete="set null")
    name = fields.Char(related="partner_id.name", store=True, readonly=False)
    email = fields.Char(related="partner_id.email", store=True, readonly=False)
    profile_bio = fields.Text()
    visibility_consent = fields.Boolean(default=False)
    profile_ready = fields.Boolean(default=False)
    is_public = fields.Boolean(string="Visible on Website", default=False)
    public_sort_order = fields.Integer(default=10)
    membership_ids = fields.One2many("student.consultancy.membership", "member_id")
    current_department_id = fields.Many2one(
        "student.consultancy.department",
        compute="_compute_current_membership_context",
        string="Current Department",
    )
    current_role_id = fields.Many2one(
        "student.consultancy.role",
        compute="_compute_current_membership_context",
        string="Current Role",
    )
    status = fields.Selection(
        [("incoming", "Incoming"), ("active", "Active"), ("paused", "Paused"), ("alumni", "Alumni")],
        compute="_compute_status",
        string="Lifecycle Status",
    )

    _sql_constraints = [
        (
            "student_consultancy_member_partner_unique",
            "unique(partner_id)",
            "A partner can only be linked to one student consultancy member record.",
        ),
    ]

    def _active_memberships(self, on_date=None):
        self.ensure_one()
        date_value = fields.Date.to_date(on_date or fields.Date.context_today(self))
        return self.membership_ids.filtered(lambda membership: membership.state == "active" and membership.is_effective_on(date_value))

    def _paused_memberships(self, on_date=None):
        self.ensure_one()
        date_value = fields.Date.to_date(on_date or fields.Date.context_today(self))
        return self.membership_ids.filtered(lambda membership: membership.state == "paused" and membership.is_effective_on(date_value))

    def _incoming_memberships(self, on_date=None):
        self.ensure_one()
        date_value = fields.Date.to_date(on_date or fields.Date.context_today(self))
        return self.membership_ids.filtered(
            lambda membership: membership.state == "incoming" and (membership.effective_start_date() or date_value) > date_value
        )

    @api.depends(
        "membership_ids.state",
        "membership_ids.start_date",
        "membership_ids.end_date",
        "membership_ids.start_cycle_period_id",
        "membership_ids.valid_through_cycle_period_id",
    )
    def _compute_status(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        for member in self:
            if member._active_memberships(on_date=today):
                member.status = "active"
            elif member._paused_memberships(on_date=today):
                member.status = "paused"
            elif member._incoming_memberships(on_date=today):
                member.status = "incoming"
            else:
                member.status = "alumni"

    @api.depends(
        "membership_ids.state",
        "membership_ids.role_id",
        "membership_ids.department_id",
        "membership_ids.start_date",
        "membership_ids.end_date",
        "membership_ids.start_cycle_period_id",
        "membership_ids.valid_through_cycle_period_id",
    )
    def _compute_current_membership_context(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        for member in self:
            membership = member._active_memberships(on_date=today)[:1]
            if not membership:
                membership = member._paused_memberships(on_date=today)[:1]
            if not membership:
                membership = member._incoming_memberships(on_date=today)[:1]
            member.current_department_id = membership.department_id if membership else False
            member.current_role_id = membership.role_id if membership else False

    def _managed_role_groups(self):
        return self.env["student.consultancy.role"].sudo().search([]).mapped("group_ids")

    def _target_role_groups(self):
        self.ensure_one()
        today = fields.Date.to_date(fields.Date.context_today(self))
        return self._active_memberships(on_date=today).mapped("role_id.group_ids")

    def _sync_partner_flags(self):
        for member in self:
            if not member.partner_id:
                continue
            member.partner_id.student_consultancy_mark_contact(
                is_member=member.status in ("incoming", "active", "paused"),
                is_alumni=member.status == "alumni",
                is_applicant=False,
            )

    def _sync_role_groups(self):
        managed_groups = self._managed_role_groups()
        default_group = self.env.ref("student_consultancy_core.group_student_consultancy_user")
        for member in self:
            if not member.user_id:
                continue
            target_groups = member._target_role_groups()
            final_groups = (member.user_id.groups_id - managed_groups) | target_groups | default_group
            member.user_id.groups_id = [(6, 0, final_groups.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        members._sync_partner_flags()
        members._sync_role_groups()
        return members

    def write(self, vals):
        result = super().write(vals)
        self._sync_partner_flags()
        self._sync_role_groups()
        return result


class StudentConsultancyMembership(models.Model):
    _name = "student.consultancy.membership"
    _description = "Student Consultancy Membership"
    _order = "start_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    member_id = fields.Many2one("student.consultancy.member", required=True, ondelete="cascade")
    role_id = fields.Many2one("student.consultancy.role", required=True, ondelete="restrict")
    department_id = fields.Many2one("student.consultancy.department", ondelete="set null")
    state = fields.Selection(
        [("incoming", "Incoming"), ("active", "Active"), ("paused", "Paused"), ("ended", "Ended")],
        default="incoming",
        required=True,
    )
    start_date = fields.Date()
    end_date = fields.Date()
    start_cycle_period_id = fields.Many2one("student.consultancy.cycle.period", ondelete="set null")
    valid_through_cycle_period_id = fields.Many2one("student.consultancy.cycle.period", ondelete="set null")
    eligible_for_staffing = fields.Boolean(compute="_compute_eligible_for_staffing")
    is_current = fields.Boolean(compute="_compute_is_current")

    @api.depends("member_id", "role_id")
    def _compute_name(self):
        for membership in self:
            member_name = membership.member_id.name or "Member"
            role_name = membership.role_id.name or "Role"
            membership.name = f"{member_name} / {role_name}"

    @api.depends("state", "role_id.eligible_for_staffing")
    def _compute_eligible_for_staffing(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        for membership in self:
            membership.eligible_for_staffing = (
                membership.state == "active"
                and membership.role_id.eligible_for_staffing
                and membership.is_effective_on(today)
            )

    @api.depends(
        "state",
        "start_date",
        "end_date",
        "start_cycle_period_id",
        "valid_through_cycle_period_id",
    )
    def _compute_is_current(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        for membership in self:
            membership.is_current = membership.state in ("active", "paused") and membership.is_effective_on(today)

    @api.constrains("start_date", "end_date")
    def _check_date_range(self):
        for membership in self:
            start = membership.effective_start_date()
            end = membership.effective_end_date()
            if start and end and start > end:
                raise ValidationError("Membership start must be on or before membership end.")

    def effective_start_date(self):
        self.ensure_one()
        return self.start_date or self.start_cycle_period_id.start_date

    def effective_end_date(self):
        self.ensure_one()
        return self.end_date or self.valid_through_cycle_period_id.end_date

    def is_effective_on(self, on_date):
        self.ensure_one()
        date_value = fields.Date.to_date(on_date)
        start = self.effective_start_date()
        end = self.effective_end_date()
        if start and date_value < start:
            return False
        if end and date_value > end:
            return False
        return True

    def action_activate(self):
        self.write({"state": "active"})

    def action_pause(self):
        self.write({"state": "paused"})

    def action_end(self):
        self.write({"state": "ended", "end_date": self.end_date or fields.Date.context_today(self)})

    @api.model_create_multi
    def create(self, vals_list):
        memberships = super().create(vals_list)
        memberships.mapped("member_id")._sync_partner_flags()
        memberships.mapped("member_id")._sync_role_groups()
        return memberships

    def write(self, vals):
        result = super().write(vals)
        self.mapped("member_id")._sync_partner_flags()
        self.mapped("member_id")._sync_role_groups()
        return result
