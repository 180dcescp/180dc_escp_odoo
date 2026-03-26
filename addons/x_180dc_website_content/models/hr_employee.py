from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    x_current_public_profile_visibility = fields.Selection(
        [
            ("hidden", "Do Not Appear"),
            ("without_photo", "Appear Without Photo"),
            ("with_photo", "Appear With Photo"),
        ],
        compute="_compute_x_current_public_profile_fields",
        string="Current Website Appearance",
        store=False,
    )
    x_current_public_field_of_study = fields.Char(
        compute="_compute_x_current_public_profile_fields",
        string="Current Field of Study",
        store=False,
    )
    x_current_public_professional_background = fields.Char(
        compute="_compute_x_current_public_profile_fields",
        string="Current Professional Background",
        store=False,
    )

    @staticmethod
    def _x_180dc_public_sort_key(employee):
        contract = employee.current_membership_contract_id
        department_name = (contract.department_id.name or employee.department_id.name or "").strip()
        job_name = (contract.job_id.name or employee.job_title or "").strip()
        return (department_name.lower(), job_name.lower(), (employee.name or "").lower(), employee.id)

    def _x_180dc_public_membership_contract(self):
        self.ensure_one()
        contract = self.current_membership_contract_id
        if not contract or not contract._x_180dc_is_publicly_visible():
            return False
        return contract

    def _x_180dc_public_photo_url(self, base_url=None):
        self.ensure_one()
        contract = self._x_180dc_public_membership_contract()
        if not contract or not contract._x_180dc_photo_is_public() or not self.image_1920:
            return False
        prefix = (base_url or "").rstrip("/")
        return f"{prefix}/x_180dc/website/v1/team-photo/{self.id}" if prefix else f"/x_180dc/website/v1/team-photo/{self.id}"

    def _compute_x_current_public_profile_fields(self):
        for employee in self:
            contract = employee.current_membership_contract_id
            employee.x_current_public_profile_visibility = contract.x_public_profile_visibility if contract else False
            employee.x_current_public_field_of_study = (
                contract._x_180dc_field_of_study_label() if contract else False
            )
            employee.x_current_public_professional_background = (
                contract._x_180dc_professional_background_label() if contract else False
            )

    def _x_180dc_payload(self, base_url=None):
        self.ensure_one()
        contract = self._x_180dc_public_membership_contract()
        if not contract:
            return False
        return {
            "name": self.name,
            "role": contract.job_id.name if contract.job_id else self.job_title or "Team Member",
            "department": contract.department_id.name or "180DC ESCP",
            "campus": contract.x_work_location_id.name or self.work_location_id.name or "Unknown",
            "program": contract.x_member_program or self.x_program or None,
            "fieldOfStudy": contract._x_180dc_field_of_study_label() or None,
            "professionalBackground": contract._x_180dc_professional_background_label() or None,
            "photoUrl": self._x_180dc_public_photo_url(base_url=base_url) or None,
        }
