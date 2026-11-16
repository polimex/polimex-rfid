"""A stay nobody badged out of earns no overtime.

The complaint, from the technician who shows the system to customers
(16.11.2026), on a day somebody came in late and never badged out: "in spite
of the missed badge and in spite of being late - two faults in one day - the
employee gets overtime."

The end of such a stay is the system's own estimate. Where it falls after the
schedule, the hours past it are an estimate too, and nobody is paid a premium
for an estimate. The owner's decision the same day: an automatically closed
day gives no overtime - not for whoever came in late, and not for whoever came
in after their schedule had ended.

What a person badged out of, or an operator entered by hand, is a fact and
keeps every hour of its overtime.
"""

from datetime import datetime, time, timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TestAttendanceLateCommon

LATE_BY = 67 / 60
DAY_FIGURES = [
    "theoretical_work_time",
    "actual_work_time",
    "late_time",
    "early_come_time",
    "early_leave_time",
    "overtime",
    "overtime_night",
    "extra_time",
    "first_in",
    "last_out",
]


@tagged("post_install", "-at_install", "hr_attendance_late", "rfid_forgotten_day")
class TestAForgottenBadgeEarnsNoOvertime(TestAttendanceLateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The schedule is read on the person's own clock; the tests say which.
        cls.employee.tz = "UTC"
        cls.monday = fields.Date.from_string("2026-11-09")
        cls.tuesday_noon = datetime.combine(cls.monday + timedelta(days=1), time(12, 0))

    def at(self, hour, minute=0):
        return datetime.combine(self.monday, time(hour, minute))

    def _in(self, moment, out=None, employee=None):
        return self.create_attendance(employee or self.employee, moment, out, self.zone)

    def _settle(self, stay):
        """The stay is closed the way the scheduled task closes it, judged the next day at noon."""
        stay._at_new_entry(self.tuesday_noon).autoclose_attendance()
        self.assertTrue(stay.forgotten_badge)

    def _figures_of_monday(self, employee=None):
        employee = employee or self.employee
        employee.with_context(
            attendance_calc_time=self.tuesday_noon
        ).update_extra_attendance_data(self.monday, overwrite_existing=True)
        return self.env["hr.attendance.extra"].search(
            [("employee_id", "=", employee.id), ("for_date", "=", self.monday)]
        )

    def _a_stay_the_doors_made(self, start, stop):
        """A closed record born of door passages, not typed in by anybody."""
        return (
            self.env["hr.attendance"]
            .with_context(no_validity_check=True)
            .create(
                {
                    "employee_id": self.employee.id,
                    "check_in": start,
                    "check_out": stop,
                    "in_mode": "rfid",
                }
            )
        )

    def test_late_and_forgetful_gets_no_overtime(self):
        """In at 09:07, never out: late by an hour and seven minutes, and that is all.

        The day ends with the schedule at five. The lateness stays on the
        record, the hours actually inside the schedule are counted, and there
        is no overtime to pay for the badge that was forgotten.
        """
        self._in(self.at(9, 7))

        figures = self._figures_of_monday()

        self.assertAlmostEqual(figures.late_time, LATE_BY, 2)
        self.assertAlmostEqual(figures.actual_work_time, 8.0 - LATE_BY, 2)
        self.assertAlmostEqual(figures.overtime, 0.0, 2)
        self.assertAlmostEqual(figures.overtime_night, 0.0, 2)
        self.assertAlmostEqual(figures.early_leave_time, 0.0, 2)

    def test_the_same_day_once_the_sweep_has_closed_the_record(self):
        """The record settled and marked reads exactly as it did while still open."""
        stay = self._in(self.at(9, 7))
        while_open = self._figures_of_monday().read(DAY_FIGURES)[0]
        self._settle(stay)
        self.assertEqual(stay.check_out, self.at(17))

        figures = self._figures_of_monday()

        self.assertEqual(figures.read(DAY_FIGURES)[0], while_open)
        self.assertAlmostEqual(figures.late_time, LATE_BY, 2)
        self.assertAlmostEqual(figures.actual_work_time, 8.0 - LATE_BY, 2)
        self.assertAlmostEqual(figures.overtime, 0.0, 2)

    def test_the_evening_nobody_badged_out_of_earns_no_overtime(self):
        """In at seven in the evening, after the schedule, never out.

        The stay is still credited a working day from the arrival, so it can
        be found and corrected - but every hour of it lies after the schedule,
        and none of them is overtime until somebody says when the person left.
        """
        stay = self._in(self.at(19))
        self._settle(stay)
        self.assertEqual(stay.check_out, self.at(19) + timedelta(hours=9))

        figures = self._figures_of_monday()

        self.assertTrue(figures, "the day is on the record")
        self.assertAlmostEqual(figures.overtime, 0.0, 2)
        self.assertAlmostEqual(figures.overtime_night, 0.0, 2)

    def test_overtime_somebody_badged_out_of_is_kept(self):
        """NEGATIVE: in at eight, out at seven in the evening - two hours of overtime."""
        self._in(self.at(8), self.at(19))

        figures = self._figures_of_monday()

        self.assertAlmostEqual(figures.overtime, 2.0, 2)

    def test_a_forgotten_afternoon_does_not_cost_the_evening_its_overtime(self):
        """NEGATIVE: the forgotten stay earns none; the day's other stays keep theirs.

        Morning badged in and out. Back at one, no badge-out: credited to five,
        with the schedule. Then in at six and out at eight, both badged - two
        real hours after the schedule, and they are paid as such.
        """
        self._in(self.at(8), self.at(12))
        afternoon = self._in(self.at(13))
        self._settle(afternoon)
        self.assertEqual(afternoon.check_out, self.at(17))
        self._in(self.at(18), self.at(20))

        figures = self._figures_of_monday()

        self.assertAlmostEqual(figures.actual_work_time, 8.0, 2)
        self.assertAlmostEqual(figures.overtime, 2.0, 2)

    def test_the_hours_an_operator_enters_earn_their_overtime(self):
        """NEGATIVE: the operator types the real check-out - seven in the evening.

        That is somebody's word on when the person left, no longer the
        system's estimate: two hours of overtime, and still late that morning.
        """
        stay = self._in(self.at(9, 7))
        self._settle(stay)
        self.assertAlmostEqual(self._figures_of_monday().overtime, 0.0, 2)

        stay.check_out = self.at(19)

        figures = self._figures_of_monday()
        self.assertFalse(stay.forgotten_badge)
        self.assertAlmostEqual(figures.overtime, 2.0, 2)
        self.assertAlmostEqual(figures.late_time, LATE_BY, 2)

    def test_the_evening_still_open_earns_no_overtime_either(self):
        """In at seven in the evening, never out, and the task has not come round yet.

        The figures of the day are asked for the next noon. The stay is long
        past anything the schedule allows, so it is measured as the task will
        close it - and its hours after the schedule are no overtime.
        """
        self._in(self.at(19))

        figures = self._figures_of_monday()

        self.assertAlmostEqual(figures.overtime, 0.0, 2)
        self.assertAlmostEqual(figures.overtime_night, 0.0, 2)

    def test_a_badge_the_next_morning_does_not_turn_the_night_into_overtime(self):
        """In at 09:07, no badge-out; the next morning's passage closes the record at eight.

        Nearly a day on the record, and nobody was there for it. The day is
        measured to the end of the schedule: late by 1:07, 6:53 worked, no
        overtime - before the task has put the record itself right.
        """
        self._a_stay_the_doors_made(
            self.at(9, 7),
            datetime.combine(self.monday + timedelta(days=1), time(8, 0)),
        )

        figures = self._figures_of_monday()

        self.assertAlmostEqual(figures.late_time, LATE_BY, 2)
        self.assertAlmostEqual(figures.actual_work_time, 8.0 - LATE_BY, 2)
        self.assertAlmostEqual(figures.overtime, 0.0, 2)

    def test_a_day_settled_before_the_rule_reads_by_the_rule_once_recomputed(self):
        """Settled while the day was counted from the arrival: 09:07 to 18:07, marked.

        The record keeps its check-out. The figures of the day, computed
        again, read it to the end of the schedule: the hour and seven minutes
        that used to show as overtime are gone, the lateness stays.
        """
        stay = self._a_stay_the_doors_made(self.at(9, 7), self.at(18, 7))
        stay.with_context(rfid_machinery_write=True).write(
            {"forgotten_badge": True, "out_mode": "auto_check_out"}
        )

        figures = self._figures_of_monday()

        self.assertEqual(stay.check_out, self.at(18, 7))
        self.assertAlmostEqual(figures.late_time, LATE_BY, 2)
        self.assertAlmostEqual(figures.actual_work_time, 8.0 - LATE_BY, 2)
        self.assertAlmostEqual(figures.overtime, 0.0, 2)

    def test_a_forgotten_night_keeps_the_hours_of_its_shift(self):
        """Ten at night to six, in at half past ten, never out: seven and a half hours.

        The night is credited to six in the morning, where the shift ends.
        Those are scheduled hours, not an estimate after the schedule, and
        every one of them stays on the row of the day the night began on.
        """
        nights = self.env["resource.calendar"].create(
            {
                "name": "Nights 22-06",
                "company_id": self.company.id,
                "tz": "UTC",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "%s %s" % (day, period),
                            "dayofweek": day,
                            "hour_from": start,
                            "hour_to": stop,
                            "day_period": period,
                        },
                    )
                    for day in "0123456"
                    for period, start, stop in (
                        ("morning", 0.0, 6.0),
                        ("afternoon", 22.0, 24.0),
                    )
                ],
            }
        )
        guard = self.env["hr.employee"].create(
            {
                "name": "Night Guard",
                "company_id": self.company.id,
                "department_id": self.department.id,
                "resource_calendar_id": nights.id,
                "tz": "UTC",
            }
        )
        night = self._in(self.at(22, 30), employee=guard)
        self._settle(night)
        self.assertEqual(
            night.check_out,
            datetime.combine(self.monday + timedelta(days=1), time(6, 0)),
        )

        figures = self._figures_of_monday(guard)

        self.assertAlmostEqual(figures.actual_work_time + figures.overtime, 7.5, 2)
