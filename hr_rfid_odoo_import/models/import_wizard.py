# -*- coding: utf-8 -*-
import json
import logging
import time
import xmlrpc.client

from markupsafe import Markup

from odoo import fields, models, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrRfidOdooImportWiz(models.TransientModel):
    _name = 'hr.rfid.odoo.import.wiz'
    _description = 'Import RFID Data from Odoo'

    # ── State ──────────────────────────────────────────────────
    state = fields.Selection(
        [
            ('connection', 'Connection'),
            ('configure', 'Configure'),
            ('confirm', 'Confirm'),
            ('importing', 'Importing'),
            ('done', 'Done'),
        ],
        string='State', default='connection', required=True, readonly=True,
        help="Step the wizard is currently on - Connection: enter source URL + creds. Configure: pick what to import. Confirm: review preview + conflicts. Importing: run in progress. Done: results shown.",
    )

    # ── Step 1: Connection ─────────────────────────────────────
    source_url = fields.Char(
        string='Source URL',
        required=True,
        help='Full URL of the source Odoo server, e.g. https://erp.example.com',
    )
    source_db = fields.Char(
        string='Source Database',
        help=(
            'Leave empty if the source server hosts a single database - it will '
            'be auto-detected. If the source has multiple databases, enter the '
            'exact database name here.'
        ),
    )
    source_slug = fields.Char(
        string='Source Identity',
        help=(
            "Which system the records come from. Leave it empty and it follows "
            "the name of the database being read, which is right for a one-off "
            "transfer.\n\n"
            "Fill it in when the same system is read from more than one place - "
            "a restored backup for the bulk of it, then the live server for what "
            "changed since. Both transfers must carry the SAME identity here, or "
            "the second one treats the live server as a different system and "
            "brings everything across a second time."
        ),
    )
    source_login = fields.Char(
        string='Username',
        default='admin',
        required=True,
        help="Login of an admin-level user on the source Odoo instance - the user must have read access to every model the import will fetch.",
    )
    source_password = fields.Char(
        string='Password',
        default='admin',
        required=True,
        help="Password for the source user above. Use an API key if the source enforces 2FA. Stored only for the wizard's lifetime.",
    )
    source_version = fields.Char(
        string='Source Odoo Version',
        readonly=True,
        help="Major Odoo version detected on the source instance (e.g. '14.0', '15.0'). Used to dispatch the right importer per phase.",
    )
    source_uid = fields.Integer(
        string='Source UID',
        readonly=True,
        help="res.users ID of the connected source user. Cached after Test Connection.",
    )
    installed_modules_json = fields.Text(
        string='Installed Modules (JSON)',
        readonly=True,
        help="JSON list of installed modules on the source instance.",
    )

    # ── Step 2: Configuration ──────────────────────────────────
    company_line_ids = fields.One2many(
        'hr.rfid.odoo.import.company.line',
        'wizard_id',
        string='Company Mapping',
        help="One row per company discovered on the source. Operator picks which to import and which existing target company to merge into.",
    )
    import_hardware = fields.Boolean(
        string='Import Hardware', default=True,
        help="Include webstacks, controllers, doors, readers and time schedules.",
    )
    import_people = fields.Boolean(
        string='Import People', default=True,
        help="Include employees and partner contacts referenced by the imported access groups and cards.",
    )
    import_access = fields.Boolean(
        string='Import Access Control', default=True,
        help="Include access groups (and their door/department bindings) and zones.",
    )
    import_cards = fields.Boolean(
        string='Import Cards', default=True,
        help="Include hr.rfid.card records, including their owner and access-group memberships.",
    )
    import_sites = fields.Boolean(
        string='Import sites', default=True,
        help="Include the tree of sites, the equipment assigned to them and "
             "the contacts that belong to them.",
    )
    import_cameras = fields.Boolean(
        string='Import cameras', default=True,
        help="Include ANPR cameras, the readers and doors that belong to them, "
             "and the plate lists they hold.",
    )
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
        help="Include the historical hr.rfid.event.user log. Can be large - disable for first pass, re-run separately later if needed.",
    )
    import_system_events = fields.Boolean(
        string='Import system events',
        default=False,
        help="Include the historical hr.rfid.event.system log (controller power loss, tamper, etc.).",
    )
    import_th_logs = fields.Boolean(
        string='Import temperature/humidity logs',
        default=False,
        help="Include temperature-controller log records. Disable unless the source actually used temperature controllers.",
    )
    event_date_from = fields.Date(
        string='Events from date',
        help='Only import events newer than this date. Leave empty for all events.',
    )
    orphan_event_cutoff = fields.Date(
        string='Module-only events from date',
        help="Some system events are recorded against the communication module alone, "
             "with no controller attached (power-on, module connected). They are usually "
             "the bulk of the log. Set a date to bring across only the recent ones and "
             "leave the older noise behind; leave empty to bring all of them. "
             "Events that do name a controller are always imported in full.",
    )
    import_vending = fields.Boolean(
        string='Import vending data',
        default=False,
        help="Include vending balances, history and events. Only visible if both source and target have hr_rfid_vending installed.",
    )
    import_attendance = fields.Boolean(
        string='Import attendance',
        default=False,
        help="Include hr.attendance records linked to RFID events.",
    )
    import_attendance_extra = fields.Boolean(
        string='Import attendance extra',
        default=False,
        help="Include the daily roll-ups produced by hr_attendance_late (late/overtime/extra time).",
    )
    import_service = fields.Boolean(
        string='Import service data',
        default=False,
        help="Include rfid.service catalog and rfid.service.sale records from the source.",
    )

    source_has_vending = fields.Boolean(
        readonly=True,
        help="Source instance has the hr_rfid_vending module installed (detected from Test Connection).",
    )
    source_has_attendance = fields.Boolean(
        readonly=True,
        help="Source instance has hr_attendance_multi_rfid installed.",
    )
    source_has_attendance_late = fields.Boolean(
        readonly=True,
        help="Source instance has hr_attendance_late installed.",
    )
    source_has_service = fields.Boolean(
        readonly=True,
        help="Source instance has rfid_service_base installed.",
    )
    target_has_vending = fields.Boolean(
        compute='_compute_target_modules',
        help="This (target) instance has hr_rfid_vending installed - the related import_vending toggle is only meaningful when both source and target have it.",
    )
    target_has_attendance = fields.Boolean(
        compute='_compute_target_modules',
        help="This (target) instance has hr_attendance_multi_rfid installed.",
    )
    target_has_attendance_late = fields.Boolean(
        compute='_compute_target_modules',
        help="This (target) instance has hr_attendance_late installed.",
    )
    target_has_service = fields.Boolean(
        compute='_compute_target_modules',
        help="This (target) instance has rfid_service_base installed.",
    )

    # ── Step 3: Confirm / Preview ──────────────────────────────
    warnings = fields.Json(
        string='Warnings',
        compute='_compute_warnings',
        help="Pre-flight warnings calculated from the configuration (e.g. asked to import vending but target doesn't have the module). Shown on the confirm page.",
    )
    has_blocking = fields.Boolean(
        compute='_compute_warning_render',
        help="True while something must be sorted out before the transfer can start.",
    )
    has_advisory = fields.Boolean(
        compute='_compute_warning_render',
        help="True when there is something worth knowing that does not stop the transfer.",
    )
    blocking_html = fields.Html(
        compute='_compute_warning_render', sanitize=False,
        help="What must be sorted out first, written for the operator to read.",
    )
    advisory_html = fields.Html(
        compute='_compute_warning_render', sanitize=False,
        help="What is worth knowing before starting, written for the operator to read.",
    )
    preview_text = fields.Text(
        string='Preview',
        readonly=True,
        help="Human-readable summary of what will be created/linked if the operator confirms. Filled by the dry-run preview.",
    )
    conflict_ids = fields.One2many(
        'hr.rfid.odoo.import.conflict',
        'wizard_id',
        string='Conflicts',
        help="Per-record collisions detected against the target. Operator must pick a resolution (Link / Create / Skip) before running the import.",
    )
    dry_run = fields.Boolean(
        string='Full dry-run',
        default=False,
        help='Execute full import + rollback to verify everything works.',
    )

    # ── Step 4: Progress ───────────────────────────────────────
    progress_text = fields.Text(
        string='Progress', readonly=True,
        help="Live status of the running import job (current phase, processed records). Updated by the worker that performs the import.",
    )
    progress_percent = fields.Float(
        string='Progress %', readonly=True,
        help="Estimated completion percentage. Driven by the phase log - useful for the operator to gauge runtime.",
    )

    # ── Step 5: Results ────────────────────────────────────────
    error_message = fields.Text(
        string='Error', readonly=True,
        help="Top-level error captured if the run aborted mid-way. Individual phase errors are also stored on their log rows.",
    )

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

    #: Internal module name -> the thing the operator actually recognises.
    #: Warning text is read by the person moving the system, not by a
    #: developer; "hr_attendance_late" tells them nothing.
    _FEATURE_LABELS = {
        'hr_rfid_vending': lambda env: env._("vending machines"),
        'hr_attendance_multi_rfid': lambda env: env._("attendance"),
        'hr_attendance_late': lambda env: env._("working time reports"),
        'rfid_service_base': lambda env: env._("visitor services"),
    }

    def _feature_label(self, module_name):
        """Human name of a feature, for text the operator reads."""
        maker = self._FEATURE_LABELS.get(module_name)
        return maker(self.env) if maker else module_name

    @api.depends('warnings')
    def _compute_warning_render(self):
        """Render the warnings as something a person can read.

        ``warnings`` stays the machine-readable source - the gate in
        ``action_import`` and the tests read its structure. These fields are
        derived from it purely for display, so nothing depends on the markup.
        """
        for wiz in self:
            entries = wiz.warnings or {}
            blocking = [v.get('message', '') for v in entries.values()
                        if v.get('level') == 'danger']
            advisory = [v.get('message', '') for v in entries.values()
                        if v.get('level') != 'danger']
            wiz.has_blocking = bool(blocking)
            wiz.has_advisory = bool(advisory)
            wiz.blocking_html = wiz._render_notice_list(blocking)
            wiz.advisory_html = wiz._render_notice_list(advisory)

    @staticmethod
    def _render_notice_list(messages):
        if not messages:
            return False
        return Markup('<ul class="mb-0">%s</ul>') % Markup('').join(
            Markup('<li>%s</li>') % m for m in messages
        )

    @api.depends('state',
                 'company_line_ids.do_import', 'company_line_ids.target_company_id',
                 'conflict_ids', 'conflict_ids.resolution',
                 'source_db', 'source_slug',
                 'import_vending', 'import_attendance',
                 'import_attendance_extra', 'import_service',
                 'source_has_vending', 'source_has_attendance',
                 'source_has_attendance_late', 'source_has_service')
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
                    feature = wiz._feature_label(mod_name)
                    if getattr(wiz, field_name):
                        # User wants to import but target module is missing - block
                        warnings[f'missing_{mod_name}'] = {
                            'level': 'danger',
                            'message': self.env._(
                                "This system cannot take over %(feature)s yet. "
                                "Add that capability here first, or leave it out "
                                "of the transfer.",
                                feature=feature,
                            ),
                        }
                    else:
                        # Informational: source has module, target doesn't
                        warnings[f'info_missing_{mod_name}'] = {
                            'level': 'warning',
                            'message': self.env._(
                                "The other system keeps %(feature)s, which this one "
                                "does not have. That data will stay behind.",
                                feature=feature,
                            ),
                        }

            # Check: something here already came from a DIFFERENT system
            warnings.update(wiz._warn_about_other_source_identity())

            # Always said out loud: a repeat transfer refreshes from the source
            warnings.update(wiz._warn_about_refresh_on_rerun())

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
    # Which system are we transferring from
    # ══════════════════════════════════════════════════════════

    #: How many systems to name in the warning before it stops listing.
    OTHER_SOURCE_NAMES_SHOWN = 3

    def _effective_source_identity(self):
        """The identity this transfer will record its records against."""
        self.ensure_one()
        from .importers.base_importer import normalise_source_slug
        return normalise_source_slug(self.source_slug or self.source_db)

    @staticmethod
    def _escape_for_like(value):
        """A literal string, safe to use as the start of a LIKE pattern."""
        return (value.replace('\\', '\\\\')
                     .replace('_', r'\_')
                     .replace('%', r'\%'))

    def _identities_this_transfer_has_read(self):
        """Every system a transfer started here has read, under the name it used.

        This is what tells our own transfers apart from the other import tools.
        All three of them - this one, the Andromeda import and the old cloud
        import - record what they bring in the same way, so the records
        themselves cannot say which tool put them here. The question can be put
        the other way round: this module keeps a permanent account of every
        transfer ever started in this database, and each one names the system it
        read. A name that is not in that account belongs to another tool, which
        reads something this transfer cannot read at all - so its records can
        neither be recognised nor copied a second time by the transfer being
        prepared now, and warning about them would stop a first transfer over a
        system the operator never chose.
        """
        self.ensure_one()
        from .importers.base_importer import normalise_source_slug
        runs = self.env['hr.rfid.odoo.import.run'].sudo().search_read(
            [], ['source_slug', 'source_db'])
        names = {
            normalise_source_slug(run['source_slug'] or run['source_db'] or '')
            for run in runs
        }
        names.discard('')
        return names

    def _holds_records_from(self, identity):
        """Whether anything that system brought over is still here."""
        self.ensure_one()
        from .importers.base_importer import (
            EXTERNAL_ID_MODULE, EXTERNAL_ID_PREFIX,
        )
        # Not readable by everyone who may run a transfer, and which systems
        # this database already holds is not private to them.
        return bool(self.env['ir.model.data'].sudo().search_count(
            [
                ('module', '=', EXTERNAL_ID_MODULE),
                ('name', '=like', self._escape_for_like(
                    '%s%s_' % (EXTERNAL_ID_PREFIX, identity)) + '%'),
            ],
            limit=1,
        ))

    def _other_source_identities(self):
        """Systems already transferred into this database, other than ours.

        Asked one system at a time, rather than by reading a sample of what is
        already here: a sample answers with whichever records it meets first, so
        in a database that also holds a large import from another tool the one
        name that matters can fall outside it and the warning never appears.
        """
        self.ensure_one()
        ours = self._effective_source_identity()
        if not ours:
            return []
        return [
            identity
            for identity in sorted(self._identities_this_transfer_has_read() - {ours})
            if self._holds_records_from(identity)
        ]

    def _warn_about_other_source_identity(self):
        """Warn when this transfer would file its records under a new name.

        The identity is part of how every transferred record is recognised on
        the next run. Read a restored backup once and the live server the next
        time, leaving the box empty both times, and the two are two different
        names for one system: nothing matches, and every person, door, zone,
        membership and event arrives a second time. Measured on the o15 cloud,
        that is 298 937 duplicated events alone.

        Blocking while the box is empty, because then nobody has decided
        anything. Filling it in IS the decision - the operator names the system
        and the transfer goes ahead on their word.
        """
        self.ensure_one()
        others = self._other_source_identities()
        if not others:
            return {}
        current = self._effective_source_identity()
        shown = others[:self.OTHER_SOURCE_NAMES_SHOWN]
        existing = ', '.join('"%s"' % name for name in shown)
        if len(others) > len(shown):
            existing = self.env._(
                "%(names)s and others", names=existing)

        if self.source_slug:
            # The operator has named the system themselves - taken as meant.
            return {'other_source_identity': {
                'level': 'warning',
                'message': self.env._(
                    "Records from %(existing)s are already here, and this "
                    "transfer is filed under \"%(current)s\". You have named "
                    "the system yourself, so the two are kept apart: anything "
                    "they both hold will end up here twice.",
                    existing=existing, current=current,
                ),
            }}
        return {'other_source_identity': {
            'level': 'danger',
            'message': self.env._(
                "Records from %(existing)s are already here. This transfer "
                "would file its own under \"%(current)s\", so the two would be "
                "treated as separate systems and everything they both hold "
                "would come across a second time - the same people, the same "
                "doors, the same events. If this is the system you transferred "
                "from before, put its name in the Source identity box on the "
                "first page. If it really is a different system, put "
                "\"%(current)s\" in that same box to say so, and start again.",
                existing=existing, current=current,
            ),
        }}

    def _warn_about_refresh_on_rerun(self):
        """Say plainly what a repeat transfer does to what is already here.

        Every word here has to be true of the code, because the operator
        decides whether to start on the strength of it. A repeat transfer does
        NOT do one single thing to everything it brought over, and the text has
        to say both halves:

        * The equipment and the cards go back to what the other system holds.
          They are written again every time (``_load_records``, and the time
          schedules explicitly), so a card switched off here comes back on and
          a door renamed here gets its old name back.
        * People, contacts, departments, staff tags, card types, access groups
          and sites are recognised by their external ID and left exactly as they
          are - the write is never reached for them - so a correction made here
          survives every later transfer.
        * Lists are a third case. One the other system keeps as a whole - the
          departments and the groups an access group inherits, the doors a
          reader serves - is written back whole, so an entry added here is
          taken out again. The example has to be one of those: the DOORS of an
          access group are not a list but permissions of their own, and those
          are only ever added, never taken away. Zone membership is only added
          to as well.

        The behaviour itself is the owner's decision and stays as it is; only
        the promise had to be brought into line with it.
        """
        self.ensure_one()
        return {'refresh_on_rerun': {
            'level': 'warning',
            'message': self.env._(
                "Running this transfer again later puts the equipment and the "
                "cards back to what the other system holds - a card switched "
                "off here comes back on, a door renamed here gets its old name "
                "back. People, contacts, departments and access groups keep the "
                "details corrected here. A list the other system keeps is "
                "rebuilt from it, so a department added here to an access group "
                "is taken out of it again. No record is deleted."
            ),
        }}

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
            # Auto-detect database name if left empty
            if not self.source_db:
                db_proxy = xmlrpc.client.ServerProxy(
                    f'{self.source_url}/xmlrpc/2/db',
                    allow_none=True,
                )
                try:
                    databases = db_proxy.list()
                except xmlrpc.client.Fault:
                    raise UserError(_(
                        "Source server does not expose the database list "
                        "(list_db=False). Please enter the database name manually."
                    ))
                if not databases:
                    raise UserError(_("No databases found on the source server."))
                if len(databases) > 1:
                    raise UserError(_(
                        "Source server hosts multiple databases: %s. "
                        "Please specify which one to use.",
                        ', '.join(databases),
                    ))
                self.source_db = databases[0]

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

            # Which features the source keeps. The list is DERIVED from the
            # phases (phase.py) rather than written here: a list maintained
            # separately falls behind whenever a phase is added, and the phase
            # then reports "the other system does not keep this" about data
            # that is sitting right there.
            from .importers.phase import source_probe_modules
            probe_modules = source_probe_modules()
            rfid_modules = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                'ir.module.module', 'search_read',
                [[('name', 'in', probe_modules), ('state', '=', 'installed')]],
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

    # Реалните УНИКАЛНИ ограничения в целта - единственото основание за конфликт.
    # Ключът е ПЪЛЕН: съпоставяне по ЧАСТ от него измисля конфликти там, където
    # базата няма нищо против. Измерено на живо (сесия 9): детекторът търсеше
    # `hr.rfid.ctrl` само по `serial_number`, а ограничението е
    # (serial_number, hw_version) - два контролера на РАЗЛИЧНИ клиенти със сериен
    # 868 и hw 11/17 не се сблъскват изобщо, но бяха обявени за един и същ уред.
    # `company_scoped=True` => ограничението е per company, тоест същата стойност
    # при друг наемател е ЗАКОННА, не конфликт.
    _CONFLICT_KEYS = {
        'hr.rfid.webstack': {
            'fields': ('serial',),
            'company_scoped': False,   # UNIQUE(serial)
        },
        'hr.rfid.ctrl': {
            'fields': ('serial_number', 'hw_version'),
            'company_scoped': False,   # UNIQUE(serial_number, hw_version)
        },
        'hr.rfid.card': {
            'fields': ('number',),
            'company_scoped': True,    # UNIQUE(number, company_id)
        },
    }

    def _source_scan_domain(self, model, company_ids):
        """Обхватът на сканирането в ИЗТОЧНИКА - винаги по фирмите на прогона.

        `hr.rfid.ctrl` няма собствен `company_id`; оста му е през webstack-а.
        Празен домейн (сканиране на целия източник) е дефект: докарва конфликти
        за чужди наематели в прогон, който не ги мигрира.
        """
        if model == 'hr.rfid.ctrl':
            return [('webstack_id.company_id', 'in', company_ids)]
        return [('company_id', 'in', company_ids)]

    def _external_id_target_id(self, importer, model, source_id):
        """Идентичността на вече мигриран запис - САМО от външния ИД."""
        return importer._resolve_from_imd(model, source_id)

    def _target_company_map(self):
        """{source company id: target company id} за фирмите в този прогон.

        Празен `target_company_id` значи "фирмата ще се създаде" - тогава в целта
        още няма нищо, с което да се сблъскаме.
        """
        return {
            line.source_id: line.target_company_id.id
            for line in self.company_line_ids.filtered('do_import')
            if line.target_company_id
        }

    def _conflict_probe_importer(self, company_ids):
        """Лек `BaseImporter` само за справки по външен ИД при конфликтите.

        Ползва се единствено `_resolve_from_imd` (четене на `ir.model.data`);
        нищо не се внася на този етап.
        """
        from .importers.base_importer import BaseImporter
        company_map = self._target_company_map()
        return BaseImporter(
            env=self.env,
            source_url=self.source_url,
            source_db=self.source_db,
            source_uid=self.source_uid,
            source_password=self.source_password,
            company_map={cid: company_map.get(cid) for cid in company_ids},
            options={},
            source_slug=self.source_slug,
        )

    def _detect_conflicts(self, models_proxy, company_ids):
        """Открий РЕАЛНИТЕ сблъсъци с уникалните ограничения на целта.

        Дисциплина (`identity-by-id-never-by-text`): идентичността на запис идва
        ЕДИНСТВЕНО от source id-то през външния ИД. Съвпадащ надпис - сериен номер,
        номер на карта - НЕ е идентичност; той е само повод базата да откаже реда.

        Затова тук:
          1. Източников запис, който вече има външен ИД = НЕ е конфликт (това е
             повторен прогон; картата source->target вече съществува и печели).
          2. Конфликт се вдига само когато целта ДЕЙСТВИТЕЛНО държи ПЪЛНИЯ ключ
             на ограничението, в правилния обхват (per company там, където
             ограничението е per company).
          3. Конфликтът се ДОКЛАДВА, не се разрешава мълчаливо: `resolution`
             остава празна и прогонът е блокиран, докато операторът не реши.
             Автоматичното "link" сливаше РАЗЛИЧНИ обекти - на живо закачи
             четците и вратите на един клиент за контролера на друг и повлече
             1 964 негови събития в чужда фирма.
        """
        self.conflict_ids.unlink()
        conflicts = []
        importer = self._conflict_probe_importer(company_ids)

        for model, key in self._CONFLICT_KEYS.items():
            try:
                conflicts.extend(self._detect_model_conflicts(
                    models_proxy, importer, model, key, company_ids))
            except Exception:
                # Пропуснат детектор значи прогон БЕЗ защитата, която той дава -
                # това е WARNING, не диагностика. Не е блокиращо, защото
                # ограничението, което детекторът предугажда, пак се налага от
                # базата: сблъсъкът ще гръмне при записа на реда, силно и видимо.
                # Загубата е удобството да се разбере ПРЕДИ прогона, не тихо
                # изтичане на данни.
                _logger.warning(
                    "Проверката за сблъсък по %s не можа да се изпълни - "
                    "прогонът продължава без нея", model, exc_info=True)

        if conflicts:
            self.env['hr.rfid.odoo.import.conflict'].create(conflicts)

    def _detect_model_conflicts(self, models_proxy, importer, model, key,
                                company_ids):
        """Конфликтите за един модел. Виж `_detect_conflicts` за дисциплината."""
        fields_to_read = ['display_name', *key['fields']]
        if key['company_scoped']:
            fields_to_read.append('company_id')
        source_records = models_proxy.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_read',
            [self._source_scan_domain(model, company_ids)],
            {'fields': fields_to_read},
        )

        Target = self.env[model].sudo().with_context(active_test=False)
        company_map = self._target_company_map()
        out = []
        for rec in source_records:
            # 1. Външният ИД е идентичността. Има ли ред - това НЕ е конфликт.
            if self._external_id_target_id(importer, model, rec['id']):
                continue
            # 2. Пълният ключ на ограничението, в правилния обхват.
            domain = []
            incomplete = False
            for f in key['fields']:
                value = rec.get(f)
                if not value:
                    # Празна част от ключа - PostgreSQL UNIQUE не хваща NULL,
                    # значи сблъсък няма как да има.
                    incomplete = True
                    break
                domain.append((f, '=', value))
            if incomplete:
                continue
            if key['company_scoped']:
                source_company = rec.get('company_id')
                source_company = (source_company[0]
                                  if isinstance(source_company, (list, tuple))
                                  else source_company)
                target_company = company_map.get(source_company)
                if not target_company:
                    continue
                domain.append(('company_id', '=', target_company))
            existing = Target.search(domain, limit=1)
            if not existing:
                continue
            out.append({
                'wizard_id': self.id,
                'source_model': model,
                'source_id': rec['id'],
                'source_name': rec.get('display_name') or str(rec['id']),
                'source_ref': ' / '.join(str(rec[f]) for f in key['fields']),
                'target_id': existing.id,
                'target_name': existing.display_name,
                'conflict_field': ', '.join(key['fields']),
                # Празна резолюция = блокира прогона до решение на оператора.
                'resolution': False,
            })
        return out

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

        run = self._queue_run()
        # Doing the work here would put it inside the HTTP request, which is
        # cut off after limit_time_real seconds - far less than a real site
        # takes. The request only records what to do and wakes the worker.
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Data Transfer"),
            'res_model': 'hr.rfid.odoo.import.run',
            'res_id': run.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _check_background_worker_available(self):
        """Refuse rather than accept a transfer nothing will ever pick up.

        A scheduled job that has been switched off is never run, not even when
        something asks for it: the trigger is dropped without a word
        (odoo/addons/base/models/ir_cron.py:774-776). The transfer would sit
        there reading "waiting to start" for ever, and the operator would press
        the button beside it again and again with nothing happening.
        """
        cron = self.env.ref('hr_rfid_odoo_import.ir_cron_import_run',
                            raise_if_not_found=False)
        if cron and cron.sudo().active:
            return
        if cron and self.env.user.has_group('base.group_system'):
            raise RedirectWarning(
                self.env._(
                    "The transfer cannot start: the scheduled task that does "
                    "the work is switched off. Switch it back on and try "
                    "again."),
                {
                    'type': 'ir.actions.act_window',
                    'res_model': 'ir.cron',
                    'res_id': cron.id,
                    'views': [(False, 'form')],
                    'target': 'current',
                },
                self.env._("Open the scheduled task"),
            )
        raise UserError(self.env._(
            "The transfer cannot start: the scheduled task that does the work "
            "is switched off. Please ask your system administrator to switch "
            "it back on."))

    def _queue_run(self):
        """Hand the work over to a record that outlives this dialog."""
        self.ensure_one()
        self._check_background_worker_available()
        run = self.env['hr.rfid.odoo.import.run'].create({
            'source_url': self.source_url,
            'source_db': self.source_db,
            'source_login': self.source_login,
            'source_password': self.source_password,
            'source_uid': self.source_uid,
            'source_slug': self.source_slug,
            'installed_modules_json': self.installed_modules_json,
            'options_json': json.dumps(self._build_options()),
            'company_map_json': json.dumps({
                str(line.source_id): line.target_company_id.id
                for line in self.company_line_ids.filtered('do_import')
            }),
            'resolution_json': json.dumps([
                {
                    'model': c.source_model,
                    'source_id': c.source_id,
                    'target_id': c.target_id,
                    'resolution': c.resolution,
                }
                for c in self.conflict_ids if c.resolution
            ]),
        })
        run.action_start()
        return run

    def _build_options(self):
        """What the operator chose, in the form the phases read."""
        self.ensure_one()
        return {
            'import_hardware': self.import_hardware,
            'import_people': self.import_people,
            'import_access': self.import_access,
            'import_cameras': self.import_cameras,
            'import_sites': self.import_sites,
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
            'orphan_event_cutoff': str(self.orphan_event_cutoff) if self.orphan_event_cutoff else False,
            'import_vending': self.import_vending and self.source_has_vending and self.target_has_vending,
            'import_attendance': self.import_attendance and self.source_has_attendance and self.target_has_attendance,
            'import_attendance_extra': self.import_attendance_extra and self.source_has_attendance_late and self.target_has_attendance_late,
            'import_service': self.import_service and self.source_has_service and self.target_has_service,
        }

    def _do_import(self):
        """Run everything in one go, in this transaction.

        Kept for tests and for a source small enough to finish inside a single
        request. The operator's path goes through the background transfer,
        which is the only one that can survive a real workload.
        """
        from .importers.base_importer import BaseImporter

        company_map = {
            line.source_id: line.target_company_id.id
            for line in self.company_line_ids.filtered('do_import')
        }
        options = self._build_options()

        # Initialize base importer
        importer = BaseImporter(
            env=self.env,
            source_url=self.source_url,
            source_db=self.source_db,
            source_uid=self.source_uid,
            source_password=self.source_password,
            company_map=company_map,
            options=options,
            source_slug=self.source_slug,
        )

        # Apply conflict resolutions
        for conflict in self.conflict_ids:
            if conflict.resolution == 'link':
                # `link_existing`, не само `_set_target_id`: одобреното от
                # оператора съответствие трябва да ОЦЕЛЕЕ прогона. Външният ИД
                # Е картата source->target - без реда сверката отчита класа като
                # липсващ, макар данните да са налице и правилно мапнати.
                importer.link_existing(
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

        from .importers.phase import phase_plan, total_weight

        source_modules = set(json.loads(self.installed_modules_json or '[]'))
        weight_total = total_weight()
        done_weight = 0

        for cls, skip_reason in phase_plan(self.env, options, source_modules):
            pct_start = done_weight * 100.0 / weight_total
            done_weight += cls.WEIGHT
            pct_end = done_weight * 100.0 / weight_total
            if skip_reason:
                self._log_skipped_phase(cls, skip_reason)
                self.progress_percent = pct_end
                continue
            self._run_phase(cls.PHASE_ID, cls.NAME, cls(importer),
                            pct_start, pct_end)

        self.progress_percent = 100.0
        self._append_progress(_("Import completed successfully!"))

    def _log_skipped_phase(self, cls, reason):
        """Record what was left out, and why.

        A phase that is skipped without a line in the log looks exactly like a
        phase that ran and found nothing: the operator sees an empty result in
        both cases and has no way to tell them apart. That is how missing
        capabilities went unnoticed until someone checked the data by hand
        weeks later.
        """
        self.env['hr.rfid.odoo.import.log'].create({
            'phase': cls.PHASE_ID,
            'model': cls.NAME,
            'status': 'skipped',
            'error_message': reason,
        })
        self._append_progress("  %s: %s", cls.NAME, reason)

    def _run_phase(self, phase_id, phase_name, phase_importer, pct_start, pct_end):
        """Execute a single import phase with logging.

        Each phase runs inside a savepoint. If a phase fails, only that
        phase's work is rolled back - previous phases are preserved.
        """
        self._append_progress(_("\n--- %s: %s ---", phase_id, phase_name))
        self.progress_percent = pct_start
        start_time = time.time()

        # id_map живее в паметта и НЕ се откатва със savepoint-а. Без снимка,
        # една паднала фаза оставя мапинги към записи, които вече не
        # съществуват, и всяка СЛЕДВАЩА фаза пише FK към тях: наблюдавано на
        # живо - Phase 2 падна с hr_employee_user_uniq, а фази 3b/4/5/6a/6b
        # после гръмнаха една по една с ForeignKeyViolation. По-опасният случай
        # е тих: освободеният id може да бъде преизползван от друг запис.
        id_map_snapshot = {m: dict(v) for m, v in phase_importer.b.id_map.items()}

        try:
            with self.env.cr.savepoint():
                results = phase_importer.run(self)

            duration = time.time() - start_time

            # Create log entries from results
            for result in (results or []):
                self.env['hr.rfid.odoo.import.log'].create({
                    'phase': phase_id,
                    'model': result.get('model', ''),
                    'source_count': result.get('source_count', 0),
                    'imported_count': result.get('imported_count', 0),
                    'skipped_count': result.get('skipped_count', 0),
                    'rejected_count': result.get('rejected_count', 0),
                    'linked_count': result.get('linked_count', 0),
                    'status': result.get('status', 'done'),
                    'duration': result.get('duration', duration),
                    'error_message': result.get('error', ''),
                })
                self._append_progress(
                    "  %s: %d imported, %d linked, %d skipped, %d rejected",
                    result.get('model', '?'),
                    result.get('imported_count', 0),
                    result.get('linked_count', 0),
                    result.get('skipped_count', 0),
                    result.get('rejected_count', 0),
                )

            self.progress_percent = pct_end

        except Exception as e:
            duration = time.time() - start_time
            _logger.error("Phase %s failed: %s", phase_id, e, exc_info=True)
            # Savepoint auto-rolled back - transaction is still clean. Върни и
            # id_map-а към състоянието отпреди фазата, за да не сочи към
            # изтрити записи.
            phase_importer.b.id_map.clear()
            phase_importer.b.id_map.update(id_map_snapshot)
            self.env['hr.rfid.odoo.import.log'].create({
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
