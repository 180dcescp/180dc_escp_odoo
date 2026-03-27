from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sc_instance_name = fields.Char(
        string="Instance Name",
        config_parameter="student_consultancy.instance_name",
        default="Student Consultancy Instance",
    )
    sc_instance_code = fields.Char(
        string="Instance Code",
        config_parameter="student_consultancy.instance_code",
        default="student_consultancy",
    )
    sc_configuration_warnings = fields.Text(
        string="Student Consultancy Mode Checks",
        compute="_compute_sc_configuration_warnings",
        readonly=True,
    )

    @api.depends("sc_instance_name", "sc_instance_code")
    def _compute_sc_configuration_warnings(self):
        warnings = self.env["student.consultancy.mode"].configuration_warnings()
        value = "\n".join(f"- {warning}" for warning in warnings) if warnings else "All curated mode checks passed."
        for settings in self:
            settings.sc_configuration_warnings = value
