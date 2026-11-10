# -*- coding: utf-8 -*-
"""Контролът на собственика: другата система има ли това, което имаме и ние?

Бизнес твърдение (собственик, 2026-08-17, след двуизточниковото прехвърляне):
всяка фаза брои КАКВОТО Е ПРЕНЕСЛА, а никоя не отговаря на въпроса, който
собственикът задава - "тази система държи ли вече това, което държи другата,
фирма по фирма". Затова накрая операторът пуска една проверка, която пита
ИЗТОЧНИКА за неговите числа и ги сравнява с пристигналото тук.

Мерено на живо (числата са доказателството, не украсата):

* един наемател загуби ВСИЧКИТЕ си 400 карти (стъпката гърмеше на първия
  неоткриваем притежател), а всеки друг ред в протокола изглеждаше чист;
* 152 469 дневни обобщения на работното време останаха отвъд БЕЗ НИТО ЕДИН
  ред в протокола - изключената настройка не оставя ред, а липсващият ред се
  чете като "такива данни няма";
* страницата за преглед обеща 6 395 карти и 5 984 души, а пристигнаха 8 505 и
  6 176 - защото броеше по друга ос (без архивираните), а прехвърлянето чете и
  архивираните;
* 19 карти се оказаха на човек от ДРУГА фирма (безфирмен контакт пристигна в
  фирмата по подразбиране на целта).

Проверката е трябвало да съществува - днешните дефекти бяха намерени именно с
такова ръчно броене от двете страни. Тези тестове я заключват, за да не се
наложи да се пише отново.

Ключово за доверието: проверка, която НЕ Е МИНАЛА, изглежда точно като
проверка, която е съгласна. Затова всеки случай тук има и отрицателен близнак -
какво НЕ бива да се случва: нула вместо отказ, чист ред вместо мълчание, чужди
записи вместо пренесените, "done" вместо "не можах да сравня".
"""

import json
import time
import xmlrpc.client
from datetime import datetime

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.consistency_importer import ConsistencyImporter
from ..models.importers.phase import registry
from ..models.importers.reconcile_importer import (
    CARRYABLE_LEAVE_STATES, KIND_LABELS, RECONCILED, ReconcileImporter,
)
from .test_older_source_missing_models import _OlderSource


def at_the_source(company, count=1, active=True, state=None, **values):
    """`count` записа на този наемател в ДРУГАТА система.

    Фикстурата е малка, доказателството - живо: два реда тук стоят за 400-те
    карти на един наемател или за 152 469-те дневни обобщения. Размерът не е
    твърдението; твърдението е в поведението на контрола.

    ``values`` са полетата, по които проверката пита отделно (човекът на
    присъствието: `employee_id` с номера му в другата система).
    """
    return [dict({'company': company, 'active': active, 'state': state}, **values)
            for _ in range(count)]


def _option_names(option):
    """Настройката на вида като списък - един вид може да се иска с няколко."""
    return list(option) if isinstance(option, tuple) else [option]


#: Пълен пренос: всичко, което проверката сверява, е отметнато.
EVERYTHING_CARRIED = {name: True for entry in RECONCILED
                      for name in _option_names(entry[2])}


class _PerTenantCountProxy:
    """RPC двойник, който БРОИ - и брои архивираните само когато го помолят.

    Умишлено строг за архивираните: истинският източник не просто скрива
    архивирания запис, а собственото му правило за достъп (верижна фирмена
    проверка) ОТКАЗВА записа под архивиран модул, ако контекстът не е
    `active_test=False`. Затова двойникът дава архивираните само по контекста
    или когато самото условие назовава `active` - както броячът на
    прехвърлянето прави винаги. Броене, което заобикаля този брояч, тук връща
    по-малко число, точно както страницата за преглед обеща 6 395 при 8 505.
    """

    def __init__(self, counts):
        #: {модел: [{'company': 101, 'active': True, 'state': 'validate'}, ...]}
        self.counts = counts
        self.calls = []
        #: Модели, за които другата система отказва да брои изобщо.
        self.refuse = set()
        #: Модели, за които отказва само въпроса „чии са“ (`not in`).
        self.refuse_owner_question = set()
        #: Условия, които двойникът не може да изпълни честно. Проверката
        #: поглъща всяка грешка при броенето като „не може да се каже“, затова
        #: тук те се записват и тестът ги проверява сам след прогона.
        self.fixture_errors = []

    def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
        kwargs = kwargs or {}
        domain = list(args[0]) if args else []
        self.calls.append({
            'model': model, 'method': method, 'domain': domain,
            'context': dict(kwargs.get('context') or {}),
        })
        if method != 'search_count':
            return 0
        if model in self.refuse:
            raise xmlrpc.client.Fault(
                2, "You are not allowed to access '%s' records." % model)
        if model in self.refuse_owner_question and any(
                isinstance(leaf, (list, tuple)) and len(leaf) == 3
                and leaf[1] == 'not in' for leaf in domain):
            raise xmlrpc.client.Fault(2, "the request is too large")
        return len(self._matching(model, domain,
                                  kwargs.get('context') or {}))

    def _matching(self, model, domain, context):
        wants_archived = context.get('active_test') is False
        company = states = actives = None
        others = []
        for leaf in domain:
            if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
                continue
            name, op, value = leaf
            if str(name).endswith('company_id'):
                company = value
            elif name == 'state':
                states = list(value) if isinstance(value, (list, tuple)) else [value]
            elif name == 'active' and op == 'in':
                # As on a real server: a domain that names `active` itself is
                # not narrowed by active_test.
                actives = list(value)
            elif op == 'not in' or (op in ('!=', '=') and value is False):
                if op == 'not in' and not any(
                        name in row for row in self.counts.get(model, [])):
                    # A fixture that forgot the owner would make every row
                    # "an owner who is not here" - and the test pass for it.
                    self._refuse_the_fixture(
                        'никой ред на %s няма поле %s - фикстурата не казва '
                        'чий е записът' % (model, name))
                others.append((name, op, value))
            else:
                self._refuse_the_fixture(
                    'двойникът не познава условието %r - добави го, вместо '
                    'да го пропуска мълчаливо' % (leaf,))
        out = []
        for row in self.counts.get(model, []):
            if company is not None and row.get('company') != company:
                continue
            if states is not None and row.get('state') not in states:
                continue
            if actives is not None:
                if row.get('active', True) not in actives:
                    continue
            elif not wants_archived and not row.get('active', True):
                continue
            if not all(self._holds(row.get(name) or False, op, value)
                       for name, op, value in others):
                continue
            out.append(row)
        return out

    def _refuse_the_fixture(self, message):
        self.fixture_errors.append(message)
        raise AssertionError(message)

    @staticmethod
    def _holds(field_value, op, value):
        """A leaf on a many2one, as the server reads it (False = no link)."""
        if op == 'not in':
            return field_value not in value
        if op == '!=':
            return field_value != value
        return field_value == value

    def companies_asked_about(self, model):
        return [call['domain'] for call in self.calls
                if call['model'] == model and call['method'] == 'search_count']


