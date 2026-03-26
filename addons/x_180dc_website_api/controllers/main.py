import json
import secrets

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request


class WebsiteAPIController(http.Controller):
    def _json_error(self, message, status=400):
        return request.make_json_response({"ok": False, "error": message}, status=status)

    def _json_ok(self, payload, status=200):
        return request.make_json_response(payload, status=status)

    def _authenticate(self):
        configured_token = (
            request.env["ir.config_parameter"].sudo().get_param("x_180dc_website_api.api_key", "").strip()
        )
        if not configured_token:
            raise AccessDenied("Website API key is not configured")

        header_token = request.httprequest.headers.get("X-API-Key", "").strip()
        auth_header = request.httprequest.headers.get("Authorization", "").strip()
        bearer_token = ""
        if auth_header.lower().startswith("bearer "):
            bearer_token = auth_header.split(" ", 1)[1].strip()

        supplied_token = header_token or bearer_token
        if not supplied_token:
            raise AccessDenied("Missing API key")
        if not secrets.compare_digest(supplied_token, configured_token):
            raise AccessDenied("Invalid API key")

    def _json_payload(self):
        raw = request.httprequest.data or b"{}"
        return json.loads(raw.decode("utf-8"))

    def _clean_value(self, payload, key):
        value = payload.get(key)
        if isinstance(value, str):
            value = value.strip()
        return value or False

    def _find_or_create_partner(self, payload):
        email = self._clean_value(payload, "email")
        partner = request.env["res.partner"].sudo().search([("email", "=", email)], limit=1) if email else False
        partner_vals = {
            "name": self._clean_value(payload, "name"),
            "email": email,
            "phone": self._clean_value(payload, "phone"),
            "mobile": self._clean_value(payload, "phone"),
            "website": self._clean_value(payload, "website"),
        }
        if partner:
            updates = {key: value for key, value in partner_vals.items() if value and partner[key] != value}
            if updates:
                partner.write(updates)
            return partner
        return request.env["res.partner"].sudo().create({key: value for key, value in partner_vals.items() if value})

    def _find_or_create_candidate(self, payload, partner):
        email = self._clean_value(payload, "email")
        candidate = request.env["hr.candidate"].sudo().search([("email_from", "=", email)], limit=1) if email else False
        candidate_vals = {
            "partner_id": partner.id,
            "partner_name": partner.name or self._clean_value(payload, "name"),
            "email_from": email,
            "linkedin_profile": self._clean_value(payload, "linkedinUrl"),
        }
        if candidate:
            updates = {key: value for key, value in candidate_vals.items() if value and candidate[key] != value}
            if updates:
                candidate.write(updates)
            return candidate
        return request.env["hr.candidate"].sudo().create(candidate_vals)

    def _find_work_location(self, payload):
        campus = self._clean_value(payload, "campus") or self._clean_value(payload, "location")
        if not campus:
            return False
        return request.env["hr.work.location"].sudo().search([("name", "ilike", campus)], limit=1)

    def _find_job(self, payload):
        job_id = payload.get("jobId")
        if job_id:
            return request.env["hr.job"].sudo().browse(int(job_id)).exists()

        job_slug = self._clean_value(payload, "jobSlug") or self._clean_value(payload, "slug")
        if not job_slug:
            return False

        jobs = request.env["hr.job"].sudo().search([("active", "=", True)])
        return jobs.filtered(lambda job: job._x_180dc_public_opening_slug() == job_slug)[:1]

    def _visible_engagements(self):
        return request.env["x_180dc.engagement"].sudo().search(
            [("active", "=", True)],
            order="date_start desc, id desc",
        )

    @http.route("/x_180dc/website/v1/content", type="http", auth="public", methods=["GET"], csrf=False)
    def website_content(self, **kwargs):
        try:
            self._authenticate()
        except AccessDenied as error:
            return self._json_error(str(error), status=401)

        settings = request.env["x_180dc.website.settings"].sudo()._x_180dc_get_settings()
        public_base_url = request.httprequest.url_root.rstrip("/")
        engagements = self._visible_engagements()
        service_map = {}
        for engagement in engagements:
            if not engagement._x_180dc_project_is_publishable():
                continue
            for project_type in engagement.project_type_ids:
                service_map.setdefault(project_type.id, request.env["x_180dc.engagement"])
                service_map[project_type.id] |= engagement

        visible_project_types = request.env["x_180dc.engagement.project_type"].sudo().browse(list(service_map))
        services = [
            project_type._x_180dc_payload(service_map)
            for project_type in visible_project_types.sorted(lambda rec: ((rec.name or "").lower(), rec.id))
            if project_type.name
        ]
        projects = [
            engagement._x_180dc_payload()
            for engagement in engagements
            if engagement._x_180dc_project_is_publishable()
        ]
        client_mentions = [
            engagement._x_180dc_client_mention_payload()
            for engagement in engagements
            if engagement._x_180dc_client_mention_payload()
        ]
        positions = [
            job._x_180dc_public_opening_payload()
            for job in request.env["hr.job"].sudo().search([("active", "=", True)]).sorted(
                key=lambda rec: (
                    (rec.department_id.name or "").lower(),
                    (rec.name or "").lower(),
                    rec.id,
                )
            )
            if job._x_180dc_is_publicly_open()
        ]
        employees = request.env["hr.employee"].sudo().search([("active", "=", True)]).sorted(
            key=request.env["hr.employee"]._x_180dc_public_sort_key
        )
        team = [
            employee._x_180dc_payload(base_url=public_base_url)
            for employee in employees
            if employee._x_180dc_public_membership_contract()
        ]
        team = [payload for payload in team if payload]
        role_catalog = [
            department._x_180dc_public_payload()
            for department in request.env["hr.department"].sudo().search([], order="name asc, id asc")
        ]

        payload = {
            "generatedAt": fields.Datetime.now().isoformat(),
            "mode": "live",
            "source": "odoo",
            "siteSettings": settings._x_180dc_payload(),
            "metrics": settings._x_180dc_metrics_payload(),
            "services": services,
            "projects": projects,
            "positions": positions,
            "team": team,
            "clientMentions": client_mentions,
            "roleCatalog": role_catalog,
            "updates": [],
        }
        return self._json_ok(payload)

    @http.route(
        "/x_180dc/website/v1/team-photo/<int:employee_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def team_photo(self, employee_id, **kwargs):
        employee = request.env["hr.employee"].sudo().browse(employee_id).exists()
        if not employee:
            return request.not_found()
        contract = employee._x_180dc_public_membership_contract()
        if not contract or not contract._x_180dc_photo_is_public() or not employee.image_1920:
            return request.not_found()

        image_bytes = base64.b64decode(employee.image_1920)
        return request.make_response(
            image_bytes,
            headers=[
                ("Content-Type", "image/jpeg"),
                ("Cache-Control", "public, max-age=3600"),
            ],
        )

    @http.route("/x_180dc/website/v1/client-intake", type="http", auth="public", methods=["POST"], csrf=False)
    def client_intake(self, **kwargs):
        try:
            self._authenticate()
        except AccessDenied as error:
            return self._json_error(str(error), status=401)

        payload = self._json_payload()

        lead = request.env["crm.lead"].sudo().create(
            {
                "name": f"{payload.get('organization', 'Organisation')}: {payload.get('serviceInterest', 'Client Intake')}",
                "partner_name": payload.get("organization"),
                "contact_name": payload.get("name"),
                "email_from": payload.get("email"),
                "website": payload.get("website"),
                "description": (
                    f"Organisation type: {payload.get('organizationType')}\n"
                    f"Service interest: {payload.get('serviceInterest')}\n"
                    f"Timeline: {payload.get('timeline')}\n\n"
                    f"Challenge:\n{payload.get('challenge')}"
                ),
                "type": "lead",
            }
        )
        return self._json_ok({"ok": True, "leadId": lead.id})

    @http.route("/x_180dc/website/v1/talent-pool", type="http", auth="public", methods=["POST"], csrf=False)
    def talent_pool(self, **kwargs):
        try:
            self._authenticate()
        except AccessDenied as error:
            return self._json_error(str(error), status=401)

        payload = self._json_payload()
        partner = self._find_or_create_partner(payload)
        candidate = self._find_or_create_candidate(payload, partner)
        partner.write(
            {
                "comment": (
                    f"Campus: {payload.get('campus')}\n"
                    f"Program: {payload.get('program')}\n"
                    f"LinkedIn: {payload.get('linkedinUrl')}\n\n"
                    f"Motivation:\n{payload.get('motivation')}"
                )
            }
        )
        return self._json_ok({"ok": True, "candidateId": candidate.id, "partnerId": partner.id})

    @http.route("/x_180dc/website/v1/apply", type="http", auth="public", methods=["POST"], csrf=False)
    def apply(self, **kwargs):
        try:
            self._authenticate()
        except AccessDenied as error:
            return self._json_error(str(error), status=401)

        payload = self._json_payload()
        job = self._find_job(payload)
        if not job:
            return self._json_error("Unknown position.", status=404)
        if not job._x_180dc_is_publicly_open():
            return self._json_error("This position is not currently open for applications.", status=409)

        partner = self._find_or_create_partner(payload)
        candidate = self._find_or_create_candidate(payload, partner)
        work_location = self._find_work_location(payload)

        applicant = request.env["hr.applicant"].sudo().search(
            [
                ("job_id", "=", job.id),
                "|",
                ("candidate_id", "=", candidate.id),
                ("email_from", "=", self._clean_value(payload, "email")),
            ],
            limit=1,
        )
        description = (
            f"Campus: {payload.get('campus')}\n"
            f"Program: {payload.get('program')}\n"
            f"LinkedIn: {payload.get('linkedinUrl')}\n\n"
            f"Motivation:\n{payload.get('motivation')}"
        )
        applicant_vals = {
            "candidate_id": candidate.id,
            "partner_id": partner.id,
            "partner_name": partner.name or self._clean_value(payload, "name"),
            "email_from": self._clean_value(payload, "email"),
            "partner_phone": self._clean_value(payload, "phone"),
            "linkedin_profile": self._clean_value(payload, "linkedinUrl"),
            "job_id": job.id,
            "applicant_notes": description,
            "x_program": self._clean_value(payload, "program"),
            "x_work_location_id": work_location.id if work_location else False,
            "x_escp_email": self._clean_value(payload, "escpEmail"),
            "x_180dc_email": self._clean_value(payload, "180dcEmail"),
        }
        if applicant:
            applicant.write({key: value for key, value in applicant_vals.items() if value})
        else:
            applicant = request.env["hr.applicant"].sudo().create(applicant_vals)

        return self._json_ok({"ok": True, "jobId": job.id, "candidateId": candidate.id, "applicantId": applicant.id})
