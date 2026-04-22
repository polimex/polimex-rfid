# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""E2E test for firmware event 32 (SOT_DENIED) handling.

Event 32 is emitted by iCON115/iCON180 controllers (firmware v7.13+)
when an arm/disarm attempt is refused by an alarm zone. The payload
carries the card of the person who attempted arm/disarm.

Semantics match event 33 (Zone Arm/Disarm Denied): card events are
recorded as hr.rfid.event.user with event_action '15' (disarm attempted
on armed zone) or '5' (arm attempted on disarmed zone). Events without
a recognised card fall back to hr.rfid.event.system so the controller
still receives 200 and stops retrying.

The test picks the first existing iCON115 (hw_version='11') controller
with a door and reader, so it works against any database that has such
hardware — no fixed IDs, no client-specific references.
"""
import json
import logging
import unittest

from odoo.tests.common import HttpCase, tagged

_logger = logging.getLogger(__name__)

_TIMEOUT = 30


@tagged('standard', 'at_install', 'sot_denied')
class TestSotDenied(HttpCase):
    # v18+ HttpCase runs the test transaction read-only by default;
    # the endpoint under test creates records, so switch the mode off.
    readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Disable cron jobs that could race with the test POSTs.
        for xmlid in (
            'hr_rfid.hr_rfid_read_ctrl_status_cron',
            'hr_rfid.hr_rfid_sync_ctrl_clock_cron',
            'hr_rfid.hr_rfid_set_card_active_inactive_status',
        ):
            cron = cls.env.ref(xmlid, raise_if_not_found=False)
            if cron:
                cron.active = False

        # Pick any iCON115 controller that already has a door and a reader.
        Ctrl = cls.env['hr.rfid.ctrl']
        Door = cls.env['hr.rfid.door']
        Reader = cls.env['hr.rfid.reader']
        candidates = Ctrl.search([('hw_version', '=', '11')])
        cls.ctrl = False
        for c in candidates:
            if Door.search([('controller_id', '=', c.id)], limit=1) \
               and Reader.search([('controller_id', '=', c.id)], limit=1):
                cls.ctrl = c
                break
        if not cls.ctrl:
            raise unittest.SkipTest(
                'No iCON115 controller with door+reader found in DB')
        cls.webstack = cls.ctrl.webstack_id
        cls.door = Door.search(
            [('controller_id', '=', cls.ctrl.id)], limit=1)
        cls.reader = Reader.search(
            [('controller_id', '=', cls.ctrl.id)], limit=1)
        cls.app_url = '/hr/rfid/event'

        # Pick any active card on the controller's company for a known-card
        # test case. Optional — tests 02 and 03 still run if none exists.
        cls.real_card = cls.env['hr.rfid.card'].search([
            ('company_id', '=', cls.webstack.company_id.id),
            ('active', '=', True),
        ], limit=1)

    def _post_event_32(self, card_number, reader=1):
        payload = {
            'convertor': self.webstack.serial,
            'key': self.webstack.key,
            'event': {
                'id': self.ctrl.ctrl_id,
                'cmd': 'FA',
                'tos': 1,
                'bos': 1,
                'event_n': 32,
                'time': '14:30:00',
                'day': 3,
                'date': '22.04.26',
                'card': card_number,
                'reader': reader,
                'dt': '0000',
                'err': 0,
            },
        }
        return self.url_open(
            self.app_url,
            data=json.dumps(payload),
            timeout=_TIMEOUT,
            headers={'Content-Type': 'application/json'},
        )

    def _count_user_events(self, card):
        return self.env['hr.rfid.event.user'].search_count(
            [('card_id', '=', card.id), ('event_action', 'in', ['5', '15'])])

    def _count_sys_events(self):
        return self.env['hr.rfid.event.system'].search_count(
            [('controller_id', '=', self.ctrl.id), ('event_action', '=', '32')])

    def test_01_known_card_creates_user_event(self):
        """Cardholder triggers SOT_DENIED → user event with action 5 or 15."""
        if not self.real_card:
            self.skipTest('No active card on this company')
        user_before = self._count_user_events(self.real_card)
        sys_before = self._count_sys_events()

        response = self._post_event_32(card_number=self.real_card.number)
        self.assertTrue(response.ok,
                        'Event 32 must return 200, not 500, after the fix')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self._count_user_events(self.real_card), user_before + 1,
                         'Card event must create one hr.rfid.event.user record')
        self.assertEqual(self._count_sys_events(), sys_before,
                         'No system event must be created when card is known')

        ev = self.env['hr.rfid.event.user'].search(
            [('card_id', '=', self.real_card.id)], order='id desc', limit=1)
        # '15' when line was armed (→ disarm denied); '5' when disarmed
        # (→ arm denied). Both are valid depending on current zone state.
        self.assertIn(ev.event_action, ('5', '15'))
        self.assertEqual(ev.ctrl_addr, self.ctrl.ctrl_id)

    def test_02_unknown_card_falls_back_to_system_event(self):
        """Unrecognised card number → system event (not a user event)."""
        user_before = self.env['hr.rfid.event.user'].search_count([])
        sys_before = self._count_sys_events()

        response = self._post_event_32(card_number='9999999998')
        self.assertTrue(response.ok)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.env['hr.rfid.event.user'].search_count([]),
                         user_before,
                         'Unknown card must not create a user event')
        self.assertGreaterEqual(self._count_sys_events(), sys_before + 1,
                                'Unknown card must create a system event')

    def test_03_no_card_falls_back_to_system_event(self):
        """Hardware-only trigger (card=0000000000) → system event fallback."""
        sys_before = self._count_sys_events()

        response = self._post_event_32(card_number='0000000000')
        self.assertTrue(response.ok)
        self.assertEqual(response.status_code, 200)

        self.assertGreaterEqual(self._count_sys_events(), sys_before + 1,
                                'Zero card must create a system event')
