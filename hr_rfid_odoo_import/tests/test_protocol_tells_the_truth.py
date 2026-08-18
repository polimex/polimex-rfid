# -*- coding: utf-8 -*-
"""Протоколът е това, по което собственикът съди дали пренасянето е станало.

Бизнес твърдение (собственик, 2026-08-17, при пренасянето на наемател от Odoo 14
и на облака с 27 фирми): числата на страницата преди старта и редовете в
протокола след него трябва да КАЗВАТ ИСТИНАТА. Операторът няма как да провери
6 176 служителя на ръка; той сравнява обещаното с докладваното и решава.

Петте начина, по които протоколът лъжеше, мерени на живо:

  * завършила стъпка докладваше среза на ПОСЛЕДНИЯ си пас, тоест "0 внесени"
    върху пренесени 6 176 души (и 20 851 камерни събития другаде);
  * паднала стъпка оставяше курсора и преброеното напред, макак редовете ѝ да
    са били върнати - следващият пас прескачаше точно тях, а протоколът ги
    броеше за пренесени завинаги;
  * страницата преди старта обещаваше 6 395 карти и 5 984 души, а пренасянето
    донесе 8 505 и 6 176 (тя броеше без архивираните, а прочитът ги чете);
  * никоя фаза не назоваваше hr_attendance_late, значи източникът не беше питан,
    отметката остана свалена сама и 152 469 дневни обобщения останаха там БЕЗ
    ред в протокола - тишина, която се чете точно като "нямаше такива данни";
  * тази система сама смята дневните обобщения, затова последните дни завършваха
    с ДВА реда за един човек (мерени 10 такива дни) и всеки отчет над тях брои
    двойно.

Всеки тест по-долу твърди какво трябва да прочете операторът, и има отрицателен
близнак за това, което НЕ бива да се случи: без дубликат, без тиха нула, без
обещание, което пренасянето не изпълнява.
"""

import json
import types
import xmlrpc.client

from odoo.tests.common import TransactionCase, tagged

from ..models import import_wizard
from ..models.importers.attendance_importer import AttendanceImporter
from ..models.importers.base_importer import BaseImporter
from ..models.importers.people_importer import PeopleImporter
from ..models.importers.phase import (
    PhaseImporter, phase_plan, source_probe_modules,
)
from .test_company_scope import _FakeSource
from .test_run_totals_survive_the_passes import _PagedSource


class _RefusingWriteSource(_PagedSource):
    """Базата отказва записа на ЕДИН вид данни, другият минава.

    Формата от живия прогон: една стъпка пада, съседната ѝ е свършила работа.
    Двойник, който отказва ВСИЧКО, не може да покаже разликата между "върни
    преброеното на падналата" и "върни преброеното на всички".
    """

    #: Моделът, чийто запис базата отказва.
    REFUSES = 'hr.rfid.event.system'

    def _direct_sql_insert_tracked(self, table, columns, rows, model,
                                   source_ids, batch_size=5000):
        if model == self.REFUSES:
            raise ValueError('the database said no')
        return super()._direct_sql_insert_tracked(
            table, columns, rows, model, source_ids, batch_size=batch_size)


class _TwoKindsPhase(PhaseImporter):
    """Фаза с две стъпки, всяка с продължим прочит и свой ред в протокола.

    Стъпките са с формата на истинските (прочит с курсор -> запис в базата ->
    ред с тоталите на ПРОГОНА). Проверяваният механизъм е `PhaseImporter.steps`
    заедно с `progress_snapshot`/`restore_progress`; стъпките са само стойката,
    която го подлага на живата форма - едната пада, другата е успяла.
    """

    PHASE_ID = 'Phase T'
    NAME = 'Two kinds'
    REQUIRES_TARGET = ('hr.rfid.event.user',)

    FIRST_CURSOR = 'twokinds:hr.rfid.event.user'
    SECOND_CURSOR = 'twokinds:hr.rfid.event.system'

    def run(self, wizard):
        return self.steps(self._import_the_first_kind,
                          self._import_the_second_kind)

    def _move(self, model, table, cursor_key):
        records = self.b._read_all(model, [], ['event_time'], cursor_key)
        imported, already, rejected = self.b._direct_sql_insert_tracked(
            table, ['event_time'], [(r['event_time'],) for r in records],
            model, [r['id'] for r in records])
        self.results.append(self.b.accumulated_result(
            cursor_key, model, len(records), imported, already))

    def _import_the_first_kind(self):
        self._move('hr.rfid.event.user', 'hr_rfid_event_user',
                   self.FIRST_CURSOR)

    def _import_the_second_kind(self):
        self._move('hr.rfid.event.system', 'hr_rfid_event_system',
                   self.SECOND_CURSOR)


