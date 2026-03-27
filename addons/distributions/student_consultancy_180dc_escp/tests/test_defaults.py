from odoo.tests.common import TransactionCase


class TestStudentConsultancy180DCEscp(TransactionCase):
    def test_distribution_defaults_are_applied(self):
        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(params.get_param("student_consultancy.instance_name"), "180 Degrees Consulting ESCP")
        self.assertEqual(params.get_param("student_consultancy.website.organization_name"), "180 Degrees Consulting ESCP")

        schema = self.env.ref("student_consultancy_180dc_escp.student_consultancy_cycle_schema_escp_semester")
        self.assertEqual(schema.mode, "semester")
