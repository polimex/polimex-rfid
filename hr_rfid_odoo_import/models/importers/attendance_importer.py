# -*- coding: utf-8 -*-
import logging
import time

from odoo import _
from odoo.exceptions import UserError
from .base_importer import BaseImporter, IMPORT_CONTEXT

_logger = logging.getLogger(__name__)


class AttendanceImporter:
    """Phase 6b: Attendance data.

    Steps: hr.attendance (Direct SQL), hr.attendance.extra (Direct SQL).
    """

    def __init__(self, base: BaseImporter):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        """Execute Phase 6b."""
        if self.b.options.get('import_attendance'):
            self._import_attendance()
        if self.b.options.get('import_attendance_extra'):
            self._import_attendance_extra()
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

    def _import_attendance(self):
        """Step 36: hr.attendance — Direct SQL batch."""
        start = time.time()
        model = 'hr.attendance'
        table = 'hr_attendance'

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['employee_id', 'check_in', 'check_out']
        # in_zone_id added by rfid_service module
        if 'in_zone_id' in source_fields_info and 'in_zone_id' in target_fields:
            fields_to_read.append('in_zone_id')
        if 'out_zone_id' in source_fields_info and 'out_zone_id' in target_fields:
            fields_to_read.append('out_zone_id')

        source_records = self.b._read_all(model, [], fields_to_read, batch_size=5000)
        imported = 0
        already = 0

        # date is a stored computed field in v19 (from check_in + tz)
        # We must include it in SQL INSERT since it's required
        has_date_col = 'date' in target_fields
        columns = ['employee_id', 'check_in', 'check_out']
        if has_date_col:
            columns.append('date')
        if 'in_zone_id' in fields_to_read:
            columns.append('in_zone_id')
        if 'out_zone_id' in fields_to_read:
            columns.append('out_zone_id')

        rows = []
        src_ids = []
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                continue

            check_in = rec['check_in']
            row = [
                emp_target,
                check_in,
                rec.get('check_out') or None,
            ]
            if has_date_col:
                # Compute date from check_in (UTC → date, simplified)
                # check_in is a string like '2025-08-28 11:59:46'
                row.append(check_in[:10] if check_in else None)
            if 'in_zone_id' in columns:
                zone_target = self.b._map_m2o('hr.rfid.zone', rec.get('in_zone_id'))
                row.append(zone_target or None)
            if 'out_zone_id' in columns:
                zone_target = self.b._map_m2o('hr.rfid.zone', rec.get('out_zone_id'))
                row.append(zone_target or None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported, already,
            duration=time.time() - start,
        ))

    def _import_attendance_extra(self):
        """Step 37: hr.attendance.extra — Direct SQL batch.

        Model from hr_attendance_late module (NOT hr_attendance_multi_rfid!).
        """
        start = time.time()
        model = 'hr.attendance.extra'
        table = 'hr_attendance_extra'

        source_fields_info = self.b._get_source_fields(model)
        target_fields = set(self.env[model]._fields.keys())

        fields_to_read = ['employee_id', 'department_id']
        # 'for_date' is NOT NULL in the target — it must be read and written,
        # otherwise every batch is rejected and no extra record migrates at all.
        for f in ['for_date', 'check_in', 'check_out', 'late_minutes',
                   'early_leave_minutes', 'overtime_minutes', 'worked_hours']:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        source_records = self.b._read_all(model, [], fields_to_read, batch_size=5000)
        imported = 0
        already = 0

        columns = ['employee_id', 'department_id']
        # 'for_date' is NOT NULL in the target — it must be read and written,
        # otherwise every batch is rejected and no extra record migrates at all.
        for f in ['for_date', 'check_in', 'check_out', 'late_minutes',
                   'early_leave_minutes', 'overtime_minutes', 'worked_hours']:
            if f in fields_to_read:
                columns.append(f)

        rows = []
        src_ids = []
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                continue
            dept_target = self.b._map_m2o('hr.department', rec.get('department_id'))

            row = [emp_target, dept_target or None]
            for f in columns[2:]:
                row.append(rec.get(f) if rec.get(f) is not False else None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance extra: %s", e)
                self.results.append(self._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self._make_result(
            model, len(source_records), imported, already,
            duration=time.time() - start,
        ))
