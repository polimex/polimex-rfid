# -*- coding: utf-8 -*-
"""Rebuilding attendance is a job the operator hands over, not one they wait for.

Every test below states what the person using the system gets, not what the
code does: control back at once, everybody in the list rebuilt, one bad
employee not taking the rest down with them, and an interrupted rebuild picking
up where it stopped instead of starting again.
"""
import logging
from datetime import datetime, time, timedelta
from unittest.mock import patch

from pytz import timezone, utc

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.hr_attendance_multi_rfid.models import attendance_recalc_run

_logger = logging.getLogger(__name__)

#: The transfer that brings attendance over from an older installation. It is
#: not part of every site, and where it is missing the refusal it raises
#: cannot be watched from end to end - which is said out loud rather than
#: passed over in silence.
THE_TRANSFER = 'hr.rfid.odoo.import.run'

#: Somewhere three hours ahead of London in summer, so that "the last day the
#: operator chose" is a different span of hours depending on where it is
#: measured - which is the whole point of the tests that use it.
WHERE_THEY_WORK = timezone('Europe/Sofia')

#: The way out is the last thing a refusal says, so it is the first thing lost
#: when one is cut short.
LAST_WORDS_OF_THE_REFUSAL = "run the transfer again"

#: A refusal the length of a real one. The only refusal this product raises
#: today runs past five hundred characters and puts what to do instead at the
#: very end (hr_rfid_odoo_import/models/hr_employee.py,
#: _transferred_attendance_message).
A_REFUSAL_OF_REAL_LENGTH = (
    "This attendance was brought over from another system and cannot be "
    "recalculated here.\n\n"
    "17 attendance records of these people are a copy of what the old system "
    "recorded. They cannot be worked out again from the door events, and "
    "recalculating them would break the link with the old system: the next "
    "transfer would no longer recognise them and would bring them over a "
    "second time.\n\n"
    "To refresh this data, %s. To recalculate the rest, choose a period "
    "without these records, or leave these people out."
) % LAST_WORDS_OF_THE_REFUSAL


def _windows_the_browser_must_open(action):
    """Every window in a returned action, the chained ones included.

    An action can carry another one to open after it (``params['next']``), and
    the browser treats what it finds there exactly like a top-level window.
    """
    if not isinstance(action, dict):
        return
    if action.get('type') == 'ir.actions.act_window':
        yield action
    yield from _windows_the_browser_must_open((action.get('params') or {}).get('next'))



