import json

from odoo import fields
from odoo.tests.common import HttpCase, TransactionCase


class TestStudentConsultancyWebsite(TransactionCase):
    def test_payload_filters_private_records(self):
        schema = self.env["student.consultancy.cycle.schema"].create(
            {"name": "Semester", "code": "semester", "mode": "semester", "start_month": 9, "start_day": 1}
        )
        current_period = self.env["student.consultancy.cycle.service"].get_current_cycle(
            schema=schema, on_date=fields.Date.context_today(self.env.user)
        )
        department = self.env["student.consultancy.department"].create({"name": "Consulting", "code": "consulting"})
        role = self.env["student.consultancy.role"].create({"name": "Consultant", "code": "consultant"})
        public_partner = self.env["res.partner"].create({"name": "Public Member"})
        private_partner = self.env["res.partner"].create({"name": "Private Member"})
        public_member = self.env["student.consultancy.member"].create(
            {
                "partner_id": public_partner.id,
                "is_public": True,
                "visibility_consent": True,
                "profile_ready": True,
                "profile_bio": "Visible biography.",
            }
        )
        self.env["student.consultancy.membership"].create(
            {
                "member_id": public_member.id,
                "role_id": role.id,
                "department_id": department.id,
                "state": "active",
                "start_cycle_period_id": current_period.id,
                "valid_through_cycle_period_id": current_period.id,
            }
        )
        self.env["student.consultancy.member"].create({"partner_id": private_partner.id, "is_public": False})
        self.env["student.consultancy.position"].create({"name": "Open Role", "state": "open", "is_public": True})
        self.env["student.consultancy.position"].create({"name": "Private Role", "state": "open", "is_public": False})
        self.env["student.consultancy.project"].create(
            {"name": "Visible Project", "state": "active", "public_visibility": "public"}
        )
        self.env["student.consultancy.project"].create(
            {"name": "Hidden Project", "state": "active", "public_visibility": "hidden"}
        )

        payload = self.env["student.consultancy.public_api"].public_payload()

        self.assertEqual(len(payload["members"]), 1)
        self.assertEqual(len(payload["positions"]), 1)
        self.assertEqual(len(payload["projects"]), 1)

    def test_application_endpoint_logic_is_idempotent_by_position_and_email(self):
        position = self.env["student.consultancy.position"].create({"name": "Consultant", "state": "open", "is_public": True})
        api = self.env["student.consultancy.public_api"]
        first = api.create_application_from_payload(
            {"positionId": position.id, "name": "Mila", "email": "mila@example.org", "motivation": "First"}
        )
        second = api.create_application_from_payload(
            {"positionId": position.id, "name": "Mila", "email": "mila@example.org", "motivation": "Updated"}
        )

        self.assertEqual(first, second)
        self.assertEqual(second.motivation, "Updated")
        self.assertTrue(second.partner_id)
        self.assertEqual(second.partner_id.name, "Mila")
        self.assertEqual(second.partner_id.email, "mila@example.org")


class TestStudentConsultancyWebsiteHttp(HttpCase):
    def test_public_route_returns_json(self):
        response = self.url_open("/student_consultancy/v1/public")
        payload = json.loads(response.text)

        self.assertEqual(response.status_code, 200)
        self.assertIn("chapterProfile", payload)
