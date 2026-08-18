# -*- coding: utf-8 -*-
"""По-стар източник няма всичко - това не бива да коства чужда работа.

Бизнес твърдение (собственик, 2026-08-17): "от одоо 14 трябва и отпуските да
прехвърлим" - тоест прехвърляне от 14-та версия трябва да ДОНЕСЕ данните ѝ,
а не да се спъне в нещо, което тази версия просто не води.

Мерено на живо на източник от Odoo 14: модулът за работно време там няма
модел за дневните обобщения изобщо (в 14-та той само разширява присъствията).
Стъпката за обобщенията гърмеше на първия си ред, а понеже двете стъпки бяха
извикани една след друга, savepoint-ът на фазата връщаше и вече записаните
196 659 присъствия. Загубата беше пълна, а протоколът показваше един червен
ред, който не казва, че е взел и присъствията със себе си.
"""

import xmlrpc.client

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.attendance_importer import AttendanceImporter
from .test_company_scope import _FakeSource


class _OlderSource(_FakeSource):
    """Двойник, който се държи като истински по-стар сървър.

    Ключовото: сървър, който няма такъв модел, НЕ връща празен списък - той
    вдига грешка ("Object hr.attendance.extra doesn't exist", мерено срещу
    живата 14-та). Двойник, който мълчаливо връща нищо, не може да докаже
    нищо за този случай - изглежда зелен и при повредения код.
    """

    def _missing(self, model):
        raise xmlrpc.client.Fault(
            2, "Object %s doesn't exist" % model)

    def _has_model(self, model):
        # Огледало на истинския: пита източника и хваща отказа му.
        try:
            self._search_read(model, [], ['id'])
            return True
        except xmlrpc.client.Fault:
            return False

    def _get_source_fields(self, model):
        if model not in self._data:
            self._missing(model)
        return super()._get_source_fields(model)

    def _search_read(self, model, domain, fields, order='id asc', limit=0,
                     include_archived=True):
        if model not in self._data:
            self._missing(model)
        return super()._search_read(model, domain, fields, order=order,
                                    limit=limit,
                                    include_archived=include_archived)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_v14')
class TestOlderSourceMissingModels(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'V14 Tenant'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Работник от 14-та', 'company_id': cls.company.id,
        })

    def _source(self):
        """Източник като 14-та: има присъствия, няма дневни обобщения."""
        src = _OlderSource(
            self.env, {101: self.company.id},
            {'import_attendance': True, 'import_attendance_extra': True},
            {'hr.attendance': [
                {'id': 1, 'employee_id': [7, 'Работник'],
                 'check_in': '2026-08-01 06:00:00',
                 'check_out': '2026-08-01 14:00:00'},
                {'id': 2, 'employee_id': [7, 'Работник'],
                 'check_in': '2026-08-02 06:00:00',
                 'check_out': '2026-08-02 14:00:00'},
            ]},
        )
        src.id_map = {'hr.employee': {7: self.employee.id}}
        return src

    def test_the_attendances_survive_a_source_without_the_roll_ups(self):
        source = self._source()
        phase = AttendanceImporter(source)
        # Ако липсващият модел събори фазата, дотук не се стига изобщо -
        # точно това правеше прехвърлянето от 14-та.
        phase.run(wizard=None)

        rows = {r['model']: r for r in phase.results}
        self.assertIn(
            'hr.attendance', rows,
            'Присъствията изчезнаха заедно с падналата съседна стъпка - точно '
            'загубата, измерена на 14-та версия',
        )
        self.assertEqual(rows['hr.attendance']['imported_count'], 2)
        written = [call for call in source.bulk_calls
                   if call['table'] == 'hr_attendance']
        self.assertEqual(
            [len(call['rows']) for call in written], [2],
            'Редовете не са стигнали до записа, макар протоколът да ги брои',
        )

    def test_it_says_that_system_keeps_no_such_thing(self):
        source = self._source()
        phase = AttendanceImporter(source)
        phase.run(wizard=None)

        rows = {r['model']: r for r in phase.results}
        self.assertIn(
            'hr.attendance.extra', rows,
            'Липсващият модел не е обяснен изобщо - редът просто липсва, '
            'което операторът чете като "стъпката не е минавала"',
        )
        extra = rows['hr.attendance.extra']
        self.assertEqual(extra['status'], 'skipped')
        self.assertNotEqual(
            extra['status'], 'error',
            'Версия, която не води такива данни, не е повреда',
        )
        self.assertTrue(extra['error'], 'Пропускът е без обяснена причина')
