# -*- coding: utf-8 -*-
"""A transfer that outlives the screen it was started from.

Doing this work inside the HTTP request cannot succeed: a request is cut off
after ``limit_time_real`` seconds (120 on a standard install), and a real site
carries tens of thousands of events. The cron thread is NOT exempt either -
``limit_time_real_cron`` only replaces the limit when it is positive, and
exceeding it does not merely kill the job, it restarts the server. So the work
is done in pieces, each committed, each small enough to finish.

The request itself cannot live on the wizard: that is a TransientModel and the
cleaner removes it after an hour, taking the whole job with it. Odoo core makes
the same split - account.move.send.batch.wizard is transient, while the state
lives on the permanent account.move.sending_data.
"""
import json
import logging
import time
from datetime import timedelta

from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

#: How long one pass may spend reading before it stops and asks for another.
#: One cron wake-up calls the job at least ten times inside a ten-second
#: budget, and the whole thread is capped at limit_time_real. A pass that
#: overruns does not just fail - it brings the server down with it, so this
#: is a safety parameter, not a tuning knob.
PASS_SECONDS = 5.0

#: A transfer untouched for this long is treated as dead. Long enough that a
#: slow pass is never mistaken for a stalled one, short enough that the stored
#: credentials do not outlive the job by a working day.
STALLED_MINUTES = 30


