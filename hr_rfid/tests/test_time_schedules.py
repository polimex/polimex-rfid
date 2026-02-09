# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.hr_rfid.tests.common import RFIDAppCase

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_schedules')
class TestTimeScheduleIntervals(RFIDAppCase):
    """Test time schedule interval constraints."""

    def test_time_schedule_exists(self):
        """Test that default time schedules exist after module install."""
        ts = self.env['hr.rfid.time.schedule'].search([], limit=1)
        self.assertTrue(ts, 'At least one time schedule should exist')

    def test_interval_begin_before_end(self):
        """Test begin time must be before end time."""
        ts_line = self.env['hr.rfid.ctrl.ts.line']
        with self.assertRaises(ValidationError):
            ts_line.create({
                'day': '0',
                'day_number': 0,
                'begin': 18,
                'end': 8,
                'number': 1,
            })

    def test_valid_interval_creation(self):
        """Test creating a valid time schedule interval."""
        ts_line = self.env['hr.rfid.ctrl.ts.line'].create({
            'day': '0',
            'day_number': 0,
            'begin': 8,
            'end': 17,
            'number': 1,
        })
        self.assertTrue(ts_line.id, 'Valid interval should be created')
        self.assertEqual(ts_line.begin, 8)
        self.assertEqual(ts_line.end, 17)

    def test_interval_float_to_str(self):
        """Test float to string conversion for time values."""
        ts_line = self.env['hr.rfid.ctrl.ts.line']
        interval_str = ts_line._get_float_to_str(8.5)
        self.assertEqual(interval_str, '0830', 'Float 8.5 should convert to 0830')
        interval_str = ts_line._get_float_to_str(17.25)
        self.assertEqual(interval_str, '1715', 'Float 17.25 should convert to 1715')

    def test_zero_end_allowed(self):
        """Test that end=0 is allowed (means midnight/24h)."""
        ts_line = self.env['hr.rfid.ctrl.ts.line'].create({
            'day': '0',
            'day_number': 0,
            'begin': 8,
            'end': 0,
            'number': 1,
        })
        self.assertTrue(ts_line.id, 'End=0 (midnight) should be valid')

    def test_equal_begin_end_raises(self):
        """Test that begin == end raises ValidationError (except when end=0)."""
        ts_line = self.env['hr.rfid.ctrl.ts.line']
        with self.assertRaises(ValidationError):
            ts_line.create({
                'day': '0',
                'day_number': 0,
                'begin': 10,
                'end': 10,
                'number': 1,
            })

    def test_display_name(self):
        """Test display name computation for time schedule line."""
        ts_line = self.env['hr.rfid.ctrl.ts.line'].create({
            'day': '0',
            'day_number': 0,
            'begin': 8,
            'end': 17,
            'number': 1,
        })
        self.assertEqual(ts_line.display_name, '0-1',
                         'Display name should be day-number format')
