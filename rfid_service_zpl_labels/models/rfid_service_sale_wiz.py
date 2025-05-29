import pytz
from dateutil.relativedelta import relativedelta

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

    def print_label(self):
        """Print ZPL wristband label and close wizard"""
        # First write the card to create the sale record
        sale_id, partner_id, access_group_contact_rel, card_id = self._write_card()
        
        # Get the report action
        report_action = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband').report_action(sale_id)
        
        # Update the action to close the wizard after download
        report_action.update({'close_on_report_download': True})
        
        return report_action

