"""A survey of a running access control system, and its import.

The survey reads modules and controllers WITHOUT changing them, keeps what it
read as evidence, lets the operator name the card holders and review the
proposed access groups, and finally creates the records here - again without a
single command to the hardware. Pointing a module to this server is a separate,
explicit action on the module row.

The long parts (finding modules, reading card tables, creating records) run in
a scheduled worker in small committed pieces, exactly like the Odoo-to-Odoo
transfer of the sibling module: a request is cut off after a couple of minutes
and a card table can take a quarter of an hour to read.
"""
import json
import logging
import re
import time
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from ..helpers import transport
from ..helpers.codecs import display_number

_logger = logging.getLogger(__name__)

#: How long one worker pass may run before it stops and asks for another.
PASS_SECONDS = 5.0

#: A survey the worker has not touched for this long is treated as dead.
STALLED_MINUTES = 30

#: A survey parked by the operator (modules listed, names, groups) keeps the
#: module passwords it was given for this long; after that they are cleared
#: and have to be entered again before the modules can be read.
IDLE_PASSWORD_HOURS = 24

WORKER_STATES = ('discovering', 'reading', 'analysing', 'importing')

#: The longest a network search may wait for answers. A discovery pass runs
#: inside the scheduled action's time limit and must never approach it.
MAX_DISCOVERY_TIMEOUT = 30.0

#: A configuration key holding any of these is never kept, and neither are
#: credentials written into an address (http://user:pass@host).
SECRET_KEY_HINTS = ('key', 'password', 'pass', 'pwd', 'secret', 'token', 'psk', 'pin', 'auth', 'credential')
USERINFO_IN_URL = re.compile(r'://[^/@\s]+@')

#: Test seam: the object that makes discovery and module clients. Tests and
#: demos substitute a scripted backend here; production uses real sockets.
_BACKEND_OVERRIDE = None


def override_backend(backend):
    """Install (or, with None, remove) a substitute transport backend."""
    global _BACKEND_OVERRIDE
    _BACKEND_OVERRIDE = backend


def current_backend():
    return _BACKEND_OVERRIDE or transport.RealBackend()


