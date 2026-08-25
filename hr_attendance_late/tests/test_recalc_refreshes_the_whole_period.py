# -*- coding: utf-8 -*-
"""Recalculating a period refreshes every day in it, not only the busy ones.

The operator presses Recalculate for a month and then reads the daily figures.
Rebuilding the attendance refreshes the days whose records changed - that part
has always worked - but on a real installation most days have no passage at
all, and those kept whatever an older calculation had written.

Measured on a copy of a customer database, one June, ten people: of 148 daily
rows, 82 still showed the old planned time after a full rebuild. Every one of
them was a day with nothing to replay. That is what the owner was looking at
when he said the figures were still wrong after the recalculation.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TestAttendanceLateCommon


@tagged('post_install', '-at_install', 'hr_attendance_late', 'rfid_attendance_recalc')
class TestRecalcRefreshesTheWholePeriod(TestAttendanceLateCommon):

    def _a_past_working_day(self):
        today = fields.Date.today()
        return today - timedelta(days=today.weekday() + 7)  # last Monday

    def test_a_day_with_no_passage_is_recalculated_too(self):
        """The day nobody walked through a door still gets its figures redone.

        An older calculation left 9 planned hours on it - the lunch break
        counted as work. Nothing about that day will ever change again by
        itself: no attendance record to write, no hook to fire. Pressing
        Recalculate for the period has to be enough, because it is what the
        button says.
        """
        day = self._a_past_working_day()
        stale = self.env['hr.attendance.extra'].create({
            'employee_id': self.employee.id,
            'for_date': day,
            'theoretical_work_time': 9.0,
            'actual_work_time': 0.0,
        })
        self.assertFalse(
            self.env['hr.attendance'].search_count([
                ('employee_id', '=', self.employee.id),
                ('check_in', '>=', '%s 00:00:00' % day),
                ('check_in', '<=', '%s 23:59:59' % day)]),
            "the premise: nothing happened on that day")

        self.employee.recalc_attendance(day, day)

        self.assertAlmostEqual(
            stale.theoretical_work_time, 8.0, places=2,
            msg="the planned day is eight hours - the unpaid break is not "
                "work - and the recalculation must say so even where there "
                "was nothing to replay")

    def test_the_figures_of_a_day_that_was_worked_are_redone_as_well(self):
        """NEGATIVE: the days that DO have attendance keep working.

        They were refreshed before this change, by the write hooks on the
        attendance records, and they must still be refreshed now - the new
        pass over the period must not undo what those hooks did.
        """
        day = self._a_past_working_day()
        self.create_attendance(
            self.employee,
            fields.Datetime.to_datetime('%s 08:00:00' % day),
            fields.Datetime.to_datetime('%s 17:00:00' % day),
        )

        self.employee.recalc_attendance(day, day)

        extra = self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id), ('for_date', '=', day)])
        self.assertTrue(extra)
        self.assertAlmostEqual(extra.theoretical_work_time, 8.0, places=2)
        self.assertAlmostEqual(extra.actual_work_time, 8.0, places=2,
                               msg="a full day at work measures the full day")
