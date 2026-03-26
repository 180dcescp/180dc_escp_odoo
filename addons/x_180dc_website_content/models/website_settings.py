from odoo import api, fields, models


class X180DCWebsiteSettings(models.Model):
    _name = "x_180dc.website.settings"
    _description = "180DC Website Settings"
    _order = "id asc"

    name = fields.Char(default="Website Settings", required=True)
    site_name = fields.Char(required=True, default="180 Degrees Consulting ESCP")
    site_url = fields.Char(required=True, default="https://180dc-escp.org")
    contact_email = fields.Char(required=True, default="contact@180dc-escp.org")
    intake_description = fields.Text(
        required=True,
        default=(
            "Tell us what decision you are trying to make, the timeline around it, "
            "and where you need outside strategic support."
        ),
    )
    linkedin_url = fields.Char(default="https://www.linkedin.com/company/180-degrees-consulting-escp")
    instagram_url = fields.Char(default="https://www.instagram.com/180dc_escp")

    @api.model
    def _x_180dc_get_settings(self):
        settings = self.search([], order="id asc", limit=1)
        if settings:
            return settings
        return self.create({})

    def _x_180dc_payload(self):
        self.ensure_one()
        return {
            "siteName": self.site_name,
            "siteUrl": self.site_url,
            "contactEmail": self.contact_email,
            "intakeDescription": self.intake_description,
            "socialLinks": {
                "linkedin": self.linkedin_url or "",
                "instagram": self.instagram_url or "",
                "email": self.contact_email,
            },
        }

    @api.model
    def _x_180dc_metric_context(self):
        membership_type = self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")

        engagements = self.env["x_180dc.engagement"].sudo().search([("active", "=", True)])
        publishable_projects = engagements.filtered(lambda engagement: engagement._x_180dc_project_is_publishable())
        visible_project_types = publishable_projects.mapped("project_type_ids").filtered(lambda record: record.name)
        client_mentions = engagements.filtered(
            lambda engagement: engagement._x_180dc_effective_public_visibility_state() == "client_only"
        )
        featured_projects = publishable_projects.filtered("x_featured")
        full_disclosure_projects = engagements.filtered(
            lambda engagement: engagement._x_180dc_effective_public_visibility_state() == "full_disclosure"
            and engagement.x_public_slug
        )
        visible_clients = (
            full_disclosure_projects.mapped("client_company_id") | client_mentions.mapped("client_company_id")
        ).filtered(lambda partner: partner)
        client_sectors = {sector for sector in visible_clients.mapped("x_public_sector_label") if sector}
        scheduled_changes = engagements.filtered(
            lambda engagement: engagement.x_scheduled_public_visibility and engagement.x_scheduled_public_visibility_at
        )

        active_employees = self.env["hr.employee"].sudo().search([("active", "=", True)])
        current_membership_contracts = active_employees.mapped("current_membership_contract_id").filtered(
            lambda contract: contract.contract_type_id == membership_type
        )
        visible_team_members = active_employees.filtered(lambda employee: employee._x_180dc_public_membership_contract())
        visible_team_with_photo = visible_team_members.filtered(lambda employee: employee._x_180dc_public_photo_url())
        campuses = current_membership_contracts.mapped("x_work_location_id").filtered(lambda location: location)

        departments = self.env["hr.department"].sudo().search([])
        described_departments = departments.filtered(lambda department: department.x_public_description)
        jobs = self.env["hr.job"].sudo().search([("active", "=", True)])
        described_jobs = jobs.filtered(lambda job: job.description)
        open_jobs = jobs.filtered(lambda job: job._x_180dc_is_publicly_open())

        candidates = self.env["hr.candidate"].sudo().search([("active", "=", True)])
        applicants = self.env["hr.applicant"].sudo().search([])

        return {
            "engagements": engagements,
            "publishable_projects": publishable_projects,
            "visible_project_types": visible_project_types,
            "client_mentions": client_mentions,
            "featured_projects": featured_projects,
            "visible_clients": visible_clients,
            "client_sectors": client_sectors,
            "active_employees": active_employees,
            "current_membership_contracts": current_membership_contracts,
            "visible_team_members": visible_team_members,
            "visible_team_with_photo": visible_team_with_photo,
            "campuses": campuses,
            "departments": departments,
            "described_departments": described_departments,
            "jobs": jobs,
            "described_jobs": described_jobs,
            "open_jobs": open_jobs,
            "candidates": candidates,
            "applicants": applicants,
            "scheduled_changes": scheduled_changes,
        }

    @api.model
    def _x_180dc_metric_value(self, key, context=None):
        context = context or self._x_180dc_metric_context()
        values = {
            "engagements_total": len(context["engagements"]),
            "publishable_projects_total": len(context["publishable_projects"]),
            "featured_projects_total": len(context["featured_projects"]),
            "client_mentions_total": len(context["client_mentions"]),
            "project_types_total": len(self.env["x_180dc.engagement.project_type"].sudo().search([])),
            "publishable_services_total": len(context["visible_project_types"]),
            "client_companies_showcased_total": len(context["visible_clients"]),
            "client_sectors_total": len(context["client_sectors"]),
            "active_members_total": len(context["current_membership_contracts"]),
            "public_team_members_total": len(context["visible_team_members"]),
            "public_team_with_photo_total": len(context["visible_team_with_photo"]),
            "campuses_total": len(context["campuses"]),
            "departments_total": len(context["departments"]),
            "departments_described_total": len(context["described_departments"]),
            "active_jobs_total": len(context["jobs"]),
            "positions_described_total": len(context["described_jobs"]),
            "open_positions_total": len(context["open_jobs"]),
            "active_candidates_total": len(context["candidates"]),
            "applicants_total": len(context["applicants"]),
            "scheduled_disclosure_changes_total": len(context["scheduled_changes"]),
        }
        return values.get(key, 0)

    @api.model
    def _x_180dc_metrics_payload(self):
        context = self._x_180dc_metric_context()
        payload = []
        definitions = self.env["x_180dc.website.kpi_definition"].sudo().search([("active", "=", True)], order="sequence asc, id asc")
        for spec in definitions:
            value = self._x_180dc_metric_value(spec["key"], context=context)
            payload.append(
                {
                    "key": spec["key"],
                    "label": spec["label"],
                    "value": str(value),
                    "suffix": spec.suffix or "",
                    "emphasis": spec.emphasis or "proof",
                    "internalDescription": spec.internal_description or "",
                    "externalDescription": spec.external_description or "",
                    "description": spec.external_description or "",
                }
            )
        return payload

    @api.model
    def x_180dc_dashboard_payload(self):
        settings = self.sudo()._x_180dc_get_settings()
        membership_type = self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")

        engagements = self.env["x_180dc.engagement"].sudo().search([("active", "=", True)], order="date_start desc, id desc")
        publishable_projects = engagements.filtered(lambda engagement: engagement._x_180dc_project_is_publishable())
        publishable_services = publishable_projects.mapped("project_type_ids").filtered(lambda record: record.name)
        client_mentions = engagements.filtered(
            lambda engagement: engagement._x_180dc_effective_public_visibility_state() == "client_only"
        )
        scheduled_changes = engagements.filtered(
            lambda engagement: engagement.x_scheduled_public_visibility and engagement.x_scheduled_public_visibility_at
        ).sorted(key=lambda engagement: engagement.x_scheduled_public_visibility_at or fields.Datetime.now())
        logo_fallbacks = engagements.filtered(
            lambda engagement: engagement.x_public_visibility in {"client_only", "full_disclosure"}
            and engagement.client_company_id
            and not engagement.client_company_id.x_public_logo_url
        )
        missing_project_slugs = engagements.filtered(
            lambda engagement: engagement.x_public_visibility in {"anonymized", "full_disclosure"} and not engagement.x_public_slug
        )

        active_employees = self.env["hr.employee"].sudo().search([("active", "=", True)])
        current_membership_contracts = active_employees.mapped("current_membership_contract_id").filtered(
            lambda contract: contract.contract_type_id == membership_type
        )
        visible_team_members = active_employees.filtered(lambda employee: employee._x_180dc_public_membership_contract())
        incomplete_contracts = current_membership_contracts.filtered(
            lambda contract: contract._x_180dc_requires_profile_completion(force=True) and not contract.x_public_profile_ready
        )

        departments = self.env["hr.department"].sudo().search([], order="name asc, id asc")
        jobs = self.env["hr.job"].sudo().search([], order="department_id, name, id")
        open_jobs = jobs.filtered(lambda job: job._x_180dc_is_publicly_open())
        departments_missing_description = departments.filtered(lambda department: not department.x_public_description)
        jobs_missing_description = jobs.filtered(lambda job: not job.description)

        return {
            "generatedAt": fields.Datetime.now().isoformat(),
            "summaryCards": [
                {
                    "key": "services",
                    "label": "Publishable Services",
                    "value": len(publishable_services),
                    "help": "Project types backed by at least one publishable engagement.",
                },
                {
                    "key": "projects",
                    "label": "Publishable Projects",
                    "value": len(publishable_projects),
                    "help": "Engagements currently exposed as anonymized or fully disclosed cases.",
                },
                {
                    "key": "team",
                    "label": "Visible Team Members",
                    "value": len(visible_team_members),
                    "help": "Active members whose current membership contract allows website appearance.",
                },
                {
                    "key": "openings",
                    "label": "Positions Open for Applications",
                    "value": len(open_jobs),
                    "help": "Native job records explicitly marked as open on the public site.",
                },
                {
                    "key": "client_mentions",
                    "label": "Client Mentions Only",
                    "value": len(client_mentions),
                    "help": "Engagements that may mention the client without exposing project details.",
                },
                {
                    "key": "scheduled_changes",
                    "label": "Scheduled Disclosure Changes",
                    "value": len(scheduled_changes),
                    "help": "Engagements with a future disclosure transition configured.",
                },
            ],
            "quickActions": [
                {
                    "label": "Engagement Publishing",
                    "description": "Disclosure, slugs, summaries, and client-proof controls.",
                    "actionXmlId": "x_180dc_website_content.x_180dc_website_engagement_action",
                },
                {
                    "label": "Team Visibility",
                    "description": "Membership-contract consent, profile readiness, and photo status.",
                    "actionXmlId": "x_180dc_website_content.x_180dc_website_team_contract_action",
                },
                {
                    "label": "Departments",
                    "description": "Department public descriptions used in the role catalog.",
                    "actionXmlId": "x_180dc_website_content.x_180dc_website_department_action",
                },
                {
                    "label": "Positions",
                    "description": "Native job records with public descriptions and explicit application state.",
                    "actionXmlId": "x_180dc_website_content.x_180dc_website_job_action",
                },
                {
                    "label": "Site Settings",
                    "description": "Site-wide contact details, intake copy, and social links.",
                    "actionXmlId": "x_180dc_website_content.x_180dc_website_settings_action",
                },
            ],
            "healthQueues": {
                "logoFallbacks": [
                    {
                        "id": engagement.id,
                        "name": engagement.name,
                        "client": engagement.client_company_id.name or "No client",
                        "configuredVisibility": engagement.x_public_visibility,
                        "effectiveVisibility": engagement._x_180dc_effective_public_visibility_state(),
                    }
                    for engagement in logo_fallbacks[:8]
                ],
                "missingProjectSlugs": [
                    {
                        "id": engagement.id,
                        "name": engagement.name,
                        "client": engagement.client_company_id.name or "No client",
                        "configuredVisibility": engagement.x_public_visibility,
                    }
                    for engagement in missing_project_slugs[:8]
                ],
                "incompleteProfiles": [
                    {
                        "id": contract.id,
                        "member": contract.employee_id.name or "Unknown member",
                        "department": contract.department_id.name or "",
                        "position": contract.job_id.name or "",
                        "visibility": contract.x_public_profile_visibility,
                        "missingFields": contract._x_180dc_public_profile_missing_fields(force=True),
                    }
                    for contract in incomplete_contracts[:8]
                ],
                "departmentsMissingDescription": [
                    {
                        "id": department.id,
                        "name": department.name,
                    }
                    for department in departments_missing_description[:8]
                ],
                "jobsMissingDescription": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "department": job.department_id.name or "",
                    }
                    for job in jobs_missing_description[:8]
                ],
            },
            "scheduledChanges": [
                {
                    "id": engagement.id,
                    "name": engagement.name,
                    "client": engagement.client_company_id.name or "",
                    "currentVisibility": engagement.x_public_visibility,
                    "scheduledVisibility": engagement.x_scheduled_public_visibility,
                    "scheduledAt": fields.Datetime.to_string(engagement.x_scheduled_public_visibility_at),
                }
                for engagement in scheduled_changes[:10]
            ],
            "catalogStatus": {
                "departmentsTotal": len(departments),
                "departmentsDescribed": len(departments) - len(departments_missing_description),
                "positionsTotal": len(jobs),
                "positionsWithDescription": len(jobs) - len(jobs_missing_description),
                "positionsCurrentlyOpen": len(open_jobs),
            },
            "siteSettings": {
                "siteName": settings.site_name,
                "siteUrl": settings.site_url,
                "contactEmail": settings.contact_email,
            },
        }
