from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidWebstack(models.Model):
    _name = 'hr.rfid.webstack'
    _inherit = ['hr.rfid.webstack', 'refresh.mixin']
    _description = 'Module'

    # Real-time refresh settings: Update views when webstacks are created or modified
    _refresh_on_create = True  # Refresh when new modules are connected
    _refresh_on_write = True   # Refresh when module status/settings change
    # Every check-in of every module stamps these; on a 60 s heartbeat that is
    # one dashboard broadcast per module per minute, measured at 92% of all the
    # bus traffic the suite produces - and it tells the operator nothing that is
    # not already on screen. The record is still written (the presence cron and
    # the "last seen" column read it), only the broadcast is dropped.
    #  - updated_at / last_ip: stamped on EVERY HTTP device request
    #    (hr_rfid/controllers/main.py, _ws_db_update_dict)
    #  - ws_last_seen / ws_last_n / ws_auth_fail_*: the same on the real-time
    #    channel; they live on polimex.ws.endpoint but reach this model through
    #    the _inherits delegation, so they hit this write() too
    #  - presence_misses: the presence scan's own tolerance counter; only the
    #    verdict it eventually produces (last_update) is news
    _refresh_ignore_fields = frozenset({
        'updated_at', 'last_ip', 'presence_misses',
        'ws_last_seen', 'ws_last_n', 'ws_auth_fail_count', 'ws_auth_fail_since',
    })

    def get_company_ids(self):
        # A shared module concerns every company that uses it.
        return self.company_id | self.sudo().shared_company_ids