class _CountingSource(_OlderSource):
    """Източник, който отговаря на "колко имаш за тази фирма".

    Стъпва върху `_OlderSource`, защото сървър БЕЗ такъв модел не връща празен
    списък, а вдига грешка (мерено срещу живата 14-та версия). Двойник, който
    мълчаливо връща нищо, не доказва нищо за този случай - той изглежда зелен и
    при повреден контрол.
    """

    def __init__(self, env, company_map, options, counts, extra_data=None):
        # Всеки броен модел съществува там и има `active` - точно шевът, на
        # който преглеждащата страница се разминаваше с прехвърлянето.
        data = {model: [{'id': 0, 'active': True}] for model in counts}
        data.update(extra_data or {})
        super().__init__(env, company_map, options, data)
        self.rpc_models = _PerTenantCountProxy(counts)
        #: Модели, при които самата ПРОВЕРКА пада (прекъсната връзка, отказан
        #: достъп) - не липсващ модел.
        self.blow_up_on = set()

    def _has_model(self, model):
        if model in self.blow_up_on:
            raise RuntimeError("the connection to the other system dropped")
        return super()._has_model(model)


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_reconcile')
class TestReconcileWithTheSource(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = cls.env['res.company'].create({'name': 'Наемател А (пренос)'})
        cls.other = cls.env['res.company'].create({'name': 'Наемател Б (пренос)'})
        #: 101 и 202 са двата наемателя на другата система.
        cls.company_map = {101: cls.tenant.id, 202: cls.other.id}
        cls.webstack = cls.env['hr.rfid.webstack'].create({
            'name': 'Модул на наемател А', 'serial': '778899', 'key': '0000',
            'company_id': cls.tenant.id, 'available': 'a',
            'tz': 'Europe/Sofia', 'active': True,
        })

    # ── двойник и помощници ───────────────────────────────────

    def _source(self, counts, company_map=None, **options):
        """Другата система с тези числа; без изброени настройки - пълен пренос."""
        return _CountingSource(
            self.env,
            dict(company_map if company_map is not None else self.company_map),
            options or dict(EVERYTHING_CARRIED), counts)

    def _rows(self, source):
        """Протоколните редове на проверката, по етикета, който операторът чете."""
        phase = ReconcileImporter(source)
        phase.run(None)
        self.assertFalse(source.rpc_models.fixture_errors,
                         'Двойникът не можа да отговори честно - резултатът '
                         'на проверката не значи нищо')
        return {row['model']: row for row in phase.results}

    def _employee(self, company, name):
        return self.env['hr.employee'].create({
            'name': name, 'company_id': company.id,
        })

    def _card(self, employee, number):
        return self.env['hr.rfid.card'].with_context(
            no_hardware_commands=True).create({
                'number': number, 'card_input_type': 'w34',
                'employee_id': employee.id,
                'company_id': employee.company_id.id,
            })

    def _arrived(self, source, model, source_id, record):
        """Записът тук носи идентичността на преноса.

        Написана със СОБСТВЕНИЯ идентификационен път на прехвърлянето, а не с
        ръчно сглобено име - иначе тестът щеше да проверява своята представа за
        идентичността, не тази на продукта.
        """
        self.assertTrue(
            source.adopt_existing(model, source_id, record),
            'фикстурата не успя да закачи идентичността на преноса за %s' % model)
        return record

    # ── редът на фазите ───────────────────────────────────────

    def test_the_check_runs_after_everything_it_checks(self):
        """Сверка преди данните да са пристигнали не значи нищо.

        Тя пита другата система за числата ѝ и ги сравнява с пристигналото -
        значи има смисъл едва след като всяка друга фаза е минала. Пусната
        по-рано, тя щеше да обяви за загубени точно данните, които следващата
        фаза тепърва носи.
        """
        phases = registry()
        self.assertIs(
            phases[-1], ReconcileImporter,
            'Сверката с другата система не е последна (последна е %s) - тя '
            'сравнява пристигналото, значи всичко останало трябва да е минало '
            'преди нея' % phases[-1].NAME,
        )
        self.assertLess(
            phases.index(ConsistencyImporter), phases.index(ReconcileImporter),
            'Двата контрола са в грешен ред: първо целостта на пренесеното '
            '(Фаза 9), после сверката с другата система',
        )
        self.assertEqual(
            ReconcileImporter.PHASE_ID, 'Phase 10',
            'Проверката се обявява като %r, а върви десета - операторът чете '
            'номера на фазата в протокола и по него търси реда'
            % ReconcileImporter.PHASE_ID,
        )
        self.assertFalse(
            ReconcileImporter.OPTION or ReconcileImporter.OPTION_ANY,
            'Контролът не бива да зависи от настройка, която операторът може да '
            'забрави - точно така 152 469 дневни обобщения останаха отвъд без '
            'нито един ред в протокола',
        )

    # ── съгласие ──────────────────────────────────────────────

    def test_a_tenant_whose_numbers_agree_gets_one_clean_line_per_kind(self):
        """Три души там, три души тук - един ред, който казва и двете числа."""
        source = self._source({'hr.employee': at_the_source(101, 3)})
        for index in range(1, 4):
            self._arrived(source, 'hr.employee', index,
                          self._employee(self.tenant, 'Човек %s' % index))

        rows = self._rows(source)
        self.assertIn(
            'people', rows,
            'Няма ред за хората - липсващият ред се чете като "такива данни '
            'няма", а точно това скри 152 469 обобщения',
        )
        row = rows['people']
        self.assertEqual(
            (row['source_count'], row['imported_count']), (3, 3),
            'Редът трябва да носи ДВЕТЕ числа - на другата система и тукашното; '
            'получи се %s там / %s тук' % (row['source_count'],
                                           row['imported_count']),
        )
        self.assertEqual(
            row['status'], 'done',
            'Числата съвпадат, а редът не е чист: %s' % row['error'],
        )
        self.assertFalse(row['error'], 'Чист ред с оплакване: %s' % row['error'])

    # ── загуба ────────────────────────────────────────────────

    def test_the_tenant_that_lost_its_cards_is_named_with_both_numbers(self):
        """Живият случай: един наемател загуби ВСИЧКИТЕ си 400 карти.

        Стъпката гърмеше на първия неоткриваем притежател, а всеки друг ред в
        протокола изглеждаше чист. Операторът няма къде да търси, ако редът не
        каже КОЙ наемател и КОИ две числа.
        """
        source = self._source({'hr.rfid.card': at_the_source(101, 4)})
        owner = self._employee(self.tenant, 'Притежател')
        self._arrived(source, 'hr.rfid.card', 1, self._card(owner, '7730000001'))
        self._arrived(source, 'hr.rfid.card', 2, self._card(owner, '7730000002'))

        row = self._rows(source)['cards']
        self.assertEqual(
            row['status'], 'error',
            'Другата система държи 4 карти, дошли са 2, а редът не е грешка - '
            'така 400 изгубени карти минаха за чист пренос',
        )
        self.assertEqual(
            (row['source_count'], row['imported_count']), (4, 2),
            'Редът показва %s там / %s тук вместо 4 / 2 - точните числа са '
            'единственото, по което операторът разбира колко карти липсват'
            % (row['source_count'], row['imported_count']),
        )
        for expected in (self.tenant.name, '4', '2'):
            self.assertIn(
                expected, row['error'],
                'Редът не назовава %r - операторът вижда "нещо липсва" без '
                'наемател и без числа: %s' % (expected, row['error']),
            )

    def test_another_tenants_records_do_not_fill_this_tenants_gap(self):
        """Пристигнало при ДРУГ наемател не е пристигнало при този.

        Мерено на живо: 19 карти се оказаха на човек от друга фирма, защото
        безфирмен контакт пристигна във фирмата по подразбиране на целта. Ако
        сверката брои пренесеното без да гледа фирмата, точно тази загуба се
        покрива от чуждия запис.
        """
        source = self._source({
            'hr.employee': at_the_source(101, 2) + at_the_source(202, 1),
        })
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Наш човек'))
        # Този е ПРИСТИГНАЛ, но в чужда фирма - за наемател А той липсва.
        self._arrived(source, 'hr.employee', 2,
                      self._employee(self.other, 'Човек в чужда фирма'))

        row = self._rows(source)['people']
        self.assertEqual(
            row['status'], 'error',
            'Двама души на наемател А, един е при него - редът трябва да е '
            'грешка, а не да брои чуждия запис за наличен',
        )
        self.assertIn(
            self.tenant.name, row['error'],
            'Назован е грешният наемател (или никой): %s' % row['error'])
        self.assertNotIn(
            self.other.name, row['error'],
            'Наемател Б е с пълни числа (1 там / 1 тук), а е обявен за '
            'потърпевш: %s' % row['error'],
        )

    def test_records_this_system_made_itself_do_not_cover_a_loss(self):
        """Броим ПРЕНЕСЕНОТО, не всичко, което се е събрало тук.

        Тази система си произвежда записи и сама (провизиране от хардуера,
        собствени задания). Плаен брой на целта би скрил загубата зад тях -
        и точно това прави разликата между контрол и успокоение.
        """
        source = self._source({'hr.employee': at_the_source(101, 3)})
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Пренесен човек'))
        # Двама, които не идват от преноса - без идентичност на преноса.
        self._employee(self.tenant, 'Роден тук 1')
        self._employee(self.tenant, 'Роден тук 2')

        row = self._rows(source)['people']
        self.assertEqual(
            row['imported_count'], 1,
            'Броени са 3 вместо 1: записите, родени тук, не носят идентичност '
            'на преноса и не бива да покриват липсващите',
        )
        self.assertEqual(
            row['status'], 'error',
            'Трима там, един пренесен - редът е чист само защото са преброени '
            'и чуждите записи',
        )

    def test_records_of_another_old_system_with_a_longer_name_are_not_this_ones(self):
        """Пренесеното от ДРУГА стара система не покрива загуба от тази.

        Една система може да приеме преноси от няколко стари, а името на
        едната може да е продължение на другата („acme“ и „acme_old“).
        Записите от втората носят своя идентичност; ако проверката на
        първата ги брои за свои, загубата ѝ изглежда покрита.
        """
        source = self._source({'hr.employee': at_the_source(101, 1)})
        older = self._source({'hr.employee': at_the_source(101, 1)})
        older.source_slug = source.source_slug + '_old'
        self._arrived(older, 'hr.employee', 1,
                      self._employee(self.tenant, 'От другата стара система'))

        row = self._rows(source)['people']
        self.assertEqual(
            (row['imported_count'], row['status']), (0, 'error'),
            'Човекът от „%s“ е броен като пренесен от „%s“: %s'
            % (older.source_slug, source.source_slug, row['error']))

    # ── нещо, което не може да се сравни ──────────────────────

    def test_records_the_other_system_does_not_keep_are_not_reported_as_lost(self):
        """Версия, която не води такива данни, не е повреда.

        Живата 14-та версия няма модел за дневните обобщения изобщо - на
        въпроса за него сървърът вдига грешка, а не връща празно. Такъв ред е
        "нямаше какво да сравня", не "изгубено".

        Проверява се и КОЯ страна не го води: двата клона на пропускането
        („тази система не пази такива данни" и „другата система не пази
        такива данни") дават един и същ статус, така че тест, който гледа
        само статуса, минава и по грешната причина.
        """
        source = self._source({'hr.employee': at_the_source(101, 1)})
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Единственият'))

        rows = self._rows(source)
        row = rows['daily working-time summaries']
        self.assertEqual(
            row['status'], 'skipped',
            'Липсващият в другата система модел е отчетен като %r вместо '
            'пропуснат - контрол, който вика "вълк", не се чете'
            % row['status'],
        )
        self.assertTrue(
            row['error'],
            'Пропускът е без обяснена причина - непояснено мълчание се чете '
            'като съгласие',
        )
        self.assertIn(
            'other system does not keep', row['error'],
            'Редът не казва КОЯ страна не води данните: %s. Другият клон на '
            'пропускането („тази система не пази такива данни") дава същия '
            'статус, значи тестът може да мине и по грешната причина.'
            % row['error'],
        )
        self.assertEqual(
            rows['people']['status'], 'done',
            'Един непроверим вид повлече и проверимите със себе си',
        )

    def test_a_kind_this_system_does_not_keep_is_not_a_loss_either(self):
        """Тук няма къде да пристигне - значи няма и загуба.

        Обратната посока на същото правило: източникът води данните, а тази
        инсталация не може да ги приеме (модулът не е инсталиран). Това се
        КАЗВА, но не се брои за изгубено.
        """
        source = self._source({})
        phase = ReconcileImporter(source)
        row = phase._reconcile('hr.rfid.no.such.model.here', '',
                               'нещо, което тук не съществува', time.time())
        self.assertEqual(
            row['status'], 'skipped',
            'Вид данни, които тази инсталация не води, е отчетен като %r'
            % row['status'],
        )
        self.assertTrue(row['error'], 'Пропускът е без обяснена причина')

    def test_a_source_that_cannot_be_asked_is_not_counted_as_zero(self):
        """Отказ да отговори не е "нула там".

        Нула там и нула тук се четат като съгласие. Точно затова отказът се
        КАЗВА: сверка, която не е минала, не бива да изглежда като сверка,
        която е съгласна.
        """
        source = self._source({'hr.rfid.card': at_the_source(101, 4)})
        source.rpc_models.refuse.add('hr.rfid.card')

        row = self._rows(source)['cards']
        self.assertEqual(
            row['status'], 'skipped',
            'Отказът на другата система е отчетен като %r - при 4 карти там и '
            '0 преброени тук това е тихо "всичко е добре"' % row['status'],
        )
        self.assertNotEqual(
            row['status'], 'done',
            'Непроведена сверка се представя за съгласие')
        self.assertTrue(
            row['error'],
            'Отказът е без обяснение - операторът не знае, че този вид данни '
            'изобщо не е бил сверен',
        )

    def test_a_check_that_breaks_is_a_finding_and_does_not_blind_the_rest(self):
        """Паднала проверка е находка, а не липсващ ред.

        Урокът от 14-та версия, приложен към самия контрол: една паднала стъпка
        отнесе 196 659 присъствия със себе си. Тук една паднала проверка не бива
        да отнася останалите - и трябва да остави ред за себе си.
        """
        source = self._source({
            'hr.employee': at_the_source(101, 1),
            'hr.rfid.card': at_the_source(101, 1),
        })
        owner = self._employee(self.tenant, 'Притежател')
        self._arrived(source, 'hr.rfid.card', 1, self._card(owner, '7730000009'))
        source.blow_up_on.add('hr.employee')

        rows = self._rows(source)
        self.assertIn(
            'people', rows,
            'Падналата проверка не остави ред - липсващият ред се чете като '
            '"нямаше какво да се проверява"',
        )
        self.assertEqual(
            rows['people']['status'], 'error',
            'Паднала проверка е отчетена като %r с 1 там / 0 тук - непроведена '
            'сверка не бива да се чете като съгласие'
            % rows['people']['status'],
        )
        self.assertTrue(
            rows['people']['error'],
            'Падналата проверка не казва защо е паднала')
        self.assertEqual(
            rows['cards']['status'], 'done',
            'Една паднала проверка ослепи и останалите - точно щетата, която '
            'коства 196 659 присъствия на 14-та версия',
        )

    # ── оста на броенето ──────────────────────────────────────

    def test_the_count_includes_the_archived_records_the_transfer_carries(self):
        """Броим по ОСТА, по която прехвърлянето чете - с архивираните.

        Мерено на живо: страницата за преглед обеща 6 395 карти и 5 984 души,
        а пристигнаха 8 505 и 6 176 - тя броеше без архивираните, а
        прехвърлянето чете и тях. Контрол, който брои по другата ос, обявява
        всеки архивиран запис за изгубен и се превръща в шум.
        """
        source = self._source({
            'hr.employee': at_the_source(101, 1) + at_the_source(101, 3,
                                                                active=False),
        })
        for index in range(1, 5):
            employee = self._employee(self.tenant, 'Човек %s' % index)
            self._arrived(source, 'hr.employee', index, employee)
            if index > 1:
                employee.active = False       # архивиран и ТУК

        row = self._rows(source)['people']
        self.assertEqual(
            (row['source_count'], row['imported_count']), (4, 4),
            'Архивираните изпадат от броенето (%s там / %s тук) - оттам идва '
            'разликата 6 395 обещани срещу 8 505 пристигнали'
            % (row['source_count'], row['imported_count']),
        )
        self.assertEqual(
            row['status'], 'done',
            'Четири там, четири тук, а редът е %r (%s) - архивираните излизат '
            'като липси на всеки прогон' % (row['status'], row['error']),
        )
        counted = [call for call in source.rpc_models.calls
                   if call['method'] == 'search_count']
        self.assertTrue(counted, 'Другата система не е питана изобщо')
        for call in counted:
            self.assertIs(
                call['context'].get('active_test'), False,
                'Броенето на %s заобикаля собствения брояч на прехвърлянето - '
                'без active_test=False архивираният модул скрива всичко под '
                'себе си и правилото за достъп на източника ОТКАЗВА записа'
                % call['model'],
            )

    def test_the_chain_to_the_company_is_the_business_one(self):
        """Контролерът стига до фирмата през модула, не сам по себе си.

        Хардуерът няма своя фирма - той я наследява по веригата модул ->
        контролер -> врата -> четец. Сверка, която пита за нея направо, не
        може да сравни нито едно от тези звена.
        """
        source = self._source({'hr.rfid.ctrl': at_the_source(101, 2)})
        for index, ctrl_id in enumerate((81, 82), start=1):
            self._arrived(source, 'hr.rfid.ctrl', index,
                          self.env['hr.rfid.ctrl'].create({
                              'name': 'Контролер %s' % ctrl_id,
                              'ctrl_id': ctrl_id,
                              'webstack_id': self.webstack.id,
                          }))

        row = self._rows(source)['controllers']
        self.assertEqual(
            (row['source_count'], row['imported_count']), (2, 2),
            'Контролерите не се сверяват (%s там / %s тук) - веригата до '
            'фирмата минава през модула'
            % (row['source_count'], row['imported_count']),
        )
        self.assertEqual(row['status'], 'done', row['error'])
        asked = source.rpc_models.companies_asked_about('hr.rfid.ctrl')
        self.assertTrue(asked, 'Другата система не е питана за контролерите')
        self.assertIn(
            ('webstack_id.company_id', '=', 101), asked[0],
            'Контролерите са питани по друга ос: %s' % asked[0])

    # ── обяснена разлика ──────────────────────────────────────

    def test_more_here_than_there_is_said_out_loud(self):
        """Повече тук не е загуба, но не е и мълчание.

        Другата система живее нататък: изтрит или архивиран там запис прави
        пренесеното тук повече от нейното. Това не е дефект, но никой не бива
        да го научава от отчет след месеци - затова редът е "частично", с
        двете числа.
        """
        source = self._source({'hr.employee': at_the_source(101, 2)})
        for index in range(1, 4):
            self._arrived(source, 'hr.employee', index,
                          self._employee(self.tenant, 'Пренесен %s' % index))

        row = self._rows(source)['people']
        self.assertEqual(
            row['status'], 'partial',
            'Три пренесени срещу два останали там дадоха %r - "done" мълчи, а '
            '"error" вика "вълк" за нещо, което не е загуба' % row['status'],
        )
        self.assertEqual(
            (row['source_count'], row['imported_count']), (2, 3),
            'Редът показва %s там / %s тук вместо 2 / 3 - разликата се обяснява '
            'само с двете числа пред очите на оператора'
            % (row['source_count'], row['imported_count']),
        )
        for expected in (self.tenant.name, '2', '3'):
            self.assertIn(
                expected, row['error'],
                'Разликата не назовава %r: %s' % (expected, row['error']))

    def test_the_absences_it_compares_are_the_ones_the_transfer_carries(self):
        """Отказаният отпуск не е изгубен отпуск.

        Пропуска се на инсталация без отпуски: модулът не зависи от
        hr_holidays, а тест, който пада заради липсващ съсед, не казва нищо
        за контрола.

        Прехвърлянето носи одобрените и още неприключилите отсъствия. Ако
        контролът брои и отказаните/отменените, всеки прогон ще обявява
        стотици липси - мерено: 3 300 отсъствия на един наемател, от които
        2 848 бяха отказани точно защото друг дефект искаше от всички тях
        наличност. Контрол, който вика "вълк", не се чете.
        """
        if 'hr.leave' not in self.env:
            self.skipTest('hr_holidays не е инсталиран тук')
        source = self._source({'hr.leave': at_the_source(101, 2,
                                                         state='refuse')})
        row = self._rows(source)['absences']
        self.assertEqual(
            (row['source_count'], row['imported_count']), (0, 0),
            'Отказаните отсъствия се броят за пренасяни (%s там) и излизат '
            'като липси на всеки прогон' % row['source_count'],
        )
        self.assertEqual(row['status'], 'done', row['error'])
        asked = source.rpc_models.companies_asked_about('hr.leave')
        self.assertTrue(asked, 'Другата система не е питана за отсъствията')
        self.assertIn(
            ('state', 'in', CARRYABLE_LEAVE_STATES), asked[0],
            'Отсъствията са питани без филтър по състояние: %s' % asked[0])

        # Отрицателният близнак: одобреното отсъствие, което НЕ е дошло, е
        # загуба и трябва да се вика.
        loud = self._source({'hr.leave': at_the_source(101, 1,
                                                        state='validate')})
        loud_row = self._rows(loud)['absences']
        self.assertEqual(
            loud_row['status'], 'error',
            'Одобрено отсъствие, което не е пристигнало, минава за чисто - '
            'филтърът по състояние е станал сито за всичко',
        )

    # ── обхват на самия контрол ───────────────────────────────

    def test_a_tenant_outside_this_transfer_is_not_compared(self):
        """Чужд наемател не е наша липса.

        В облака с 27 фирми се пренасят по няколко наведнъж. Данните на
        наемател, който не е в този пренос, не бива да се броят никъде - иначе
        всеки прогон завършва с "липсват" за неща, които никой не е искал.
        """
        source = self._source(
            {'hr.employee': at_the_source(101, 1) + at_the_source(202, 5)},
            company_map={101: self.tenant.id, 202: False})
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Нашият'))

        row = self._rows(source)['people']
        self.assertEqual(
            (row['source_count'], row['imported_count']), (1, 1),
            'Преброени са и петимата на непренасяния наемател (%s там) - всеки '
            'прогон ще завършва с измислена липса' % row['source_count'],
        )
        self.assertEqual(row['status'], 'done', row['error'])
        for domain in source.rpc_models.companies_asked_about('hr.employee'):
            self.assertNotIn(
                ('company_id', '=', 202), domain,
                'Другата система е питана за наемател, който не е в този '
                'пренос: %s' % domain)

    def test_every_kind_the_transfer_lost_live_is_on_the_list(self):
        """Вид данни, който не е в списъка, е сляпо петно на контрола.

        Всеки от изброените тук е бил ЗАГУБЕН на живо (400 карти, 152 469
        дневни обобщения, 4 202 събития без притежател, 23 членства в групи за
        достъп, 3 546 зареждания) и точно затова контролът трябва да ги пита.
        Изпадне ли един, контролът пак ослепява там, където вече е ослепявал.

        Контактите умишлено НЕ са тук: безфирменият контакт няма фирмена ос, по
        която да бъде преброен - точно затова прехвърлянето разширява обхвата
        му през картите и членствата. За тях е нужен отделен контрол, не ред в
        този списък.
        """
        listed = [entry[0] for entry in RECONCILED]
        for model in ('hr.rfid.card', 'hr.employee', 'hr.rfid.ctrl',
                      'hr.rfid.door', 'hr.rfid.reader',
                      'hr.rfid.access.group.door.rel',
                      'hr.rfid.access.group.employee.rel',
                      'hr.rfid.access.group.contact.rel',
                      'hr.rfid.event.user', 'hr.rfid.event.system',
                      'hr.attendance', 'hr.attendance.extra',
                      'hr.leave', 'hr.leave.allocation'):
            self.assertIn(
                model, listed,
                'Контролът не пита другата система за %s - точно този вид '
                'данни е оставал отвъд без ред в протокола' % model)
        self.assertEqual(
            len(listed), len(set(listed)),
            'Един и същ вид данни се сверява два пъти: %s. Операторът получава '
            'два реда за едно нещо и не знае кой да чете'
            % [m for m in listed if listed.count(m) > 1],
        )
        reaching_the_run = set(self.env['hr.rfid.odoo.import.wiz'].new({})
                               ._build_options())
        phase_switches = {name for cls in registry()
                          for name in (cls.OPTION,) + tuple(cls.OPTION_ANY) if name}
        self.assertEqual(
            set(KIND_LABELS), set(listed),
            'Видовете с име и сверяваните видове се разминават - вид без име '
            'гърми в проверката, име без вид е мъртво')
        for entry in RECONCILED:
            self.assertIn(
                len(entry), (3, 4),
                'Ред от списъка е с непознат вид: %s' % (entry,))
            label = self.env._(KIND_LABELS[entry[0]])
            self.assertTrue(
                label and label == label.strip(),
                'Видът %s се показва на оператора без четимо име' % entry[0])
            # Сгрешено име на настройката прави вида „непренасян" завинаги -
            # всяка загуба в него минава за забележка.
            names = _option_names(entry[2])
            for name in names:
                self.assertIn(
                    name, reaching_the_run,
                    'Видът %s се води пренасян от %r, а такава отметка не '
                    'стига до преноса - загубата му ще излиза като забележка'
                    % (entry[0], name))
            self.assertTrue(
                set(names) & phase_switches,
                'Видът %s се води пренасян от %s, а нито една от тях не пуска '
                'стъпка - видът ще се брои за пренасян, без да е'
                % (entry[0], names))

    # ── само пренесеното е проблем (собственикът, 10.11.2026) ─────

    def _stay(self, person, day):
        """Едно затворено присъствие на човека в този ден, тук."""
        return self.env['hr.attendance'].create({
            'employee_id': person.id,
            'check_in': datetime(2025, 12, day, 7, 0),
            'check_out': datetime(2025, 12, day, 15, 0),
        })

    def test_a_kind_left_out_of_the_transfer_is_a_remark_not_a_problem(self):
        """Повторен пренос само на присъствията не е „спрян поради проблем“ заради хората.

        Мерено на 10.11.2026 на копие на клиентска система: всяка стъпка на
        повторния пренос мина, присъствията дойдоха, а преносът излезе като
        спрян - заради хора, събития и обобщения, които никой не е искал да
        пренася. Собственикът: проблем е само пренесеното, останалото е
        забележка. Разликата пак се казва, с двете числа, защото е полезна.
        """
        source = self._source({'hr.employee': at_the_source(101, 3)},
                              import_attendance=True)
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Пренесен по-рано'))

        row = self._rows(source)['people']
        self.assertEqual(
            row['status'], 'skipped',
            'Хората не са част от този пренос, а разликата им е отчетена като '
            '%r - така преносът на присъствията излиза спрян' % row['status'])
        for expected in (self.tenant.name, '3 there', '1 here',
                         'not part of this transfer'):
            self.assertIn(
                expected, row['error'],
                'Забележката не казва %r - операторът не знае каква е разликата '
                'и защо не е проблем: %s' % (expected, row['error']))
        self.assertEqual(
            (row['source_count'], row['imported_count']), (3, 1),
            'Числата на забележката не са в колоните, където операторът ги чете')

        # Обратният близнак: отметнати ли са хората, същата разлика е загуба.
        carried = self._source({'hr.employee': at_the_source(101, 3)},
                               import_people=True)
        self.assertEqual(
            self._rows(carried)['people']['status'], 'error',
            'Хората са част от преноса, двама не са дошли, а редът не е грешка')

    def test_a_kind_left_out_with_the_same_numbers_is_a_clean_line(self):
        """Непренасян вид без разлика не оставя забележка.

        Забележка без разлика е шум, а шумът учи оператора да не чете реда.
        """
        source = self._source({'hr.employee': at_the_source(101, 1)},
                              import_attendance=True)
        self._arrived(source, 'hr.employee', 1,
                      self._employee(self.tenant, 'Единственият'))

        row = self._rows(source)['people']
        self.assertEqual((row['status'], row['error']), ('done', ''),
                         'Един там, един тук, а редът казва нещо: %s' % row['error'])

    def test_a_stay_of_a_person_who_is_not_here_is_a_remark_when_people_were_not_carried(self):
        """Присъствие на човек, когото тук няма, не спира пренос само на присъствията.

        Мерено на 10.11.2026: от 41 856 присъствия на другата система едно не
        дойде - на човек, когото новата система няма, - и преносът излезе
        спрян. Без човек тук присъствието няма към кого да се закачи, а
        хората не са били част от преноса. Разликата е тяхната, казана още
        веднъж - като забележка, с броя и с двете числа.
        """
        person = self._employee(self.tenant, 'Пренесен човек')
        counts = {
            'hr.employee': at_the_source(101, 2),
            'hr.attendance': (at_the_source(101, 2, employee_id=77)
                              + at_the_source(101, 1, employee_id=78)),
        }
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))
        self._arrived(source, 'hr.attendance', 2, self._stay(person, 4))

        row = self._rows(source)['attendances']
        self.assertEqual(
            row['status'], 'partial',
            'Присъствие на човек, когото тук няма и не е пренасян, е отчетено '
            'като %r: %s' % (row['status'], row['error']))
        for expected in (self.tenant.name, '3 there', '2 here', 'people',
                         'not part of this transfer'):
            self.assertIn(
                expected, row['error'],
                'Забележката не казва %r: %s' % (expected, row['error']))

        # Близнак 1: хората СА част от преноса - липсващият човек е загуба на
        # преноса, и присъствието му с него.
        with_people = self._source(counts, import_attendance=True,
                                   import_people=True)
        self.assertEqual(
            self._rows(with_people)['attendances']['status'], 'error',
            'Хората са пренасяни, един не е дошъл, а присъствието му не е загуба')

    def test_a_lost_stay_of_a_person_who_is_here_still_stops_the_transfer(self):
        """Забележката за липсващия човек не покрива истинска загуба до нея.

        Човекът е тук, присъствието му е там, а не е дошло - това е точно
        загубата, заради която проверката съществува, каквото и друго да е
        обяснено в същия ред.
        """
        person = self._employee(self.tenant, 'Пренесен човек')
        counts = {
            'hr.attendance': (at_the_source(101, 3, employee_id=77)
                              + at_the_source(101, 1, employee_id=78)),
        }
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))
        self._arrived(source, 'hr.attendance', 2, self._stay(person, 4))

        row = self._rows(source)['attendances']
        self.assertEqual(
            row['status'], 'error',
            'Едно присъствие на човек, който Е тук, не е дошло, а редът е %r: %s'
            % (row['status'], row['error']))

    def test_a_person_deleted_here_after_the_first_transfer_counts_as_not_here(self):
        """Изтритият тук човек е „няма го тук“, макар първият пренос да го е донесъл.

        При клиента човекът на администратора е бил пренесен и после изтрит;
        идентичността му в преноса си е отишла с него. Проверката трябва да го
        вижда като липсващ, а не да брои присъствието му за изгубено.
        """
        person = self._employee(self.tenant, 'Остава')
        gone = self._employee(self.tenant, 'Изтрит после')
        counts = {'hr.attendance': (at_the_source(101, 1, employee_id=77)
                                    + at_the_source(101, 1, employee_id=78))}
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.employee', 78, gone)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))
        gone_id = gone.id
        gone.unlink()

        row = self._rows(source)['attendances']
        self.assertEqual(
            row['status'], 'partial',
            'Присъствие на изтрит тук човек е отчетено като %r: %s'
            % (row['status'], row['error']))

        # Изтриване покрай ORM (каскада в базата) оставя идентичността да сочи
        # празно място. Тя не прави човека „тук“.
        source.link_existing('hr.employee', 78, gone_id)
        row = self._rows(source)['attendances']
        self.assertEqual(
            row['status'], 'partial',
            'Идентичност без запис зад нея е броена за човек тук: %r, %s'
            % (row['status'], row['error']))

    def test_a_card_of_a_person_who_is_not_here_does_not_stop_a_transfer_of_the_cards(self):
        """Пренос на картите без хората: карта на човек, когото тук няма, е забележка.

        Стъпката оставя такава карта назад по име („картата ... е на човек,
        който не е дошъл"). Отметнати ли са и хората, липсващият човек е загуба
        на преноса - и картата му с него.
        """
        person = self._employee(self.tenant, 'Притежател тук')
        counts = {'hr.rfid.card': (at_the_source(101, 1, employee_id=77, contact_id=False)
                                   + at_the_source(101, 1, employee_id=78, contact_id=False))}
        source = self._source(counts, import_access=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.rfid.card', 1, self._card(person, '7730000101'))

        row = self._rows(source)['cards']
        self.assertEqual(row['status'], 'partial',
                         'Карта на човек, когото тук няма: %r, %s'
                         % (row['status'], row['error']))

        with_people = self._source(counts, import_access=True, import_people=True)
        self.assertEqual(self._rows(with_people)['cards']['status'], 'error',
                         'Хората са пренасяни, един не е дошъл, а картата му '
                         'не е загуба')

    def test_a_card_asked_for_by_its_own_tick_and_lost_is_a_problem(self):
        """„Импорт на карти" е отметка на екрана: картите с нея са поискани.

        Картите идват с достъпа, а самата отметка вече не пуска стъпка. Който
        я е отметнал, е поискал картите - изгубени, те са проблем, не забележка.
        """
        counts = {'hr.rfid.card': at_the_source(101, 2, employee_id=77, contact_id=False)}
        source = self._source(counts, import_cards=True)
        # The holder is here, so nothing explains the two lost cards.
        self._arrived(source, 'hr.employee', 77,
                      self._employee(self.tenant, 'Притежател тук'))
        row = self._rows(source)['cards']
        self.assertEqual(row['status'], 'error',
                         'Поисканите карти не са дошли, а редът е %r: %s'
                         % (row['status'], row['error']))

        untouched = self._source(counts, import_attendance=True)
        self.assertEqual(self._rows(untouched)['cards']['status'], 'skipped')

    def test_an_archived_person_here_is_here(self):
        """Архивиран човек тук е тук: изгубено негово присъствие е загуба.

        Архивираните вече веднъж минаха за липсващи (6 395 срещу 8 505). Ако
        минат за „ги няма тук", загубата им става забележка.
        """
        person = self._employee(self.tenant, 'Архивиран')
        counts = {'hr.attendance': at_the_source(101, 2, employee_id=77)}
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))
        person.active = False

        row = self._rows(source)['attendances']
        self.assertEqual(row['status'], 'error',
                         'Присъствие на архивиран човек тук е скрито като '
                         'забележка: %s' % row['error'])

    def test_a_person_missing_in_one_tenant_does_not_explain_a_loss_in_another(self):
        """Липсващ човек при един наемател не покрива загуба при друг."""
        ours = self._employee(self.tenant, 'Тук, наемател А')
        counts = {'hr.attendance': (at_the_source(101, 2, employee_id=77)
                                    + at_the_source(202, 1, employee_id=78))}
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, ours)
        self._arrived(source, 'hr.attendance', 1, self._stay(ours, 3))

        row = self._rows(source)['attendances']
        self.assertEqual(row['status'], 'error')
        loss = row['error'].split('. ')[0]
        self.assertIn(self.tenant.name, loss,
                      'Загубата при наемател А не е назована: %s' % row['error'])
        self.assertNotIn(self.other.name, loss,
                         'Наемател Б е назован като загубил: %s' % row['error'])

    def test_records_of_people_not_here_are_counted_by_the_same_filter(self):
        """Отказаните отсъствия на липсващ човек не покриват одобрено, изгубено.

        Проверката брои само отсъствията, които преносът носи. Ако „чии са"
        се питаше без същия филтър, 2 848-те отказани отсъствия от живия
        случай щяха да обяснят всяка загуба.
        """
        if 'hr.leave' not in self.env:
            self.skipTest('hr_holidays не е инсталиран тук')
        person = self._employee(self.tenant, 'Тук')
        counts = {'hr.leave': (at_the_source(101, 1, state='validate', employee_id=77)
                               + at_the_source(101, 1, state='refuse', employee_id=78))}
        source = self._source(counts, import_leaves=True)
        self._arrived(source, 'hr.employee', 77, person)

        row = self._rows(source)['absences']
        self.assertEqual(row['status'], 'error',
                         'Отказано отсъствие на липсващ човек покри одобрено, '
                         'изгубено: %s' % row['error'])

    def test_when_the_other_system_will_not_say_whose_they_are_the_loss_stays(self):
        """Не можем да питаме „чии са" - разликата остава загуба и се казва защо."""
        person = self._employee(self.tenant, 'Тук')
        counts = {'hr.attendance': (at_the_source(101, 1, employee_id=77)
                                    + at_the_source(101, 1, employee_id=78))}
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))
        source.rpc_models.refuse_owner_question.add('hr.attendance')

        row = self._rows(source)['attendances']
        self.assertEqual(row['status'], 'error')
        self.assertIn('did not say', row['error'],
                      'Не е казано, че обяснението не е проверено: %s' % row['error'])

    def test_more_records_of_people_not_here_than_are_missing_explains_nothing(self):
        """Повече „на липсващи хора" отколкото липсват - числата не се връзват.

        Недошлите записи не могат да са повече от разликата. Излязат ли
        повече, двете числа не говорят за едни и същи записи и не обясняват
        нищо: разликата остава загуба.
        """
        person = self._employee(self.tenant, 'Тук')
        counts = {'hr.attendance': (at_the_source(101, 2, employee_id=77)
                                    + at_the_source(101, 2, employee_id=78))}
        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        for index, day in ((1, 3), (2, 4), (3, 5)):
            self._arrived(source, 'hr.attendance', index, self._stay(person, day))

        row = self._rows(source)['attendances']
        self.assertEqual(row['status'], 'error')
        self.assertIn('do not add up', row['error'])

    def test_a_kind_left_out_with_more_here_is_still_said(self):
        """Непренасян вид с повече тук също се казва - като забележка."""
        source = self._source({'hr.employee': at_the_source(101, 1)},
                              import_attendance=True)
        for index in (1, 2):
            self._arrived(source, 'hr.employee', index,
                          self._employee(self.tenant, 'Пренесен %s' % index))

        row = self._rows(source)['people']
        self.assertEqual(row['status'], 'skipped')
        self.assertIn('1 there', row['error'])

    def test_a_tick_this_system_cannot_take_is_still_the_operators_request(self):
        """Отметнато, а системата тук не може да го приеме: остава загуба.

        Превключвателят на стъпката е изключен, защото тук няма къде да дойде,
        но операторът го е поискал. Неотметнатото е забележка.
        """
        counts = {'hr.attendance': at_the_source(101, 2, employee_id=77)}
        self._arrived(self._source(counts), 'hr.employee', 77,
                      self._employee(self.tenant, 'Тук'))
        asked = self._source(counts, import_attendance=False,
                             ticked={'import_attendance': True})
        self.assertEqual(self._rows(asked)['attendances']['status'], 'error')

        not_asked = self._source(counts, import_attendance=False,
                                 ticked={'import_attendance': False})
        self.assertEqual(self._rows(not_asked)['attendances']['status'], 'skipped')

    def test_a_check_that_breaks_on_a_kind_not_carried_does_not_stop_the_transfer(self):
        """Паднала проверка на непренасян вид се казва, но не спира преноса."""
        source = self._source({'hr.employee': at_the_source(101, 1)},
                              import_attendance=True)
        source.blow_up_on.add('hr.employee')

        row = self._rows(source)['people']
        self.assertEqual(row['status'], 'skipped')
        self.assertTrue(row['error'], 'Падналата проверка не казва защо')

    def test_a_transfer_of_the_attendance_alone_ends_as_finished(self):
        """Целият пренос, не само редът: само присъствия, разлика само в хората.

        Решението на собственика е за ПРЕНОСА - „излезе като спрян". Тук
        минава истинският край на прогона: стъпката, редовете в протокола и
        състоянието, което операторът вижда.
        """
        from ..models.importers import phase as phase_module

        person = self._employee(self.tenant, 'Тук')
        counts = {'hr.employee': at_the_source(101, 2),
                  'hr.attendance': (at_the_source(101, 1, employee_id=77)
                                    + at_the_source(101, 1, employee_id=78))}

        Run = self.registry['hr.rfid.odoo.import.run']
        current = {}
        self.patch(phase_module, 'phase_plan',
                   lambda env, options, modules: [(ReconcileImporter, None)])
        self.patch(Run, '_build_importer', lambda records, options: current['source'])
        self.patch(Run, '_wake_the_worker', lambda records: None)
        # The pass makes its progress permanent after every step; in a test
        # that would end the test's own transaction.
        self.patch(self.env.cr, 'commit', lambda: None)

        def finish(counts, people_too=False):
            options = {'import_attendance': True, 'import_people': people_too}
            current['source'] = self._source(counts, **options)
            run = self.env['hr.rfid.odoo.import.run'].create({
                'source_url': 'http://localhost:1', 'source_login': 'admin',
                'source_db': 'src', 'source_password': 'secret',
                'options_json': json.dumps(options),
                'installed_modules_json': json.dumps(['hr_rfid']),
                'company_map_json': json.dumps(
                    {str(k): v for k, v in self.company_map.items()}),
                'state': 'queued',
            })
            run._process_pass()
            self.assertFalse(current['source'].rpc_models.fixture_errors)
            return run

        source = self._source(counts, import_attendance=True)
        self._arrived(source, 'hr.employee', 77, person)
        self._arrived(source, 'hr.attendance', 1, self._stay(person, 3))

        run = finish(counts)
        self.assertEqual(run.state, 'done',
                         'Само присъствия, разлика само в хората, а преносът е %r'
                         % run.state)

        # Близнакът: хората са пренасяни и един липсва - преносът е спрян.
        self.assertEqual(finish(counts, people_too=True).state, 'failed')
