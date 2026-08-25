# -*- coding: utf-8 -*-
"""Rebuilding attendance is a job, not a click.

Rebuilding one employee means deleting a period of attendance and replaying
every door event in it, and a site has hundreds of employees. Done inside the
screen the operator pressed, it is cut off after ``limit_time_real`` seconds
(120 on a standard install) and the operator is left with attendance that was
half deleted and never rebuilt. The scheduler thread is NOT exempt either -
``limit_time_real_cron`` only replaces the limit when it is positive, and
exceeding it does not merely stop the job, it restarts the server. So the work
is done in pieces, each committed, each small enough to finish.

The request itself cannot live on the wizard: that is a TransientModel and the
cleaner removes it after an hour, taking the whole job with it. Odoo core makes
the same split - account.move.send.batch.wizard is transient, while the state
lives on the permanent account.move.sending_data
(odoo/addons/account/wizard/account_move_send_batch_wizard.py:105-109).

The shape below is deliberately the same as hr_rfid_odoo_import/models/
import_run.py, so this codebase has one pattern for long jobs and not two.
"""
import logging
import time
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)

#: How long one pass may spend rebuilding before it stops and asks for another.
#: One scheduler wake-up calls the job at least ten times inside a ten-second
#: budget (odoo/odoo/addons/base/models/ir_cron.py:31-37), and the whole thread
#: is capped at limit_time_real. A pass that overruns does not just fail - it
#: brings the server down with it, so this is a safety parameter, not a tuning
#: knob.
PASS_SECONDS = 5.0

#: A rebuild untouched for this long is treated as dead. Long enough that a
#: slow employee is never mistaken for a stalled job, short enough that a
#: half-finished rebuild does not block every later one for a working day.
STALLED_MINUTES = 30

#: How many people are named in a summary before it switches to a count. A
#: message that lists four hundred names is a message nobody reads.
NAMES_SHOWN = 8

#: A rebuild in one of these is over, whatever came of it. Anything else is
#: still on its way and must never be tidied away or offered a "carry on".
FINISHED_STATES = ('done', 'nothing', 'refused', 'failed')