class HrRfidOdooImportRun(models.Model):
    _name = 'hr.rfid.odoo.import.run'
    _description = 'RFID Data Transfer'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        compute='_compute_name', store=True,
        help="Short label of this transfer, built from the source it reads.",
    )
    state = fields.Selection(
        [
            ('queued', 'Waiting to start'),
            ('running', 'In progress'),
            ('done', 'Finished'),
            ('failed', 'Stopped by a problem'),
        ],
        default='queued', required=True, tracking=True, index=True,
        help="Where this transfer has got to. It continues on its own; you can "
             "close the page.",
    )
    user_id = fields.Many2one(
        'res.users', string='Started by', required=True, index=True,
        default=lambda self: self.env.user,
        help="Who started the transfer. The work runs in the background, so "
             "this is who gets told when it finishes.",
    )
    source_url = fields.Char(required=True, help="Address of the system being read.")
    source_db = fields.Char(help="Which database on that system.")
    source_login = fields.Char(required=True, help="Account used to read it.")
    source_password = fields.Char(
        groups='base.group_system',
        help="Password for that account. Kept only while the transfer runs and "
             "cleared the moment it ends.",
    )
    source_uid = fields.Integer(help="Internal id of that account, from the login.")
    source_slug = fields.Char(
        help="Which source system these records are recorded against. Left "
             "empty it follows the database name of the system being read.",
    )
    installed_modules_json = fields.Text(help="What the other system was found to keep.")
    options_json = fields.Text(help="What the operator chose to bring across.")
    company_map_json = fields.Text(help="Which company on the other side becomes which here.")
    resolution_json = fields.Text(
        help="Decisions the operator made about records that clash with existing ones.",
    )
    done_phases_json = fields.Text(
        default='[]',
        help="Which steps have already finished, so a resumed transfer does not repeat them.",
    )
    read_cursors_json = fields.Text(
        default='{}',
        help="How far each long read got, so the next pass carries on instead "
             "of reading the same records again.",
    )
    current_phase = fields.Char(
        readonly=True, help="The step being worked on right now.",
    )
    done_count = fields.Integer(readonly=True, help="Steps finished.")
    total_count = fields.Integer(readonly=True, help="Steps in total.")
    progress = fields.Integer(
        compute='_compute_progress',
        help="How far along the transfer is.",
    )
    log_ids = fields.One2many(
        'hr.rfid.odoo.import.log', 'run_id', string='What happened',
        help="One line per step, with what came across and what did not.",
    )

    @api.depends('source_url', 'source_db')
    def _compute_name(self):
        for run in self:
            # Not named "source": that is the first parameter of Environment._
            # itself, so passing it as a keyword collides with it.
            run.name = self.env._(
                "Transfer from %(system)s",
                system=run.source_db or run.source_url or '?',
            )

    @api.depends('done_count', 'total_count')
    def _compute_progress(self):
        for run in self:
            run.progress = int(run.done_count * 100 / run.total_count) if run.total_count else 0

    # ── Lifecycle ─────────────────────────────────────────────

    def action_start(self):
        """Ask for the work to begin. Returns at once.

        Called once, by the wizard, on a transfer that has just been written
        down and that nobody is working on yet.
        """
        self.ensure_one()
        self.state = 'queued'
        self._wake_the_worker()
        return True

    def action_refresh(self):
        """Show what the worker has done since the page was opened.

        This writes NOTHING to the transfer, and that is the whole point.

        It used to call action_start, which set the state - on the same row the
        worker rewrites at every phase. Odoo runs at REPEATABLE READ
        (odoo/sql_db.py:373), so updating a row another transaction has changed
        and committed since our snapshot raises SerializationFailure; Odoo then
        replays the whole request up to five times
        (odoo/service/model.py:29-30, :185), each attempt colliding again with
        a worker that commits every phase. The operator sat waiting while a
        request thread burned through all five, and was then shown a red server
        error - on a transfer that was running perfectly well.

        Waking the scheduler is only meaningful when nothing is working on this
        transfer yet; a running one already has a worker, and poking it can
        only start a second pass that finds the row locked.
        """
        self.ensure_one()
        if self.state == 'queued':
            self._wake_the_worker()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_download_protocol(self):
        """The whole protocol as one plain-text file the operator can send.

        Reading a long protocol through list-view truncation loses exactly the
        part that matters - the error texts. One file, every line in full,
        downloadable and pasteable into a support conversation.
        """
        self.ensure_one()
        header = [
            self.name or '',
            '%s / %s / %s' % (self.source_url or '', self.source_db or '',
                              self.source_slug or ''),
            'state: %s  done: %s/%s  phase: %s' % (
                self.state, self.done_count, self.total_count,
                self.current_phase or '-'),
            '-' * 78,
            'phase | model | source | imported | linked | skipped | rejected | status | error',
            '-' * 78,
        ]
        rows = [
            '%s | %s | %s | %s | %s | %s | %s | %s | %s' % (
                l.phase, l.model, l.source_count, l.imported_count,
                l.linked_count, l.skipped_count, l.rejected_count, l.status,
                (l.error_message or '').replace('\n', ' '),
            )
            for l in self.log_ids.sorted('id')
        ]
        attachment = self.env['ir.attachment'].create({
            'name': 'transfer-%s-protocol.txt' % self.id,
            'raw': '\n'.join(header + rows).encode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/plain',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _wake_the_worker(self):
        cron = self.env.ref('hr_rfid_odoo_import.ir_cron_import_run',
                            raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()

    def _finish(self, state, message=None):
        """End the transfer and stop holding the other system's password."""
        self.ensure_one()
        self.write({
            'state': state,
            'source_password': False,
            'current_phase': False,
        })
        if message:
            self.message_post(body=message)

    # ── The worker ────────────────────────────────────────────

    @api.model
    def _cron_process(self):
        """One pass of work. Called by the scheduler.

        Pressed from the interface instead, this would do the whole job inside
        the HTTP request and hit the request time limit - so from there it only
        wakes the scheduler up. Core does the same (cloud_storage/ir_attachment).
        """
        if request:
            self.env['hr.rfid.odoo.import.run']._wake_the_worker()
            return
        if self._abandon_stalled_runs():
            # Closing the dead transfers is a finished piece of work in its own
            # right, so it is kept before the next one is started. The pass
            # below rolls the transaction back when it fails - and that would
            # otherwise undo exactly the closures that unblock the queue,
            # leaving the same dead transfers in the way on every wake-up, and
            # the other system's password in the database with them. Core keeps
            # each completed unit before beginning the next the same way
            # (odoo/addons/mail/models/fetchmail.py:340), and so does the
            # attendance rebuild this worker is modelled on
            # (hr_attendance_multi_rfid/models/attendance_recalc_run.py:211-219).
            self.env.cr.commit()
        run = self.search([('state', 'in', ('queued', 'running'))],
                          order='create_date asc', limit=1)
        if not run:
            return
        try:
            run._process_pass()
        except Exception as exc:
            # Without this the transfer stays queued forever and, because it is
            # the oldest, it is picked again on every wake-up - blocking every
            # later transfer behind it. The scheduler only runs daily, so that
            # is a queue nobody notices is stuck.
            _logger.error("Transfer %s could not be worked on: %s",
                          run.id, exc, exc_info=True)
            self.env.cr.rollback()
            run._finish('failed', self.env._(
                "The transfer stopped because of a problem outside the steps "
                "themselves: %(problem)s", problem=str(exc)[:300],
            ))
            self.env.cr.commit()

    @api.model
    def _abandon_stalled_runs(self):
        """End transfers that stopped being worked on, and drop their password.

        A pass that dies outright - the process is killed, the server restarts
        mid-step - leaves the transfer sitting in "running" for good. Two things
        follow from that, and the second is the reason this exists: the queue is
        blocked behind it, and the other system's password stays in the database
        indefinitely, long after anyone would think the job was over.

        :return: the transfers that were closed, so the caller knows there is
            something worth keeping before it starts the next pass
        """
        cutoff = fields.Datetime.now() - timedelta(minutes=STALLED_MINUTES)
        stalled = self.search([
            ('state', '=', 'running'),
            ('write_date', '<', cutoff),
        ])
        for run in stalled:
            _logger.warning(
                "Transfer %s has not moved since %s - abandoning it and "
                "clearing the stored credentials", run.id, run.write_date)
            run._finish('failed', self.env._(
                "This transfer stopped without finishing and has been closed. "
                "The access details it held have been cleared. Start a new one "
                "when you are ready - what already came across will not be "
                "brought over twice."
            ))
        return stalled

    def _process_pass(self):
        """Work through as many steps as fit in this pass."""
        self.ensure_one()
        from .importers.phase import phase_plan, registry

        # Another worker may have taken this job between the search and here.
        if not self.try_lock_for_update():
            return
        self.invalidate_recordset(['state', 'done_phases_json'])
        if self.state not in ('queued', 'running'):
            return

        options = json.loads(self.options_json or '{}')
        source_modules = set(json.loads(self.installed_modules_json or '[]'))
        done_phases = set(json.loads(self.done_phases_json or '[]'))
        plan = phase_plan(self.env, options, source_modules)
        self.write({'state': 'running', 'total_count': len(plan)})

        importer = self._build_importer(options)
        deadline = time.monotonic() + PASS_SECONDS
        importer.time_is_up = lambda: time.monotonic() > deadline

        for cls, skip_reason in plan:
            if cls.PHASE_ID in done_phases:
                continue
            if skip_reason:
                self._log_phase(cls, status='skipped', message=skip_reason)
                done_phases.add(cls.PHASE_ID)
                self._save_progress(done_phases, cls,
                                    remaining=len(plan) - len(done_phases),
                                    importer=importer)
                continue

            self.current_phase = cls.NAME
            self._drop_stale_phase_lines(cls)
            phase = cls(importer)
            complete = self._run_one_phase(phase, cls)
            if complete:
                done_phases.add(cls.PHASE_ID)
            self._save_progress(done_phases, cls,
                                remaining=len(plan) - len(done_phases),
                                importer=importer)

            if time.monotonic() > deadline:
                # Out of time. Whatever is left waits for the next pass; the
                # external IDs make re-reading safe, so nothing is duplicated.
                self._wake_the_worker()
                return

        self._report_refused_fields(importer)
        self._finish_reporting_failures()

    def _drop_stale_phase_lines(self, cls):
        """Replace, never pile up, the protocol lines of a re-entered phase.

        A phase runs again only when the last pass stopped it mid-way (out of
        time). Its half-written lines describe work this pass is about to redo
        and re-count; left in place they accumulate one copy per pass - a live
        protocol held SEVEN copies of the events lines, and the operator read
        "20 851 missing events" seven times over as seven separate problems.
        """
        self.ensure_one()
        self.log_ids.filtered(lambda l: l.phase == cls.PHASE_ID).unlink()

    def _report_refused_fields(self, importer):
        """Every field the source declined to hand over, in the protocol.

        The transfer carries on without such a field - that is the fix for a
        live migration where one refused field cost the whole hardware phase -
        but carrying on SILENTLY would turn the fix into a hole: the operator
        must see what was left behind and decide whether it matters.
        """
        for model, fields_ in sorted((importer.refused_fields or {}).items()):
            self.env['hr.rfid.odoo.import.log'].create({
                'run_id': self.id,
                'phase': 'fields',
                'model': model,
                'status': 'partial',
                'error_message': self.env._(
                    "The account used to read the other system is not allowed "
                    "to see: %(fields)s. Everything else about these records "
                    "came across. If those details matter, widen that "
                    "account's access rights over there and run the transfer "
                    "again.", fields=", ".join(sorted(fields_)),
                ),
            })

    def _finish_reporting_failures(self):
        """End the run, saying plainly whether anything did not come across.

        Telling the operator "finished" over a transfer that lost a whole step
        is worse than telling them nothing: they close the page and find out
        weeks later.
        """
        broken = self.log_ids.filtered(lambda l: l.status == 'error')
        partial = self.log_ids.filtered(lambda l: l.status == 'partial')
        if broken:
            self._finish('failed', self.env._(
                "The transfer stopped with %(count)s part(s) that did not come "
                "across: %(parts)s. Everything else is here. Look at the list "
                "below, put the cause right, and start the transfer again.",
                count=len(broken),
                parts=", ".join(broken.mapped('model')[:8]),
            ))
        elif partial:
            self._finish('done', self.env._(
                "The transfer has finished, but %(count)s part(s) came across "
                "only in part. The list below says which.",
                count=len(partial),
            ))
        else:
            self._finish('done', self.env._("The transfer has finished."))

    def _run_one_phase(self, phase, cls):
        """Run one step. Returns whether it got all the way through."""
        phase.b.stopped_early = False
        # The savepoint below throws away the rows a failing step wrote, but
        # the source->target map it filled lives in memory and survives. The
        # next step would then write links to ids that no longer exist - or,
        # worse, to ids the database has since handed to somebody else's
        # record. The synchronous path has guarded against this since a live
        # incident; the background one must too.
        id_map_snapshot = {m: dict(v) for m, v in phase.b.id_map.items()}
        try:
            with self.env.cr.savepoint():
                results = phase.run(self)
            for result in (results or []):
                self._log_phase(cls, result=result,
                                partial=phase.b.stopped_early)
            return not phase.b.stopped_early
        except Exception as exc:
            _logger.error("Transfer step %s failed: %s", cls.NAME, exc, exc_info=True)
            phase.b.id_map.clear()
            phase.b.id_map.update(id_map_snapshot)
            # The savepoint has already undone everything this phase wrote and
            # cleared the cache with it (_FlushingSavepoint.rollback,
            # odoo/sql_db.py:137-140). Nothing more may be undone here: a plain
            # cr.rollback() goes back to the last COMMIT and takes the pass's
            # own bookkeeping with it - the same defect cost the attendance
            # rebuild its fixture and every already-finished person of a pass.
            self._log_phase(cls, status='error', message=str(exc)[:500])
            self.message_post(body=self.env._(
                "The step \"%(step)s\" could not be completed: %(problem)s",
                step=cls.NAME, problem=str(exc)[:300],
            ))
            self.env.cr.commit()
            # Considered finished so the same failure does not loop forever -
            # but if the step had only read part of the source, saying so would
            # throw the rest away without a trace.
            return not phase.b.stopped_early

    def _save_progress(self, done_phases, cls, remaining=None, importer=None):
        values = {
            'done_phases_json': json.dumps(sorted(done_phases)),
            'done_count': len(done_phases),
        }
        if importer is not None:
            # Where each long read got to. Without this the next pass starts
            # the same read from the beginning and the transfer never advances.
            values['read_cursors_json'] = json.dumps(importer.read_cursors)
        self.write(values)
        # Commits, records how far we got, and tells the scheduler how much
        # time is left. Called outside the savepoint above on purpose:
        # committing inside an open savepoint destroys it.
        # Passing what is left lets core reschedule itself immediately. Without
        # it core computes zero remaining, calls the job fully done, and the
        # next attempt waits for the daily interval - leaving the manual wake-up
        # below as the only thing keeping the transfer moving.
        self.env['ir.cron']._commit_progress(processed=1, remaining=remaining)

    def _log_phase(self, cls, result=None, status=None, message=None,
                   partial=False):
        outcome = status or (result or {}).get('status', 'done')
        if partial and outcome == 'done':
            # Read only part of the source before running out of time. Marking
            # it done would make the row read as a completed step and quietly
            # make the reconciliation totals meaningless.
            outcome = 'partial'
        values = {
            'run_id': self.id,
            'phase': cls.PHASE_ID,
            'model': (result or {}).get('model') or cls.NAME,
            'status': outcome,
            'error_message': message or (result or {}).get('error', ''),
        }
        if result:
            values.update({
                'source_count': result.get('source_count', 0),
                'imported_count': result.get('imported_count', 0),
                'skipped_count': result.get('skipped_count', 0),
                'rejected_count': result.get('rejected_count', 0),
                'linked_count': result.get('linked_count', 0),
                'duration': result.get('duration', 0),
            })
        self.env['hr.rfid.odoo.import.log'].create(values)

    def _build_importer(self, options):
        from .importers.base_importer import BaseImporter
        importer = BaseImporter(
            env=self.env,
            source_url=self.source_url,
            source_db=self.source_db,
            source_uid=self.source_uid,
            source_password=self.source_password,
            company_map={int(k): v for k, v in
                         json.loads(self.company_map_json or '{}').items()},
            options=options,
            source_slug=self.source_slug,
        )
        importer.read_cursors = json.loads(self.read_cursors_json or '{}')
        self._apply_resolutions(importer)
        return importer

    def _apply_resolutions(self, importer):
        """Re-apply the operator's decisions at the start of every pass.

        They live in memory otherwise, and a pass that runs in a fresh process
        would treat a record the operator chose to leave alone as new - which
        then collides with the existing one and takes the step down.
        """
        for entry in json.loads(self.resolution_json or '[]'):
            if entry.get('resolution') == 'link':
                importer.link_existing(entry['model'], entry['source_id'],
                                       entry['target_id'])
            elif entry.get('resolution') == 'skip':
                importer._set_target_id(entry['model'], entry['source_id'], None)
