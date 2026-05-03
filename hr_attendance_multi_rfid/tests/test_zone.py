from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_attendance_zone")
class TestAttendanceZone(TransactionCase):
    """Backend coverage for hr.rfid.zone — the existing test_functional.py
    covers the full hardware loop; this suite locks down the model
    surface that test was implicitly relying on."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.tag = cls.env["hr.employee.category"].create({
            "name": "Attendance Tag",
            "color": 1,
        })

    def _make_zone(self, name="Default Zone", attendance=True, **vals):
        return self.env["hr.rfid.zone"].create({
            "name": name,
            "company_id": self.company.id,
            "attendance": attendance,
            "permitted_employee_category_ids": [(4, self.tag.id, 0)],
            **vals,
        })

    def test_create_attendance_zone(self):
        zone = self._make_zone()
        self.assertTrue(zone.id)
        self.assertTrue(zone.attendance)
        self.assertEqual(zone.permitted_employee_category_ids, self.tag)

    def test_zone_name_is_required(self):
        from psycopg2.errors import NotNullViolation  # noqa: F401
        from odoo.tools import mute_logger
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self.env["hr.rfid.zone"].create({"company_id": self.company.id})

    def test_attendance_flag_can_be_disabled(self):
        zone = self._make_zone("Non-attendance", attendance=False)
        self.assertFalse(zone.attendance)

    def test_event_user_extension_loaded(self):
        Model = self.env["hr.rfid.event.user"]
        self.assertEqual(Model._name, "hr.rfid.event.user")
