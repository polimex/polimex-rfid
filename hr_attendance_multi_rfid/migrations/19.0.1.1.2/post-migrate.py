# -*- coding: utf-8 -*-
"""
Migration 19.0.1.1.2 - Stamp zone-born attendance as made by the RFID machinery.

hr.attendance now carries in_mode='rfid' on every record the RFID flow
creates, and the attendance rebuild deletes ONLY those records - a typed-in
record (manual/kiosk/systray) survives a rebuild untouched.

Existing databases were written before the stamp existed: everything the zone
flow made sits at the core default ('manual') or NULL, indistinguishable from
a real hand-typed entry. The one thing only the zone flow ever sets is
in_zone_id, so records carrying a zone and still wearing the default mode are
the zone flow's own and are backfilled to 'rfid'. A record whose mode was set
by a person through the UI can only be 'manual' after an edit - but the UI
never sets in_zone_id, so the combination stays unambiguous.

Plain SQL: a backfill over a potentially large table must not fire ORM
write hooks (person_left, recompute) for a value that changes nothing else.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE hr_attendance
           SET in_mode = 'rfid'
         WHERE in_zone_id IS NOT NULL
           AND (in_mode = 'manual' OR in_mode IS NULL)
    """)
    _logger.info(
        "hr_attendance_multi_rfid 19.0.1.1.2: stamped %d zone-born attendance "
        "record(s) with in_mode='rfid'", cr.rowcount,
    )
