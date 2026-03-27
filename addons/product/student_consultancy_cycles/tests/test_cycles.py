from odoo.tests.common import TransactionCase


class TestStudentConsultancyCycles(TransactionCase):
    def test_cycle_resolution_supports_all_modes(self):
        service = self.env["student.consultancy.cycle.service"]
        expectations = {
            "semester": "S2 2025-2026",
            "trimester": "T2 2025-2026",
            "quarter": "Q3 2025-2026",
        }

        for mode, expected_name in expectations.items():
            schema = self.env["student.consultancy.cycle.schema"].create(
                {"name": mode.title(), "code": mode, "mode": mode, "start_month": 9, "start_day": 1}
            )
            current = service.get_cycle_for_date(target_date="2026-03-27", schema=schema)
            self.assertEqual(current.name, expected_name)

    def test_next_cycle_resolution_moves_across_cycle_boundaries(self):
        schema = self.env["student.consultancy.cycle.schema"].create(
            {"name": "Semester", "code": "semester", "mode": "semester", "start_month": 9, "start_day": 1}
        )
        service = self.env["student.consultancy.cycle.service"]

        current = service.get_cycle_for_date(target_date="2026-03-27", schema=schema)
        next_period = service.get_next_cycle(current)
        valid_through = service.get_valid_through_cycle(current, step_count=1)

        self.assertEqual(next_period.name, "S1 2026-2027")
        self.assertEqual(valid_through, next_period)
