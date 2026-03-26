from odoo import api, models
from odoo.exceptions import ValidationError


class X180DCAdminRuleMixin(models.AbstractModel):
    _name = "x_180dc.admin_rule_mixin"
    _description = "180DC Admin-only Rule Mixin"

    @api.model
    def _x_180dc_allow_rule_admin_write(self):
        return bool(
            self.env.uid == 1
            or self.env.context.get("install_mode")
            or self.env.context.get("x_180dc_allow_rule_admin_write")
        )

    @api.model_create_multi
    def create(self, vals_list):
        if not self._x_180dc_allow_rule_admin_write():
            raise ValidationError("Only the protected superadmin can modify operating-rule definitions.")
        return super().create(vals_list)

    def write(self, vals):
        if not self._x_180dc_allow_rule_admin_write():
            raise ValidationError("Only the protected superadmin can modify operating-rule definitions.")
        return super().write(vals)

    def unlink(self):
        if not self._x_180dc_allow_rule_admin_write():
            raise ValidationError("Only the protected superadmin can modify operating-rule definitions.")
        return super().unlink()
