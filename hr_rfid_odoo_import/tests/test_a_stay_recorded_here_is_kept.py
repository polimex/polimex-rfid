# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A transfer never lays a second stay over one this system has recorded.

Customer case, 23.10.2026: the attendance of a site was rebuilt here from its
door events for the months the old system was still in use, and a second
transfer from an older copy of that system was about to bring the same months
over again - 11 116 stays on top of the ones here, 9 808 of them the same to
the second. Each is a day counted twice in hours and in pay, and nothing in the
table refuses them: the transfer writes past core's own check.

Owner's decision, 23.10.2026: what is recorded here stays. A stay of the other
system the same to the second is already here; one that differs is left out
and listed, with both times, for the people who keep the records.
"""
import json
import unittest
from contextlib import closing
from datetime import date

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import format_date, format_datetime

from odoo.addons.hr_attendance.models.hr_attendance import (
    HrAttendance as CoreAttendance,
)

from ..models.importers.attendance_importer import (
    ATTENDANCE_CURSOR,
    DIFFERS_KEY,
    AttendanceImporter,
    refused_beside,
)
from ..models.importers.base_importer import BaseImporter
from ..models.importers.reconcile_importer import ReconcileImporter
from .test_reconcile_with_the_source import _CountingSource, at_the_source
from .test_run_totals_survive_the_passes import _PagedSource
from .test_transferred_attendance_has_hours import _WritingSource

DAY = 3  # September 2026


def moment(hour, day=DAY, minute=0, month=9):
    """A moment as the database keeps it: UTC, without a zone."""
    return fields.Datetime.to_datetime(
        '2026-%02d-%02d %02d:%02d:00' % (month, day, hour, minute))


class _PagedWritingSource(_PagedSource):
    """One row per pass, and the rows really land: a big tenant in small."""

    PAGE = 1

    def _direct_sql_insert_tracked(self, *args, **kwargs):
        return BaseImporter._direct_sql_insert_tracked(self, *args, **kwargs)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_stay_kept')
class TestAStayRecordedHereIsKept(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.attendance' not in cls.env:
            raise unittest.SkipTest("attendance is not installed on this database")
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Other Tenant (test)'})
        cls.company_map = {101: cls.company.id, 202: cls.other_company.id}

        def person(name, tz='UTC', company=cls.company):
            return cls.env['hr.employee'].create({
                'name': name, 'tz': tz, 'company_id': company.id,
            })

        cls.person = person('Person With Stays Here (test)')
        cls.colleague = person('Colleague (test)')
        cls.sofia = person('Person In Sofia (test)', tz='Europe/Sofia')
        cls.elsewhere = person('Person Of The Other Tenant (test)',
                               company=cls.other_company)

    # -- the transfer --------------------------------------------------------

    def _source(self, rows, paged=False):
        source_class = _PagedWritingSource if paged else _WritingSource
        source = source_class(
            self.env, dict(self.company_map), {'import_attendance': True},
            {'hr.attendance': list(rows)})
        source.link_existing('hr.employee', 77, self.person.id)
        source.link_existing('hr.employee', 78, self.colleague.id)
        source.link_existing('hr.employee', 79, self.sofia.id)
        source.link_existing('hr.employee', 80, self.elsewhere.id)
        return source

    @staticmethod
    def _row(source_id, start, stop, source_person=77):
        return {
            'id': source_id,
            'employee_id': [source_person, 'Somebody'],
            'check_in': fields.Datetime.to_string(start),
            'check_out': stop and fields.Datetime.to_string(stop),
        }

    def _line(self, results):
        lines = [r for r in results if r['model'] == 'hr.attendance']
        self.assertEqual(len(lines), 1, 'one protocol line for the attendance')
        return lines[0]

    def _transfer(self, source):
        return self._line(AttendanceImporter(source).run(None))

    def _transfer_in_passes(self, source):
        """Pass after pass until the read is done, the totals kept as a run keeps them."""
        for _attempt in range(50):
            line = self._line(AttendanceImporter(source).run(None))
            source.step_totals = json.loads(json.dumps(source.step_totals))
            source.read_cursors = json.loads(json.dumps(source.read_cursors))
            if source.read_is_finished(ATTENDANCE_CURSOR):
                return line
        self.fail('the read never finished')

    def _recorded_here(self, employee, start, stop):
        return self.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': start, 'check_out': stop,
        })

    def _stays_of(self, employee):
        return self.env['hr.attendance'].search(
            [('employee_id', '=', employee.id)], order='check_in')

    def _run_record(self, source):
        return self.env['hr.rfid.odoo.import.run'].create({
            'source_url': 'http://localhost:1', 'source_login': 'admin',
            'source_slug': source.source_slug,
            'step_totals_json': json.dumps(source.step_totals),
        })

    def _listed(self, source, employee):
        """What the downloaded protocol says about that person, one line per stay."""
        lines = self._run_record(source)._protocol_stays_left_out()
        return [line for line in lines if line.startswith(employee.name + ' |')]

    def _shown(self, value, employee):
        """A time the way the downloaded protocol writes it for that person."""
        return format_datetime(self.env, value, tz=employee.tz, dt_format='short')

    def _reconciled(self, step_totals, counts):
        counting = _CountingSource(self.env, dict(self.company_map), {}, counts)
        # Through JSON, as every pass after the first reads them.
        counting.step_totals = json.loads(json.dumps(step_totals))
        phase = ReconcileImporter(counting)
        phase.run(None)
        return {row['model']: row for row in phase.results}['attendances']

    # -- what the person and the clerk see ----------------------------------

    def test_a_stay_already_here_to_the_second_is_not_brought_again(self):
        """The same stay from the other system does not make a second one here.

        The clerk reading the person's day sees one stay and its hours, not
        the same hours twice - also for a stay that began and ended at one
        moment, which core itself would let stand beside its twin.
        """
        here = self._recorded_here(self.person, moment(8), moment(17))
        blip = self._recorded_here(self.person, moment(19), moment(19))
        hours = here.worked_hours
        line = self._transfer(self._source([
            self._row(10, moment(8), moment(17)),
            self._row(11, moment(19), moment(19)),
        ]))

        stays = self._stays_of(self.person)
        self.assertEqual(stays, here | blip,
                         'a stay arrived a second time on top of the one here')
        self.assertTrue(hours)
        self.assertEqual(sum(stays.mapped('worked_hours')), hours,
                         "the day's hours were counted twice")
        self.assertEqual((line['imported_count'], line['linked_count'],
                          line['skipped_count'], line['status']),
                         (0, 2, 0, 'done'),
                         'the same stay is counted as already here, not as a loss')

    def test_a_different_stay_at_that_time_is_left_out_and_the_one_here_stays(self):
        """What is recorded here stays; the other system's version is named and listed.

        The person's day keeps the stay people have worked with since; the
        protocol tells the operator who, and the downloaded protocol gives the
        record keepers both versions - the other system may be gone by then.
        """
        here = self._recorded_here(self.person, moment(8), moment(17))
        source = self._source([self._row(10, moment(7), moment(16))])
        line = self._transfer(source)

        self.assertEqual(self._stays_of(self.person), here)
        self.assertEqual((here.check_in, here.check_out), (moment(8), moment(17)),
                         'the stay recorded here was changed')
        self.assertEqual((line['imported_count'], line['skipped_count'], line['status']),
                         (0, 1, 'partial'))
        self.assertIn(self.person.name, line['error'])
        listed = self._listed(source, self.person)
        self.assertEqual(len(listed), 1)
        for value in (moment(7), moment(16), moment(8), moment(17)):
            self.assertIn(self._shown(value, self.person), listed[0])

    def test_a_stay_with_nothing_here_at_that_time_still_arrives(self):
        """The rule keeps out only what collides - the history still comes across.

        A stay the next morning, a stay that begins the moment the one here
        ends, and a colleague's stay at the very same hours all arrive.
        """
        self._recorded_here(self.person, moment(8), moment(17))
        line = self._transfer(self._source([
            self._row(10, moment(8, DAY + 1), moment(17, DAY + 1)),
            self._row(11, moment(17), moment(19)),
            self._row(12, moment(8), moment(17), source_person=78),
        ]))

        self.assertEqual(line['imported_count'], 3)
        self.assertEqual(line['status'], 'done')
        self.assertEqual(len(self._stays_of(self.person)), 3)
        self.assertEqual(len(self._stays_of(self.colleague)), 1)

    def test_two_overlapping_stays_of_the_other_system_bring_only_the_first(self):
        """The other system's own overlaps are held to the same rule.

        It recorded 08:00-17:00 and then 12:00-20:00 for one person; only the
        first arrives, the second is listed like any other stay that collides.
        """
        source = self._source([self._row(10, moment(8), moment(17)),
                               self._row(11, moment(12), moment(20))])
        line = self._transfer(source)

        stays = self._stays_of(self.person)
        self.assertEqual([(s.check_in, s.check_out) for s in stays],
                         [(moment(8), moment(17))])
        self.assertEqual((line['imported_count'], line['skipped_count']), (1, 1))
        listed = self._listed(source, self.person)
        self.assertEqual(len(listed), 1)
        self.assertIn(self._shown(moment(20), self.person), listed[0])

    def test_a_person_at_work_right_now_keeps_one_open_stay(self):
        """A stay still open here holds the time from its check-in on.

        The person badged in at 08:00 and is still at work. The other system
        sends a stay it never closed, from a month ago, 07:00-09:00 and
        09:00-10:00 of this morning; none may arrive - the first would be a
        second open stay, the others would make the open one impossible to
        close (and, with the check bypassed, count that time twice; core
        accepts 09:00-10:00 when it is written and refuses only the close).
        Last week arrives.
        """
        at_work = self._recorded_here(self.person, moment(8), False)
        source = self._source([
            self._row(20, moment(9, 4, month=8), None),
            self._row(21, moment(7), moment(9)),
            self._row(22, moment(8, 27, month=8), moment(17, 27, month=8)),
            self._row(23, moment(9), moment(10)),
        ])
        line = self._transfer(source)

        stays = self._stays_of(self.person)
        self.assertEqual(stays.filtered(lambda s: not s.check_out), at_work,
                         'the person must still have exactly one open stay')
        self.assertEqual(len(stays), 2, 'last week arrives, nothing else')
        self.assertEqual((line['imported_count'], line['skipped_count']), (1, 3))
        listed = self._listed(source, self.person)
        self.assertEqual(len(listed), 3)
        self.assertTrue(any(self.env._("still open") in item for item in listed))

    def test_the_rule_is_cores_own(self):
        """A stay is kept out exactly when core would refuse it - now, or when an open one closes.

        The oracle is core's own check, called as core wrote it: each shape is
        written beside a stay already recorded, the way the transfer writes,
        and core is asked about the new one; an open stay is then closed later
        that day and core is asked again, because that is when it refuses a
        stay begun after the open one. Asked through create() instead, the
        answer would be whatever the modules installed over core make of it.
        """
        shapes = [
            # (here: start, stop) (new: start, stop)
            ((8, 17), (7, 9)), ((8, 17), (16, 18)), ((8, 17), (17, 18)),
            ((8, 17), (6, 8)), ((8, 17), (9, 12)), ((8, 17), (8, 17)),
            ((8, 17), (7, 18)), ((8, 17), (12, None)), ((8, 17), (18, None)),
            ((8, 17), (7, None)), ((8, 17), (8, None)), ((8, 17), (17, None)),
            ((8, None), (6, 7)), ((8, None), (7, 9)), ((8, None), (9, 10)),
            ((8, None), (8, 9)), ((8, None), (10, None)), ((8, None), (8, None)),
        ]

        def written(start, stop):
            self.env.cr.execute(
                "INSERT INTO hr_attendance (employee_id, check_in, check_out, date)"
                " VALUES (%s, %s, %s, %s) RETURNING id",
                (self.person.id, start, stop, start.date()))
            return self.env['hr.attendance'].browse(self.env.cr.fetchone()[0])

        def refused_by_core(record):
            try:
                CoreAttendance._check_validity(record)
            except ValidationError:
                return True
            return False

        def refused_when_closed(record):
            self.env.cr.execute("UPDATE hr_attendance SET check_out = %s WHERE id = %s",
                                (moment(23), record.id))
            record.invalidate_recordset(['check_out'])
            return refused_by_core(record)

        for (here_in, here_out), (new_in, new_out) in shapes:
            with self.subTest(here=(here_in, here_out), new=(new_in, new_out)):
                here_stop = here_out and moment(here_out)
                new_stop = new_out and moment(new_out)
                # closing() takes the shape's stays back before the next one
                # (odoo/sql_db.py, Savepoint: "wrapped in contextlib.closing to
                # unconditionally roll it back").
                with closing(self.env.cr.savepoint()):
                    here = written(moment(here_in), here_stop)
                    new = written(moment(new_in), new_stop)
                    core_refuses = refused_by_core(new)
                    if not core_refuses and new_stop is None:
                        core_refuses = refused_when_closed(new)
                    if not core_refuses and here_stop is None:
                        core_refuses = refused_when_closed(here)
                self.assertEqual(
                    refused_beside(moment(new_in), new_stop, moment(here_in), here_stop),
                    core_refuses)

    def test_stays_read_over_several_passes_are_judged_as_if_read_at_once(self):
        """A big tenant is read in passes; the verdicts are the same as in one go.

        A stay that collides with one brought over by an EARLIER pass is left
        out, the other system's own duplicate is recognised, and the last
        pass's line - the only one the protocol keeps - names the person.
        """
        source = self._source([
            self._row(10, moment(8), moment(17)),
            self._row(11, moment(12), moment(20)),
            self._row(12, moment(8), moment(17)),
            self._row(13, moment(8, DAY + 1), moment(17, DAY + 1)),
        ], paged=True)
        line = self._transfer_in_passes(source)

        self.assertEqual((line['imported_count'], line['linked_count'],
                          line['skipped_count'], line['status']),
                         (2, 1, 1, 'partial'))
        self.assertIn(self.person.name, line['error'])
        listed = self._listed(source, self.person)
        self.assertEqual(len(listed), 1)
        self.assertIn(self._shown(moment(20), self.person), listed[0])
        self.assertEqual(len(self._stays_of(self.person)), 2)

    def test_a_page_read_again_after_a_failed_write_lists_each_stay_once(self):
        """A write that fails sends the read back to the start; nothing is said twice.

        The first page leaves a stay out; the second page's write fails once,
        so the next pass reads from the beginning and meets that stay again.
        """
        self._recorded_here(self.person, moment(8), moment(17))
        source = self._source([self._row(10, moment(7), moment(16)),
                               self._row(11, moment(8, DAY + 1), moment(17, DAY + 1))],
                              paged=True)
        failures = [ValueError('the database said no')]
        real_insert = _PagedWritingSource._direct_sql_insert_tracked

        def fails_once(importer, *args, **kwargs):
            if failures:
                raise failures.pop()
            return real_insert(importer, *args, **kwargs)

        self.patch(_PagedWritingSource, '_direct_sql_insert_tracked', fails_once)
        self._transfer_in_passes(source)

        self.assertFalse(failures, 'the write never failed - the case was not set up')
        self.assertEqual(len(self._listed(source, self.person)), 1)
        self.assertEqual(len(source.step_totals[ATTENDANCE_CURSOR][DIFFERS_KEY]), 1)
        self.assertEqual(
            self._reconciled(source.step_totals,
                             {'hr.attendance': at_the_source(101, 2)})['status'],
            'done')

    def test_the_reconciliation_does_not_count_the_stays_kept_here_as_lost(self):
        """Three stays over there, one arrived and two kept here: nothing is lost.

        Counted as a loss, every transfer over a working system would end as a
        failed one, and the operator would learn to ignore the check.
        """
        self._recorded_here(self.person, moment(8), moment(17))
        self._recorded_here(self.person, moment(8, DAY + 1), moment(17, DAY + 1))
        writing = self._source([
            self._row(10, moment(8), moment(17)),                    # same
            self._row(11, moment(7, DAY + 1), moment(16, DAY + 1)),  # differs
            self._row(12, moment(8, DAY + 2), moment(17, DAY + 2)),  # arrives
        ])
        self._transfer(writing)
        counts = {'hr.attendance': at_the_source(101, 3)}

        row = self._reconciled(writing.step_totals, counts)
        self.assertEqual((row['imported_count'], row['linked_count'], row['status']),
                         (1, 2, 'done'))
        # The twin that proves the check still bites: without the transfer's
        # own account of what it kept here, the same numbers are a loss.
        self.assertEqual(self._reconciled({}, counts)['status'], 'error')

    def test_stays_kept_here_for_one_tenant_do_not_hide_a_loss_in_another(self):
        """What one tenant kept here on purpose cannot cover another tenant's loss."""
        self._recorded_here(self.person, moment(8), moment(17))
        writing = self._source([
            self._row(10, moment(8), moment(17)),                    # same
            self._row(11, moment(7), moment(16)),                    # differs
            self._row(12, moment(8, DAY + 2), moment(17, DAY + 2)),  # arrives
        ])
        self._transfer(writing)

        row = self._reconciled(writing.step_totals, {
            'hr.attendance': at_the_source(101, 3) + at_the_source(202, 2)})
        self.assertEqual(row['status'], 'error')
        self.assertIn(self.other_company.name, row['error'])
        self.assertNotIn(self.company.name + ':', row['error'])

    def test_a_later_transfer_without_attendance_does_not_report_the_kept_stays_as_lost(self):
        """A transfer of the cards alone still knows what an earlier one kept here.

        The check compares every kind, whatever was ticked; the stays an
        earlier transfer of the same system kept here on purpose are not a
        loss in a later one that carried no attendance at all.
        """
        self._recorded_here(self.person, moment(8), moment(17))
        first = self._source([self._row(10, moment(8), moment(17)),
                              self._row(11, moment(7, DAY + 1), moment(16, DAY + 1))])
        self._transfer(first)
        counts = {'hr.attendance': at_the_source(101, 2)}
        self.assertEqual(self._reconciled({}, counts)['status'], 'error',
                         'without the earlier transfer on record the check must bite')

        self._run_record(first)
        self.assertEqual(self._reconciled({}, counts)['status'], 'done')

    def test_a_second_run_changes_nothing_and_reconciles_the_same(self):
        """Running the transfer again adds nothing, says the same, and balances the same."""
        self._recorded_here(self.person, moment(8), moment(17))
        self._recorded_here(self.person, moment(8, DAY + 1), moment(17, DAY + 1))
        rows = [self._row(10, moment(8), moment(17)),
                self._row(11, moment(7, DAY + 1), moment(16, DAY + 1)),
                self._row(12, moment(17, DAY + 1), moment(18, DAY + 1))]
        counts = {'hr.attendance': at_the_source(101, 3)}
        first_source = self._source(rows)
        first = self._transfer(first_source)
        before = self._stays_of(self.person)
        second_source = self._source(rows)
        second = self._transfer(second_source)

        self.assertEqual(self._stays_of(self.person), before)
        self.assertEqual((first['imported_count'], first['linked_count'],
                          first['skipped_count']), (1, 1, 1))
        self.assertEqual((second['imported_count'], second['linked_count'],
                          second['skipped_count'], second['status']), (0, 2, 1, 'partial'))
        self.assertIn(self.person.name, second['error'])
        for source in (first_source, second_source):
            row = self._reconciled(source.step_totals, counts)
            self.assertEqual((row['imported_count'], row['linked_count'], row['status']),
                             (1, 2, 'done'))

    def test_a_stay_left_out_arrives_on_a_later_run_once_the_stay_here_is_corrected(self):
        """The record keepers put the day right; the next transfer brings the stay.

        Nothing remembers a stay as "left out for good": every run asks again.
        """
        here = self._recorded_here(self.person, moment(8), moment(17))
        rows = [self._row(10, moment(7), moment(16))]
        self.assertEqual(self._transfer(self._source(rows))['skipped_count'], 1)

        here.unlink()
        line = self._transfer(self._source(rows))

        self.assertEqual((line['imported_count'], line['status']), (1, 'done'))
        self.assertNotIn(self.person.name, line['error'] or '')
        self.assertEqual([(s.check_in, s.check_out) for s in self._stays_of(self.person)],
                         [(moment(7), moment(16))])

    def test_an_undone_attendance_step_takes_back_its_left_out_stays(self):
        """A step that fails after deciding leaves neither rows nor verdicts behind."""
        self._recorded_here(self.person, moment(8), moment(17))
        source = self._source([self._row(10, moment(7), moment(16)),
                               self._row(11, moment(8, DAY + 1), moment(17, DAY + 1))])

        def breaks(importer):
            raise ValueError('the protocol could not be written')

        self.patch(AttendanceImporter, '_differs_note', breaks)
        results = AttendanceImporter(source).run(None)

        self.assertTrue([r for r in results if r['status'] == 'error'])
        self.assertEqual(len(self._stays_of(self.person)), 1, 'the rows were not undone')
        self.assertFalse(source.step_totals.get(ATTENDANCE_CURSOR, {}).get(DIFFERS_KEY),
                         'the verdicts survived the undone step')

    def test_the_protocol_line_names_the_first_day_as_the_person_lived_it(self):
        """00:30 on 3 September in Sofia is 2 September in the database; the line says 3."""
        self._recorded_here(self.sofia, moment(22, DAY - 1), moment(4))
        self._recorded_here(self.sofia, moment(5, DAY + 2), moment(14, DAY + 2))
        line = self._transfer(self._source([
            self._row(10, moment(21, DAY - 1, minute=30), moment(5), source_person=79),
            self._row(11, moment(6, DAY + 2), moment(15, DAY + 2), source_person=79),
        ]))

        self.assertIn(format_date(self.env, date(2026, 9, 3)), line['error'])
        for day in (2, 5):
            self.assertNotIn(format_date(self.env, date(2026, 9, day)), line['error'])

    def test_the_downloaded_file_lists_every_stay_left_out(self):
        """The file the operator downloads holds every stay, with all four times.

        Seven people - more than the protocol line names - one of them of the
        other tenant, downloaded by an administrator who has only the first
        company selected: the file must still come, and still be complete.
        """
        people = self.person | self.colleague | self.elsewhere
        for number in range(4):
            people |= self.env['hr.employee'].create({
                'name': 'Another Person %s (test)' % number, 'tz': 'UTC',
                'company_id': self.company.id,
            })
        rows = []
        source = self._source([])
        for number, employee in enumerate(people, start=1):
            self._recorded_here(employee, moment(8), moment(17))
            source.link_existing('hr.employee', 100 + number, employee.id)
            rows.append(self._row(number, moment(7), moment(16), source_person=100 + number))
        source._data['hr.attendance'] = rows
        self._transfer(source)
        run = self._run_record(source)
        operator = self.env['res.users'].create({
            'name': 'Operator (test)', 'login': 'operator_download_test',
            'group_ids': [Command.link(self.env.ref('base.group_system').id)],
            'company_id': self.company.id,
            'company_ids': [Command.set([self.company.id, self.other_company.id])],
        })

        # A download is a request of its own: nothing read so far as superuser
        # may answer for the operator from the cache.
        self.env.invalidate_all()
        action = run.with_user(operator).with_context(
            allowed_company_ids=[self.company.id]).action_download_protocol()

        attachment = self.env['ir.attachment'].browse(
            int(action['url'].split('/web/content/')[1].split('?')[0]))
        text = attachment.raw.decode()
        for employee in people:
            listed = [line for line in text.splitlines()
                      if line.startswith(employee.name + ' |')]
            self.assertEqual(len(listed), 1, employee.name)
            for value in (moment(7), moment(16), moment(8), moment(17)):
                self.assertIn(self._shown(value, employee), listed[0])
