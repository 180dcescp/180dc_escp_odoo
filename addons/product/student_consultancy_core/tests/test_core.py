from odoo.tests.common import TransactionCase


class TestStudentConsultancyCore(TransactionCase):
    def test_settings_roundtrip_uses_config_parameters(self):
        settings = self.env["res.config.settings"].create(
            {
                "sc_instance_name": "Example Consulting Society",
                "sc_instance_code": "example_consulting",
            }
        )
        settings.execute()

        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(params.get_param("student_consultancy.instance_name"), "Example Consulting Society")
        self.assertEqual(params.get_param("student_consultancy.instance_code"), "example_consulting")

    def test_apply_lockdown_to_menu_adds_hidden_group(self):
        menu = self.env["ir.ui.menu"].create({"name": "Unsupported App"})
        self.env["student.consultancy.mode"].apply_lockdown_to_menu(menu)

        hidden_group = self.env.ref("student_consultancy_core.group_student_consultancy_hidden_app")
        self.assertIn(hidden_group, menu.groups_id)
