from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    student_consultancy_project_id = fields.Many2one("student.consultancy.project", readonly=True)

    def _student_consultancy_should_create_project(self):
        self.ensure_one()
        return bool(self.type == "opportunity" and self.stage_id and self.stage_id.is_won and not self.student_consultancy_project_id)

    def _student_consultancy_project_vals(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id if self.partner_id else False
        return {
            "name": self.name or self.partner_name or "New Project",
            "client_partner_id": partner.id if partner else False,
            "lead_id": self.id,
            "summary": self.description,
            "start_date": fields.Date.to_date(self.date_closed) or fields.Date.context_today(self),
            "state": "active",
        }

    def _student_consultancy_create_missing_projects(self):
        project_model = self.env["student.consultancy.project"].sudo()
        for lead in self:
            if lead._student_consultancy_should_create_project():
                project = project_model.create(lead._student_consultancy_project_vals())
                lead.student_consultancy_project_id = project.id

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        leads._student_consultancy_create_missing_projects()
        return leads

    def write(self, vals):
        result = super().write(vals)
        self._student_consultancy_create_missing_projects()
        return result
