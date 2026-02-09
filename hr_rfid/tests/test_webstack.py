# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_webstack')
class TestWebstackCRUD(RFIDAppCase):
    """Test webstack CRUD operations."""

    def test_webstack_create(self):
        """Test creating a webstack."""
        self.assertTrue(self.test_webstack_10_3_id.id,
                        'Webstack should be created')

    def test_webstack_serial(self):
        """Test webstack serial number."""
        self.assertEqual(self.test_webstack_10_3_id.serial, '234567',
                         'Webstack serial should be 234567')

    def test_webstack_available(self):
        """Test webstack availability status."""
        self.assertEqual(self.test_webstack_10_3_id.available, 'a',
                         'Webstack should be available')

    def test_webstack_timezone(self):
        """Test webstack timezone setting."""
        self.assertEqual(self.test_webstack_10_3_id.tz, 'Europe/Sofia',
                         'Webstack timezone should be Europe/Sofia')

    def test_webstack_company(self):
        """Test webstack company assignment."""
        self.assertEqual(self.test_webstack_10_3_id.company_id.id,
                         self.test_company_id,
                         'Webstack should belong to test company')

    def test_webstack_key_generated(self):
        """Test webstack key is generated on creation."""
        self.assertTrue(self.test_webstack_10_3_id.key,
                        'Webstack should have a key')

    def test_create_second_webstack(self):
        """Test creating a second webstack with different serial."""
        ws2 = self.env['hr.rfid.webstack'].create({
            'name': 'Second Stack',
            'serial': '654321',
            'company_id': self.test_company_id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        self.assertNotEqual(ws2.serial, self.test_webstack_10_3_id.serial,
                            'Second webstack should have different serial')


@tagged('standard', 'at_install', 'rfid', 'rfid_webstack')
class TestWebstackHeartbeat(RFIDAppCase, HttpCase):
    """Test webstack heartbeat communication."""
    _registry_readonly_enabled = False

    def test_heartbeat_empty_response(self):
        """Test heartbeat with no pending commands returns empty."""
        response = self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(response, {},
                         'Heartbeat with no commands should return empty')

    def test_heartbeat_increments(self):
        """Test heartbeat counter increments properly."""
        initial = self.heartbeat
        self._hearbeat(self.test_webstack_10_3_id)
        self.assertEqual(self.heartbeat, initial + 1,
                         'Heartbeat counter should increment')
