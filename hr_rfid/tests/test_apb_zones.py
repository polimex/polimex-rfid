# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_apb')
class TestZoneCreation(RFIDController, HttpCase):
    """Test zone CRUD operations."""
    _registry_readonly_enabled = False

    def test_create_zone(self):
        """Test creating a basic zone."""
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Test Zone',
            'company_id': self.test_company_id,
        })
        self.assertTrue(zone.id, 'Zone should be created')
        self.assertEqual(zone.name, 'Test Zone')

    def test_create_apb_zone(self):
        """Test creating anti-passback zone."""
        zone = self.env['hr.rfid.zone'].create({
            'name': 'APB Zone',
            'company_id': self.test_company_id,
            'anti_pass_back': True,
        })
        self.assertTrue(zone.anti_pass_back, 'Zone should have APB enabled')

    def test_zone_add_doors(self):
        """Test adding doors to a zone."""
        self._add_iCon110()
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Zone With Doors',
            'company_id': self.test_company_id,
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        self.assertEqual(len(zone.door_ids), len(self.c_110.door_ids),
                         'Zone should contain controller doors')

    def test_zone_department_filter(self):
        """Test zone with department filter."""
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Department Zone',
            'company_id': self.test_company_id,
            'permitted_department_ids': [(4, self.test_department_id.id)],
        })
        self.assertIn(self.test_department_id, zone.permitted_department_ids)

    def test_zone_tag_filter(self):
        """Test zone with employee tag filter."""
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Tag Zone',
            'company_id': self.test_company_id,
            'permitted_employee_category_ids': [(4, self.test_employee_tag1_id.id)],
        })
        self.assertIn(self.test_employee_tag1_id,
                      zone.permitted_employee_category_ids)


@tagged('standard', 'at_install', 'rfid', 'rfid_apb')
class TestAntiPassback(RFIDController, HttpCase):
    """Test anti-passback zone functionality."""
    _registry_readonly_enabled = False

    def _setup_apb_environment(self):
        """Set up controllers and access groups for APB testing."""
        self._add_iCon110()
        self._add_iCon115()
        self._add_iCon130()
        self._add_Turnstile()

        # Change modes for APB support
        self._change_mode(self.c_110, 1)
        self.assertTrue(self.c_110.mode == 1)
        self._change_mode(self.c_115, 1)
        self.assertTrue(self.c_115.mode == 1)
        self._change_mode(self.c_130, 2)
        self.assertTrue(self.c_130.mode == 2)

        # Add doors to partner AG
        add_door_wiz = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_partner_1.id]}).create([{
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        }])
        add_door_wiz.add_doors()
        add_door_wiz.unlink()
        # Clear partner card add commands (1 partner card per controller)
        self._check_cmd_add_card_and_remove(self.c_110, 1, 3)
        self._check_cmd_add_card_and_remove(self.c_115, 1, 3)
        self._check_cmd_add_card_and_remove(self.c_130, 1, 15)
        self._check_cmd_add_card_and_remove(self.c_turnstile, 1, 3)

        # Add doors to employee AG (needed for card_door_rel and APB flag updates)
        add_door_wiz2 = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_employee_1.id]}).create([{
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        }])
        add_door_wiz2.add_doors()
        add_door_wiz2.unlink()
        # Clear employee card add commands (2 employee cards per controller)
        self._check_cmd_add_card_and_remove(self.c_110, 2, 3)
        self._check_cmd_add_card_and_remove(self.c_115, 2, 3)
        self._check_cmd_add_card_and_remove(self.c_130, 2, 15)
        self._check_cmd_add_card_and_remove(self.c_turnstile, 2, 3)

    # Fixed: hr_rfid_command.py:1046 now uses from_controller context
    def test_apb_zone_creation_generates_commands(self):
        """Test that creating APB zone generates APB flag commands."""
        self._setup_apb_environment()

        test_apb_zone = self.env['hr.rfid.zone'].create({
            'name': 'Test APB Zone',
            'company_id': self.test_company_id,
            'anti_pass_back': True,
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
            ]
        })

        # Process APB mode commands
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)

        # APB flag update commands should be generated (3 cards: 2 employee + 1 partner)
        self._check_cmd_add_card_and_remove(self.c_110, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=3, rights=0, mask=96)
        self._check_cmd_add_card_and_remove(self.c_turnstile, count=3, rights=0, mask=64)

    # Fixed: hr_rfid_command.py:1046 now uses from_controller context
    def test_apb_entry_event_updates_flags(self):
        """Test APB entry event generates flag update commands."""
        self._setup_apb_environment()

        test_apb_zone = self.env['hr.rfid.zone'].create({
            'name': 'Test APB Zone',
            'company_id': self.test_company_id,
            'anti_pass_back': True,
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
            ]
        })

        # Process APB mode commands
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)

        # Clear initial APB flag commands (3 cards: 2 employee + 1 partner)
        self._check_cmd_add_card_and_remove(self.c_110, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=3, rights=0, mask=96)
        self._check_cmd_add_card_and_remove(self.c_turnstile, count=3, rights=0, mask=64)

        # Make Granted entry event on turnstile (event_code=3 → event_action='1' Granted)
        self._make_event(self.c_turnstile, reader=1, event_code=3)

        # Check APB flag update commands for other doors
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=1, rights=96, mask=96)

    # Fixed: hr_rfid_command.py:1046 now uses from_controller context
    def test_apb_zone_tracks_employees(self):
        """Test APB zone tracks employees inside."""
        self._setup_apb_environment()

        test_apb_zone = self.env['hr.rfid.zone'].create({
            'name': 'Test APB Zone',
            'company_id': self.test_company_id,
            'anti_pass_back': True,
            'door_ids': [
                (4, self.c_110.door_ids[0].id, 0),
                (4, self.c_115.door_ids[0].id, 0),
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
                (4, self.c_turnstile.door_ids[0].id, 0),
            ]
        })

        # Process APB mode commands
        response = self._hearbeat(self.test_webstack_10_3_id)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)
        response = self._send_cmd_response(response)

        # Clear initial APB flag commands (3 cards: 2 employee + 1 partner)
        self._check_cmd_add_card_and_remove(self.c_110, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=3, rights=0, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=3, rights=0, mask=96)
        self._check_cmd_add_card_and_remove(self.c_turnstile, count=3, rights=0, mask=64)

        # Make Granted entry event on turnstile (event_code=3 → event_action='1' Granted)
        self._make_event(self.c_turnstile, reader=1, event_code=3)

        # Check employee is tracked in zone
        self.assertTrue(test_apb_zone.employee_ids.ids == self.test_employee_id.ids,
                        'Employee should be tracked inside APB zone')

        # Clear remaining commands
        self._check_cmd_add_card_and_remove(self.c_110, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_115, count=1, rights=64, mask=64)
        self._check_cmd_add_card_and_remove(self.c_130, count=1, rights=96, mask=96)

        self._check_no_cmd(self.c_110)
        self._check_no_cmd(self.c_115)
        self._check_no_cmd(self.c_130)
        self._check_no_cmd(self.c_turnstile)
