# -*- coding: utf-8 -*-
"""Theoretical working time comes from the core calendar intervals.

Business oracle (owner decisions, Stage 1 / task 1b):

* A schedule of 8-12 / 12-13 lunch break / 13-17 plans EIGHT paid hours a
  day. The lunch break is unpaid and is never part of the theoretical time.
  (On the client's live database every one of the 34 956 daily rows carried
  9.0 planned hours because the break row was summed in.)
* Presence during the lunch break is not worked time: badging 08:00-17:00
  straight through the break yields 8 worked hours, not 9.
* Owner decision 1: a validated full-day leave clears the schedule - the
  day has zero planned hours and the employee is NOT a no-show.
* Owner decision 2: a global public holiday on a weekday clears the
  schedule too, and hours actually worked on it count as extra (premium)
  time so the labour-cost layer can pay them at the holiday rate.
* Agreed zone formula: an open attendance is administratively closed at
  check_in + auto_close_time_for_zone, falling back to the zone's own
  max_time_in_zone when the auto-close duration is not configured - never
  a hardcoded 8 hours.
"""
from datetime import datetime, time, timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _monday_of_last_week():
    today = fields.Date.today()
    return today - timedelta(days=today.weekday() + 7)


# A scheduled weekday far enough in the future to never collide with
# existing chronology on shared test databases (2027-03-01 is a Monday).
FUTURE_MONDAY = fields.Date.to_date('2027-03-01')


@tagged('post_install', '-at_install', 'hr_attendance_late',
        'hr_attendance_late_theoretical')
