# Polimex Holding Ltd. - https://polimex.co
"""The scheduled action that follows time off shows its new name and runs on
its new pace at once.

The name is set in English only: the translations of the old name go, and
the upgrade fills them from the module's catalogs right after this script
(odoo/modules/loading.py, _update_translations without overwrite fills only
the missing languages). The list of scheduled actions shows a stored copy of
the name (ir.cron.cron_name, computed from the server action's name), so the
copy is recomputed too.

Before the action followed the leaves every 15 minutes it ran once a day; its
next run is brought forward, or a leave that begins before that run would
keep its cards working until then.
"""

from odoo import SUPERUSER_ID, api, fields

CRON_NAME = "RFID: Follow time off (stop and give back access)"


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref(
        "hr_rfid_leave_block.ir_cron_restore_expired_leave_blocks",
        raise_if_not_found=False,
    )
    if not cron:
        return
    action = cron.ir_actions_server_id
    cr.execute(
        "UPDATE ir_act_server SET name = jsonb_build_object('en_US', %s) WHERE id = %s",
        [CRON_NAME, action.id],
    )
    action.invalidate_recordset(["name"])
    action.modified(["name"])
    now = fields.Datetime.now()
    if cron.nextcall > now:
        cron.nextcall = now
    env.flush_all()