@tagged("post_install", "-at_install", "rfid_attendance_recalc")
class TestAttendanceRebuildInBackground(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.main_company')
        # Several tests read what the operator was TOLD, and the message is
        # written in the requesting account's language - so on a database
        # installed in Bulgarian those assertions were reading Bulgarian and
        # failing, while the same tests passed on an English one. Which
        # language a customer installed is not what they are about. Pin it, the
        # way core does when a test depends on a language
        # (odoo/addons/account/tests/test_account_move_entry.py:1455).
        cls.env['res.lang']._activate_lang('en_US')
        cls.env.user.lang = 'en_US'
        # Minimum hardware a rebuild needs: one door with an entry and an exit
        # reader, in a zone that counts towards attendance. Shape copied from
        # hr_rfid/tests/test_system_event_dedup.py.
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Rebuild WS', 'serial': '884401', 'key': '1234',
            'hw_version': '100.1', 'version': '1.44', 'active': True,
            'tz': 'Europe/Sofia', 'company_id': cls.company.id})
        cls.ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Rebuild CTRL', 'ctrl_id': 9, 'serial_number': '8844',
            'webstack_id': cls.webstack.id, 'hw_version': '9', 'sw_version': '740',
            'max_cards_count': 100, 'max_events_count': 100, 'readers': 2,
            'mode': 2, 'inputs': 0, 'outputs': 0, 'input_states': 0,
            'output_states': 0, 'alarm_lines': 0, 'io_table_lines': 0,
            'io_table': ''})
        card_type = cls.env.ref('hr_rfid.hr_rfid_card_type_def')
        cls.door = cls.env['hr.rfid.door'].with_context(
            no_hardware_commands=True).create({
                'name': 'Rebuild Door', 'number': 1,
                'controller_id': cls.ctrl.id, 'card_type': card_type.id})
        cls.reader_in = cls.env['hr.rfid.reader'].with_context(
            no_hardware_commands=True).create({
                'name': 'Rebuild Reader In', 'number': 1, 'reader_type': '0',
                'controller_id': cls.ctrl.id,
                'door_ids': [Command.link(cls.door.id)]})
        cls.reader_out = cls.env['hr.rfid.reader'].with_context(
            no_hardware_commands=True).create({
                'name': 'Rebuild Reader Out', 'number': 2, 'reader_type': '1',
                'controller_id': cls.ctrl.id,
                'door_ids': [Command.link(cls.door.id)]})
        cls.zone = cls.env['hr.rfid.zone'].create({
            'name': 'Rebuild Zone', 'company_id': cls.company.id,
            'attendance': True,
            'door_ids': [Command.link(cls.door.id)]})
        cls.employees = cls.env['hr.employee'].create([
            {'name': 'Rebuild Employee %d' % number,
             'company_id': cls.company.id}
            for number in (1, 2, 3)
        ])
        cls.employee_1, cls.employee_2, cls.employee_3 = cls.employees

        cls.yesterday = fields.Datetime.now() - timedelta(days=1)
        cls.start_date = fields.Date.to_date(cls.yesterday) - timedelta(days=7)
        cls.end_date = fields.Date.today()

    def setUp(self):
        super().setUp()
        # The job commits after every person so that an interrupted rebuild
        # keeps what it has done. Inside a test the cursor must not really
        # commit or roll back, so the boundary is neutralised the way core
        # neutralises it (odoo/addons/sms_twilio/tests/test_sms_twilio.py:206-212).
        self.patch(self.registry['ir.cron'], '_commit_progress',
                   lambda cron_model, processed=0, remaining=None, **kwargs: 60.0)
        self.patch(self.env.cr, 'commit', lambda: None)
        self.patch(self.env.cr, 'rollback', lambda: None)

    # ── helpers ───────────────────────────────────────────────

    def _door_event(self, employee, reader, moment):
        return self.env['hr.rfid.event.user'].create({
            'employee_id': employee.id,
            'door_id': self.door.id,
            'reader_id': reader.id,
            'event_time': moment,
            'event_action': '1',  # granted
        })

    def _a_normal_working_day(self, employee, day_offset=0):
        """Entry in the morning, exit in the evening - one whole day."""
        base = self.yesterday.replace(hour=8, minute=0, second=0, microsecond=0)
        base -= timedelta(days=day_offset)
        self._door_event(employee, self.reader_in, base)
        self._door_event(employee, self.reader_out, base + timedelta(hours=9))
        return base, base + timedelta(hours=9)

    def _attendance_as_it_stands(self, employee):
        """Everything this person's attendance says right now.

        Door events make attendance as they arrive, so a person who has been
        through a door already has some before any rebuild is asked for.
        "Left exactly as it was" therefore has to be checked against the thing
        itself - the same records, saying the same - and not against an empty
        list, which a rebuild that deleted the lot and replayed nothing would
        satisfy just as well.
        """
        return {
            attendance.id: (attendance.check_in, attendance.check_out)
            for attendance in self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id)])
        }

    def _when_they_are(self, day, hour, minute=0):
        """The moment the clock on their wall says, as the database keeps it."""
        local = WHERE_THEY_WORK.localize(datetime.combine(day, time(hour, minute)))
        return local.astimezone(utc).replace(tzinfo=None)

    def _ask_for_a_rebuild(self, employees=None, start=None, end=None):
        """Press the button the way the operator does. Returns the recorded
        request and what the operator was shown."""
        wizard = self.env['hr.attendance.recalc.wizard'].create({
            'employee_ids': [Command.set((employees or self.employees).ids)],
            'start_date': start or self.start_date,
            'end_date': end or self.end_date,
        })
        shown = wizard.execute()
        run = self.env['hr.attendance.recalc.run'].browse(
            shown['params']['next']['res_id'])
        return run, shown

    def _refuse_every_rebuild(self, reason=A_REFUSAL_OF_REAL_LENGTH):
        """Stand in for an add-on that holds records it will not have rebuilt.

        The refusal itself is the add-on's, not ours - all this module knows
        is that somebody objected, in the one way the objection can be made
        (hr_rfid/models/hr_employee.py, _check_recalc_allowed).
        """
        def refuse(employees, start_date, end_date):
            raise UserError(reason)

        self.patch(self.registry['hr.employee'], '_check_recalc_allowed', refuse)

    def _let_the_scheduler_work(self, run, passes=10):
        Run = self.env['hr.attendance.recalc.run']
        for _pass in range(passes):
            if run.state not in ('queued', 'running'):
                return
            Run._cron_process()
        self.assertNotIn(run.state, ('queued', 'running'),
                         "the rebuild never finished within %d passes" % passes)

    # ── what the operator gets ────────────────────────────────

    def test_operator_gets_control_back_immediately(self):
        """Asking for a rebuild records the request and returns - it does not
        delete or rebuild anything while the operator waits."""
        self._a_normal_working_day(self.employee_1)
        # Attendance the rebuild would delete and re-create, sitting in the
        # period being asked about - on a different day from the one the door
        # events made. Two attendances over the same hours is a state the
        # product refuses (hr.attendance._check_validity), so putting one there
        # would be testing against something no site can hold.
        an_earlier_day = self.yesterday - timedelta(days=3)
        existing = self.env['hr.attendance'].create({
            'employee_id': self.employee_1.id,
            'check_in': an_earlier_day.replace(hour=9, minute=0, second=0,
                                               microsecond=0),
            'check_out': an_earlier_day.replace(hour=10, minute=0, second=0,
                                                microsecond=0),
        })
        as_it_was = self._attendance_as_it_stands(self.employee_1)

        run, result = self._ask_for_a_rebuild()

        self.assertTrue(existing.exists(),
                        "asking for a rebuild must not touch attendance yet - "
                        "the work belongs in the background")
        self.assertEqual(self._attendance_as_it_stands(self.employee_1),
                         as_it_was,
                         "nothing at all may be deleted or replayed while the "
                         "operator is still waiting on the screen")
        self.assertEqual(run.state, 'queued',
                         "the request must be written down, waiting to start")
        self.assertFalse(run.log_ids,
                         "nothing may have been rebuilt inside the wizard call")
        self.assertEqual(run.employee_ids, self.employees)
        self.assertEqual(result.get('tag'), 'display_notification',
                         "the operator must be told the work has started")
        self.assertEqual(result['params']['next']['res_model'],
                         'hr.attendance.recalc.run',
                         "and be shown where to watch it")

    def test_the_progress_screen_the_operator_is_sent_to_can_open(self):
        """Being told where to watch is not the same as getting there.

        What the button returns is cleaned by the server
        (web/controllers/utils.py:23, clean_action) and then handed to the
        browser, which calls action.views.map(...) on every window it is asked
        to open (web/static/src/webclient/actions/action_service.js:442). The
        cleaning fills in 'views' for the action that is RETURNED, and only for
        that one - a window carried inside another action's params is passed
        through untouched. Without 'views' it takes the whole screen down with
        "Cannot read properties of undefined", AFTER the rebuild has been
        queued and started: the work runs to completion and the operator is
        left looking at a crash, with no way to the progress they were
        promised. Reported from a 208-person site on 2026-08-21, where the
        rebuild had in fact finished - 107 people rebuilt - while the screen
        showed an error.

        The test asserts the browser's rule, not ours, and walks the whole
        chain: it is the nested window that nobody completes.
        """
        # The server's own cleaning, so the test sees exactly what the browser
        # is sent - not what the method happened to return.
        from odoo.addons.web.controllers.utils import clean_action

        self._a_normal_working_day(self.employee_1)
        _, shown = self._ask_for_a_rebuild()

        windows = list(_windows_the_browser_must_open(
            clean_action(shown, env=self.env)))
        self.assertTrue(
            windows,
            "the operator is told where to watch the rebuild - if no window is "
            "offered any more, this test is guarding nothing")
        for window in windows:
            self.assertIsInstance(
                window.get('views'), list,
                "the window '%s' reaches the browser without 'views', and the "
                "browser maps over it unconditionally - the operator gets a "
                "crash instead of the progress screen"
                % (window.get('res_model') or window.get('name')))

    def test_the_rebuild_replays_the_door_events(self):
        """Once the scheduler picks it up, attendance matches the doors."""
        check_in, check_out = self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)

        self._let_the_scheduler_work(run)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id)])
        self.assertEqual(len(attendances), 1,
                         "the entry and the exit make one day at work")
        self.assertEqual(attendances.check_in, check_in)
        self.assertEqual(attendances.check_out, check_out)
        self.assertEqual(run.state, 'done')
        line = run.log_ids
        self.assertEqual(line.employee_id, self.employee_1)
        self.assertEqual(line.status, 'done')
        self.assertEqual(line.attendance_count, 1)

    def test_all_employees_are_processed(self):
        """Everybody on the list is accounted for, including the people who
        never went through a door - they must not look forgotten."""
        self._a_normal_working_day(self.employee_1)
        self._a_normal_working_day(self.employee_3)
        run, _shown = self._ask_for_a_rebuild()

        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'done')
        self.assertEqual(set(run.log_ids.employee_id.ids), set(self.employees.ids),
                         "every person asked for must have a line")
        self.assertEqual(run.done_count, 3)
        self.assertEqual(run.progress, 100)
        by_employee = {line.employee_id: line.status for line in run.log_ids}
        self.assertEqual(by_employee[self.employee_1], 'done')
        self.assertEqual(by_employee[self.employee_2], 'no_events',
                         "no door events means their attendance was left alone")
        self.assertEqual(by_employee[self.employee_3], 'done')

    def test_one_bad_employee_does_not_lose_the_others(self):
        """A person whose rebuild breaks is named in the report; everybody
        else is still rebuilt."""
        self._a_normal_working_day(self.employee_1)
        self._a_normal_working_day(self.employee_3)
        run, _shown = self._ask_for_a_rebuild()

        original = self.registry['hr.employee']._recalc_attendance_one
        broken_id = self.employee_2.id

        def sometimes_broken(employee, from_date, to_date, ctx):
            if employee.id == broken_id:
                raise ValueError('door events unreadable')
            return original(employee, from_date, to_date, ctx)

        self.patch(self.registry['hr.employee'], '_recalc_attendance_one',
                   sometimes_broken)
        self._let_the_scheduler_work(run)

        by_employee = {line.employee_id: line for line in run.log_ids}
        self.assertEqual(by_employee[self.employee_2].status, 'error')
        self.assertEqual(by_employee[self.employee_1].status, 'done')
        self.assertEqual(by_employee[self.employee_3].status, 'done')
        self.assertTrue(
            self.env['hr.attendance'].search_count([
                ('employee_id', '=', self.employee_3.id)]),
            "a person after the failure must still have been rebuilt")
        self.assertEqual(run.state, 'failed',
                         "the rebuild must not report success over a person "
                         "it could not do")
        self.assertTrue(
            any(self.employee_2.display_name in (message.body or '')
                for message in run.message_ids),
            "the report must name who was left out")

    def test_a_breakdown_is_reported_in_words_the_operator_can_act_on(self):
        """When rebuilding somebody breaks, the operator is told what it means
        for them - not shown the words the program failed with.

        The text of a database or programming error tells the person at the
        screen nothing they can do anything about, and reading one makes a
        working system look broken. It belongs in the server log, where
        whoever keeps the system running will look for it.
        """
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)

        def falls_over(employee, from_date, to_date, ctx):
            raise ValueError("relation hr_attendance does not exist LINE 1:")

        self.patch(self.registry['hr.employee'], '_recalc_attendance_one',
                   falls_over)
        self._let_the_scheduler_work(run)

        line = run.log_ids
        told = " ".join(message.body or '' for message in run.message_ids)
        for programmer_text in ("relation hr_attendance", "ValueError", "LINE 1"):
            self.assertNotIn(
                programmer_text, line.error_message,
                "the list the operator reads must not carry the text of the "
                "error itself")
            self.assertNotIn(
                programmer_text, told,
                "and neither must the report they are sent")
        self.assertIn(
            self.employee_1.display_name, told,
            "they must still be told who could not be rebuilt")
        self.assertTrue(
            line.error_message,
            "and be left with something readable on the line, not a blank")

    def test_interrupted_run_continues_where_it_stopped(self):
        """A rebuild cut short by the time limit carries on with the next
        person instead of starting the list again."""
        for employee in self.employees:
            self._a_normal_working_day(employee)
        run, _shown = self._ask_for_a_rebuild()

        # No time at all for a second person in a pass.
        with patch.object(attendance_recalc_run, 'PASS_SECONDS', 0):
            self.env['hr.attendance.recalc.run']._cron_process()
            self.assertEqual(run.done_count, 1,
                             "one pass may only do what fits in it")
            self.assertEqual(run.state, 'running')
            self.assertEqual(run.processed_employee_id, min(self.employees.ids),
                             "where to carry on from must be written down")
            self.env['hr.attendance.recalc.run']._cron_process()
            self.assertEqual(run.done_count, 2)

        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'done')
        self.assertEqual(len(run.log_ids), 3,
                         "nobody may be rebuilt twice and nobody skipped")
        self.assertEqual(set(run.log_ids.employee_id.ids), set(self.employees.ids))

    def test_a_rebuild_that_died_does_not_block_the_next_one(self):
        """A rebuild whose worker was killed is closed, so the queue moves."""
        abandoned, _shown = self._ask_for_a_rebuild(self.employee_1)
        abandoned.state = 'running'
        # The rebuild waiting behind has a day at work to replay. Without one
        # it would finish with nothing rebuilt, which shows the queue moved
        # but not that the work behind it was actually done.
        self._a_normal_working_day(self.employee_2)
        waiting, _shown = self._ask_for_a_rebuild(self.employee_2)

        # Everything still open counts as untouched for too long.
        with patch.object(attendance_recalc_run, 'STALLED_MINUTES', -1):
            self.env['hr.attendance.recalc.run']._cron_process()

        self.assertEqual(abandoned.state, 'failed',
                         "a rebuild nobody is working on must be closed")
        self._let_the_scheduler_work(waiting)
        self.assertEqual(waiting.state, 'done',
                         "the rebuild behind it must still get done")

    def test_a_dead_rebuild_is_closed_for_good_before_the_next_one_is_tried(self):
        """Closing a dead rebuild is kept even when the rebuild behind it
        breaks - otherwise the queue is blocked by the very rebuilds that
        were just cleared, and it stays blocked on every later attempt."""
        abandoned, _shown = self._ask_for_a_rebuild(self.employee_1)
        abandoned.state = 'running'
        waiting, _shown = self._ask_for_a_rebuild(self.employee_2)

        # What the database would have been left holding at each point where
        # the work so far was made permanent.
        kept = []
        self.patch(self.env.cr, 'commit',
                   lambda: kept.append((abandoned.state, waiting.state)))

        def falls_over(run):
            raise ValueError('the worker fell over')

        self.patch(self.registry['hr.attendance.recalc.run'], '_process_pass',
                   falls_over)
        with patch.object(attendance_recalc_run, 'STALLED_MINUTES', -1):
            self.env['hr.attendance.recalc.run']._cron_process()

        self.assertEqual(abandoned.state, 'failed',
                         "a rebuild nobody is working on must be closed")
        self.assertTrue(kept, "the closure must be made permanent")
        self.assertEqual(
            kept[0], ('failed', 'queued'),
            "the dead rebuild must be closed and kept BEFORE the next one is "
            "attempted - kept only afterwards, the breakage takes the closure "
            "down with it")

    def test_operator_is_told_when_there_was_nothing_to_rebuild(self):
        """A site where no area counts towards attendance has no doors to
        read, so a rebuild replays nothing at all. Reporting that as success
        sends the operator away from the setting that is actually wrong."""
        self._a_normal_working_day(self.employee_1)
        # The likeliest misconfiguration, not an edge case.
        self.zone.attendance = False

        run, _shown = self._ask_for_a_rebuild()
        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'nothing',
                         "a rebuild that replayed nothing must not be "
                         "reported as a finished one")
        self.assertEqual(set(run.log_ids.mapped('status')), {'no_events'},
                         "nobody had anything to replay")
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertIn("Nothing was rebuilt", told,
                      "the operator must be told plainly that nothing was done")
        self.assertIn("area", told,
                      "and pointed at the likely cause in their own terms")
        self.assertNotIn("has been rebuilt for", told,
                         "nothing was rebuilt, so nothing may claim it was")

    def test_a_rebuild_that_did_part_of_the_work_is_not_called_empty(self):
        """One person out of three is a finished rebuild. The people left
        alone are counted in the report rather than hidden in it."""
        self._a_normal_working_day(self.employee_1)

        run, _shown = self._ask_for_a_rebuild()
        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'done',
                         "work was done, so this is a finished rebuild")
        statuses = {line.employee_id: line.status for line in run.log_ids}
        self.assertEqual(statuses[self.employee_1], 'done')
        self.assertEqual(statuses[self.employee_2], 'no_events')
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertNotIn("Nothing was rebuilt", told,
                         "somebody was rebuilt, so this is not an empty run")

    def test_the_report_counts_only_the_people_whose_attendance_was_rebuilt(self):
        """Somebody the rebuild failed on has not been rebuilt, and the count
        the operator is given must not include them.

        The number in the report is what they check against the number of
        people they selected. A count that quietly includes the failures
        matches, so nobody goes looking for the ones that did not work.
        """
        for employee in self.employees:
            self._a_normal_working_day(employee)
        run, _shown = self._ask_for_a_rebuild()

        original = self.registry['hr.employee']._recalc_attendance_one
        broken_id = self.employee_2.id

        def sometimes_broken(employee, from_date, to_date, ctx):
            if employee.id == broken_id:
                raise ValueError('door events unreadable')
            return original(employee, from_date, to_date, ctx)

        self.patch(self.registry['hr.employee'], '_recalc_attendance_one',
                   sometimes_broken)
        self._let_the_scheduler_work(run)

        rebuilt = run.log_ids.filtered(lambda line: line.status == 'done')
        self.assertEqual(len(rebuilt), 2,
                         "two of the three were actually rebuilt")
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertNotIn(
            "3 person(s) could not", told,
            "only the one that failed may be reported as failed")
        self.assertIn(
            "1 person(s) could not be rebuilt", told,
            "the operator must be given the true number of people left out")

    def test_a_period_that_was_emptied_is_not_reported_as_rebuilt(self):
        """A rebuild that clears somebody's attendance and puts nothing back
        has not rebuilt them, and must not say it did.

        This is how attendance disappears without anybody noticing: the door
        events are there, so the person looks done, while the days they used
        to have are gone. The operator has to see it on the day, not at the
        end of the month.
        """
        # Something the operator already had, on a day of its own inside the
        # period they are about to rebuild.
        a_quiet_day = self.yesterday - timedelta(days=3)
        # A record the RFID machinery itself made on an earlier run - the
        # only kind a rebuild clears. A typed-in record surviving is its own
        # test (test_zone_autoclose); here the point is the honest report.
        theirs = self.env['hr.attendance'].create({
            'employee_id': self.employee_1.id,
            'check_in': a_quiet_day.replace(hour=9, minute=0, second=0,
                                            microsecond=0),
            'check_out': a_quiet_day.replace(hour=17, minute=0, second=0,
                                             microsecond=0),
            'in_mode': 'rfid',
        })
        # A door event that cannot make a day at work on its own: somebody
        # leaving, with no record of them arriving. Replaying it produces
        # nothing, so the period is cleared and stays empty.
        self._door_event(self.employee_1, self.reader_out,
                         self.yesterday.replace(hour=17, minute=0, second=0,
                                                microsecond=0))

        run, _shown = self._ask_for_a_rebuild(self.employee_1)
        self._let_the_scheduler_work(run)

        self.assertFalse(
            theirs.exists(),
            "the rebuild did clear the period - if it stopped doing that, "
            "this test is no longer about anything")
        self.assertEqual(
            run.log_ids.status, 'no_result',
            "a person whose attendance was cleared with nothing put back "
            "must not be listed as rebuilt")
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertNotIn(
            "has been rebuilt", told,
            "nobody was rebuilt, so nothing may say somebody was")
        self.assertIn(
            "cleared and nothing was put back", told,
            "the operator must be told plainly that the period is now empty")

    def test_a_day_ends_when_midnight_passes_where_the_person_works(self):
        """The last chosen day is covered whole and stops at their midnight,
        not at midnight three hours behind them."""
        self.employee_1.tz = 'Europe/Sofia'
        first_day = fields.Date.today() - timedelta(days=14)
        last_day = first_day + timedelta(days=6)

        # Late on the last day the operator chose - part of it.
        self._door_event(self.employee_1, self.reader_in,
                         self._when_they_are(last_day, 23, 30))
        # Half an hour later by their clock it is already the next day, even
        # though in London it is still the day they chose.
        self._door_event(self.employee_1, self.reader_out,
                         self._when_they_are(last_day + timedelta(days=1), 0, 30))

        run, _shown = self._ask_for_a_rebuild(
            self.employee_1, start=first_day, end=last_day)
        self._let_the_scheduler_work(run)

        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id)])
        self.assertEqual(len(attendance), 1,
                         "the late entry belongs to the last chosen day")
        self.assertEqual(attendance.check_in,
                         self._when_they_are(last_day, 23, 30))
        self.assertFalse(
            attendance.check_out,
            "the exit happened on the day after the one chosen, so it is not "
            "part of this rebuild")

    # ── what must NOT happen ──────────────────────────────────

    def test_rebuild_stops_at_the_last_day_the_operator_chose(self):
        """Attendance after the chosen last day is neither cleared nor
        replayed. The operator scoping a rebuild to one week must keep
        everything they did not ask about, exactly as it was."""
        self.employee_1.tz = 'Europe/Sofia'
        first_day = fields.Date.today() - timedelta(days=14)
        last_day = first_day + timedelta(days=6)
        inside = first_day + timedelta(days=2)
        later = last_day + timedelta(days=3)

        for day in (inside, later):
            self._door_event(self.employee_1, self.reader_in,
                             self._when_they_are(day, 8))
            self._door_event(self.employee_1, self.reader_out,
                             self._when_they_are(day, 17))

        # What the operator already has for a day they did not ask about: the
        # attendance those later door events made as they came in. Nothing is
        # put there by hand over the same hours - two overlapping attendances
        # is a state the product refuses - and this is the stronger record to
        # watch anyway, because its day HAS events waiting to be replayed: a
        # rebuild running one day too far would delete this one and put a
        # freshly made record in its place.
        untouched = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id),
            ('check_in', '>=', self._when_they_are(later, 0)),
        ])
        self.assertEqual(
            len(untouched), 1,
            "the later day must start out with the one attendance its door "
            "events made, otherwise there is nothing to keep")
        as_it_was = (untouched.id, untouched.check_in, untouched.check_out)

        run, _shown = self._ask_for_a_rebuild(
            self.employee_1, start=first_day, end=last_day)
        self._let_the_scheduler_work(run)

        self.assertTrue(
            untouched.exists(),
            "attendance outside the chosen period must survive the rebuild")
        self.assertEqual(
            (untouched.id, untouched.check_in, untouched.check_out), as_it_was,
            "and survive unchanged - it was never part of what was asked for")
        rebuilt = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id)]) - untouched
        self.assertEqual(
            len(rebuilt), 1,
            "only the day inside the chosen period may be replayed")
        self.assertEqual(rebuilt.check_in, self._when_they_are(inside, 8))
        self.assertEqual(rebuilt.check_out, self._when_they_are(inside, 17))

    def test_pressing_run_manually_does_not_do_the_work_in_the_request(self):
        """Started from the interface, the scheduled task only asks for a
        worker - doing the rebuild there would hit the request time limit."""
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)
        as_it_was = self._attendance_as_it_stands(self.employee_1)

        # Something that looks like a live web request to the worker.
        with patch.object(attendance_recalc_run, 'request', object()):
            self.env['hr.attendance.recalc.run']._cron_process()

        self.assertEqual(run.state, 'queued',
                         "no work may be done inside a web request")
        self.assertFalse(run.log_ids)
        self.assertEqual(self._attendance_as_it_stands(self.employee_1),
                         as_it_was,
                         "no attendance may be deleted or replayed inside a "
                         "web request")

    def test_a_forbidden_rebuild_is_refused_before_anything_is_queued(self):
        """When another module forbids rebuilding these people, the operator
        is told on the screen they are looking at - and nothing is queued."""
        self._refuse_every_rebuild()
        before = self.env['hr.attendance.recalc.run'].search_count([])

        with self.assertRaises(UserError):
            self._ask_for_a_rebuild()

        self.assertEqual(self.env['hr.attendance.recalc.run'].search_count([]),
                         before,
                         "a rebuild that may not happen must not be queued")

    def test_a_rebuild_forbidden_after_queueing_never_touches_attendance(self):
        """The answer can change while the request waits its turn: what may
        not be rebuilt when the work starts is not rebuilt."""
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)
        as_it_was = self._attendance_as_it_stands(self.employee_1)

        self._refuse_every_rebuild()
        self._let_the_scheduler_work(run)

        self.assertEqual(self._attendance_as_it_stands(self.employee_1),
                         as_it_was,
                         "attendance must be left exactly as it was")

    def test_being_refused_is_not_the_same_as_breaking_down(self):
        """Told that somebody's records are not for this system to rebuild,
        the operator must be able to tell that apart from a breakdown.

        The two need opposite things from them. A breakdown is worth putting
        right and trying again; a refusal is not - the same request gets the
        same answer for ever, and what to do instead is written in the
        refusal. Reported as a breakdown, the operator keeps starting the
        rebuild and keeps being told the system stopped by a problem.
        """
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)

        self._refuse_every_rebuild()
        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'refused',
                         "a refusal must not be recorded as the rebuild "
                         "having been stopped by a problem")
        self.assertEqual(run.log_ids.status, 'refused',
                         "and the person's line must say the same")
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertNotIn(
            "put the cause right", told,
            "there is no cause to put right, so the operator must not be "
            "sent looking for one")
        self.assertIn(
            "same answer", told,
            "they must be told that asking again changes nothing")

    def test_the_reason_a_rebuild_was_refused_reaches_the_operator_whole(self):
        """What to do instead is at the END of the refusal, so a refusal that
        arrives cut short is a refusal that tells the operator nothing.

        The one refusal this product actually raises runs past five hundred
        characters and finishes with the way out - run the transfer again,
        or choose a period without those records.
        """
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)

        self.assertGreater(
            len(A_REFUSAL_OF_REAL_LENGTH), 500,
            "the refusal being tested with must be as long as a real one, "
            "or it proves nothing about cutting them short")
        self._refuse_every_rebuild()
        self._let_the_scheduler_work(run)

        self.assertIn(
            LAST_WORDS_OF_THE_REFUSAL, run.log_ids.error_message,
            "the line the operator reads must carry the whole reason, "
            "including the part that says what to do instead")
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertIn(
            LAST_WORDS_OF_THE_REFUSAL, told,
            "and so must the report they are sent")

    def test_a_rebuild_asked_for_by_somebody_who_has_left_is_not_carried_out(self):
        """The person who asked has gone by the time their turn comes, so the
        rebuild is refused instead of being done on rights nobody holds.

        The one account this must never catch is the system's own. It is
        switched off permanently by design - core refuses to switch it on at
        all ("You cannot activate the superuser",
        odoo/addons/base/models/res_users.py:597-598) - and it is who a
        rebuild started from a shell or a scheduled action runs as, which is
        how a whole site gets rebuilt. Every other test here runs as it and
        would stop passing the moment it were mistaken for somebody departed.
        """
        self._a_normal_working_day(self.employee_1)
        run, _shown = self._ask_for_a_rebuild(self.employee_1)
        departed = self.env['res.users'].create({
            'name': 'Someone Who Has Left',
            'login': 'rebuild_operator_who_left',
            'lang': 'en_US',
        })
        run.user_id = departed
        as_it_was = self._attendance_as_it_stands(self.employee_1)
        departed.active = False

        self._let_the_scheduler_work(run)

        self.assertEqual(run.state, 'failed',
                         "nobody is left to answer for this rebuild, so it "
                         "must not be carried out")
        # Stopping is not enough on its own: a rebuild simply turned loose on
        # a departed account also stops, by falling over the first thing that
        # account may no longer read - and reports that as a breakdown nobody
        # can act on. The rebuild has to be refused knowingly, and say so.
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertIn(
            "no longer in use", told,
            "the operator must be told the account that asked for this has "
            "gone, not shown whatever the rebuild happened to trip over "
            "while running on it")
        self.assertFalse(run.log_ids,
                         "and nobody may have been rebuilt on the way to "
                         "refusing it")
        self.assertEqual(self._attendance_as_it_stands(self.employee_1),
                         as_it_was,
                         "attendance must be left exactly as it was")

    # ── attendance a person typed in ──────────────────────────

    def test_a_rebuild_never_asks_to_clear_what_somebody_typed_in(self):
        """Attendance entered by hand is not for a rebuild to take.

        Somebody sat down and typed those hours in because the doors did not
        record them - a forgotten badge, a day off site, a correction agreed
        with the person. Nothing in the door events can produce them again, so
        a rebuild that deletes them loses them for good.

        Every record the RFID machinery makes is stamped as its own
        (in_mode 'rfid'), so the rebuild can ask for exactly those and
        nothing else: not manual entries, not kiosk or systray check-ins,
        and nothing outside the chosen period or person.
        """
        period_start, period_end = self.employee_1._recalc_window(
            self.start_date, self.end_date)

        asked_for = self.employee_1._recalc_clear_domain(period_start, period_end)

        self.assertIn(('in_mode', '=', 'rfid'), asked_for,
                      "the rebuild may ask only for the records the machine "
                      "itself made - anything else was put there by a person "
                      "and is not ours to delete")
        self.assertNotIn('|', asked_for,
                         "and there is no branch that widens the asking "
                         "beyond them")
        self.assertIn(('employee_id', '=', self.employee_1.id), asked_for,
                      "and only for this person")
        self.assertIn(('check_in', '>=', period_start), asked_for)
        self.assertIn(('check_in', '<', period_end), asked_for,
                      "and only inside the period that was asked about")

    def test_a_typed_in_record_survives_the_rebuild_that_replays_the_rest(self):
        """The HR officer's own entry outlives a rebuild; the machine's does not.

        A person forgot their badge on Tuesday, so HR typed the day in by
        hand. Later the operator rebuilds the whole week from the door
        events. The week's machine-made attendance is deleted and replayed -
        but the typed-in Tuesday, which no door event can produce again,
        comes out of the rebuild exactly as it went in.
        """
        # The machine records a working day from the door events.
        came_in, went_out = self._a_normal_working_day(self.employee_1)
        made_by_the_machine = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id)])
        self.assertTrue(made_by_the_machine,
                        "walking through the door must record attendance")
        self.assertEqual(set(made_by_the_machine.mapped('in_mode')), {'rfid'},
                         "and what the machine records is stamped as the "
                         "machine's own")

        # HR types in a day the doors never saw, three days earlier.
        typed_in_day = self.yesterday.replace(
            hour=8, minute=0, second=0, microsecond=0) - timedelta(days=3)
        typed_in = self.env['hr.attendance'].create({
            'employee_id': self.employee_1.id,
            'check_in': typed_in_day,
            'check_out': typed_in_day + timedelta(hours=8),
        })
        self.assertNotEqual(typed_in.in_mode, 'rfid',
                            "an entry typed in through the form is nobody's "
                            "machine record")

        run, _shown = self._ask_for_a_rebuild(employees=self.employee_1)
        self._let_the_scheduler_work(run)
        self.assertEqual(run.state, 'done')

        self.assertTrue(typed_in.exists(),
                        "the typed-in day must survive the rebuild - it "
                        "cannot be worked out again from the door events")
        self.assertEqual((typed_in.check_in, typed_in.check_out),
                         (typed_in_day, typed_in_day + timedelta(hours=8)),
                         "and it must say exactly what the person typed")
        replayed = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id),
            ('in_mode', '=', 'rfid')])
        self.assertEqual(
            [(r.check_in, r.check_out) for r in replayed],
            [(came_in, went_out)],
            "while the machine's own record is replayed from the door "
            "events - the same working day once, neither lost nor doubled")

    def test_a_person_still_inside_is_replayed_open_and_stamped(self):
        """An employee still at work when the rebuild runs stays checked in.

        Somebody walked in and has not left yet. The rebuild replays their
        entry as an OPEN attendance - no check-out is invented for them - and
        the open record is stamped as the machine's own, so the next rebuild
        may take it back and replay it again.
        """
        came_in = self.yesterday.replace(hour=8, minute=0, second=0,
                                         microsecond=0)
        self._door_event(self.employee_1, self.reader_in, came_in)

        run, _shown = self._ask_for_a_rebuild(employees=self.employee_1)
        self._let_the_scheduler_work(run)
        self.assertEqual(run.state, 'done')

        replayed = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_1.id)])
        self.assertEqual(len(replayed), 1,
                         "one entry through the door is one attendance")
        self.assertEqual(replayed.check_in, came_in)
        self.assertFalse(replayed.check_out,
                         "no check-out may be invented for a person still "
                         "inside")
        self.assertEqual(replayed.in_mode, 'rfid',
                         "and the open record is stamped as the machine's "
                         "own")