class TestTheoreticalFromCoreCalendar(TransactionCase):
    """The daily plan mirrors what the rest of Odoo calls working time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Theoretical Time Co',
        })
        # The client-shaped calendar: morning / lunch break / afternoon.
        # The break row is what used to inflate the plan from 8h to 9h.
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Lunch Break Calendar 8-12/12-13/13-17',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {
                    'name': '%s %s' % (day_name, period_name),
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                })
                for dayofweek, day_name in [
                    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
                    ('3', 'Thursday'), ('4', 'Friday'),
                ]
                for period_name, hour_from, hour_to, day_period in [
                    ('Morning', 8, 12, 'morning'),
                    ('Break', 12, 13, 'lunch'),
                    ('Afternoon', 13, 17, 'afternoon'),
                ]
            ],
        })
        # No department on purpose: zero tolerances, so every metric the
        # tests assert is the raw measurement.
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Lunch Break Worker',
            'company_id': cls.company.id,
            'resource_calendar_id': cls.calendar.id,
        })
        if 'hr.rfid.zone' in cls.env:
            cls.zone_no_autoclose = cls.env['hr.rfid.zone'].create({
                'name': 'Zone Without Auto-Close Duration',
                'company_id': cls.company.id,
                'attendance': True,
                'max_time_in_zone': 10.0,
                'auto_close_time_for_zone': 0.0,
            })
        else:
            cls.zone_no_autoclose = False

    def _extra_for(self, day):
        return self.env['hr.attendance.extra'].search([
            ('employee_id', '=', self.employee.id),
            ('for_date', '=', day),
        ])

    def _badge(self, day, hour_in, hour_out, minute_out=0, zone=None):
        vals = {
            'employee_id': self.employee.id,
            'check_in': datetime.combine(day, time(hour_in, 0)),
        }
        if hour_out is not None:
            vals['check_out'] = datetime.combine(
                day, time(hour_out, minute_out))
        if zone and 'in_zone_id' in self.env['hr.attendance']._fields:
            vals['in_zone_id'] = zone.id
        return self.env['hr.attendance'].create(vals)

    def test_lunch_break_calendar_plans_eight_hours(self):
        """The payroll clerk must see 8 planned hours on a day scheduled
        8-12 / lunch / 13-17 - the unpaid break is not planned work."""
        self._badge(FUTURE_MONDAY, 8, 17)
        self.employee.update_extra_attendance_data(
            FUTURE_MONDAY, overwrite_existing=True)
        extra = self._extra_for(FUTURE_MONDAY)
        self.assertTrue(extra)
        self.assertAlmostEqual(extra.theoretical_work_time, 8.0, places=2,
                               msg="the lunch break must not be planned time")

    def test_presence_through_lunch_is_not_worked_time(self):
        """NEGATIVE: an employee who stays on site through the lunch break
        (badge 08:00-17:00) has worked 8 hours - the break hour is neither
        worked nor overtime."""
        self._badge(FUTURE_MONDAY, 8, 17)
        self.employee.update_extra_attendance_data(
            FUTURE_MONDAY, overwrite_existing=True)
        extra = self._extra_for(FUTURE_MONDAY)
        self.assertTrue(extra)
        self.assertAlmostEqual(extra.actual_work_time, 8.0, places=2)
        self.assertLess(extra.actual_work_time, 9.0,
                        "presence during the break must not be credited")
        self.assertAlmostEqual(extra.overtime, 0.0, places=2)
        self.assertAlmostEqual(extra.late_time, 0.0, places=2)
        self.assertAlmostEqual(extra.early_leave_time, 0.0, places=2)

    def test_scheduled_day_without_badge_is_absence_of_eight_hours(self):
        """A worker who never badges on a scheduled day is an absence - and
        the absence row plans 8 hours (not 9) on the lunch-break calendar."""
        monday = _monday_of_last_week()
        self.employee.update_extra_attendance_data(
            monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra, "a no-show on a scheduled day must be recorded")
        self.assertAlmostEqual(extra.theoretical_work_time, 8.0, places=2)
        self.assertEqual(extra.actual_work_time, 0)

    def test_validated_leave_day_is_not_an_absence(self):
        """Owner decision 1: an employee on a validated full-day leave has
        zero planned hours - they are NOT counted as a no-show."""
        if 'hr.leave' not in self.env:
            self.skipTest("hr_holidays is not installed")
        monday = _monday_of_last_week()
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Unpaid Test Leave',
            'requires_allocation': False,
            'company_id': False,
            'leave_validation_type': 'hr',
        })
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': monday,
            'request_date_to': monday,
        })
        leave.action_approve()
        self.assertEqual(leave.state, 'validate')

        self.employee.update_extra_attendance_data(
            monday, monday, overwrite_existing=True)
        self.assertFalse(
            self._extra_for(monday),
            "a validated leave day must not produce an absence row")

    def test_public_holiday_weekday_zeroes_plan_and_pays_extra(self):
        """Owner decision 2: a global public holiday falling on a weekday
        clears the plan, and the hours actually worked on it count as
        extra (premium) time - never as ordinary/late/overtime hours."""
        # The holiday is bound to the working schedule, which is the shape a
        # Bulgarian installation gets (l10n_bg_hr_attendance_overtime_rates
        # generates the year that way) AND the only shape whose company is
        # decided outright: core computes company_id from the calendar, and
        # for a calendar-less holiday falls back to whichever company happens
        # to be active when the value is first read - passing company_id in
        # does nothing, the field is readonly and computed
        # (resource_calendar_leaves.py:35-37, 58-61). Measured on a customer
        # copy: a holiday created under company X landed on the ambient
        # company, and core then skipped it for X's people, so the day showed
        # a holiday on screen and still planned eight hours.
        # The calendar-less shape an operator types into Time Off -> Public
        # Holidays is covered in hr_attendace_rfid_hr_hourly_cost.
        self.env['resource.calendar.leaves'].create({
            'name': 'Test Public Holiday',
            'calendar_id': self.calendar.id,
            'resource_id': False,
            'time_type': 'leave',
            'date_from': datetime.combine(FUTURE_MONDAY, time.min),
            'date_to': datetime.combine(FUTURE_MONDAY, time.max),
        })
        self._badge(FUTURE_MONDAY, 8, 17)
        self.employee.update_extra_attendance_data(
            FUTURE_MONDAY, overwrite_existing=True)
        extra = self._extra_for(FUTURE_MONDAY)
        self.assertTrue(extra)
        self.assertAlmostEqual(extra.theoretical_work_time, 0.0, places=2,
                               msg="a public holiday plans no work")
        self.assertAlmostEqual(extra.extra_time, 9.0, places=2,
                               msg="all presence on the holiday is extra time")
        self.assertAlmostEqual(extra.actual_work_time, 0.0, places=2)
        # NEGATIVE: holiday work is never late arrival or overtime.
        self.assertAlmostEqual(extra.late_time, 0.0, places=2)
        self.assertAlmostEqual(extra.overtime, 0.0, places=2)

    def test_autoclose_falls_back_to_zone_max_time(self):
        """NEGATIVE (no hardcoded 8h): with no auto-close duration on the
        zone, a forgotten badge-out is closed at check_in + max_time_in_zone
        (10h here -> 08:00-18:00), so the day measures the full schedule
        plus one hour of overtime."""
        if not self.zone_no_autoclose:
            self.skipTest("hr_rfid zones are not installed")
        monday = _monday_of_last_week()
        self._badge(monday, 8, None, zone=self.zone_no_autoclose)
        calc_time = datetime.combine(monday, time(23, 0))
        self.employee.with_context(
            attendance_calc_time=calc_time,
        ).update_extra_attendance_data(monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra)
        # Closed at 18:00: schedule 8-12 + 13-17 fully covered (8h) and one
        # hour past the scheduled end (17-18) is overtime. A hardcoded 8h
        # close (16:00) would measure 7h worked and no overtime instead.
        self.assertAlmostEqual(extra.actual_work_time, 8.0, places=2)
        self.assertAlmostEqual(extra.overtime, 1.0, places=2)

    def test_a_technical_no_show_marker_does_not_hide_the_absence(self):
        """NEGATIVE (core coexistence): the one-second 'technical' attendance
        core's absence detection plants at midnight is bookkeeping, not
        presence. The day must still measure as an absence - not as somebody
        who came at midnight and worked nothing."""
        monday = _monday_of_last_week()
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime.combine(monday, time.min),
            'check_out': datetime.combine(monday, time(0, 0, 1)),
            'in_mode': 'technical',
            'out_mode': 'technical',
        })
        self.employee.update_extra_attendance_data(
            monday, monday, overwrite_existing=True)
        extra = self._extra_for(monday)
        self.assertTrue(extra, "the scheduled day must still produce a row")
        self.assertAlmostEqual(extra.theoretical_work_time, 8.0, places=2)
        self.assertAlmostEqual(extra.actual_work_time, 0.0, places=2,
                               msg="a technical marker is not worked time")
        self.assertAlmostEqual(
            extra.early_come_time, 0.0, places=2,
            msg="midnight bookkeeping must not read as an 8h early arrival")

    def test_a_flexible_hours_person_is_not_measured_against_a_schedule(self):
        """NEGATIVE: flexible-hours calendars plan no rows - measuring such a
        person would call every workday 'unscheduled' and bill the whole
        presence as premium extra time. No daily rows are produced for them,
        same as core's auto check-out skips them."""
        flexible = self.env['resource.calendar'].with_company(self.company).create({
            'name': 'Flexible Test Calendar',
            'company_id': self.company.id,
            'tz': 'UTC',
            'flexible_hours': True,
        })
        free_spirit = self.env['hr.employee'].create({
            'name': 'Flexible Worker',
            'company_id': self.company.id,
            'resource_calendar_id': flexible.id,
        })
        self.env['hr.attendance'].create({
            'employee_id': free_spirit.id,
            'check_in': datetime.combine(FUTURE_MONDAY, time(8, 0)),
            'check_out': datetime.combine(FUTURE_MONDAY, time(17, 0)),
        })
        free_spirit.update_extra_attendance_data(
            FUTURE_MONDAY, overwrite_existing=True)
        self.assertFalse(
            self.env['hr.attendance.extra'].search([
                ('employee_id', '=', free_spirit.id)]),
            "a flexible-hours person must not get schedule-measured rows")
