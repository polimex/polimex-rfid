# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'hr_attendance_late', 'att_no_show')
class TestNoShowDigestKpi(TransactionCase):
    """The no-show digest KPI counts distinct employees with a 'technical'
    attendance (core absence detection's marker for scheduled-but-absent) in
    the digest window."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.digest = cls.env['digest.digest'].create({
            'name': 'Att Digest', 'company_id': cls.company.id,
            'periodicity': 'daily', 'kpi_hr_rfid_att_no_show': True,
        })
        cls.e1 = cls.env['hr.employee'].create({'name': 'NS1', 'company_id': cls.company.id})
        cls.e2 = cls.env['hr.employee'].create({'name': 'NS2', 'company_id': cls.company.id})

    def _technical(self, employee, day_offset):
        """Mimic core absence detection: 1-second technical attendance."""
        check_in = datetime.now() - timedelta(days=day_offset)
        return self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': check_in,
            'check_out': check_in + timedelta(seconds=1),
            'in_mode': 'technical', 'out_mode': 'technical',
        })

    def _kpi(self):
        # The window comes from context (core passes start/end at send time).
        start = datetime.now() - timedelta(days=2)
        end = datetime.now() + timedelta(days=1)
        digest = self.digest.with_context(start_datetime=start, end_datetime=end)
        digest.invalidate_recordset(['kpi_hr_rfid_att_no_show_value'])
        return digest.sudo().kpi_hr_rfid_att_no_show_value

    def test_counts_distinct_absent_employees(self):
        self._technical(self.e1, 0)
        self._technical(self.e2, 0)
        self.assertEqual(self._kpi(), 2)

    def test_same_employee_counted_once(self):
        # Two technical records for the same employee in the window → 1.
        self._technical(self.e1, 0)
        self.assertEqual(self._kpi(), 1)

    def test_real_attendance_not_counted(self):
        """A genuine (non-technical) attendance is not a no-show."""
        check_in = datetime.now()
        self.env['hr.attendance'].create({
            'employee_id': self.e1.id, 'check_in': check_in,
            'check_out': check_in + timedelta(hours=8),
            'in_mode': 'kiosk', 'out_mode': 'kiosk',
        })
        self.assertEqual(self._kpi(), 0)
