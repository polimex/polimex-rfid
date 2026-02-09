# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_wizards')
class TestAccessGroupWizard(RFIDController, HttpCase):
    """Test HrRfidAccessGroupWizard (add/remove doors)."""
    _registry_readonly_enabled = False

    def test_wizard_add_doors(self):
        """Test adding doors to AG via wizard."""
        self._add_iCon110()
        wiz = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_employee_1.id]}
        ).create({
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        wiz.add_doors()
        self.assertTrue(len(self.test_ag_employee_1.door_ids) > 0,
                        'AG should have doors after wizard add')

    def test_wizard_del_doors(self):
        """Test removing doors from AG via wizard."""
        self._add_iCon110()
        # First add doors
        self.test_ag_employee_1.add_doors(self.c_110.door_ids)
        initial_count = len(self.test_ag_employee_1.door_ids)
        self.assertTrue(initial_count > 0, 'AG should have doors before removal')

        # Then remove via wizard
        wiz = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_employee_1.id]}
        ).create({
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        wiz.del_doors()
        self.assertEqual(len(self.test_ag_employee_1.door_ids), 0,
                         'AG should have no doors after wizard removal')


@tagged('standard', 'at_install', 'rfid', 'rfid_wizards')
class TestZoneDoorsWizard(RFIDController, HttpCase):
    """Test HrRfidZoneDoorsWizard (add/remove doors to zone)."""
    _registry_readonly_enabled = False

    def test_zone_wizard_add_doors(self):
        """Test adding doors to zone via wizard."""
        self._add_iCon110()
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Wizard Zone',
            'company_id': self.test_company_id,
        })
        wiz = self.env['hr.rfid.zone.doors.wiz'].with_context(
            {'active_ids': [zone.id]}
        ).create({
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        wiz.add_doors()
        self.assertEqual(len(zone.door_ids), len(self.c_110.door_ids),
                         'Zone should have controller doors')

    def test_zone_wizard_remove_doors(self):
        """Test removing doors from zone via wizard."""
        self._add_iCon110()
        zone = self.env['hr.rfid.zone'].create({
            'name': 'Wizard Zone 2',
            'company_id': self.test_company_id,
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        initial_count = len(zone.door_ids)
        self.assertTrue(initial_count > 0)

        wiz = self.env['hr.rfid.zone.doors.wiz'].with_context(
            {'active_ids': [zone.id]}
        ).create({
            'door_ids': [(4, d.id) for d in self.c_110.door_ids],
        })
        wiz.remove_doors()
        self.assertEqual(len(zone.door_ids), 0,
                         'Zone should have no doors after removal')


@tagged('standard', 'at_install', 'rfid', 'rfid_wizards')
class TestDepartmentAccessGroupWizard(RFIDController, HttpCase):
    """Test department access group wizards."""
    _registry_readonly_enabled = False

    def test_dept_acc_gr_wizard(self):
        """Test setting allowed access groups on department via wizard."""
        new_ag = self.env['hr.rfid.access.group'].create({
            'name': 'Dept Wizard AG',
            'company_id': self.test_company_id,
        })
        wiz = self.env['hr.department.acc.grs'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'acc_grs': [(6, 0, [self.test_ag_employee_1.id, new_ag.id])],
        })
        wiz.add_acc_grs()
        self.assertIn(new_ag, self.test_department_id.hr_rfid_allowed_access_groups,
                      'New AG should be in allowed list')

    def test_dept_def_acc_gr_wizard(self):
        """Test setting default access group via wizard."""
        wiz = self.env['hr.department.def.acc.gr'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'def_acc_gr': self.test_ag_employee_1.id,
        })
        wiz.change_default_access_group()
        self.assertEqual(
            self.test_department_id.hr_rfid_default_access_group.id,
            self.test_ag_employee_1.id,
            'Default AG should be set')

    def test_dept_change_and_apply_def_acc_gr(self):
        """Test changing default AG and applying to all employees."""
        wiz = self.env['hr.department.def.acc.gr'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'def_acc_gr': self.test_ag_employee_1.id,
        })
        wiz.change_and_apply_def_acc_gr()
        self.assertEqual(
            self.test_department_id.hr_rfid_default_access_group.id,
            self.test_ag_employee_1.id)

    def test_dept_mass_add_acc_grs(self):
        """Test mass adding access groups to department employees."""
        wiz = self.env['hr.department.mass.wiz'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'acc_gr_ids': [(6, 0, [self.test_ag_employee_1.id])],
        })
        wiz.add_acc_grs()

    def test_dept_mass_remove_acc_grs(self):
        """Test mass removing access groups from department employees."""
        # First add
        wiz_add = self.env['hr.department.mass.wiz'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'acc_gr_ids': [(6, 0, [self.test_ag_employee_1.id])],
        })
        wiz_add.add_acc_grs()

        # Then remove
        wiz_remove = self.env['hr.department.mass.wiz'].with_context(
            {'active_ids': [self.test_department_id.id]}
        ).create({
            'acc_gr_ids': [(6, 0, [self.test_ag_employee_1.id])],
        })
        wiz_remove.remove_acc_grs()


