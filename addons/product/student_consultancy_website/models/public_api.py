from odoo import api, fields, models


class StudentConsultancyPublicAPI(models.AbstractModel):
    _name = "student.consultancy.public_api"
    _description = "Student Consultancy Public API"

    @api.model
    def _chapter_profile_payload(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "organizationName": params.get_param("student_consultancy.website.organization_name", "Student Consultancy"),
            "contactEmail": params.get_param("student_consultancy.website.contact_email", "contact@example.org"),
            "websiteUrl": params.get_param("student_consultancy.website.url", "https://example.org"),
            "tagline": params.get_param(
                "student_consultancy.website.tagline",
                "Student-led strategic consulting for mission-driven organizations.",
            ),
            "chapterProfile": params.get_param(
                "student_consultancy.website.chapter_profile",
                "A community-first student consultancy chapter.",
            ),
        }

    @api.model
    def public_payload(self):
        members = self.env["student.consultancy.member"].sudo().search(
            [
                ("active", "=", True),
                ("is_public", "=", True),
                ("visibility_consent", "=", True),
                ("profile_ready", "=", True),
            ],
            order="public_sort_order asc, name asc, id asc",
        ).filtered(lambda member: member.status in ("incoming", "active", "paused"))
        positions = self.env["student.consultancy.position"].sudo().search(
            [("active", "=", True), ("state", "=", "open"), ("is_public", "=", True)],
            order="application_deadline asc, id asc",
        )
        projects = self.env["student.consultancy.project.service"].sudo().public_projects()
        return {
            "version": "v1",
            "generatedAt": fields.Datetime.now().isoformat(),
            "chapterProfile": self._chapter_profile_payload(),
            "members": [
                {
                    "id": member.id,
                    "name": member.name,
                    "role": member.current_role_id.name or "",
                    "department": member.current_department_id.name or "",
                    "bio": member.profile_bio or member.partner_id.sc_public_bio or "",
                }
                for member in members
            ],
            "positions": [
                {
                    "id": position.id,
                    "name": position.name,
                    "department": position.department_id.name or "",
                    "role": position.target_role_id.name or "",
                    "description": position.description or "",
                    "deadline": position.application_deadline.isoformat() if position.application_deadline else None,
                }
                for position in positions
            ],
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "type": project.type_id.name or "",
                    "client": project.client_partner_id.name or "",
                    "summary": project.summary or "",
                    "visibility": project.public_visibility,
                }
                for project in projects
            ],
        }

    @api.model
    def create_application_from_payload(self, payload):
        position_id = payload.get("positionId")
        if not position_id:
            raise ValueError("positionId is required.")
        applicant_name = (payload.get("name") or "").strip()
        applicant_email = (payload.get("email") or "").strip().lower()
        if not applicant_name:
            raise ValueError("name is required.")
        if not applicant_email:
            raise ValueError("email is required.")

        try:
            normalized_position_id = int(position_id)
        except (TypeError, ValueError):
            raise ValueError("positionId must be an integer.") from None

        position = self.env["student.consultancy.position"].sudo().browse(normalized_position_id).exists()
        if not position or position.state != "open" or not position.is_public:
            raise ValueError("The selected position is not open for public applications.")

        partner = self.env["res.partner"].sudo().search([("email", "=", applicant_email)], limit=1)
        application_model = self.env["student.consultancy.application"].sudo()
        application_domain = [("position_id", "=", position.id), ("applicant_email", "=", applicant_email)]
        if partner:
            application_domain = [("position_id", "=", position.id), ("partner_id", "=", partner.id)]
        application = application_model.search(application_domain, limit=1)
        values = {
            "position_id": position.id,
            "partner_id": partner.id if partner else False,
            "applicant_name": applicant_name,
            "applicant_email": applicant_email,
            "motivation": (payload.get("motivation") or "").strip(),
            "source": "website",
        }
        if application:
            application.write(values)
            return application
        return application_model.create(values)
