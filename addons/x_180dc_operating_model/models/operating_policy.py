from odoo import api, fields, models


class X180DCOperatingPolicy(models.Model):
    _name = "x_180dc.operating_policy"
    _description = "180DC Operating Policy"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "id asc"

    name = fields.Char(default="Operating Policy", required=True)
    alumni_cooldown_months = fields.Integer(default=6, required=True)
    allowed_email_domain_ids = fields.One2many(
        "x_180dc.allowed_email_domain",
        "policy_id",
        string="Allowed Employee Email Domains",
    )

    @api.model
    def _x_180dc_get_policy(self):
        policy = self.search([], order="id asc", limit=1)
        if policy:
            return policy
        return self.with_context(x_180dc_allow_rule_admin_write=True).create({})

    def _x_180dc_payload(self):
        self.ensure_one()
        return {
            "alumniCooldownMonths": self.alumni_cooldown_months,
            "allowedEmailDomains": self.allowed_email_domain_ids.mapped("domain"),
        }

    def _x_180dc_normalized_email_domains(self):
        self.ensure_one()
        return {
            (domain.domain or "").strip().lower()
            for domain in self.allowed_email_domain_ids
            if domain.domain
        }

    def _x_180dc_email_domain_allowed(self, email):
        self.ensure_one()
        email = (email or "").strip().lower()
        if "@" not in email:
            return False
        domain = email.rsplit("@", 1)[1]
        allowed_domains = self._x_180dc_normalized_email_domains()
        return bool(domain and domain in allowed_domains)

    @api.model
    def _x_180dc_allowed_employee_email(self, email):
        return self._x_180dc_get_policy()._x_180dc_email_domain_allowed(email)

    @api.model
    def _x_180dc_ensure_default_policy(self):
        policy = self._x_180dc_get_policy()
        if policy.alumni_cooldown_months <= 0:
            policy.with_context(x_180dc_allow_rule_admin_write=True).write({"alumni_cooldown_months": 6})
        if not policy.allowed_email_domain_ids.filtered(lambda record: record.domain == "180dc.org"):
            self.env["x_180dc.allowed_email_domain"].with_context(
                x_180dc_allow_rule_admin_write=True
            ).create(
                {
                    "policy_id": policy.id,
                    "domain": "180dc.org",
                }
            )


class X180DCAllowedEmailDomain(models.Model):
    _name = "x_180dc.allowed_email_domain"
    _description = "180DC Allowed Employee Email Domain"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "domain, id"

    policy_id = fields.Many2one("x_180dc.operating_policy", required=True, ondelete="cascade")
    domain = fields.Char(required=True)

    _sql_constraints = [
        (
            "x_180dc_allowed_email_domain_uniq",
            "unique(policy_id, domain)",
            "Employee email domains must be unique per operating policy.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("domain"):
                vals["domain"] = vals["domain"].strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("domain"):
            vals = dict(vals)
            vals["domain"] = vals["domain"].strip().lower()
        return super().write(vals)
