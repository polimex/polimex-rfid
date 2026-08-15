# -*- coding: utf-8 -*-
"""Отпуските пътуват с хората - тихо, в реалното си състояние.

Собственикът (2026-08-14): правим HR система - клиентите често имат и
модулите за служители и отпуски, затова прехвърлянето ги носи.

Одобреният отпуск от старата система е ИСТОРИЯ: влиза одобрен, без никой
да получи имейл за преодобряване и без картовият snapshot на
hr_rfid_leave_block да пипне желязото (той реагира на ДЕЙСТВИЕТО одобри,
което историята не изпълнява повторно).
"""
from datetime import date, datetime

from odoo.tests.common import TransactionCase, tagged

from .test_company_scope import _FakeSource


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_leaves')
class TestLeavesComeAcrossQuietly(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.leave' not in cls.env:
            raise cls.skipTest(cls, 'hr_holidays не е инсталиран')
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leaves Person', 'company_id': cls.company.id})

    def _importer(self, data):
        imp = _FakeSource(self.env, {901: self.company.id},
                          {'import_leaves': True, 'import_people': True}, data)
        imp._set_target_id('hr.employee', 71, self.employee.id)
        return imp

    def _leave_data(self):
        return {
            'hr.leave.type': [
                {'id': 11, 'name': 'Migrated PTO', 'active': True},
            ],
            'hr.leave.allocation': [
                {'id': 21, 'employee_id': 71, 'holiday_status_id': 11,
                 'state': 'validate', 'name': 'Yearly', 'number_of_days': 20.0,
                 'date_from': '2026-01-01'},
            ],
            'hr.leave': [
                {'id': 31, 'employee_id': 71, 'holiday_status_id': 11,
                 'state': 'validate',
                 'date_from': '2026-07-01 06:00:00',
                 'date_to': '2026-07-03 15:00:00',
                 'request_date_from': '2026-07-01',
                 'request_date_to': '2026-07-03',
                 'number_of_days': 3.0, 'name': 'Summer'},
            ],
        }

    def test_an_approved_leave_arrives_approved_and_silent(self):
        """Служителят си вижда старите отпуски одобрени; никой не получава
        писмо за преодобряване; желязото не получава нито една команда."""
        from ..models.importers.leave_importer import LeaveImporter
        imp = self._importer(self._leave_data())
        commands_before = self.env['hr.rfid.command'].search_count([])
        mails_before = self.env['mail.mail'].sudo().search_count([])

        results = LeaveImporter(imp).run(None)

        leave = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee.id)])
        self.assertEqual(len(leave), 1, str(results))
        self.assertEqual(leave.state, 'validate',
                         "Одобреното пристига одобрено, не чака наново")
        self.assertEqual(leave.holiday_status_id.name, 'Migrated PTO')
        self.assertEqual(
            self.env['hr.rfid.command'].search_count([]), commands_before,
            "Нула команди към желязото - историята не пипа контролери")
        self.assertEqual(
            self.env['mail.mail'].sudo().search_count([]), mails_before,
            "Никой не получава писмо за чужд стар отпуск")

    def test_a_second_run_brings_nothing_twice(self):
        """Критерият на собственика важи и тук: безкрайно пускане, нула дубли."""
        from ..models.importers.leave_importer import LeaveImporter
        imp = self._importer(self._leave_data())
        LeaveImporter(imp).run(None)
        first = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee.id)]).ids

        again = self._importer(self._leave_data())
        LeaveImporter(again).run(None)

        self.assertEqual(
            self.env['hr.leave'].search(
                [('employee_id', '=', self.employee.id)]).ids, first,
            "Същите отпуски, същите записи - нищо второ")

    def test_a_refused_leave_is_left_behind_by_design(self):
        """Отказаното и черновите са шум на другата система - НЕ пътуват."""
        from ..models.importers.leave_importer import LeaveImporter
        data = self._leave_data()
        data['hr.leave'].append({
            'id': 32, 'employee_id': 71, 'holiday_status_id': 11,
            'state': 'refuse',
            'date_from': '2026-08-01 06:00:00', 'date_to': '2026-08-02 15:00:00',
            'request_date_from': '2026-08-01', 'request_date_to': '2026-08-02',
            'number_of_days': 2.0, 'name': 'Refused one'})
        imp = self._importer(data)

        LeaveImporter(imp).run(None)

        self.assertEqual(
            self.env['hr.leave'].search_count(
                [('employee_id', '=', self.employee.id)]), 1,
            "Отказаният отпуск не бива да се появява тук")

    def test_shipped_leave_types_are_recognised_not_recreated(self):
        """Стандартният тип от модула не става втори 'Paid Time Off' -
        урокът от видовете карти."""
        from ..models.importers.leave_importer import LeaveImporter
        shipped = self.env['hr.leave.type'].search([], limit=1)
        if not shipped:
            self.skipTest('няма доставени типове')
        data = {'hr.leave.type': [{'id': 12, 'name': shipped.name,
                                   'active': True}],
                'hr.leave.allocation': [], 'hr.leave': []}
        imp = self._importer(data)
        # Източникът "доставя" типа със същия external id като целта.
        src_imd = self.env['ir.model.data'].search(
            [('model', '=', 'hr.leave.type'), ('res_id', '=', shipped.id)],
            limit=1)
        if not src_imd:
            self.skipTest('доставените типове нямат external id тук')
        imp._data['ir.model.data'] = [{
            'id': 900, 'module': src_imd.module, 'name': src_imd.name,
            'model': 'hr.leave.type', 'res_id': 12}]
        before = self.env['hr.leave.type'].search_count([])

        LeaveImporter(imp).run(None)

        self.assertEqual(self.env['hr.leave.type'].search_count([]), before,
                         "Доставеният тип се разпознава, не се създава втори")
