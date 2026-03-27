from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestStudentConsultancyHR(TransactionCase):
    def test_role_group_mapping_syncs_user_groups(self):
        partner = self.env["res.partner"].create({"name": "Alice", "email": "alice@example.org"})
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Alice",
                "login": "alice.hr@example.org",
                "partner_id": partner.id,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        group = self.env["res.groups"].create({"name": "Board Access"})
        role = self.env["student.consultancy.role"].create({"name": "President", "code": "president", "group_ids": [(6, 0, [group.id])]})
        department = self.env["student.consultancy.department"].create({"name": "Board", "code": "board"})
        member = self.env["student.consultancy.member"].create({"partner_id": partner.id, "user_id": user.id})

        self.env["student.consultancy.membership"].create(
            {
                "member_id": member.id,
                "role_id": role.id,
                "department_id": department.id,
                "state": "active",
                "start_date": fields.Date.context_today(self),
            }
        )

        self.assertIn(group, user.groups_id)
        self.assertEqual(member.status, "active")

    def test_member_status_tracks_membership_periods(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        schema = self.env["student.consultancy.cycle.schema"].create(
            {"name": "Semester", "code": "semester", "mode": "semester", "start_month": today.month, "start_day": 1}
        )
        current_period = self.env["student.consultancy.cycle.service"].get_current_cycle(schema=schema, on_date=today)
        role = self.env["student.consultancy.role"].create({"name": "Consultant", "code": "consultant"})
        partner = self.env["res.partner"].create({"name": "Bob", "email": "bob@example.org"})
        member = self.env["student.consultancy.member"].create({"partner_id": partner.id})
        membership = self.env["student.consultancy.membership"].create(
            {
                "member_id": member.id,
                "role_id": role.id,
                "state": "active",
                "start_cycle_period_id": current_period.id,
                "valid_through_cycle_period_id": current_period.id,
            }
        )

        self.assertEqual(member.status, "active")
        membership.action_pause()
        self.assertEqual(member.status, "paused")

        membership.write({"state": "ended", "end_date": today - timedelta(days=1)})
        self.assertEqual(member.status, "alumni")
