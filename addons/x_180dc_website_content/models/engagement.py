from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .utils import slugify_name


PROJECT_TYPE_DEFAULTS = {
    "go-to-market-and-commercialization": (
        "Sharpen commercial focus, refine offer positioning, and build a clearer path from proposition to traction."
    ),
    "market-entry-and-expansion-strategy": (
        "Assess expansion priorities, sequencing, and go-to-market choices when organisations move into new markets."
    ),
    "business-model-and-organization-design": (
        "Improve organisational shape, role design, and operating choices so strategy can actually land."
    ),
    "operations-and-process-optimization": (
        "Remove operational drag, tighten delivery rhythm, and design processes that support scale."
    ),
    "partner-and-ecosystem-strategy": (
        "Clarify ecosystem priorities, partner logic, and collaboration models for mission-led growth."
    ),
    "portfolio-and-innovation-strategy": (
        "Prioritise initiatives, shape innovation bets, and align portfolios with real organisational capacity."
    ),
    "fundraising-and-revenue-diversification": (
        "Support fundraising logic, revenue resilience, and clearer capital narratives."
    ),
    "program-and-service-design": (
        "Design services and programmes around user reality, operational feasibility, and measurable value."
    ),
    "research-and-impact-assessment": (
        "Turn research and evidence into decision-ready recommendations for teams under time pressure."
    ),
    "digital-and-marketing-strategy": (
        "Clarify digital priorities, channel logic, and messaging structure for stronger audience traction."
    ),
    "market-opportunity-and-growth-strategy": (
        "Size opportunities, identify growth paths, and stress-test where momentum can realistically come from."
    ),
}


class X180DCEngagementProjectType(models.Model):
    _inherit = "x_180dc.engagement.project_type"

    x_short_description = fields.Text(string="Short Description")
    x_long_description = fields.Html(string="Long Description")

    def _x_180dc_seed_public_defaults(self):
        for record in self:
            updates = {}
            slug = slugify_name(record.name)
            default_description = PROJECT_TYPE_DEFAULTS.get(slug)
            if default_description and not record.x_short_description:
                updates["x_short_description"] = default_description
            if default_description and not record.x_long_description:
                updates["x_long_description"] = f"<p>{default_description}</p>"
            if updates:
                record.write(updates)

    def _x_180dc_payload(self, engagement_map):
        self.ensure_one()
        project_ids = [engagement.id for engagement in engagement_map.get(self.id, self.env["x_180dc.engagement"])]
        return {
            "slug": slugify_name(self.name),
            "name": self.name,
            "shortDescription": self.x_short_description or self.name,
            "longDescription": self.x_long_description or f"<p>{self.x_short_description or self.name}</p>",
            "projectCount": len(project_ids),
            "featuredProjectIds": [
                engagement.x_public_slug
                for engagement in engagement_map.get(self.id, self.env["x_180dc.engagement"]).filtered("x_featured")
                if engagement.x_public_slug
            ],
        }