@tagged("post_install", "-at_install", "rfid_attendance_recalc")
class TestOldRebuildsAreClearedAway(TransactionCase):
    """The account of who rebuilt what is kept while it can still be asked
    about, and then it goes.

    "Who rebuilt this month's attendance, and what did it do?" is asked when
    payroll does not add up - weeks after the rebuild, not years. Keeping the
    account for ever grows a table nobody reads; clearing it while a rebuild
    is still being done deletes the job itself.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Run = cls.env['hr.attendance.recalc.run']
        cls.employee = cls.env['hr.employee'].create(
            {'name': 'Rebuild History Employee'})

    def _a_rebuild(self, state, asked_for_days_ago):
        run = self.Run.create({
            'employee_ids': [Command.set(self.employee.ids)],
            'date_from': fields.Date.today() - timedelta(days=7),
            'date_to': fields.Date.today(),
        })
        run.state = state
        # When it was asked for is kept by the database and the ORM will not
        # write it (odoo/orm/models.py:4386-4390 drops it from the values), so
        # it is moved the way core's own tests move it
        # (odoo/addons/hr/tests/test_resource.py:26).
        self.env.cr.execute(
            "UPDATE hr_attendance_recalc_run SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=asked_for_days_ago), run.id),
        )
        run.invalidate_recordset(['create_date'])
        return run

    @property
    def _long_ago(self):
        return attendance_recalc_run.HrAttendanceRecalcRun.GC_DAYS + 1

    def test_a_rebuild_being_worked_on_is_never_cleared_away(self):
        """A rebuild that is waiting or under way is a job, not history.

        Long jobs are exactly the ones that sit in the queue - a year for a
        whole site is asked for once and worked through for as long as it
        takes. Clearing one away because it was asked for a long time ago
        deletes the work while it is being done, and the operator is never
        told.
        """
        waiting = self._a_rebuild('queued', self._long_ago)
        under_way = self._a_rebuild('running', self._long_ago)

        self.Run._gc_recalc_runs()

        self.assertTrue(waiting.exists(),
                        "a rebuild still waiting its turn must survive")
        self.assertTrue(under_way.exists(),
                        "and one being worked on must survive")

    def test_a_recent_rebuild_is_kept_for_whoever_asks_about_it(self):
        """Last week's rebuild is what somebody asks about, so it stays."""
        yesterday = self._a_rebuild('done', 1)

        self.Run._gc_recalc_runs()

        self.assertTrue(yesterday.exists(),
                        "a rebuild from yesterday must still be there to "
                        "answer for itself")

    def test_every_kind_of_finished_rebuild_is_eventually_cleared_away(self):
        """A rebuild that is over is over, whatever came of it.

        Every way a rebuild can end has to age out. One that is left out of
        the clear-out is kept for ever, and nobody notices until the table is
        full of them.
        """
        over = [self._a_rebuild(state, self._long_ago)
                for state in ('done', 'nothing', 'refused', 'failed')]

        self.Run._gc_recalc_runs()

        still_there = [run for run in over if run.exists()]
        self.assertFalse(
            still_there,
            "these ended long ago and must not be kept: %s" % ", ".join(
                run.state for run in still_there))

    def test_a_big_clear_out_is_done_in_pieces_and_asks_to_carry_on(self):
        """The clear-out never tries to empty years of history in one go.

        Deleting everything in a single transaction locks the table and times
        out, which takes down the nightly housekeeping with it. It does a
        bounded piece, says whether there is more, and is called again.
        """
        self.patch(self.registry['hr.attendance.recalc.run'], 'GC_LIMIT', 2)
        mine = [self._a_rebuild('done', self._long_ago) for _each in range(3)]

        cleared, more = self.Run._gc_recalc_runs()

        self.assertEqual(cleared, 2,
                         "one piece is as big as the piece is allowed to be")
        self.assertTrue(more,
                        "and it must say there is more to do, or the rest is "
                        "left until tomorrow")
        for _attempt in range(5):
            _cleared, more = self.Run._gc_recalc_runs()
            if not more:
                break
        self.assertFalse([run for run in mine if run.exists()],
                         "carrying on must finish the job")
        self.assertFalse(more,
                         "and then say there is nothing left, or the "
                         "housekeeping never stops")


