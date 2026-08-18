# -*- coding: utf-8 -*-
"""Един източник с ДВА наемателя, и втори източник след него - без смесване.

Бизнес твърдение (собственик, 2026-08-17, при пренасянето на облака с 27
фирми): всеки наемател получава СВОЕТО и само своето. Клиентът, който отваря
базата след пренасянето, не бива да вижда чужди видове отпуск, нито собствената
си карта, вписана на човек от друга фирма, нито двойни слотове за график, при
които никой не може да каже към кой от двата сочи едно право за врата.

Измерено на живо, преди поправките - всяко от тези четири неща се случи:

* Видовете отпуск се четат БЕЗ фирмен филтър (един вид принадлежи на един
  наемател), но пристигаха БЕЗ фирма, тоест глобални: всичките 22 вида на
  облака с 27 фирми се предлагаха на всеки един наемател.
* Графиците са СЛОТОВЕ, които самата цел създава по 16 на фирма. Пренасянето
  създаваше свои ДО тях: 32 записа за 16 хардуерни слота на наемател.
* Контакт без фирма (в Odoo контактът е споделен и обикновено няма своя фирма)
  влизаше във фирмата по подразбиране на целта, "My Company". Всичките 11
  картодържащи контакта на един Odoo 14 наемател легнаха там, и финалната
  проверка после отчете 19 от картите му като държани от човек на друга фирма -
  и беше права, защото бяха.
* Записът на отделовите "разрешени групи за достъп" фабрикуваше правото по
  подразбиране на всеки член без права и махаше всяко право извън списъка,
  който току-що е получил: шест души тук получиха врати, които на другата
  система не са имали.

Двойниците ОТРИЧАТ, не само потвърждават: контакт, който този наемател не
ползва, НЕ бива да бъде довлечен; вид отпуск на наемател, който не пренасяме,
НЕ бива да стане глобален; втори прогон от ДРУГА система не бива да пипне нищо
от първата; и извън пренасяне отделът трябва да СИ управлява членовете както
досега - иначе поправката тихо е изключила реална функция на hr_rfid.
"""

from collections import Counter

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.access_importer import AccessImporter
from ..models.importers.base_importer import (
    IMPORT_CONTEXT,
    normalise_source_slug,
)
from ..models.importers.core_importer import CoreImporter
from ..models.importers.leave_importer import LeaveImporter
from ..models.importers.people_importer import PeopleImporter
from .test_second_run_changes_nothing import _StubbedSource

#: Как другата система номерира фирмите си. 303 е наемател, който НЕ пренасяме -
#: той е в базата на източника, но не е в този прогон.
TENANT_A = 101
TENANT_B = 202
TENANT_WE_ARE_NOT_MOVING = 303
#: Единственият наемател на ВТОРАТА система, която пренасяме след първата.
OTHER_SYSTEM_TENANT = 501

#: Двете системи се различават по идентичност (влиза в external ID-тата).
FIRST_SYSTEM = 'cloud_of_27_tenants'
SECOND_SYSTEM = 'odoo14_single_tenant'

#: Номера на записите в първия източник. Изписани, за да може съобщението при
#: провал да назове реален запис.
TS_A_ROUND_THE_CLOCK = 201
TS_A_DAY_SHIFT = 202
TS_B_ROUND_THE_CLOCK = 203
CONTACT_A_WITH_CARD = 901
CONTACT_A_IN_A_GROUP = 904
CONTACT_B_WITH_CARD = 902
CONTACT_NOBODY_USES = 903
EMPLOYEE_A = 1001
EMPLOYEE_B = 1002
GROUP_A = 701
GROUP_B = 702
GROUP_A_CONTACT_REL = 801
CARD_A_OF_THE_EMPLOYEE = 851
CARD_A_OF_THE_CONTACT = 852
CARD_B_OF_THE_EMPLOYEE = 853
CARD_B_OF_THE_CONTACT = 854
LEAVE_TYPE_A = 601
LEAVE_TYPE_B = 602
LEAVE_TYPE_WE_ARE_NOT_MOVING = 603

#: Номера на записите във втория източник - различни, както биха били наистина.
SECOND_TS = 1201
SECOND_CONTACT = 1901
SECOND_EMPLOYEE = 1301
SECOND_GROUP = 1701
SECOND_CARD = 1851
SECOND_LEAVE_TYPE = 1601

