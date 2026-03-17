# -*- coding: utf-8 -*-
import json
import logging
import time
import xmlrpc.client

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrRfidOdooImportWiz(models.TransientModel):
    _name = 'hr.rfid.odoo.import.wiz'
    _description = 'Import RFID Data from Odoo'

    # ── State ──────────────────────────────────────────────────
    state = fields.Selection([
        ('connection', 'Connection'),
        ('configure', 'Configure'),
        ('confirm', 'Confirm'),
        ('importing', 'Importing'),
        ('done', 'Done'),
    ], string='State', default='connection', required=True, readonly=True)

    # ── Step 1: Connection ─────────────────────────────────────
    source_url = fields.Char(
        string='Source URL',
        default='http://localhost:8069',
        required=True,
    )
    source_db = fields.Char(
        string='Source Database',
        required=True,
    )
    source_login = fields.Char(
        string='Username',
        default='admin',
        required=True,
    )
    source_password = fields.Char(
        string='Password',
        default='admin',
        required=True,
    )
    source_version = fields.Char(
        string='Source Odoo Version',
        readonly=True,
    )
    source_uid = fields.Integer(
        string='Source UID',
        readonly=True,
    )
    installed_modules_json = fields.Text(
        string='Installed Modules (JSON)',
        readonly=True,
    )

    # ── Step 2: Configuration ──────────────────────────────────
    company_line_ids = fields.One2many(
        'hr.rfid.odoo.import.company.line',
        'wizard_id',
        string='Company Mapping',
    )
    import_hardware = fields.Boolean(string='Import Hardware', default=True)
    import_people = fields.Boolean(string='Import People', default=True)
    import_access = fields.Boolean(string='Import Access Control', default=True)
    import_cards = fields.Boolean(string='Import Cards', default=True)
    import_all_partners = fields.Boolean(
        string='Import all partners',
        default=False,
        help='Import all partners from selected companies, not just RFID-linked ones.',
    )
    import_all_employees = fields.Boolean(
        string='Import all employees',
        default=False,
        help='Import all employees from selected companies, not just RFID-linked ones.',
    )
    import_images = fields.Boolean(
        string='Import photos',
        default=True,
        help='Import employee and partner photos (may slow down import).',
    )
    import_users = fields.Boolean(
        string='Create users',
        default=False,
        help='Create res.users for imported employees (matched by login or created with temp password).',
    )
    import_user_groups = fields.Boolean(
        string='Transfer user groups',
        default=False,
        help='Copy security group assignments from source users (matched by xml_id).',
    )
    import_user_events = fields.Boolean(
        string='Import user events',
        default=False,
    )
    import_system_events = fields.Boolean(
        string='Import system events',
        default=False,
    )
    import_th_logs = fields.Boolean(
        string='Import temperature/humidity logs',
        default=False,
    )
    event_date_from = fields.Date(
        string='Events from date',
        help='Only import events newer than this date. Leave empty for all events.',
    )
    import_vending = fields.Boolean(
        string='Import vending data',
        default=False,
    )
    import_attendance = fields.Boolean(
        string='Import attendance',
        default=False,
    )
    import_attendance_extra = fields.Boolean(
        string='Import attendance extra',
        default=False,
    )
    import_service = fields.Boolean(
        string='Import service data',
        default=False,
    )

    # Module availability flags (computed from source + target)
    source_has_vending = fields.Boolean(readonly=True)
    source_has_attendance = fields.Boolean(readonly=True)
    source_has_attendance_late = fields.Boolean(readonly=True)
    source_has_service = fields.Boolean(readonly=True)
    target_has_vending = fields.Boolean(compute='_compute_target_modules')
    target_has_attendance = fields.Boolean(compute='_compute_target_modules')
    target_has_attendance_late = fields.Boolean(compute='_compute_target_modules')
    target_has_service = fields.Boolean(compute='_compute_target_modules')

    # ── Step 3: Confirm / Preview ──────────────────────────────
    warnings = fields.Json(
        string='Warnings',
        compute='_compute_warnings',
    )
    preview_text = fields.Text(
        string='Preview',
        readonly=True,
    )
    conflict_ids = fields.One2many(
        'hr.rfid.odoo.import.conflict',
        'wizard_id',
        string='Conflicts',
    )
    dry_run = fields.Boolean(
        string='Full dry-run',
        default=False,
        help='Execute full import + rollback to verify everything works.',
    )

    # ── Step 4: Progress ───────────────────────────────────────
    progress_text = fields.Text(string='Progress', readonly=True)
    progress_percent = fields.Float(string='Progress %', readonly=True)

    # ── Step 5: Results ────────────────────────────────────────
    log_ids = fields.One2many(
        'hr.rfid.odoo.import.log',
        'wizard_id',
        string='Import Log',
    )
    error_message = fields.Text(string='Error', readonly=True)

    # ══════════════════════════════════════════════════════════
    # Computed fields
    # ══════════════════════════════════════════════════════════

    def _compute_target_modules(self):
        IrModule = self.env['ir.module.module']
        for wiz in self:
            wiz.target_has_vending = bool(IrModule.search([
                ('name', '=', 'hr_rfid_vending'), ('state', '=', 'installed')
            ], limit=1))
            wiz.target_has_attendance = bool(IrModule.search([
                ('name', '=', 'hr_attendance_multi_rfid'), ('state', '=', 'installed')
            ], limit=1))
            wiz.target_has_attendance_late = bool(IrModule.search([
                ('name', '=', 'hr_attendance_late'), ('state', '=', 'installed')
            ], limit=1))
            wiz.target_has_service = bool(IrModule.search([
                ('name', '=', 'rfid_service_base'), ('state', '=', 'installed')
            ], limit=1))

    @api.depends('state', 'company_line_ids.do_import', 'conflict_ids')
    def _compute_warnings(self):
        for wiz in self:
            if wiz.state != 'confirm':
                wiz.warnings = False
                continue

            warnings = {}
            installed_modules = json.loads(wiz.installed_modules_json or '[]')

            # Check: no companies selected
            selected = wiz.company_line_ids.filtered('do_import')
            if not selected:
                warnings['no_companies'] = {
                    'level': 'danger',
                    'message': _("No companies selected for import."),
                }

            # Check: company not mapped
            for line in selected:
                if not line.target_company_id:
                    warnings[f'no_target_{line.source_id}'] = {
                        'level': 'danger',
                        'message': _(
                            "Company '%s' is selected but has no target company assigned.",
                            line.source_name,
                        ),
                    }

            # Check: source has module, target doesn't
            module_checks = [
                ('hr_rfid_vending', 'import_vending', 'source_has_vending', 'target_has_vending'),
                ('hr_attendance_multi_rfid', 'import_attendance', 'source_has_attendance', 'target_has_attendance'),
                ('hr_attendance_late', 'import_attendance_extra', 'source_has_attendance_late', 'target_has_attendance_late'),
                ('rfid_service_base', 'import_service', 'source_has_service', 'target_has_service'),
            ]
            for mod_name, field_name, src_field, tgt_field in module_checks:
                if getattr(wiz, src_field) and not getattr(wiz, tgt_field):
                    if getattr(wiz, field_name):
                        # User wants to import but target module is missing — block
                        warnings[f'missing_{mod_name}'] = {
                            'level': 'danger',
                            'message': _(
                                "Source has '%s' installed but it's not installed in target. "
                                "Install it first or disable this import option.",
                                mod_name,
                            ),
                        }
                    else:
                        # Informational: source has module, target doesn't
                        warnings[f'info_missing_{mod_name}'] = {
                            'level': 'warning',
                            'message': _(
                                "Source has '%s' installed but it's not installed in target. "
                                "Data for this module will not be imported.",
                                mod_name,
                            ),
                        }

            # Check: unresolved conflicts
            unresolved = wiz.conflict_ids.filtered(lambda c: not c.resolution)
            if unresolved:
                warnings['unresolved_conflicts'] = {
                    'level': 'danger',
                    'message': _(
                        "%d conflicts need resolution before import can proceed.",
                        len(unresolved),
                    ),
                }

            wiz.warnings = warnings if warnings else False

    # ══════════════════════════════════════════════════════════
    # Actions
    # ══════════════════════════════════════════════════════════

    def _keep_open(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'target': 'new',
            'views': [(False, 'form')],
            'res_id': self.id,
        }

    def action_test_connection(self):
        """Step 1 → Step 2: Test connection and load companies."""
        self.ensure_one()

        try:
            # Authenticate
            common = xmlrpc.client.ServerProxy(
                f'{self.source_url}/xmlrpc/2/common',
                allow_none=True,
            )
            uid = common.authenticate(
                self.source_db, self.source_login, self.source_password, {}
            )
            if not uid:
                raise UserError(_("Authentication failed. Check credentials."))

            models_proxy = xmlrpc.client.ServerProxy(
                f'{self.source_url}/xmlrpc/2/object',
                allow_none=True,
            )

            # Detect version
            base_mod = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                'ir.module.module', 'search_read',
                [[('name', '=', 'base'), ('state', '=', 'installed')]],
                {'fields': ['latest_version'], 'limit': 1}
            )
            version = base_mod[0]['latest_version'] if base_mod else 'unknown'

            # Detect installed RFID modules
            rfid_modules = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                'ir.module.module', 'search_read',
                [[('name', 'in', [
                    'hr_rfid', 'hr_rfid_vending', 'hr_attendance_multi_rfid',
                    'hr_attendance_late', 'rfid_service_base',
                    'hr_rfid_vertical_elections',
                ]), ('state', '=', 'installed')]],
                {'fields': ['name']}
            )
            installed = [m['name'] for m in rfid_modules]

            # Load companies
            companies = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                'res.company', 'search_read',
                [[]],
                {'fields': ['name'], 'order': 'id asc'}
            )

            # Update wizard
            self.write({
                'source_uid': uid,
                'source_version': version,
                'installed_modules_json': json.dumps(installed),
                'source_has_vending': 'hr_rfid_vending' in installed,
                'source_has_attendance': 'hr_attendance_multi_rfid' in installed,
                'source_has_attendance_late': 'hr_attendance_late' in installed,
                'source_has_service': 'rfid_service_base' in installed,
                'state': 'configure',
            })

            # Create company lines
            self.company_line_ids.unlink()
            for co in companies:
                self.env['hr.rfid.odoo.import.company.line'].create({
                    'wizard_id': self.id,
                    'source_id': co['id'],
                    'source_name': co['name'],
                    'do_import': True,
                })

        except xmlrpc.client.Fault as e:
            raise UserError(_("XML-RPC error: %s", e.faultString))
        except ConnectionRefusedError:
            raise UserError(_(
                "Cannot connect to %s. Is the source Odoo server running?",
                self.source_url,
            ))
        except Exception as e:
            if isinstance(e, (UserError, ValidationError)):
                raise
            raise UserError(_("Connection error: %s", str(e)))

        return self._keep_open()

    def action_preview(self):
        """Step 2 → Step 3: Generate preview with counts and detect conflicts."""
        self.ensure_one()

        selected = self.company_line_ids.filtered('do_import')
        if not selected:
            raise UserError(_("Please select at least one company to import."))

        for line in selected:
            if not line.target_company_id:
                raise UserError(_(
                    "Please assign a target company for '%s'.",
                    line.source_name,
                ))

        try:
            models_proxy = xmlrpc.client.ServerProxy(
                f'{self.source_url}/xmlrpc/2/object',
                allow_none=True,
            )

            company_ids = [l.source_id for l in selected]
            co_domain = [('company_id', 'in', company_ids)] if len(company_ids) > 1 \
                else [('company_id', '=', company_ids[0])]

            preview_lines = []
            preview_lines.append(_("=== Import Preview ===\n"))

            # Count source records for key models
            count_models = [
                ('hr.rfid.webstack', co_domain, 'Webstacks'),
                ('hr.rfid.ctrl', [], 'Controllers'),
                ('hr.rfid.door', [], 'Doors'),
                ('hr.rfid.card', co_domain, 'Cards'),
                ('hr.employee', co_domain, 'Employees'),
                ('res.partner', co_domain, 'Partners'),
                ('hr.rfid.access.group', co_domain, 'Access Groups'),
                ('hr.rfid.zone', [], 'Zones'),
            ]

            for model, domain, label in count_models:
                try:
                    count = models_proxy.execute_kw(
                        self.source_db, self.source_uid, self.source_password,
                        model, 'search_count', [domain]
                    )
                    preview_lines.append(f"  {label}: {count}")
                except Exception:
                    preview_lines.append(f"  {label}: (error reading)")

            # Event counts
            if self.import_user_events or self.import_system_events or self.import_th_logs:
                preview_lines.append(_("\n--- Events ---"))
                event_models = []
                if self.import_user_events:
                    event_models.append(('hr.rfid.event.user', 'User Events'))
                if self.import_system_events:
                    event_models.append(('hr.rfid.event.system', 'System Events'))
                if self.import_th_logs:
                    event_models.append(('hr.rfid.ctrl.th.log', 'TH Logs'))

                for model, label in event_models:
                    ev_domain = []
                    if self.event_date_from:
                        ev_domain.append(('event_time', '>=', str(self.event_date_from)))
                    try:
                        count = models_proxy.execute_kw(
                            self.source_db, self.source_uid, self.source_password,
                            model, 'search_count', [ev_domain]
                        )
                        preview_lines.append(f"  {label}: {count}")
                    except Exception:
                        preview_lines.append(f"  {label}: (error reading)")

            # Detect conflicts
            self._detect_conflicts(models_proxy, company_ids)

            if self.conflict_ids:
                preview_lines.append(_(
                    "\n--- %d Conflicts Detected ---",
                    len(self.conflict_ids),
                ))
                preview_lines.append(_(
                    "Review the conflicts table below and choose a resolution for each.",
                ))

            self.write({
                'preview_text': '\n'.join(str(l) for l in preview_lines),
                'state': 'confirm',
            })

        except Exception as e:
            if isinstance(e, (UserError, ValidationError)):
                raise
            raise UserError(_("Preview error: %s", str(e)))

        return self._keep_open()

    def _detect_conflicts(self, models_proxy, company_ids):
        """Scan source records against target for potential conflicts."""
        self.conflict_ids.unlink()
        conflicts = []

        co_domain = [('company_id', 'in', company_ids)] if len(company_ids) > 1 \
            else [('company_id', '=', company_ids[0])]

        # Webstacks: match by serial
        try:
            source_ws = models_proxy.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                'hr.rfid.webstack', 'search_read',
                [co_domain],
                {'fields': ['name', 'serial']}
            )
            for ws in source_ws:
                if not ws.get('serial'):
                    continue
                existing = self.env['hr.rfid.webstack'].search([
                    ('serial', '=', ws['serial'])
                ], limit=1)
                if existing:
                    conflicts.append({
                        'wizard_id': self.id,
                        'source_model': 'hr.rfid.webstack',
                        'source_id': ws['id'],
                        'source_name': ws['name'],
                        'source_ref': ws['serial'],
                        'target_id': existing.id,
                        'target_name': existing.display_name,
                        'conflict_field': 'serial',
                        'resolution': 'link',
                    })
        except Exception as e:
            _logger.warning("Error detecting webstack conflicts: %s", e)

        # Cards: match by number
        try:
            source_cards = models_proxy.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                'hr.rfid.card', 'search_read',
                [co_domain],
                {'fields': ['name', 'number']}
            )
            for card in source_cards:
                if not card.get('number'):
                    continue
                existing = self.env['hr.rfid.card'].search([
                    ('number', '=', card['number'])
                ], limit=1)
                if existing:
                    conflicts.append({
                        'wizard_id': self.id,
                        'source_model': 'hr.rfid.card',
                        'source_id': card['id'],
                        'source_name': card.get('name', card['number']),
                        'source_ref': card['number'],
                        'target_id': existing.id,
                        'target_name': existing.display_name,
                        'conflict_field': 'number',
                        'resolution': 'link',
                    })
        except Exception as e:
            _logger.warning("Error detecting card conflicts: %s", e)

        # Controllers: match by serial_number
        try:
            source_ctrls = models_proxy.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                'hr.rfid.ctrl', 'search_read',
                [[]],
                {'fields': ['name', 'serial_number']}
            )
            for ctrl in source_ctrls:
                if not ctrl.get('serial_number'):
                    continue
                existing = self.env['hr.rfid.ctrl'].search([
                    ('serial_number', '=', ctrl['serial_number'])
                ], limit=1)
                if existing:
                    conflicts.append({
                        'wizard_id': self.id,
                        'source_model': 'hr.rfid.ctrl',
                        'source_id': ctrl['id'],
                        'source_name': ctrl['name'],
                        'source_ref': str(ctrl['serial_number']),
                        'target_id': existing.id,
                        'target_name': existing.display_name,
                        'conflict_field': 'serial_number',
                        'resolution': 'link',
                    })
        except Exception as e:
            _logger.warning("Error detecting controller conflicts: %s", e)

        # Create conflict records
        if conflicts:
            self.env['hr.rfid.odoo.import.conflict'].create(conflicts)

    def action_back(self):
        """Navigate back one step."""
        self.ensure_one()
        back_map = {
            'configure': 'connection',
            'confirm': 'configure',
        }
        new_state = back_map.get(self.state)
        if new_state:
            self.state = new_state
        return self._keep_open()

    def action_import(self):
        """Step 3 → Step 4 → Step 5: Execute the import."""
        self.ensure_one()

        # Validate warnings
        if self.warnings:
            danger_warnings = {
                k: v for k, v in self.warnings.items()
                if v.get('level') == 'danger'
            }
            if danger_warnings:
                raise UserError(_(
                    "Cannot start import: there are %d blocking issues to resolve. "
                    "Check the warnings above.",
                    len(danger_warnings),
                ))

        self.state = 'importing'
        self.progress_percent = 0.0
        self.progress_text = _("Starting import...\n")

        try:
            self._do_import()
            self.state = 'done'
        except Exception as e:
            _logger.error("Import error: %s", e, exc_info=True)
            self.error_message = str(e)
            self.state = 'done'

        return self._keep_open()

    def _do_import(self):
        """Execute the full import process."""
        from .importers.base_importer import BaseImporter

        # Build company map
        company_map = {}
        for line in self.company_line_ids.filtered('do_import'):
            company_map[line.source_id] = line.target_company_id.id

        # Build options dict
        options = {
            'import_hardware': self.import_hardware,
            'import_people': self.import_people,
            'import_access': self.import_access,
            'import_cards': self.import_cards,
            'import_all_partners': self.import_all_partners,
            'import_all_employees': self.import_all_employees,
            'import_images': self.import_images,
            'import_users': self.import_users,
            'import_user_groups': self.import_user_groups,
            'import_user_events': self.import_user_events,
            'import_system_events': self.import_system_events,
            'import_th_logs': self.import_th_logs,
            'event_date_from': str(self.event_date_from) if self.event_date_from else False,
            'import_vending': self.import_vending and self.source_has_vending and self.target_has_vending,
            'import_attendance': self.import_attendance and self.source_has_attendance and self.target_has_attendance,
            'import_attendance_extra': self.import_attendance_extra and self.source_has_attendance_late and self.target_has_attendance_late,
            'import_service': self.import_service and self.source_has_service and self.target_has_service,
        }

        # Initialize base importer
        importer = BaseImporter(
            env=self.env,
            source_url=self.source_url,
            source_db=self.source_db,
            source_uid=self.source_uid,
            source_password=self.source_password,
            company_map=company_map,
            options=options,
        )

        # Apply conflict resolutions
        for conflict in self.conflict_ids:
            if conflict.resolution == 'link':
                importer._set_target_id(
                    conflict.source_model,
                    conflict.source_id,
                    conflict.target_id,
                )
            elif conflict.resolution == 'skip':
                # Use None sentinel to mark as skipped
                importer._set_target_id(
                    conflict.source_model,
                    conflict.source_id,
                    None,
                )

        # Phase 1+3: Core (foundation + hardware)
        from .importers.core_importer import CoreImporter
        self._run_phase(
            'Phase 1+3', 'Core & Hardware',
            CoreImporter(importer), 0, 30,
        )

        # Phase 2: People
        if options['import_people']:
            from .importers.people_importer import PeopleImporter
            self._run_phase(
                'Phase 2', 'People',
                PeopleImporter(importer), 30, 45,
            )

        # Phase 4: Access Control
        if options['import_access']:
            from .importers.access_importer import AccessImporter
            self._run_phase(
                'Phase 4', 'Access Control',
                AccessImporter(importer), 45, 60,
            )

        # Phase 5: Events
        if any([options['import_user_events'], options['import_system_events'], options['import_th_logs']]):
            from .importers.event_importer import EventImporter
            self._run_phase(
                'Phase 5', 'Events',
                EventImporter(importer), 60, 75,
            )

        # Phase 6a: Vending
        if options['import_vending']:
            from .importers.vending_importer import VendingImporter
            self._run_phase(
                'Phase 6a', 'Vending',
                VendingImporter(importer), 75, 85,
            )

        # Phase 6b: Attendance
        if options['import_attendance'] or options['import_attendance_extra']:
            from .importers.attendance_importer import AttendanceImporter
            self._run_phase(
                'Phase 6b', 'Attendance',
                AttendanceImporter(importer), 85, 92,
            )

        # Phase 6c: Service
        if options['import_service']:
            from .importers.service_importer import ServiceImporter
            self._run_phase(
                'Phase 6c', 'Service',
                ServiceImporter(importer), 92, 98,
            )

        self.progress_percent = 100.0
        self._append_progress(_("Import completed successfully!"))

    def _run_phase(self, phase_id, phase_name, phase_importer, pct_start, pct_end):
        """Execute a single import phase with logging.

        Each phase runs inside a savepoint. If a phase fails, only that
        phase's work is rolled back — previous phases are preserved.
        """
        self._append_progress(_("\n--- %s: %s ---", phase_id, phase_name))
        self.progress_percent = pct_start
        start_time = time.time()

        try:
            with self.env.cr.savepoint():
                results = phase_importer.run(self)

            duration = time.time() - start_time

            # Create log entries from results
            for result in (results or []):
                self.env['hr.rfid.odoo.import.log'].create({
                    'wizard_id': self.id,
                    'phase': phase_id,
                    'model': result.get('model', ''),
                    'source_count': result.get('source_count', 0),
                    'imported_count': result.get('imported_count', 0),
                    'skipped_count': result.get('skipped_count', 0),
                    'linked_count': result.get('linked_count', 0),
                    'status': result.get('status', 'done'),
                    'duration': result.get('duration', duration),
                    'error_message': result.get('error', ''),
                })
                self._append_progress(
                    "  %s: %d imported, %d linked, %d skipped",
                    result.get('model', '?'),
                    result.get('imported_count', 0),
                    result.get('linked_count', 0),
                    result.get('skipped_count', 0),
                )

            self.progress_percent = pct_end

        except Exception as e:
            duration = time.time() - start_time
            _logger.error("Phase %s failed: %s", phase_id, e, exc_info=True)
            # Savepoint auto-rolled back — transaction is still clean
            self.env['hr.rfid.odoo.import.log'].create({
                'wizard_id': self.id,
                'phase': phase_id,
                'model': phase_name,
                'status': 'error',
                'duration': duration,
                'error_message': str(e)[:500],
            })
            self._append_progress(_("  ERROR: %s", str(e)[:200]))

    def _append_progress(self, msg, *args):
        """Append a line to the progress text."""
        if args:
            msg = msg % args
        current = self.progress_text or ''
        self.progress_text = current + str(msg) + '\n'
