# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestCardConstraints(RFIDAppCase):
    """Test card model constraints."""

    def test_card_number_unique_per_type(self):
        """Test card number must be unique per card type and company."""
        # Card 7734512345 w34 already exists from setUpClass
        with self.assertRaises(Exception):
            self.env['hr.rfid.card'].create({
                'number': '7734512345',
                'card_input_type': 'w34',
                'employee_id': self.test_employee_2_id.id,
                'company_id': self.test_company_id,
            })

    def test_card_number_padding(self):
        """Test that short card numbers are padded to 10 digits."""
        card = self.env['hr.rfid.card'].create({
            'number': '99999',
            'card_input_type': 'w34',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(len(card.number), 10,
                         'Card number should be padded to 10 digits')
        self.assertEqual(card.number, '0000099999',
                         'Card number should be left-padded with zeros')

    def test_card_number_digits_only(self):
        """Test card number must contain only digits."""
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.card'].create({
                'number': 'ABCDE12345',
                'card_input_type': 'w34',
                'employee_id': self.test_employee_2_id.id,
                'company_id': self.test_company_id,
            })

    def test_card_owner_xor(self):
        """Test card must have employee XOR contact, not both."""
        with self.assertRaises(Exception):
            self.env['hr.rfid.card'].create({
                'number': '9876543210',
                'card_input_type': 'w34',
                'employee_id': self.test_employee_id.id,
                'contact_id': self.test_partner.id,
                'company_id': self.test_company_id,
            })

    def test_card_number_10_digits_valid(self):
        """Test valid 10-digit card number."""
        card = self.env['hr.rfid.card'].create({
            'number': '5555555555',
            'card_input_type': 'w34',
            'employee_id': self.test_employee_2_id.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.number, '5555555555')
        card.unlink()


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestWorkcodeConstraints(RFIDAppCase):
    """Test workcode model constraints."""

    def test_workcode_exactly_4_chars(self):
        """Test workcode must be exactly 4 characters."""
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.workcode'].create({
                'name': 'Test WC Short',
                'workcode': '123',  # Only 3 chars
                'company_id': self.test_company_id,
            })

    def test_workcode_digits_only(self):
        """Test workcode must contain only digits."""
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.workcode'].create({
                'name': 'Test WC Alpha',
                'workcode': 'ABCD',
                'company_id': self.test_company_id,
            })

    def test_workcode_valid(self):
        """Test valid workcode creation."""
        wc = self.env['hr.rfid.workcode'].create({
            'name': 'Start Work',
            'workcode': '0001',
            'company_id': self.test_company_id,
        })
        self.assertEqual(wc.workcode, '0001')

    def test_workcode_unique(self):
        """Test workcode uniqueness SQL constraint."""
        self.env['hr.rfid.workcode'].create({
            'name': 'WC 1',
            'workcode': '1111',
            'company_id': self.test_company_id,
        })
        with self.assertRaises(Exception):
            self.env['hr.rfid.workcode'].create({
                'name': 'WC 2',
                'workcode': '1111',  # Duplicate
                'company_id': self.test_company_id,
            })


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestEmployeeConstraints(RFIDAppCase):
    """Test employee RFID-related constraints."""

    def test_employee_pin_exactly_4_digits(self):
        """Test employee PIN code must be exactly 4 digits."""
        with self.assertRaises(ValidationError):
            self.test_employee_id.hr_rfid_pin_code = '123'

    def test_employee_pin_digits_only(self):
        """Test employee PIN code must contain only digits."""
        with self.assertRaises(ValidationError):
            self.test_employee_id.hr_rfid_pin_code = 'ABCD'

    def test_employee_pin_valid(self):
        """Test valid employee PIN code."""
        self.test_employee_id.hr_rfid_pin_code = '1234'
        self.assertEqual(self.test_employee_id.hr_rfid_pin_code, '1234')

    def test_employee_ag_must_be_in_department(self):
        """Test employee AG must be in department's allowed list."""
        other_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Not In Department',
            'company_id': self.test_company_id,
        })
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.access.group.employee.rel'].create({
                'access_group_id': other_ag.id,
                'employee_id': self.test_employee_id.id,
            })


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestPartnerConstraints(RFIDAppCase):
    """Test partner RFID-related constraints."""

    def test_partner_pin_exactly_4_digits(self):
        """Test partner PIN code must be exactly 4 digits."""
        with self.assertRaises(ValidationError):
            self.test_partner.hr_rfid_pin_code = '12'

    def test_partner_pin_digits_only(self):
        """Test partner PIN code must contain only digits."""
        with self.assertRaises(ValidationError):
            self.test_partner.hr_rfid_pin_code = 'WXYZ'

    def test_partner_pin_valid(self):
        """Test valid partner PIN code."""
        self.test_partner.hr_rfid_pin_code = '5678'
        self.assertEqual(self.test_partner.hr_rfid_pin_code, '5678')


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestDepartmentConstraints(RFIDAppCase):
    """Test department RFID-related constraints."""

    def test_default_ag_must_be_in_allowed(self):
        """Test default access group must be in allowed access groups list."""
        other_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Not Allowed in Dept',
            'company_id': self.test_company_id,
        })
        with self.assertRaises(ValidationError):
            self.test_department_id.hr_rfid_default_access_group = other_ag

    def test_default_ag_valid(self):
        """Test valid default access group setting."""
        self.assertEqual(
            self.test_department_id.hr_rfid_default_access_group.id,
            self.test_ag_employee_1.id,
            'Default AG should be AG1 which is in allowed list')

    def test_add_allowed_ag(self):
        """Test adding an access group to allowed list."""
        new_ag = self.env['hr.rfid.access.group'].create({
            'name': 'New Allowed AG',
            'company_id': self.test_company_id,
        })
        self.test_department_id.hr_rfid_allowed_access_groups = [
            (4, new_ag.id, 0)
        ]
        self.assertIn(new_ag, self.test_department_id.hr_rfid_allowed_access_groups)


@tagged('standard', 'at_install', 'rfid', 'rfid_constraints')
class TestAccessGroupConstraints(RFIDAppCase):
    """Test access group specific constraints."""

    def test_circular_inheritance_direct(self):
        """Test direct circular inheritance raises error."""
        ag1 = self.env['hr.rfid.access.group'].create({
            'name': 'Circular AG 1',
            'company_id': self.test_company_id,
        })
        ag2 = self.env['hr.rfid.access.group'].create({
            'name': 'Circular AG 2',
            'company_id': self.test_company_id,
            'inherited_ids': [(4, ag1.id)],
        })
        with self.assertRaises(ValidationError):
            ag1.inherited_ids = [(4, ag2.id)]

    def test_self_inheritance_raises(self):
        """Test self-inheritance raises error."""
        ag = self.env['hr.rfid.access.group'].create({
            'name': 'Self AG',
            'company_id': self.test_company_id,
        })
        with self.assertRaises(ValidationError):
            ag.inherited_ids = [(4, ag.id)]
