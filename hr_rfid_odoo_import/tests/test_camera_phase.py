# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_odoo_import.models.importers.camera_importer import (
    KNOWN_LIST_CATEGORIES, SAFE_LIST_CATEGORY, CameraImporter,
)
from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
    phase_plan, registry,
)


@tagged('post_install', '-at_install', 'rfid_import_cameras')
class TestCameraPhase(TransactionCase):
    """Камерите пристигат заедно с номерата, които пазят.

    Бизнес твърдение (собственик, 2026-08-13): при преместване на системата
    камерите на обекта трябва да са там и след това - разпознати по същия
    сериен номер, със същите номера в белия и черния списък. Досега помощникът
    изобщо не питаше за тях и прогонът отчиташе успех.
    """

    def _names(self):
        return [p.NAME for p in registry()]

    def test_cameras_are_part_of_the_transfer(self):
        """Камерите изобщо са в обхвата."""
        self.assertIn(
            'Cameras', self._names(),
            "Помощникът пак не знае за камери",
        )

    def test_cameras_come_after_the_access_rights(self):
        """Камерите идват след правата.

        Раздаването на права карта-врата минава по път, който огледалва към
        списъците на камерата. Ако камерите дойдат преди това, огледалото
        произвежда връзки без произход, които после се сблъскват с пренесените.
        """
        names = self._names()
        self.assertGreater(
            names.index('Cameras'), names.index('Access Control'),
        )

    def test_the_camera_is_recognised_after_the_move(self):
        """Пренасят се и полетата, по които камерата се разпознава.

        Входящите събития се насочват към камерата по нейния сериен номер;
        без тях камерата спира да приема събития и това се вижда чак когато
        някой мине през бариерата.
        """
        for field in ('serial_number', 'sub_serial_number'):
            self.assertIn(
                field, CameraImporter.IDENTITY_FIELDS,
                "Камерата ще пристигне без начин да бъде разпозната",
            )

    def test_unknown_bucket_never_becomes_permission(self):
        """Номер от непознат списък отива в забраняващия, не в разрешаващия.

        Стари инсталации носят кофи извън двете, които уредът познава. Да ги
        приемем за бял списък значи да отворим достъп, който преди е бил
        отказан - единствената грешка тук, която пуска автомобил през бариера.
        """
        self.assertEqual(SAFE_LIST_CATEGORY, 'blacklist')
        self.assertNotIn(SAFE_LIST_CATEGORY, ('whitelist',))
        self.assertEqual(set(KNOWN_LIST_CATEGORIES), {'whitelist', 'blacklist'})

    def test_camera_phase_is_offered_only_when_the_source_has_cameras(self):
        """Не се предлага на клиент без камери, и казва защо."""
        plan = phase_plan(self.env, {'import_cameras': True},
                          source_modules={'hr_rfid'})
        reason = {cls.NAME: r for cls, r in plan}['Cameras']
        self.assertTrue(reason, "Камерна фаза се предлага при източник без камери")
        self.assertNotIn('_', reason, "Причината съдържа вътрешно име")

    def test_camera_phase_runs_when_both_sides_have_cameras(self):
        """При налични камери от двете страни фазата е изпълнима."""
        plan = phase_plan(self.env, {'import_cameras': True},
                          source_modules={'hr_rfid', 'polimex_ip_cam'})
        reason = {cls.NAME: r for cls, r in plan}['Cameras']
        if 'cctv.camera' in self.env:
            self.assertIsNone(
                reason, "Камерна фаза е пропусната, макар всичко да е налице")
        else:
            self.assertTrue(reason)

    def test_camera_phase_needs_the_reader_link(self):
        """Фазата иска и връзката четец-камера, не само самия модел.

        Наличието на модел не значи, че схемата му приема камерни четци;
        липсва ли колоната, вмъкването пада по средата вместо преди началото.
        """
        self.assertIn(
            ('hr.rfid.reader', 'camera_id'), CameraImporter.REQUIRES_TARGET,
        )


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_cameras')
class TestNotificationAddressFollowsTheServer(TransactionCase):
    """Известяването сочи сървъра, който РАБОТИ, не онзи, който беше.

    server_setup пътува дословно и редът ipAddress= назовава СТАРИЯ сървър -
    целият мигриран парк уведомяваше машина, която вече не отговаря, и
    единственият видим знак беше тихо остаряващ heartbeat (собственикът:
    "камерата не е настроена към ИП от което я диагностицираме")."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Retarget Tenant'})
        cls.company_map = {101: cls.company.id}

    def _import(self, server_setup):
        from unittest.mock import patch
        from .test_company_scope import _FakeSource
        from ..models.importers.camera_importer import CameraImporter
        if 'cctv.camera' not in self.env:
            self.skipTest('камерите не са част от тази инсталация')
        base = _FakeSource(self.env, dict(self.company_map), {}, {
            'cctv.camera': [{
                'id': 301, 'name': 'Пренасочена', 'company_id': [101, 'X'],
                'ip_address': '10.7.7.7', 'username': 'admin',
                'password': 'x', 'brand': 'hikvision', 'tz': 'Europe/Sofia',
                'server_setup': server_setup,
            }],
        })
        with patch('odoo.addons.hr_rfid_odoo_import.models.importers.'
                   'camera_importer.get_local_ip',
                   return_value='192.168.0.99'):
            importer = CameraImporter(base)
            importer._import_cameras()
        camera = self.env['cctv.camera'].browse(
            base._map_m2o('cctv.camera', 301))
        return camera, importer.results[-1]

    def test_the_old_servers_address_is_replaced_and_said(self):
        camera, row = self._import('ipAddress=192.168.0.190\nportNo=8069')
        self.assertIn('ipAddress=192.168.0.99', camera.server_setup,
                      'известяването остана насочено към стария сървър')
        self.assertIn('portNo=8069', camera.server_setup,
                      'портът е операторски избор - не се пипа')
        self.assertNotIn('192.168.0.190', camera.server_setup)
        self.assertIn('192.168.0.99', row['error'],
                      'протоколът не казва, че адресът е пренасочен')

    def test_an_address_already_here_travels_untouched_and_unmentioned(self):
        camera, row = self._import('ipAddress=192.168.0.99\nportNo=80')
        self.assertIn('ipAddress=192.168.0.99', camera.server_setup)
        self.assertFalse(row['error'],
                         'протоколът обявява пренасочване, каквото няма')
