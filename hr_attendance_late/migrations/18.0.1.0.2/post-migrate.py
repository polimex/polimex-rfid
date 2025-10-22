# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration to fix attendance calculation issues:
    1. Remove hr.attendance.extra records with theoretical time but no actual attendance
    2. Recalculate attendance data for the last 30 days with corrected auto-close logic

    This fixes two issues:
    - Auto-close now uses max_time_in_zone instead of auto_close_time_for_zone
    - Prevents creation of attendance.extra records without real attendance data
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Starting hr_attendance_late migration 18.0.1.0.2")

    # Step 1: Find and delete invalid hr.attendance.extra records
    # These are records with theoretical work time but no actual attendance
    _logger.info("Step 1: Finding invalid attendance.extra records...")
    cr.execute("""
        SELECT hae.id, e.name, hae.for_date, hae.theoretical_work_time, hae.actual_work_time
        FROM hr_attendance_extra hae
        JOIN hr_employee e ON e.id = hae.employee_id
        WHERE hae.theoretical_work_time > 0
        AND hae.actual_work_time = 0
        AND NOT EXISTS (
            SELECT 1
            FROM hr_attendance ha
            WHERE ha.employee_id = hae.employee_id
            AND DATE(ha.check_in) = hae.for_date
        )
    """)

    invalid_records = cr.fetchall()
    if invalid_records:
        _logger.info(f"Found {len(invalid_records)} invalid attendance.extra records")

        # Log some examples for verification
        for i, record in enumerate(invalid_records[:5]):
            _logger.info(f"  Example {i+1}: Employee '{record[1]}' on {record[2]} - "
                        f"theoretical: {record[3]}h, actual: {record[4]}h")

        # Delete invalid records
        invalid_ids = [r[0] for r in invalid_records]
        cr.execute("""
            DELETE FROM hr_attendance_extra
            WHERE id = ANY(%s)
        """, (invalid_ids,))

        _logger.info(f"Deleted {cr.rowcount} invalid attendance.extra records")
    else:
        _logger.info("No invalid attendance.extra records found")

    # Step 2: Recalculate attendance data for the last 30 days
    # This applies the new auto-close logic using max_time_in_zone
    _logger.info("Step 2: Recalculating attendance data with corrected auto-close logic...")

    from datetime import timedelta
    from odoo import fields

    from_date = fields.Date.today() - timedelta(days=30)
    to_date = fields.Date.today()

    # Get all employees with attendance in the last 30 days
    cr.execute("""
        SELECT DISTINCT e.id, e.name
        FROM hr_employee e
        INNER JOIN hr_attendance a ON a.employee_id = e.id
        WHERE a.check_in >= %s::date
        ORDER BY e.name
    """, (from_date,))

    employees_data = cr.fetchall()

    if employees_data:
        _logger.info(f"Found {len(employees_data)} employees to recalculate")

        # Process in batches to avoid memory issues
        batch_size = 20
        total_employees = len(employees_data)

        for i in range(0, total_employees, batch_size):
            batch_data = employees_data[i:i + batch_size]
            batch_ids = [emp[0] for emp in batch_data]
            employees = env['hr.employee'].browse(batch_ids)

            batch_num = i // batch_size + 1
            total_batches = (total_employees + batch_size - 1) // batch_size
            _logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_ids)} employees)")

            for employee in employees.exists():
                try:
                    # Validate dates before calling
                    if not from_date or not to_date:
                        _logger.warning(f"Skipping {employee.name} - invalid dates: from={from_date}, to={to_date}")
                        continue

                    # Recalculate attendance extra data with overwrite
                    # Use context flag to prevent recursive recalculation from attendance hooks
                    employee.with_context(migration_mode=True).update_extra_attendance_data(
                        from_date, to_date, overwrite_existing=True
                    )
                    _logger.debug(f"  Recalculated: {employee.name}")
                except Exception as e:
                    _logger.error(f"Error recalculating attendance for {employee.name} (ID: {employee.id}): {str(e)}")
                    import traceback
                    _logger.error(traceback.format_exc())
                    continue

            # Commit after each batch
            env.cr.commit()
            completed = min(i + batch_size, total_employees)
            _logger.info(f"Completed {completed}/{total_employees} employees")
    else:
        _logger.info("No employees with recent attendance found")

    _logger.info("Migration 18.0.1.0.2 completed successfully")
    _logger.info(f"Summary: Deleted {len(invalid_records) if invalid_records else 0} invalid records, "
                 f"recalculated {len(employees_data)} employees")