@tagged('standard', 'at_install', 'rfid', 'rfid_wizards')
class TestCardAddRemoveEmployee(RFIDController, HttpCase):
    """Test adding/removing cards from employees via controller initialization."""
    _registry_readonly_enabled = False

    def test_add_remove_card_employee(self):
        """Test full employee card add/remove cycle."""
        self._add_iCon50()
        self._check_no_cmd(self.c_50)

        test_ag_id = self.env['hr.rfid.access.group'].create({
            'name': 'Test AG Card',
            'company_id': self.test_company_id,
            'door_ids': [(0, 0, {'door_id': d_id}) for d_id in self.c_50.door_ids.mapped('id')]
        })
        self.test_employee_id.department_id.write({
            'hr_rfid_allowed_access_groups': [(4, test_ag_id.id, 0)],
        })

        # AG in future - no commands
        from dateutil.relativedelta import relativedelta
        test_emp_ag_rel = self.env['hr.rfid.access.group.employee.rel'].create({
            'access_group_id': test_ag_id.id,
            'employee_id': self.test_employee_id.id,
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
            'expiration': fields.Datetime.now() + relativedelta(hours=2),
            'visits_counting': True,
            'permitted_visits': 1,
        })
        self._check_no_cmd(self.c_50)

        # Activate now
        test_emp_ag_rel.activate_on = fields.Datetime.now() + relativedelta(minutes=-1)
        self._check_cmd_add_card_and_remove(self.c_50)
        self._check_no_cmd(self.c_50)

        # Expire
        test_emp_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=-1),
        })
        self._check_cmd_delete_card_and_remove(self.c_50)
        self._check_no_cmd(self.c_50)

        # Cleanup
        test_ag_id.unlink()


@tagged('standard', 'at_install', 'rfid', 'rfid_wizards')
class TestCardAddRemovePartner(RFIDController, HttpCase):
    """Test adding/removing cards from partners via controller initialization."""
    _registry_readonly_enabled = False

    def test_add_remove_card_partner(self):
        """Test full partner card add/remove cycle with card validity interaction."""
        self._add_iCon50()
        self._check_no_cmd(self.c_50)

        test_ag_id = self.env['hr.rfid.access.group'].create({
            'name': 'Test AG Partner Card',
            'company_id': self.test_company_id,
            'door_ids': [(0, 0, {'door_id': d_id}) for d_id in self.c_50.door_ids.mapped('id')]
        })

        from dateutil.relativedelta import relativedelta

        # AG in future, card in past - no commands
        test_partner_ag_rel = self.env['hr.rfid.access.group.contact.rel'].create({
            'access_group_id': test_ag_id.id,
            'contact_id': self.test_partner.id,
            'activate_on': fields.Datetime.now() + relativedelta(hours=1),
            'expiration': fields.Datetime.now() + relativedelta(hours=2),
            'visits_counting': True,
            'permitted_visits': 1,
        })
        self.test_card_partner.activate_on = fields.Datetime.now() + relativedelta(hours=-1)
        self.test_card_partner.deactivate_on = fields.Datetime.now() + relativedelta(minutes=-30)
        self._check_no_cmd(self.c_50)

        # Activate AG but card still expired - no commands
        test_partner_ag_rel.activate_on = fields.Datetime.now() + relativedelta(minutes=-1)
        self._check_no_cmd(self.c_50)

        # Card in present - now commands
        self.test_card_partner.write({
            'activate_on': fields.Datetime.now() + relativedelta(hours=-1),
            'deactivate_on': fields.Datetime.now() + relativedelta(minutes=+30),
        })
        self._check_cmd_add_card_and_remove(self.c_50)
        self._check_no_cmd(self.c_50)

        # Expire AG
        test_partner_ag_rel.write({
            'activate_on': fields.Datetime.now() + relativedelta(minutes=-3),
            'expiration': fields.Datetime.now() + relativedelta(minutes=-1),
        })
        self._check_cmd_delete_card_and_remove(self.c_50)
        self._check_no_cmd(self.c_50)

        # Cleanup
        test_ag_id.unlink()
