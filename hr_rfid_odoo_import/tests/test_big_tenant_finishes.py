# -*- coding: utf-8 -*-
"""Голям наемател СТИГА до края - прочитът продължава оттам, докъдето е стигнал.

Бизнес твърдение (собственик, 2026-08-17, при пренасянето на облака с 27
фирми): "прехвърли ми тези бази" - тоест прехвърлянето трябва да ЗАВЪРШИ и
върху най-голямата от тях, а не да върви безкрайно.

Измерено на живо преди поправката, на облака с 27 фирми (6 176 служителя):
фазата "Хора" четеше от началото при всеки пас, времето ѝ свършваше на същото
място и целта остана с 1 001 служителя завинаги - при това с протокол, който
не казваше нищо тревожно. Същото важеше за 200 004 температурни отчета,
280 046 вендинг реда и 6 625 продажби на услуги: всяка таблица, по-голяма от
един пас, спираше прехвърлянето на място.

Затова тестът е за ДВЕ неща, които вървят заедно:
  * прочитът помни докъде е стигнал (иначе прогонът не завършва),
  * редът в протокола брои целия прогон (иначе завършилият прогон докладва
    "0 внесени" - редът, за който собственикът вече пита веднъж).
"""

import json

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.people_importer import PeopleImporter
from .test_run_totals_survive_the_passes import _PagedSource


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_totals')
class TestBigTenantFinishes(TransactionCase):
    """Източник с повече хора, отколкото един пас успява да прочете."""

    #: Толкова, че да са нужни няколко паса при страница от _PagedSource.PAGE.
    PEOPLE = 2500

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Big Tenant'})
        cls.company_map = {101: cls.company.id}

    def _employees(self):
        return [
            {'id': i, 'name': 'Служител %s' % i, 'company_id': 101,
             'active': True}
            for i in range(1, self.PEOPLE + 1)
        ]

    def _partners(self):
        # Всеки втори виси на предишния - родителят е с ПО-ГОЛЯМ номер, тоест
        # попада в СЛЕДВАЩ срез. Точно връзката, която срязването губи.
        rows = []
        for i in range(1, 21):
            rec = {'id': i, 'name': 'Контакт %s' % i, 'company_id': 101,
                   'active': True}
            if i % 2:
                rec['parent_id'] = [i + 1, 'Контакт %s' % (i + 1)]
            rows.append(rec)
        return rows

    def _source(self, data, previous=None):
        src = _PagedSource(self.env, dict(self.company_map),
                           {'import_people': True, 'import_all_employees': True,
                            'import_all_partners': True}, data)
        if previous is not None:
            # Нов пас: паметта е празна, пренася се само записаното на прогона.
            src.read_cursors = json.loads(json.dumps(previous.read_cursors))
            src.step_totals = json.loads(json.dumps(previous.step_totals))
        return src

    def test_every_person_arrives_however_many_passes_it_takes(self):
        data = {'hr.employee': self._employees(), 'res.partner': []}
        source, rows, passes = None, [], 0
        while passes < 20:
            source = self._source(data, previous=source)
            phase = PeopleImporter(source)
            phase._import_employees()
            rows = phase.results
            passes += 1
            if source.read_cursors.get('people:hr.employee') == source.CURSOR_FINISHED:
                break

        arrived = self.env['hr.employee'].with_context(
            active_test=False).search_count([('company_id', '=', self.company.id)])
        self.assertEqual(
            arrived, self.PEOPLE,
            'Прехвърлянето спря на %s от %s души: прочитът започва отначало '
            'при всеки пас, значи голям наемател никога не минава' % (
                arrived, self.PEOPLE))
        self.assertGreater(
            passes, 1,
            'Тестът не е доказал нищо - източникът е минал в един пас, а '
            'дефектът се вижда само когато пасовете са няколко')
        self.assertEqual(
            (rows[0]['source_count'], rows[0]['imported_count']),
            (self.PEOPLE, self.PEOPLE),
            'Протоколът показва среза на последния пас вместо целия прогон')

    def test_a_finished_read_is_not_read_again(self):
        """Втори прогон по същия курсор не пипа източника повторно."""
        data = {'hr.employee': self._employees()[:5], 'res.partner': []}
        source = self._source(data)
        PeopleImporter(source)._import_employees()
        self.assertEqual(source.read_cursors.get('people:hr.employee'),
                         source.CURSOR_FINISHED)

        again = self._source(data, previous=source)
        phase = PeopleImporter(again)
        phase._import_employees()
        self.assertEqual(
            phase.results[0]['imported_count'], 5,
            'Приключил прочит трябва да докладва работата на прогона, а не '
            'нулата на собствения си празен срез')

    def test_a_contact_finds_its_parent_in_a_later_slice(self):
        """Родителят идва в следващ срез - връзката пак се получава."""
        data = {'res.partner': self._partners(), 'hr.employee': []}
        source, phase = None, None
        for _ in range(10):
            source = self._source(data, previous=source)
            phase = PeopleImporter(source)
            phase._import_partners()
            if source.read_cursors.get('people:res.partner') == source.CURSOR_FINISHED:
                break

        Partner = self.env['res.partner'].with_context(active_test=False)
        children = Partner.search([('company_id', '=', self.company.id),
                                   ('name', '=', 'Контакт 1')])
        self.assertTrue(children, 'контактът изобщо не пристигна')
        self.assertEqual(
            children[0].parent_id.name, 'Контакт 2',
            'Контакт, чийто родител е в по-късен срез, остана без родител - '
            'при срязан прочит връзката се губи безшумно')
