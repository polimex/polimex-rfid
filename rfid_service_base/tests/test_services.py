# Copyright 2022 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta, datetime, time

from freezegun import freeze_time

from odoo import fields
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, tagged
import json

import logging

from odoo.tools.safe_eval import pytz

_logger = logging.getLogger(__name__)


def _pinned_now():
    """The wall clock the whole test runs on (naive UTC).

    Mid-day - 12:30 or 13:30 in Europe/Sofia, the timezone the scaffolding
    forces - so the service window the test derives as
    [hour(now-1h):00, hour(now+1h):00] local always contains "now" and the
    sale is deterministically 'progress' at assert time, whatever the
    machine's clock and timezone. 10:30 UTC is also many hours away from any
    DST switch, which happens overnight.

    The instant is DERIVED from the real clock and never a fixed calendar
    date. The shared fixtures - the partner's card and his membership of the
    access group - are created by setUpClass at the real wall clock and carry
    "valid from" stamps of that moment. Pinning the test to a date in the
    past would put those stamps in the future: the card would not be usable
    yet, so adding the doors to the group would grant the partner nothing and
    the controller would receive no command at all. Tomorrow is always after
    the fixtures, so the partner starts the scenario holding a card that
    works and a membership that is already running.
    """
    return (fields.Datetime.now() + timedelta(days=1)).replace(
        hour=10, minute=30, second=0, microsecond=0
    )


@tagged('rfid_service')
class RFIDServices(RFIDController, HttpCase):
    def setUp(self):
        # Freeze BEFORE super(): RFIDController.setUp() computes the simulated
        # device clock (test_date_10_3 / test_time_10_3) from
        # fields.Datetime.now(), so freezing first keeps the device events and
        # the ORM clock on the same instant. All model-side comparisons
        # (rfid.service.sale._compute_state, the access-group rel state and
        # the wizard's start/end calculation) use fields.Datetime.now() /
        # datetime.now(), which freezegun pins process-wide, including the
        # HttpCase server thread that handles /hr/rfid/event.
        freezer = freeze_time(_pinned_now())
        freezer.start()
        self.addCleanup(freezer.stop)
        super().setUp()

    def test_rfid_services(self):
        now = fields.Datetime.context_timestamp(
            self.test_webstack_10_3_id, fields.Datetime.now()
        )
        start = (now - timedelta(hours=1)).hour
        start_check = pytz.timezone(self.env.user.tz).localize(datetime.combine(now.date(), time(start, 0))).astimezone(
            pytz.UTC).replace(tzinfo=None)
        end = (now + timedelta(hours=1)).hour
        end_check = pytz.timezone(self.env.user.tz).localize(datetime.combine(now.date(), time(end, 0))).astimezone(
            pytz.UTC).replace(tzinfo=None)
        service_id = self.env['rfid.service'].create({
            'name': 'Test Half Day',
            'company_id': self.test_company_id,
            'service_type': 'time_count',
            'visits': '1',
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
        self.test_partner_ag_rel.activate_on = fields.Datetime.now() - timedelta(weeks=2)
        self.test_partner_ag_rel.expiration = fields.Datetime.now() - timedelta(weeks=1)
        self.c_110.door_ids.card_type = service_id.card_type
        self._clear_ctrl_cmd(self.c_110)

        # sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(default_service_id=service_id.id).create({
        #     'card_number': card_number,
        #     'partner_id': self.test_partner.id
        # })
        sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service_id.id,
            default_card_number=card_number,
            default_partner_id=self.test_partner.id
        ).create({})
        self.assertNotEqual(sale_wiz_id.start_date, False, 'Start Date must be set')
        self.assertNotEqual(sale_wiz_id.end_date, False, 'End Date must be set')
        sale_wiz_id.write_card()

        sales_ids = self.env['rfid.service.sale'].search([('service_id.company_id', '=', self.test_company_id)])
        self.assertEqual(len(sales_ids), 1)
        self.assertEqual(len(self.test_partner.hr_rfid_access_group_ids), 2)
        self.assertEqual(len(self.test_partner.hr_rfid_access_group_ids.filtered(lambda agr: agr.state)), 1)
        self.assertEqual(sales_ids.start_date, start_check)
        self.assertEqual(sales_ids.end_date, end_check)
        self.assertEqual(sales_ids.state, 'progress')
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=3)

        response = self._make_event(self.c_110, card_number, reader=1, event_code=3)
        self.assertEqual(len(self.test_partner.hr_rfid_access_group_ids.filtered(lambda agr: agr.state)), 0,
                         'Only one visit permitted')
        # The consumed last visit revokes the card on the controller: the
        # event response carries the D1 revoke command. Acknowledge it like
        # the real device would, so it does not linger in the command queue
        # (commands created in the HTTP request's own transaction sort newer
        # than anything from the test transaction and would otherwise shadow
        # the next sale's add-card command in _check_cmd_add_card).
        self.assertEqual(response['cmd']['c'], 'D1', 'Expecting card revoke command after the last visit')
        self.assertEqual(self._send_cmd_response(response), {}, 'Queue must be empty after the revoke ack')

        service_id.generate_barcode_card = True
        hex_num, num = self.env['hr.rfid.card'].create_bc_card()
        # sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(active_id=service_id.id).create({})
        sale_wiz_id = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service_id.id,
            default_card_number=num,
        ).create({})
        self.assertNotEqual(sale_wiz_id.start_date, False, 'Start Date must be set')
        self.assertNotEqual(sale_wiz_id.end_date, False, 'End Date must be set')
        sale_wiz_id.write_card()
        self.assertEqual(sale_wiz_id.card_number, num, 'Same number as provided')
        self.assertEqual(len(sale_wiz_id.partner_id.hr_rfid_access_group_ids.filtered(lambda agr: agr.state)), 1)

        sales_ids = self.env['rfid.service.sale'].search([('service_id.company_id', '=', self.test_company_id)])
        self.assertEqual(len(sales_ids), 2)
        self.assertEqual(sales_ids[-1].state, 'progress')
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=3)

        response = self._make_event(self.c_110, num, reader=1, event_code=3)
        self.assertEqual(len(sale_wiz_id.partner_id.hr_rfid_access_group_ids.filtered(lambda agr: agr.state)), 0)
        # Same revoke-and-ack cycle for the barcode card's single visit.
        self.assertEqual(response['cmd']['c'], 'D1', 'Expecting card revoke command after the last visit')
        self.assertEqual(self._send_cmd_response(response), {}, 'Queue must be empty after the revoke ack')

    def _add_service(self):
        pass
