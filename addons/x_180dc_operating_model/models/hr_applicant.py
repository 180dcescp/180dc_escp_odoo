from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    x_180dc_email = fields.Char(string="180DC Email")
    x_escp_email = fields.Char(string="ESCP Email")
    x_program = fields.Char(string="Program")
    x_estimated_graduation_date = fields.Date(string="Estimated Graduation Date")
    x_work_location_id = fields.Many2one("hr.work.location", string="Campus / Work Location")
    x_pl_potential = fields.Boolean(string="Project Leader Potential")
    x_application_survey_id = fields.Many2one(related="job_id.x_application_survey_id", readonly=True)
    x_case_survey_id = fields.Many2one(related="job_id.x_case_survey_id", readonly=True)
    x_second_round_survey_id = fields.Many2one(related="job_id.x_second_round_survey_id", readonly=True)

    def _x_180dc_action_send_survey(self, survey):
        self.ensure_one()
        if not survey:
            return False
        if not self.partner_id:
            partner_name = self.partner_name or self.candidate_id.partner_name or self.candidate_id.partner_id.name
            if partner_name:
                self.partner_id = self.env["res.partner"].sudo().create(
                    {
                        "is_company": False,
                        "name": partner_name,
                        "email": self.email_from,
                        "phone": self.partner_phone,
                        "mobile": self.partner_phone,
                    }
                )
        survey.check_validity()
        return {
            "type": "ir.actions.act_window",
            "name": survey.title,
            "view_mode": "form",
            "res_model": "survey.invite",
            "target": "new",
            "context": {
                "default_applicant_id": self.id,
                "default_partner_ids": self.partner_id.ids,
                "default_survey_id": survey.id,
                "default_email_layout_xmlid": "mail.mail_notification_light",
            },
        }

    def action_send_application_survey(self):
        self.ensure_one()
        return self._x_180dc_action_send_survey(self.x_application_survey_id)

    def action_send_case_survey(self):
        self.ensure_one()
        return self._x_180dc_action_send_survey(self.x_case_survey_id)

    def action_send_second_round_survey(self):
        self.ensure_one()
        return self._x_180dc_action_send_survey(self.x_second_round_survey_id)

    def create_employee_from_applicant(self):
        self.ensure_one()
        action = super().create_employee_from_applicant()
        employee = self.env["hr.employee"].browse(action["res_id"]).sudo()
        if not employee:
            return action

        employee_vals = {
            "work_email": self.x_180dc_email or employee.work_email,
            "x_escp_email": self.x_escp_email or self.email_from or employee.x_escp_email,
            "x_program": self.x_program or employee.x_program,
            "x_estimated_graduation_date": self.x_estimated_graduation_date or employee.x_estimated_graduation_date,
        }
        employee.write({key: value for key, value in employee_vals.items() if value})

        membership_type = self.env.ref("x_180dc_member_contract.x_180dc_contract_type_membership")
        current_season = self.env["x_180dc.season"]._x_180dc_current_season()
        current_contract = self.env["hr.contract"].sudo().search(
            [
                ("employee_id", "=", employee.id),
                ("contract_type_id", "=", membership_type.id),
                ("season_id", "=", current_season.id),
            ],
            limit=1,
        )
        if not current_contract:
            self.env["hr.contract"].sudo().create(
                {
                    "name": f"{employee.name} Membership {current_season.name}",
                    "employee_id": employee.id,
                    "contract_type_id": membership_type.id,
                    "department_id": self.department_id.id,
                    "job_id": self.job_id.id,
                    "x_work_location_id": self.x_work_location_id.id,
                    "season_id": current_season.id,
                    "state": "open",
                    "x_staffing_status": "staffable",
                }
            )

        employee._x_180dc_sync_membership_state()
        return action
