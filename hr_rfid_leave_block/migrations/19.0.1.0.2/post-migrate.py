# Polimex Holding Ltd. - https://polimex.co
"""Time off stops the cards when it begins, not when it is approved.

The scheduled action is kept with noupdate, so its new job and pace are set
here. Cards stopped at the approval of a leave that has not begun yet are
given back now; the scheduled action stops them again when the leave begins.
"""

import logging

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)

CRON_NAME = "RFID: Follow time off (stop and give back access)"


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
        # The new name in English only: the translations of the old name go,
        # and the upgrade fills them from the module's catalogs right after
        # this script (odoo/modules/loading.py, _update_translations without
        # overwrite fills only the missing languages).
        cr.execute(
            "UPDATE ir_act_server SET name = jsonb_build_object('en_US', %s) WHERE id = %s",
            [CRON_NAME, cron.ir_actions_server_id.id],
        )
        cron.invalidate_recordset(["name"])
    early = env["hr.rfid.leave.block"].search(
        [("state", "=", "active"), ("leave_id.date_from", ">", fields.Datetime.now())]
    )
    if early:
        _logger.info(
            "Giving back RFID access stopped ahead of %s leave(s) that have not begun.",
            len(early),
        )
        early._restore()
