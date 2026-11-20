# Polimex Holding Ltd. - https://polimex.co
"""The exit of a stay says who made it.

An operator reading an attendance sees how it began and how it ended. Core
writes that for each of its own channels (kiosk, systray, a time typed in the
form). A badge at the door is one more channel: a stay the door closed reads
"RFID" at its exit, and a check-out somebody typed afterwards reads "Manual"
again. Without it every badge-out read as if a person had typed it.
"""

import importlib.util
from datetime import timedelta

from odoo.tests.common import tagged
from odoo.tools.misc import file_path

from .test_why_not_counted import AZoneThatCountsAttendance


@tagged("post_install", "-at_install", "rfid_attendance_zone", "rfid_exit_mode")
class TestTheExitSaysWhoMadeIt(AZoneThatCountsAttendance):
    def _a_day_by_badge(self):
        self._passage(self.reader_in, self.morning)
        self._passage(self.reader_out, self.morning + timedelta(hours=8))
        return self._attendance_of()

    def test_a_badge_at_the_exit_reads_rfid(self):
        stay = self._a_day_by_badge()

        self.assertEqual(stay.check_out, self.morning + timedelta(hours=8))
        self.assertEqual((stay.in_mode, stay.out_mode), ("rfid", "rfid"))

    def test_a_stay_still_open_has_no_exit_by_badge(self):
        self._passage(self.reader_in, self.morning)

        self.assertFalse(self._attendance_of().check_out)
        self.assertEqual(self._attendance_of().out_mode, "manual")

    def test_the_last_exit_of_the_day_reads_rfid(self):
        """A zone that takes the last exit moves the check-out by badge."""
        self.zone.overwrite_check_out = True
        self._a_day_by_badge()
        last = self._passage(
            self.reader_out, self.morning + timedelta(hours=8, minutes=30)
        )

        self.assertEqual(self._attendance_of().check_out, last.event_time)
        self.assertEqual(self._attendance_of().out_mode, "rfid")

    def test_a_rebuilt_day_reads_rfid_too(self):
        self._a_day_by_badge()

        self._rebuild()

        stay = self._attendance_of()
        self.assertEqual(len(stay), 1)
        self.assertEqual((stay.in_mode, stay.out_mode), ("rfid", "rfid"))

    def test_a_check_out_somebody_typed_reads_manual(self):
        stay = self._a_day_by_badge()

        stay.write({"check_out": self.morning + timedelta(hours=9)})

        self.assertEqual((stay.in_mode, stay.out_mode), ("manual", "manual"))

    def test_the_kiosk_keeps_its_own_name(self):
        """Core's channels say who they are; the badge does not speak for them."""
        self._passage(self.reader_in, self.morning)
        stay = self._attendance_of()

        stay.write(
            {"check_out": self.morning + timedelta(hours=8), "out_mode": "kiosk"}
        )

        self.assertEqual(stay.out_mode, "kiosk")

    def test_a_forgotten_badge_keeps_its_automatic_exit(self):
        """A stay the system closed for a forgotten badge was not closed at a
        door, and does not read as if it were."""
        self._passage(self.reader_in, self.morning)
        stay = self._attendance_of()

        stay.autoclose_attendance()

        self.assertTrue(stay.check_out)
        self.assertEqual(stay.out_mode, "auto_check_out")

    def test_a_badge_shows_no_empty_device_details(self):
        """Where device tracking is on, core shows the browser, the address
        and the position of an entry made from a device. A door has none, so
        a badge hides them as core's manual entry does."""
        from lxml import etree

        arch = etree.fromstring(
            self.env["hr.attendance"].get_view(view_type="form")["arch"]
        )

        def hidden_when(xpath):
            return arch.xpath(xpath)[0].get("invisible")

        for field in ("in_ip_address", "in_browser"):
            self.assertIn("'rfid'", hidden_when(f"//field[@name='{field}']"))
        for field in ("out_ip_address", "out_browser"):
            self.assertIn(
                "out_mode == 'rfid'", hidden_when(f"//field[@name='{field}']")
            )
        self.assertIn(
            "in_mode in ('manual', 'rfid')",
            hidden_when("//field[@name='in_location']/.."),
        )
        self.assertIn(
            "out_mode in ('manual', 'rfid')",
            hidden_when("//field[@name='out_location']/.."),
        )

    def test_the_upgrade_marks_the_stays_the_door_closed(self):
        """Stays written before the mark existed: the ones the door closed
        get it, the ones a person or the system closed keep theirs."""
        Attendance = self.env["hr.attendance"].with_context(no_validity_check=True)
        day = self.morning - timedelta(days=10)

        def stay(shift, **vals):
            start = day + timedelta(days=shift)
            return Attendance.create(
                {
                    "employee_id": self.employee.id,
                    "check_in": start,
                    "check_out": start + timedelta(hours=8),
                    **vals,
                }
            )

        by_badge = stay(0, in_mode="rfid")
        typed = stay(1, in_mode="manual")
        kiosk = stay(2, in_mode="kiosk", out_mode="kiosk")
        forgotten = stay(3, in_mode="rfid", out_mode="auto_check_out")
        still_inside = Attendance.create(
            {
                "employee_id": self.employee.id,
                "check_in": day + timedelta(days=4),
                "in_mode": "rfid",
            }
        )
        everything = by_badge | typed | kiosk | forgotten | still_inside
        # As the database held them before this version.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_attendance SET out_mode = 'manual' WHERE id IN %s",
            [tuple((by_badge | typed | still_inside).ids)],
        )
        self.env.invalidate_all()

        path = file_path(
            "hr_attendance_multi_rfid/migrations/19.0.1.6.4/post-migrate.py"
        )
        spec = importlib.util.spec_from_file_location("exit_mode_upgrade", path)
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        script.migrate(self.env.cr, "19.0.1.6.3")
        self.env.invalidate_all()

        self.assertEqual(
            everything.mapped("out_mode"),
            ["rfid", "manual", "kiosk", "auto_check_out", "manual"],
        )
