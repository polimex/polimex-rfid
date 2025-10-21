# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Remove invalid SQL constraint 'hr_rfid_notification_no_notification_recipients'
    This constraint referenced a non-existent field 'notify_user_ids' and used incorrect
    SQL syntax for Many2many fields. The validation is properly handled by Python constraint.
    """
    _logger.info("Starting hr_rfid pre-migration 15.0.2.2.2")

    # Drop the constraint if it exists
    cr.execute("""
        ALTER TABLE hr_rfid_notification
        DROP CONSTRAINT IF EXISTS hr_rfid_notification_no_notification_recipients
    """)

    _logger.info("Dropped constraint hr_rfid_notification_no_notification_recipients (if existed)")
    _logger.info("Pre-migration 15.0.2.2.2 completed successfully")