class _PhaseThatFallsOverHalfway:
    """Фаза, която е прочела, преброила и мапнала - и после е паднала.

    Точката, в която savepoint-ът връща РЕДОВЕТЕ, а курсорът, тоталите и
    картата source->target живеят в паметта и биха оцелели.
    """

    CURSOR = 'halfway:hr.employee'
    READ_UP_TO = 1000
    SOURCE_EMPLOYEE = 42

    def __init__(self, base):
        self.b = base

    def _got_this_far(self):
        self.b.read_cursors[self.CURSOR] = self.READ_UP_TO
        self.b.accumulate(self.CURSOR, source=self.READ_UP_TO,
                          imported=self.READ_UP_TO)
        self.b._set_target_id('hr.employee', self.SOURCE_EMPLOYEE, 4242)

    def run(self, wizard):
        self._got_this_far()
        raise ValueError('базата отказа реда')


class _PhaseThatFinishes(_PhaseThatFallsOverHalfway):
    """Същата работа, без падането - близнакът срещу презастраховане."""

    def run(self, wizard):
        self._got_this_far()
        return [self.b._make_result('hr.employee', self.READ_UP_TO,
                                    self.READ_UP_TO)]


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_protocol')
class TestProtocolTellsTheTruth(TransactionCase):
    """Числата в протокола са числата на ПРОГОНА, и само на легналите редове."""

    #: Служителите на най-големия наемател в облака с 27 фирми, мерено.
    PEOPLE = 6176
    #: Докъдето стигаше един пас. Прехвърлянето седеше на 1 001 завинаги.
    FIRST_PASS = 1000

    def setUp(self):
        super().setUp()
        # Записването на напредъка прави свършеното постоянно (кронът трябва да
        # намери докъде е стигнало). В тест това би върнало самата подготовка,
        # затова се обезврежда - същото прави и sms_twilio в кора.
        self.patch(self.env.cr, 'commit', lambda: None)
        self.company = self.env['res.company'].create({'name': 'Protocol Tenant'})

    def _run_record(self, **overrides):
        values = {
            'source_url': 'http://localhost:1',
            'source_db': 'src',
            'source_login': 'admin',
            'source_password': 'secret',
            'options_json': json.dumps({'import_people': True}),
            'installed_modules_json': json.dumps(['hr_rfid']),
            'company_map_json': json.dumps({'101': self.company.id}),
        }
        values.update(overrides)
        return self.env['hr.rfid.odoo.import.run'].create(values)

    def _source(self, data, **options):
        return _PagedSource(self.env, {101: self.company.id}, options, data)

    # ── Завършил прогон казва числата на прогона ───────────────

    def test_a_finished_transfer_reports_everything_it_moved(self):
        """Три паса в три процеса: накрая протоколът казва 6 176, не 0.

        Всеки пас чете само това, което курсорът му още не е покрил, и редът в
        протокола се строи наново на всеки пас. Строен само от собствения срез,
        той докладва ФИНАЛНИЯ - а финалният по дизайн няма какво да чете. Точно
        този ред собственикът вече е чел веднъж: "0 внесени / 20 851 не дойдоха"
        върху пълно пренасяне.

        Пасовете тук минават през ЗАПИСА на прогона, защото между два паса няма
        обща памет - работникът е нов процес.
        """
        run = self._run_record()
        options = {'import_people': True}
        cursor = 'people:hr.employee'
        rest = self.PEOPLE - self.FIRST_PASS

        first = run._build_importer(options)
        first.accumulated_result(cursor, 'hr.employee',
                                 self.FIRST_PASS, self.FIRST_PASS)
        first.read_cursors[cursor] = self.FIRST_PASS
        run._save_progress({'Phase 2'}, PeopleImporter, importer=first)

        second = run._build_importer(options)
        second.accumulated_result(cursor, 'hr.employee', rest, rest)
        second.read_cursors[cursor] = second.CURSOR_FINISHED
        run._save_progress({'Phase 2'}, PeopleImporter, importer=second)

        last = run._build_importer(options)
        row = last.accumulated_result(cursor, 'hr.employee', 0, 0)

        self.assertEqual(
            (row['source_count'], row['imported_count']),
            (self.PEOPLE, self.PEOPLE),
            'Протоколът казва %s внесени от %s, а прогонът е пренесъл всички '
            '%s души на %s+%s: тоталите не преживяват смяната на процеса, значи '
            'завършило пренасяне пак се чете като провалено' % (
                row['imported_count'], row['source_count'], self.PEOPLE,
                self.FIRST_PASS, rest),
        )
        self.assertEqual(
            row['status'], 'done',
            'Пренасяне, донесло всички %s души, е отчетено като "%s" - точно '
            'редът, за който собственикът пита' % (self.PEOPLE, row['status']),
        )

    def test_what_a_pass_read_and_what_it_counted_travel_together(self):
        """Докъде е стигнал прочитът и колко е преброил се пазят ЗАЕДНО.

        Поотделно не значат нищо: курсор, минал отвъд редове, които не са
        преброени (или обратното), прави финалния протокол лъжа за прогон,
        който е работил. Затова и двете стоят на записа на прогона и се връщат
        при следващия пас.
        """
        run = self._run_record()
        cursor = 'people:hr.employee'

        first = run._build_importer({})
        first.read_cursors[cursor] = first.CURSOR_FINISHED
        first.accumulate(cursor, source=self.PEOPLE, imported=self.PEOPLE)
        run._save_progress({'Phase 2'}, PeopleImporter, importer=first)

        self.assertEqual(
            json.loads(run.read_cursors_json or '{}').get(cursor),
            first.CURSOR_FINISHED,
            'Докъде е стигнал прочитът не е записано на прогона - следващият '
            'пас започва от нулата и %s служителя се четат наново' % self.PEOPLE,
        )
        self.assertEqual(
            json.loads(run.step_totals_json or '{}').get(cursor, {}).get('imported'),
            self.PEOPLE,
            'Преброеното не е записано на прогона - новият процес брои от нула '
            'и протоколът пак казва "0 внесени" върху %s пренесени души'
            % self.PEOPLE,
        )

        fresh = run._build_importer({})
        self.assertTrue(
            fresh.read_is_finished(cursor),
            'Новият пас не знае, че прочитът е завършил, и чете %s служителя '
            'повторно' % self.PEOPLE,
        )
        self.assertEqual(
            fresh.step_totals.get(cursor, {}).get('source'), self.PEOPLE,
            'Новият пас не вижда преброеното от предишните - редът в протокола '
            'ще каже само неговия (празен) срез',
        )

    # ── Върнати редове не се броят и не се прескачат ───────────

    def test_a_step_whose_rows_were_thrown_away_counts_none_of_them(self):
        """Паднала стъпка забравя и докъде е стигнала, и колко е преброила.

        Мерено на живо: стъпка прочиташе страници, базата отказваше записа,
        savepoint-ът връщаше редовете - а курсорът беше вече отвъд тях. Следващият
        пас прескачаше ТОЧНО редовете, които не бяха легнали, а тоталите ги
        отчитаха за пренесени завинаги.

        Съседната стъпка, която е успяла, запазва своето: връщане "за всеки
        случай" на цялата фаза значи същата загуба, само от другата страна.
        """
        source = _RefusingWriteSource(
            self.env, {101: self.company.id}, {},
            {
                'hr.rfid.event.user': [
                    {'id': 1, 'event_time': '2026-08-01 07:00:00'},
                    {'id': 2, 'event_time': '2026-08-01 08:00:00'},
                ],
                'hr.rfid.event.system': [
                    {'id': 11, 'event_time': '2026-08-01 09:00:00'},
                    {'id': 12, 'event_time': '2026-08-01 10:00:00'},
                ],
            })
        phase = _TwoKindsPhase(source)
        results = phase.run(wizard=None)

        self.assertNotIn(
            _TwoKindsPhase.SECOND_CURSOR, source.read_cursors,
            'Курсорът на падналата стъпка остана напред: следващият пас ще '
            'прескочи точно 2-та реда, които базата отказа, и никой няма да '
            'разбере - на живо така изчезваха цели страници',
        )
        self.assertNotIn(
            _TwoKindsPhase.SECOND_CURSOR, source.step_totals,
            'Падналата стъпка е преброила своите 2 реда: протоколът ще ги '
            'докладва като пренесени, а savepoint-ът ги е върнал - и никой '
            'пас след това не ги брои наново',
        )

        self.assertEqual(
            source.read_cursors.get(_TwoKindsPhase.FIRST_CURSOR),
            source.CURSOR_FINISHED,
            'Стъпката, която е успяла, загуби докъде е стигнала заради '
            'съседната - същата загуба, само от другата страна',
        )
        self.assertEqual(
            source.step_totals.get(_TwoKindsPhase.FIRST_CURSOR, {}).get('imported'), 2,
            'Успялата стъпка загуби преброеното си: 2 внесени реда изчезнаха '
            'от протокола, макар да са в базата',
        )

        statuses = [r['status'] for r in results]
        self.assertIn(
            'error', statuses,
            'Падналата стъпка не остави и ред в протокола - операторът чете '
            'липсата ѝ като "тази стъпка не е минавала"',
        )

    def test_a_phase_that_fell_over_forgets_what_its_savepoint_undid(self):
        """Фонов прогон: паднала фаза връща курсора, тоталите И картата.

        savepoint-ът връща редовете, но всичко трите живеят в паметта и биха
        оцелели. Мерено на живо по синхронния път: Phase 2 падна, а 3b/4/5/6a/6b
        след нея гърмяха една по една с ForeignKeyViolation, защото картата още
        сочеше към откатнатите записи. По-тихият вариант е по-лошият - освободеният
        номер може вече да е даден на ЧУЖД запис.
        """
        run = self._run_record()
        source = self._source({})
        source._set_target_id('hr.employee', 7, 777)   # отпреди фазата
        before = source.progress_snapshot()

        finished = run._run_one_phase(
            _PhaseThatFallsOverHalfway(source), PeopleImporter)

        self.assertEqual(
            source.read_cursors, before[0],
            'Курсорът на падналата фаза остана на %s: следващият пас започва '
            'СЛЕД редове, които никога не са легнали' % (
                _PhaseThatFallsOverHalfway.READ_UP_TO),
        )
        self.assertEqual(
            source.step_totals, before[1],
            'Тоталите на падналата фаза останаха: протоколът ще докладва %s '
            'внесени души, които savepoint-ът е върнал' % (
                _PhaseThatFallsOverHalfway.READ_UP_TO),
        )
        self.assertEqual(
            source._get_target_id('hr.employee', 7), 777,
            'Мапингите отпреди падналата фаза трябва да оцелеят',
        )
        self.assertFalse(
            source._get_target_id(
                'hr.employee', _PhaseThatFallsOverHalfway.SOURCE_EMPLOYEE),
            'Мапинг от откатната фаза остана: следващата фаза ще запише връзка '
            'към запис, който не съществува - или към чужд',
        )
        self.assertTrue(
            finished,
            'Падналата фаза трябва да се смята за приключена, иначе същият '
            'провал се върти безкрайно',
        )
        self.assertTrue(
            run.log_ids.filtered(lambda l: l.status == 'error'),
            'Падналата фаза не остави ред в протокола - операторът не разбира '
            'какво липсва',
        )

    def test_a_phase_that_worked_keeps_every_number_it_reported(self):
        """Отрицателният близнак: успяла фаза НЕ губи нищо.

        Връщане на напредъка при всяка фаза "за всеки случай" е същият дефект,
        обърнат: пренесените редове остават в базата, но прогонът ги чете наново
        и протоколът ги брои от нула.
        """
        run = self._run_record()
        source = self._source({})

        run._run_one_phase(_PhaseThatFinishes(source), PeopleImporter)

        self.assertEqual(
            source.read_cursors.get(_PhaseThatFinishes.CURSOR),
            _PhaseThatFinishes.READ_UP_TO,
            'Успялата фаза загуби докъде е стигнала - следващият пас чете '
            'първите %s реда наново' % _PhaseThatFinishes.READ_UP_TO,
        )
        self.assertEqual(
            source.step_totals.get(_PhaseThatFinishes.CURSOR, {}).get('imported'),
            _PhaseThatFinishes.READ_UP_TO,
            'Успялата фаза загуби преброеното: %s внесени души изчезват от '
            'протокола' % _PhaseThatFinishes.READ_UP_TO,
        )
        self.assertEqual(
            source._get_target_id(
                'hr.employee', _PhaseThatFinishes.SOURCE_EMPLOYEE), 4242,
            'Успялата фаза загуби картата source->target и следващата фаза ще '
            'сметне вече пренесените хора за непознати',
        )

    def test_the_operators_own_transfer_also_forgets_a_rolled_back_slice(self):
        """Синхронният път (от съветника) пази същото обещание.

        Двата пътя пишат едни и същи данни; гаранция, дадена само в единия,
        значи че операторът получава различен протокол според това как е пуснал
        пренасянето.
        """
        wiz = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:1',
            'source_login': 'admin',
            'source_password': 'secret',
        })
        source = self._source({})
        before = source.progress_snapshot()

        wiz._run_phase('Phase 2', 'People',
                       _PhaseThatFallsOverHalfway(source), 0, 1)

        self.assertEqual(
            source.read_cursors, before[0],
            'Курсорът остана напред след откатната фаза - следващият пас '
            'прескача %s реда, които не са легнали'
            % _PhaseThatFallsOverHalfway.READ_UP_TO,
        )
        self.assertEqual(
            source.step_totals, before[1],
            'Тоталите останаха след откатната фаза - протоколът ще докладва '
            '%s внесени души, които ги няма в базата'
            % _PhaseThatFallsOverHalfway.READ_UP_TO,
        )

    # ── Истинската нула остава тревога ─────────────────────────

    def test_a_transfer_that_moved_nothing_is_never_reported_as_finished(self):
        """Нула внесени при пълен източник е тревога, не "готово".

        Тоталите на прогона съществуват, за да не гърми фалшива тревога на
        финалния (празен) пас. Те НЕ бива да заглушат истинската: 6 176 записа
        в другата система и нито един тук е провал, а от числата провалът и
        чистият прогон изглеждат еднакво.
        """
        base = self._source({})
        row = base.accumulated_result('people:hr.employee', 'hr.employee',
                                      self.PEOPLE, 0)

        self.assertEqual(
            row['status'], 'error',
            'Другата система държи %s записа, нито един не е дошъл, а редът е '
            '"%s": счупено пренасяне се чете като чисто'
            % (self.PEOPLE, row['status']),
        )
        self.assertTrue(
            row['error'],
            'Нула от %s дошли, без обяснена причина - операторът няма откъде '
            'да започне' % self.PEOPLE,
        )
        self.assertIn(
            str(self.PEOPLE), row['error'],
            'Причината не казва КОЛКО записа са останали в другата система',
        )

    def test_nothing_of_that_kind_is_not_the_same_as_all_of_it_lost(self):
        """Отрицателният близнак: празен източник е "готово", не провал.

        Наемател без такива данни и наемател, чиито данни са изпаднали, дават
        едни и същи нули. Разликата е единственото, по което операторът може да
        различи чист прогон от счупен.
        """
        base = self._source({})
        row = base.accumulated_result('empty:hr.rfid.card', 'hr.rfid.card', 0, 0)
        self.assertEqual(
            row['status'], 'done',
            'Наемател, който няма такива данни, е отчетен като "%s" - всеки '
            'чист прогон изглежда счупен и тревогата губи смисъл'
            % row['status'],
        )

        partly = self._source({})
        row = partly.accumulated_result('people:hr.employee', 'hr.employee',
                                        self.PEOPLE, self.FIRST_PASS)
        self.assertEqual(
            row['status'], 'partial',
            'Дошли са %s от %s души, а редът казва "%s": непълно пренасяне се '
            'чете като завършено' % (self.FIRST_PASS, self.PEOPLE,
                                     row['status']),
        )


