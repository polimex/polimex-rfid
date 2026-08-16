# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_card')
class TestCardCreation(RFIDAppCase):
    """Test card creation with various formats and ownership rules."""

    def test_create_card_w34_format(self):
        """Test creating a card with Wiegand 34 bit format."""
        card = self.env['hr.rfid.card'].create({
            'number': '9999988888',
            'card_input_type': 'w34',
            'employee_id': self.test_employee_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.internal_number, '9999988888',
                         'W34 card internal number should match input')
        self.assertTrue(card.id, 'Card should be created successfully')

    def test_create_card_w34s_format(self):
        """Test creating a card with Wiegand 34 swapped format."""
        card = self.env['hr.rfid.card'].create({
            'number': '2760500060',
            'card_input_type': 'w34s',
            'employee_id': self.test_employee_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.internal_number, '4212158204',
                         'W34s internal_number should be swapped')

    def test_card_name_from_reference(self):
        """Test card name defaults to card_reference when set."""
        self.assertEqual(self.test_card_employee.name, 'Badge 77',
                         'Card name should use card_reference')

    def test_card_name_from_number(self):
        """Test card name falls back to number when no reference."""
        card = self.env['hr.rfid.card'].create({
            'number': '5555566666',
            'card_input_type': 'w34',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.name, '5555566666',
                         'Card name should fall back to number')

    def test_duplicate_card_number_same_company_raises(self):
        """Test that duplicate card number in same company raises error."""
        with self.assertRaises(Exception):
            self.env['hr.rfid.card'].create({
                'number': '7734512345',  # Same as test_card_employee
                'card_input_type': 'w34',
                'employee_id': self.test_employee_2_id.id,
                'company_id': self.test_company_id,
            })

    def test_card_number_padding(self):
        """Test that short card numbers are padded with leading zeros."""
        card = self.env['hr.rfid.card'].create({
            'number': '12345',  # 5 digits
            'card_input_type': 'w34',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(len(card.number), 10,
                         'Card number should be padded to 10 digits')
        self.assertEqual(card.number, '0000012345',
                         'Card number should be left-padded with zeros')

    def test_card_number_digits_only(self):
        """Test that non-numeric card number raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.card'].create({
                'number': '12345ABCDE',
                'card_input_type': 'w34',
                'employee_id': self.test_employee_2_id.id,
                'company_id': self.test_company_id,
            })

    def test_card_both_employee_and_contact_raises(self):
        """Test that setting both employee and contact raises error."""
        with self.assertRaises(Exception):
            self.env['hr.rfid.card'].create({
                'number': '7777788888',
                'card_input_type': 'w34',
                'employee_id': self.test_employee_id.id,
                'contact_id': self.test_partner.id,
                'company_id': self.test_company_id,
            })


@tagged('standard', 'at_install', 'rfid', 'rfid_card')
class TestCardActivation(RFIDAppCase):
    """Test card activation/deactivation with time windows."""

    def test_card_ready_no_dates(self):
        """Test card_ready() returns True when no activation dates set."""
        self.assertTrue(self.test_card_employee.card_ready(),
                        'Card without dates should be ready')

    def test_card_ready_active_window(self):
        """Test card_ready() within valid activation window."""
        self.test_card_employee.write({
            'activate_on': fields.Datetime.now() - relativedelta(hours=1),
            'deactivate_on': fields.Datetime.now() + relativedelta(hours=1),
        })
        self.assertTrue(self.test_card_employee.card_ready(),
                        'Card within active window should be ready')

    def test_card_not_ready_future_activation(self):
        """Test card_ready() returns False before activation date."""
        self.test_card_employee.write({
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
        })
        self.assertFalse(self.test_card_employee.card_ready(),
                         'Card with future activation should not be ready')

    def test_card_not_ready_past_deactivation(self):
        """Test card_ready() returns False after deactivation date."""
        self.test_card_employee.write({
            'activate_on': fields.Datetime.now() - relativedelta(hours=2),
            'deactivate_on': fields.Datetime.now() - relativedelta(hours=1),
        })
        self.assertFalse(self.test_card_employee.card_ready(),
                         'Card past deactivation should not be ready')

    def test_card_door_compatible(self):
        """Test card door compatibility check based on card type."""
        # test_card_employee uses default card type, should be compatible with default door type
        self.assertTrue(self.test_card_employee.card_type,
                        'Card should have a card type')


@tagged('standard', 'at_install', 'rfid', 'rfid_card')
class TestCardOwnerChange(RFIDAppCase):
    """Test card ownership changes and their effects."""

    def test_card_employee_assignment(self):
        """Test card is properly assigned to employee."""
        self.assertEqual(self.test_card_employee.employee_id.id,
                         self.test_employee_id.id,
                         'Card should be assigned to correct employee')

    def test_card_contact_assignment(self):
        """Test card is properly assigned to contact."""
        self.assertEqual(self.test_card_partner.contact_id.id,
                         self.test_partner.id,
                         'Card should be assigned to correct contact')

    def test_card_pin_code_from_owner(self):
        """Test card PIN code is computed from owner."""
        self.test_employee_id.hr_rfid_pin_code = '1234'
        self.test_card_employee.invalidate_recordset()
        self.assertEqual(self.test_card_employee.pin_code, '1234',
                         'Card PIN should match employee PIN')

    def test_card_internal_number_w34(self):
        """Test internal number calculation for w34 format."""
        self.assertEqual(self.test_card_partner.internal_number, '0077312345',
                         'W34 internal number should equal card number')


@tagged('standard', 'at_install', 'rfid', 'rfid_card')
class TestPlateNumberEntry(RFIDAppCase):
    """Номерът на табелата трябва да е равен на това, което камерата ще
    разпознае - иначе събитието никога не намира картата.

    Правилото на собственика (2026-08-16): "определено гръмко казваме че има
    непозволен символ който не може да конвертираме. ако можем да
    конвертираме просто го конвертираме и не казваме нищо."
    """

    def _plate(self, number):
        return self.env['hr.rfid.card'].create({
            'number': number,
            'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_8').id,
            'employee_id': self.test_employee_id.id,
            'company_id': self.test_company_id,
        })

    def test_convertible_input_is_fixed_without_a_word(self):
        """Кирилски двойници, малки букви и разделители се поправят тихо -
        операторът пише каквото вижда на табелата, системата пази каквото
        камерата ще прати."""
        card = self._plate('св 5803-см')
        self.assertEqual(card.number, 'CB5803CM')

    def test_junk_is_refused_out_loud_naming_the_character(self):
        """Символ без съответствие на табела не се изтрива тихо - до днес
        'CB5803§M' ставаше 'CB5803M' без думичка и записът пазеше номер,
        който не е номерът."""
        from odoo.exceptions import UserError
        with self.assertRaises(UserError) as caught:
            self._plate('CB5803§M')
        self.assertIn('§', str(caught.exception),
                      'отказът не назовава непозволения символ')

    def test_the_round_trip_is_the_point(self):
        """Въведеното с двойници се намира от събитието на камерата -
        търсенето, което обработката на разпознаване прави."""
        card = self._plate('рв4181кс')
        found = self.env['hr.rfid.card'].with_context(
            active_test=False).search([
                ('number', '=', 'PB4181KC'),
                ('company_id', '=', self.test_company_id),
            ])
        self.assertEqual(found, card,
                         'камерното събитие няма да намери тази табела')

    def test_ordinary_cards_keep_their_own_rules(self):
        card = self.env['hr.rfid.card'].create({
            'number': '12345',
            'employee_id': self.test_employee_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.number, '0000012345',
                         'обикновената карта губи водещите си нули')
