from odoo import fields, models


class X180DCWebsiteKPIDefinition(models.Model):
    _name = "x_180dc.website.kpi_definition"
    _description = "180DC Website KPI Definition"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    key = fields.Char(required=True, index=True)
    label = fields.Char(required=True)
    internal_description = fields.Text()
    external_description = fields.Text()
    suffix = fields.Char()
    emphasis = fields.Selection(
        [
            ("proof", "Proof"),
            ("scale", "Scale"),
            ("journey", "Journey"),
        ],
        default="proof",
        required=True,
    )

    _sql_constraints = [
        ("x_180dc_website_kpi_definition_key_uniq", "unique(key)", "Website KPI key must be unique."),
    ]
