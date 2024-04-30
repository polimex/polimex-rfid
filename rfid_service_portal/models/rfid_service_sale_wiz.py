from odoo import fields, models, api, _
from datetime import datetime, timedelta, date, time, timezone
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_cron import _intervalTypes
from odoo.addons.resource.models.utils import float_to_time
from pytz import timezone, UTC
import requests

import logging

_logger = logging.getLogger(__name__)


class RfidServiceBaseSaleWiz(models.TransientModel):
    _name = 'rfid.service.sale.wiz'
    _description = 'Base RFID Service Sale Wizard'
    _inherit = ['rfid.service.sale.wiz']

    def share_card(self):
        if not self.email and not self.mobile:
            raise UserError(_('Please fill the e-mail or mobile in the form'))
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        act = card_id.action_share()
        act['name'] = _('Share web card %s to %s' % (sale_id.name, partner_id.name))
        act['company_dependent']= True
        act['context'] = {
            'active_id': card_id.id,
            'force_website': True,
            'partner_ids': [self.partner_id.id],
            'active_model': card_id._name,
            'default_partner_ids': partner_id.ids,
        }
        return act
