from odoo import api, fields, models
from odoo.exceptions import ValidationError


PUBLIC_PROFILE_VISIBILITY = [
    ("hidden", "Do Not Appear"),
    ("without_photo", "Appear Without Photo"),
    ("with_photo", "Appear With Photo"),
]

FIELD_OF_STUDY = [
    ("business", "Business"),
    ("engineering", "Engineering"),
    ("law", "Law"),
    ("economics", "Economics"),
    ("politics", "Politics / International Affairs"),
    ("data", "Data / Computer Science"),
    ("social_science", "Social Science"),
    ("other", "Other"),
]

PROFESSIONAL_BACKGROUND = [
    ("consulting", "Consulting"),
    ("marketing", "Marketing / Communications"),
    ("finance", "Finance"),
    ("operations", "Operations"),
    ("research", "Research"),
    ("product", "Product / Tech"),
    ("sales", "Sales / Business Development"),
    ("nonprofit", "Nonprofit / Impact"),
    ("other", "Other"),
]


class HrContract(models.Model):
    _inherit = "hr.contract"

    x_member_program = fields.Char(string="ESCP Program")
    x_public_profile_visibility = fields.Selection(
        PUBLIC_PROFILE_VISIBILITY,
        string="Website Appearance",
        default="with_photo",
        tracking=True,
    )
    x_public_field_of_study = fields.Selection(
        FIELD_OF_STUDY,
        string="Field of Study",
        tracking=True,
    )
    x_public_professional_background = fields.Selection(
        PROFESSIONAL_BACKGROUND,
        string="Professional Background",
        tracking=True,
    )
    x_public_profile_ready = fields.Boolean(
        compute="_compute_x_public_profile_ready",
        search="_search_x_public_profile_ready",
        string="Public Profile Ready",
        store=False,
    )

    def _x_180dc_membership_contract_type(self):
        return self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")

    def _x_180dc_is_membership_contract_record(self):
        membership_type = self._x_180dc_membership_contract_type()
        return self.filtered(lambda contract: contract.contract_type_id == membership_type)

    def _x_180dc_selection_label(self, field_name):
        self.ensure_one()
        value = self[field_name]
        if not value:
            return False
        return dict(self._fields[field_name].selection).get(value)

    def _x_180dc_field_of_study_label(self):
        self.ensure_one()
        return self._x_180dc_selection_label("x_public_field_of_study")

    def _x_180dc_professional_background_label(self):
        self.ensure_one()
        return self._x_180dc_selection_label("x_public_professional_background")

    def _x_180dc_requires_profile_completion(self, force=False):
        self.ensure_one()
        return bool(
            self.contract_type_id == self._x_180dc_membership_contract_type() and (force or self.x_contract_sent_at)
        )

    def _x_180dc_public_profile_missing_fields(self, force=False):
        self.ensure_one()
        if not self._x_180dc_requires_profile_completion(force=force):
            return []

        missing = []
        if not self.x_public_profile_visibility:
            missing.append("Visibility preference")
        if not self.x_work_location_id:
            missing.append("Campus / work location")
        if not self.x_member_program:
            missing.append("Program")
        if self.x_public_profile_visibility in {"without_photo", "with_photo"}:
            if not self.x_public_field_of_study:
                missing.append("Field of study")
            if not self.x_public_professional_background:
                missing.append("Professional background")
        if self.x_public_profile_visibility == "with_photo" and not self.employee_id.image_1920:
            missing.append("Profile photo")
        return missing

    def _x_180dc_is_publicly_visible(self):
        self.ensure_one()
        return self.x_public_profile_visibility in {"without_photo", "with_photo"}

    def _x_180dc_photo_is_public(self):
        self.ensure_one()
        return self.x_public_profile_visibility == "with_photo"

    @api.depends(
        "x_contract_sent_at",
        "x_member_program",
        "x_public_profile_visibility",
        "x_public_field_of_study",
        "x_public_professional_background",
        "x_work_location_id",
        "employee_id.image_1920",
    )
    def _compute_x_public_profile_ready(self):
        for contract in self:
            if not contract._x_180dc_requires_profile_completion():
                contract.x_public_profile_ready = True
                continue
            contract.x_public_profile_ready = not bool(contract._x_180dc_public_profile_missing_fields())

    @api.model
    def _search_x_public_profile_ready(self, operator, value):
        if operator not in {"=", "!=", "in", "not in"}:
            raise ValidationError("Unsupported operator for public profile readiness search.")

        if operator in {"=", "!="}:
            target_values = {bool(value)}
        else:
            target_values = {bool(item) for item in (value or [])}

        matching_ids = self.search([]).filtered(lambda contract: contract.x_public_profile_ready in target_values).ids
        if operator in {"!=", "not in"}:
            return [("id", "not in", matching_ids)]
        return [("id", "in", matching_ids)]

    def _x_180dc_prefill_profile_vals(self, vals):
        employee = False
        if vals.get("employee_id"):
            employee = self.env["hr.employee"].browse(vals["employee_id"])

        if employee and not vals.get("x_member_program") and employee.x_program:
            vals["x_member_program"] = employee.x_program
        if employee and not vals.get("x_work_location_id") and employee.work_location_id:
            vals["x_work_location_id"] = employee.work_location_id.id

    def _x_180dc_sync_employee_profile(self):
        today = fields.Date.context_today(self)
        membership_type = self._x_180dc_membership_contract_type()
        for contract in self.filtered(lambda rec: rec.contract_type_id == membership_type and rec.employee_id):
            active_contract = self.search(
                [
                    ("employee_id", "=", contract.employee_id.id),
                    ("contract_type_id", "=", membership_type.id),
                    ("state", "=", "open"),
                    ("date_start", "<=", today),
                    "|",
                    ("date_end", "=", False),
                    ("date_end", ">=", today),
                ],
                order="date_start desc, id desc",
                limit=1,
            )
            if active_contract != contract:
                continue

            updates = {}
            if contract.x_member_program and contract.employee_id.x_program != contract.x_member_program:
                updates["x_program"] = contract.x_member_program
            if contract.x_work_location_id and contract.employee_id.work_location_id != contract.x_work_location_id:
                updates["work_location_id"] = contract.x_work_location_id.id
            if updates:
                contract.employee_id.sudo().write(updates)

    def _x_180dc_validate_public_profile(self, force=False):
        for contract in self:
            if not contract._x_180dc_requires_profile_completion(force=force):
                continue
            missing = contract._x_180dc_public_profile_missing_fields(force=force)
            if missing:
                raise ValidationError(
                    "The membership contract is missing website profile information: %s." % ", ".join(missing)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._x_180dc_prefill_profile_vals(vals)
        contracts = super().create(vals_list)
        contracts._x_180dc_sync_employee_profile()
        return contracts

    def write(self, vals):
        for contract in self:
            contract_vals = dict(vals)
            if {"employee_id", "x_member_program", "x_work_location_id"} & set(contract_vals):
                contract._x_180dc_prefill_profile_vals(contract_vals)
            super(HrContract, contract).write(contract_vals)
        self._x_180dc_sync_employee_profile()
        return True

    def action_mark_contract_sent(self):
        self._x_180dc_validate_public_profile(force=True)
        return super().action_mark_contract_sent()
