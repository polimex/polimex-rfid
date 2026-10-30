# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""Regenerating the overtime from the screen leaves every day's figures right.

Customer case, 12.10.2026: after a transfer from an older system more than half
of the closed attendances read 0 hours worked, and about a third showed regular
hours that were not worked minus overtime. The owner asked for both to be put
right without a script. Core already has the button for it - "Regenerate
overtimes" on the overtime ruleset - so these tests press THAT button and look
at what the person sees in the attendance report afterwards.

The figures come from the standard schedule, not from the code: 08:00-12:00
and 13:00-17:00, so 08:00-17:00 is 8 hours worked and 08:00-18:00 is 9 worked,
1 extra and 8 regular under a daily rule over the scheduled day.
"""
from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'rfid_attendance_figures')
class TestRegeneratePutsFiguresRight(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Core's own default schedule, made here (resource_calendar.py,
        # _get_default_attendance_ids): the shared standard one is the
        # customer's to change, and a test reading it measures the site.
        calendar = cls.env['resource.calendar'].create({
            'name': 'Standard schedule (test)',
            'tz': 'UTC',
            'attendance_ids': cls.env['resource.calendar']._get_default_attendance_ids(),
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Figures Person (test)',
            'resource_calendar_id': calendar.id,
            'tz': 'UTC',
        })
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily over schedule (test)',
        })
        cls.env['hr.attendance.overtime.rule'].create({
            'name': 'Over the scheduled day',
            'ruleset_id': cls.ruleset.id,
            'base_off': 'quantity',
            'quantity_period': 'day',
            'expected_hours_from_contract': True,
        })
        # The button regenerates from the start of the employee's version on.
        cls.employee.version_ids.write({
            'ruleset_id': cls.ruleset.id,
            'date_version': '2026-01-01',
        })

    def _attendance(self, day, start_hour, end_hour):
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 9, day, start_hour, 0, 0),
            'check_out': datetime(2026, 9, day, end_hour, 0, 0),
        })
        self.env.flush_all()
        return attendance

    def _left_by_a_transfer(self, day, start_hour, end_hour):
        """A row written the way a transfer writes it: times only, no figures."""
        self.env.flush_all()
        self.env.cr.execute(
            "INSERT INTO hr_attendance (employee_id, check_in, check_out, in_mode, date)"
            " VALUES (%s, %s, %s, 'rfid', %s) RETURNING id",
            (self.employee.id, datetime(2026, 9, day, start_hour),
             datetime(2026, 9, day, end_hour), '2026-09-%02d' % day))
        return self.env['hr.attendance'].browse(self.env.cr.fetchone()[0])

    def _figures(self, attendance):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT worked_hours, overtime_hours, expected_hours FROM hr_attendance"
            " WHERE id = %s", (attendance.id,))
        return tuple(None if value is None else round(value, 4)
                     for value in self.env.cr.fetchone())

    def test_regenerate_gives_a_transferred_day_the_hours_worked(self):
        """The payroll clerk sees the hours the person worked, not 0.

        08:00-17:00 on the standard schedule is eight hours worked (core takes
        the lunch hour off). A transfer left it at 0; one press of the button
        must bring the eight hours back.
        """
        attendance = self._left_by_a_transfer(8, 8, 17)
        self.assertIsNone(self._figures(attendance)[0],
                          "the test must start from a record with no worked hours")

        self.ruleset.action_regenerate_overtimes()

        self.assertEqual(
            self._figures(attendance), (8.0, 0.0, 8.0),
            "After regenerating, a transferred 08:00-17:00 day must read the "
            "8 hours worked - the report summed this person's month as 0")

    def test_regenerate_gives_a_transferred_long_day_its_extra_hour(self):
        """A ten-hour day reads 9 worked, 1 extra and 8 regular after the button.

        Regular hours are worked minus extra - the relation core's own column
        is defined by - and the extra hour is there for the manager to approve.
        """
        attendance = self._left_by_a_transfer(9, 8, 18)

        self.ruleset.action_regenerate_overtimes()

        self.assertEqual(self._figures(attendance), (9.0, 1.0, 8.0))

    def test_regenerate_puts_right_regular_hours_left_behind(self):
        """Hours worked right, regular hours left from an earlier calculation.

        The second shape on the customer's database. On this core the button
        corrects it even without this module, because core marks the regular
        hours since odoo/odoo 17577a1f9c6 (in 19.0 since 30.03.2026); the module marks them
        itself for the older servers a transfer often lands on, which no test
        on this tree can tell apart.
        """
        attendance = self._attendance(10, 8, 18)
        self.env.cr.execute(
            "UPDATE hr_attendance SET expected_hours = 11.0 WHERE id = %s",
            (attendance.id,))
        self.env.invalidate_all()

        self.ruleset.action_regenerate_overtimes()

        self.assertEqual(self._figures(attendance), (9.0, 1.0, 8.0))

    def test_regenerate_does_not_move_a_day_that_was_already_right(self):
        """A correct day reads exactly the same before and after the button.

        Regenerating is pressed over a whole workforce; it must put right what
        is wrong and leave everything else as it was.
        """
        attendance = self._attendance(11, 8, 18)
        before = self._figures(attendance)
        self.assertEqual(before, (9.0, 1.0, 8.0))

        self.ruleset.action_regenerate_overtimes()

        self.assertEqual(self._figures(attendance), before,
                         "Regenerating changed a day that was already right")

    def test_regenerate_reaches_only_from_the_start_of_the_version(self):
        """Before the employee's version the button does not reach - the transfer does.

        Core regenerates from the earliest version that carries the ruleset
        (hr_attendance_overtime_ruleset.py, _attendances_to_regenerate_for).
        On a transferred database the versions begin at the transfer, so the
        history before it is put right by running the transfer again, which
        is what this module's documentation and the transfer protocol say.
        If core ever reaches further, this test says those texts are stale.
        """
        self.employee.version_ids.write({'date_version': '2026-09-15'})
        before_version = self._left_by_a_transfer(8, 8, 17)
        after_version = self._left_by_a_transfer(22, 8, 17)

        self.ruleset.action_regenerate_overtimes()

        self.assertEqual(self._figures(after_version), (8.0, 0.0, 8.0))
        self.assertIsNone(
            self._figures(before_version)[0],
            "The button now reaches before the version start - the advice to "
            "run the transfer again for the history is out of date")
