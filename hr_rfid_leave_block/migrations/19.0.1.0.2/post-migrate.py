# Polimex Holding Ltd. - https://polimex.co
"""Time off stops the cards when it begins, not when it is approved.

The scheduled action is kept with noupdate, so its new job and pace are set
here (its name and next run: 19.0.1.0.3). Cards stopped at the approval of a leave that has not begun yet are
given back now; the scheduled action stops them again when the leave begins.
"""

import logging

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref(
        "hr_rfid_leave_block.ir_cron_restore_expired_leave_blocks",
        raise_if_not_found=False,
    )
    if cron:
        cron.write(
            {
                "code": "model._cron_follow_the_leaves()",
                "interval_number": 15,
                "interval_type": "minutes",
            }
        )
    early = env["hr.rfid.leave.block"].search(
        [("state", "=", "active"), ("leave_id.date_from", ">", fields.Datetime.now())]
    )
    if early:
        _logger.info(
            "Giving back RFID access stopped ahead of %s leave(s) that have not begun.",
            len(early),
        )
        early._restore()
