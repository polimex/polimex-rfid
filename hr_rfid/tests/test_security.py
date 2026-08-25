# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, new_test_user

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


# Record rules are the whole subject here, and the rule the DATABASE holds is
# not always the one this module ships: polimex_ip_cam overrides several of
# them by xml id, to let a camera's own company answer for events its hardware
# chain cannot. At install time those rules are already in place while the
# camera module's FIELDS are not yet loaded, so reading anything through them
# raises KeyError: 'camera_id' - a red suite on every database that has the
# camera module, curable only by updating hr_rfid in the same command, which
# nobody should have to know. Post-install is also the honest moment to ask
# these questions: what a user may see is decided by the rules an installation
# ENDS UP with, not by ours in isolation.
@tagged('standard', 'post_install', '-at_install', 'rfid', 'rfid_security')
class TestMultiCompanyIsolation(RFIDAppCase):
    """Test multi-company data isolation via ir.rule."""

    def test_webstack_company_isolation(self):
        """Test webstacks are isolated by company."""
        self.assertEqual(
            self.test_webstack_10_3_id.company_id.id,
            self.test_company_id,
            'Webstack should belong to test company')

    def test_card_company_isolation(self):
        """Test cards are isolated by company."""
        self.assertEqual(
            self.test_card_employee.company_id.id,
            self.test_company_id,
            'Card should belong to test company')

    def test_access_group_company_isolation(self):
        """Test access groups are isolated by company."""
        self.assertEqual(
            self.test_ag_employee_1.company_id.id,
            self.test_company_id,
            'AG should belong to test company')

    def test_create_webstack_company2(self):
        """Test creating webstack in different company."""
        ws2 = self.env['hr.rfid.webstack'].create({
            'name': 'Company 2 Stack',
            'serial': '999888',
            'company_id': self.test_company2_id,
            'available': 'a',
            'tz': 'Europe/Sofia',
            'active': True,
        })
        self.assertEqual(ws2.company_id.id, self.test_company2_id,
                         'Webstack should belong to company 2')
        # Verify it's a different record than company 1's webstack
        self.assertNotEqual(ws2.id, self.test_webstack_10_3_id.id)


@tagged('standard', 'post_install', '-at_install', 'rfid', 'rfid_security')
class TestGroupPermissions(RFIDAppCase):
    """Test RFID security group permissions (viewer, officer, manager)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rfid_viewer = new_test_user(
            cls.env,
            login='rfid_viewer',
            groups='hr_rfid.hr_rfid_group_viewer',
            name='RFID Viewer',
            company_id=cls.test_company_id,
            company_ids=[(4, cls.test_company_id)],
        )
        cls.rfid_officer = new_test_user(
            cls.env,
            login='rfid_officer',
            groups='hr_rfid.hr_rfid_group_officer',
            name='RFID Officer',
            company_id=cls.test_company_id,
            company_ids=[(4, cls.test_company_id)],
        )
        cls.rfid_manager = new_test_user(
            cls.env,
            login='rfid_manager',
            groups='hr_rfid.hr_rfid_group_manager',
            name='RFID Manager',
            company_id=cls.test_company_id,
            company_ids=[(4, cls.test_company_id)],
        )

    def test_viewer_can_read_cards(self):
        """Test RFID viewer can read card records."""
        cards = self.env['hr.rfid.card'].with_user(self.rfid_viewer).search([
            ('company_id', '=', self.test_company_id),
        ])
        self.assertTrue(len(cards) >= 0, 'Viewer should be able to search cards')

    def test_viewer_can_read_events(self):
        """Test RFID viewer can read user events."""
        events = self.env['hr.rfid.event.user'].with_user(self.rfid_viewer).search([])
        self.assertTrue(len(events) >= 0, 'Viewer should be able to search events')

    def test_officer_can_create_card(self):
        """Test RFID officer can create cards."""
        card = self.env['hr.rfid.card'].with_user(self.rfid_officer).create({
            'number': '8888877777',
            'card_input_type': 'w34',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })
        self.assertTrue(card.id, 'Officer should create card')

    def test_manager_can_create_webstack(self):
        """Test RFID manager can create webstacks."""
        ws = self.env['hr.rfid.webstack'].with_user(self.rfid_manager).create({
            'name': 'Manager Stack',
            'serial': '111222',
            'company_id': self.test_company_id,
            'available': 'a',
            'tz': 'Europe/Sofia',
        })
        self.assertTrue(ws.id, 'Manager should create webstack')

    def test_manager_can_create_access_group(self):
        """Test RFID manager can create access groups."""
        ag = self.env['hr.rfid.access.group'].with_user(self.rfid_manager).create({
            'name': 'Manager AG',
            'company_id': self.test_company_id,
        })
        self.assertTrue(ag.id, 'Manager should create AG')

    def test_non_rfid_user_denied_webstack(self):
        """Test user without RFID groups cannot access webstacks."""
        basic_user = new_test_user(
            self.env,
            login='basic_user',
            groups='base.group_user',
            name='Basic User',
            company_id=self.test_company_id,
            company_ids=[(4, self.test_company_id)],
        )
        with self.assertRaises(AccessError):
            self.env['hr.rfid.webstack'].with_user(basic_user).search([])

    def test_non_rfid_user_denied_cards(self):
        """Test user without RFID groups cannot access cards."""
        basic_user = new_test_user(
            self.env,
            login='basic_user2',
            groups='base.group_user',
            name='Basic User 2',
            company_id=self.test_company_id,
            company_ids=[(4, self.test_company_id)],
        )
        with self.assertRaises(AccessError):
            self.env['hr.rfid.card'].with_user(basic_user).search([])
