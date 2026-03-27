from odoo import fields
from odoo.tests.common import TransactionCase


class TestStudentConsultancyProjects(TransactionCase):
    def test_won_opportunity_creates_project(self):
        stage = self.env["crm.stage"].create({"name": "Won", "is_won": True})
        lead = self.env["crm.lead"].create({"name": "Campus Strategy", "type": "opportunity"})

        lead.write({"stage_id": stage.id})

        self.assertTrue(lead.student_consultancy_project_id)
        self.assertEqual(lead.student_consultancy_project_id.lead_id, lead)

    def test_staffing_assignment_uses_membership_eligibility(self):
        schema = self.env["student.consultancy.cycle.schema"].create(
            {"name": "Semester", "code": "semester", "mode": "semester", "start_month": 9, "start_day": 1}
        )
        current_period = self.env["student.consultancy.cycle.service"].get_current_cycle(
            schema=schema, on_date=fields.Date.context_today(self)
        )
        partner = self.env["res.partner"].create({"name": "Mila", "email": "mila@example.org"})
        member = self.env["student.consultancy.member"].create({"partner_id": partner.id})
        role = self.env["student.consultancy.role"].create({"name": "Consultant", "code": "consultant"})
        membership = self.env["student.consultancy.membership"].create(
            {
                "member_id": member.id,
                "role_id": role.id,
                "state": "active",
                "start_cycle_period_id": current_period.id,
                "valid_through_cycle_period_id": current_period.id,
            }
        )
        project = self.env["student.consultancy.project"].create({"name": "Sustainability Sprint", "state": "active"})

        assignment = self.env["student.consultancy.staffing.assignment"].create(
            {"project_id": project.id, "member_id": member.id}
        )
        assignment.action_confirm()

        self.assertEqual(assignment.membership_id, membership)
        self.assertEqual(assignment.state, "confirmed")
