import logging
import time

from odoo import SUPERUSER_ID, http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)

# One lookup per card swipe is the natural rate; a terminal that asks much
# faster is either misbehaving or being probed.
RATE_WINDOW_S = 10
RATE_MAX_CALLS = 20
_rate_state = {}


def _rate_limited(serial):
    """True when this module serial exceeded the lookup budget."""
    now = time.monotonic()
    window_start, count = _rate_state.get(serial, (now, 0))
    if now - window_start > RATE_WINDOW_S:
        window_start, count = now, 0
    count += 1
    _rate_state[serial] = (window_start, count)
    return count > RATE_MAX_CALLS


class TerminalLookup(http.Controller):
    """Read-only card-to-employee lookup for display terminals."""

    @http.route('/hr/rfid/terminal/lookup', type='json2', auth='none',
                methods=['POST'], csrf=False, cors='*', save_session=False)
    def lookup(self, **post):
        data = request.get_json_data() if not post else post
        serial = str(data.get('convertor') or '')
        key = str(data.get('key') or '')
        card_number = str(data.get('card') or '').strip()

        if not serial or not card_number:
            return {'found': False, 'error': 'missing_parameters'}
        if _rate_limited(serial):
            _logger.info('Terminal %s exceeded the lookup rate budget', serial)
            return {'found': False, 'error': 'rate_limited'}

        webstack = request.env['hr.rfid.webstack'].with_user(SUPERUSER_ID).search([
            '|', ('active', '=', True), ('active', '=', False),
            ('serial', '=', serial),
        ], limit=1)
        # Constant-time compare, same contract as the event endpoint: a forged
        # serial must not be able to enumerate the card base.
        if not webstack or not webstack.key or not tools.consteq(webstack.key, key):
            return {'found': False, 'error': 'unauthorized'}

        card = request.env['hr.rfid.card'].with_user(SUPERUSER_ID).search([
            ('number', '=', card_number),
            ('company_id', '=', webstack.company_id.id),
        ], limit=1)
        if not card:
            return {'found': False}

        owner = card.get_owner()
        if not owner:
            return {'found': False}
        return {
            'found': True,
            'name': owner.name or '',
            'employee_id': owner.id if owner._name == 'hr.employee' else 0,
        }
