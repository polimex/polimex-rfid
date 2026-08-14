# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
    _target_available, phase_plan, registry, source_probe_modules,
)


@tagged('post_install', '-at_install', 'rfid_import_registry')
class TestPhaseRegistry(TransactionCase):
    """Пренасянето казва какво пропуска и защо.

    Бизнес твърдение (собственик, 2026-08-13): операторът не бива да открива
    липсващи данни седмица по-късно. Всичко, което не е пренесено, стои в
    протокола с причина, разбираема без да се чете код.
    """

    def _names(self):
        return [p.NAME for p in registry()]

    def _all_options(self):
        opts = {}
        for cls in registry():
            if cls.OPTION:
                opts[cls.OPTION] = True
            for o in cls.OPTION_ANY:
                opts[o] = True
        return opts

    def test_zones_come_after_people(self):
        """Зоните се пълнят с хора, значи хората идват първи.

        Обратният ред записва празни списъци с членство и никой не забелязва -
        поправят се чак ако някой пусне прехвърлянето втори път.
        """
        names = self._names()
        self.assertIn('People', names)
        self.assertIn('Zones', names)
        self.assertGreater(
            names.index('Zones'), names.index('People'),
            "Зоните тръгват преди хората и ще останат без членове",
        )

    def test_every_phase_has_an_identity(self):
        """Всяка фаза има име и етикет - иначе протоколът е нечетим."""
        for cls in registry():
            self.assertTrue(cls.PHASE_ID, "%s няма етикет" % cls.__name__)
            self.assertTrue(cls.NAME, "%s няма име" % cls.__name__)
            self.assertTrue(cls.REQUIRES_TARGET,
                            "%s не казва какво му трябва" % cls.__name__)

    def test_missing_feature_is_reported_not_silent(self):
        """Липсваща функционалност в източника се отчита с причина."""
        plan = phase_plan(self.env, self._all_options(), source_modules=set())
        self.assertEqual(len(plan), len(registry()))
        skipped = [(cls, reason) for cls, reason in plan if reason]
        self.assertTrue(skipped, "Нищо не е отчетено като пропуснато")
        for cls, reason in skipped:
            self.assertTrue(
                (reason or '').strip(),
                "Фаза %s е пропусната, без да казва защо" % cls.NAME,
            )

    def test_reason_is_a_sentence_for_a_person(self):
        """Причината е изречение, не вътрешно име."""
        plan = phase_plan(self.env, self._all_options(), source_modules=set())
        for cls, reason in plan:
            if not reason:
                continue
            self.assertNotIn('_', reason,
                             "Причината съдържа вътрешно име: %s" % reason)

    def test_abstract_model_does_not_count_as_available(self):
        """Модел без собствена таблица не минава за налична функционалност."""
        self.assertFalse(_target_available(self.env, 'hr.rfid.access.group.rel'))

    def test_model_without_the_needed_column_does_not_count(self):
        """Наличен модел без нужната колона също не минава."""
        self.assertFalse(
            _target_available(self.env, ('res.partner', 'no_such_field_here')))
        self.assertTrue(_target_available(self.env, ('res.partner', 'name')))
        self.assertFalse(_target_available(self.env, 'no.such.model.at.all'))

    def test_progress_is_monotonic_and_complete(self):
        """Лентата расте и стига до края."""
        total = sum(p.WEIGHT for p in registry())
        self.assertGreater(total, 0)
        acc, last = 0, 0.0
        for p in registry():
            self.assertGreater(p.WEIGHT, 0, "%s тежи нула" % p.NAME)
            acc += p.WEIGHT
            pct = acc * 100.0 / total
            self.assertGreaterEqual(pct, last)
            last = pct
        self.assertAlmostEqual(last, 100.0, places=6)

    def test_probe_list_is_derived_from_the_phases(self):
        """Списъкът, който питаме източника, идва от фазите.

        Държан отделно, той изостава при всяко добавяне на фаза - точно така
        камерите изобщо не бяха потърсени.
        """
        probed = set(source_probe_modules())
        declared = {m for cls in registry() for m in cls.REQUIRES_SOURCE}
        self.assertEqual(probed, declared)

    def test_plan_needs_no_network(self):
        """Планът се смята без връзка към източника и без запис в базата."""
        plan = phase_plan(self.env, {'import_people': True},
                          source_modules={'hr_rfid'})
        self.assertEqual(len(plan), len(registry()))
        by_name = {cls.NAME: reason for cls, reason in plan}
        self.assertIsNone(by_name['People'], "Хората би трябвало да са изпълними")
        self.assertTrue(by_name['Vending'],
                        "Вендингът няма как да е изпълним без своята функционалност")

    def test_composite_phase_is_skipped_when_nothing_of_it_is_wanted(self):
        """Фаза с няколко вида данни не тръгва, ако никой от тях не е избран.

        Иначе тя минава, не прави нищо и се отчита като изпълнена - което
        изглежда точно като "нямаше данни".
        """
        plan = phase_plan(self.env, {'import_hardware': True},
                          source_modules={'hr_rfid'})
        by_name = {cls.NAME: reason for cls, reason in plan}
        self.assertTrue(by_name['Events'],
                        "Събитията тръгват, без да е поискан нито един вид")
