# -*- coding: utf-8 -*-
"""
Migration 19.0.1.1.3 - Retire the module's own auto-close scheduled task.

The zone sweep now rides core's "Attendance: Automatically check-out
employees" task (our _cron_auto_check_out override): one scheduled task,
both closing rules. The module's own cron record was noupdate="1", so
dropping its data file leaves the record alive on every existing database,
still firing next to the core one - it has to be removed here.

Deleted through SQL on ir_cron + ir_model_data: the record is the module's
own, nothing else references it, and a migration must not depend on the
ORM state of the model registry mid-upgrade.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_cron
         WHERE id IN (SELECT res_id FROM ir_model_data
                       WHERE module = 'hr_attendance_multi_rfid'
                         AND name = 'hr_attendance_multi_rfid_autoclose_cron'
                         AND model = 'ir.cron')
    """)
    removed = cr.rowcount
    cr.execute("""
        DELETE FROM ir_model_data
         WHERE module = 'hr_attendance_multi_rfid'
           AND name = 'hr_attendance_multi_rfid_autoclose_cron'
    """)
    _logger.info(
        "hr_attendance_multi_rfid 19.0.1.1.3: retired %d module cron(s) - "
        "the zone sweep now runs on core's check-out task", removed,
    )
