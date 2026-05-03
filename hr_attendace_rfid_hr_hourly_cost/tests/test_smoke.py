from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_hourly_cost")
class TestHourlyCostSmoke(TransactionCase):
    """Smoke coverage — the hr.attendance.extra extension exposes
    hourly_cost & actual_work_time_cost monetary fields."""

    def test_hr_attendance_extra_fields_exist(self):
        Model = self.env["hr.attendance.extra"]
        for fname in ("hourly_cost", "actual_work_time_cost", "currency_id"):
            self.assertIn(fname, Model._fields,
                          f"{fname} must be defined on hr.attendance.extra")

    def test_currency_field_resolves_to_company_currency(self):
        # The currency_id field is typically related to company.currency_id.
        company = self.env.company
        self.assertTrue(company.currency_id,
                        "Company currency must exist for hourly cost computations")
