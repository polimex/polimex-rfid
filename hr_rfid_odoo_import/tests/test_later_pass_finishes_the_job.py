# -*- coding: utf-8 -*-
"""Работата, която идва СЛЕД първата стъпка, не изчезва между двата пъти.

Бизнес твърдение (собственик, 2026-08-14): прехвърлянето може да се пуска
неограничен брой пъти и всеки път да си довършва работата.

Голямото прехвърляне не се побира в един ход - то върви на пасове. Всеки пас
започва наново и помни само кои стъпки вече са минали. Стъпките, които ДОПЪЛВАТ
вече пренесени записи (кой отдел с коя група за достъп е, кой уред на кой обект
стои, кой човек с какъв кредит е), в следващия пас не намираха нищо и не правеха
нищо - без нито един ред в протокола. Отделите оставаха без група за достъп,
уредите без обект, хората без кредит, а прогонът изглеждаше чист.

Второто твърдение е за зоните: човек, добавен в зона ТУК след прехвърлянето,
трябва да остане в нея и след следващото прехвърляне. Списъкът се допълва, не
се подменя.
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.access_importer import AccessImporter
from ..models.importers.core_importer import ZoneImporter
from ..models.importers.site_importer import SiteImporter
from ..models.importers.vending_importer import VendingImporter
from .test_company_scope import _FakeSource


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_later_pass')
class TestALaterPassFinishesTheJob(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Later Pass Tenant'})
        cls.company_map = {101: cls.company.id}

    def _source(self, data, **options):
        opts = {'import_hardware': True, 'import_access': True,
                'import_sites': True, 'import_vending': True}
        opts.update(options)
        return _FakeSource(self.env, dict(self.company_map), opts, data)

    def _remember(self, model, source_id, record):
        """Записва това, което ПРЕДИШНИЯТ пас вече е пренесъл."""
        self._source({}).link_existing(model, source_id, record.id)

    # ── Отдели: групата за достъп по подразбиране ──────────────

    def test_a_department_gets_its_access_group_in_a_later_pass(self):
        """Отделът получава групата си, дори стъпката да върви отделно.

        Отделите се пренасят в една стъпка, а групите им за достъп - в друга,
        много по-късно. Между двете прехвърлянето може да е спирало и да е
        продължило в нов ход, който не помни нищо от предишния.
        """
        group = self.env['hr.rfid.access.group'].create({
            'name': 'Later Pass AG', 'company_id': self.company.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Later Pass Dept', 'company_id': self.company.id,
        })
        self._remember('hr.rfid.access.group', 61, group)
        self._remember('hr.department', 501, department)

        # Нов пас: нищо не е останало в паметта от предишния.
        base = self._source({'hr.department': [{
            'id': 501,
            'hr_rfid_default_access_group': [61, 'Later Pass AG'],
            'hr_rfid_allowed_access_groups': [61],
        }]})
        self.assertFalse(base.id_map, 'новият пас започва с празна памет')
        AccessImporter(base)._department_second_pass()

        self.assertEqual(
            department.hr_rfid_default_access_group, group,
            'Отделът остана без група за достъп, защото стъпката е тръгнала '
            'в нов ход и не е намерила нищо в паметта',
        )

    def test_the_department_step_reports_a_line_when_it_did_nothing(self):
        """"Нямаше какво да се прави" и "не се изпълни" не бива да си приличат."""
        base = self._source({'hr.department': [
            {'id': 502, 'name': 'Без група', 'hr_rfid_default_access_group': False},
        ]})
        importer = AccessImporter(base)
        importer._department_second_pass()

        self.assertTrue(
            importer.results,
            'Стъпката мина без нито един ред в протокола - от него не личи '
            'дали изобщо се е изпълнила',
        )

    def test_the_department_step_reports_a_line_when_the_source_has_no_groups(self):
        """Същото и когато другата система изобщо не води такива групи."""
        base = self._source({'hr.department': [{'id': 503, 'name': 'Отдел'}]})
        importer = AccessImporter(base)
        importer._department_second_pass()

        self.assertTrue(importer.results, 'липсва ред в протокола')
        self.assertEqual(importer.results[0]['status'], 'skipped')

    # ── Обекти: уредът си намира мястото ──────────────────────

    def test_equipment_gets_its_site_in_a_later_pass(self):
        """Уредът получава обекта си, макар да е дошъл в предишен ход."""
        if 'hr.rfid.site' not in self.env:
            self.skipTest('обектите не са част от тази инсталация')
        site = self.env['hr.rfid.site'].create({
            'name': 'Later Pass Site', 'company_id': self.company.id,
            'make_access_group': False,
        })
        webstack = self.env['hr.rfid.webstack'].create({
            'name': 'Later Pass Stack', 'serial': '778899', 'key': '0000',
            'company_id': self.company.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
        })
        self._remember('hr.rfid.site', 71, site)
        self._remember('hr.rfid.webstack', 81, webstack)

        base = self._source({'hr.rfid.webstack': [
            {'id': 81, 'site_id': [71, 'Later Pass Site']},
        ]})
        self.assertFalse(base.id_map, 'новият пас започва с празна памет')
        SiteImporter(base)._link_sites_to_hardware()

        self.assertEqual(
            webstack.site_id, site,
            'Уредът остана без обект, защото стъпката е тръгнала в нов ход',
        )

    # ── Вендинг: кредитът на човека ───────────────────────────

    def test_a_persons_vending_balance_arrives_in_a_later_pass(self):
        """Кредитът за вендинг стига до човека и в следващия ход."""
        if 'hr_rfid_vending_balance' not in self.env['hr.employee']._fields:
            self.skipTest('вендингът не е част от тази инсталация')
        employee = self.env['hr.employee'].create({
            'name': 'Later Pass Person', 'company_id': self.company.id,
        })
        self._remember('hr.employee', 901, employee)

        base = self._source({'hr.employee': [
            {'id': 901, 'hr_rfid_vending_balance': 12.5},
        ]})
        self.assertFalse(base.id_map, 'новият пас започва с празна памет')
        importer = VendingImporter(base)
        importer._update_employee_vending_fields()

        self.assertEqual(
            employee.hr_rfid_vending_balance, 12.5,
            'Кредитът остана в другата система, защото стъпката е тръгнала '
            'в нов ход и не е намерила човека в паметта',
        )
        self.assertTrue(importer.results, 'липсва ред в протокола')


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_later_pass')
class TestZoneMembersAreAddedNotReplaced(TransactionCase):
    """Човек, вписан в зона ТУК, остава в нея и след следващото прехвърляне."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Zone Tenant'})
        cls.company_map = {101: cls.company.id}
        cls.transferred = cls.env['hr.employee'].create({
            'name': 'Дошъл с прехвърлянето', 'company_id': cls.company.id,
        })
        cls.added_here = cls.env['hr.employee'].create({
            'name': 'Вписан на място', 'company_id': cls.company.id,
        })

    def _run_transfer(self):
        base = _FakeSource(
            self.env, dict(self.company_map), {'import_hardware': True},
            {'hr.rfid.zone': [{
                'id': 31, 'name': 'Zone With Members',
                'company_id': [101, 'Zone Tenant'],
                'employee_ids': [900],
            }]},
        )
        base.id_map['hr.employee'] = {900: self.transferred.id}
        ZoneImporter(base).run(None)
        return self.env['hr.rfid.zone'].browse(
            base._map_m2o('hr.rfid.zone', 31))

    def test_someone_added_here_survives_the_next_transfer(self):
        zone = self._run_transfer()
        self.assertIn(self.transferred, zone.employee_ids)

        zone.write({'employee_ids': [(4, self.added_here.id)]})
        self._run_transfer()

        self.assertIn(
            self.added_here, zone.employee_ids,
            'Второто прехвърляне изхвърли човека, вписан в зоната тук - '
            'списъкът се подменя вместо да се допълва',
        )
        self.assertIn(
            self.transferred, zone.employee_ids,
            'Пренесеният член също трябва да е там - допълването не бива да '
            'изтрива това, което самото прехвърляне е донесло',
        )
