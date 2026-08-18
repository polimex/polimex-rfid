# -*- coding: utf-8 -*-
import logging
import time

from odoo import fields

from .base_importer import BaseImporter
from .phase import PhaseImporter

_logger = logging.getLogger(__name__)


#: What a day of work says: hours worked, day and night, against what was owed,
#: plus lateness, early leaving and overtime. Every name exists on the target
#: model - asserted by a test. The previous list asked for 'check_in',
#: 'check_out', 'late_minutes', 'early_leave_minutes', 'overtime_minutes' and
#: 'worked_hours', which exist in NEITHER version, so every roll-up would have
#: arrived as an empty shell: a person and a date, and not one of the numbers
#: the record is kept for. 'for_date' is NOT NULL in the target.
EXTRA_OPTIONAL_FIELDS = [
    'for_date', 'shift_number',
    'actual_work_time', 'actual_work_time_day', 'actual_work_time_night',
    'theoretical_work_time', 'late_time', 'early_come_time',
    'early_leave_time', 'overtime', 'overtime_night', 'extra_time',
    'extra_night',
]


class AttendanceImporter(PhaseImporter):
    """Phase 6b: Attendance data.

    Steps: hr.attendance (Direct SQL), hr.attendance.extra (Direct SQL).
    """

    PHASE_ID = 'Phase 6b'
    NAME = 'Attendance'
    REQUIRES_SOURCE = ('hr_attendance_multi_rfid',)
    # Asked about, not required: the daily roll-ups come from this module and
    # have their own switch, which can only be on if the source is known to
    # keep them.
    PROBE_SOURCE = ('hr_attendance_late',)
    REQUIRES_TARGET = ('hr.attendance',)
    OPTION = ''
    OPTION_ANY = ('import_attendance', 'import_attendance_extra')
    WEIGHT = 7

    def run(self, wizard):
        """Execute Phase 6b.

        Through ``steps`` so the two are independent. They were called one
        after the other, and on an Odoo 14 source - where hr_attendance_late
        keeps no daily roll-up model at all - the second one raised on its
        first line and the phase savepoint took the FIRST one's rows with it:
        196 659 attendances read, written and thrown away, reported as one
        red line. One step failing must never cost another step's work.
        """
        steps = []
        if self.b.options.get('import_attendance'):
            steps.append(self._import_attendance)
        if self.b.options.get('import_attendance_extra'):
            steps.append(self._import_attendance_extra)
        return self.steps(*steps)

    def _import_attendance(self):
        """Step 36: hr.attendance - Direct SQL batch."""
        start = time.time()
        model = 'hr.attendance'
        table = 'hr_attendance'

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        fields_to_read = ['employee_id', 'check_in', 'check_out']
        # in_zone_id added by rfid_service module
        if 'in_zone_id' in source_fields_info and 'in_zone_id' in target_fields:
            fields_to_read.append('in_zone_id')
        if 'out_zone_id' in source_fields_info and 'out_zone_id' in target_fields:
            fields_to_read.append('out_zone_id')

        # Attendance belongs to the employee's company. Reading globally and
        # dropping foreign rows in the loop reported the WHOLE source as this
        # company's source_count, so "no attendance for this client" and
        # "every row was dropped" looked identical in the protocol.
        cursor_key = 'attendance:%s' % model
        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            cursor_key, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

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
                skipped += 1
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
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))

    def _drop_days_already_summed_here(self, columns, rows, src_ids):
        """Leave out the days this system has already summed up itself.

        The daily figures are produced HERE too, by this system's own scheduled
        job, for whichever days it can see - and after a transfer it can see
        the days it has just received. So the most recent days end up with two
        rows for one person: the one that came across and the one worked out
        here. Nothing refuses it (there is no unique index), and a day with two
        rows is a day counted twice in every report over it. Measured while
        moving a 27-tenant cloud: 10 such days, all of them yesterday and
        today.

        The row already here is left alone rather than replaced: it was worked
        out from the attendances of a day that may still be running, and
        replacing it with a figure taken before midnight would be the same
        double bookkeeping in reverse.
        """
        if not rows or 'for_date' not in columns:
            return rows, src_ids, 0
        emp_at = columns.index('employee_id')
        date_at = columns.index('for_date')
        shift_at = columns.index('shift_number') if 'shift_number' in columns else None

        def day_key(employee, day, shift):
            """One shape for both sides of the comparison.

            The two sides arrive in DIFFERENT types and that is the whole
            trap: the other system hands its date over the wire as the text
            '2026-08-16', while reading our own table gives a date object, and
            a shift left unset is False here and 0 there. Compared as they
            come, the key never matches, no day is ever recognised as already
            summed, and this guard quietly does nothing at all - which is
            precisely what a review of it found before the second live run
            could hide it again.
            """
            if isinstance(employee, (list, tuple)):
                employee = employee[0]
            return (employee, fields.Date.to_date(day) if day else None,
                    int(shift or 0) if shift_at is not None else None)

        employees = {row[emp_at] for row in rows}
        dates = {row[date_at] for row in rows if row[date_at]}
        if not employees or not dates:
            return rows, src_ids, 0
        here = self.env['hr.attendance.extra'].sudo().search_read(
            [('employee_id', 'in', list(employees)),
             ('for_date', 'in', list(dates))],
            ['employee_id', 'for_date', 'shift_number'])
        taken = {day_key(rec['employee_id'], rec['for_date'],
                         rec.get('shift_number'))
                 for rec in here}
        kept_rows, kept_ids, dropped = [], [], 0
        for row, source_id in zip(rows, src_ids):
            key = day_key(row[emp_at], row[date_at],
                          row[shift_at] if shift_at is not None else None)
            if key in taken:
                dropped += 1
                continue
            kept_rows.append(row)
            kept_ids.append(source_id)
        return kept_rows, kept_ids, dropped

    def _import_attendance_extra(self):
        """Step 37: hr.attendance.extra - Direct SQL batch.

        Model from hr_attendance_late module (NOT hr_attendance_multi_rfid!).
        """
        start = time.time()
        model = 'hr.attendance.extra'
        table = 'hr_attendance_extra'

        if not self.b._has_model(model):
            # Odoo 14 ships hr_attendance_late without the daily roll-up
            # model - it only extends hr.attendance there. "That system keeps
            # no such thing" is not a failure, and saying so is not optional:
            # a step that returns nothing without a line reads exactly like a
            # step that ran and found no data.
            self.results.append(self.b._make_result(
                model, 0, 0, status='skipped',
                error=self.env._(
                    "The other system does not keep daily working-time "
                    "roll-ups - it only records the attendances themselves, "
                    "which came across above."),
                duration=time.time() - start,
            ))
            return

        source_fields_info = self.b._get_source_fields(model)
        # Real columns only - a non-stored field in a raw INSERT is an
        # UndefinedColumn that kills the whole step.
        target_fields = self.b._target_columns(model)

        fields_to_read = ['employee_id', 'department_id']
        # What a day of work actually says: hours worked, day and night,
        # against what was owed, plus lateness, early leaving and overtime.
        # The names are the ones both versions really use - a live 15 and this
        # 19 agree on all sixteen. The previous list asked for 'check_in',
        # 'check_out', 'late_minutes', 'early_leave_minutes',
        # 'overtime_minutes' and 'worked_hours', which exist in NEITHER, so
        # even when the step ran, every roll-up arrived as an empty shell -
        # a person and a date, and not one of the numbers the record is for.
        # 'for_date' is NOT NULL in the target - it must be read and written,
        # otherwise every batch is rejected and no extra record migrates at all.
        for f in EXTRA_OPTIONAL_FIELDS:
            if f in source_fields_info and f in target_fields:
                fields_to_read.append(f)

        cursor_key = 'attendance:%s' % model
        source_records = self.b._read_all(
            model, self.b._scoped_domain('employee_id'), fields_to_read,
            cursor_key, batch_size=5000)
        imported = 0
        already = 0
        rejected = 0
        skipped = 0

        columns = ['employee_id', 'department_id']
        for f in fields_to_read:
            if f not in columns:
                columns.append(f)

        rows = []
        src_ids = []
        for rec in source_records:
            emp_target = self.b._map_m2o('hr.employee', rec.get('employee_id'))
            if not emp_target:
                skipped += 1
                continue
            dept_target = self.b._map_m2o('hr.department', rec.get('department_id'))

            row = [emp_target, dept_target or None]
            for f in columns[2:]:
                row.append(rec.get(f) if rec.get(f) is not False else None)

            rows.append(tuple(row))
            src_ids.append(rec['id'])

        rows, src_ids, ours = self._drop_days_already_summed_here(
            columns, rows, src_ids)
        if ours:
            self.b.note_skip_reason(self.env._(
                "%(count)s day(s) had already been worked out here - the "
                "figures this system produced for them are kept, so a day is "
                "not counted twice", count=ours))
        skipped += ours

        if rows:
            try:
                with self.env.cr.savepoint():
                    imported, already, rejected = self.b._direct_sql_insert_tracked(
                        table, columns, rows, model, src_ids)
            except Exception as e:
                _logger.error("Failed to insert attendance extra: %s", e, exc_info=True)
                self.b.rewind_cursors(cursor_key)
                self.results.append(self.b._make_result(
                    model, len(source_records), 0, 0, len(source_records),
                    duration=time.time() - start,
                    status='error', error=str(e)[:500],
                ))
                return

        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(source_records), imported, already, skipped,
            duration=time.time() - start, rejected_count=rejected,
        ))
