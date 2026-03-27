from odoo import fields
from odoo.tests.common import TransactionCase


class TestStudentConsultancyRecruitment(TransactionCase):
    def test_accepted_application_creates_member_and_membership(self):
        schema = self.env["student.consultancy.cycle.schema"].create(
            {"name": "Semester", "code": "semester", "mode": "semester", "start_month": 9, "start_day": 1}
        )
        current_period = self.env["student.consultancy.cycle.service"].get_current_cycle(
            schema=schema, on_date=fields.Date.context_today(self.env.user)
        )
        department = self.env["student.consultancy.department"].create({"name": "Consulting", "code": "consulting"})
        role = self.env["student.consultancy.role"].create({"name": "Consultant", "code": "consultant"})
        position = self.env["student.consultancy.position"].create(
            {
                "name": "Consultant",
                "state": "open",
                "is_public": True,
                "department_id": department.id,
                "target_role_id": role.id,
                "cycle_period_id": current_period.id,
            }
        )
        application = self.env["student.consultancy.application"].create(
            {
                "position_id": position.id,
                "applicant_name": "Alex",
                "applicant_email": "alex@example.org",
                "motivation": "Ready to contribute.",
            }
        )

        self.assertTrue(application.partner_id)
        self.assertEqual(application.partner_id.name, "Alex")
        self.assertEqual(application.partner_id.email, "alex@example.org")

        application.action_accept()

        self.assertEqual(application.state, "accepted")
        self.assertTrue(application.converted_member_id)
        self.assertEqual(application.converted_member_id.partner_id, application.partner_id)
        self.assertEqual(application.converted_membership_id.role_id, role)
        self.assertEqual(application.converted_membership_id.department_id, department)
