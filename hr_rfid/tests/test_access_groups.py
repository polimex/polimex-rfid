# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group')
class TestAccessGroupBasic(RFIDAppCase):
    """Test basic access group CRUD operations."""

    def test_create_access_group(self):
        """Test creating a basic access group."""
        ag = self.env['hr.rfid.access.group'].create({
            'name': 'New Test AG',
            'company_id': self.test_company_id,
        })
        self.assertTrue(ag.id, 'Access group should be created')
        self.assertEqual(ag.name, 'New Test AG')

    def test_access_group_company_isolation(self):
        """Test access groups belong to specific company."""
        self.assertEqual(self.test_ag_employee_1.company_id.id,
                         self.test_company_id,
                         'AG should belong to test company')

    def test_access_group_delay_default(self):
        """Test delay_between_events defaults to 0."""
        self.assertEqual(self.test_ag_employee_1.delay_between_events, 0,
                         'Default delay should be 0')

    def test_access_group_set_delay(self):
        """Test setting delay_between_events."""
        self.test_ag_employee_1.delay_between_events = 60
        self.assertEqual(self.test_ag_employee_1.delay_between_events, 60,
                         'Delay should be set to 60')

    def test_access_group_unlink(self):
        """Test deleting an access group."""
        ag = self.env['hr.rfid.access.group'].create({
            'name': 'Temp AG',
            'company_id': self.test_company_id,
        })
        ag_id = ag.id
        ag.unlink()
        self.assertFalse(
            self.env['hr.rfid.access.group'].search([('id', '=', ag_id)]),
            'AG should be deleted')


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group')
class TestAccessGroupInheritance(RFIDAppCase):
    """Test access group inheritance and circular reference detection."""

    def test_simple_inheritance(self):
        """Test basic parent→child inheritance."""
        parent_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Parent AG',
            'company_id': self.test_company_id,
        })
        child_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Child AG',
            'company_id': self.test_company_id,
            'inherited_ids': [(4, parent_ag.id)],
        })
        self.assertIn(parent_ag, child_ag.inherited_ids,
                      'Parent should be in inherited_ids')

    def test_circular_reference_raises(self):
        """Test circular inheritance raises ValidationError."""
        ag1 = self.env['hr.rfid.access.group'].create({
            'name': 'AG Circular 1',
            'company_id': self.test_company_id,
        })
        ag2 = self.env['hr.rfid.access.group'].create({
            'name': 'AG Circular 2',
            'company_id': self.test_company_id,
            'inherited_ids': [(4, ag1.id)],
        })
        with self.assertRaises(ValidationError):
            ag1.write({'inherited_ids': [(4, ag2.id)]})

    def test_deep_circular_reference_raises(self):
        """Test deep circular inheritance (A→B→C→A) raises ValidationError."""
        ag_a = self.env['hr.rfid.access.group'].create({
            'name': 'AG A',
            'company_id': self.test_company_id,
        })
        ag_b = self.env['hr.rfid.access.group'].create({
            'name': 'AG B',
            'company_id': self.test_company_id,
            'inherited_ids': [(4, ag_a.id)],
        })
        ag_c = self.env['hr.rfid.access.group'].create({
            'name': 'AG C',
            'company_id': self.test_company_id,
            'inherited_ids': [(4, ag_b.id)],
        })
        with self.assertRaises(ValidationError):
            ag_a.write({'inherited_ids': [(4, ag_c.id)]})


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group')
class TestAccessGroupEmployeeRel(RFIDAppCase):
    """Test access group ↔ employee relationships."""

    def test_create_employee_rel(self):
        """Test creating employee ↔ AG relationship."""
        rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': self.test_ag_employee_1.id,
            'employee_id': self.test_employee_id.id,
        })
        self.assertTrue(rel.id, 'Employee AG rel should be created')

    def test_employee_rel_future_activation(self):
        """Test employee rel with future activation date."""
        rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': self.test_ag_employee_1.id,
            'employee_id': self.test_employee_id.id,
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
        })
        self.assertTrue(rel.activate_on > fields.Datetime.now(),
                        'Activation should be in the future')

    def test_employee_rel_expired(self):
        """Test employee rel with past expiration."""
        rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': self.test_ag_employee_1.id,
            'employee_id': self.test_employee_id.id,
            'activate_on': fields.Datetime.now() - relativedelta(hours=2),
            'expiration': fields.Datetime.now() - relativedelta(hours=1),
        })
        self.assertTrue(rel.expiration < fields.Datetime.now(),
                        'Expiration should be in the past')

    def test_employee_rel_visits_counting(self):
        """Test visits counting on employee AG relationship."""
        rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': self.test_ag_employee_1.id,
            'employee_id': self.test_employee_id.id,
            'visits_counting': True,
            'permitted_visits': 5,
        })
        self.assertTrue(rel.visits_counting, 'Visits counting should be enabled')
        self.assertEqual(rel.permitted_visits, 5, 'Permitted visits should be 5')
        self.assertEqual(rel.visits_counter, 0, 'Visits counter should start at 0')

    def test_employee_ag_must_be_in_department_allowed(self):
        """Test AG must be in department's allowed access groups."""
        # Create AG not in department's allowed list
        other_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Not Allowed AG',
            'company_id': self.test_company_id,
        })
        with self.assertRaises(ValidationError):
            self.env['hr.rfid.access.group.employee.rel'].create({
                'access_group_id': other_ag.id,
                'employee_id': self.test_employee_id.id,
            })


@tagged('standard', 'at_install', 'rfid', 'rfid_access_group')
class TestAccessGroupContactRel(RFIDAppCase):
    """Test access group ↔ contact relationships."""

    def test_create_contact_rel(self):
        """Test creating contact ↔ AG relationship."""
        # test_partner_ag_rel already exists from setUpClass
        self.assertEqual(self.test_partner_ag_rel.contact_id.id,
                         self.test_partner.id)
        self.assertEqual(self.test_partner_ag_rel.access_group_id.id,
                         self.test_ag_partner_1.id)

    def test_contact_rel_with_different_ag(self):
        """Test creating contact rel with a different access group."""
        new_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Different AG for Contact',
            'company_id': self.test_company_id,
        })
        rel = self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': new_ag.id,
            'contact_id': self.test_partner.id,
        })
        self.assertTrue(rel.id, 'Contact rel with different AG should be created')

    def test_contact_rel_visits_counting(self):
        """Test visits counting on contact AG relationship."""
        new_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Visits AG',
            'company_id': self.test_company_id,
        })
        rel = self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': new_ag.id,
            'contact_id': self.test_partner.id,
            'visits_counting': True,
            'permitted_visits': 3,
        })
        self.assertTrue(rel.visits_counting)
        self.assertEqual(rel.permitted_visits, 3)