class X180DCEngagement(models.Model):
    _inherit = "x_180dc.engagement"

    x_public_visibility = fields.Selection(
        [
            ("private", "Private"),
            ("client_only", "Client Mention Only"),
            ("anonymized", "Anonymized Case"),
            ("full_disclosure", "Full Disclosure"),
        ],
        string="Public Disclosure",
        default="private",
        required=True,
        tracking=True,
    )
    x_scheduled_public_visibility = fields.Selection(
        [
            ("private", "Private"),
            ("client_only", "Client Mention Only"),
            ("anonymized", "Anonymized Case"),
            ("full_disclosure", "Full Disclosure"),
        ],
        string="Scheduled Disclosure",
        tracking=True,
    )
    x_scheduled_public_visibility_at = fields.Datetime(string="Scheduled Disclosure At", tracking=True)
    x_public_slug = fields.Char(string="Public Slug", copy=False, index=True)
    x_public_summary = fields.Text(string="Public Summary")
    x_public_outcomes = fields.Text(string="Public Outcomes")
    x_featured = fields.Boolean(string="Featured on Website", default=False)
    x_effective_public_visibility = fields.Selection(
        [
            ("private", "Private"),
            ("client_only", "Client Mention Only"),
            ("anonymized", "Anonymized Case"),
            ("full_disclosure", "Full Disclosure"),
        ],
        compute="_compute_x_effective_public_visibility",
        search="_search_x_effective_public_visibility",
        string="Effective Disclosure",
        store=False,
    )

    _sql_constraints = [
        ("x_180dc_engagement_public_slug_uniq", "unique(x_public_slug)", "Engagement slug must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") and not vals.get("x_public_slug"):
                vals["x_public_slug"] = slugify_name(vals["name"])
        return super().create(vals_list)

    def write(self, vals):
        for record in self:
            update_vals = dict(vals)
            if "name" in vals and not vals.get("x_public_slug"):
                update_vals["x_public_slug"] = slugify_name(vals["name"])
            super(X180DCEngagement, record).write(update_vals)
        return True

    def _x_180dc_public_outcome_list(self):
        self.ensure_one()
        return [line.strip() for line in (self.x_public_outcomes or "").splitlines() if line.strip()]

    def _x_180dc_current_public_visibility(self):
        self.ensure_one()
        if (
            self.x_scheduled_public_visibility
            and self.x_scheduled_public_visibility_at
            and self.x_scheduled_public_visibility_at <= fields.Datetime.now()
        ):
            return self.x_scheduled_public_visibility
        return self.x_public_visibility

    def _x_180dc_effective_public_visibility_state(self):
        self.ensure_one()
        visibility = self._x_180dc_current_public_visibility()
        has_logo = bool(self.client_company_id and self.client_company_id.x_public_logo_url)
        if visibility == "client_only" and not has_logo:
            return "private"
        if visibility == "full_disclosure" and not has_logo:
            return "anonymized"
        return visibility

    def _compute_x_effective_public_visibility(self):
        for engagement in self:
            engagement.x_effective_public_visibility = engagement._x_180dc_effective_public_visibility_state()

    @api.model
    def _search_x_effective_public_visibility(self, operator, value):
        if operator not in {"=", "!=", "in", "not in"}:
            raise ValidationError("Unsupported operator for effective disclosure search.")

        if operator in {"=", "!="}:
            target_values = {value}
        else:
            target_values = set(value or [])

        matching_ids = self.search([]).filtered(
            lambda engagement: engagement._x_180dc_effective_public_visibility_state() in target_values
        ).ids
        if operator in {"!=", "not in"}:
            return [("id", "not in", matching_ids)]
        return [("id", "in", matching_ids)]

    @api.onchange("x_public_visibility", "x_scheduled_public_visibility", "client_company_id")
    def _onchange_x_public_visibility(self):
        selected_visibilities = {self.x_public_visibility, self.x_scheduled_public_visibility}
        if (
            selected_visibilities & {"client_only", "full_disclosure"}
            and self.client_company_id
            and not self.client_company_id.x_public_logo_url
        ):
            return {
                "warning": {
                    "title": "Missing client logo",
                    "message": (
                        "This disclosure level names the client, but the selected client company has no public logo URL. "
                        "Client-only disclosure will fall back to private, and full disclosure will fall back to anonymized."
                    ),
                }
            }

    @api.constrains("x_scheduled_public_visibility", "x_scheduled_public_visibility_at")
    def _check_scheduled_public_visibility(self):
        for engagement in self:
            if bool(engagement.x_scheduled_public_visibility) != bool(engagement.x_scheduled_public_visibility_at):
                raise ValidationError("Scheduled disclosure state and scheduled disclosure time must be set together.")

    def _x_180dc_project_is_publishable(self):
        self.ensure_one()
        return self._x_180dc_effective_public_visibility_state() in {"anonymized", "full_disclosure"} and bool(
            self.x_public_slug
        )

    def _x_180dc_client_mention_payload(self):
        self.ensure_one()
        if self._x_180dc_effective_public_visibility_state() != "client_only" or not self.client_company_id:
            return False
        return {
            "client": self.client_company_id._x_180dc_public_payload(),
            "engagementName": self.name,
            "serviceSlugs": [slugify_name(project_type.name) for project_type in self.project_type_ids if project_type.name],
        }

    @api.model
    def _x_180dc_cron_apply_scheduled_public_visibility(self):
        due_engagements = self.search(
            [
                ("x_scheduled_public_visibility", "!=", False),
                ("x_scheduled_public_visibility_at", "!=", False),
                ("x_scheduled_public_visibility_at", "<=", fields.Datetime.now()),
            ]
        )
        for engagement in due_engagements:
            engagement.write(
                {
                    "x_public_visibility": engagement.x_scheduled_public_visibility,
                    "x_scheduled_public_visibility": False,
                    "x_scheduled_public_visibility_at": False,
                }
            )

    def _x_180dc_payload(self):
        self.ensure_one()
        effective_visibility = self._x_180dc_effective_public_visibility_state()
        client_payload = None
        if effective_visibility == "full_disclosure" and self.client_company_id:
            client_payload = self.client_company_id._x_180dc_public_payload()

        return {
            "slug": self.x_public_slug,
            "title": self.name,
            "visibility": effective_visibility,
            "summary": self.x_public_summary or (self.summary or "").strip() or self.name,
            "serviceSlugs": [slugify_name(project_type.name) for project_type in self.project_type_ids if project_type.name],
            "year": self.cycle_year or fields.Date.today().year,
            "sector": self.client_company_id.x_public_sector_label or None,
            "outcomes": self._x_180dc_public_outcome_list(),
            "featured": bool(self.x_featured),
            "client": client_payload,
        }
