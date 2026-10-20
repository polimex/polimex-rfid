# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A transferred attendance reads the hours the person really worked.

Customer case, 12.10.2026: a transfer from an older system wrote attendance
straight into the table and nothing worked out the stored figures - more than
half of the closed attendances read 0 hours worked, and about a third showed
regular hours that were not worked minus extra, so every working-time report of the
database was wrong. These tests run the real attendance phase against a source
that really writes, then read what the payroll clerk and the manager read.

The figures come from the standard schedule, not from the code: 08:00-12:00
and 13:00-17:00, so 08:00-17:00 is 8 hours worked and 08:00-18:00 is 9 worked,
1 extra and 8 regular under a daily rule over the scheduled day.
"""
import unittest
from datetime import date, datetime
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.importers.attendance_importer import (
    ATTENDANCE_CURSOR, FIGURES_KEY, AttendanceImporter,
)
from ..models.importers.base_importer import BaseImporter
from .test_company_scope import _FakeSource

# A night stay in Sofia, as the database stores it: 00:30 to 08:30 on
# 15 September there is 21:30 on the 14th to 05:30 on the 15th in UTC.
NIGHT_STAY_IN = fields.Datetime.to_datetime("2026-09-14 21:30:00")
NIGHT_STAY_OUT = fields.Datetime.to_datetime("2026-09-15 05:30:00")


class _WritingSource(_FakeSource):
    """The in-memory source, but the rows really land in the target table.

    The shared double only records the bulk call; the defect lives exactly in
    what happens to the rows AFTER they land, so here they must land. Its read
    keeps the real contract too: the whole source comes in one page, the read
    is then finished, and a later pass of the same transfer reads nothing.
    """

    def _direct_sql_insert_tracked(self, *args, **kwargs):
        return BaseImporter._direct_sql_insert_tracked(self, *args, **kwargs)

    def _read_all(self, model, domain, fields, cursor_key, batch_size=1000):
        if self.read_is_finished(cursor_key):
            return []
        self.read_cursors[cursor_key] = self.CURSOR_FINISHED
        return self._search_read(model, domain, fields)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_attendance_hours')
class TestTransferredAttendanceHasHours(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.attendance.overtime.ruleset' not in cls.env:
            raise unittest.SkipTest("attendance is not installed on this database")
        cls.company = cls.env.company
        calendar = cls.env.ref('resource.resource_calendar_std')
        ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Daily over schedule (test)',
        })
        cls.env['hr.attendance.overtime.rule'].create({
            'name': 'Over the scheduled day',
            'ruleset_id': ruleset.id,
            'base_off': 'quantity',
            'quantity_period': 'day',
            'expected_hours_from_contract': True,
        })

        def person(name):
            employee = cls.env['hr.employee'].create({
                'name': name,
                'resource_calendar_id': calendar.id,
                'tz': 'UTC',
                'company_id': cls.company.id,
            })
            employee.version_ids.write({
                'ruleset_id': ruleset.id, 'date_version': '2026-01-01'})
            return employee

        cls.person = person('Transferred Person (test)')
        cls.second = person('Second Transferred Person (test)')
        cls.bystander = person('Not In This Transfer (test)')

    # -- the transfer --------------------------------------------------------

    def _source(self, rows=()):
        """A source holding these rows; its people known the way the product knows them.

        ``link_existing`` writes the external ID a transfer leaves on every
        person it carries - the identity the step finds people by.
        """
        source = _WritingSource(
            self.env, {101: self.company.id}, {'import_attendance': True},
            {'hr.attendance': list(rows)})
        source.link_existing('hr.employee', 77, self.person.id)
        source.link_existing('hr.employee', 78, self.second.id)
        return source

    @staticmethod
    def _row(source_id, day, start_hour, end_hour, source_person=77):
        return {
            'id': source_id,
            'employee_id': [source_person, 'Transferred Person'],
            'check_in': '2026-09-%02d %02d:00:00' % (day, start_hour),
            'check_out': '2026-09-%02d %02d:00:00' % (day, end_hour),
        }

    def _run(self, source):
        return AttendanceImporter(source).run(None)

    @staticmethod
    def _hours_line(results):
        lines = [r for r in results if r['model'] == 'Worked Hours']
        return lines[0] if len(lines) == 1 else None

    # -- what is on the database ---------------------------------------------

    def _landed(self, source, source_id):
        return self.env['hr.attendance'].browse(
            source._get_target_id('hr.attendance', source_id))

    def _left_by_an_older_transfer(self, employee, day, start_hour, end_hour):
        """A row written the way the transfer writes it: times only, no figures."""
        self.env.flush_all()
        self.env.cr.execute(
            "INSERT INTO hr_attendance (employee_id, check_in, check_out, in_mode, date)"
            " VALUES (%s, %s, %s, 'rfid', %s) RETURNING id",
            (employee.id, datetime(2026, 9, day, start_hour), datetime(2026, 9, day, end_hour),
             '2026-09-%02d' % day))
        return self.env['hr.attendance'].browse(self.env.cr.fetchone()[0])

    def _recorded_here(self, employee, day, start_hour, end_hour):
        """A day recorded on this system, its overtime worked out by core."""
        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(2026, 9, day, start_hour),
            'check_out': datetime(2026, 9, day, end_hour),
        })
        self.env.flush_all()
        return attendance

    def _figures(self, attendance):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT worked_hours, overtime_hours, expected_hours FROM hr_attendance"
            " WHERE id = %s", (attendance.id,))
        return tuple(None if value is None else round(value, 4)
                     for value in self.env.cr.fetchone())

    def _overtime_lines(self, employee):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT id, status, duration FROM hr_attendance_overtime_line"
            " WHERE employee_id = %s ORDER BY id", (employee.id,))
        return self.env.cr.fetchall()

    # -- the clerk's figures ---------------------------------------------------

    def test_a_transferred_day_reads_the_hours_worked(self):
        """08:00-17:00 reads 8 hours worked, no extra, 8 regular - not 0."""
        source = self._source([self._row(41, 8, 8, 17)])

        self._run(source)

        self.assertEqual(
            self._figures(self._landed(source, 41)), (8.0, 0.0, 8.0),
            "A transferred 08:00-17:00 day must read 8 worked, 0 extra, 8 "
            "regular - the customer's transfer left more than half of them at 0")

    def test_a_transferred_long_day_counts_its_extra_hour(self):
        """08:00-18:00 is 9 worked, 1 extra and 8 regular, as the manager approves it."""
        source = self._source([self._row(46, 9, 8, 18)])

        self._run(source)

        self.assertEqual(
            self._figures(self._landed(source, 46)), (9.0, 1.0, 8.0),
            "A transferred ten-hour day must show its hour of extra time - "
            "otherwise the overtime is neither paid nor approved")

    def test_an_earlier_transfer_is_put_right_by_the_next_one(self):
        """A database transferred by an older version gets its hours back.

        Its rows carry times and nothing else. The next transfer finds every
        such row of the people it carries, whatever its date.
        """
        left_at_zero = self._left_by_an_older_transfer(self.person, 1, 8, 17)

        self._run(self._source([self._row(42, 9, 8, 17)]))

        self.assertEqual(
            self._figures(left_at_zero), (8.0, 0.0, 8.0),
            "An attendance an earlier transfer left without hours must be "
            "worked out by the next transfer of the same person")

    def test_the_hours_are_worked_out_without_the_attendance_add_on(self):
        """The transfer does its own work; it does not lean on another module.

        The transfer module does not require the RFID attendance add-on, so
        the result must be the same with core's overtime run alone.
        """
        from odoo.addons.hr_attendance.models.hr_attendance import HrAttendance
        left_at_zero = self._left_by_an_older_transfer(self.person, 1, 8, 17)

        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          HrAttendance._update_overtime):
            self._run(self._source())

        self.assertEqual(self._figures(left_at_zero), (8.0, 0.0, 8.0))

    def test_regular_hours_that_disagree_are_put_right_and_the_decision_kept(self):
        """Regular hours left behind are corrected; the manager's refusal stays.

        The second shape on the customer's database: hours worked out, regular
        hours left from an earlier calculation. Correcting the report column
        must not undo what the manager decided about that day's overtime.
        """
        day = self._recorded_here(self.person, 2, 8, 18)
        day.action_refuse_overtime()
        lines_before = self._overtime_lines(self.person)
        self.env.cr.execute(
            "UPDATE hr_attendance SET expected_hours = 11.0 WHERE id = %s", (day.id,))
        self.env.invalidate_all()

        self._run(self._source())

        self.assertEqual(self._figures(day), (9.0, 1.0, 8.0),
                         "regular hours must be worked minus extra again")
        self.assertEqual(
            self._overtime_lines(self.person), lines_before,
            "Correcting the regular hours re-created the overtime of the day - "
            "the manager's refusal came back as a decision nobody took")

    def test_a_decided_day_between_two_transferred_days_keeps_the_decision(self):
        """Working out the days around it leaves a refused day refused.

        Core's overtime run re-creates every overtime line in the range it is
        given, and a re-created line forgets the manager's decision. A day that
        was right must never be in that range.
        """
        self._left_by_an_older_transfer(self.person, 1, 8, 17)
        decided = self._recorded_here(self.person, 2, 8, 18)
        decided.action_refuse_overtime()
        after = self._left_by_an_older_transfer(self.person, 3, 8, 18)
        lines_before = self._overtime_lines(self.person)
        self.assertEqual([status for _id, status, _d in lines_before], ['refused'])

        self._run(self._source())

        self.assertEqual(self._figures(after), (9.0, 1.0, 8.0))
        lines_after = self._overtime_lines(self.person)
        self.assertIn(
            lines_before[0], lines_after,
            "The refused overtime of 02.09 was re-created while its neighbours "
            "were worked out - the refusal is gone")

    # -- whose, and how often --------------------------------------------------

    def test_people_outside_the_transfer_are_not_touched(self):
        """A person this source did not carry keeps exactly what they had."""
        untouched = self._left_by_an_older_transfer(self.bystander, 1, 8, 17)

        self._run(self._source([self._row(43, 10, 8, 17)]))

        self.assertIsNone(
            self._figures(untouched)[0],
            "The transfer reached into the attendance of a person it does not "
            "carry - a run for one tenant must not rewrite another's records")

    def test_a_second_transfer_finds_nothing_left_to_do(self):
        """After one transfer every day holds, so the next one changes nothing."""
        rows = [self._row(44, 11, 8, 18)]
        self._run(self._source(rows))
        lines_before = self._overtime_lines(self.person)

        results = self._run(self._source(rows))

        self.assertEqual(self._overtime_lines(self.person), lines_before,
                         "a repeated transfer re-created overtime that was right")
        line = self._hours_line(results)
        self.assertTrue(line, "the protocol must say what happened to the hours")
        self.assertEqual((line['source_count'], line['status']), (0, 'done'))

    def test_the_transfer_leaves_no_message_on_each_attendance(self):
        """Working out the hours does not write thousands of history entries."""
        left_at_zero = self._left_by_an_older_transfer(self.person, 1, 8, 18)

        self._run(self._source())

        self.assertFalse(
            self.env['mail.message'].search_count([
                ('model', '=', 'hr.attendance'), ('res_id', '=', left_at_zero.id)]),
            "every transferred attendance got a tracking message dated today")

    # -- when it cannot, and when time runs out -------------------------------

    def test_a_refused_person_is_named_and_the_others_still_get_their_hours(self):
        """One person whose days the system refuses does not stop anybody else.

        The protocol names the person and the first day, says what the system
        answered, and says how to put it right; the run is not reported as a
        transfer that lost its attendance.
        """
        refused = self._left_by_an_older_transfer(self.person, 1, 8, 17)
        fine = self._left_by_an_older_transfer(self.second, 1, 8, 17)
        Attendance = type(self.env['hr.attendance'])
        original = Attendance._update_overtime

        def refuse_the_first(records, *args, **kwargs):
            if self.person in records.employee_id:
                raise UserError("Refused for the test")
            return original(records, *args, **kwargs)

        with patch.object(Attendance, '_update_overtime', autospec=True,
                          side_effect=refuse_the_first):
            results = self._run(self._source())

        self.assertEqual(self._figures(fine), (8.0, 0.0, 8.0))
        self.assertTrue(refused.exists(), "the transferred attendance must stay")
        self.assertIsNone(self._figures(refused)[0],
                          "a day that could not be worked out must stay findable")
        line = self._hours_line(results)
        self.assertEqual((line['status'], line['source_count'], line['imported_count']),
                         ('partial', 2, 1))
        for part in ('Transferred Person (test)', 'Refused for the test',
                     'Import attendance'):
            self.assertIn(part, line['error'])
        self.assertFalse([r for r in results if r.get('status') == 'error'],
                         "the attendance itself arrived - nothing may read as lost")

    def _works_in_sofia(self):
        """The person works in Sofia, two or three hours ahead of UTC."""
        calendar = self.env.ref('resource.resource_calendar_std').copy(
            {'tz': 'Europe/Sofia'})
        self.person.write({'tz': 'Europe/Sofia', 'resource_calendar_id': calendar.id})

    def test_a_night_stay_lands_under_the_morning_it_began_on(self):
        """A guard who came in at 00:30 on 15 September reads the 15th.

        In UTC that moment is 21:30 on the 14th. The carried record must read
        the date a record made by the doors here would read, from the moment
        it lands - also when this pass could not work out the person's hours
        and leaves the record as it arrived.
        """
        self._works_in_sofia()
        source = self._source([{
            'id': 501,
            'employee_id': [77, 'Transferred Person'],
            'check_in': '2026-09-14 21:30:00',
            'check_out': '2026-09-15 05:30:00',
        }])
        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          side_effect=UserError("Refused for the test")):
            self._run(source)

        landed = self._landed(source, 501)
        landed.invalidate_recordset()
        made_here = self.env['hr.attendance'].new({
            'employee_id': self.person.id,
            'check_in': NIGHT_STAY_IN,
        })
        self.assertEqual(landed.date, made_here.date,
                         "a carried record is dated as one made here")
        self.assertEqual(landed.date, date(2026, 9, 15),
                         "the morning the stay began on")

    def test_the_carried_date_is_cores_when_the_zones_differ(self):
        """Schedule kept in Sofia, person in UTC: the record reads core's date.

        Core dates an attendance in the zone of the working hours first
        (hr_attendance.py:90, _compute_date); the person's own zone - UTC
        here - would file the same stay a day earlier. A carried record must
        read exactly like one the doors made, whatever the daily figures do.
        """
        calendar = self.env.ref('resource.resource_calendar_std').copy(
            {'tz': 'Europe/Sofia'})
        self.person.write({'resource_calendar_id': calendar.id})
        self.person.tz = 'UTC'
        source = self._source([{
            'id': 502,
            'employee_id': [77, 'Transferred Person'],
            'check_in': '2026-09-14 21:30:00',
            'check_out': '2026-09-15 05:30:00',
        }])
        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          side_effect=UserError("Refused for the test")):
            self._run(source)

        landed = self._landed(source, 502)
        landed.invalidate_recordset()
        made_here = self.env['hr.attendance'].new({
            'employee_id': self.person.id,
            'check_in': NIGHT_STAY_IN,
        })
        self.assertEqual(landed.date, made_here.date,
                         "a carried record is dated as one made here")
        self.assertEqual(landed.date, date(2026, 9, 15),
                         "core reads the day in the schedule's zone, Sofia")

    def test_an_older_transfers_wrong_date_is_put_right_by_the_next_one(self):
        """A night stay an older transfer filed under the evening before moves to its morning."""
        self._works_in_sofia()
        self.env.flush_all()
        self.env.cr.execute(
            "INSERT INTO hr_attendance (employee_id, check_in, check_out, in_mode, date)"
            " VALUES (%s, %s, %s, 'rfid', %s) RETURNING id",
            (self.person.id, NIGHT_STAY_IN, NIGHT_STAY_OUT,
             '2026-09-14'))
        older = self.env['hr.attendance'].browse(self.env.cr.fetchone()[0])

        self._run(self._source())

        older.invalidate_recordset()
        self.assertEqual(older.date, date(2026, 9, 15))

    def test_a_refusal_without_words_still_names_the_person(self):
        """When the system refuses without saying why, the person is still named."""
        self._left_by_an_older_transfer(self.person, 1, 8, 17)
        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          side_effect=UserError('')):
            results = self._run(self._source())

        line = self._hours_line(results)
        self.assertEqual(line['status'], 'partial')
        self.assertIn('Transferred Person (test)', line['error'])
        self.assertIn('UserError', line['error'])

    def test_the_named_person_stays_in_the_protocol_on_the_next_pass(self):
        """A later pass of the same transfer writes the protocol again, name included."""
        self._left_by_an_older_transfer(self.person, 1, 8, 17)
        source = self._source()
        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          side_effect=UserError("Refused for the test")):
            self._run(source)

        results = self._run(source)

        line = self._hours_line(results)
        self.assertEqual(line['status'], 'partial')
        self.assertIn('Transferred Person (test)', line['error'])

    def test_out_of_time_it_carries_on_in_the_next_pass(self):
        """A pass that runs out of time stops between people and resumes there."""
        first = self._left_by_an_older_transfer(self.person, 1, 8, 17)
        second = self._left_by_an_older_transfer(self.second, 1, 8, 17)
        source = self._source()
        source.time_is_up = lambda: True

        self._run(source)

        self.assertTrue(source.stopped_early)
        done = [att for att in (first, second) if self._figures(att)[0] is not None]
        self.assertEqual(len(done), 1, "one person per pass at least, then stop")

        source.stopped_early = False
        self._run(source)

        self.assertEqual([self._figures(att)[0] for att in (first, second)], [8.0, 8.0])
        self.assertTrue(source.read_is_finished(FIGURES_KEY))

    def test_history_before_the_first_version_gets_hours_and_no_invented_overtime(self):
        """A transferred day from before the person was set up here: hours, no rules.

        On a transferred database the person's first version starts at the
        transfer and the history lies before it. Core has no schedule there and
        would count the whole day as approved extra time; its own button never
        reaches that far. The day gets its hours worked and nothing invented.
        """
        self.person.version_ids.write({'date_version': '2026-10-01'})
        history = self._left_by_an_older_transfer(self.person, 8, 8, 18)

        self._run(self._source())

        self.assertEqual(self._figures(history), (9.0, 0.0, 9.0),
                         "08:00-18:00 is 9 hours worked (the lunch hour is "
                         "still taken off), none of them extra")
        self.assertFalse(self._overtime_lines(self.person),
                         "the transfer invented overtime nobody approved")

    def test_people_of_another_company_from_the_same_source_are_not_touched(self):
        """A transfer for one company does not work on another company's people.

        The same old system read earlier for another tenant brought that
        tenant's people across with the same source identity; this transfer
        writes into its own company only.
        """
        other_company = self.env['res.company'].create({'name': 'Other Tenant (test)'})
        neighbour = self.env['hr.employee'].create({
            'name': 'Other Tenant Person (test)', 'tz': 'UTC',
            'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            'company_id': other_company.id})
        source = self._source()
        source.link_existing('hr.employee', 79, neighbour.id)
        theirs = self._left_by_an_older_transfer(neighbour, 1, 8, 17)

        self._run(source)

        self.assertIsNone(self._figures(theirs)[0],
                          "a transfer for one company worked on another company's people")

    def test_a_person_being_written_by_a_door_waits_for_the_next_pass(self):
        """Busy rows are not a problem in somebody's days: the person waits.

        A door event writing the same person's attendance at that moment makes
        the database refuse the second writer. The person is neither reported
        nor skipped; the next pass starts with them.
        """
        from psycopg2 import errors
        busy = self._left_by_an_older_transfer(self.person, 1, 8, 17)
        source = self._source()

        with patch.object(type(self.env['hr.attendance']), '_update_overtime',
                          side_effect=errors.SerializationFailure()):
            self._run(source)

        self.assertTrue(source.stopped_early, "the phase must be returned to")
        self.assertFalse(source.read_is_finished(FIGURES_KEY))
        self.assertFalse((source.step_totals.get(FIGURES_KEY) or {}).get('failed'),
                         "a busy person was reported as a problem in their days")

        source.stopped_early = False
        self._run(source)

        self.assertEqual(self._figures(busy), (8.0, 0.0, 8.0))

    def test_it_waits_until_the_attendance_has_all_arrived(self):
        """While attendance is still coming in, nobody's hours are worked out yet."""
        left_at_zero = self._left_by_an_older_transfer(self.person, 1, 8, 17)
        source = self._source()
        source.read_cursors[ATTENDANCE_CURSOR] = 500
        step = AttendanceImporter(source)

        step._settle_attendance_figures()

        self.assertIsNone(self._figures(left_at_zero)[0])
        self.assertFalse(step.results, "no line until the hours are being worked out")
