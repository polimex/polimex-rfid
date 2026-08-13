# -*- coding: utf-8 -*-
import logging
import time

from .base_importer import BaseImporter
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


class EventImporter(PhaseImporter):
    """Phase 5: Events - Direct SQL batch for performance.

    Steps: event.user, event.system, th.log
    All via Direct SQL INSERT (bypass ORM - historical data without side effects).
    command_id = NULL (commands are not migrated).

    Every read here is scoped to the companies being imported, through the
    Many2one chain that owns the record (see BaseImporter._scoped_domain).
    Relying on a per-row ``continue`` instead would ship the whole source
    table over XML-RPC on every per-company run, and would report the GLOBAL
    row count as this company's source count.
    """

    PHASE_ID = 'Phase 5'
    NAME = 'Events'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.event.user', 'hr.rfid.event.system')
    OPTION = ''
    OPTION_ANY = ('import_user_events', 'import_system_events', 'import_th_logs')
    WEIGHT = 15

    def run(self, wizard):
        """Execute Phase 5."""
        if self.b.options.get('import_user_events'):
            self._import_user_events()
        if self.b.options.get('import_system_events'):
            self._import_system_events()
        if self.b.options.get('import_th_logs'):
            self._import_th_logs()
        return self.results

    def _event_date_domain(self, field='event_time'):
        """Build date filter domain for events."""
        date_from = self.b.options.get('event_date_from')
        if date_from:
            return [(field, '>=', date_from)]
        return []

    def _import_user_events(self):
        """Step 26: hr.rfid.event.user - Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.event.user'
        table = 'hr_rfid_event_user'

        # Scope on reader_id: it is required=True on the model, whereas door_id
        # is nullable (the source writes it as False for alarm-line actions).
        # A dotted domain is an EXISTS, so a nullable link would silently drop
        # rows. Both chains yield the same 292685 rows on this source, but only
        # this one is guaranteed by a constraint rather than by luck.
        domain = (self.b._scoped_domain('reader_id.controller_id.webstack_id')
                  + self._event_date_domain())
        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        # Required fields
        fields_to_read = ['event_time']
        # Optional fields (check source availability)
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id', 'input_js',
                  'card_number', 'department_id', 'alarm_line_id']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=2000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        # Target columns for SQL INSERT - only include columns available in target
        columns = ['event_time']
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id',
                  'department_id', 'alarm_line_id', 'input_js', 'card_number']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)

        # M2O field → (model, skip_if_unmapped)
        # Events may reference doors/controllers/readers from other companies - soft skip
        m2o_models = {
            'door_id': ('hr.rfid.door', True),
            'reader_id': ('hr.rfid.reader', True),
            'controller_id': ('hr.rfid.ctrl', False),
            'card_id': ('hr.rfid.card', False),
            'employee_id': ('hr.employee', False),
            'contact_id': ('res.partner', False),
            'department_id': ('hr.department', False),
            'alarm_line_id': ('hr.rfid.ctrl.alarm', False),
        }

        rows = []
        src_ids = []
        for rec in source_records:
            row = []
            skip_row = False
            for col in columns:
                if col == 'event_time':
                    row.append(rec['event_time'])
                elif col in m2o_models:
                    model_name, skip_if_unmapped = m2o_models[col]
                    if rec.get(col):
                        target = self.b._map_m2o(model_name, rec[col])
                        if not target and skip_if_unmapped:
                            skip_row = True
                            break
                        row.append(target or None)
                    else:
                        row.append(None)
                else:
                    row.append(rec.get(col, '') or None)
            if skip_row:
                skipped += 1
                continue
            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert user events: %s", e, exc_info=True)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b._make_result(
            model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))

    def _import_system_events(self):
        """Step 27: hr.rfid.event.system - Direct SQL batch.

        Two things make this step different from the user-event one:

        1. The owning link is the WEBSTACK, not the door. A large share of
           system events name no controller at all (module power-on, module
           connected), so scoping through ``controller_id`` - which is what
           the source instance's own record rule does - hides them entirely.
        2. Because that class of event is mostly noise yet dominates the
           table, ``orphan_event_cutoff`` limits how far back the
           controller-less ones are carried. Events that DO name a
           controller are always imported in full.
        """
        start = time.time()
        model = 'hr.rfid.event.system'
        table = 'hr_rfid_event_system'

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        # Detect time field name in source and target
        # System events use 'timestamp' in both v15 and v19
        source_time_field = 'timestamp'
        if 'timestamp' not in source_fields_info:
            if 'event_time' in source_fields_info:
                source_time_field = 'event_time'
        target_time_field = 'timestamp'
        if 'timestamp' not in target_fields:
            target_time_field = 'event_time'

        domain = self.b._scoped_domain('webstack_id')
        orphan_cutoff = self.b.options.get('orphan_event_cutoff')
        if orphan_cutoff:
            # Keep every controller-bound event; take the module-only ones
            # from the cutoff onwards. The prefix operator binds the two
            # leaves that follow it; the scope leaf above stays ANDed.
            domain = domain + ['|', ('controller_id', '!=', False),
                               (source_time_field, '>=', orphan_cutoff)]
        domain += self._event_date_domain(source_time_field)

        fields_to_read = [source_time_field, 'webstack_id']
        for f in ['event_action', 'door_id', 'controller_id', 'alarm_line_id',
                  'error_description', 'input_js', 'card_number', 'siren',
                  'occurrences', 'last_occurrence']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=2000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        columns = [target_time_field]
        # webstack_id carries the company attribution - without it every row
        # lands unattributable and multi-company reporting cannot place it.
        for f in ['webstack_id', 'event_action', 'door_id', 'controller_id',
                  'alarm_line_id', 'error_description']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)
        for f in ['input_js', 'card_number', 'siren', 'occurrences',
                  'last_occurrence']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)

        m2o_models = {
            'webstack_id': ('hr.rfid.webstack', True),
            'door_id': ('hr.rfid.door', False),
            'controller_id': ('hr.rfid.ctrl', False),
            'alarm_line_id': ('hr.rfid.ctrl.alarm', False),
        }
        # Bulk SQL bypasses the ORM, so Python-side field defaults never run.
        # Anything the model declares a default for must be supplied here, or
        # the column lands NULL where the application expects a value.
        sql_defaults = {'occurrences': 1, 'siren': False}

        rows = []
        src_ids = []
        for rec in source_records:
            row = []
            skip_row = False
            for col in columns:
                if col == target_time_field:
                    row.append(rec[source_time_field])
                elif col in m2o_models:
                    model_name, skip_if_unmapped = m2o_models[col]
                    if rec.get(col):
                        target = self.b._map_m2o(model_name, rec[col])
                        if not target and skip_if_unmapped:
                            skip_row = True
                            break
                        row.append(target or None)
                    elif skip_if_unmapped:
                        # No owning module in the source => not attributable.
                        skip_row = True
                        break
                    else:
                        row.append(None)
                elif col in sql_defaults:
                    value = rec.get(col)
                    row.append(sql_defaults[col] if value in (False, None) else value)
                else:
                    row.append(rec.get(col, '') or None)
            if skip_row:
                skipped += 1
                continue
            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert system events: %s", e, exc_info=True)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b._make_result(
            model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))

    def _import_th_logs(self):
        """Step 28: hr.rfid.ctrl.th.log - Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.ctrl.th.log'
        table = 'hr_rfid_ctrl_th_log'

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        # TH logs may use 'event_time' or 'log_date' for the reading time.
        source_time_field = 'event_time' if 'event_time' in source_fields_info else 'log_date'
        domain = (self.b._scoped_domain('th_id.controller_id.webstack_id')
                  + self._event_date_domain(source_time_field))

        fields_to_read = ['th_id', 'temperature', 'humidity', source_time_field]

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        # Determine time column name in target
        time_col = 'event_time' if 'event_time' in target_fields else 'log_date'
        columns = [time_col, 'th_id', 'temperature', 'humidity']

        rows = []
        src_ids = []
        for rec in source_records:
            th_target = False
            if rec.get('th_id'):
                th_target = self.b._map_m2o('hr.rfid.ctrl.th', rec['th_id'])
            if not th_target:
                skipped += 1
                continue

            row = (
                rec.get(source_time_field),
                th_target,
                rec.get('temperature', 0.0),
                rec.get('humidity', 0.0),
            )
            rows.append(row)
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert TH logs: %s", e, exc_info=True)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b._make_result(
            model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))
