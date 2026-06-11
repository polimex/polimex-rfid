# Copyright 2022 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_rfid.tests.test_functional import RFIDTests
from odoo.tests.common import HttpCase, tagged
from odoo import fields

import logging

_logger = logging.getLogger(__name__)


# @tagged('post_install', '-at_install', 'migration')
@tagged('standard', 'at_install', 'migration')
class RFIDAttendanceTests(RFIDTests, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 'absent' is only computed for employees that are scheduled to work at
        # the moment the compute runs: hr_attendance/models/hr_employee.py
        # _compute_presence_state requires membership in
        # hr/models/hr_employee.py _get_employee_working_now(), which checks
        # the resource calendar for a work interval within [now, now + 1h].
        # With the default Mon-Fri 8-17 company calendar the check-out
        # assertions would only hold during office hours, so pin a 24/7
        # calendar on the test employees to make the test independent of the
        # wall-clock time the suite runs at.
        cls.full_time_calendar = cls.env['resource.calendar'].create({
            'name': 'Test 24/7 Calendar',
            'company_id': cls.test_company_id,
            'tz': 'Europe/Sofia',
            'attendance_ids': [
                (0, 0, {
                    'name': 'Day %d' % day,
                    'dayofweek': str(day),
                    'hour_from': 0.0,
                    # 24:00 is interpreted as 23:59:59.999999 by core, see
                    # resource.calendar.attendance hour_from help text.
                    'hour_to': 24.0,
                    'day_period': 'full_day',
                })
                for day in range(7)
            ],
        })
        employees = cls.test_employee_id + cls.test_employee_2_id
        employees.resource_calendar_id = cls.full_time_calendar
        assert len(cls.full_time_calendar.attendance_ids) == 7, \
            'The 24/7 test calendar must keep its explicit attendance lines'
        assert all(e.resource_calendar_id == cls.full_time_calendar for e in employees), \
            'Both test employees must be on the 24/7 calendar'

    def setUp(self):
        super(RFIDAttendanceTests, self).setUp()

    def _event_time_args(self, seconds_ago):
        """date/day/time payload arguments for a controller event that
        happened ``seconds_ago`` seconds before ``self.test_now``.

        All three strings are derived from the same datetime, so events keep
        their relative order even when the test runs around midnight (the
        default ``self.test_*_10_3`` strings share a single per-test
        timestamp, which would make check-in and check-out coincide)."""
        moment = self.test_now - relativedelta(seconds=seconds_ago)
        return {
            'date': '%02d.%02d.%02d' % (moment.day, moment.month, moment.year - 2000),
            'day': '%d' % moment.weekday(),
            'time': '%02d:%02d:%02d' % (moment.hour, moment.minute, moment.second),
        }

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

        # Make events with cards on entrance/exit readers. Real controllers
        # timestamp every event individually, so simulate an ordered stream
        # (check-ins strictly before check-outs) instead of reusing the single
        # per-test timestamp for all four events.
        response = self._make_event(self.c_130, card=self.test_card_employee.number, reader=1, event_code=3,
                                    **self._event_time_args(180))
        self.assertTrue(self.test_employee_id.hr_presence_state == 'present',
                        'Check correct present for Employee 1 after checkin')
        self.assertTrue(test_att_zone_1.employee_count == '1', 'Check correct employee count of the attendance zone 1')

        response = self._make_event(self.c_130, card=self.test_card_employee_2.number, reader=1, event_code=3,
                                    **self._event_time_args(150))
        self.assertTrue(self.test_employee_2_id.hr_presence_state == 'present',
                        'Check correct present for Employee 2 after checkin')
        self.assertTrue(test_att_zone_2.employee_count == '1', 'Check correct employee count of the attendance zone 2')

        response = self._make_event(self.c_130, card=self.test_card_employee.number, reader=4, event_code=15,
                                    **self._event_time_args(120))
        self.assertTrue(self.test_employee_id.hr_presence_state == 'absent',
                        'Check correct absent for Employee 1 after check out')
        self.assertTrue(test_att_zone_1.employee_count == '0', 'Check correct employee count of the attendance zone 1')

        response = self._make_event(self.c_130, card=self.test_card_employee_2.number, reader=4, event_code=15,
                                    **self._event_time_args(90))
        self.assertTrue(self.test_employee_2_id.hr_presence_state == 'absent',
                        'Check correct absent for Employee 2 after check out')
        self.assertTrue(test_att_zone_2.employee_count == '0', 'Check correct employee count of the attendance zone 2')

        pass
