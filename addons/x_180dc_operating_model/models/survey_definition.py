from odoo import api, fields, models


class X180DCSurveyDefinition(models.Model):
    _name = "x_180dc.survey.definition"
    _description = "180DC Survey Definition"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "sequence, name, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    title = fields.Char(required=True)
    question_ids = fields.One2many("x_180dc.survey.definition.question", "definition_id", string="Questions")

    _sql_constraints = [
        ("x_180dc_survey_definition_key_uniq", "unique(key)", "Survey definition key must be unique."),
    ]

    def _x_180dc_question_specs(self):
        self.ensure_one()
        return [question._x_180dc_payload() for question in self.question_ids.sorted("sequence")]


class X180DCSurveyDefinitionQuestion(models.Model):
    _name = "x_180dc.survey.definition.question"
    _description = "180DC Survey Definition Question"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "sequence, id"

    definition_id = fields.Many2one("x_180dc.survey.definition", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    key = fields.Char(required=True)
    title = fields.Text(required=True)
    description = fields.Text()
    question_type = fields.Selection(
        [
            ("text_box", "Text Box"),
            ("simple_choice", "Simple Choice"),
        ],
        default="text_box",
        required=True,
    )
    placeholder = fields.Char()
    mandatory = fields.Boolean(default=True)
    answer_ids = fields.One2many("x_180dc.survey.definition.answer", "question_id", string="Suggested Answers")

    def _x_180dc_payload(self):
        self.ensure_one()
        return {
            "key": self.key,
            "title": self.title,
            "description": self.description or False,
            "question_type": self.question_type,
            "placeholder": self.placeholder or False,
            "mandatory": bool(self.mandatory),
            "answers": [answer.value for answer in self.answer_ids.sorted("sequence")],
        }


class X180DCSurveyDefinitionAnswer(models.Model):
    _name = "x_180dc.survey.definition.answer"
    _description = "180DC Survey Definition Suggested Answer"
    _inherit = "x_180dc.admin_rule_mixin"
    _order = "sequence, id"

    question_id = fields.Many2one("x_180dc.survey.definition.question", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    value = fields.Char(required=True)
