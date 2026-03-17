# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class EventImporter:
    """Phase 5: Events — Direct SQL batch for performance.

    Steps: event.user, event.system, th.log
    All via Direct SQL INSERT (bypass ORM — historical data without side effects).
    command_id = NULL (commands are not migrated).
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        """Execute Phase 5."""
        if self.b.options.get('import_user_events'):
            self._import_user_events()
        if self.b.options.get('import_system_events'):
            self._import_system_events()
        if self.b.options.get('import_th_logs'):
            self._import_th_logs()
        return self.results

    def _make_result(self, model, source_count, imported_count, linked_count=0,
                     skipped_count=0, duration=0, status='done', error=''):
        return {
            'model': model,
            'source_count': source_count,
            'imported_count': imported_count,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'duration': duration,
            'status': status,
            'error': error,
        }

    def _event_date_domain(self):
        """Build date filter domain for events."""
        date_from = self.b.options.get('event_date_from')
        if date_from:
            return [('event_time', '>=', date_from)]
        return []

    def _import_user_events(self):
        """Step 26: hr.rfid.event.user — Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.event.user'
        table = 'hr_rfid_event_user'

        domain = self._event_date_domain()
        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Required fields
        fields_to_read = ['event_time']
        # Optional fields (check source availability)
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id', 'input_js']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=2000)
        imported = 0
        skipped = 0

        # Target columns for SQL INSERT — only include columns available in target
        columns = ['event_time']
        for f in ['event_action', 'door_id', 'reader_id', 'card_id',
                  'employee_id', 'contact_id', 'controller_id']:
            if f in target_fields and f in fields_to_read:
                columns.append(f)
        if 'input_js' in target_fields and 'input_js' in fields_to_read:
            columns.append('input_js')

        # M2O field → (model, skip_if_unmapped)
        # Events may reference doors/controllers/readers from other companies — soft skip
        m2o_models = {
            'door_id': ('hr.rfid.door', True),
            'reader_id': ('hr.rfid.reader', True),
            'controller_id': ('hr.rfid.ctrl', False),
            'card_id': ('hr.rfid.card', False),
            'employee_id': ('hr.employee', False),
            'contact_id': ('res.partner', False),
        }

        rows = []
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

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported = self.b._direct_sql_insert(table, columns, rows)
            except Exception as e:
                _logger.error("Failed to insert user events: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported, 0, skipped,
            duration=time.time() - start,
        ))

    def _import_system_events(self):
        """Step 27: hr.rfid.event.system — Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.event.system'
        table = 'hr_rfid_event_system'

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        # Detect time field name in source and target
        # System events use 'timestamp' in both v15 and v19
        source_time_field = 'timestamp'
        if 'timestamp' not in source_fields_info:
            if 'event_time' in source_fields_info:
                source_time_field = 'event_time'
        target_time_field = 'timestamp'
        if 'timestamp' not in target_fields:
            target_time_field = 'event_time'

        # Build date domain using correct source field name
        domain = []
        date_from = self.b.options.get('event_date_from')
        if date_from:
            domain.append((source_time_field, '>=', date_from))

        fields_to_read = [source_time_field]
        for f in ['event_action', 'door_id', 'controller_id',
                  'error_description', 'input_js', 'card_number']:
            if f in source_fields_info:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=2000)
        imported = 0

        columns = [target_time_field]
        for f in ['event_action', 'door_id', 'controller_id', 'error_description']:
            if f in target_fields:
                columns.append(f)
        if 'input_js' in target_fields and 'input_js' in source_fields_info:
            columns.append('input_js')
        if 'card_number' in target_fields and 'card_number' in source_fields_info:
            columns.append('card_number')

        rows = []
        for rec in source_records:
            door_target = False
            if rec.get('door_id'):
                door_target = self.b._map_m2o('hr.rfid.door', rec['door_id'])
            ctrl_target = False
            if rec.get('controller_id'):
                ctrl_target = self.b._map_m2o('hr.rfid.ctrl', rec['controller_id'])

            row = [rec[source_time_field]]
            if 'event_action' in columns:
                row.append(rec.get('event_action', '') or None)
            if 'door_id' in columns:
                row.append(door_target or None)
            if 'controller_id' in columns:
                row.append(ctrl_target or None)
            if 'error_description' in columns:
                row.append(rec.get('error_description', '') or None)
            if 'input_js' in columns:
                row.append(rec.get('input_js', '') or None)
            if 'card_number' in columns:
                row.append(rec.get('card_number', '') or None)

            rows.append(tuple(row))

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported = self.b._direct_sql_insert(table, columns, rows)
            except Exception as e:
                _logger.error("Failed to insert system events: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))

    def _import_th_logs(self):
        """Step 28: hr.rfid.ctrl.th.log — Direct SQL batch."""
        start = time.time()
        model = 'hr.rfid.ctrl.th.log'
        table = 'hr_rfid_ctrl_th_log'

        domain = self._event_date_domain()
        if domain:
            # TH logs may use 'event_time' or 'log_date'
            if self.b._has_field(model, 'event_time'):
                pass  # domain already uses event_time
            elif self.b._has_field(model, 'log_date'):
                domain = [(d[0].replace('event_time', 'log_date'), d[1], d[2])
                          if d[0] == 'event_time' else d for d in domain]

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['th_id', 'temperature', 'humidity']
        if 'event_time' in source_fields_info:
            fields_to_read.append('event_time')
        if 'log_date' in source_fields_info:
            fields_to_read.append('log_date')

        source_records = self.b._read_all(model, domain, fields_to_read, batch_size=5000)
        imported = 0

        # Determine time column name in target
        time_col = 'event_time' if 'event_time' in target_fields else 'log_date'
        columns = [time_col, 'th_id', 'temperature', 'humidity']

        rows = []
        for rec in source_records:
            th_target = False
            if rec.get('th_id'):
                th_target = self.b._map_m2o('hr.rfid.ctrl.th', rec['th_id'])
            if not th_target:
                continue

            event_time = rec.get('event_time') or rec.get('log_date')
            row = (
                event_time,
                th_target,
                rec.get('temperature', 0.0),
                rec.get('humidity', 0.0),
            )
            rows.append(row)

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported = self.b._direct_sql_insert(table, columns, rows)
            except Exception as e:
                _logger.error("Failed to insert TH logs: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported,
            duration=time.time() - start,
        ))
