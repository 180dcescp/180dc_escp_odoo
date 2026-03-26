from odoo import api, fields, models


class X180DCRecruitmentProfile(models.Model):
    _name = "x_180dc.recruitment_profile"
    _description = "180DC Recruitment Profile"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "sequence, name, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    recruitment_owner_scope = fields.Selection(
        [
            ("people_ops", "People & Organisation"),
            ("consulting", "Consulting Department"),
            ("head_of_department", "Head of Department"),
            ("presidency", "Presidency"),
        ],
        required=True,
    )
    second_round_owner_scope = fields.Selection(
        [
            ("none", "No Second Round Owner"),
            ("consulting", "Consulting Department"),
        ],
        required=True,
        default="none",
    )
    application_title_template = fields.Char(required=True)
    interview_title_template = fields.Char(required=True)
    case_title_template = fields.Char(required=True)
    second_round_title_template = fields.Char(required=True)
    essay_question_1_template = fields.Text()
    essay_question_2_template = fields.Text()
    essay_question_3_template = fields.Text()
    personal_fit_prompt_template = fields.Text(required=True)
    case_study_prompt_template = fields.Text(required=True)
    second_round_prompt_template = fields.Text(required=True)
    job_ids = fields.One2many("hr.job", "x_recruitment_profile_id", string="Jobs")

    _sql_constraints = [
        ("x_180dc_recruitment_profile_key_uniq", "unique(key)", "Recruitment profile key must be unique."),
    ]

    def _x_180dc_render(self, template, role_name):
        self.ensure_one()
        return (template or "").format(role_name=role_name or "Applicant").strip()

    def _x_180dc_job_survey_specs(self, job):
        self.ensure_one()
        role_name = job.name or "Applicant"
        questions = []
        for index, field_name in enumerate(
            ("x_application_question_1", "x_application_question_2", "x_application_question_3"),
            start=1,
        ):
            prompt = (job[field_name] or "").strip()
            if not prompt:
                prompt = self._x_180dc_render(getattr(self, f"essay_question_{index}_template"), role_name)
            if prompt:
                questions.append({"key": f"essay_{index}", "title": prompt})
        return {
            "application": {
                "title": (job.x_application_survey_title or self._x_180dc_render(self.application_title_template, role_name)),
                "questions": questions,
            },
            "interview": {
                "title": (job.x_interview_survey_title or self._x_180dc_render(self.interview_title_template, role_name)),
                "questions": [
                    {
                        "key": "personal_fit",
                        "title": (
                            job.x_personal_fit_prompt
                            or self._x_180dc_render(self.personal_fit_prompt_template, role_name)
                        ),
                    }
                ],
            },
            "case": {
                "title": (job.x_case_survey_title or self._x_180dc_render(self.case_title_template, role_name)),
                "questions": [
                    {
                        "key": "case_study",
                        "title": (
                            job.x_case_study_prompt
                            or self._x_180dc_render(self.case_study_prompt_template, role_name)
                        ),
                    }
                ],
            },
            "second_round": {
                "title": (
                    job.x_second_round_survey_title or self._x_180dc_render(self.second_round_title_template, role_name)
                ),
                "questions": [
                    {
                        "key": "second_round",
                        "title": (
                            job.x_second_round_prompt
                            or self._x_180dc_render(self.second_round_prompt_template, role_name)
                        ),
                    }
                ],
            },
        }

    @api.model
    def _x_180dc_seed_default_profiles(self):
        specs = [
            {
                "key": "presidency_led_recruitment",
                "name": "Presidency-led Recruitment",
                "sequence": 10,
                "recruitment_owner_scope": "presidency",
                "second_round_owner_scope": "none",
                "application_title_template": "{role_name} Application Essay",
                "interview_title_template": "{role_name} Interview - Personal Fit",
                "case_title_template": "{role_name} Interview - Case Study",
                "second_round_title_template": "{role_name} Second Round - Leadership Potential",
                "essay_question_1_template": "Why do you want to join 180DC as {role_name}?",
                "essay_question_2_template": "Describe a leadership situation where you had to align people around a clear direction.",
                "essay_question_3_template": "What operating change would you drive first in this role?",
                "personal_fit_prompt_template": "Capture the personal fit discussion points for {role_name}.",
                "case_study_prompt_template": "Capture the case study observations for {role_name}.",
                "second_round_prompt_template": "Capture leadership-potential observations for {role_name}.",
            },
            {
                "key": "head_owned_recruitment",
                "name": "Head-owned Recruitment",
                "sequence": 20,
                "recruitment_owner_scope": "head_of_department",
                "second_round_owner_scope": "none",
                "application_title_template": "{role_name} Application Essay",
                "interview_title_template": "{role_name} Interview - Personal Fit",
                "case_title_template": "{role_name} Interview - Case Study",
                "second_round_title_template": "{role_name} Second Round - Functional Leadership",
                "essay_question_1_template": "Why do you want to take on the {role_name} role at 180DC?",
                "essay_question_2_template": "Describe how you would raise the bar in the function you want to join.",
                "essay_question_3_template": "What kind of team environment do you want to help build?",
                "personal_fit_prompt_template": "Capture the personal fit discussion points for {role_name}.",
                "case_study_prompt_template": "Capture the case study observations for {role_name}.",
                "second_round_prompt_template": "Capture second-round observations for {role_name}.",
            },
            {
                "key": "consulting_led_recruitment",
                "name": "Consulting-led Recruitment",
                "sequence": 30,
                "recruitment_owner_scope": "consulting",
                "second_round_owner_scope": "none",
                "application_title_template": "{role_name} Application Essay",
                "interview_title_template": "{role_name} Interview - Personal Fit",
                "case_title_template": "{role_name} Interview - Case Study",
                "second_round_title_template": "{role_name} Second Round - PL Potential",
                "essay_question_1_template": "Why do you want to join 180DC as {role_name}?",
                "essay_question_2_template": "Describe a project or initiative where you created meaningful impact.",
                "essay_question_3_template": "",
                "personal_fit_prompt_template": "Capture the personal fit discussion points for {role_name}.",
                "case_study_prompt_template": "Capture the case study observations for {role_name}.",
                "second_round_prompt_template": "Capture Project Leader potential observations.",
            },
            {
                "key": "people_ops_recruitment",
                "name": "People & Organisation Recruitment",
                "sequence": 40,
                "recruitment_owner_scope": "people_ops",
                "second_round_owner_scope": "none",
                "application_title_template": "{role_name} Application Essay",
                "interview_title_template": "{role_name} Interview - Personal Fit",
                "case_title_template": "{role_name} Interview - Case Study",
                "second_round_title_template": "{role_name} Second Round - PL Potential",
                "essay_question_1_template": "Why do you want to join 180DC as {role_name}?",
                "essay_question_2_template": "Describe a project or initiative where you created meaningful impact.",
                "essay_question_3_template": "",
                "personal_fit_prompt_template": "Capture the personal fit discussion points for {role_name}.",
                "case_study_prompt_template": "Capture the case study observations for {role_name}.",
                "second_round_prompt_template": "Capture Project Leader potential observations.",
            },
            {
                "key": "consultant_pipeline",
                "name": "Consultant Pipeline",
                "sequence": 50,
                "recruitment_owner_scope": "people_ops",
                "second_round_owner_scope": "consulting",
                "application_title_template": "{role_name} Application Essay",
                "interview_title_template": "{role_name} Interview - Personal Fit",
                "case_title_template": "{role_name} Interview - Case Study",
                "second_round_title_template": "{role_name} Second Round - PL Potential",
                "essay_question_1_template": "Why do you want to join 180DC as {role_name}?",
                "essay_question_2_template": "Describe a project or initiative where you created meaningful impact.",
                "essay_question_3_template": "",
                "personal_fit_prompt_template": "Capture the personal fit discussion points for {role_name}.",
                "case_study_prompt_template": "Capture the case study observations for {role_name}.",
                "second_round_prompt_template": "Capture Project Leader potential observations.",
            },
        ]
        for spec in specs:
            profile = self.sudo().search([("key", "=", spec["key"])], limit=1)
            if profile:
                profile.write(spec)
            else:
                self.sudo().create(spec)

