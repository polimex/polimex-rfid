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
