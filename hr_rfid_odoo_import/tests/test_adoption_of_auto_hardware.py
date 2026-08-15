# -*- coding: utf-8 -*-
"""Вносът осиновява хардуера, който автоматиката на целта е родила.

Предупреждение на собственика (2026-08-15): "внимавай със създаването на
хардуера - има автоматични алгоритми, които го създават, и ръчното му
създаване трябва да е доста прецизирано."

Модулът за достъп сам създава хардуер: heartbeat провизира контролери, F0
строи вратите и четците им ПОЗИЦИОННО, камерата си фабрикува врата. Когато
живото желязо говори с целта преди вноса, тези записи съществуват БЕЗ
transfer идентичност - и създаването на собствено копие или удря уникално
ограничение (контролери), или ражда тихи близнаци (врати и четци нямат
ограничение; четири камерни врати на жива миграция направиха точно това).

Осиновяването е по ключа на САМАТА автоматика - (webstack, ctrl_id) за
контролер, (контролер, номер) за врата и четец - никога по име.
"""
from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import (
    EXTERNAL_ID_MODULE, BaseImporter,
)
from .test_company_scope import _FakeSource


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_adopt')
class TestImportAdoptsAutomationBornHardware(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Хардуер, "роден от автоматиката": създаден направо на целта, без
        # transfer идентичност - както го оставя heartbeat + F0.
        cls.ws = cls.env['hr.rfid.webstack'].create({
            'name': 'Adopt WS', 'serial': '777001', 'key': '9999',
            'hw_version': '100.1', 'version': '1.44', 'active': True,
            'tz': 'Europe/Sofia', 'company_id': cls.company.id})
        cls.ctrl = cls.env['hr.rfid.ctrl'].create({
            'name': 'Controller', 'ctrl_id': 3, 'serial_number': '7770',
            'webstack_id': cls.ws.id, 'hw_version': '9', 'sw_version': '740',
            'max_cards_count': 10, 'max_events_count': 10, 'readers': 2,
            'mode': 2, 'inputs': 0, 'outputs': 0, 'input_states': 0,
            'output_states': 0, 'alarm_lines': 0, 'io_table_lines': 0,
            'io_table': ''})
        card_type = cls.env.ref('hr_rfid.hr_rfid_card_type_def')
        cls.door = cls.env['hr.rfid.door'].with_context(
            no_hardware_commands=True).create({
                'name': 'F0 Door', 'number': 2,
                'controller_id': cls.ctrl.id, 'card_type': card_type.id})

    def _importer(self):
        return _FakeSource(
            self.env, {901: self.company.id}, {'import_hardware': True}, {})

    def test_a_provisioned_controller_is_adopted_not_duplicated(self):
        """Контролер от heartbeat-а става съответникът на source №55 -
        по (webstack, ctrl_id), без втори запис и без отказ от UNIQUE."""
        imp = self._importer()
        imp._set_target_id('hr.rfid.webstack', 40, self.ws.id)
        before = self.env['hr.rfid.ctrl'].search_count([])

        adopted = imp.adopt_existing('hr.rfid.ctrl', 55, self.ctrl)

        self.assertTrue(adopted)
        self.assertEqual(self.env['hr.rfid.ctrl'].search_count([]), before,
                         "Осиновяването не създава втори контролер")
        self.assertEqual(imp._map_m2o('hr.rfid.ctrl', 55), self.ctrl.id,
                         "Съответствието вече минава през идентичността")
        imd = self.env['ir.model.data'].search([
            ('module', '=', EXTERNAL_ID_MODULE),
            ('model', '=', 'hr.rfid.ctrl'), ('res_id', '=', self.ctrl.id)])
        self.assertEqual(len(imd), 1, "Идентичността е записана точно веднъж")

    def test_a_record_of_another_source_is_a_conflict_not_a_merge(self):
        """Запис, който вече принадлежи на ДРУГ запис от източника, не се
        сваля от него - фалшивото сливане е по-лошо от пропуска."""
        imp = self._importer()
        self.assertTrue(imp.adopt_existing('hr.rfid.door', 5, self.door))

        stolen = imp.adopt_existing('hr.rfid.door', 6, self.door)

        self.assertFalse(stolen, "Втори source запис не открадва осиновения")
        result = imp._make_result('hr.rfid.door', 1, 0, 0, 1)
        self.assertTrue(result['error'],
                        "Отказът от сливане се казва в протокола")

    def test_adoption_is_idempotent_across_runs(self):
        """Втори прогон намира осиновеното по идентичност - нула нови записи,
        нула нови идентичности."""
        first = self._importer()
        self.assertTrue(first.adopt_existing('hr.rfid.door', 5, self.door))
        # Нов процес: нов importer, празна памет - остава само trajno-то.
        second = self._importer()
        self.assertEqual(second._map_m2o('hr.rfid.door', 5), self.door.id)
        self.assertTrue(second.adopt_existing('hr.rfid.door', 5, self.door),
                        "Повторното осиновяване на същия е разпознаване")
        imd = self.env['ir.model.data'].search_count([
            ('module', '=', EXTERNAL_ID_MODULE),
            ('model', '=', 'hr.rfid.door'), ('res_id', '=', self.door.id)])
        self.assertEqual(imd, 1)
