# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
import logging
import queue

from polimex.hr_rfid.models.hr_rfid_event_user import HrRfidUserEvent

_logger = logging.getLogger(__name__)


class HrRfidAccessGroupRelations(models.AbstractModel):
    _name = 'hr.rfid.access.group.rel'
    _description = 'Relation between access groups and employees'

    rfid_service_sale_id = fields.Many2one(
        comodel_name='rfid.service.sale'
    )

    def process_event_data(self, user_event_id: HrRfidUserEvent):
        super().process_event_data(user_event_id)
        if self.rfid_service_sale_id:
            self.rfid_service_sale_id.process_event_data(user_event_id)
