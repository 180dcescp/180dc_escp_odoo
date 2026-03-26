from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    x_recruitment_profile_id = fields.Many2one("x_180dc.recruitment_profile", string="Recruitment Profile", ondelete="restrict")
    x_recruitment_owner_scope = fields.Selection(
        [
            ("people_ops", "People & Organisation"),
            ("consulting", "Consulting Department"),
            ("head_of_department", "Head of Department"),
            ("presidency", "Presidency"),
        ],
        string="Recruitment Owner",
    )
    x_second_round_owner_scope = fields.Selection(
        [
            ("none", "No Second Round Owner"),
            ("consulting", "Consulting Department"),
        ],
        string="Second Round Owner",
        default="none",
    )
    x_application_survey_id = fields.Many2one("survey.survey", string="Application Essay Survey", ondelete="set null")
    x_case_survey_id = fields.Many2one("survey.survey", string="Case Study Survey", ondelete="set null")
    x_second_round_survey_id = fields.Many2one("survey.survey", string="Second Round Survey", ondelete="set null")
    x_application_survey_title = fields.Char(string="Application Essay Survey Title")
    x_interview_survey_title = fields.Char(string="Personal Fit Survey Title")
    x_case_survey_title = fields.Char(string="Case Study Survey Title")
    x_second_round_survey_title = fields.Char(string="Second Round Survey Title")
    x_application_question_1 = fields.Text(string="Essay Question 1")
    x_application_question_2 = fields.Text(string="Essay Question 2")
    x_application_question_3 = fields.Text(string="Essay Question 3")
    x_personal_fit_prompt = fields.Text(string="Personal Fit Interview Prompt")
    x_case_study_prompt = fields.Text(string="Case Study Prompt")
    x_second_round_prompt = fields.Text(string="Second Round Prompt")

    def _x_180dc_ensure_job_surveys(self):
        Survey = self.env["survey.survey"]
        for job in self:
            profile = job.x_recruitment_profile_id
            if not profile:
                continue
            specs = profile._x_180dc_job_survey_specs(job)
            application_survey = Survey._x_180dc_ensure_survey(
                f"180dc_job_{job.id}_application",
                specs["application"]["title"],
                specs["application"]["questions"],
            )
            interview_survey = Survey._x_180dc_ensure_survey(
                f"180dc_job_{job.id}_interview",
                specs["interview"]["title"],
                specs["interview"]["questions"],
            )
            case_survey = Survey._x_180dc_ensure_survey(
                f"180dc_job_{job.id}_case",
                specs["case"]["title"],
                specs["case"]["questions"],
            )
            second_round_survey = Survey._x_180dc_ensure_survey(
                f"180dc_job_{job.id}_second_round",
                specs["second_round"]["title"],
                specs["second_round"]["questions"],
            )
            updates = {}
            if job.x_application_survey_id != application_survey:
                updates["x_application_survey_id"] = application_survey.id
            if job.survey_id != interview_survey:
                updates["survey_id"] = interview_survey.id
            if job.x_case_survey_id != case_survey:
                updates["x_case_survey_id"] = case_survey.id
            if job.x_second_round_survey_id != second_round_survey:
                updates["x_second_round_survey_id"] = second_round_survey.id
            if job.x_recruitment_owner_scope != profile.recruitment_owner_scope:
                updates["x_recruitment_owner_scope"] = profile.recruitment_owner_scope
            if job.x_second_round_owner_scope != profile.second_round_owner_scope:
                updates["x_second_round_owner_scope"] = profile.second_round_owner_scope
            if updates:
                super(HrJob, job).write(updates)

    @api.model
    def _x_180dc_backfill_job_surveys(self):
        self.search([])._x_180dc_ensure_job_surveys()

    @api.model_create_multi
    def create(self, vals_list):
        jobs = super().create(vals_list)
        jobs._x_180dc_ensure_job_surveys()
        return jobs

    def write(self, vals):
        res = super().write(vals)
        if {
            "name",
            "x_recruitment_profile_id",
            "x_application_survey_title",
            "x_interview_survey_title",
            "x_case_survey_title",
            "x_second_round_survey_title",
            "x_application_question_1",
            "x_application_question_2",
            "x_application_question_3",
            "x_personal_fit_prompt",
            "x_case_study_prompt",
            "x_second_round_prompt",
        } & set(vals):
            self._x_180dc_ensure_job_surveys()
        return res

    @api.model
    def _x_180dc_seed_recruitment_profiles_on_jobs(self):
        Profile = self.env["x_180dc.recruitment_profile"].sudo()
        for job in self.sudo().search([]):
            if job.x_recruitment_profile_id:
                continue
            profile_key = "people_ops_recruitment"
            if (job.name or "").strip() in {"President", "Vice-President", "Head of"}:
                profile_key = "presidency_led_recruitment"
            elif (job.name or "").strip() == "Associate Director":
                profile_key = "head_owned_recruitment"
            elif (job.name or "").strip() == "Project Leader":
                profile_key = "consulting_led_recruitment"
            elif (job.name or "").strip() in {"Consultant", "Senior Consultant"}:
                profile_key = "consultant_pipeline"
            profile = Profile.search([("key", "=", profile_key)], limit=1)
            if profile:
                job.write({"x_recruitment_profile_id": profile.id})