class HrAttendanceRecalcRun(models.Model):
    _name = 'hr.attendance.recalc.run'
    _description = 'Attendance Rebuild'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    #: Runs removed per vacuum pass. Bounded on purpose: deleting years of
    #: history in one transaction locks the table and times out
    #: (odoo/odoo/addons/base/models/ir_cron.py:906-915 is the shape).
    GC_LIMIT = 500
    #: A week. Long enough to answer "what did yesterday's rebuild do?" while
    #: anybody still cares, and short enough that the log does not become an
    #: archive: the attendance itself is the record, this is only the receipt
    #: of the job that rebuilt it (owner's decision, 24.08.2026).
    GC_DAYS = 7

    name = fields.Char(
        compute='_compute_name', store=True,
        help="Short label of this rebuild, built from the period it covers.",
    )
    state = fields.Selection(
        [
            ('queued', 'Waiting to start'),
            ('running', 'In progress'),
            ('done', 'Finished'),
            # A rebuild that found nothing to replay is neither a success nor a
            # breakdown, and calling it either one misleads: the commonest
            # reason is that no zone counts towards attendance, which the
            # operator can put right in a minute once they are told.
            ('nothing', 'Nothing to rebuild'),
            # Being told "these records are not for this system to rebuild" is
            # not the rebuild breaking down, and it must not be dressed as one:
            # nothing is broken, nothing can be put right, and asking again
            # gets the same answer.
            ('refused', 'Refused'),
            ('failed', 'Stopped by a problem'),
        ],
        default='queued', required=True, tracking=True, index=True,
        help="Where this rebuild has got to. It continues on its own; you can "
             "close the page.",
    )
    user_id = fields.Many2one(
        'res.users', string='Started by', required=True, index=True,
        default=lambda self: self.env.user,
        help="Who asked for the rebuild. The work runs in the background, so "
             "this is who gets told when it finishes.",
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company,
        help="The company this rebuild was started for.",
    )
    date_from = fields.Date(
        string='From', required=True,
        help="Attendance is rebuilt from this day onwards.",
    )
    date_to = fields.Date(
        string='To', required=True,
        help="Last day the rebuild covers.",
    )
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        help="The people whose attendance is being rebuilt, as chosen when "
             "the rebuild was asked for. Somebody taken on afterwards is not "
             "added to it. If this list is changed while the rebuild is under "
             "way, the change applies from the next person onwards - anybody "
             "already finished is not done a second time.",
    )
    processed_employee_id = fields.Integer(
        readonly=True,
        help="Where to carry on from. The work is done one person at a time, "
             "and this is the last one finished - so a rebuild that was "
             "interrupted picks up instead of starting again.",
    )
    current_employee_id = fields.Many2one(
        'hr.employee', string='Working on', readonly=True,
        help="The person being rebuilt right now.",
    )
    # Deliberately NOT "people finished": it counts everybody the rebuild has
    # got through, and getting through somebody includes finding nothing to do
    # for them and failing on them. What actually came of each person is on the
    # list below, and the summary at the end says how many were rebuilt.
    done_count = fields.Integer(
        string='People dealt with', readonly=True,
        help="How many of the people on the list the rebuild has got through "
             "so far - whether or not there was anything to rebuild for them, "
             "and whether or not it worked. What came of each one is on the "
             "list below.",
    )
    total_count = fields.Integer(
        string='People in total', readonly=True,
        help="How many people this rebuild covers.",
    )
    progress = fields.Integer(
        compute='_compute_progress',
        help="How far along the rebuild is.",
    )
    log_ids = fields.One2many(
        'hr.attendance.recalc.log', 'run_id', string='What happened',
        help="One line per person, with what was rebuilt and what was not.",
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for run in self:
            run.name = self.env._(
                "Attendance rebuild %(start)s - %(end)s",
                start=run.date_from or '?',
                end=run.date_to or '?',
            )

    @api.depends('done_count', 'total_count')
    def _compute_progress(self):
        for run in self:
            run.progress = int(run.done_count * 100 / run.total_count) if run.total_count else 0

    # ── Lifecycle ─────────────────────────────────────────────

    def action_start(self):
        """Ask for the work to begin. Returns at once."""
        self.ensure_one()
        # Written only when it is not already what it says. A rebuild the
        # worker has in hand must not be written to from a web request at
        # all: the two transactions touch the same row and the request loses
        # with "could not serialize access due to concurrent update" - a
        # server error on the operator's screen while the system is working
        # perfectly well.
        if self.state != 'queued':
            self.state = 'queued'
        # How many people this covers is known the moment it is asked for.
        # Left to the worker, the operator opens a rebuild of 208 people and
        # reads "0 people in total" until the scheduler comes round - which
        # looks like an empty request, not a waiting one.
        if self.total_count != len(self.employee_ids):
            self.total_count = len(self.employee_ids)
        self._wake_the_worker()
        return True

    def action_refresh(self):
        """Show what the rebuild has got to by now.

        Reading, never writing. The progress bar does not move on its own,
        so the operator is given a way to look again - but looking must not
        touch the record the worker is updating, which is what an earlier
        "Continue now" button did: it set the state on every press and
        collided with the running worker.

        The worker is nudged as well, in case the scheduler has not come
        round yet; that writes a trigger row of its own and never the
        rebuild (ir_cron._trigger_list, base/models/ir_cron.py:781-785).
        """
        self.ensure_one()
        if self.state in ('queued', 'running'):
            self._wake_the_worker()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def _wake_the_worker(self):
        cron = self.env.ref(
            'hr_attendance_multi_rfid.hr_attendance_multi_rfid_recalc_cron',
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger()

    def _for_the_operator(self):
        """This record, read in the language of whoever asked for the rebuild.

        The background work runs as the scheduler's user, so anything written
        here would otherwise reach the operator in somebody else's language.
        """
        self.ensure_one()
        return self.with_context(lang=self.user_id.lang or self.env.lang)

    def _finish(self, state, message=None):
        """End the rebuild and tell the person who asked for it."""
        self.ensure_one()
        self.write({'state': state, 'current_employee_id': False})
        if message:
            self.message_post(body=message)
            self._tell_the_operator(state, message)

    def _tell_the_operator(self, state, message):
        """Put the result on the screen of whoever asked for it.

        The note on the record is for whoever reads it later; this is for the
        person still waiting. Core sends both - a live message and a durable
        one (odoo/addons/account/models/account_move_send.py:531-552, and the
        plain form used here, odoo/addons/hr_timesheet/models/hr_timesheet.py:352).
        """
        self.ensure_one()
        if not self.user_id:
            return
        self.user_id._bus_send('simple_notification', {
            # Only a rebuild that actually rebuilt something is green. One that
            # found nothing has to be read, not glanced at.
            'type': 'success' if state == 'done' else 'warning',
            'title': self._for_the_operator().env._("Attendance rebuild"),
            'message': message,
            # Kept on screen when something went wrong: a warning nobody sees
            # is the same as no warning at all.
            'sticky': state != 'done',
        })

    # ── The worker ────────────────────────────────────────────

    @api.model
    def _cron_process(self):
        """One pass of work. Called by the scheduler.

        Pressed from the interface instead, this would do the whole job inside
        the HTTP request and hit the request time limit - so from there it only
        wakes the scheduler up. Core does the same
        (odoo/addons/cloud_storage_migration/models/ir_attachment.py:74-78).
        """
        if request:
            self.env['hr.attendance.recalc.run']._wake_the_worker()
            return
        if self._abandon_stalled_runs():
            # Closing the dead rebuilds is a finished piece of work in its own
            # right, so it is kept before the next one is started. The pass
            # below rolls the transaction back when it fails - and that would
            # otherwise undo exactly the closures that unblock the queue,
            # leaving the same dead rebuilds in the way on every wake-up. Core
            # keeps each completed unit before beginning the next the same way
            # (odoo/addons/mail/models/fetchmail.py:340).
            self.env.cr.commit()
        run = self.search([('state', 'in', ('queued', 'running'))],
                          order='create_date asc', limit=1)
        if not run:
            return
        try:
            run._process_pass()
        except Exception as exc:
            # Without this the rebuild stays queued forever and, because it is
            # the oldest, it is picked again on every wake-up - blocking every
            # later rebuild behind it. The scheduler only runs daily, so that
            # is a queue nobody notices is stuck.
            # What went wrong belongs here, with its traceback, where whoever
            # keeps the system running will look for it. It does not belong in
            # the message below: the operator can do nothing with the text of
            # a database error, and reading one on their screen only makes a
            # working system look broken.
            _logger.error("Attendance rebuild %s could not be worked on: %s",
                          run.id, exc, exc_info=True)
            self.env.cr.rollback()
            run._finish('failed', run._for_the_operator().env._(
                "The rebuild stopped because of a problem in the system "
                "itself, and not with any of the people on the list. Nothing "
                "was changed by this attempt. Start it again; if it stops a "
                "second time, your system administrator can see what went "
                "wrong."
            ))
            self.env.cr.commit()

    @api.model
    def _abandon_stalled_runs(self):
        """End rebuilds that stopped being worked on.

        A pass that dies outright - the process is killed, the server restarts
        halfway through somebody - leaves the rebuild sitting in "In progress"
        for good, and every rebuild asked for afterwards waits behind it.

        :return: the rebuilds that were closed, so the caller knows there is
            something worth keeping before it starts the next pass
        """
        cutoff = fields.Datetime.now() - timedelta(minutes=STALLED_MINUTES)
        stalled = self.search([
            ('state', '=', 'running'),
            ('write_date', '<', cutoff),
        ])
        for run in stalled:
            _logger.warning(
                "Attendance rebuild %s has not moved since %s - abandoning it",
                run.id, run.write_date)
            run._finish('failed', run._for_the_operator().env._(
                "This rebuild stopped without finishing and has been closed. "
                "The people it had already done keep their rebuilt attendance. "
                "Start a new one for the rest when you are ready."
            ))
        return stalled

    def _process_pass(self):
        """Rebuild as many people as fit in this pass."""
        self.ensure_one()
        # Another worker may have taken this job between the search and here.
        # The lock skips a row it cannot take rather than waiting for it, so
        # the answer is in what comes back, not in whether it raised: an empty
        # result means somebody else has this rebuild and we leave it to them
        # (odoo/addons/mail/models/fetchmail.py:276 reads it the same way).
        if not self.try_lock_for_update():
            return
        self.invalidate_recordset(['state', 'processed_employee_id'])
        if self.state not in ('queued', 'running'):
            return

        # Ordered by id and resumed on "greater than the last one done": that
        # is monotone and index-backed, and it does not care whether somebody
        # was added to or removed from the list while the job was waiting.
        all_ids = sorted(self.employee_ids.ids)
        todo = [eid for eid in all_ids if eid > self.processed_employee_id]
        self.write({'state': 'running', 'total_count': len(all_ids)})
        if not todo:
            self._finish_reporting_outcome()
            return

        worker = self._as_the_operator_would()
        if worker is None:
            self._finish('failed', self._for_the_operator().env._(
                "This rebuild cannot be carried out: the account that asked "
                "for it is no longer in use. Ask for it again from an active "
                "account."
            ))
            return

        # Seeds how much is left before any of it is done, so an interrupted
        # pass is rescheduled at once instead of waiting for the next daily
        # run (odoo/addons/sale/models/sale_order.py:1307-1317).
        self.env['ir.cron']._commit_progress(remaining=len(todo))

        ctx = worker._recalc_attendance_context()
        deadline = time.monotonic() + PASS_SECONDS
        for position, employee_id in enumerate(todo, start=1):
            # Browsed one at a time: every person ends in a commit, which
            # empties the cache, and walking a recordset across that re-reads
            # the whole remainder each time
            # (odoo/addons/sale/models/sale_order.py:1310 does the same).
            employee = worker.browse(employee_id)
            self.current_employee_id = employee_id
            self._run_one_employee(employee, ctx)
            time_left = self._save_progress(employee_id,
                                            remaining=len(todo) - position)
            if time_left <= 0 or time.monotonic() > deadline:
                # Out of time. The rest waits for the next pass; the cursor
                # above means nobody is rebuilt twice.
                self._wake_the_worker()
                return

        self._finish_reporting_outcome()

    def _as_the_operator_would(self):
        """The employee model as the person who asked for the rebuild sees it.

        The work must do exactly what that person could have done themselves.
        Left to the scheduler's own account it would run with rights they do
        not have, and it would read the company settings off the wrong company
        - which decides which attendance is deleted.

        Returns None when that account is no longer in use, because carrying
        on would mean doing it with more rights than were ever granted.

        The superuser is the one account for which being switched off means
        nothing of the sort: it is switched off permanently and by design -
        core refuses to switch it on at all ("You cannot activate the
        superuser", odoo/addons/base/models/res_users.py:597-598) - and it is
        the account every rebuild started outside a browser runs under, from a
        shell or a scheduled action. Refusing those would turn the commonest
        way of rebuilding a year for a whole site into a rebuild that reports
        a departed operator who never existed. Core treats it as a legitimate
        user to work as, not as an archived one (models.py:5981-5988: "by
        convention, the superuser is always in superuser mode").
        """
        self.ensure_one()
        if not self.user_id:
            return None
        if not self.user_id.active and not self.user_id._is_superuser():
            return None
        return self.env['hr.employee'].with_user(self.user_id).with_company(
            self.company_id)

    def _run_one_employee(self, employee, ctx):
        """Rebuild one person. A failure here must not cost the others.

        One person is the whole unit: their attendance for the period is
        deleted before it is replayed, so stopping halfway through one would
        leave that person with history removed and nothing put back.
        """
        self.ensure_one()
        # Permission is asked first and on its own. A refusal and a breakdown
        # both arrive as the same kind of error, and only where it came from
        # tells them apart - reading the words would stop working the moment
        # they are translated. Asking here costs one question per person and
        # buys the difference between "this cannot be rebuilt here, and here
        # is what to do instead" and "something went wrong, try again".
        # Nothing is skipped by asking early: the rebuild itself asks again
        # before it touches anything.
        try:
            employee._check_recalc_allowed(self.date_from, self.date_to)
        except AccessError as exc:
            # Not an objection to the rebuild - the account simply may not
            # read something. Nothing to put right by running a transfer, so
            # it is reported with the breakdowns.
            self._breakdown_on_employee(employee, exc)
            return
        except UserError as refusal:
            # The one way an add-on refuses (hr_rfid/models/hr_employee.py,
            # _check_recalc_allowed).
            #
            # What is refused is REPLAYING their attendance from the door
            # events - it would break the link with the system the records
            # came from. Measuring the days again touches no attendance at
            # all: it only reads what is there and writes the daily figures.
            # So it still happens, or these people would be the only ones on
            # the screen still showing what an older calculation said, with
            # nothing an operator could press to put it right.
            try:
                with self.env.cr.savepoint():
                    employee._recompute_daily_figures(
                        self.date_from, self.date_to)
            except Exception:
                _logger.warning(
                    "Could not refresh the daily figures of %s after the "
                    "rebuild was refused for them; their older figures stand.",
                    employee.display_name, exc_info=True)
            self._refusal_on_employee(employee, refusal)
            return
        try:
            with self.env.cr.savepoint():
                result = employee._recalc_attendance_one(
                    self.date_from, self.date_to, ctx)
        except Exception as exc:
            # The savepoint has already undone everything this person's rebuild
            # wrote, and cleared the cache with it (_FlushingSavepoint.rollback,
            # odoo/sql_db.py:137-140). Nothing else may be undone here: a plain
            # cr.rollback() goes back to the last COMMIT, which throws away every
            # person already rebuilt in this pass - and inside a test it discards
            # the fixture and the run itself, which is how this was caught.
            # Durability is not this method's job either: _save_progress runs on
            # the very next line of the loop and commits through the scheduler.
            self._breakdown_on_employee(employee, exc)
            return
        self._log_employee(
            employee,
            status=self._outcome_of(result or {}),
            result=result,
        )

    @staticmethod
    def _outcome_of(result):
        """What actually came of one person's rebuild.

        Three outcomes, not two. Door events that produce no attendance at all
        are not a rebuild: that person's period was cleared and nothing went
        back into it, which the operator has to see rather than read as
        "Rebuilt" and never look at again.
        """
        if result.get('attendance_count'):
            return 'done'
        if result.get('event_count'):
            return 'no_result'
        return 'no_events'

    def _breakdown_on_employee(self, employee, exc):
        """Record that this person could not be rebuilt.

        What went wrong goes to the server log with its traceback, because
        that is where whoever keeps the system running will look for it. The
        operator gets told what it means for them instead: this person was
        left alone, and somebody else has to look at it.
        """
        self.ensure_one()
        _logger.error(
            "Attendance rebuild %s failed on employee %s: %s",
            self.id, employee.id, exc, exc_info=True)
        speaking_to_them = self._for_the_operator()
        self._log_employee(employee, status='error', message=speaking_to_them.env._(
            "Something went wrong while this person was being rebuilt. Their "
            "attendance was put back the way it was. Your system "
            "administrator can see what happened."
        ))
        self.message_post(body=speaking_to_them.env._(
            "Attendance for %(person)s could not be rebuilt and was left "
            "exactly as it was. Your system administrator can see what went "
            "wrong.",
            person=employee.display_name,
        ))

    def _refusal_on_employee(self, employee, refusal):
        """Record that this person's attendance is not for us to rebuild.

        Nothing is broken here, so nothing is written to the log as if it
        were, and no traceback is kept. The reason was written for the
        operator by whoever refused - it says what to do instead - so it is
        passed on whole rather than cut to fit a column.
        """
        self.ensure_one()
        reason = str(refusal)
        _logger.info(
            "Attendance rebuild %s: employee %s may not be rebuilt: %s",
            self.id, employee.id, reason)
        self._log_employee(employee, status='refused', message=reason)
        self.message_post(body=plaintext2html(
            self._for_the_operator().env._(
                "Attendance for %(person)s was not rebuilt.\n\n%(reason)s",
                person=employee.display_name, reason=reason,
            )))

    def _save_progress(self, employee_id, remaining):
        """Record how far we got and hand the time budget back."""
        self.write({
            'processed_employee_id': employee_id,
            'done_count': self.done_count + 1,
        })
        # Commits, records how far we got, and returns the seconds left in this
        # scheduler slice. Called outside the savepoint above on purpose:
        # committing inside an open savepoint destroys it.
        # Passing what is left lets core reschedule itself immediately. Without
        # it core computes zero remaining, calls the job fully done
        # (odoo/odoo/addons/base/models/ir_cron.py:525-529), and the rest of
        # the people wait for the next daily run.
        return self.env['ir.cron']._commit_progress(processed=1,
                                                    remaining=remaining)

    def _log_employee(self, employee, status, result=None, message=None):
        self.ensure_one()
        self.env['hr.attendance.recalc.log'].create({
            'run_id': self.id,
            'employee_id': employee.id,
            'status': status,
            'event_count': (result or {}).get('event_count', 0),
            'attendance_count': (result or {}).get('attendance_count', 0),
            'error_message': message or '',
        })

    def _finish_reporting_outcome(self):
        """End the rebuild, saying plainly what came of it.

        More can come of a rebuild than "it worked" and "it broke". It can do
        the work; it can fail somebody; it can be told that somebody's records
        are not for this system to rebuild; it can clear a period and find the
        door events make no attendance at all; and it can find nothing to
        replay in the first place - which is the likeliest of them all when
        something is set up wrong, because a site with no zone counting
        towards attendance has no doors to read.

        Telling the operator "finished" over any of the others is worse than
        telling them nothing: they close the page and find out at the end of
        the month, when payroll does not add up.
        """
        self.ensure_one()
        run = self._for_the_operator()
        broken = run.log_ids.filtered(lambda line: line.status == 'error')
        refused = run.log_ids.filtered(lambda line: line.status == 'refused')
        rebuilt = run.log_ids.filtered(lambda line: line.status == 'done')
        cleared = run.log_ids.filtered(lambda line: line.status == 'no_result')
        untouched = run.log_ids.filtered(lambda line: line.status == 'no_events')

        # Whether the sentence chosen below already accounts for the people it
        # does not name, so that they are not counted twice - or, worse, left
        # out of the report altogether.
        said_the_cleared = said_the_untouched = False

        if broken:
            state, said = 'failed', run.env._(
                "The rebuild finished, but attendance for %(count)s person(s) "
                "could not be rebuilt: %(people)s. Everybody else is done. "
                "Look at the list below, put the cause right, and start a "
                "rebuild for those people again.",
                count=len(broken), people=run._name_a_few(broken),
            )
        elif rebuilt:
            state, said = 'done', run.env._(
                "Attendance has been rebuilt for %(count)s person(s).",
                count=len(rebuilt),
            )
        elif cleared:
            said_the_cleared = True
            state, said = 'nothing', run.env._(
                "Nothing was rebuilt. %(count)s person(s) did have door "
                "events between the dates you chose, but those events did not "
                "make a single attendance record: %(people)s. Their "
                "attendance for that period was cleared and nothing was put "
                "back. This normally means the doors those events came from "
                "have no reader set as the way in. Check the readers on those "
                "doors, then start the rebuild again.",
                count=len(cleared), people=run._name_a_few(cleared),
            )
        elif refused:
            # Every single person was refused, so the refusal IS the outcome
            # and the note below says the whole of it.
            state, said = 'refused', ''
        else:
            # Nobody was rebuilt, refused, cleared or broken, so everybody on
            # the list is somebody this sentence is about.
            said_the_untouched = True
            state, said = 'nothing', run.env._(
                "Nothing was rebuilt: none of the %(count)s person(s) had a "
                "single door event between the dates you chose, so their "
                "attendance was left exactly as it was. The usual reason is "
                "that no area is set to count towards attendance, which "
                "leaves no doors to read; otherwise nobody passed those doors "
                "in that period. Check the areas, then start the rebuild "
                "again.",
                count=len(run.log_ids),
            )

        run._finish(state, " ".join(part for part in (
            said,
            '' if said_the_cleared else run._also_cleared(cleared),
            '' if said_the_untouched else run._also_left_alone(untouched),
            run._also_refused(refused),
        ) if part))

    def _name_a_few(self, lines):
        """The people on these lines, as many as are worth reading."""
        return ", ".join(lines.mapped('employee_id.display_name')[:NAMES_SHOWN])

    def _also_left_alone(self, untouched):
        if not untouched:
            return ''
        return self.env._(
            "%(count)s other person(s) had no door events between the dates "
            "you chose, so their attendance was left as it was.",
            count=len(untouched),
        )

    def _also_cleared(self, cleared):
        if not cleared:
            return ''
        return self.env._(
            "%(count)s person(s) had door events that made no attendance at "
            "all, so their attendance for that period was cleared and nothing "
            "was put back: %(people)s.",
            count=len(cleared), people=self._name_a_few(cleared),
        )

    def _also_refused(self, refused):
        """What to say about people this system may not rebuild.

        Never "put the cause right and start it again": there is no cause to
        put right and the same request gets the same answer. What to do
        instead is on each line, in the words of whoever refused - they are
        the ones who know.
        """
        if not refused:
            return ''
        return self.env._(
            "Attendance for %(count)s person(s) is not for this system to "
            "rebuild and was left untouched: %(people)s. The line below for "
            "each of them says why, and what to do instead - asking for the "
            "same rebuild again will get the same answer.",
            count=len(refused), people=self._name_a_few(refused),
        )

    # ── Housekeeping ──────────────────────────────────────────

    @api.autovacuum
    def _gc_recalc_runs(self):
        """Clear out rebuilds nobody will ask about again.

        Only rebuilds that are over: one still waiting or under way is not
        old, however long ago it was asked for, and tidying it away would
        delete a job while it is being done.
        """
        cutoff = fields.Datetime.now() - timedelta(days=self.GC_DAYS)
        stale = self.search([
            ('state', 'in', FINISHED_STATES),
            ('create_date', '<', cutoff),
        ], limit=self.GC_LIMIT)
        count = len(stale)
        stale.unlink()
        return count, count == self.GC_LIMIT


class HrAttendanceRecalcLog(models.Model):
    """What the rebuild did, person by person - kept, not cleaned away."""

    _name = 'hr.attendance.recalc.log'
    _description = 'Attendance Rebuild Line'
    _order = 'id'

    run_id = fields.Many2one(
        'hr.attendance.recalc.run',
        required=True, ondelete='cascade', index=True,
        help="The rebuild this line belongs to.",
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='run_id.company_id', store=True, index=True,
        help="The company the rebuild was started for.",
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        ondelete='cascade', index=True,
        help="The person this line is about.",
    )
    status = fields.Selection(
        [
            ('done', 'Rebuilt'),
            ('no_events', 'No door events'),
            ('no_result', 'Cleared, nothing put back'),
            ('refused', 'Refused'),
            ('error', 'Not rebuilt'),
        ],
        required=True, default='done',
        help="Rebuilt: their attendance was replayed from the door events. "
             "No door events: there was nothing in the period to replay, so "
             "their attendance was left alone. Cleared, nothing put back: "
             "there were door events, but they made no attendance at all - "
             "the period is now empty for this person. Refused: their "
             "attendance is not for this system to rebuild, and the reason "
             "says what to do instead. Not rebuilt: something went wrong and "
             "their attendance is as it was.",
    )
    event_count = fields.Integer(
        string='Door events', readonly=True,
        help="How many door events were replayed for this person.",
    )
    attendance_count = fields.Integer(
        string='Attendance records', readonly=True,
        help="How many attendance records came out of them.",
    )
    error_message = fields.Text(
        string='Reason', readonly=True,
        help="Why this person's attendance was not rebuilt, and what to do "
             "about it.",
    )
