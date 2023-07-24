# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta, datetime, time

from odoo import fields
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, tagged
import json

import logging

from odoo.tools.safe_eval import pytz

_logger = logging.getLogger(__name__)


@tagged('rfid_service')
class RFIDServices(RFIDController, HttpCase):
    def test_rfid_services(self):
        now = fields.Datetime.context_timestamp(
            self.test_webstack_10_3_id, fields.Datetime.now()
        )
        start = (now - timedelta(hours=1)).hour
        start_check = pytz.timezone(self.env.user.tz).localize(datetime.combine(now.date(), time(start, 0))).astimezone(pytz.UTC).replace(tzinfo=None)
        end = (now + timedelta(hours=1)).hour
        end_check = pytz.timezone(self.env.user.tz).localize(datetime.combine(now.date(), time(end, 0))).astimezone(pytz.UTC).replace(tzinfo=None)
        service_id = self.env['rfid.service'].create({
            'name': 'Test Half Day',
            'company_id': self.test_company_id,
            'service_type': 'time',
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
            'time_interval_number': 4,
            'time_interval_type': 'hours',
            'time_interval_start': start,
            'time_interval_end': end,
            'access_group_id': self.test_ag_partner_1.id
        })
        card_number = '1212233445'
        self._add_iCon110()
        self.test_ag_partner_1.add_doors(self.c_110.door_ids)
        self.c_110.door_ids.card_type = service_id.card_type
        self._clear_ctrl_cmd(self.c_110)

        sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(active_id=service_id.id).create({
            'card_number': card_number,
            'partner_id': self.test_partner.id
        })
        sale_wiz_id.write_card()

        sales_ids = self.env['rfid.service.sale'].search([('service_id.company_id', '=', self.test_company_id)])
        self.assertEqual(len(sales_ids), 1)
        self.assertEqual(sales_ids.start_date, start_check)
        self.assertEqual(sales_ids.end_date, end_check)
        self.assertEqual(sales_ids.state, 'progress')
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=3)

        self._make_event(self.c_110, card_number, reader=1, event_code=3)

        service_id.generate_barcode_card = True
        sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(active_id=service_id.id).create({})
        card_number = sale_wiz_id.card_number
        sale_wiz_id.write_card()
        sales_ids = self.env['rfid.service.sale'].search([('service_id.company_id', '=', self.test_company_id)])
        self.assertEqual(len(sales_ids), 2)
        self.assertEqual(sales_ids[-1].state, 'progress')
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=3)

        self._make_event(self.c_110, card_number, reader=1, event_code=3)
        pass

    def _add_service(self):
        pass
