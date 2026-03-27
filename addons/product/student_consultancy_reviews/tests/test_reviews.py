from odoo.tests.common import TransactionCase


class TestStudentConsultancyReviews(TransactionCase):
    def test_review_assignment_tracks_lifecycle_and_scope(self):
        partner_a = self.env["res.partner"].create({"name": "Alice"})
        partner_b = self.env["res.partner"].create({"name": "Bob"})
        member_a = self.env["student.consultancy.member"].create({"partner_id": partner_a.id})
        member_b = self.env["student.consultancy.member"].create({"partner_id": partner_b.id})
        template = self.env["student.consultancy.review.template"].create(
            {"name": "Project Feedback", "scope": "project", "prompt": "Share actionable feedback."}
        )
        project = self.env["student.consultancy.project"].create({"name": "Visible Project", "state": "active"})

        assignment = self.env["student.consultancy.review.assignment"].create(
            {
                "name": "Alice by Bob",
                "template_id": template.id,
                "subject_member_id": member_a.id,
                "reviewer_member_id": member_b.id,
                "project_id": project.id,
            }
        )

        self.assertEqual(assignment.state, "draft")
        assignment.action_mark_sent()
        assignment.action_start()
        assignment.action_mark_done()
        self.assertEqual(assignment.state, "done")
        self.assertEqual(assignment.project_id, project)
