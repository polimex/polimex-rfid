# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration to clean up invalid RFID attendance data:
    1. Remove duplicate user events
    2. Remove multiple open attendances per employee
    3. Remove invalid attendance records
    4. Recalculate attendances for affected employees
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Starting hr_attendance_late migration 15.0.1.0.1")
    
    # Step 1: Remove duplicate hr_rfid_event_user records
    _logger.info("Step 1: Cleaning duplicate user events...")
    cr.execute("""
        DELETE FROM hr_rfid_event_user 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM hr_rfid_event_user 
            WHERE employee_id IS NOT NULL
            GROUP BY employee_id, event_time, door_id, event_action
        )
        AND employee_id IS NOT NULL
    """)
    deleted_events = cr.rowcount
    _logger.info(f"Deleted {deleted_events} duplicate user events")
    
    # Step 2: Find employees with multiple open attendances
    _logger.info("Step 2: Finding employees with multiple open attendances...")
    cr.execute("""
        SELECT employee_id, COUNT(*) as open_count
        FROM hr_attendance 
        WHERE check_out IS NULL
        GROUP BY employee_id
        HAVING COUNT(*) > 1
    """)
    employees_with_multiple = cr.fetchall()
    
    # Delete ALL open attendances for employees with multiple open records
    if employees_with_multiple:
        employee_ids = [emp[0] for emp in employees_with_multiple]
        _logger.info(f"Found {len(employee_ids)} employees with multiple open attendances")
        
        cr.execute("""
            DELETE FROM hr_attendance 
            WHERE employee_id = ANY(%s)
            AND check_out IS NULL
        """, (employee_ids,))
        deleted_open = cr.rowcount
        _logger.info(f"Deleted {deleted_open} open attendance records")
    
    # Step 3: Remove invalid attendance records
    _logger.info("Step 3: Removing invalid attendance records...")
    
    # Delete records where check_out < check_in
    cr.execute("""
        DELETE FROM hr_attendance 
        WHERE check_out IS NOT NULL 
        AND check_out < check_in
    """)
    deleted_invalid = cr.rowcount
    _logger.info(f"Deleted {deleted_invalid} records where check_out < check_in")
    
    # Delete records with duration > 24 hours
    cr.execute("""
        DELETE FROM hr_attendance
        WHERE check_out IS NOT NULL
        AND (check_out - check_in) > INTERVAL '24 hours'
    """)
    deleted_long = cr.rowcount
    _logger.info(f"Deleted {deleted_long} records with duration > 24 hours")
    
    # Step 4: Get list of affected employees for recalculation
    _logger.info("Step 4: Getting affected employees for recalculation...")
    cr.execute("""
        SELECT DISTINCT employee_id 
        FROM hr_attendance 
        WHERE check_in >= NOW() - INTERVAL '30 days'
        AND employee_id IN (
            SELECT id FROM hr_employee 
            WHERE id IN (
                SELECT DISTINCT employee_id 
                FROM hr_rfid_card 
                WHERE employee_id IS NOT NULL
            )
        )
    """)
    affected_employee_ids = [row[0] for row in cr.fetchall()]
    
    if affected_employee_ids:
        _logger.info(f"Found {len(affected_employee_ids)} employees to recalculate")
        
        # Recalculate attendance for affected employees
        from datetime import timedelta
        from odoo import fields
        
        employees = env['hr.employee'].browse(affected_employee_ids)
        from_date = fields.Date.today() - timedelta(days=30)
        to_date = fields.Date.today()
        
        for employee in employees.exists():
            try:
                _logger.info(f"Recalculating attendance for {employee.name}")
                if hasattr(employee, 'recalc_attendance'):
                    employee.recalc_attendance(from_date, to_date)
                # Also update attendance extra data
                employee.update_extra_attendance_data(from_date, to_date, overwrite_existing=True)
            except Exception as e:
                _logger.error(f"Error recalculating attendance for {employee.name}: {str(e)}")
    
    _logger.info("Migration 15.0.1.0.1 completed successfully")
    _logger.info(f"Summary: {deleted_events} duplicate events, "
                 f"{deleted_open if employees_with_multiple else 0} open attendances, "
                 f"{deleted_invalid} invalid attendances, {deleted_long} long attendances deleted")