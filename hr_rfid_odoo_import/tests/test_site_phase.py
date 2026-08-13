# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
    phase_plan, registry,
)
from odoo.addons.hr_rfid_odoo_import.models.importers.site_importer import (
    SiteImporter,
)


@tagged('post_install', '-at_install', 'rfid_import_sites')
class TestSitePhase(TransactionCase):
    """Обектите идват с дървото си, а не с двойни групи.

    Бизнес твърдение (собственик, 2026-08-13): след преместването охраната
    вижда същите обекти, в същата подредба, всеки с една група за достъп -
    не две - и контактите знаят на кой обект принадлежат.
    """

    def _names(self):
        return [p.NAME for p in registry()]

    def test_sites_are_part_of_the_transfer(self):
        self.assertIn('Sites', self._names(), "Обектите не са в обхвата")

    def test_sites_arrive_after_the_equipment(self):
        """Обектът държи оборудване - то трябва да съществува преди него."""
        names = self._names()
        self.assertGreater(names.index('Sites'), names.index('Core & Hardware'))

    def test_own_group_is_restored_after_the_real_groups(self):
        """Собствената група на обекта се включва последна.

        Включи ли се по-рано, обектът си построява група веднага и тя застава
        до онази, която идва от източника. Изтриването после е ръчно, защото
        модулът отказва да махне групата, докато обектът я иска.
        """
        names = self._names()
        self.assertGreater(
            names.index('Site Groups'), names.index('Access Control'),
            "Обектът ще си построи група преди истинската да е пристигнала",
        )

    def test_parent_always_comes_before_its_children(self):
        """Дървото се строи отгоре надолу.

        Записът на родителя след създаването не преизчислява групите на
        предците - вратите на децата просто не влизат в тях, без грешка.
        """
        records = [
            {'id': 3, 'parent_id': (2, 'Етаж 1')},
            {'id': 1, 'parent_id': False},
            {'id': 4, 'parent_id': (3, 'Стая 1')},
            {'id': 2, 'parent_id': (1, 'Сграда')},
        ]
        order = [r['id'] for r in SiteImporter._parent_first(records)]
        for child, parent in ((2, 1), (3, 2), (4, 3)):
            self.assertLess(
                order.index(parent), order.index(child),
                "Обект %s се създава преди родителя си %s" % (child, parent),
            )

    def test_a_site_without_a_parent_is_kept(self):
        """Обект от най-горно ниво не изпада от подредбата."""
        records = [{'id': 7, 'parent_id': False}]
        self.assertEqual(
            [r['id'] for r in SiteImporter._parent_first(records)], [7])

    def test_parent_outside_the_scope_does_not_lose_the_child(self):
        """Дете, чийто родител не е в обхвата, пак се пренася.

        Иначе цял клон изчезва мълчаливо, защото родителят му е на друга фирма.
        """
        records = [{'id': 9, 'parent_id': (99, 'Извън обхвата')}]
        self.assertEqual(
            [r['id'] for r in SiteImporter._parent_first(records)], [9])

    def test_sites_are_offered_only_when_the_source_has_them(self):
        """Не се предлага на клиент без обекти, и казва защо."""
        plan = phase_plan(self.env, {'import_sites': True},
                          source_modules={'hr_rfid'})
        reason = {cls.NAME: r for cls, r in plan}['Sites']
        self.assertTrue(reason, "Обектна фаза се предлага при източник без обекти")
        self.assertNotIn('_', reason, "Причината съдържа вътрешно име")
