from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    x_180dc_template_key = fields.Char(index=True)

    def _x_180dc_sync_questions(self, questions):
        Question = self.env["survey.question"].sudo()
        Answer = self.env["survey.question.answer"].sudo()
        existing = {question.x_180dc_question_key: question for question in self.question_ids if question.x_180dc_question_key}
        seen_keys = set()
        for sequence, spec in enumerate(questions, start=1):
            key = spec["key"]
            values = {
                "survey_id": self.id,
                "x_180dc_question_key": key,
                "title": spec["title"],
                "description": spec.get("description"),
                "question_type": spec.get("question_type", "text_box"),
                "question_placeholder": spec.get("placeholder"),
                "constr_mandatory": spec.get("mandatory", True),
                "sequence": sequence * 10,
                "validation_required": spec.get("mandatory", True),
            }
            question = existing.get(key)
            if question:
                question.write(values)
            else:
                question = Question.create(values)
            desired_answers = spec.get("answers", [])
            if desired_answers:
                if [answer.value for answer in question.suggested_answer_ids] != desired_answers:
                    question.suggested_answer_ids.unlink()
                    for answer_sequence, answer_value in enumerate(desired_answers, start=1):
                        Answer.create(
                            {
                                "question_id": question.id,
                                "value": answer_value,
                                "sequence": answer_sequence * 10,
                            }
                        )
            elif question.suggested_answer_ids:
                question.suggested_answer_ids.unlink()
            seen_keys.add(key)

        obsolete_questions = self.question_ids.filtered(
            lambda question: question.x_180dc_question_key and question.x_180dc_question_key not in seen_keys
        )
        if obsolete_questions:
            obsolete_questions.unlink()

    @api.model
    def _x_180dc_ensure_survey(self, key, title, questions):
        survey = self.sudo().search([("x_180dc_template_key", "=", key)], limit=1)
        if not survey:
            survey = self.sudo().create(
                {
                    "title": title,
                    "access_mode": "token",
                    "x_180dc_template_key": key,
                }
            )
        else:
            survey.sudo().write({"title": title, "access_mode": "token"})
        survey._x_180dc_sync_questions(questions)
        return survey

    @api.model
    def _x_180dc_ensure_default_surveys(self):
        definitions = self.env["x_180dc.survey.definition"].sudo().search([("active", "=", True)], order="sequence asc, id asc")
        for definition in definitions:
            self._x_180dc_ensure_survey(definition.key, definition.title, definition._x_180dc_question_specs())


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    x_180dc_question_key = fields.Char(index=True)
