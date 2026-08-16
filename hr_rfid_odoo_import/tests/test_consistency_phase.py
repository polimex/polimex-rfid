# -*- coding: utf-8 -*-
"""Финалният валидатор: целта гарантира за целостта си, поименно.

Бизнес твърдения (собственик, 2026-08-16, при живата загуба на събития):
1. "имаме ли накрая валидатор дали данните са консистентни?" - последната
   фаза проверява цялото, а не броя на парчетата.
2. Камера с празен списък четци губи всяко разпознаване - точно живият
   случай: четците бяха там, вързани по camera_id, а списъкът празен.
3. "контролерите също имат верига от модул през контролер, четец врати" -
   веригата на достъпа се проверява по всичките ѝ звена.
4. Нарушение се НАЗОВАВА (кой запис), не само се брои.
5. Пренесеният камерен парк получава списъците си от самия импорт - и
   повторен прогон ЛЕКУВА вече пренесена инсталация.
"""
from odoo.tests.common import TransactionCase, tagged

from ..models.importers.camera_importer import CameraImporter
from ..models.importers.consistency_importer import ConsistencyImporter
from ..models.importers.phase import registry
from .test_company_scope import _FakeSource


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_consistency')
class TestConsistencyPhase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Consistency Tenant'})
        cls.company_map = {101: cls.company.id}

    def _rows(self, data=None):
        base = _FakeSource(self.env, dict(self.company_map), {}, data or {})
        importer = ConsistencyImporter(base)
        importer.run(None)
        return {r['model']: r for r in importer.results}

    def _camera(self, name='Вход'):
        if 'cctv.camera' not in self.env:
            self.skipTest('камерите не са част от тази инсталация')
        return self.env['cctv.camera'].create({
            'name': name, 'ip_address': '10.0.0.9', 'username': 'admin',
            'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
            'company_id': self.company.id,
        })

    def test_the_check_is_the_last_phase(self):
        """Валидаторът гледа ЦЯЛОТО - значи върви след всичко останало."""
        self.assertEqual(registry()[-1].NAME, 'Consistency check')

    def test_a_clean_target_reports_every_check_green(self):
        rows = self._rows()
        self.assertTrue(rows, 'валидаторът не отчете нито една проверка')
        bad = {name: r for name, r in rows.items() if r['status'] != 'done'}
        self.assertFalse(bad, 'чиста цел, а проверки се оплакват: %s' % bad)

    def test_a_camera_with_an_empty_reader_list_is_named(self):
        """Живият случай: четците вързани по camera_id, списъкът празен.

        Създаването на камера авто-провизира четците И списъка - затова
        празният списък тук се прави изрично, точно каквото завари живият
        обект след преноса."""
        camera = self._camera('ВХОД ХАН БОГРОВ')
        camera.reader_ids = [(5, 0, 0)]
        row = [r for name, r in self._rows().items() if 'drop their events' in name]
        self.assertTrue(row, 'липсва проверката за камерните списъци')
        self.assertEqual(row[0]['status'], 'error')
        self.assertIn('ВХОД ХАН БОГРОВ', row[0]['error'],
                      'нарушителят не е назован - операторът няма къде да търси')

    def test_a_controller_behind_an_archived_module_is_named(self):
        """Архивиран модул скрива всичко под себе си от фирмените обхвати."""
        webstack = self.env['hr.rfid.webstack'].create({
            'name': 'Скрит модул', 'serial': '445566', 'key': '0000',
            'company_id': self.company.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
        })
        self.env['hr.rfid.ctrl'].create({
            'name': 'Контролер зад завесата', 'ctrl_id': 5,
            'webstack_id': webstack.id,
        })
        webstack.active = False
        row = [r for name, r in self._rows().items() if 'archived module' in name]
        self.assertTrue(row)
        self.assertEqual(row[0]['status'], 'error')
        self.assertIn('Контролер зад завесата', row[0]['error'])

    def test_the_transfer_itself_fills_the_camera_reader_list(self):
        """Импортът пълни списъка; повторен прогон лекува заварена дупка."""
        camera = self._camera('ИЗХОД ХАН БОГРОВ')
        reader = self.env['hr.rfid.reader'].search(
            [('camera_id', '=', camera.id)], limit=1)
        self.assertTrue(reader, 'камерата не е авто-провизирала четците си')
        camera.reader_ids = [(5, 0, 0)]
        self.assertFalse(camera.reader_ids, 'списъкът не се изпразни')
        base = _FakeSource(self.env, dict(self.company_map), {},
                           {'cctv.camera': []})
        base.id_map['cctv.camera'] = {901: camera.id}
        CameraImporter(base)._link_camera_readers()
        self.assertIn(reader, camera.reader_ids,
                      'списъкът на камерата остана празен - събитията ѝ ще '
                      'се губят точно както на живия обект')

    def test_every_violation_report_names_and_counts_agree(self):
        """Редът казва и броя, и имената - никога само едното."""
        self._camera('Безчетцова').reader_ids = [(5, 0, 0)]
        rows = [r for name, r in self._rows().items() if 'drop their events' in name]
        self.assertEqual(rows[0]['source_count'], 1)
        self.assertTrue(rows[0]['error'])
