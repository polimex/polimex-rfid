from odoo import fields, models, api, _, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class HrRfidController(models.Model):
    _name = 'hr.rfid.ctrl'
    _inherit = ['hr.rfid.ctrl', 'refresh.mixin']
    _description = 'Controller'

    # Real-time refresh settings: Update views when controllers are created or modified
    _refresh_on_create = True  # Refresh when new controllers are added
    _refresh_on_write = True   # Refresh when controller settings change
    # The 5-minute status poll (B3) brings analog readings that differ on every
    # single read - supply voltage, temperature, humidity - alongside the state
    # the operator actually watches. Without this list every controller would
    # broadcast a refresh every 5 minutes forever, saying nothing.
    # NB: the gate only silences a write whose fields are ALL listed here, so it
    # works together with the write-on-change in the B3 handler
    # (hr_rfid/models/hr_rfid_webstack.py): an unchanged poll must not carry the
    # state fields along, or the write stops being ignorable.
    _refresh_ignore_fields = frozenset({
        'system_voltage', 'input_voltage', 'temperature', 'humidity',
        'cards_count', 'read_b3_cmd',
    })

    def get_company_id(self):
        return self.webstack_id.company_id

    def get_company_ids(self):
        return self.webstack_id.get_company_ids()
