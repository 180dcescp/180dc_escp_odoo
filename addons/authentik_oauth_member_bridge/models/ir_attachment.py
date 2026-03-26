from odoo import api, models
from odoo.exceptions import ValidationError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _attachment_policy_enabled(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("global_attachment_policy.block_user_uploads", "1")
        )
        return (value or "1").strip().lower() in {"1", "true", "yes", "on"}

    @api.model
    def _attachment_policy_bypass(self):
        return (
            not self._attachment_policy_enabled()
            or self.env.su
            or self.env.user.has_group("base.group_system")
            or self.env.context.get("attachment_policy_bypass")
        )

    @api.model
    def _attachment_policy_is_binary(self, vals):
        attachment_type = vals.get("type")
        if attachment_type == "url":
            return False
        binary_markers = (
            vals.get("datas"),
            vals.get("raw"),
            vals.get("db_datas"),
            vals.get("store_fname"),
        )
        return attachment_type in (None, "binary") or any(binary_markers)

    @api.model
    def _attachment_policy_enforce(self, vals_list):
        if self._attachment_policy_bypass():
            return
        if any(self._attachment_policy_is_binary(vals) for vals in vals_list):
            raise ValidationError(
                "File uploads are disabled in Odoo. Store files in Google Drive and save only the share link in Odoo."
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._attachment_policy_enforce(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        self._attachment_policy_enforce([vals])
        return super().write(vals)