class _PreviewCountProxy:
    """Източник, който брои РАЗЛИЧНО според това как го питаш.

    Точно както истинският: живите записи, или живите и архивираните. Мерено на
    живо на облака с 27 фирми - разликата е 2 110 карти и 192 души.
    """

    #: Каквото вижда преглед без архивираните - числата от живия екран.
    LIVE_ONLY = {'hr.rfid.card': 6395, 'hr.employee': 5984}
    #: Каквото донесе пренасянето, защото прочитът чете и архивираните.
    ARCHIVED_TOO = {'hr.rfid.card': 8505, 'hr.employee': 6176}

    def __init__(self, refuses=()):
        self.counts = []
        self.refuses = set(refuses)

    def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
        kwargs = kwargs or {}
        if method == 'fields_get':
            return {'active': {}, 'company_id': {}}
        if method == 'search_count':
            self.counts.append({'model': model, 'domain': args[0],
                                'kwargs': kwargs})
            if model in self.refuses:
                raise xmlrpc.client.Fault(
                    2, "Object %s doesn't exist" % model)
            archived_too = kwargs.get('context', {}).get(
                'active_test', True) is False
            table = self.ARCHIVED_TOO if archived_too else self.LIVE_ONLY
            return table.get(model, 7)
        return 0


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_protocol')
class TestThePagePromisesWhatTheTransferBrings(TransactionCase):
    """Числата преди старта са числата, срещу които се чете протоколът.

    Мерено на живо: страницата обеща 6 395 карти и 5 984 души, пренасянето
    донесе 8 505 и 6 176. Операторът сравнява едното с другото, вижда повече
    записи, отколкото са му обещани, и не знае кое от двете да вярва - защото
    страницата броеше без архивираните, а прочитът ги чете.
    """

    def _wizard(self):
        wiz = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:1',
            'source_db': 'src',
            'source_login': 'admin',
            'source_password': 'secret',
            'source_uid': 2,
        })
        company = self.env['res.company'].create({'name': 'Preview Tenant'})
        self.env['hr.rfid.odoo.import.company.line'].create({
            'wizard_id': wiz.id,
            'source_id': 101,
            'source_name': 'Наемател 101',
            'do_import': True,
            'target_company_id': company.id,
        })
        return wiz

    def _counter(self, proxy):
        """`BaseImporter` без мрежа - само броячът и неговият източник."""
        base = BaseImporter.__new__(BaseImporter)
        base.env = self.env
        base.source_db = 'src'
        base.source_uid = 2
        base.source_password = 'x'
        base.company_map = {101: self.env.company.id}
        base.id_map = {}
        base.options = {}
        base._field_cache = {}
        base.rpc_models = proxy
        base.refused_fields = {}
        return base

    def _preview_with(self, proxy):
        wiz = self._wizard()
        counter = self._counter(proxy)
        model_cls = self.registry['hr.rfid.odoo.import.wiz']
        self.patch(model_cls, '_conflict_probe_importer',
                   lambda self_, company_ids: counter)
        # Сблъсъците се откриват по друг път и имат свои тестове; тук се съди
        # само за числата на страницата.
        self.patch(model_cls, '_detect_conflicts',
                   lambda self_, models_proxy, company_ids: None)
        wiz.action_preview()
        return wiz

    def test_the_page_counts_the_records_the_transfer_will_actually_bring(self):
        """Обещаните карти са 8 505, колкото пристигат, не 6 395.

        Прочитът на пренасянето чете и архивираните (архивиран модул иначе
        скрива всичко под себе си), затова и броенето трябва да е по същата ос.
        """
        proxy = _PreviewCountProxy()
        wiz = self._preview_with(proxy)
        text = wiz.preview_text or ''

        self.assertIn(
            '8505', text,
            'Страницата не обещава 8 505 карти, а пренасянето донася точно '
            'толкова: операторът сравнява протокола с грешно число',
        )
        self.assertNotIn(
            '6395', text,
            'Страницата обещава 6 395 карти (само живите), а пристигат 8 505: '
            'разликата от 2 110 изглежда като необяснено надхвърляне',
        )
        self.assertIn(
            '6176', text,
            'Страницата не обещава 6 176 души, колкото пренасянето донася',
        )
        self.assertNotIn(
            '5984', text,
            'Страницата обещава 5 984 души, а пристигат 6 176 - 192 души '
            'повече от обещаното, без обяснение',
        )

        self.assertTrue(proxy.counts, 'Страницата не е питала източника изобщо')
        for call in proxy.counts:
            self.assertIs(
                call['kwargs'].get('context', {}).get('active_test'), False,
                'Броенето на %s е питано без архивираните, а прочитът ги чете: '
                'обещаното число не може да съвпадне с пренесеното'
                % call['model'],
            )
        self.assertEqual(
            wiz.state, 'confirm',
            'Страницата с числата не е стигнала до потвърждение',
        )

    def test_a_kind_the_other_system_will_not_count_is_named_not_hidden(self):
        """Отрицателният близнак: отказано броене се НАЗОВАВА, а не чупи страницата.

        По-стар източник няма всеки модел (мерено на Odoo 14 - там няма дневни
        обобщения изобщо) и отказва да го преброи. Това не бива нито да събори
        страницата, нито да мине като нула - нулата се чете като "няма такива
        данни".
        """
        proxy = _PreviewCountProxy(refuses=('hr.rfid.zone',))
        wiz = self._preview_with(proxy)
        text = wiz.preview_text or ''

        self.assertEqual(
            wiz.state, 'confirm',
            'Един непреброим вид събори цялата страница - операторът не вижда '
            'нито едно от останалите числа',
        )
        self.assertIn(
            '8505', text,
            'Останалите числа изчезнаха заедно с непреброимия вид',
        )
        zones = self.env._('Zones')
        self.assertIn(
            zones, text,
            'Видът, който другата система отказа да преброи, изобщо не се '
            'споменава - операторът не знае, че за него няма число',
        )
        self.assertNotIn(
            '%s: 0' % zones, text,
            'Непреброимият вид е минал като нула, а нулата се чете като "няма '
            'такива данни": операторът ще сметне за нормално, че после не '
            'пристига нищо',
        )
        self.assertEqual(
            len([c for c in proxy.counts if c['model'] == 'hr.rfid.zone']), 1,
            'Отказът е бил преглътнат мълчаливо, вместо да стигне до реда за '
            'този вид данни',
        )


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_protocol')
class TestEveryKindOfDataIsAskedAbout(TransactionCase):
    """Каквото една фаза може да донесе, за него източникът СЕ ПИТА.

    Мерено на живо на облака с 27 фирми: дневните обобщения се водят от
    hr_attendance_late, никоя фаза не го назоваваше, източникът не беше питан,
    отметката остана свалена сама и 152 469 реда останаха там. В протокола
    нямаше и ред за това - свалена отметка не оставя следа, а операторът чете
    липсата като "нямаше такива данни".
    """

    def _wizard(self):
        return self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:1',
            'source_db': 'src',
            'source_login': 'admin',
            'source_password': 'secret',
        })

    def _connect(self, wiz, keeps):
        """Свързва съветника към източник, който води точно `keeps`.

        Питането е през xmlrpc в самия модул; тестът го подменя, за да няма
        мрежа, и записва за какво е бил питан източникът.
        """
        asked = {}

        class _Proxy:
            def __init__(self, url, allow_none=True):
                self.url = url

            def authenticate(self, db, login, password, context):
                return 2

            def execute_kw(self, db, uid, password, model, method, args,
                           kwargs=None):
                if model == 'ir.module.module':
                    leaf = next(l for l in args[0] if l[0] == 'name')
                    if leaf[1] == 'in':
                        asked['modules'] = list(leaf[2])
                        return [{'name': n} for n in keeps if n in leaf[2]]
                    return [{'latest_version': '15.0.1.0.0'}]
                if model == 'res.company':
                    return [{'id': 101, 'name': 'Наемател 101'}]
                return []

        self.patch(import_wizard, 'xmlrpc', types.SimpleNamespace(
            client=types.SimpleNamespace(
                Fault=xmlrpc.client.Fault, ServerProxy=_Proxy)))
        wiz.action_test_connection()
        return asked

    def test_the_other_system_is_asked_about_every_kind_a_phase_can_bring(self):
        """Питаме за точно това, което фазите обявяват - нищо по-малко.

        Списък, държан на ръка в самото питане, изостава при всяка нова фаза;
        точно така камерите не бяха потърсени изобщо, а дневните обобщения -
        152 469 реда - останаха при клиента.
        """
        wiz = self._wizard()
        asked = self._connect(wiz, keeps=['hr_rfid'])

        self.assertEqual(
            sorted(asked.get('modules') or []), sorted(source_probe_modules()),
            'Питането не идва от фазите: %s вместо %s. Ръчният списък изостава '
            'при всяка нова фаза и данните остават при клиента' % (
                sorted(asked.get('modules') or []),
                sorted(source_probe_modules())),
        )
        self.assertIn(
            'hr_attendance_late', asked.get('modules') or [],
            'Модулът, който води дневните обобщения, не се пита - отметката не '
            'може да се вдигне и 152 469 реда остават без ред в протокола',
        )

    def test_a_kind_the_other_system_keeps_can_therefore_be_switched_on(self):
        """Щом другата система го води, операторът може да го поиска.

        Обратното е дефектът: източникът не беше питан, отметката остана
        свалена сама и 152 469 дневни обобщения не бяха дори предложени за
        пренасяне.
        """
        wiz = self._wizard()
        self._connect(wiz, keeps=['hr_rfid', 'hr_attendance_multi_rfid',
                                  'hr_attendance_late'])

        self.assertTrue(
            wiz.source_has_attendance_late,
            'Източникът води дневните обобщения, а съветникът не го е разбрал: '
            '152 469 реда остават непоискани',
        )

        wiz.import_attendance_extra = True
        if not wiz.target_has_attendance_late:
            self.skipTest('hr_attendance_late не е инсталиран тук - целта няма '
                          'къде да приеме обобщенията')
        options = wiz._build_options()
        self.assertTrue(
            options['import_attendance_extra'],
            'Операторът е поискал дневните обобщения, източникът ги води и '
            'тази система може да ги приеме - а отметката пак стига до '
            'прогона свалена, тоест 152 469 реда остават непоискани',
        )

    def test_a_kind_the_other_system_does_not_keep_is_never_promised(self):
        """Отрицателният близнак: каквото го няма там, не се обещава тук."""
        wiz = self._wizard()
        self._connect(wiz, keeps=['hr_rfid', 'hr_attendance_multi_rfid'])

        self.assertFalse(
            wiz.source_has_attendance_late,
            'Съветникът реши, че другата система води дневни обобщения, макар '
            'да не е инсталирала модула им - стъпката ще гърми на първия си ред',
        )
        wiz.import_attendance_extra = True
        self.assertFalse(
            wiz._build_options()['import_attendance_extra'],
            'Пренасянето ще поиска дневни обобщения от система, която не води '
            'такива, и ще ги обещае в протокола',
        )

    def test_what_is_left_out_still_gets_a_line_the_operator_can_read(self):
        """Пропуснатото се вижда в протокола, с причина на човешки език.

        Тишината е дефектът: фаза, пропусната без ред, изглежда точно като фаза,
        която е минала и не е намерила нищо. Така 152 469 дневни обобщения
        останаха незабелязани.
        """
        wiz = self._wizard()
        options = {'import_attendance': False, 'import_attendance_extra': False}
        plan = {cls.NAME: reason for cls, reason
                in phase_plan(self.env, options,
                              {'hr_rfid', 'hr_attendance_multi_rfid'})}
        reason = plan.get(AttendanceImporter.NAME)

        self.assertTrue(
            reason,
            'Присъствията са пропуснати, без планът да казва защо - операторът '
            'няма как да разбере, че липсват',
        )
        wiz._log_skipped_phase(AttendanceImporter, reason)

        line = self.env['hr.rfid.odoo.import.log'].search(
            [('model', '=', AttendanceImporter.NAME),
             ('status', '=', 'skipped')], order='id desc', limit=1)
        self.assertTrue(
            line, 'Пропуснатата фаза не остави ред в протокола изобщо')
        self.assertEqual(
            line.error_message, reason,
            'Редът в протокола не носи причината, която планът е сметнал',
        )
        self.assertIn(
            reason, wiz.progress_text or '',
            'Операторът не вижда пропуска и в хода на прехвърлянето',
        )


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_protocol')
class TestADayIsNotSummedTwice(TransactionCase):
    """Един работен ден на един човек има ЕДИН ред, каквото и да се пренася.

    Дневните обобщения се смятат и ТУК, от собствения планировчик на тази
    система, за дните, които вижда - а след пренасяне тя вижда и току-що
    получените. Затова последните дни завършваха с ДВА реда за един човек:
    единият дошъл, другият сметнат тук. Нищо не го отказва (няма уникален
    индекс), а ден с два реда е ден, броен двойно във всеки отчет над него.
    Мерено при пренасянето на облака с 27 фирми: 10 такива дни, все вчера и
    днес.

    Редът, който вече е тук, се ОСТАВЯ, а не се подменя: сметнат е от
    присъствията на ден, който може още да не е свършил, и подмяната му с
    число, взето преди полунощ, е същото двойно счетоводство наобратно.
    """

    #: Дните, които на живо завършиха с два реда за един човек.
    MEASURED_DOUBLE_DAYS = 10
    #: Денят, който тази система вече е обобщила сама.
    SUMMED_HERE = '2026-08-16'
    #: Ден, който тя още не е обобщила.
    NOT_SUMMED_HERE = '2026-08-15'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Roll-up Tenant'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Работник с обобщения', 'company_id': cls.company.id,
        })

    def setUp(self):
        super().setUp()
        if 'hr.attendance.extra' not in self.env:
            self.skipTest('дневните обобщения не са част от тази инсталация')

    def _source(self):
        """Другата система държи три обобщения, едно от които вече е сметнато тук.

        Датите идват като ТЕКСТ, защото така ги подава другата система по
        мрежата - същото, което прави и стъпката за присъствията, когато реже
        деня от `check_in[:10]`. Тук това е носещо: денят от другата система и
        денят в базата трябва да се разпознаят като ЕДИН И СЪЩИ ден, макар да
        идват в различен вид.
        """
        data = {'hr.attendance.extra': [
            {'id': 1, 'employee_id': [7, 'Работник'], 'department_id': False,
             'for_date': self.SUMMED_HERE, 'shift_number': 1,
             'actual_work_time': 8.0},
            {'id': 2, 'employee_id': [7, 'Работник'], 'department_id': False,
             'for_date': self.NOT_SUMMED_HERE, 'shift_number': 1,
             'actual_work_time': 7.0},
            {'id': 3, 'employee_id': [7, 'Работник'], 'department_id': False,
             'for_date': self.SUMMED_HERE, 'shift_number': 2,
             'actual_work_time': 4.0},
        ]}
        src = _FakeSource(self.env, {101: self.company.id},
                          {'import_attendance_extra': True}, data)
        src.id_map = {'hr.employee': {7: self.employee.id}}
        return src

    def _already_summed_here(self):
        return self.env['hr.attendance.extra'].create({
            'employee_id': self.employee.id,
            'for_date': self.SUMMED_HERE,
            'shift_number': 1,
            'actual_work_time': 7.5,
        })

    def _import(self):
        source = self._source()
        phase = AttendanceImporter(source)
        phase._import_attendance_extra()
        return source, phase

    def test_a_day_this_system_has_already_worked_out_is_not_sent_again(self):
        """Денят, обобщен тук, не получава втори ред от пренасянето.

        Мерено при пренасянето на облака с 27 фирми: 10 дни завършиха с по два
        реда за един човек, защото и двете системи бяха сметнали един и същи
        ден.
        """
        ours = self._already_summed_here()
        source, _phase = self._import()

        call = source.last_bulk('hr.attendance.extra')
        self.assertIsNotNone(
            call, 'Нито едно обобщение не е стигнало до записа')
        self.assertNotIn(
            1, call['source_ids'],
            'Денят %s, който тази система вече е обобщила сама, се внася втори '
            'път: човекът получава ДВА реда за един ден и всеки отчет над него '
            'брои двойно - на живо така пострадаха %s дни. Сравнението е между '
            'датата, подадена от другата система, и датата в базата - ако те не '
            'се разпознават като един и същи ден, пропускането е мълчаливо '
            'бездействие' % (self.SUMMED_HERE, self.MEASURED_DOUBLE_DAYS),
        )
        self.assertEqual(
            self.env['hr.attendance.extra'].search_count(
                [('employee_id', '=', self.employee.id),
                 ('for_date', '=', self.SUMMED_HERE),
                 ('shift_number', '=', 1)]), 1,
            'Денят %s свърши с повече от един ред за един човек' % self.SUMMED_HERE,
        )
        self.assertEqual(
            ours.actual_work_time, 7.5,
            'Редът, който вече е тук, е подменен: той е сметнат от присъствията '
            'на ден, който може още да не е свършил, а числото отсреща е взето '
            'преди полунощ - същото двойно счетоводство наобратно',
        )

    def test_a_day_this_system_has_not_worked_out_still_arrives(self):
        """Отрицателният близнак: пропускането не бива да изяде останалите дни."""
        self._already_summed_here()
        source, _phase = self._import()

        call = source.last_bulk('hr.attendance.extra')
        self.assertIn(
            2, call['source_ids'],
            'Денят %s, който тази система НЕ е обобщила, също остана вън: '
            'предпазването от двоен ред изхвърли истински данни'
            % self.NOT_SUMMED_HERE,
        )
        self.assertIn(
            3, call['source_ids'],
            'Втората смяна на %s е сметната за същия ред като първата: смяна с '
            'друг номер е ДРУГ ред и изчезва без следа' % self.SUMMED_HERE,
        )

    def test_the_protocol_says_how_many_days_were_left_alone(self):
        """Оставеният ден се брои и се обяснява - иначе изглежда като загуба."""
        self._already_summed_here()
        _source, phase = self._import()

        row = next(r for r in phase.results
                   if r['model'] == 'hr.attendance.extra')
        self.assertEqual(
            row['skipped_count'], 1,
            'Оставеният ден не е преброен: от числата "нямаше такива данни" и '
            '"един ден беше оставен нарочно" изглеждат еднакво',
        )
        self.assertTrue(
            row['error'],
            'Оставеният ден е без обяснена причина - операторът го чете като '
            'изгубен ред',
        )
        self.assertIn(
            '1', row['error'],
            'Причината не казва КОЛКО дни са оставени, а на живо те бяха %s'
            % self.MEASURED_DOUBLE_DAYS,
        )
