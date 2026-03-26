from odoo import api, fields, models


class HrRecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    x_180dc_key = fields.Char(index=True)

    @api.model
    def _x_180dc_ensure_default_pipeline(self):
        Applicant = self.env["hr.applicant"].sudo()
        Candidate = self.env["hr.candidate"].sudo()
        specs = [
            ("application_form", "Application Form", 10, False, False),
            ("screening", "Screening (CV + Essay)", 20, False, False),
            ("interview_personal_fit", "Interview - Personal Fit", 30, False, False),
            ("interview_case", "Interview - Case Study", 40, False, False),
            ("second_round", "Second Round - PL Potential", 50, False, False),
            ("invitation", "Invitation", 60, False, False),
            ("accepted", "Accepted", 70, True, False),
            ("rejected", "Rejected", 80, False, True),
        ]
        canonical = self.browse()
        for key, name, sequence, hired_stage, fold in specs:
            stage = self.search([("x_180dc_key", "=", key)], limit=1)
            if not stage:
                stage = self.search([("name", "=", name)], limit=1)
            values = {
                "name": name,
                "sequence": sequence,
                "hired_stage": hired_stage,
                "fold": fold,
                "x_180dc_key": key,
            }
            if stage:
                stage.write(values)
            else:
                stage = self.create(values)
            canonical |= stage

        if not Applicant.search_count([]) and not Candidate.search_count([]):
            legacy = self.search([("id", "not in", canonical.ids)])
            if legacy:
                legacy.unlink()