class HwImportRun(models.Model):
    _name = 'hr.rfid.hw.import.run'
    _description = 'Hardware Survey'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True,
                       help="Label of this survey, from when it was started and for which company.")
    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company,
                                 help="Every record the import creates belongs to this company.")
    user_id = fields.Many2one('res.users', string='Started by', required=True, index=True,
                              default=lambda self: self.env.user,
                              help="Who started the survey; the work runs in the background.")
    state = fields.Selection([
        ('draft', 'Modules'),
        ('discovering', 'Searching the network'),
        ('reading', 'Reading controllers'),
        ('analysing', 'Analysing'),
        ('naming', 'Names'),
        ('grouping', 'Access groups'),
        ('importing', 'Importing'),
        ('done', 'Done'),
        ('failed', 'Stopped by a problem'),
    ], default='draft', required=True, tracking=True, index=True,
        help="Where the survey has got to. The steps run in order; each can be skipped.")
    discovery_broadcast = fields.Boolean(string="Search the local network",
        default=True, help="Search the local network for modules. Modules behind a router are added by address.")
    discovery_timeout = fields.Float(string="Wait for answers (seconds)",
        default=2.0, help="How many seconds to wait for modules to answer the network search.")
    names_file = fields.Binary(string="Names file", attachment=True, help="The uploaded names file, kept for reference.")
    names_file_name = fields.Char(string="Names file name", help="Name of the uploaded names file.")
    placeholder_owner_type = fields.Selection(string="Create generated holders as", selection=[
        ('contact', 'Contact'), ('employee', 'Employee')], default='contact', required=True,
        help="Cards without a known name get a generated owner of this kind. Each person can be changed.")
    default_department_id = fields.Many2one(
        'hr.department', string="Department for employees", help="Department for the people imported as employees. Required as soon as any "
                              "person is an employee.")
    import_hardware = fields.Boolean(default=True, help="Create the modules, controllers, doors and readers.")
    import_schedules = fields.Boolean(default=True, help="Take the time schedules from the controllers.")
    import_people = fields.Boolean(default=True, help="Create the card holders as contacts or employees.")
    import_cards = fields.Boolean(default=True, help="Create the cards.")
    import_groups = fields.Boolean(default=True, help="Create the access groups and give them to the people.")

    current_phase = fields.Char(string="Current phase", readonly=True, help="What the worker is doing right now.")
    done_count = fields.Integer(readonly=True, help="Pieces of work finished in the current step.")
    total_count = fields.Integer(readonly=True, help="Pieces of work in the current step.")
    progress = fields.Integer(compute='_compute_progress', help="How far the current step has got.")
    phase_done_json = fields.Text(string="Import steps done", default='[]', help="Import steps already finished, so a resumed import does not repeat them.")
    discovered_at = fields.Datetime(string="Network searched on", help="When the network search finished.")
    read_at = fields.Datetime(string="Controllers read on", help="When the controllers were read.")
    analysed_at = fields.Datetime(string="Analysed on", help="When the analysis finished.")
    imported_at = fields.Datetime(string="Imported on", help="When the import finished.")
    last_error = fields.Text(string="Why it stopped", help="Why the survey stopped, if it did.")

    module_ids = fields.One2many('hr.rfid.hw.import.module', 'run_id', string='Modules',
                                 help="The modules found on the network or added by address.")
    ctrl_ids = fields.One2many('hr.rfid.hw.import.ctrl', 'run_id', string='Controllers',
                               help="The controllers found on those modules.")
    card_ids = fields.One2many('hr.rfid.hw.import.card', 'run_id', string='Cards',
                               help="Every card number found on the controllers.")
    person_ids = fields.One2many('hr.rfid.hw.import.person', 'run_id', string='People',
                                 help="The card holders: named from the file, or generated.")
    name_line_ids = fields.One2many('hr.rfid.hw.import.name', 'run_id', string='Names file lines',
                                    help="The lines of the uploaded names file and what happened to each.")
    group_ids = fields.One2many('hr.rfid.hw.import.group', 'run_id', string='Proposed access groups',
                                help="Access groups derived from the rights the controllers hold.")
    ts_slot_ids = fields.One2many('hr.rfid.hw.import.ts.slot', 'run_id', string='Schedule slots',
                                  help="The time schedule slots across all controllers.")
    issue_ids = fields.One2many('hr.rfid.hw.import.issue', 'run_id', string='Findings',
                                help="Conflicts, warnings and report lines.")
    cmd_log_ids = fields.One2many('hr.rfid.hw.import.cmd.log', 'run_id', string='Command log',
                                  help="Every command sent to the hardware, with its reply.")

    module_count = fields.Integer(string="Number of modules", compute='_compute_counts', help="Modules found or added. Fewer than the site has means one is behind a router: add it by address.")
    ctrl_count = fields.Integer(string="Number of controllers", compute='_compute_counts', help="Controllers the modules see. Fewer than the site has means one is off or unplugged; see the Controllers tab.")
    card_count = fields.Integer(string="Number of cards", compute='_compute_counts', help="Card numbers found on the controllers that were read. Far fewer than the site issues means a controller was not read; see the Controllers tab.")
    person_count = fields.Integer(string="Number of people", compute='_compute_counts', help="Card holders, named from the file or generated. More people than cards cannot happen; fewer means the file merged names.")
    group_count = fields.Integer(string="Number of access groups", compute='_compute_counts', help="Access groups proposed from the rights. Many small groups means the site grants rights door by door; merge the ones that belong together.")
    blocker_count = fields.Integer(string="Must be resolved", compute='_compute_counts', help="Findings that stop the import; 0 means it can start.")
    has_blockers = fields.Boolean(compute='_compute_counts', help="The import cannot start yet.")
    included_module_count = fields.Integer(string="Modules to read", compute='_compute_counts', help="Modules ticked for reading.")
    has_read_failures = fields.Boolean(compute='_compute_counts',
                                       help="A module or controller could not be read; it can be read again.")

    @api.depends('create_date', 'company_id')
    def _compute_name(self):
        for run in self:
            stamp = fields.Datetime.context_timestamp(run, run.create_date or fields.Datetime.now())
            run.name = self.env._('Survey %(date)s - %(company)s',
                                  date=stamp.strftime('%Y-%m-%d %H:%M'), company=run.company_id.name)

    @api.depends('done_count', 'total_count')
    def _compute_progress(self):
        for run in self:
            run.progress = int(run.done_count * 100 / run.total_count) if run.total_count else 0

    @api.depends('module_ids', 'module_ids.include', 'module_ids.status', 'module_ids.read_state', 'ctrl_ids',
                 'ctrl_ids.read_state', 'card_ids', 'person_ids', 'group_ids', 'issue_ids.resolved',
                 'ts_slot_ids.state', 'person_ids.review_state', 'person_ids.include', 'import_schedules',
                 'import_people')
    def _compute_counts(self):
        for run in self:
            included = run.module_ids.filtered(lambda m: m.include and m.status != 'unreachable')
            run.has_read_failures = bool(included.filtered(lambda m: m.read_state == 'failed')
                                         or included.ctrl_ids.filtered(lambda c: c.read_state == 'failed'))
            run.module_count = len(run.module_ids)
            run.included_module_count = len(run.module_ids.filtered('include'))
            run.ctrl_count = len(run.ctrl_ids)
            run.card_count = len(run.card_ids)
            run.person_count = len(run.person_ids)
            run.group_count = len(run.group_ids)
            blockers = len(run.issue_ids.filtered(lambda i: not i.resolved))
            if run.import_schedules:
                blockers += len(run.ts_slot_ids.filtered(lambda s: s.state == 'conflict'))
            if run.import_people:
                blockers += len(run.person_ids.filtered(lambda p: p.include and p.review_state == 'blocked'))
            run.blocker_count = blockers
            run.has_blockers = blockers > 0

    # ------------------------------------------------------------ helpers

    def _backend(self):
        return current_backend()

    def _client_for(self, module):
        run = self
        module_id = module.id

        def on_log(entry):
            run.env['hr.rfid.hw.import.cmd.log'].sudo().create(dict(entry, run_id=run.id, module_id=module_id))

        return self._backend().client(module.ip, port=module.port or 80, auth=module._auth(), on_log=on_log)

    def _log_issue(self, kind, severity, message, **links):
        self.ensure_one()
        values = {'run_id': self.id, 'kind': kind, 'severity': severity, 'message': message}
        for key, value in links.items():
            values[key] = value.id if hasattr(value, 'id') else value
        return self.env['hr.rfid.hw.import.issue'].create(values)

    def _display_number(self, number):
        return display_number(number, self.company_id.card_input_type or 'w34')

    def _company_ts(self, number):
        """This company's time schedule with that slot number, if it has one."""
        self.ensure_one()
        return self.env['hr.rfid.time.schedule'].sudo().search(
            [('company_id', 'in', [self.company_id.id, False]), ('number', '=', number)], limit=1)

    def _existing_webstack(self, serial):
        """The module record already registered under ``serial`` anywhere in this
        database, and whether it belongs to this survey's company. Serial
        numbers are unique across companies, so the search is global; a record
        of another company is reported as taken, never named or linked."""
        self.ensure_one()
        existing = self.env['hr.rfid.webstack'].sudo().with_context(active_test=False).search(
            [('serial', '=', serial)], limit=1) if serial else self.env['hr.rfid.webstack']
        ours = bool(existing) and (not existing.company_id or existing.company_id == self.company_id)
        return existing, ours

    @api.constrains('discovery_timeout')
    def _check_discovery_timeout(self):
        for run in self:
            if not 0 < run.discovery_timeout <= MAX_DISCOVERY_TIMEOUT:
                raise ValidationError(self.env._(
                    "The wait for answers must be between 1 and %(max)s seconds.", max=MAX_DISCOVERY_TIMEOUT))

    def _require_state(self, *states):
        self.ensure_one()
        if self.state not in states:
            raise UserError(self.env._("This step is not available while the survey is in state '%(state)s'.",
                                       state=dict(self._fields['state'].selection).get(self.state)))

    def write(self, vals):
        old_types = {run: run.placeholder_owner_type for run in self} if 'placeholder_owner_type' in vals else {}
        result = super().write(vals)
        for run, old in old_types.items():
            if old != run.placeholder_owner_type:
                # The survey-wide choice follows through to every generated
                # holder the operator has not changed by hand.
                run.person_ids.filtered(
                    lambda p: p.source == 'placeholder' and p.owner_type == old).write(
                    {'owner_type': run.placeholder_owner_type})
        return result

    # ------------------------------------------------------------ operator actions

    def action_discover(self):
        self._require_state('draft')
        self.write({'state': 'discovering', 'current_phase': self.env._('Searching the network'),
                    'done_count': 0, 'total_count': 1})
        self._wake_the_worker()
        return True

    def action_add_module(self):
        self._require_state('draft')
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Add a module by address'),
            'res_model': 'hr.rfid.hw.import.add.ip.wiz',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_run_id': self.id},
        }

    def action_read(self):
        self._require_state('draft')
        modules = self.module_ids.filtered(lambda m: m.include and m.status != 'unreachable')
        if not modules:
            raise UserError(self.env._("Tick at least one reachable module to read."))
        modules.write({'read_state': 'pending', 'read_error': False})
        modules.ctrl_ids.filtered(lambda c: c.read_state != 'done').write({'read_state': 'pending'})
        self.write({'state': 'reading', 'current_phase': self.env._('Reading controllers'),
                    'done_count': 0, 'total_count': max(len(modules), 1)})
        self._wake_the_worker()
        return True

    def action_read_again(self):
        """Read the modules and controllers that failed, from the names step.

        The analysis is redone afterwards, so proposed groups, schedule
        decisions and generated holders are rebuilt; people from the names
        file are kept.
        """
        self._require_state('naming', 'grouping')
        modules = self.module_ids.filtered(lambda m: m.include and m.status != 'unreachable')
        failed_modules = modules.filtered(lambda m: m.read_state == 'failed')
        failed_ctrls = modules.ctrl_ids.filtered(lambda c: c.read_state == 'failed')
        if not failed_modules and not failed_ctrls:
            raise UserError(self.env._("Every module and controller was read; there is nothing to read again."))
        # The findings of the last attempt go with it; the new attempt writes its own.
        self.issue_ids.filtered(lambda i: i.phase == 'read' and (
            i.module_id in failed_modules or i.ctrl_id in failed_ctrls)).unlink()
        failed_modules.write({'read_state': 'pending', 'read_error': False})
        failed_ctrls.write({'read_state': 'pending', 'read_error': False, 'read_cursor': 1, 'cards_read': 0})
        failed_ctrls.mapped('module_id').filtered(lambda m: m.read_state == 'done').write({'read_state': 'pending'})
        self.write({'state': 'reading', 'current_phase': self.env._('Reading controllers'),
                    'done_count': 0, 'total_count': max(len(modules), 1)})
        self._wake_the_worker()
        return True

    def action_refresh(self):
        """Show the current figures. Writes nothing; wakes the worker if it is due."""
        self.ensure_one()
        if self.state in WORKER_STATES:
            self._wake_the_worker()
        return True

    def action_reopen(self):
        """Bring a survey that stopped on a problem back to the step it was at.

        Nothing is lost by a failure: what was read stays on the rows, and the
        import remembers the steps it finished and creates nothing twice. So
        the survey goes back to the last step the operator could act on,
        instead of being read again from the hardware.
        """
        self._require_state('failed')
        if self.imported_at or json.loads(self.phase_done_json or '[]'):
            state = 'grouping'
        elif self.analysed_at:
            state = 'grouping' if self.name_line_ids else 'naming'
        else:
            state = 'draft'
            self.module_ids.filtered(lambda m: m.read_state == 'reading').write({'read_state': 'pending'})
        self.write({'state': state, 'last_error': False, 'current_phase': False})
        self.message_post(body=self.env._("The survey was reopened at the step '%(step)s'.",
                                          step=dict(self._fields['state'].selection).get(state)))
        return True

    def action_upload_names(self):
        self._require_state('naming', 'grouping')
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Upload a names file'),
            'res_model': 'hr.rfid.hw.import.names.wiz',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_run_id': self.id},
        }

    def action_skip_names(self):
        self._require_state('naming')
        self.write({'state': 'grouping'})
        return True

    def action_to_grouping(self):
        self._require_state('naming')
        self.write({'state': 'grouping'})
        return True

    def action_back_to_naming(self):
        self._require_state('grouping')
        self.write({'state': 'naming'})
        return True

    def action_open_group_merge(self):
        self._require_state('grouping')
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Merge proposed access groups'),
            'res_model': 'hr.rfid.hw.import.group.merge.wiz',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_run_id': self.id},
        }

    def action_open_import_options(self):
        self._require_state('grouping')
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Import into this system'),
            'res_model': 'hr.rfid.hw.import.options.wiz',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_run_id': self.id},
        }

    def action_start_import(self):
        """Queue the import. Called by the options wizard after its checks."""
        self._require_state('grouping')
        if self.has_blockers:
            raise UserError(self.env._(
                "Resolve the findings marked 'Must be resolved' first, or leave that part of the import out."))
        employees = self.person_ids.filtered(lambda p: p.include and p.owner_type == 'employee')
        if self.import_people and employees and not self.default_department_id:
            raise UserError(self.env._("Choose a department for the people imported as employees."))
        self.write({'state': 'importing', 'current_phase': self.env._('Importing'),
                    'done_count': 0, 'total_count': 7, 'phase_done_json': '[]'})
        self._wake_the_worker()
        return True

    def action_point_modules(self):
        """Point every imported module of this survey to this server (each asks first).

        Each module is handled on its own: one that refuses does not undo the
        modules already pointed before it (they have been reconfigured for
        real), and the outcome is reported per module.
        """
        self._require_state('done')
        # Only modules this survey created: a module that was already
        # registered here reports here already, and re-pointing it would reboot
        # a working device and reset its key for nothing.
        modules = self.module_ids.filtered(lambda m: m.webstack_id and not m.pointed_at and not m.existing_webstack_id)
        if not modules:
            raise UserError(self.env._("There is no module created by this survey left to point to this server."))
        failures = []
        for module in modules:
            try:
                with self.env.cr.savepoint():
                    module.action_point_to_server()
            except (UserError, ValidationError) as exc:
                failures.append('%s: %s' % (module._display_address(), exc.args[0] if exc.args else exc))
        pointed = len(modules) - len(failures)
        if failures:
            message = self.env._("%(n)s modules were pointed to this server; these were not: %(failures)s",
                                 n=pointed, failures='; '.join(failures))
            self.message_post(body=message)
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'type': 'warning', 'title': self.env._('Not every module could be pointed'),
                           'message': message, 'sticky': True},
            }
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'type': 'success', 'title': self.env._('Modules pointed to this server'),
                       'message': self.env._("%(n)s modules now report to this server.", n=pointed),
                       'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}},
        }

    def action_download_report(self):
        self.ensure_one()
        text = self._report_text()
        attachment = self.env['ir.attachment'].create({
            'name': 'hardware-survey-%s.txt' % self.id,
            'type': 'binary',
            'raw': text.encode('utf-8'),
            'mimetype': 'text/plain',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def _report_text(self):
        self.ensure_one()
        lines = [self.name, '=' * len(self.name), '']
        lines.append(self.env._('Modules: %(n)s', n=len(self.module_ids)))
        for module in self.module_ids:
            lines.append('  %s  %s  %s  %s' % (
                module._display_address(), module.serial or '-', module.hw_version or '-',
                dict(module._fields['status'].selection).get(module.status)))
        lines.append(self.env._('Controllers: %(n)s', n=len(self.ctrl_ids)))
        for ctrl in self.ctrl_ids:
            lines.append('  %s  %s  %s  %s' % (
                ctrl.name, dict(ctrl._fields['family'].selection).get(ctrl.family),
                dict(ctrl._fields['read_state'].selection).get(ctrl.read_state),
                self.env._('cards: %(n)s', n=ctrl.cards_read)))
        lines.append(self.env._('Cards: %(n)s', n=len(self.card_ids)))
        lines.append(self.env._('People: %(n)s', n=len(self.person_ids)))
        lines.append(self.env._('Proposed access groups: %(n)s', n=len(self.group_ids)))
        for group in self.group_ids:
            lines.append('  %s: %s' % (group.name, self.env._(
                '%(cards)s cards, %(doors)s doors', cards=group.card_count, doors=group.door_count)))
        lines.append('')
        lines.append(self.env._('Findings'))
        for issue in self.issue_ids:
            lines.append('  [%s] %s' % (dict(issue._fields['severity'].selection).get(issue.severity),
                                        issue.message))
        return '\n'.join(lines) + '\n'

    # ------------------------------------------------------------ the worker

    def _wake_the_worker(self):
        """Ask the scheduled action to run now. A disabled or missing action is
        said out loud: the survey would otherwise sit in its working state for
        ever with nothing to tell the operator why."""
        cron = self.env.ref('hr_rfid_hardware_import.ir_cron_hw_import_run', raise_if_not_found=False)
        if not cron or not cron.sudo().active:
            raise UserError(self.env._(
                "The scheduled action 'RFID: continue hardware surveys' is disabled or missing, so the "
                "survey cannot work in the background. Enable it under Settings > Technical > Scheduled "
                "Actions, then try again."))
        cron.sudo()._trigger()

    def _finish(self, state, message=None):
        self.ensure_one()
        values = {'state': state, 'current_phase': False}
        if state == 'failed':
            values['last_error'] = message
        self.write(values)
        # The module passwords are only needed while the worker reads.
        self.module_ids.sudo().write({'module_password': False})
        if message:
            self.message_post(body=message)

    @api.model
    def _cron_process(self):
        """One pass of work, called by the scheduler."""
        if request:
            self.env['hr.rfid.hw.import.run']._wake_the_worker()
            return
        if self._abandon_stalled_runs():
            self.env['ir.cron']._commit_progress()
        run = self.search([('state', 'in', WORKER_STATES)], order='create_date asc', limit=1)
        if not run:
            return
        try:
            run._process_pass()
        except Exception as exc:  # noqa: BLE001 - every failure must close the survey
            _logger.error("Hardware survey %s could not be worked on: %s", run.id, exc, exc_info=True)
            self.env.cr.rollback()
            if isinstance(exc, UserError):
                problem = exc.args[0] if exc.args else str(exc)
            else:
                # The full traceback is in the server log; the operator gets
                # what to do next and a short tag for support.
                problem = self.env._("a technical error (%(tag)s)", tag=type(exc).__name__)
            run._finish('failed', self.env._(
                "The survey stopped because of a problem and was closed: %(problem)s. What was read and "
                "imported so far is kept. Press 'Reopen the survey' to continue from where it stopped; "
                "if it stops again, send the report to support.", problem=problem))
            self.env['ir.cron']._commit_progress()

    @api.model
    def _abandon_stalled_runs(self):
        """Close surveys the worker has abandoned, and clear the module passwords
        of surveys the operator has left parked for a day. Returns what changed."""
        cutoff = fields.Datetime.now() - timedelta(minutes=STALLED_MINUTES)
        stalled = self.search([('state', 'in', WORKER_STATES), ('write_date', '<', cutoff)])
        for run in stalled:
            _logger.warning("Hardware survey %s has not moved since %s - closing it", run.id, run.write_date)
            run._finish('failed', self.env._(
                "This survey stopped without finishing and has been closed. The module passwords it "
                "held have been cleared. What was read is kept; start a new survey when you are ready."))
        idle_cutoff = fields.Datetime.now() - timedelta(hours=IDLE_PASSWORD_HOURS)
        idle = self.search([('state', 'not in', WORKER_STATES + ('done', 'failed')),
                            ('write_date', '<', idle_cutoff)])
        idle_modules = idle.module_ids.sudo().filtered('module_password')
        if idle_modules:
            idle_modules.write({'module_password': False})
            for run in idle_modules.mapped('run_id'):
                run.message_post(body=self.env._(
                    "The module passwords of this survey were cleared after a day without activity; "
                    "enter them again before reading the modules."))
        return stalled | idle_modules.mapped('run_id')

    def _process_pass(self):
        self.ensure_one()
        if not self.try_lock_for_update():
            return
        self.invalidate_recordset(['state'])
        deadline = time.monotonic() + PASS_SECONDS
        if self.state == 'discovering':
            self._pass_discover()
        elif self.state == 'reading':
            self._pass_read(deadline)
        elif self.state == 'analysing':
            self._pass_analyse()
        elif self.state == 'importing':
            self._pass_import(deadline)

    def _save_progress(self, done=None, total=None, remaining=None):
        values = {}
        if done is not None:
            values['done_count'] = done
        if total is not None:
            values['total_count'] = total
        if values:
            self.write(values)
        # The scheduler reschedules itself only while something remains; other
        # surveys waiting for the worker count as remaining work, otherwise a
        # second survey started while the first one runs would wait a day.
        others = self.search_count([('state', 'in', WORKER_STATES), ('id', '!=', self.id)])
        self.env['ir.cron']._commit_progress(processed=1, remaining=(remaining or 0) + others)

    # ------------------------------------------------------------ discovery

    def _pass_discover(self):
        backend = self._backend()
        found = []
        if self.discovery_broadcast:
            try:
                found = backend.discovery().broadcast(timeout=self.discovery_timeout or 2.0)
            except transport.DiscoveryFailed as exc:
                # "The search could not run" is not "no modules on the network".
                # The operator gets the finding; the sysadmin gets the cause in the log.
                _logger.warning("Hardware survey %s: the network search could not run", self.id, exc_info=True)
                self._log_issue('warning', 'warning', self.env._(
                    "The network search could not be run on this server (the port it needs may be in use, "
                    "or the network may not allow it). Add the modules by address, or try the search again."),
                    phase='discovery')
        for item in found:
            module = self.module_ids.filtered(lambda m: m.ip == item['ip'] and m.port in (80, 0, False))[:1]
            if not module:
                module = self.env['hr.rfid.hw.import.module'].create({
                    'run_id': self.id, 'source': 'broadcast', 'ip': item['ip'], 'port': 80})
            module.write({
                'hostname': item.get('hostname'), 'mac': item.get('mac'),
                'hw_version': item.get('hw_version'), 'fw_version': item.get('fw_version'),
                'bridge_port': item.get('bridge_port') or 0,
            })
            self._adopt_serial(module, item.get('serial'))
        for module in self.module_ids:
            try:
                with self.env.cr.savepoint():
                    self._probe_module(module)
            except ValidationError as exc:
                # The same module reached by two addresses, or another rule of
                # the row: this row is set aside, the survey goes on.
                message = exc.args[0] if exc.args else str(exc)
                module.write({'status': 'unreachable', 'include': False, 'read_error': message})
                self._log_issue('warning', 'warning', self.env._(
                    "The module at %(ip)s was set aside: %(reason)s", ip=module._display_address(),
                    reason=message), phase='discovery', module_id=module)
        self.write({'state': 'draft', 'discovered_at': fields.Datetime.now(), 'current_phase': False,
                    'done_count': 1, 'total_count': 1})
        self._save_progress(remaining=0)

    def _adopt_serial(self, module, serial):
        """Give a discovered module its serial number unless another row of the
        survey already carries it (the same device reached by two addresses);
        then the row is set aside with a finding instead of a database error."""
        if not serial or module.serial == serial:
            return
        twin = self.module_ids.filtered(lambda m: m.serial == serial and m != module)[:1]
        if twin:
            module.write({'status': 'unreachable', 'include': False, 'read_error': self.env._(
                "The same module (serial %(serial)s) is already in the survey at %(ip)s.",
                serial=serial, ip=twin._display_address())})
            self._log_issue('warning', 'warning', self.env._(
                "The module at %(ip)s is the module already listed at %(other)s (serial %(serial)s); the "
                "second address was set aside.", ip=module._display_address(), other=twin._display_address(),
                serial=serial), phase='discovery', module_id=module)
            return
        module.write({'serial': serial})

    def _probe_module(self, module):
        """Ask the module who it is; classify it new / known / unreachable. No writes to the device."""
        self.ensure_one()
        backend = self._backend()
        values = {}
        if module.source == 'manual' and not module.serial:
            answer = backend.discovery().unicast(module.ip)
            if answer:
                values.update({'hostname': answer.get('hostname'), 'mac': answer.get('mac'),
                               'hw_version': answer.get('hw_version'), 'fw_version': answer.get('fw_version'),
                               'serial': answer.get('serial'), 'bridge_port': answer.get('bridge_port') or 0})
        client = self._client_for(module)
        try:
            config = client.get_config()
        except transport.Unreachable as exc:
            module.write(dict(values, status='unreachable', read_error=str(exc)))
            return False
        sdk = config.get('sdk') or {}
        settings = config.get('sdkSettings') or {}
        values.update({
            'serial': str(config.get('convertor') or values.get('serial') or module.serial or ''),
            'hw_version': str(sdk.get('sdkHardware') or values.get('hw_version') or module.hw_version or ''),
            'fw_version': str(sdk.get('sdkVersion') or values.get('fw_version') or module.fw_version or ''),
            'dev_found': int(sdk.get('devFound') or 0),
            'server_url': self._strip_secrets(str(settings.get('Server_URL') or settings.get('stsu') or '')),
            'config_json': json.dumps(self._strip_secrets(config)),
            'read_error': False,
        })
        existing, ours = self._existing_webstack(values['serial'])
        if existing:
            values.update({'status': 'known', 'existing_webstack_id': existing.id if ours else False})
            if module.status != 'known':
                values['include'] = False
        else:
            values.update({'status': 'new', 'existing_webstack_id': False})
        module.write(values)
        return True

    @api.model
    def _strip_secrets(self, config):
        """The module configuration without anything that opens a door: values
        under secret-looking keys, and credentials embedded in addresses."""
        def clean(node):
            if isinstance(node, dict):
                return {k: ('***' if any(s in k.lower() for s in SECRET_KEY_HINTS) else clean(v))
                        for k, v in node.items()}
            if isinstance(node, list):
                return [clean(v) for v in node]
            if isinstance(node, str):
                return USERINFO_IN_URL.sub('://***@', node)
            return node
        return clean(config)

    # ------------------------------------------------------------ reading

    def _pass_read(self, deadline):
        from .reader import SurveyReader
        modules = self.module_ids.filtered(lambda m: m.include and m.status != 'unreachable')
        done = 0
        for module in modules:
            if module.read_state in ('done', 'failed'):
                # A failed module is finished until the operator asks for it
                # again; the worker does not knock on a dead address each pass.
                done += 1
                continue
            reader = SurveyReader(self, module, self._client_for(module))
            finished = reader.read(deadline)
            if finished:
                done += 1
            self._save_progress(done=done, total=len(modules), remaining=len(modules) - done)
            if time.monotonic() > deadline:
                self._wake_the_worker()
                return
        self.write({'state': 'analysing', 'read_at': fields.Datetime.now(),
                    'current_phase': self.env._('Analysing')})
        self._save_progress(remaining=1)
        if time.monotonic() < deadline:
            self._pass_analyse()
        else:
            self._wake_the_worker()

    def _pass_analyse(self):
        from .analyser import SurveyAnalyser
        SurveyAnalyser(self).analyse()
        self.write({'state': 'naming', 'analysed_at': fields.Datetime.now(), 'current_phase': False,
                    'done_count': 1, 'total_count': 1})
        self._save_progress(remaining=0)

    # ------------------------------------------------------------ importing

    def _pass_import(self, deadline):
        from .importer import HardwareImporter
        importer = HardwareImporter(self)
        complete = importer.execute(deadline)
        if complete:
            self.write({'imported_at': fields.Datetime.now()})
            self._finish('done', self.env._(
                "The import finished. Nothing was sent to the controllers. To hand a module over to "
                "this system, use 'Point to this server' on the module."))
            self._save_progress(remaining=0)
        else:
            self._wake_the_worker()
