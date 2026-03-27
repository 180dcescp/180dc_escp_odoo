from odoo import models


class StudentConsultancyMode(models.AbstractModel):
    _name = "student.consultancy.mode"
    _description = "Student Consultancy Curated Mode"

    def _hidden_group(self):
        return self.env.ref("student_consultancy_core.group_student_consultancy_hidden_app")

    def unsupported_menu_xmlids(self):
        return [
            "account.menu_finance",
            "account_accountant.menu_accounting",
            "calendar.mail_menu_calendar",
            "hr.menu_hr_root",
            "hr_payroll.menu_hr_payroll_root",
            "hr_recruitment.menu_hr_recruitment_root",
            "maintenance.menu_maintenance_root",
            "mrp.menu_mrp_root",
            "point_of_sale.menu_point_root",
            "purchase.menu_purchase_root",
            "stock.menu_stock_root",
            "survey.menu_surveys",
        ]

    def unsupported_module_names(self):
        return [
            "account",
            "account_accountant",
            "hr",
            "hr_payroll",
            "maintenance",
            "mrp",
            "point_of_sale",
            "purchase",
            "stock",
        ]

    def apply_lockdown_to_menu(self, menu):
        hidden_group = self._hidden_group()
        menu.write({"groups_id": [(6, 0, [hidden_group.id])]})
        return menu

    def apply_curated_mode(self):
        for xmlid in self.unsupported_menu_xmlids():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                self.apply_lockdown_to_menu(menu)
        return True

    def configuration_warnings(self):
        warnings = []
        company_count = self.env["res.company"].sudo().search_count([])
        if company_count > 1:
            warnings.append("Only one consultancy per Odoo instance is supported; multiple companies are configured.")

        installed_modules = self.env["ir.module.module"].sudo().search(
            [("name", "in", self.unsupported_module_names()), ("state", "=", "installed")]
        )
        if installed_modules:
            warnings.append(
                "Unsupported native apps are installed and should remain hidden unless you are deliberately operating outside the curated product mode."
            )
        return warnings
