# Polimex Holding Ltd. - https://polimex.co
"""A stay the door closed says so: its exit mode becomes 'rfid'.

Until this version only the entry carried the mark of the RFID machinery;
the exit stayed at the field's default and read "Manual" on the attendance,
as if somebody had typed it.

Which stays ended at a door: the ones still marked as made by the machinery
(in_mode 'rfid'), closed, with the exit at the default. A check-out a person
typed turned the record into theirs (in_mode 'manual', hr.attendance.write),
the kiosk and the systray name themselves, and a stay closed by the
forgotten-badge rule carries 'auto_check_out' - none of them is touched.

Plain SQL, as the backfill of the entry mode (19.0.1.1.2): the value changes
nothing else, so no write hook has to run over a large table.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_attendance
           SET out_mode = 'rfid'
         WHERE in_mode = 'rfid'
           AND check_out IS NOT NULL
           AND (out_mode = 'manual' OR out_mode IS NULL)
    """)
    _logger.info(
        "hr_attendance_multi_rfid 19.0.1.6.4: %d stay(s) closed at a door now "
        "carry the exit mode 'rfid'",
        cr.rowcount,
    )
