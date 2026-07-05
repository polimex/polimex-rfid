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

    # --- Proactive controller provisioning from the heartbeat 'controllers' array ---

    def _ctrl(self, ctrl_id):
        return self.env['hr.rfid.ctrl'].search([
            ('ctrl_id', '=', ctrl_id),
            ('webstack_id', '=', self.test_webstack_10_3_id.id),
        ])

    def test_heartbeat_provisions_detected_controller(self):
        """A heartbeat reporting an unknown controller creates it and queues F0
        proactively — no event from the controller required."""
        new_id = self._get_id_num()
        self.assertFalse(self._ctrl(new_id), 'precondition: controller absent')
        response = self._hearbeat(self.test_webstack_10_3_id, controllers=[new_id])
        ctrl = self._ctrl(new_id)
        self.assertEqual(len(ctrl), 1, 'controller provisioned from the heartbeat')
        self.assertEqual(ctrl.name, 'Controller')
        f0 = self.env['hr.rfid.command'].search([
            ('controller_id', '=', ctrl.id), ('cmd', '=', 'F0')])
        self.assertTrue(f0, 'F0 read-info command queued proactively')
        self.assertIn('cmd', response,
                      'the queued F0 is delivered on the heartbeat response')

    def test_heartbeat_provision_is_idempotent(self):
        """Re-reporting the same controller creates no duplicate record or F0."""
        new_id = self._get_id_num()
        self._hearbeat(self.test_webstack_10_3_id, controllers=[new_id])
        ctrl = self._ctrl(new_id)
        self.assertEqual(len(ctrl), 1)
        f0_first = self.env['hr.rfid.command'].search_count([
            ('controller_id', '=', ctrl.id), ('cmd', '=', 'F0')])
        self._hearbeat(self.test_webstack_10_3_id, controllers=[new_id])
        self.assertEqual(len(self._ctrl(new_id)), 1, 'no duplicate controller')
        f0_second = self.env['hr.rfid.command'].search_count([
            ('controller_id', '=', ctrl.id), ('cmd', '=', 'F0')])
        self.assertEqual(f0_first, f0_second, 'no duplicate F0 queued')

    def test_heartbeat_provision_mixed_only_creates_new(self):
        """An array mixing a known and an unknown id creates only the unknown one."""
        existing_id = self._get_id_num()
        existing = self.env['hr.rfid.ctrl'].create({
            'name': 'Existing', 'ctrl_id': existing_id,
            'webstack_id': self.test_webstack_10_3_id.id})
        new_id = self._get_id_num()
        self._hearbeat(self.test_webstack_10_3_id, controllers=[existing_id, new_id])
        self.assertEqual(self._ctrl(existing_id), existing,
                         'known controller untouched, not recreated')
        self.assertEqual(len(self._ctrl(new_id)), 1, 'unknown controller created')

    def test_heartbeat_without_controllers_key_is_backward_compatible(self):
        """Legacy firmware (no 'controllers' key) provisions nothing; FW still set."""
        before = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        self._hearbeat(self.test_webstack_10_3_id)  # no controllers key
        after = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        self.assertEqual(before, after, 'no controllers created on a legacy heartbeat')
        self.test_webstack_10_3_id.invalidate_recordset(['version'])
        self.assertEqual(self.test_webstack_10_3_id.version, '1.3400',
                         'FW version still recorded (existing behaviour intact)')

    def test_heartbeat_provision_skips_zero_id(self):
        """Id 0 (broadcast/no-controller) is skipped; a real id alongside is created."""
        new_id = self._get_id_num()
        self._hearbeat(self.test_webstack_10_3_id, controllers=[0, new_id])
        self.assertFalse(self._ctrl(0), 'id 0 must not be provisioned')
        self.assertEqual(len(self._ctrl(new_id)), 1, 'real id provisioned')

    def test_heartbeat_malformed_controllers_is_safe(self):
        """A malformed 'controllers' value must never break the heartbeat (no 500)."""
        before = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        # int (old devFound shape) and bad elements — must be ignored, status 200.
        self._hearbeat(self.test_webstack_10_3_id, controllers=2)
        self._hearbeat(self.test_webstack_10_3_id, controllers=[None, True, 'x'])
        after = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        self.assertEqual(before, after, 'malformed payload provisions nothing, no crash')

    def test_heartbeat_provision_caps_oversized_list(self):
        """An oversized 'controllers' array (beyond the hardware bus max) is
        ignored wholesale — no mass record creation from a hostile payload."""
        before = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        oversized = list(range(1000, 1100))  # 100 ids > MAX_DETECTED_CONTROLLERS (64)
        self._hearbeat(self.test_webstack_10_3_id, controllers=oversized)
        after = self.env['hr.rfid.ctrl'].search_count([
            ('webstack_id', '=', self.test_webstack_10_3_id.id)])
        self.assertEqual(before, after, 'oversized controllers list provisions nothing')

    def test_heartbeat_provision_failure_keeps_command_delivery(self):
        """A pre-provision failure is best-effort: the heartbeat still delivers
        the webstack's queued commands (status 200, sibling not blocked) and the
        failed controller is rolled back (savepoint), not left half-created."""
        from unittest.mock import patch
        sibling = self.env['hr.rfid.ctrl'].create({
            'name': 'Sibling', 'ctrl_id': self._get_id_num(),
            'webstack_id': self.test_webstack_10_3_id.id})
        sibling.read_controller_information_cmd()  # queue the sibling's real F0
        new_id = self._get_id_num()

        def boom(records, *args, **kwargs):
            raise ValueError('simulated provisioning failure')

        with patch.object(type(self.env['hr.rfid.ctrl']),
                          'read_controller_information_cmd', boom):
            response = self._hearbeat(self.test_webstack_10_3_id, controllers=[new_id])
        self.assertIn('cmd', response,
                      'sibling queued command still delivered despite provision failure')
        self.assertFalse(self._ctrl(new_id),
                         'failed pre-provision is rolled back (savepoint), not persisted')
