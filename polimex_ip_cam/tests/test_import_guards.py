# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'ipcam_guards')
class TestImportGuards(TransactionCase):
    """Пренасяне на данни не бива да пипа работеща камера.

    Бизнес твърдение (собственик, 2026-08-13): когато прехвърляме системата на
    нов сървър, камерите на обекта продължават да работят. Никой не им праща
    команди, докато трае прехвърлянето, и никой не им подменя настройките.
    Обектът е под охрана през цялото време на миграцията.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plate_type = cls.env.ref('hr_rfid.hr_rfid_card_type_8')
        cls.partner = cls.env['res.partner'].create({'name': 'Шофьор'})
        cls.camera = cls.env['cctv.camera'].with_context(
            no_hardware_commands=True,
        ).create({
            'name': 'Порта',
            'ip_address': '10.0.0.9',
            'brand': 'hikvision',
        })
        cls.card = cls.env['hr.rfid.card'].create({
            'number': 'CA1234AB',
            'card_type': cls.plate_type.id,
            'contact_id': cls.partner.id,
        })

    def _commands(self):
        return self.env['cctv.camera.command'].search_count([])

    def test_import_creates_no_camera_commands(self):
        """Под пренос не тръгва нито една команда към камерата."""
        before = self._commands()
        self.env['cctv.camera.rfid.rel'].with_context(
            no_hardware_commands=True,
        ).create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        self.assertEqual(
            self._commands(), before,
            "Пренасянето на номер е поставило команда в опашката на камерата",
        )

    def test_import_removal_creates_no_commands(self):
        """Махането на връзка под пренос също мълчи."""
        rel = self.env['cctv.camera.rfid.rel'].with_context(
            no_hardware_commands=True,
        ).create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        before = self._commands()
        rel.with_context(no_hardware_commands=True).unlink()
        self.assertEqual(
            self._commands(), before,
            "Махането на номер е поставило команда в опашката на камерата",
        )

    def test_import_does_not_fabricate_readers(self):
        """Пренесена камера не си измисля четци и врата.

        Четците и вратата идват от източника със своя произход. Ако камерата
        ги произведе сама, в целта стоят два комплекта и никой не знае кой е
        истинският.
        """
        camera = self.env['cctv.camera'].with_context(
            no_hardware_commands=True,
        ).create({
            'name': 'Служебен вход',
            'ip_address': '10.0.0.10',
            'brand': 'hikvision',
        })
        self.assertFalse(
            camera.reader_ids,
            "Пренесената камера е произвела четци без произход",
        )

    def test_card_door_link_does_not_reach_the_camera_under_import(self):
        """Правото карта-врата под пренос не се огледалва към камерата.

        Иначе преносът произвежда връзка номер-камера без произход, която после
        се сблъсква с пренесената от източника.
        """
        reader = self.env['hr.rfid.reader'].create({
            'name': 'Четец', 'reader_type': '0', 'mode': '01', 'number': 1,
            'camera_id': self.camera.id,
        })
        door = self.env['hr.rfid.door'].create({
            'name': 'Врата', 'number': 1,
            'card_type': self.plate_type.id,
            'reader_ids': [(4, reader.id)],
        })
        schedule = self.env['hr.rfid.time.schedule'].search([], limit=1, order='number')
        # A door only accepts card rights once it belongs to an access group
        # (hr_rfid_door.py:862-866).
        self.env['hr.rfid.access.group'].create({
            'name': 'Достъп до портата',
            'door_ids': [(0, 0, {
                'door_id': door.id, 'time_schedule_id': schedule.id,
            })],
        })
        before_rels = self.env['cctv.camera.rfid.rel'].search_count([])
        self.env['hr.rfid.card.door.rel'].with_context(
            no_hardware_commands=True,
        ).create({
            'card_id': self.card.id,
            'door_id': door.id,
            'time_schedule_id': schedule.id,
        })
        self.assertEqual(
            self.env['cctv.camera.rfid.rel'].search_count([]), before_rels,
            "Преносът е произвел връзка номер-камера без произход",
        )

    def test_normal_use_still_sends_commands(self):
        """Без пренос всичко работи както преди.

        Гардът изключва разговора с желязото само докато трае преносът. Ако
        изключеше и обикновената работа, охраната би останала без камери.
        """
        before = self._commands()
        self.env['cctv.camera.rfid.rel'].create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        self.assertGreater(
            self._commands(), before,
            "Обикновеното добавяне на номер вече не стига до камерата",
        )