#: Какво е отметнал операторът. `import_all_partners` е ИЗКЛЮЧЕНО нарочно:
#: тогава обхватът на контактите е "тези, които този наемател ползва", а това е
#: точно мястото, където контакт без фирма или отпада, или бива довлечен по
#: погрешка.
OPTIONS = {
    'import_hardware': True,
    'import_people': True,
    'import_all_partners': False,
    'import_all_employees': True,
    'import_users': False,
    'import_images': False,
    'import_access': True,
    'import_leaves': True,
}

#: Моделите, които носят фирма и по които се брои "какво има всеки наемател".
COMPANY_BOUND_MODELS = (
    'res.partner',
    'hr.employee',
    'hr.rfid.card',
    'hr.rfid.access.group',
    'hr.rfid.time.schedule',
    'hr.leave.type',
)


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_multicompany')
class TestTwoTenantsDoNotMix(TransactionCase):
    """Два наемателя в един източник, внесени в една цел, и втора система след тях."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Създаването на фирма кара hr_rfid да ѝ направи своите 16 слота -
        # точно записите, които пренасянето трябва да ОСИНОВИ, а не да удвои.
        cls.tenant_a = cls.env['res.company'].create({'name': 'Наемател А'})
        cls.tenant_b = cls.env['res.company'].create({'name': 'Наемател Б'})
        cls.tenant_c = cls.env['res.company'].create({'name': 'Наемател В'})
        cls.company_map = {TENANT_A: cls.tenant_a.id, TENANT_B: cls.tenant_b.id}
        cls.other_company_map = {OTHER_SYSTEM_TENANT: cls.tenant_c.id}
        cls.has_leaves = 'hr.leave.type' in cls.env

    # ── съдържанието на другите системи ──────────────────────

    @classmethod
    def _first_system(cls):
        """Облакът: два наемателя, които пренасяме, и един, който не пренасяме."""
        company_a = [TENANT_A, 'Наемател А']
        company_b = [TENANT_B, 'Наемател Б']
        company_out = [TENANT_WE_ARE_NOT_MOVING, 'Наемател извън прогона']
        data = {
            'hr.rfid.time.schedule': [
                {'id': TS_A_ROUND_THE_CLOCK, 'name': 'Денонощно',
                 'number': 1, 'company_id': company_a, 'ts_data': False},
                {'id': TS_A_DAY_SHIFT, 'name': 'Дневна смяна',
                 'number': 2, 'company_id': company_a, 'ts_data': False},
                {'id': TS_B_ROUND_THE_CLOCK, 'name': 'Денонощно',
                 'number': 1, 'company_id': company_b, 'ts_data': False},
            ],
            'res.partner': [
                # Контакт без СВОЯ фирма, който държи карта на наемател А.
                {'id': CONTACT_A_WITH_CARD, 'name': 'Външен изпълнител при А',
                 'company_id': False, 'active': True, 'parent_id': False},
                # Контакт без своя фирма, до когото се стига САМО през
                # членството в група за достъп на наемател А.
                {'id': CONTACT_A_IN_A_GROUP, 'name': 'Гост в група на А',
                 'company_id': False, 'active': True, 'parent_id': False},
                # Контакт СЪС своя фирма - наемател Б.
                {'id': CONTACT_B_WITH_CARD, 'name': 'Външен изпълнител при Б',
                 'company_id': company_b, 'active': True, 'parent_id': False},
                # Контакт, който никой от двамата наематели не ползва.
                {'id': CONTACT_NOBODY_USES, 'name': 'Ничий контакт',
                 'company_id': False, 'active': True, 'parent_id': False},
            ],
            'hr.employee': [
                {'id': EMPLOYEE_A, 'name': 'Охрана при А',
                 'company_id': company_a, 'active': True},
                {'id': EMPLOYEE_B, 'name': 'Охрана при Б',
                 'company_id': company_b, 'active': True},
            ],
            'hr.rfid.access.group': [
                {'id': GROUP_A, 'name': 'Портал А', 'company_id': company_a,
                 'inherited_ids': [], 'department_ids': []},
                {'id': GROUP_B, 'name': 'Портал Б', 'company_id': company_b,
                 'inherited_ids': [], 'department_ids': []},
            ],
            'hr.rfid.access.group.contact.rel': [
                {'id': GROUP_A_CONTACT_REL,
                 'access_group_id': [GROUP_A, 'Портал А'],
                 'contact_id': [CONTACT_A_IN_A_GROUP, 'Гост в група на А'],
                 'state': True, 'internal_state': True},
            ],
            'hr.rfid.card': [
                {'id': CARD_A_OF_THE_EMPLOYEE, 'number': '0000100001',
                 'company_id': company_a, 'active': True,
                 'employee_id': [EMPLOYEE_A, 'Охрана при А']},
                {'id': CARD_A_OF_THE_CONTACT, 'number': '0000100002',
                 'company_id': company_a, 'active': True,
                 'contact_id': [CONTACT_A_WITH_CARD, 'Външен изпълнител при А']},
                {'id': CARD_B_OF_THE_EMPLOYEE, 'number': '0000100003',
                 'company_id': company_b, 'active': True,
                 'employee_id': [EMPLOYEE_B, 'Охрана при Б']},
                {'id': CARD_B_OF_THE_CONTACT, 'number': '0000100004',
                 'company_id': company_b, 'active': True,
                 'contact_id': [CONTACT_B_WITH_CARD, 'Външен изпълнител при Б']},
            ],
        }
        if cls.has_leaves:
            # Видовете отпуск се четат БЕЗ фирмен филтър - единственият глобален
            # прочит в тази верига, и точно затова тук живееше дефектът.
            data['hr.leave.type'] = [
                {'id': LEAVE_TYPE_A, 'name': 'Годишен при А',
                 'active': True, 'company_id': company_a},
                {'id': LEAVE_TYPE_B, 'name': 'Годишен при Б',
                 'active': True, 'company_id': company_b},
                {'id': LEAVE_TYPE_WE_ARE_NOT_MOVING,
                 'name': 'Годишен при наемател извън прогона',
                 'active': True, 'company_id': company_out},
            ]
            data['hr.leave.allocation'] = []
            data['hr.leave'] = []
        return data

    @classmethod
    def _second_system(cls):
        """Съвсем друга система, един наемател, внесен в трета фирма тук."""
        company = [OTHER_SYSTEM_TENANT, 'Наемател В']
        data = {
            'hr.rfid.time.schedule': [
                {'id': SECOND_TS, 'name': 'Денонощно', 'number': 1,
                 'company_id': company, 'ts_data': False},
            ],
            'res.partner': [
                {'id': SECOND_CONTACT, 'name': 'Външен изпълнител при В',
                 'company_id': False, 'active': True, 'parent_id': False},
            ],
            'hr.employee': [
                {'id': SECOND_EMPLOYEE, 'name': 'Охрана при В',
                 'company_id': company, 'active': True},
            ],
            'hr.rfid.access.group': [
                {'id': SECOND_GROUP, 'name': 'Портал В', 'company_id': company,
                 'inherited_ids': [], 'department_ids': []},
            ],
            'hr.rfid.card': [
                {'id': SECOND_CARD, 'number': '0000200001',
                 'company_id': company, 'active': True,
                 'contact_id': [SECOND_CONTACT, 'Външен изпълнител при В']},
            ],
        }
        if cls.has_leaves:
            data['hr.leave.type'] = [
                {'id': SECOND_LEAVE_TYPE, 'name': 'Годишен при В',
                 'active': True, 'company_id': company},
            ]
            data['hr.leave.allocation'] = []
            data['hr.leave'] = []
        return data

    # ── как се движи прехвърлянето ───────────────────────────

    def _source(self, data, company_map, system_name):
        """Другата система, отговаряна от речник вместо по мрежата.

        Само четенето е подменено: всеки запис минава през истинския моделен
        слой, със собствените странични ефекти на модулите, тоест броеното е
        онова, което клиентът би получил. Идентичността на системата се задава
        изрично - тя влиза в external ID-тата, и точно по нея вторият източник
        не може да пипне записите на първия.
        """
        source = _StubbedSource(self.env, data, dict(company_map), dict(OPTIONS))
        source.source_db = system_name
        source.source_slug = normalise_source_slug(system_name)
        return source

    def _run_the_transfer(self, source):
        """Веригата фази, които решават фирмената принадлежност.

        Всяка стъпка казва какво е станало с нея, и тези редове се четат тук:
        фаза не спира на счупена стъпка, тя я записва и продължава - което е
        правилно, но прогон, в който ВСЯКА стъпка е паднала, също не създава
        нищо, а това е и видът на верен втори прогон. Без прочитане на редовете
        проверките отдолу биха светнали зелено над прехвърляне, което не е
        свършило нищо.
        """
        results = []
        core = CoreImporter(source)
        results += core.steps(core._import_time_schedules)
        results += PeopleImporter(source).run(None) or []
        if self.has_leaves:
            results += LeaveImporter(source).run(None) or []
        access = AccessImporter(source)
        results += access.steps(
            access._import_access_groups,
            access._import_ag_contact_rels,
            access._import_cards,
        )
        self.env.flush_all()
        broken = ['%s: %s' % (row.get('model', '?'), row.get('error', ''))
                  for row in results if row.get('status') == 'error']
        self.assertFalse(
            broken,
            'стъпки от този прогон не са могли да се изпълнят, значи нищо '
            'непоявило се не доказва нищо: %s' % '; '.join(broken))
        return results

    # ── помощни ──────────────────────────────────────────────

    def _arrived(self, source, model, source_id):
        """Записът в целта, в който е пренесен даден запис на източника."""
        xid = source._xml_id(model.replace('.', '_'), source_id)
        module, _dot, name = xid.partition('.')
        entry = self.env['ir.model.data'].sudo().search(
            [('module', '=', module), ('name', '=', name),
             ('model', '=', model)], limit=1)
        Model = self.env[model].sudo().with_context(active_test=False)
        return Model.browse(entry.res_id).exists() if entry else Model.browse()

    def _per_company_ids(self, companies):
        """{(модел, фирма): редовете, които тя държи в момента}."""
        out = {}
        for model in COMPANY_BOUND_MODELS:
            if model not in self.env:
                continue
            Model = self.env[model].sudo().with_context(active_test=False)
            for company in companies:
                out[(model, company.id)] = set(
                    Model.search([('company_id', '=', company.id)]).ids)
        return out

    def _slots_of(self, company):
        return self.env['hr.rfid.time.schedule'].sudo().with_context(
            active_test=False).search([('company_id', '=', company.id)])

    def _assert_it_really_moved_something(self, source):
        """Иначе всяка проверка отдолу би минала над мъртво прехвърляне."""
        for model, source_id in (
                ('hr.employee', EMPLOYEE_A),
                ('res.partner', CONTACT_A_WITH_CARD),
                ('hr.rfid.card', CARD_A_OF_THE_EMPLOYEE),
                ('hr.rfid.access.group', GROUP_A)):
            self.assertTrue(
                self._arrived(source, model, source_id),
                'нищо от вида %s не е дошло, значи проверките за фирмена '
                'принадлежност мерят празна цел' % model)

    def _owner_of(self, card):
        return card.employee_id or card.contact_id

    # ── видовете отпуск ──────────────────────────────────────

    def test_a_leave_type_of_one_tenant_is_not_offered_to_the_other(self):
        """Клиентът вижда СВОИТЕ видове отпуск, не чуждите 21.

        Видовете се четат без фирмен филтър, защото един вид принадлежи на един
        наемател. Създадени без фирма обаче, всичките 22 вида на облака с 27
        фирми ставаха глобални и всеки наемател виждаше останалите 21.
        """
        if not self.has_leaves:
            self.skipTest('hr_holidays не е инсталиран')
        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)

        type_a = self._arrived(source, 'hr.leave.type', LEAVE_TYPE_A)
        type_b = self._arrived(source, 'hr.leave.type', LEAVE_TYPE_B)
        self.assertTrue(
            type_a and type_b,
            'видовете отпуск на двамата наематели не са пренесени изобщо - '
            'на живо това са 22 вида, които клиентите ползват всеки ден')
        self.assertEqual(
            type_a.company_id, self.tenant_a,
            'видът отпуск на наемател А пристигна с фирма %r вместо %r; празна '
            'фирма значи глобален вид, тоест всичките 22 вида на облака с 27 '
            'фирми се предлагат на всеки наемател'
            % (type_a.company_id.name, self.tenant_a.name))
        self.assertEqual(
            type_b.company_id, self.tenant_b,
            'видът отпуск на наемател Б пристигна с фирма %r вместо %r'
            % (type_b.company_id.name, self.tenant_b.name))

        offered_to_b = self.env['hr.leave.type'].sudo().with_context(
            active_test=False).search(
                [('company_id', 'in', [self.tenant_b.id, False])])
        self.assertNotIn(
            type_a, offered_to_b,
            'видът отпуск на наемател А се предлага и на наемател Б - точно '
            'смесването, което направи 22-та вида общи за 27 фирми')
        self.assertIn(
            type_b, offered_to_b,
            'своят собствен вид отпуск ТРЯБВА да се предлага на наемател Б, '
            'иначе поправката е скрила данните вместо да ги раздели')

    def test_a_leave_type_of_a_tenant_we_do_not_move_does_not_become_global(self):
        """Отричащият двойник: наемател извън прогона не влиза през задната врата.

        Вид отпуск на наемател, който този прогон НЕ пренася, не бива да
        пристигне без фирма - глобалният вид се предлага на всяка фирма в
        базата, тоест точно на 27-те наематели, между които го разделяме.
        """
        if not self.has_leaves:
            self.skipTest('hr_holidays не е инсталиран')
        Types = self.env['hr.leave.type'].sudo().with_context(active_test=False)
        global_before = set(Types.search([('company_id', '=', False)]).ids)

        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)
        self.assertTrue(
            self._arrived(source, 'hr.leave.type', LEAVE_TYPE_A),
            'стъпката за видовете отпуск не е създала нищо, значи "нищо '
            'глобално не се е появило" не доказва нищо')

        self.assertFalse(
            self._arrived(source, 'hr.leave.type',
                          LEAVE_TYPE_WE_ARE_NOT_MOVING),
            'вид отпуск на наемател, който не пренасяме, е влязъл в целта')
        global_after = set(Types.search([('company_id', '=', False)]).ids)
        self.assertEqual(
            global_after, global_before,
            'прехвърлянето е създало %s вид(а) отпуск без фирма; глобалният '
            'вид се предлага на ВСЯКА фирма в базата - това е механизмът, по '
            'който 22 вида станаха общи за 27 наематели'
            % len(global_after - global_before))

    # ── слотовете за график ──────────────────────────────────

    def test_each_company_keeps_the_sixteen_slots_the_hardware_has(self):
        """Графикът е СЛОТ в контролера, а слотовете са 16 на фирма.

        Целта си прави своите 16 в момента, в който фирмата се появи.
        Пренасянето създаваше свои до тях: измерено на облака с 27 фирми - 32
        записа за 16 хардуерни слота на наемател, и оттам нататък е гадаене към
        кой от двата сочи дадено право за врата.
        """
        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)

        for company in (self.tenant_a, self.tenant_b):
            count = len(self._slots_of(company))
            self.assertEqual(
                count, 16,
                'фирма %r държи %s графика при 16 хардуерни слота - на живо '
                'това бяха 32 на наемател, тоест по два записа за всеки слот'
                % (company.name, count))

        all_slots = self.env['hr.rfid.time.schedule'].sudo().with_context(
            active_test=False).search([])
        doubled = {pair: seen for pair, seen in Counter(
            (slot.company_id.id, slot.number) for slot in all_slots
        ).items() if seen > 1}
        self.assertFalse(
            doubled,
            'два записа делят един и същи слот (фирма, номер): %s - при това '
            'няма как да се каже към кой от двата сочи дадено право за врата'
            % doubled)

        slot_a = self._arrived(source, 'hr.rfid.time.schedule',
                               TS_A_ROUND_THE_CLOCK)
        slot_b = self._arrived(source, 'hr.rfid.time.schedule',
                               TS_B_ROUND_THE_CLOCK)
        self.assertTrue(
            slot_a and slot_b,
            'графиците на източника не са свързани с никой слот в целта - без '
            'тази връзка правата за врати не намират своя график')
        self.assertEqual(
            slot_a.company_id, self.tenant_a,
            'слот 1 на наемател А е закачен за фирма %r' % slot_a.company_id.name)
        self.assertEqual(
            slot_b.company_id, self.tenant_b,
            'слот 1 на наемател Б е закачен за фирма %r' % slot_b.company_id.name)
        self.assertNotEqual(
            slot_a, slot_b,
            'слот 1 на двамата наематели се оказа ЕДИН запис (%s) - тогава два '
            'наемателя си делят един график и промяна при единия важи за другия'
            % slot_a.id)
        self.assertIn(
            slot_a, self._slots_of(self.tenant_a),
            'осиновеният слот трябва да е един от 16-те на фирмата, не нов до тях')

    # ── контактите и техните карти ───────────────────────────

    def test_a_contact_without_a_company_does_not_become_ours(self):
        """Контакт без фирма остава без фирма, не влиза в "My Company".

        В Odoo контактът е споделен и обикновено няма своя фирма. Изпуснато от
        стойностите, полето пада към фирмата по подразбиране на целта: всичките
        11 картодържащи контакта на един Odoo 14 наемател легнаха в "My
        Company", която не е нито един от пренасяните наематели.
        """
        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)

        contact = self._arrived(source, 'res.partner', CONTACT_A_WITH_CARD)
        self.assertTrue(contact, 'картодържащият контакт не е пренесен изобщо')
        self.assertFalse(
            contact.company_id,
            'контактът без фирма пристигна във фирма %r; така легнаха 11 от 11 '
            'контакта на един наемател, а фирмата, от която прехвърляме, е %r'
            % (contact.company_id.name, self.env.company.name))
        self.assertNotEqual(
            contact.company_id, self.env.company,
            'контактът е присвоен от фирмата, от която е стартирано '
            'прехвърлянето (%r) - тя не е наемателят, чиито данни носим'
            % self.env.company.name)

        owned = self._arrived(source, 'res.partner', CONTACT_B_WITH_CARD)
        self.assertEqual(
            owned.company_id, self.tenant_b,
            'контакт, който СИ има фирма на източника, трябва да пристигне при '
            'нея: очаквано %r, получено %r'
            % (self.tenant_b.name, owned.company_id.name))

    def test_no_card_of_a_tenant_is_held_by_a_person_of_another_company(self):
        """Редът, който финалната проверка изписа на живо: 19 такива карти.

        Проверката беше права - контактите бяха легнали в чужда фирма, значи
        картите на наемателя наистина се държаха от хора на друга фирма. Тук се
        проверяват картите на ДВАМАТА наематели, защото смесването се вижда
        едва когато в целта има повече от един.
        """
        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)

        wrong = []
        for source_id in (CARD_A_OF_THE_EMPLOYEE, CARD_A_OF_THE_CONTACT,
                          CARD_B_OF_THE_EMPLOYEE, CARD_B_OF_THE_CONTACT):
            card = self._arrived(source, 'hr.rfid.card', source_id)
            self.assertTrue(
                card, 'карта %s не е пренесена - на живо един неразрешим '
                      'притежател костваше на наемателя всичките му 400 карти'
                      % source_id)
            owner = self._owner_of(card)
            self.assertTrue(
                owner, 'карта %s пристигна без притежател - тя не отваря врата '
                       'на никого и може да бъде дадена на друг по погрешка'
                       % card.number)
            if owner.company_id and owner.company_id != card.company_id:
                wrong.append((card.number, card.company_id.name,
                              owner.display_name, owner.company_id.name))
        self.assertFalse(
            wrong,
            'карти на един наемател се държат от човек на друга фирма '
            '(карта, фирма на картата, притежател, неговата фирма): %s - на '
            'живо това бяха 19 карти на един наемател' % wrong)

    def test_a_contact_nobody_here_uses_is_not_dragged_in(self):
        """Двойникът на разширения обхват: разширен, но не безграничен.

        Обхватът на контактите е разширен до тези, до които този наемател се
        допира - държи негова карта или е член на негова група за достъп -
        защото контакт без фирма иначе отпада и с него отпадат 23 членства и
        400 карти. Разширението обаче не е "докарай всички контакти на другата
        система": контакт, който този наемател не ползва, не е негов и не бива
        да се появи в базата му.
        """
        source = self._source(self._first_system(), self.company_map,
                              FIRST_SYSTEM)
        self._run_the_transfer(source)
        self._assert_it_really_moved_something(source)

        by_the_card = self._arrived(source, 'res.partner', CONTACT_A_WITH_CARD)
        by_the_group = self._arrived(source, 'res.partner',
                                     CONTACT_A_IN_A_GROUP)
        self.assertTrue(
            by_the_card,
            'контакт без фирма, който държи карта на наемателя, не е дошъл - '
            'на живо така отпаднаха 11 от 11 и картите им след тях')
        self.assertTrue(
            by_the_group,
            'контакт без фирма, който е член на група за достъп на наемателя, '
            'не е дошъл - с него отпадат и 23-те членства')

        self.assertFalse(
            self._arrived(source, 'res.partner', CONTACT_NOBODY_USES),
            'контакт, до който този наемател не се допира по нищо, е довлечен '
            'в базата му - разширеният обхват не е "всички контакти"')

    # ── втора система в същата цел ───────────────────────────

    def test_a_second_transfer_from_another_system_leaves_the_first_alone(self):
        """Облакът и после един Odoo 14 наемател, в една и съща цел.

        Двете системи се пренасят една след друга (така мина живият тест: Odoo
        14 наемател плюс облак с 27 фирми). Втората не бива да пипне нищо от
        първата: нито да добави ред при вече пренесен наемател, нито да осинови
        неговите слотове, нито да изтрие негов запис.
        """
        first = self._source(self._first_system(), self.company_map,
                             FIRST_SYSTEM)
        self._run_the_transfer(first)
        self._assert_it_really_moved_something(first)
        before = self._per_company_ids([self.tenant_a, self.tenant_b])

        second = self._source(self._second_system(), self.other_company_map,
                              SECOND_SYSTEM)
        self._run_the_transfer(second)

        moved = [self._arrived(second, model, source_id) for model, source_id in (
            ('res.partner', SECOND_CONTACT),
            ('hr.employee', SECOND_EMPLOYEE),
            ('hr.rfid.card', SECOND_CARD),
            ('hr.rfid.access.group', SECOND_GROUP))]
        self.assertTrue(
            all(moved),
            'вторият източник не е пренесъл нищо, значи "първият не е пипнат" '
            'не доказва нищо: %s' % [bool(rec) for rec in moved])
        self.assertEqual(
            self._arrived(second, 'hr.employee', SECOND_EMPLOYEE).company_id,
            self.tenant_c,
            'наемателят на втората система е внесен в чужда фирма')

        after = self._per_company_ids([self.tenant_a, self.tenant_b])
        differences = {key: (sorted(before[key] ^ after[key]))
                       for key in after if before[key] != after[key]}
        self.assertFalse(
            differences,
            'втори пренос от ДРУГА система е променил какво държат вече '
            'пренесените наематели (модел, фирма): %s - при 27 наематели това '
            'значи, че всеки следващ пренос разбърква предишните'
            % differences)

        slots_c = len(self._slots_of(self.tenant_c))
        self.assertEqual(
            slots_c, 16,
            'фирмата на втората система държи %s графика при 16 хардуерни '
            'слота - осиновяването важи и за втория източник' % slots_c)
        all_slots = self.env['hr.rfid.time.schedule'].sudo().with_context(
            active_test=False).search([])
        doubled = {pair: seen for pair, seen in Counter(
            (slot.company_id.id, slot.number) for slot in all_slots
        ).items() if seen > 1}
        self.assertFalse(
            doubled,
            'след втория пренос два записа делят един слот (фирма, номер): %s'
            % doubled)


@tagged('post_install', '-at_install', 'rfid_odoo_import',
        'rfid_import_multicompany')
class TestDepartmentRightsComeFromTheOtherSystem(TransactionCase):
    """Кой каква врата отваря идва от другата система, не се решава тук.

    Измерено при пренасянето на облака с 27 фирми: записът на "разрешени групи
    за достъп" на един отдел фабрикува правото по подразбиране на всеки член
    без права и маха всяко право извън списъка, който току-що е получил. Шест
    души тук получиха врати, които на другата система не са имали - а правата
    им вече бяха записани точно както другата система ги държи.

    И двете посоки се проверяват: под пренасяне отделът не решава нищо, а ИЗВЪН
    пренасяне същият запис продължава да работи както преди - иначе поправката
    тихо е изключила реална функция на hr_rfid за всекидневната работа.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Отдели ООД'})

    def _department_with_two_members(self, label):
        """Отдел, в който един член има право, а друг няма никакво.

        Двамата са двете половини на механизма: единият показва отнемането,
        другият фабрикуването.
        """
        Group = self.env['hr.rfid.access.group']
        held = Group.create({
            'name': 'Право, което човекът вече има (%s)' % label,
            'company_id': self.company.id})
        arriving = Group.create({
            'name': 'Право от новия списък (%s)' % label,
            'company_id': self.company.id})
        department = self.env['hr.department'].create({
            'name': 'Портал %s' % label,
            'company_id': self.company.id,
            'hr_rfid_allowed_access_groups': [(6, 0, [held.id, arriving.id])],
            'hr_rfid_default_access_group': held.id,
        })
        Employee = self.env['hr.employee'].with_context(**IMPORT_CONTEXT)
        with_a_right = Employee.create({
            'name': 'Човек с право (%s)' % label,
            'company_id': self.company.id,
            'department_id': department.id})
        with_none = Employee.create({
            'name': 'Човек без права (%s)' % label,
            'company_id': self.company.id,
            'department_id': department.id})
        with_a_right.with_context(**IMPORT_CONTEXT).add_acc_gr(held)
        self.assertEqual(
            self._rights_of(with_a_right), held,
            'подготовката е сбъркана: човекът трябва да започне с точно едно право')
        self.assertFalse(
            self._rights_of(with_none),
            'подготовката е сбъркана: вторият човек трябва да започне без права')
        return department, held, arriving, with_a_right, with_none

    def _rights_of(self, employee):
        return employee.hr_rfid_access_group_ids.mapped('access_group_id')

    def test_a_transfer_neither_grants_nor_takes_away_a_membership(self):
        """Под пренасяне отделът записва списъка си и НЕ пипа хората.

        Правата на хората идват от другата система и вече са записани. Шест
        души на живо получиха точно тук врати, които не са имали, а членът с
        право извън новия списък го губеше.
        """
        department, held, arriving, with_a_right, with_none = \
            self._department_with_two_members('пренасяне')

        department.with_context(**IMPORT_CONTEXT).write({
            'hr_rfid_allowed_access_groups': [(6, 0, [arriving.id])]})

        self.assertEqual(
            self._rights_of(with_a_right), held,
            'човек загуби правото си %r при записа на отделовия списък; правата '
            'идват от другата система и пренасянето не бива да реши, че това не '
            'му се полага - сега държи %r'
            % (held.name, self._rights_of(with_a_right).mapped('name')))
        self.assertFalse(
            self._rights_of(with_none),
            'човек без права получи %r само защото отделът си записа списъка - '
            'на живо така шест души получиха врати, които на другата система не '
            'са имали' % self._rights_of(with_none).mapped('name'))
        self.assertEqual(
            department.hr_rfid_allowed_access_groups, arriving,
            'самият списък на отдела ТРЯБВА да се запише - пренасянето носи '
            'данните, то просто не решава кой какво отваря')

    def test_outside_a_transfer_the_department_still_manages_its_members(self):
        """Отричащият двойник: всекидневната работа е недокосната.

        Извън пренасяне същият запис прави точно каквото е правил: маха право
        извън разрешения списък и дава правото по подразбиране на човек без
        права. Ако това спре да работи, поправката е изключила реална функция
        на hr_rfid, а не е стеснила пренасянето.
        """
        department, held, arriving, with_a_right, with_none = \
            self._department_with_two_members('всекидневие')

        department.write({
            'hr_rfid_allowed_access_groups': [(6, 0, [arriving.id])]})

        self.assertNotIn(
            held, self._rights_of(with_a_right),
            'извън пренасяне правото %r е извън разрешения списък и трябва да '
            'бъде отнето, а още стои' % held.name)
        self.assertIn(
            arriving, self._rights_of(with_none),
            'извън пренасяне човек без права трябва да получи правото по '
            'подразбиране на отдела (%r), а получи %r'
            % (arriving.name, self._rights_of(with_none).mapped('name')))
