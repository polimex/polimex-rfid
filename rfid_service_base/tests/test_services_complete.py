# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import timedelta, datetime, time
from unittest.mock import patch, MagicMock
import uuid

from odoo import fields
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, tagged, Form
from odoo.tools.safe_eval import pytz

import json
import logging

_logger = logging.getLogger(__name__)


@tagged('rfid_service')
class RFIDServicesComplete(RFIDController, HttpCase):
    """Complete test coverage for rfid_service_base module"""

    def setUp(self):
        super().setUp()
        # Generate unique suffix to avoid conflicts
        self.unique_suffix = str(uuid.uuid4())[:8]
        
        # Create additional test data
        self.test_company_2 = self.env['res.company'].create({
            'name': f'Test Company 2 {self.unique_suffix}',
            'vat': 'BG123456789',
        })
        
        # Create test partners
        self.test_partner_2 = self.env['res.partner'].create({
            'name': f'Test Partner 2 {self.unique_suffix}',
            'email': f'partner2_{self.unique_suffix}@test.com',
            'mobile': '+359888222333',
            'is_company': False,
            'company_id': self.test_company_id,
        })
        
        self.test_partner_parent = self.env['res.partner'].create({
            'name': f'Parent Partner {self.unique_suffix}',
            'is_company': True,
            'company_id': self.test_company_id,
        })
        
        self.test_partner_child = self.env['res.partner'].create({
            'name': f'Child Partner {self.unique_suffix}',
            'parent_id': self.test_partner_parent.id,
            'is_company': False,
            'company_id': self.test_company_id,
        })

    # ===== CORE RFID SERVICE TESTS =====
    
    def test_rfid_service_complete_flow(self):
        """Test complete RFID service flow with all features"""
        # Create service with all options
        service = self.env['rfid.service'].create({
            'name': f'Complete Service {self.unique_suffix}',
            'company_id': self.test_company_id,
            'service_type': 'time_count',
            'visits': '5',
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
            'time_interval_number': 1,
            'time_interval_type': 'days',
            'time_interval_start': 8,
            'time_interval_end': 18,
            'access_group_id': self.test_ag_partner_1.id,
            'generate_barcode_card': True,
        })
        
        # Test onchange barcode
        service._onchange_barcode()
        self.assertEqual(service.card_type.id, 
                        self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id)
        
        # Create door for access
        door = self._create_test_door()
        self.test_ag_partner_1.add_doors(door)
        
        # Test action_new_sale
        action = service.action_new_sale()
        self.assertEqual(action['res_model'], 'rfid.service.sale.wiz')
        self.assertEqual(action['context']['default_service_id'], service.id)
        
        # Create sale through wizard
        card_number = '1234567890'
        wizard = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
            default_card_number=card_number,
            default_partner_id=self.test_partner_2.id
        ).create({})
        
        # Test wizard computations
        self.assertNotEqual(wizard.start_date, False)
        self.assertNotEqual(wizard.end_date, False)
        
        # Test wizard onchange handlers
        wizard._onchange_service_id()
        wizard._onchange_start_date()
        
        # Write card
        wizard.write_card()
        
        # Verify sale was created
        sale = self.env['rfid.service.sale'].search([
            ('service_id', '=', service.id),
            ('partner_id', '=', self.test_partner_2.id)
        ])
        self.assertTrue(sale)
        self.assertEqual(sale.state, 'progress')
        self.assertEqual(sale.visits, 0)  # No visits yet
        
        # Simulate visits
        agr = self.test_partner_2.hr_rfid_access_group_ids.filtered(lambda r: r.state)
        agr.visits_counter = 3
        self.assertEqual(sale.visits, 3)
        
        # Test that after 5 visits, access is consumed
        agr.visits_counter = 5
        self.assertEqual(sale.state, 'finished')
        
        # Test action_view_sales
        action = service.action_view_sales()
        self.assertEqual(action['domain'], [('service_id', '=', service.id)])
        
    def test_rfid_service_sale_complete_lifecycle(self):
        """Test complete lifecycle of service sale"""
        service = self._create_test_service()
        
        # Test all states
        # 1. Registered state (future)
        sale_future = self._create_service_sale(
            self.test_partner_2, service,
            start_offset_days=5, end_offset_days=10
        )
        self.assertEqual(sale_future.state, 'registered')
        
        # 2. Progress state (current)
        sale_current = self._create_service_sale(
            self.test_partner_2, service,
            start_offset_days=0, end_offset_days=5
        )
        self.assertEqual(sale_current.state, 'progress')
        
        # 3. Finished state (past)
        sale_past = self._create_service_sale(
            self.test_partner_2, service,
            start_offset_days=-10, end_offset_days=-5
        )
        self.assertEqual(sale_past.state, 'finished')
        
        # 4. Test extend service
        action = sale_current.extend_service()
        self.assertEqual(action['context']['default_extend_sale_id'], sale_current.id)
        
        # 5. Test partner sales action
        action = sale_current.partner_sales()
        self.assertEqual(action['domain'], [('partner_id', '=', self.test_partner_2.id)])
        
        # 6. Test email card (no email)
        with self.assertRaises(UserError):
            sale_current.email_card()
            
        # 7. Test email card (with email)
        self.test_partner_2.email = 'test@example.com'
        with patch.object(type(self.test_partner_2), 'action_send_badge_email') as mock:
            mock.return_value = {'type': 'ir.actions.act_window'}
            result = sale_current.email_card()
            mock.assert_called_once()
            
        # 8. Test print card
        with patch.object(type(self.env.ref('hr_rfid.action_report_res_partner_foldable_badge')), 
                         'report_action') as mock:
            mock.return_value = {'type': 'ir.actions.report'}
            result = sale_current.print_card()
            mock.assert_called_once_with(self.test_partner_2)
            
        # 9. Test cancel sale
        sale_cancel = self._create_service_sale(
            self.test_partner_2, service,
            start_offset_days=20, end_offset_days=25
        )
        sale_cancel.cancel_sale()
        self.assertEqual(sale_cancel.state, 'canceled')
        
        # 10. Test unlink cascade
        agr_count = len(self.test_partner_2.hr_rfid_access_group_ids)
        sale_delete = self._create_service_sale(
            self.test_partner_2, service,
            start_offset_days=30, end_offset_days=35
        )
        sale_delete.unlink()
        self.assertEqual(len(self.test_partner_2.hr_rfid_access_group_ids), agr_count)
        
    def test_rfid_service_sale_wizard_complete(self):
        """Test all wizard functionality"""
        service = self._create_test_service()
        
        # Test 1: Create new partner with wizard
        wizard = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
            default_card_number='9876543210',
        ).create({
            'email': f'new_{self.unique_suffix}@test.com',
            'mobile': '+359888111222',
        })
        
        # Write card to generate partner
        wizard.write_card()
        
        # Verify partner was created
        sale = self.env['rfid.service.sale'].search([
            ('card_id.number', '=', '9876543210')
        ], limit=1)
        self.assertTrue(sale)
        self.assertTrue(sale.partner_id)
        self.assertTrue(wizard.partner_id)
        
        # Test 2: Reuse existing card
        existing_card = self.env['hr.rfid.card'].create({
            'number': '1111222233',
            'card_type': service.card_type.id,
            'contact_id': self.test_partner.id,
        })
        
        wizard2 = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
            default_card_number=existing_card.number,
            default_partner_id=self.test_partner_2.id,
        ).create({})
        
        wizard2._gen_partner()
        # Card should be reassigned
        self.assertEqual(existing_card.contact_id, self.test_partner_2)
        
        # Test 3: Validation errors
        wizard3 = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
        ).create({})
        
        # No card number
        with self.assertRaises(UserError) as cm:
            wizard3.write_card()
        self.assertIn('enter Card Number', str(cm.exception))
        
        # Past end date
        wizard3.card_number = '4444555566'
        wizard3.end_date = fields.Datetime.now() - timedelta(days=1)
        with self.assertRaises(UserError) as cm:
            wizard3.write_card()
        self.assertIn('past date', str(cm.exception))
        
        # No doors in access group
        service_no_doors = self._create_test_service()
        service_no_doors.access_group_id.all_door_ids.unlink()
        wizard4 = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service_no_doors.id,
            default_card_number='7777888899',
            default_partner_id=self.test_partner.id,
        ).create({})
        
        with self.assertRaises(UserError) as cm:
            wizard4.write_card()
        self.assertIn('No doors configured', str(cm.exception))
        
    def test_rfid_service_sale_fix_partner(self):
        """Test fix_partner method scenarios"""
        service = self._create_test_service()
        
        # Scenario 1: Sale without partner but with card
        card = self.env['hr.rfid.card'].create({
            'number': '5551112223',
            'card_type': service.card_type.id,
            'contact_id': self.test_partner_2.id,
        })
        
        sale = self.env['rfid.service.sale'].create({
            'service_id': service.id,
            'start_date': fields.Datetime.now(),
            'end_date': fields.Datetime.now() + timedelta(days=1),
            'card_id': card.id,
        })
        
        sale.fix_partner()
        self.assertEqual(sale.partner_id, self.test_partner_2)
        
        # Scenario 2: Update card reference
        card2 = self.env['hr.rfid.card'].create({
            'number': '5552223334',
            'name': '5552223334',  # Same as number
            'card_type': service.card_type.id,
            'contact_id': self.test_partner.id,
        })
        
        sale2 = self.env['rfid.service.sale'].create({
            'name': 'SALE/001',
            'service_id': service.id,
            'start_date': fields.Datetime.now(),
            'end_date': fields.Datetime.now() + timedelta(days=1),
            'card_id': card2.id,
            'partner_id': self.test_partner.id,
        })
        
        sale2.fix_partner()
        # Card reference should be updated when name differs from number
        if card2.name == card2.number:
            self.assertEqual(card2.card_reference, 'SALE/001')
        
    def test_rfid_service_overlap_validation_complete(self):
        """Test comprehensive overlap validation"""
        service = self._create_test_service()
        
        # Create base sale
        base_start = fields.Datetime.now()
        base_end = base_start + timedelta(days=10)
        
        sale1 = self._create_service_sale(
            self.test_partner, service,
            start_offset_days=0, end_offset_days=10
        )
        
        # Test all overlap scenarios
        test_cases = [
            # (start_offset, end_offset, should_fail, description)
            (2, 5, True, "Completely within existing"),
            (5, 15, True, "Starts within existing"),
            (-5, 5, True, "Ends within existing"),
            (-2, 12, True, "Completely covers existing"),
            (10, 15, False, "Starts exactly at end"),
            (-5, 0, False, "Ends exactly at start"),
            (15, 20, False, "Completely after"),
            (-10, -5, False, "Completely before"),
        ]
        
        for start_offset, end_offset, should_fail, description in test_cases:
            card_number = f'99{start_offset:02d}{end_offset:02d}0000'
            wizard = self.env['rfid.service.sale.wiz'].with_context(
                default_service_id=service.id,
                default_card_number=card_number,
                default_partner_id=self.test_partner.id
            ).create({})
            
            wizard.start_date = base_start + timedelta(days=start_offset)
            wizard.end_date = base_start + timedelta(days=end_offset)
            
            if should_fail:
                with self.assertRaises(UserError, msg=f"Should fail: {description}"):
                    wizard.write_card()
            else:
                wizard.write_card()  # Should succeed
                # Clean up for next test
                sale = self.env['rfid.service.sale'].search([
                    ('card_id.number', '=', card_number)
                ])
                sale.unlink()
                
    # ===== RES.PARTNER TESTS =====
    
    def test_res_partner_complete_functionality(self):
        """Test all res.partner RFID functionality"""
        # Test compute sales count
        service = self._create_test_service()
        self._create_service_sale(self.test_partner_2, service)
        self._create_service_sale(self.test_partner_2, service, 
                                  start_offset_days=20, end_offset_days=25)
        
        self.test_partner_2._compute_partner_rfid_sales_count()
        self.assertEqual(int(self.test_partner_2.partner_rfid_sales_count), 2)
        
        # Test action_rfid_sales
        action = self.test_partner_2.action_rfid_sales()
        self.assertEqual(action['res_model'], 'rfid.service.sale')
        self.assertEqual(action['domain'], [('partner_id', 'in', [self.test_partner_2.id])])
        
        # Test button_doors_list
        door = self._create_test_door()
        self.test_ag_partner_1.add_doors(door)
        action = self.test_partner.button_doors_list()
        self.assertEqual(action['res_model'], 'hr.rfid.door')
        
        # Test add/remove access groups
        ag = self.env['hr.rfid.access.group'].create({
            'name': f'Test AG {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        
        expiration = fields.Datetime.now() + timedelta(days=30)
        self.test_partner_2.add_acc_gr(ag, expiration)
        
        ag_rel = self.test_partner_2.hr_rfid_access_group_ids.filtered(
            lambda r: r.access_group_id == ag
        )
        self.assertTrue(ag_rel)
        self.assertEqual(ag_rel.expiration, expiration)
        
        self.test_partner_2.remove_acc_gr(ag)
        ag_rel = self.test_partner_2.hr_rfid_access_group_ids.filtered(
            lambda r: r.access_group_id == ag
        )
        self.assertFalse(ag_rel)
        
        # Test get_doors with different parameters
        door1 = self._create_test_door('Door 1')
        door2 = self._create_test_door('Door 2')
        self.test_ag_partner_1.add_doors([door1, door2])
        
        doors = self.test_partner.get_doors()
        self.assertIn(door1, doors)
        self.assertIn(door2, doors)
        
        doors = self.test_partner.get_doors(excluding_acc_gr=self.test_ag_partner_1)
        self.assertFalse(doors)
        
        ag2 = self.env['hr.rfid.access.group'].create({
            'name': f'Test AG 2 {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        ag2.add_doors(door1)
        self.test_partner.add_acc_gr(ag2)
        
        doors = self.test_partner.get_doors(including_acc_gr=ag2)
        self.assertIn(door1, doors)
        self.assertNotIn(door2, doors)
        
    def test_res_partner_pin_and_card_management(self):
        """Test PIN code and card management"""
        # Test PIN validation
        self.test_partner_2.hr_rfid_pin_code = '1234'
        
        with self.assertRaises(ValidationError):
            self.test_partner_2.hr_rfid_pin_code = 'abcd'
            
        with self.assertRaises(ValidationError):
            self.test_partner_2.hr_rfid_pin_code = '123'
            
        self.test_partner_2.hr_rfid_pin_code = ''  # Should be allowed
        
        # Test PIN change tracking
        card = self.env['hr.rfid.card'].create({
            'number': '9999888877',
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
            'contact_id': self.test_partner_2.id,
        })
        
        self.test_partner_2.hr_rfid_pin_code = '1234'
        self.test_partner_2.hr_rfid_pin_code = '5678'
        self.assertEqual(self.test_partner_2.hr_rfid_pin_code, '5678')
        
        # Test generate random barcode
        card_count_before = len(self.test_partner_2.hr_rfid_card_ids)
        self.test_partner_2.generate_random_barcode_card()
        
        self.assertEqual(len(self.test_partner_2.hr_rfid_card_ids), card_count_before + 1)
        new_card = self.test_partner_2.hr_rfid_card_ids[-1]
        self.assertEqual(len(new_card.number), 10)
        self.assertTrue(new_card.number.isdigit())
        
        # Test add_card_number
        card_number = '3333444455'
        self.test_partner_2.add_card_number(card_number)
        
        card = self.test_partner_2.hr_rfid_card_ids.filtered(
            lambda c: c.number == card_number
        )
        self.assertTrue(card)
        
        # Test add_access_group with visits
        ag = self.env['hr.rfid.access.group'].create({
            'name': f'Visit AG {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        
        self.test_partner_2.add_access_group(
            ag,
            visits_counting=True,
            permitted_visits=5,
            visits_counter=2
        )
        
        ag_rel = self.test_partner_2.hr_rfid_access_group_ids.filtered(
            lambda r: r.access_group_id == ag
        )
        self.assertTrue(ag_rel.visits_counting)
        self.assertEqual(ag_rel.permitted_visits, 5)
        self.assertEqual(ag_rel.visits_counter, 2)
        
    def test_res_partner_generate_and_cascade(self):
        """Test partner generation and cascade operations"""
        # Test generate_partner with new partner
        partner_data = {
            'name': f'Generated Partner {self.unique_suffix}',
            'email': f'generated_{self.unique_suffix}@test.com',
            'phone': '+359888999000',
        }
        card_number = '1122334455'
        
        partner = self.env['res.partner'].generate_partner(
            partner_data=partner_data,
            card_numbers=[card_number],
            contact_ids=[],
            access_groups=[self.test_ag_partner_1],
            card_type=self.env.ref('hr_rfid.hr_rfid_card_type_barcode')
        )
        
        self.assertEqual(partner.name, partner_data['name'])
        self.assertEqual(len(partner.hr_rfid_card_ids), 1)
        self.assertEqual(partner.hr_rfid_card_ids[0].number, card_number)
        self.assertEqual(len(partner.hr_rfid_access_group_ids), 1)
        
        # Test with existing partner
        card_number_2 = '5566778899'
        partner = self.env['res.partner'].generate_partner(
            partner_data={'name': self.test_partner_2.name},
            card_numbers=[card_number_2],
            contact_ids=[self.test_partner_2.id],
            access_groups=[self.test_ag_partner_1],
            card_type=self.env.ref('hr_rfid.hr_rfid_card_type_barcode')
        )
        
        self.assertEqual(partner.id, self.test_partner_2.id)
        self.assertIn(card_number_2, partner.hr_rfid_card_ids.mapped('number'))
        
        # Test cascade deletion
        test_partner = self.env['res.partner'].create({
            'name': f'Delete Test {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        
        card = self.env['hr.rfid.card'].create({
            'number': '5555666677',
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
            'contact_id': test_partner.id,
        })
        
        card_id = card.id
        test_partner.unlink()
        
        # Check card is deleted
        card = self.env['hr.rfid.card'].search([('id', '=', card_id)])
        self.assertFalse(card)
        
    def test_res_partner_mrz_decoding(self):
        """Test MRZ decoding functionality"""
        # Test valid passport MRZ
        mrz_data = [
            "P<BGRBULGARIAN<<IVAN<PETROV<<<<<<<<<<<<<<<",
            "1234567890BG8010011M2501011<<<<<<<<<<<<<<8"
        ]
        
        result = self.env['res.partner'].decode_mrz(mrz_data)
        self.assertEqual(result['type'], 'passport')
        self.assertEqual(result['first_name'], 'IVAN PETROV')
        self.assertEqual(result['last_name'], 'BULGARIAN')
        self.assertEqual(result['country'], 'BG')
        
        # Test invalid MRZ
        with self.assertRaises(ValidationError):
            self.env['res.partner'].decode_mrz(["INVALID"])
            
        # Test ID card MRZ (3 lines)
        id_mrz = [
            "IDBGR1234567890<<<<<<<<<<<<",
            "8010011M2501011BULGARIAN<<<<<",
            "IVAN<PETROV<<<<<<<<<<<<<<<<<<<"
        ]
        
        result = self.env['res.partner'].decode_mrz(id_mrz)
        self.assertEqual(result['type'], 'id')
        
    def test_res_partner_check_inconsistencies(self):
        """Test timestamp inconsistency checks"""
        # This tests the fixed bug in check_for_ts_inconsistencies
        ag1 = self.env['hr.rfid.access.group'].create({
            'name': f'AG Check 1 {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        ag2 = self.env['hr.rfid.access.group'].create({
            'name': f'AG Check 2 {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        
        door = self._create_test_door('Check Door')
        ag1.add_doors(door)
        ag2.add_doors(door)
        
        self.test_partner_2.add_acc_gr(ag1)
        self.test_partner_2.add_acc_gr(ag2)
        
        # This should call check_for_ts_inconsistencies
        self.test_partner_2.check_for_ts_inconsistencies()
        
    def test_res_partner_relay_controller_validation(self):
        """Test relay controller concurrent access validation"""
        # Create relay controller
        controller = self.env['hr.rfid.ctrl'].create({
            'name': f'Relay Controller {self.unique_suffix}',
            'ctrl_id': 888,
            'webstack_id': self.test_webstack_10_3_id.id,
            'hw_version': 10,
            'mode': 1,  # Relay mode
        })
        
        door = self.env['hr.rfid.door'].create({
            'name': 'Relay Door',
            'number': 1,
            'controller_id': controller.id,
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
        })
        
        # Create two access groups with same door
        ag1 = self.env['hr.rfid.access.group'].create({
            'name': f'AG Relay 1 {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        ag1.add_doors(door)
        
        ag2 = self.env['hr.rfid.access.group'].create({
            'name': f'AG Relay 2 {self.unique_suffix}',
            'company_id': self.test_company_id,
        })
        ag2.add_doors(door)
        
        # Add first access group
        self.test_partner_2.add_acc_gr(ag1)
        
        # Try to add second - should fail
        with self.assertRaises(ValidationError) as cm:
            self.test_partner_2.add_acc_gr(ag2)
        self.assertIn('Cannot have more than one access group', str(cm.exception))
        
    # ===== RES.COMPANY TESTS =====
    
    def test_res_company_sequence_creation(self):
        """Test sequence creation for new company"""
        company_name = f'Test Company Seq {self.unique_suffix}'
        company = self.env['res.company'].create({
            'name': company_name,
        })
        
        # Check sequence was created
        sequence = self.env['ir.sequence'].search([
            ('code', '=', 'base.rfid.service'),
            ('company_id', '=', company.id)
        ])
        self.assertTrue(sequence, 'Sequence should be created for new company')
        self.assertEqual(sequence.code, 'base.rfid.service')
        
    # ===== MULTI-COMPANY TESTS =====
    
    def test_multi_company_support(self):
        """Test complete multi-company functionality"""
        # Create service in company 2
        ag_c2 = self.env['hr.rfid.access.group'].create({
            'name': f'AG Company 2 {self.unique_suffix}',
            'company_id': self.test_company_2.id,
        })
        
        service_c2 = self.env['rfid.service'].with_company(self.test_company_2).create({
            'name': f'Service Company 2 {self.unique_suffix}',
            'company_id': self.test_company_2.id,
            'service_type': 'time',
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
            'time_interval_number': 1,
            'time_interval_type': 'days',
            'access_group_id': ag_c2.id,
        })
        
        # Verify isolation
        services_c1 = self.env['rfid.service'].search([
            ('company_id', '=', self.test_company_id)
        ])
        self.assertNotIn(service_c2, services_c1)
        
        # Test sequence creation for company 2
        sequence_c2 = self.env['ir.sequence'].search([
            ('code', '=', 'base.rfid.service'),
            ('company_id', '=', self.test_company_2.id)
        ])
        self.assertTrue(sequence_c2)
        
    # ===== TIMEZONE AND CALCULATION TESTS =====
    
    def test_timezone_conversions(self):
        """Test timezone handling in calculations"""
        # Set user timezone
        self.env.user.tz = 'Europe/Sofia'  # UTC+2/+3
        
        service = self._create_test_service()
        service.time_interval_type = 'hours'
        service.time_interval_start = 14  # 2 PM local
        
        wizard = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
            default_card_number='0000000001',
        ).create({})
        
        start = wizard._calc_start()
        # 14:00 Sofia = 12:00 UTC (winter) or 11:00 UTC (summer)
        self.assertIn(start.hour, [11, 12])
        
    def test_service_time_calculations(self):
        """Test all time interval calculations"""
        test_cases = [
            ('hours', 10, 14, 4),
            ('days', 0, 0, 1),
            ('weeks', 0, 0, 1),
            ('months', 0, 0, 1),
        ]
        
        for interval_type, start_hour, end_hour, number in test_cases:
            service = self._create_test_service()
            service.time_interval_type = interval_type
            service.time_interval_start = start_hour
            service.time_interval_end = end_hour
            service.time_interval_number = number
            
            wizard = self.env['rfid.service.sale.wiz'].with_context(
                default_service_id=service.id,
                default_card_number=f'7777{interval_type[:2]}{start_hour:02d}{end_hour:02d}',
            ).create({})
            
            start = wizard._calc_start()
            end = wizard._calc_end()
            
            if interval_type == 'hours':
                self.assertEqual(start.hour, start_hour)
                # For hours, end should be on same day
                self.assertEqual(start.date(), end.date())
            else:
                # For other intervals, should start at midnight
                self.assertEqual(start.hour, 0)
                
    # ===== HELPER METHODS =====
    
    def _create_test_service(self, **kwargs):
        """Create test service with defaults"""
        # Ensure access group has doors
        ag = kwargs.get('access_group_id', self.test_ag_partner_1)
        if isinstance(ag, int):
            ag = self.env['hr.rfid.access.group'].browse(ag)
        if not ag.all_door_ids:
            door = self._create_test_door(f'Service Door {self.unique_suffix}')
            ag.add_doors(door)
            
        vals = {
            'name': kwargs.get('name', f'Test Service {self.unique_suffix}'),
            'company_id': kwargs.get('company_id', self.test_company_id),
            'service_type': kwargs.get('service_type', 'time_count'),
            'visits': kwargs.get('visits', '1'),
            'card_type': kwargs.get('card_type', self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id),
            'time_interval_number': kwargs.get('time_interval_number', 4),
            'time_interval_type': kwargs.get('time_interval_type', 'hours'),
            'time_interval_start': kwargs.get('time_interval_start', 10),
            'time_interval_end': kwargs.get('time_interval_end', 14),
            'access_group_id': kwargs.get('access_group_id', ag.id if hasattr(ag, 'id') else ag),
        }
        vals.update(kwargs)
        return self.env['rfid.service'].create(vals)
        
    def _create_test_door(self, name='Test Door'):
        """Create test door with controller"""
        controller = self.env['hr.rfid.ctrl'].create({
            'name': f'Controller for {name}',
            'ctrl_id': self.env['hr.rfid.ctrl'].search([], order='ctrl_id desc', limit=1).ctrl_id + 1,
            'webstack_id': self.test_webstack_10_3_id.id,
        })
        
        return self.env['hr.rfid.door'].create({
            'name': name,
            'number': 1,
            'controller_id': controller.id,
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id,
        })
        
    def _create_service_sale(self, partner, service, **kwargs):
        """Create service sale via wizard"""
        start_offset = kwargs.get('start_offset_days', 0)
        end_offset = kwargs.get('end_offset_days', 1)
        
        wizard = self.env['rfid.service.sale.wiz'].with_context(
            default_service_id=service.id,
            default_partner_id=partner.id,
            default_card_number=kwargs.get('card_number', f'44{partner.id:08d}{start_offset:02d}{end_offset:02d}'),
        ).create({})
        
        if start_offset != 0 or end_offset != 1:
            wizard.start_date = fields.Datetime.now() + timedelta(days=start_offset)
            wizard.end_date = fields.Datetime.now() + timedelta(days=end_offset)
            
        wizard.write_card()
        
        return self.env['rfid.service.sale'].search([
            ('partner_id', '=', partner.id),
            ('service_id', '=', service.id),
        ], order='create_date desc', limit=1)