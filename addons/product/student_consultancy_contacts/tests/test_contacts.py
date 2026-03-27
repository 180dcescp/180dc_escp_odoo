from odoo.tests.common import TransactionCase


class TestStudentConsultancyContacts(TransactionCase):
    def test_partner_flags_and_kind_are_available(self):
        partner = self.env["res.partner"].create({"name": "Jane Analyst", "email": "jane@example.org"})

        partner.student_consultancy_mark_contact(is_member=True, is_applicant=True)

        self.assertEqual(partner.sc_contact_kind, "person")
        self.assertTrue(partner.sc_is_member_contact)
        self.assertTrue(partner.sc_is_applicant_contact)
