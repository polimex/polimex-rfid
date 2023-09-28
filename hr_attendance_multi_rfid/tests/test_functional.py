# Copyright 2022 Polimex Holding Ltd..
# License APL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.test_functional import RFIDTests
from odoo.tests.common import HttpCase, tagged
from odoo import fields

import logging

_logger = logging.getLogger(__name__)


# @tagged('post_install', '-at_install', 'migration')
@tagged('standard', 'at_install', 'migration')
class RFIDAttendanceTests(RFIDTests, HttpCase):
    def setUp(self):
        super(RFIDAttendanceTests, self).setUp()

    def test_functionality(self):
        _logger.info('Start tests for iCON130 ')
        self._add_iCon130()
        self._test_attendance_zone()

    def _test_attendance_zone(self):
        self._change_mode(self.c_130, 2)  # Change mode to 2 door with two readers
        self.assertTrue(self.c_130.mode == 2)

        add_door_to_ag1_wiz = self.env['hr.rfid.access.group.wizard'].with_context(
            {'active_ids': [self.test_ag_partner_1.id]}).create([{
            'door_ids': [
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        }])
        add_door_to_ag1_wiz.add_doors()
        add_door_to_ag1_wiz.unlink()
        self._check_cmd_add_card_and_remove(self.c_130, 1, 15)

        # Make zone for Attendance
        test_att_zone_1 = self.env['hr.rfid.zone'].create({
            'name': 'Test Attendance Zone 1',
            'company_id': self.test_company_id,
            'attendance': True,
            'permitted_employee_category_ids': [
                (4, self.test_employee_tag1_id.id, 0),
            ],
            'door_ids': [
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        })

        test_att_zone_2 = self.env['hr.rfid.zone'].create({
            'name': 'Test Attendance Zone 2',
            'company_id': self.test_company_id,
            'attendance': True,
            'permitted_employee_category_ids': [
                (4, self.test_employee_tag2_id.id, 0),
            ],
            'door_ids': [
                (4, self.c_130.door_ids[0].id, 0),
                (4, self.c_130.door_ids[1].id, 0),
            ]
        })

        # self.c_110.door_ids.apb_mode = True
        response = self._hearbeat(self.test_webstack_10_3_id)
        # response = self._send_cmd_response(response)

        # self._check_cmd_add_card_and_remove(self.c_130,count=1,rights=0, mask=96)

        # Make event with card on entrance on first door
        response = self._make_event(self.c_130, card=self.test_card_employee.number, reader=1, event_code=3)
        self.assertTrue(self.test_employee_id.hr_presence_state == 'present',
                        'Check correct present for Employee 1 after checkin')
        self.assertTrue(test_att_zone_1.employee_count == '1', 'Check correct employee count of the attendance zone 1')

        response = self._make_event(self.c_130, card=self.test_card_employee_2.number, reader=1, event_code=3)
        self.assertTrue(self.test_employee_id.hr_presence_state == 'present',
                        'Check correct present for Employee 2 after checkin')
        self.assertTrue(test_att_zone_2.employee_count == '1', 'Check correct employee count of the attendance zone 2')

        response = self._make_event(self.c_130, card=self.test_card_employee.number, reader=4, event_code=15)
        self.assertTrue(self.test_employee_id.hr_presence_state == 'absent',
                        'Check correct absent for Employee 1 after check out')
        self.assertTrue(test_att_zone_1.employee_count == '0', 'Check correct employee count of the attendance zone 1')

        response = self._make_event(self.c_130, card=self.test_card_employee_2.number, reader=4, event_code=15)
        self.assertTrue(self.test_employee_id.hr_presence_state == 'absent',
                        'Check correct absent for Employee 2 after check out')
        self.assertTrue(test_att_zone_2.employee_count == '0', 'Check correct employee count of the attendance zone 2')

        pass