@tagged("post_install", "-at_install", "rfid_attendance_recalc")
class TestTransferredAttendanceIsNeverRebuilt(TransactionCase):
    """Attendance that arrived with a transfer is not put through this
    system's own code.

    Business claim (owner, 2026-08-13): transferred data does not go through
    somebody else's code. The record is a transcript of the other system and
    is refreshed by running the transfer again. Rebuilding it deletes the row
    that says which record over there it is, so the next transfer no longer
    recognises it and brings it over a second time.

    Every other test of the refusal in this file puts a stand-in in place of
    the real objection. These two use the real one, raised by the real
    add-on, through the button the operator actually presses.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create(
            {'name': 'Person Who Came With The Transfer'})
        cls.start_date = fields.Date.today() - timedelta(days=10)
        cls.end_date = fields.Date.today()

    def setUp(self):
        super().setUp()
        # The job makes its work permanent as it goes; inside a test the
        # boundary is neutralised the way core neutralises it
        # (odoo/addons/sms_twilio/tests/test_sms_twilio.py:206-212).
        self.patch(self.registry['ir.cron'], '_commit_progress',
                   lambda cron_model, processed=0, remaining=None, **kwargs: 60.0)
        self.patch(self.env.cr, 'commit', lambda: None)
        self.patch(self.env.cr, 'rollback', lambda: None)

    def _the_transfer_or_say_so(self):
        """Refuse to pass quietly when the transfer is not installed."""
        if THE_TRANSFER in self.env:
            return
        _logger.warning(
            "%s is not installed here, so %s did NOT prove that the refusal "
            "to rebuild transferred attendance survives the button the "
            "operator presses. Install it to prove that claim.",
            THE_TRANSFER, self._testMethodName)
        self.skipTest(
            "the data transfer is not installed - the refusal could not be "
            "proven from the operator's button")

    def _an_attendance_that_came_with_the_transfer(self):
        """One attendance, marked exactly as the transfer marks what it brings.

        The naming is taken from the transfer itself rather than written out
        here, so this stops being faithful the day the transfer renames what
        it writes - which is the day it would stop being recognised.
        """
        from odoo.addons.hr_rfid_odoo_import.models.importers.base_importer import (
            EXTERNAL_ID_MODULE, BaseImporter,
        )
        transfer = BaseImporter(
            self.env, 'https://example.invalid', 'old_cloud', 1, 'x', {}, {},
        )
        check_in = fields.Datetime.now() - timedelta(days=2)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_in + timedelta(hours=8),
        })
        which_row_over_there = self.env['ir.model.data'].create({
            'module': EXTERNAL_ID_MODULE,
            'name': transfer._xml_id_name('hr_attendance', 4711),
            'model': 'hr.attendance',
            'res_id': attendance.id,
        })
        return attendance, which_row_over_there

    def test_the_operator_is_stopped_at_the_button(self):
        """Pressing Re-create Attendance for somebody whose attendance came
        with a transfer is answered there and then, and queues nothing."""
        self._the_transfer_or_say_so()
        attendance, which_row_over_there = self._an_attendance_that_came_with_the_transfer()
        queued_before = self.env['hr.attendance.recalc.run'].search_count([])

        wizard = self.env['hr.attendance.recalc.wizard'].create({
            'employee_ids': [Command.set(self.employee.ids)],
            'start_date': self.start_date,
            'end_date': self.end_date,
        })
        with self.assertRaises(UserError) as caught:
            wizard.execute()

        self.assertIn(LAST_WORDS_OF_THE_REFUSAL, str(caught.exception),
                      "and told what to do instead")
        self.assertEqual(
            self.env['hr.attendance.recalc.run'].search_count([]),
            queued_before,
            "nothing may be queued that will only be refused later")
        self.assertTrue(attendance.exists(),
                        "the transferred attendance must still be there")
        self.assertTrue(
            which_row_over_there.exists(),
            "and so must the row that says which record over there it is - "
            "without it the next transfer brings it over a second time")

    def test_a_rebuild_already_queued_still_leaves_transferred_records_alone(self):
        """The button is not the only way in: a rebuild queued before the
        transfer ran, or resumed after it, reaches the work itself.

        This is the path that matters - the one where attendance is deleted
        before it is replayed - so the refusal has to hold there too, and be
        reported as a refusal rather than as the rebuild breaking down.
        """
        self._the_transfer_or_say_so()
        attendance, which_row_over_there = self._an_attendance_that_came_with_the_transfer()
        as_it_was = (attendance.check_in, attendance.check_out)

        run = self.env['hr.attendance.recalc.run'].create({
            'employee_ids': [Command.set(self.employee.ids)],
            'date_from': self.start_date,
            'date_to': self.end_date,
        })
        run.action_start()
        for _pass in range(5):
            if run.state not in ('queued', 'running'):
                break
            self.env['hr.attendance.recalc.run']._cron_process()

        self.assertTrue(attendance.exists(),
                        "the transferred attendance must survive the rebuild")
        self.assertEqual((attendance.check_in, attendance.check_out), as_it_was,
                         "and survive unchanged")
        self.assertTrue(
            which_row_over_there.exists(),
            "the row that says which record over there it is must survive "
            "too - the next transfer recognises it by that and nothing else")
        self.assertEqual(run.state, 'refused',
                         "this is a refusal, not the rebuild breaking down")
        self.assertEqual(run.log_ids.status, 'refused')
        told = " ".join(message.body or '' for message in run.message_ids)
        self.assertIn(LAST_WORDS_OF_THE_REFUSAL, told,
                      "and the operator must be told what to do instead")


@tagged("post_install", "-at_install", "rfid_attendance_recalc")
class TestAnOperatorsWordSurvivesTheRebuild(TransactionCase):
    """The operator who fixes what a worker forgot must not be undone.

    A worker badges in and forgets to badge out. The operator types the real
    leaving time into that same record. From that moment the record is the
    operator's word about the day - the door events do not hold it, so no
    delete-and-replay may take it away or write a second record next to it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref(
            'hr_attendance_multi_rfid.hr_attendance_multi_rfid_recalc_cron'
        ).active = True
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Forgetful Worker', 'company_id': cls.company.id,
        })
        webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'WS Preserve', 'serial': '777001', 'key': '0000',
            'company_id': cls.company.id, 'available': 'a',
            'tz': 'UTC', 'active': True,
        })
        ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Ctrl Preserve', 'ctrl_id': 77, 'webstack_id': webstack.id,
            'hw_version': '12', 'serial_number': '777', 'sw_version': '030',
            'mode': 1, 'inputs': 1, 'outputs': 1, 'readers': 2,
        })
        door = cls.env['hr.rfid.door'].create({
            'name': 'Door Preserve', 'number': 1, 'controller_id': ctrl.id,
            'company_id': cls.company.id,
        })
        cls.reader_in = cls.env['hr.rfid.reader'].create({
            'name': 'In', 'number': 1, 'reader_type': '0', 'mode': '01',
            'controller_id': ctrl.id, 'door_id': door.id,
        })
        cls.reader_out = cls.env['hr.rfid.reader'].create({
            'name': 'Out', 'number': 2, 'reader_type': '1', 'mode': '01',
            'controller_id': ctrl.id, 'door_id': door.id,
        })
        cls.env['hr.rfid.zone'].create({
            'name': 'Zone Preserve', 'company_id': cls.company.id,
            'attendance': True, 'door_ids': [(4, door.id)],
        })
        cls.day = (fields.Datetime.now() - timedelta(days=7)).replace(
            hour=0, minute=0, second=0, microsecond=0)

    def _door_event(self, reader, moment):
        return self.env['hr.rfid.event.user'].create({
            'employee_id': self.employee.id,
            'door_id': reader.door_id.id,
            'reader_id': reader.id,
            'event_action': '1',
            'event_time': moment,
        })

    def _day_records(self):
        return self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', self.day),
            ('check_in', '<', self.day + timedelta(days=1)),
        ], order='check_in')

    def _rebuild(self):
        ctx = self.employee._recalc_attendance_context()
        self.employee._recalc_attendance_one(
            self.day.date(), self.day.date(), ctx)

    def test_the_checkout_the_operator_typed_survives_a_rebuild(self):
        """The worker forgot to badge out; the operator typed 21:15 into the
        machine's record. A rebuild keeps that 21:15 - it does not replay
        the day back to an open record, and it does not write a twin."""
        self._door_event(self.reader_in, self.day.replace(hour=8))
        self._rebuild()
        record = self._day_records()
        self.assertEqual(len(record), 1)
        self.assertFalse(record.check_out, "the forgotten day starts open")
        self.assertEqual(record.in_mode, 'rfid')

        record.write({'check_out': self.day.replace(hour=21, minute=15)})
        self.assertEqual(record.in_mode, 'manual',
                         "the operator's edit takes the record over")

        self._rebuild()
        after = self._day_records()
        self.assertEqual(len(after), 1,
                         "no twin may appear next to the operator's record")
        self.assertEqual(after.check_out, self.day.replace(hour=21, minute=15),
                         "the operator's leaving time is the day's truth")

    def test_a_machine_close_stays_the_machines_and_is_still_rebuildable(self):
        """NEGATIVE: the zone sweep's administrative close is not a human
        statement - the record stays 'rfid' and the next rebuild may replay
        it from the door events."""
        zone = self.env['hr.rfid.zone'].search(
            [('name', '=', 'Zone Preserve')])
        zone.write({'max_time_in_zone': 10.0,
                    'auto_close_time_for_zone': 7.0})
        self._door_event(self.reader_in, self.day.replace(hour=8))
        self._rebuild()
        record = self._day_records()
        record.with_context(rfid_machinery_write=True).write(
            {'in_zone_id': zone.id})

        record.autoclose_attendance()
        self.assertTrue(record.check_out)
        self.assertEqual(record.in_mode, 'rfid',
                         "an administrative close must stay the machine's")
        self.assertEqual(record.out_mode, 'auto_check_out')

    def test_door_events_under_the_operators_record_make_no_second_record(self):
        """The operator recorded the whole day by hand; the door events of
        that day are already accounted for. A rebuild must not turn them
        into a second, overlapping record - the day would count twice.

        The realistic path: the door events arrive and the machinery makes
        its record at once; the operator finds it wrong, deletes it and
        types the whole day themselves. The events are still there - only
        the rebuild's restraint keeps the day single."""
        self._door_event(self.reader_in, self.day.replace(hour=8, minute=3))
        self._door_event(self.reader_out, self.day.replace(hour=16, minute=40))
        made_by_the_machine = self._day_records()
        self.assertTrue(made_by_the_machine,
                        "the events must have made the machine's record")
        made_by_the_machine.unlink()
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': self.day.replace(hour=8),
            'check_out': self.day.replace(hour=17, minute=30),
        })

        self._rebuild()
        after = self._day_records()
        self.assertEqual(
            len(after), 1,
            "one day, one record - the person's; no machine twin beside it")
        self.assertEqual(after.in_mode, 'manual')
        self.assertEqual(after.check_out, self.day.replace(hour=17, minute=30))

    def test_events_straddling_the_operators_record_make_no_twin(self):
        """The events sit AROUND the operator's record, not inside it.

        The person badged at 08:30 and 17:30; the operator recorded the day
        as 09:00-17:00. Replaying the pair would put a record right across
        theirs - the day counted twice, and two overlapping records for one
        day is what core's overtime engine refuses outright. Only the
        collision guard stops it: the events fall outside the record, so
        consuming them one by one is not enough.
        """
        self._door_event(self.reader_in, self.day.replace(hour=8, minute=30))
        self._door_event(self.reader_out, self.day.replace(hour=17, minute=30))
        self._day_records().unlink()
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': self.day.replace(hour=9),
            'check_out': self.day.replace(hour=17),
        })

        self._rebuild()
        after = self._day_records()
        self.assertEqual(len(after), 1,
                         "the straddling pair must not become a second record")
        self.assertEqual(after.check_in, self.day.replace(hour=9))
        self.assertEqual(after.check_out, self.day.replace(hour=17))

    def test_an_open_record_of_a_person_owns_the_rest_of_the_day(self):
        """An operator's record left open is a standing statement.

        They wrote "this person is in from 08:00" and have not closed it.
        Door events after that moment belong to that statement - the rebuild
        may not write records over the top of it. It stays as they left it.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': self.day.replace(hour=8),
        })
        self._door_event(self.reader_in, self.day.replace(hour=10))
        self._door_event(self.reader_out, self.day.replace(hour=16))

        self._rebuild()
        after = self._day_records()
        self.assertEqual(len(after), 1,
                         "nothing may be written under an open statement")
        self.assertFalse(after.check_out, "and it stays open, as they left it")
        self.assertEqual(after.in_mode, 'manual')

    def test_a_batch_edit_takes_over_only_the_machines_records(self):
        """NEGATIVE: editing several rows at once (the core list does that)
        takes over the machine's rows and leaves a person's own alone."""
        # Two people, same day: one row the machine made, one the operator
        # typed in. This is the shape a mass edit really has - one value
        # written across rows of DIFFERENT people (two rows of the same
        # person given one time would overlap, which core refuses outright).
        colleague = self.env['hr.employee'].create({
            'name': 'Second Worker', 'company_id': self.company.id,
        })
        machine = self.env['hr.attendance'].with_context(
            rfid_machinery_write=True).create({
                'employee_id': self.employee.id,
                'check_in': self.day.replace(hour=8),
                'check_out': self.day.replace(hour=16),
                'in_mode': 'rfid',
            })
        typed_in = self.env['hr.attendance'].create({
            'employee_id': colleague.id,
            'check_in': self.day.replace(hour=8),
            'check_out': self.day.replace(hour=16),
        })
        self.assertEqual(typed_in.in_mode, 'manual')

        # The operator selects both rows and corrects the leaving time. The
        # edit comes through a CLEAN recordset, the way the web client sends
        # it - a machine flag lives on the recordset's context, so writing
        # back through the very recordset the machinery created would carry
        # its flag along and prove nothing.
        both = self.env['hr.attendance'].browse((machine | typed_in).ids)
        both.write({'check_out': self.day.replace(hour=17)})
        machine.invalidate_recordset()
        typed_in.invalidate_recordset()

        self.assertEqual(machine.in_mode, 'manual',
                         "the machine's row was edited - it is theirs now")
        self.assertEqual(typed_in.in_mode, 'manual',
                         "and a row that was already theirs is untouched")

    def test_the_core_calendar_close_leaves_the_record_rebuildable(self):
        """NEGATIVE: core's own calendar-based check-out closes a forgotten
        record too - and that is still the machine talking, so the record
        keeps its origin and a later rebuild may replay it."""
        self.env.company.auto_check_out = True
        self.env['hr.attendance'].with_context(
            rfid_machinery_write=True).create({
                'employee_id': self.employee.id,
                'check_in': fields.Datetime.now() - timedelta(hours=30),
                'in_mode': 'rfid',
            })

        self.env['hr.attendance']._cron_auto_check_out()

        closed = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee.id)], order='check_in desc',
            limit=1)
        self.assertTrue(closed.check_out, "core must have closed it")
        self.assertEqual(closed.in_mode, 'rfid',
                         "an automatic close is not a person's statement")
