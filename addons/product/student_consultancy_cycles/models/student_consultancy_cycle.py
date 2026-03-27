from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


PERIOD_MODE_CONFIG = {
    "semester": {"count": 2, "prefix": "S", "months": 6},
    "trimester": {"count": 3, "prefix": "T", "months": 4},
    "quarter": {"count": 4, "prefix": "Q", "months": 3},
}


class StudentConsultancyCycleSchema(models.Model):
    _name = "student.consultancy.cycle.schema"
    _description = "Student Consultancy Cycle Schema"
    _order = "active desc, name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    mode = fields.Selection(
        [("semester", "Semester"), ("trimester", "Trimester"), ("quarter", "Quarter")],
        required=True,
        default="semester",
    )
    start_month = fields.Integer(required=True, default=9)
    start_day = fields.Integer(required=True, default=1)
    description = fields.Text()
    active = fields.Boolean(default=True)
    cycle_ids = fields.One2many("student.consultancy.cycle", "schema_id")

    _sql_constraints = [
        ("student_consultancy_cycle_schema_code_unique", "unique(code)", "The cycle schema code must be unique."),
    ]

    @api.constrains("start_month", "start_day")
    def _check_start_parts(self):
        for schema in self:
            if schema.start_month < 1 or schema.start_month > 12:
                raise ValidationError("Cycle schema start month must be between 1 and 12.")
            if schema.start_day < 1 or schema.start_day > 28:
                raise ValidationError("Cycle schema start day must be between 1 and 28.")

    def _mode_config(self):
        self.ensure_one()
        return PERIOD_MODE_CONFIG[self.mode]

    def _cycle_label(self, reference_year):
        self.ensure_one()
        return f"{reference_year}-{reference_year + 1}"

    def _period_label(self, reference_year, sequence):
        config = self._mode_config()
        return f"{config['prefix']}{sequence} {self._cycle_label(reference_year)}"

    def _cycle_start_for_reference_year(self, reference_year):
        self.ensure_one()
        return date(reference_year, self.start_month, self.start_day)

    def _reference_year_for_date(self, target_date):
        self.ensure_one()
        boundary = self._cycle_start_for_reference_year(target_date.year)
        return target_date.year if target_date >= boundary else target_date.year - 1

    def ensure_cycle_for_date(self, target_date):
        self.ensure_one()
        reference_year = self._reference_year_for_date(target_date)
        return self.ensure_cycle(reference_year)

    def ensure_cycle(self, reference_year):
        self.ensure_one()
        cycle = self.env["student.consultancy.cycle"].search(
            [("schema_id", "=", self.id), ("reference_year", "=", reference_year)],
            limit=1,
        )
        if cycle:
            return cycle

        config = self._mode_config()
        cycle_start = self._cycle_start_for_reference_year(reference_year)
        cycle_end = cycle_start + relativedelta(years=1, days=-1)
        cycle = self.env["student.consultancy.cycle"].create(
            {
                "schema_id": self.id,
                "reference_year": reference_year,
                "name": self._cycle_label(reference_year),
                "start_date": cycle_start,
                "end_date": cycle_end,
            }
        )
        periods = []
        for sequence in range(1, config["count"] + 1):
            period_start = cycle_start + relativedelta(months=config["months"] * (sequence - 1))
            period_end = cycle_start + relativedelta(months=config["months"] * sequence, days=-1)
            periods.append(
                {
                    "cycle_id": cycle.id,
                    "name": self._period_label(reference_year, sequence),
                    "code": f"{self.code}_{reference_year}_{sequence}",
                    "sequence": sequence,
                    "start_date": period_start,
                    "end_date": period_end,
                }
            )
        self.env["student.consultancy.cycle.period"].create(periods)
        return cycle


class StudentConsultancyCycle(models.Model):
    _name = "student.consultancy.cycle"
    _description = "Student Consultancy Cycle"
    _order = "start_date desc, id desc"

    name = fields.Char(required=True)
    schema_id = fields.Many2one("student.consultancy.cycle.schema", required=True, ondelete="cascade")
    reference_year = fields.Integer(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    active = fields.Boolean(default=True)
    period_ids = fields.One2many("student.consultancy.cycle.period", "cycle_id")

    _sql_constraints = [
        (
            "student_consultancy_cycle_reference_unique",
            "unique(schema_id, reference_year)",
            "A cycle schema can only have one generated cycle per reference year.",
        ),
    ]


class StudentConsultancyCyclePeriod(models.Model):
    _name = "student.consultancy.cycle.period"
    _description = "Student Consultancy Cycle Period"
    _order = "start_date desc, sequence asc, id desc"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    cycle_id = fields.Many2one("student.consultancy.cycle", required=True, ondelete="cascade")
    schema_id = fields.Many2one(related="cycle_id.schema_id", store=True, readonly=True)
    sequence = fields.Integer(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [("past", "Past"), ("current", "Current"), ("future", "Future")],
        compute="_compute_state",
    )

    _sql_constraints = [
        ("student_consultancy_cycle_period_code_unique", "unique(code)", "The cycle period code must be unique."),
    ]

    @api.depends("start_date", "end_date")
    def _compute_state(self):
        today = fields.Date.to_date(fields.Date.context_today(self))
        for period in self:
            if period.start_date and period.end_date and period.start_date <= today <= period.end_date:
                period.state = "current"
            elif period.end_date and period.end_date < today:
                period.state = "past"
            else:
                period.state = "future"

    def contains_date(self, target_date):
        self.ensure_one()
        return bool(self.start_date and self.end_date and self.start_date <= target_date <= self.end_date)


class StudentConsultancyCycleService(models.AbstractModel):
    _name = "student.consultancy.cycle.service"
    _description = "Student Consultancy Cycle Service"

    def _resolve_schema(self, schema=None):
        if schema and hasattr(schema, "_name") and schema._name == "student.consultancy.cycle.schema":
            return schema
        if schema:
            return self.env["student.consultancy.cycle.schema"].browse(schema).exists()
        return self.env["student.consultancy.cycle.schema"].search([("active", "=", True)], limit=1)

    def get_cycle_for_date(self, target_date=None, schema=None):
        schema_record = self._resolve_schema(schema)
        if not schema_record:
            return self.env["student.consultancy.cycle.period"]

        normalized_date = fields.Date.to_date(target_date or fields.Date.context_today(self))
        cycle = schema_record.ensure_cycle_for_date(normalized_date)
        return cycle.period_ids.filtered(lambda period: period.contains_date(normalized_date))[:1]

    def get_current_cycle(self, schema=None, on_date=None):
        return self.get_cycle_for_date(target_date=on_date, schema=schema)

    def get_next_cycle(self, period):
        period.ensure_one()
        next_period = self.env["student.consultancy.cycle.period"].search(
            [("schema_id", "=", period.schema_id.id), ("start_date", ">", period.start_date)],
            order="start_date asc",
            limit=1,
        )
        if next_period:
            return next_period
        next_cycle = period.schema_id.ensure_cycle(period.cycle_id.reference_year + 1)
        return next_cycle.period_ids.sorted("sequence")[:1]

    def get_valid_through_cycle(self, period, step_count=0):
        period.ensure_one()
        current = period
        for _step in range(step_count):
            current = self.get_next_cycle(current)
        return current
