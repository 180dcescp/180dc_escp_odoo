from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    _X_180DC_PROTECTED_SUPERUSER_ID = 1

    x_manual_business_group_ids = fields.Many2many(
        "res.groups",
        "x_180dc_res_users_business_group_rel",
        "user_id",
        "group_id",
        string="180DC Business Roles",
    )
    x_available_business_group_ids = fields.Many2many(
        "res.groups",
        compute="_compute_x_available_business_group_ids",
        string="Available 180DC Business Roles",
    )

    @api.model
    def _x_180dc_business_group_xmlids(self):
        return [
            "x_180dc_operating_model.group_180dc_presidency",
            "x_180dc_operating_model.group_180dc_people_org_associate_director",
            "x_180dc_operating_model.group_180dc_people_org_head",
            "x_180dc_operating_model.group_180dc_business_development_associate_director",
            "x_180dc_operating_model.group_180dc_business_development_head",
            "x_180dc_operating_model.group_180dc_marketing_associate_director",
            "x_180dc_operating_model.group_180dc_marketing_head",
            "x_180dc_operating_model.group_180dc_finance_associate_director",
            "x_180dc_operating_model.group_180dc_finance_head",
            "x_180dc_operating_model.group_180dc_consulting_associate_director",
            "x_180dc_operating_model.group_180dc_consulting_head",
            "x_180dc_operating_model.group_180dc_consulting_project_leader",
            "x_180dc_operating_model.group_180dc_consultant",
        ]

    @api.model
    def _x_180dc_business_groups(self):
        groups = [
            self.env.ref(xmlid, raise_if_not_found=False)
            for xmlid in self._x_180dc_business_group_xmlids()
        ]
        return self.env["res.groups"].browse([group.id for group in groups if group])

    @api.model
    def _x_180dc_allow_user_create(self):
        return bool(
            self.env.context.get("x_180dc_allow_user_create")
            or self.env.context.get("install_mode")
        )

    @api.model
    def _x_180dc_allow_password_write(self):
        return bool(
            self.env.context.get("x_180dc_allow_password_write")
            or self.env.context.get("install_mode")
        )

    @api.model
    def _x_180dc_allow_native_group_assignment(self):
        return bool(
            self.env.uid == self._X_180DC_PROTECTED_SUPERUSER_ID
            or self.env.context.get("x_180dc_allow_native_group_assignment")
            or self.env.context.get("install_mode")
        )

    @api.depends_context("uid")
    def _compute_x_available_business_group_ids(self):
        groups = self._x_180dc_business_groups()
        for user in self:
            user.x_available_business_group_ids = groups

    def _oauth_bridge_member_employee(self, email):
        normalized_email = self._oauth_bridge_normalize_email(email)
        if not self.env["x_180dc.operating_policy"].sudo()._x_180dc_allowed_employee_email(normalized_email):
            return self.env["hr.employee"]
        employee = (
            self.env["hr.employee"]
            .with_user(1)
            .sudo()
            .search([("active", "=", True), ("work_email", "=", normalized_email)], limit=1)
        )
        if not employee:
            return employee
        employee._x_180dc_sync_membership_state()
        return employee.filtered("is_current_member")[:1]

    def _oauth_bridge_existing_user(self, email, provider, oauth_uid):
        employee = self._oauth_bridge_member_employee(email)
        if employee and employee.user_id:
            return employee.user_id.sudo()
        return super()._oauth_bridge_existing_user(email, provider, oauth_uid)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._x_180dc_allow_user_create():
            raise ValidationError(
                "Manual user creation is disabled. Users must be provisioned from employees or Authentik."
            )
        return super().create(vals_list)

    def write(self, vals):
        protected_superuser = self.filtered(
            lambda user: user.id == self._X_180DC_PROTECTED_SUPERUSER_ID
        )
        native_group_keys = {
            key for key in vals
            if key == "groups_id" or key.startswith("in_group_") or key.startswith("sel_groups_")
        }
        if protected_superuser and {"login", "email", "active"} & set(vals):
            raise ValidationError(
                "The protected superadmin user cannot be renamed or deactivated."
            )
        if native_group_keys and not self._x_180dc_allow_native_group_assignment():
            raise ValidationError(
                "Only the protected superadmin can edit native group assignments. Use 180DC Business Roles instead."
            )
        if vals.get("password") and not self._x_180dc_allow_password_write():
            raise ValidationError(
                "Password login is disabled. Use Authentik SSO or an API key."
            )
        result = super().write(vals)
        if "x_manual_business_group_ids" in vals:
            self._x_180dc_sync_manual_business_groups()
        return result

    def unlink(self):
        if any(user.id == self._X_180DC_PROTECTED_SUPERUSER_ID for user in self):
            raise ValidationError("The protected superadmin user cannot be deleted.")
        return super().unlink()

    def _x_180dc_sync_manual_business_groups(self):
        business_group_ids = set(self._x_180dc_business_groups().ids)
        for user in self.with_context(active_test=False):
            if user.id == self._X_180DC_PROTECTED_SUPERUSER_ID:
                continue
            if user.employee_ids:
                user.employee_ids.with_context(active_test=False)._x_180dc_sync_membership_state()
                continue
            preserved_group_ids = [
                group_id for group_id in user.groups_id.ids if group_id not in business_group_ids
            ]
            desired_group_ids = sorted(set(preserved_group_ids) | set(user.x_manual_business_group_ids.ids))
            if set(user.groups_id.ids) != set(desired_group_ids):
                user.with_context(x_180dc_allow_native_group_assignment=True).write(
                    {"groups_id": [(6, 0, desired_group_ids)]}
                )


class ResGroups(models.Model):
    _inherit = "res.groups"

    @api.model
    def _x_180dc_allow_group_definition_write(self):
        return bool(
            self.env.uid == 1
            or self.env.context.get("install_mode")
            or self.env.context.get("x_180dc_allow_group_definition_write")
        )

    @api.model_create_multi
    def create(self, vals_list):
        if not self._x_180dc_allow_group_definition_write():
            raise ValidationError("Only the protected superadmin can modify group definitions.")
        return super().create(vals_list)

    def write(self, vals):
        if not self._x_180dc_allow_group_definition_write():
            raise ValidationError("Only the protected superadmin can modify group definitions.")
        return super().write(vals)

    def unlink(self):
        if not self._x_180dc_allow_group_definition_write():
            raise ValidationError("Only the protected superadmin can modify group definitions.")
        return super().unlink()
