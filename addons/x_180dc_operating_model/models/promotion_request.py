from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class X180DCPromotionRequest(models.Model):
    _name = "x_180dc.promotion.request"
    _description = "180DC Appointment"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    current_department_id = fields.Many2one("hr.department", compute="_compute_current_role")
    current_job_id = fields.Many2one("hr.job", compute="_compute_current_role")
    requested_department_id = fields.Many2one("hr.department", required=True, ondelete="restrict")
    requested_job_id = fields.Many2one("hr.job", required=True, ondelete="restrict")
    requested_work_location_id = fields.Many2one("hr.work.location", ondelete="set null")
    approval_scope_id = fields.Many2one(
        "x_180dc.approval.scope",
        compute="_compute_approval_scope",
        string="Approval Scope",
        store=False,
    )
    requested_by_user_id = fields.Many2one(
        "res.users",
        string="Requested By",
        required=True,
        default=lambda self: self.env.user.id,
        ondelete="restrict",
    )
    approved_by_user_id = fields.Many2one("res.users", string="Approved By", ondelete="set null")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
    )
    reason = fields.Text()

    @api.depends("employee_id")
    def _compute_current_role(self):
        for request in self:
            contract = request.employee_id.current_membership_contract_id
            request.current_department_id = contract.department_id if contract else False
            request.current_job_id = contract.job_id if contract else False

    @api.depends("requested_department_id", "requested_job_id", "requested_work_location_id")
    def _compute_approval_scope(self):
        for request in self:
            rule = request._x_180dc_approval_rule()
            request.approval_scope_id = rule.approval_scope_id

    def _x_180dc_approval_rule(self):
        self.ensure_one()
        if not self.requested_job_id:
            return self.env["x_180dc.promotion_approval_rule"]
        return self.env["x_180dc.promotion_approval_rule"]._x_180dc_rule_for_request(self)

    def _x_180dc_required_approval_scope(self):
        self.ensure_one()
        return self._x_180dc_approval_rule().approval_scope_id

    def _x_180dc_can_approve(self, user):
        scope = self._x_180dc_required_approval_scope()
        return bool(scope and scope._x_180dc_matches_approver(user, self))

    @api.constrains("employee_id", "requested_department_id", "requested_job_id")
    def _check_employee_current_member(self):
        for request in self:
            if not request.employee_id.is_current_member:
                raise ValidationError("Promotion requests require a current member with a current-season contract.")
            if not request._x_180dc_required_approval_scope():
                raise ValidationError("No promotion approval rule is configured for the selected target role.")

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        for request in self:
            if not request._x_180dc_can_approve(self.env.user):
                raise AccessError("You are not allowed to approve this promotion request.")
            contract = request.employee_id.current_membership_contract_id
            if not contract:
                raise ValidationError("The employee no longer has a current membership contract.")
            contract._x_180dc_retrigger_membership_contract(
                {
                    "department_id": request.requested_department_id.id,
                    "job_id": request.requested_job_id.id,
                    "x_work_location_id": request.requested_work_location_id.id or contract.x_work_location_id.id,
                }
            )
            request.write({"state": "approved", "approved_by_user_id": self.env.user.id})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
