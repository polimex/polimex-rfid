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

import time
import xmlrpc.client

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.consistency_importer import ConsistencyImporter
from ..models.importers.phase import registry
from ..models.importers.reconcile_importer import (
    CARRYABLE_LEAVE_STATES, RECONCILED, ReconcileImporter,
)
from .test_older_source_missing_models import _OlderSource


def at_the_source(company, count=1, active=True, state=None):
    """`count` записа на този наемател в ДРУГАТА система.

    Фикстурата е малка, доказателството - живо: два реда тук стоят за 400-те
    карти на един наемател или за 152 469-те дневни обобщения. Размерът не е
    твърдението; твърдението е в поведението на контрола.
    """
    return [{'company': company, 'active': active, 'state': state}
            for _ in range(count)]


class _PerTenantCountProxy:
    """RPC двойник, който БРОИ - и брои архивираните само когато го помолят.

    Умишлено строг за архивираните: истинският източник не просто скрива
    архивирания запис, а собственото му правило за достъп (верижна фирмена
    проверка) ОТКАЗВА записа под архивиран модул, ако контекстът не е
    `active_test=False`. Затова двойникът дава архивираните САМО по контекста -
    броене, което заобикаля собствения брояч на прехвърлянето, тук връща
    по-малко число, точно както страницата за преглед обеща 6 395 при 8 505.
    """

    def __init__(self, counts):
        #: {модел: [{'company': 101, 'active': True, 'state': 'validate'}, ...]}
        self.counts = counts
        self.calls = []
        #: Модели, за които другата система отказва да брои изобщо.
        self.refuse = set()

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
        return len(self._matching(model, domain,
                                  kwargs.get('context') or {}))

    def _matching(self, model, domain, context):
        wants_archived = context.get('active_test') is False
        company = states = None
        for leaf in domain:
            if not isinstance(leaf, (list, tuple)) or len(leaf) != 3:
                continue
            name, _op, value = leaf
            if str(name).endswith('company_id'):
                company = value
            elif name == 'state':
                states = list(value) if isinstance(value, (list, tuple)) else [value]
        out = []
        for row in self.counts.get(model, []):
            if company is not None and row.get('company') != company:
                continue
            if states is not None and row.get('state') not in states:
                continue
            if not wants_archived and not row.get('active', True):
                continue
            out.append(row)
        return out

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
        return _CountingSource(
            self.env,
            dict(company_map if company_map is not None else self.company_map),
            options, counts)

    def _rows(self, source):
        """Протоколните редове на проверката, по етикета, който операторът чете."""
        phase = ReconcileImporter(source)
        phase.run(None)
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
        for entry in RECONCILED:
            self.assertIn(
                len(entry), (3, 4),
                'Ред от списъка е с непознат вид: %s' % (entry,))
            self.assertTrue(
                entry[2] and entry[2] == entry[2].strip(),
                'Видът %s се показва на оператора без четимо име' % entry[0])
