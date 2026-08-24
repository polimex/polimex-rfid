# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time

from odoo import fields
from .common import TestAttendanceLateCommon
import logging

_logger = logging.getLogger(__name__)


class TestAttendanceAutoClose(TestAttendanceLateCommon):
    """A forgotten check-out is settled by ONE setting, in one place.

    Settings -> Attendances -> Automatic Check-Out says WHEN: the person's own
    scheduled day plus the tolerance (8h + 4h here, so a stay is settled once
    it runs past twelve). The Forgotten Badge policy beside it says WHAT is
    then credited - here the scheduled day, eight hours.

    The zone used to carry a second pair of hours answering the same thing
    with different numbers; it no longer does.

    The day calculation is driven through the module's own test seam
    (context key attendance_calc_time) instead of mocking the clock.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.zone:
            cls.skipTest(cls, "hr.rfid.zone model not available")

    def test_a_forgotten_badge_out_is_credited_the_scheduled_day(self):
        """The payroll officer sees the scheduled day, not the whole stay.

        An employee badges in at 08:00 and never badges out. When the day is
        calculated 14 hours later - past the twelve the settings allow - the
        stay is credited their working day: eight hours of work and the unpaid
        break between them, so presence 08:00-17:00 and a day worth the eight
        hours it was supposed to hold. A settled day is worth a normal one;
        nobody has to explain why a forgotten badge costs an hour.

        Had the whole stay been counted instead, the day would have run to
        22:00 and shown five hours of overtime nobody worked.
        """
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Badge in at 08:00, never badge out
        self.create_attendance(
            self.employee,
            datetime.combine(test_date, time(8, 0)),
            None,
            self.zone,
        )

        # The day is calculated at 22:00 - 14 hours in the zone, past the max
        calc_time = datetime.combine(test_date, time(22, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time
        ).update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra, "Attendance extra should be created")
        # Presence 08:00-17:00 - the working day from the moment they came -
        # against the 08:00-12:00/13:00-17:00 schedule = 8h of work.
        self.assertAlmostEqual(
            attendance_extra.actual_work_time, 8.0, 1,
            "a settled stay is worth the working day, never the whole time "
            "the badge stood open")
        self.assertAlmostEqual(
            attendance_extra.overtime, 0.0, 1,
            "and an administrative close earns nobody overtime")

    def test_a_company_that_counts_nothing_gets_nothing_counted(self):
        """The other policy, where it shows: on the payroll report.

        Some companies want a forgotten badge to cost the whole day, so the
        person has to come and say why they forgot. With that setting the day
        measures no work at all - not a settled eight hours - and somebody has
        to type the real times in.
        """
        self.company.write({'forgotten_badge_policy': 'ignore'})
        # A day already past: an absence is only recorded for a day that has
        # been and gone, never for one still ahead.
        today = fields.Date.today()
        test_date = today - timedelta(days=today.weekday() + 7)  # last Monday
        self.create_attendance(
            self.employee,
            datetime.combine(test_date, time(8, 0)),
            None,
            self.zone,
        )

        calc_time = datetime.combine(test_date, time(22, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time,
        ).update_extra_attendance_data(test_date, overwrite_existing=True)

        extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])
        self.assertTrue(extra, "the day must be recorded, not skipped")
        self.assertAlmostEqual(
            extra.actual_work_time, 0.0, 1,
            "the company counts nothing for a forgotten badge")
        self.assertAlmostEqual(
            extra.theoretical_work_time, 8.0, 1,
            "and the day still says what they were supposed to work, so the "
            "gap is visible instead of silent")

    def test_auto_close_does_not_fire_within_max_time(self):
        """A person still at work is measured up to now, not settled early.

        The same employee badges in at 08:00; the day is calculated at 12:00,
        only 4 hours later - well within the zone's 12-hour limit. Nothing is
        auto-closed: the calculation simply counts the morning worked so far
        (4 hours), and must NOT credit the 8 auto-close hours.
        """
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        self.create_attendance(
            self.employee,
            datetime.combine(test_date, time(8, 0)),
            None,
            self.zone,
        )

        # Calculated at 12:00 - 4 hours in the zone, within the maximum
        calc_time = datetime.combine(test_date, time(12, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time
        ).update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertTrue(attendance_extra)
        # 08:00 to 12:00 - the morning worked so far, no auto-close credit
        self.assertAlmostEqual(
            attendance_extra.actual_work_time, 4.0, 1,
            "Within the zone maximum the day is measured up to the "
            "calculation moment, never settled with auto-close hours")

    def test_no_extra_record_without_attendance(self):
        """Test that no hr.attendance.extra is created without real attendance"""
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Do NOT create any attendance record

        # Try to calculate attendance extra
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        # Check that NO attendance_extra was created
        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra,
                         "No attendance.extra should be created without real attendance data")

    def test_no_extra_record_recreated_after_deletion(self):
        """Test that deleted invalid records are not recreated"""
        test_date = fields.Date.from_string('2026-11-09')  # Monday

        # Do NOT create any attendance

        # Try to calculate - should not create anything
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra, "Should not create extra without attendance")

        # Try again with overwrite=True - should still not create
        self.employee.update_extra_attendance_data(test_date, overwrite_existing=True)

        attendance_extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', test_date),
        ])

        self.assertFalse(attendance_extra,
                         "Should not recreate extra records without attendance even with overwrite")
