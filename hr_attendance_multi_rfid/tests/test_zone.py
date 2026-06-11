from odoo import fields
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

    def test_same_second_checkout_closes_attendance(self):
        """Controller clocks have 1-second resolution: an entry and an exit on
        adjacent readers can carry the same timestamp. person_left() must
        close the open attendance even when the exit event time equals
        check_in (core allows check_out == check_in)."""
        employee = self.env["hr.employee"].create({
            "name": "Same Second Employee",
            "company_id": self.company.id,
            "category_ids": [(4, self.tag.id)],
        })
        zone = self._make_zone("Same Second Zone")
        event_time = fields.Datetime.now()
        attendance = self.env["hr.attendance"].create({
            "employee_id": employee.id,
            "check_in": event_time,
            "in_zone_id": zone.id,
        })
        # Lightweight pseudo-event: person_left() only reads event_time and
        # flags in_or_out, so no controller/door fixture is needed.
        event = self.env["hr.rfid.event.user"].new({"event_time": event_time})

        zone.person_left(employee, event)

        self.assertEqual(attendance.check_out, event_time,
                         "Same-second exit event must close the open attendance")
        self.assertEqual(event.in_or_out, "out")
        self.assertEqual(employee.attendance_state, "checked_out")
