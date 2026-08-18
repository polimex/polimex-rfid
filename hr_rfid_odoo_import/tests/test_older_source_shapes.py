# -*- coding: utf-8 -*-
"""Формите на по-стария източник - въпросът за баланса и контактите с карти.

Бизнес твърдение (собственик, 2026-08-17): "от одоо 14 трябва и отпуските да
прехвърлим" и "прехвърли ми тези бази" - тоест прехвърлянето трябва да донесе
историята на наемателя ТАКАВА, КАКВАТО Е, а не такава, каквато днешната версия
би я поискала.

Две загуби, мерени на живо при двуизточниковия прогон (наемател от одоо 14 +
облак от одоо 15 с 27 фирми):

1. "Иска ли този вид отпуск баланс?" на по-старите системи е ДУМА, не чекбокс.
   Одоо 15 отговаря 'yes' / 'no', а одоо 14 пита същото под друго име
   (allocation_type) с 'no' / 'fixed' / 'fixed_allocation'. Думата "no" е
   непразен низ, тоест ИСТИНА за чекбокс - непрочетена, всеки вид отпуск
   пристигаше с изискван баланс и отсъствията се отказваха на входа с текст,
   който вини СЛУЖИТЕЛЯ ("X does not have a valid allocation"). Мерено:
   14 от 22-та вида в облака казват "no"; отказани са 72 от 1 083 одобрени
   отсъствия в облака и 2 848 от 3 300 при наемателя от одоо 14 - 86 на сто
   от историята му.

2. Контактът, който държи карта, обикновено НЯМА своя фирма (контактът в Odoo
   е споделен, не притежаван), а обхватът беше само по фирма. Мерено при
   наемателя от одоо 14: и 11-те контакта с карти останаха отвъд, 23-те им
   членства в групи за достъп паднаха с тях, а после стъпката с картите гръмна
   на първия неразрешим собственик и коства на наемателя ВСИЧКИТЕ му 400 карти.

Тук се проверява и третото: една стъпка не бива да коства работата на съседна
(редът в протокола казва честно, че тя е паднала).
"""

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.access_importer import AccessImporter
from ..models.importers.leave_importer import LeaveImporter
from ..models.importers.people_importer import PeopleImporter
from .test_older_source_missing_models import _OlderSource


class _OlderTenantSource(_OlderSource):
    """По-стар сървър, който УВАЖАВА обхвата на заявката.

    Наследява отказа на `_OlderSource` (сървър без такъв модел вдига грешка,
    не връща празен списък) и добавя едно нещо: когато заявката пита за
    КОНКРЕТНИ номера, връща само тях. Двойник, който връща цялата таблица
    независимо какво е поискано, не може да докаже, че чужд контакт е останал
    отвъд - при него той пристига и при повредения обхват, и при поправения.
    """

    def _search_read(self, model, domain, fields, order='id asc', limit=0,
                     include_archived=True):
        rows = super()._search_read(model, domain, fields, order=order,
                                    limit=limit,
                                    include_archived=include_archived)
        return self._only_the_ids_asked_for(rows, domain)

    @staticmethod
    def _only_the_ids_asked_for(rows, domain):
        """Реалният сървър връща само поисканите номера."""
        if any(isinstance(leaf, str) for leaf in domain):
            # Съставен обхват (ИЛИ / НЕ) - не се преценява тук.
            return rows
        for leaf in domain:
            if (isinstance(leaf, (list, tuple)) and len(leaf) == 3
                    and leaf[0] == 'id' and leaf[1] == 'in'):
                wanted = set(leaf[2] or ())
                return [r for r in rows if r['id'] in wanted]
        return rows

    @staticmethod
    def ids_asked_for(domain):
        """Номерата, които стъпката е поискала - за проверка на обхвата."""
        for leaf in domain or []:
            if (isinstance(leaf, (list, tuple)) and len(leaf) == 3
                    and leaf[0] == 'id' and leaf[1] == 'in'):
                return list(leaf[2] or ())
        return []


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_v14')
class TestABalanceNobodyAskedFor(TransactionCase):
    """Вид отпуск, който НЕ е искал баланс, не бива да започне да иска."""

    EMPLOYEE = 71

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.leave' not in cls.env:
            raise cls.skipTest(cls, 'hr_holidays не е инсталиран')
        cls.company = cls.env.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Отпускар от 14-та', 'company_id': cls.company.id})

    # ── източникът ────────────────────────────────────────────

    def _source(self, leave_type, leaves=(), balances_readable=True):
        data = {
            # Реален по-стар сървър го има; тук няма нито един ред, който да
            # съвпадне - видът отпуск се пренася, не се разпознава.
            'ir.model.data': [],
            'hr.leave.type': [leave_type],
            'hr.leave': list(leaves),
        }
        if balances_readable:
            data['hr.leave.allocation'] = []
        src = _OlderTenantSource(
            self.env, {901: self.company.id},
            {'import_leaves': True}, data)
        src._set_target_id('hr.employee', self.EMPLOYEE, self.employee.id)
        return src

    def _leave(self, leave_id, type_id):
        """Одобрено отсъствие от по-старата система - готова история."""
        return {
            'id': leave_id, 'employee_id': self.EMPLOYEE,
            'holiday_status_id': type_id, 'state': 'validate',
            'date_from': '2026-07-01 06:00:00',
            'date_to': '2026-07-03 15:00:00',
            'request_date_from': '2026-07-01',
            'request_date_to': '2026-07-03',
            'number_of_days': 3.0, 'name': 'Лято',
        }

    def _balance_required_after_transfer(self, type_id, field, word):
        """Какво казва целта за баланса, след като думата е пренесена."""
        src = self._source({'id': type_id, 'name': 'Вид %s' % type_id,
                            'active': True, field: word})
        LeaveImporter(src)._import_leave_types()
        target_id = src._get_target_id('hr.leave.type', type_id)
        self.assertTrue(
            target_id,
            'Видът отпуск с %s=%r изобщо не пристигна - без него нито едно '
            'отсъствие от този вид не може да дойде' % (field, word))
        return self.env['hr.leave.type'].browse(target_id).requires_allocation

    # ── одоо 14: същият въпрос под друго име ──────────────────

    def test_a_kind_of_leave_that_needed_no_balance_still_needs_none(self):
        """Одоо 14 пита за баланса в allocation_type, с три отговора.

        Мерено на наемателя от одоо 14: полето се казва allocation_type, а
        отговорите му са 'no' (без ограничение), 'fixed' и 'fixed_allocation'.
        Непрочетено, всеки вид отпуск пристигна с изискван баланс и 2 848 от
        3 300 одобрени отсъствия бяха отказани на входа.
        """
        self.assertFalse(
            self._balance_required_after_transfer(101, 'allocation_type', 'no'),
            'Вид отпуск, който на одоо 14 казва allocation_type="no" (без '
            'ограничение), пристигна с ИЗИСКВАН баланс - точно причината '
            '2 848 от 3 300 одобрени отсъствия да бъдат отказани')
        for word in ('fixed', 'fixed_allocation'):
            self.assertTrue(
                self._balance_required_after_transfer(
                    102 if word == 'fixed' else 103, 'allocation_type', word),
                'Вид отпуск, който на одоо 14 казва allocation_type=%r, '
                'изисква баланс - разхлабен тук, целта престава да пази '
                'правилото, по което са дадени всичките 3 300 отсъствия'
                % word)

    # ── одоо 15: думата "no", която е ИСТИНА за чекбокс ───────

    def test_the_cloud_says_no_with_a_word_and_a_word_is_not_a_yes(self):
        """Одоо 15 казва 'yes' / 'no' - и "no" е непразен низ.

        Точно капанът: пренесена както е, думата "no" е ИСТИНА за чекбокса
        тук. Мерено в облака: 14 от 22-та вида казват "no", а 72 от 1 083
        одобрени отсъствия бяха отказани заради това.
        """
        self.assertFalse(
            self._balance_required_after_transfer(
                201, 'requires_allocation', 'no'),
            'Думата "no" от одоо 15 пристигна като ДА - непразен низ е '
            'истина за чекбокс; така 14 от 22-та вида в облака започнаха да '
            'искат баланс и 72 от 1 083 отсъствия бяха отказани')
        self.assertTrue(
            self._balance_required_after_transfer(
                202, 'requires_allocation', 'yes'),
            'Думата "yes" от одоо 15 трябва да пристигне като ДА - иначе '
            'поправката на "no" разхлабва и видовете, които наистина искат '
            'баланс')

    def test_a_word_this_transfer_does_not_know_keeps_the_balance_required(self):
        """ОТРИЦАТЕЛНИЯТ близнак: непозната дума НЕ разхлабва политика.

        Отказът е гръмък и се оправя с един запис; политика, разхлабена зад
        гърба на оператора, не се вижда никога. Затова непозната дума остава
        "иска баланс".
        """
        self.assertTrue(
            self._balance_required_after_transfer(
                301, 'allocation_type', 'set_by_time_off_officer'),
            'Непозната дума за баланса разхлаби вида отпуск - прехвърляне, '
            'което гадае в посока "по-разрешено", отваря отсъствия, които '
            'никой не е одобрявал; при 22 вида в облака една непозната дума '
            'стига')

    # ── бизнес изходът, не флагът ─────────────────────────────

    def test_an_absence_approved_without_a_balance_arrives(self):
        """Служителят си вижда одобрения отпуск, макар да няма баланс.

        Видът отпуск на другата система не е искал баланс, значи и тук не
        иска - и одобреното отсъствие влиза одобрено. Точно 2 848-те
        отсъствия на наемателя от одоо 14, които преди това се отказваха с
        текст, който вини служителя.
        """
        src = self._source(
            {'id': 401, 'name': 'Неплатен отпуск', 'active': True,
             'allocation_type': 'no'},
            leaves=[self._leave(31, 401)])

        rows = LeaveImporter(src).run(None)

        arrived = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee.id)])
        self.assertEqual(
            len(arrived), 1,
            'Одобреното отсъствие от вид БЕЗ баланс не пристигна - това е 1 '
            'от 2 848-те, отказани при наемателя от одоо 14 (86%% от '
            'историята му). Протокол: %s' % rows)
        self.assertEqual(
            arrived.state, 'validate',
            'Отсъствието пристигна, но не одобрено - историята чака наново '
            'одобрение, което никой няма да даде за 2 848 стари записа')
        self.assertFalse(
            arrived.holiday_status_id.requires_allocation,
            'Видът отпуск иска баланс тук, макар другата система да не е '
            'искала - следващият прогон ще отказва точно същите отсъствия')

    def test_an_absence_of_a_kind_that_does_need_a_balance_is_left_behind_named(self):
        """ОТРИЦАТЕЛНИЯТ близнак: не всичко минава, и пропускът се обяснява.

        Същият източник, сменена е САМО думата: вид отпуск, който наистина
        иска баланс, а баланс няма - отсъствието остава отвъд и редът в
        протокола казва защо. Без този близнак горният тест минава и при
        прехвърляне, което просто заглушава всяка проверка.
        """
        src = self._source(
            {'id': 501, 'name': 'Платен отпуск', 'active': True,
             'allocation_type': 'fixed'},
            leaves=[self._leave(51, 501)])

        rows = LeaveImporter(src).run(None)

        self.assertEqual(
            self.env['hr.leave'].search_count(
                [('employee_id', '=', self.employee.id)]), 0,
            'Отсъствие от вид, който иска баланс, влезе БЕЗ баланс - тогава '
            'проверката е заглушена изобщо и горният тест за 2 848-те '
            'отсъствия не доказва нищо')
        row = next(r for r in rows if r['model'] == 'hr.leave')
        self.assertEqual(
            row['skipped_count'], 1,
            'Оставеното отсъствие не е преброено: "няма такива данни" и '
            '"всичките 2 848 паднаха" изглеждат еднакво в протокола')
        self.assertTrue(
            row['error'],
            'Оставеното отсъствие е без обяснена причина - операторът не '
            'научава, че става дума за баланси и че повторният прогон ще '
            'донесе точно липсващите')

    # ── една стъпка не коства работата на съседната ───────────

    def test_the_absences_arrive_even_when_the_balances_cannot_be_read(self):
        """Балансите не се четат, отсъствията пристигат.

        Разширение на същото, което 14-та версия направи с дневните
        обобщения (196 659 присъствия, откатнати от паднала съседна стъпка):
        сметката, с която четем другата система, често не вижда всеки модел -
        реален клиентски одоо 17 отказа цели модели. Паднала стъпка се
        записва като паднала и фазата продължава.
        """
        src = self._source(
            {'id': 601, 'name': 'Неплатен отпуск', 'active': True,
             'allocation_type': 'no'},
            leaves=[self._leave(61, 601)],
            balances_readable=False)

        rows = LeaveImporter(src).run(None)

        self.assertEqual(
            self.env['hr.leave'].search_count(
                [('employee_id', '=', self.employee.id)]), 1,
            'Отсъствията изчезнаха заедно с падналата стъпка за балансите - '
            'същата загуба, която на 14-та версия отнесе 196 659 присъствия. '
            'Протокол: %s' % rows)
        failed = [r for r in rows if r['status'] == 'error']
        self.assertTrue(
            failed,
            'Стъпка, която не е могла да прочете балансите, е минала за '
            'успешна - операторът не научава, че балансите липсват, и после '
            'се чуди защо отсъствията не се връзват')
        self.assertTrue(
            all(r['error'] for r in failed),
            'Падналата стъпка е без обяснена причина - редът казва само '
            '"грешка", а причината е права за четене на другата система')


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_v14')
class TestCardHoldingContactsOfAnOlderTenant(TransactionCase):
    """Контактът с карта няма своя фирма - и въпреки това пътува.

    Мерено при наемателя от одоо 14: и 11-те контакта с карти бяха без фирма,
    затова обхватът само по фирма не хвана нито един; 23-те им членства в
    групи за достъп паднаха след тях; после стъпката с картите гръмна на
    първия неразрешим собственик и наемателят остана без ВСИЧКИТЕ си 400 карти.
    """

    #: Първата по номер е повредената нарочно - гръмнала стъпка отнася всичко
    #: СЛЕД себе си, тоест точно другите карти на наемателя.
    CARD_WITHOUT_OWNER = 401
    CARD_OF_CONTACT = 402
    CARD_OF_EMPLOYEE = 403
    HOLDER = 11
    MEMBER = 12
    STRANGER = 13
    LOST_OWNER = 99
    GROUP = 51
    REL = 61
    EMPLOYEE = 71

    NUMBER_WITHOUT_OWNER = '0000400001'
    NUMBER_OF_CONTACT = '0000400002'
    NUMBER_OF_EMPLOYEE = '0000400003'
    STRANGER_NAME = 'Контакт извън контрола на достъп'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'V14 Card Tenant'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Пазач', 'company_id': cls.company.id})
        cls.group = cls.env['hr.rfid.access.group'].create({
            'name': 'Външни изпълнители', 'company_id': cls.company.id})

    def _source(self):
        company = [101, self.company.name]
        src = _OlderTenantSource(
            self.env, {101: self.company.id},
            {'import_people': True, 'import_access': True},
            {
                'res.partner': [
                    # Тримата са БЕЗ своя фирма - така изглежда контактът в
                    # Odoo. Първите два са споменати от контрола на достъп на
                    # този наемател, третият от никого.
                    {'id': self.HOLDER, 'name': 'Изпълнител с карта',
                     'company_id': False, 'active': True},
                    {'id': self.MEMBER, 'name': 'Изпълнител в група',
                     'company_id': False, 'active': True},
                    {'id': self.STRANGER, 'name': self.STRANGER_NAME,
                     'company_id': False, 'active': True},
                ],
                'hr.rfid.access.group.contact.rel': [
                    {'id': self.REL,
                     'access_group_id': [self.GROUP, 'Външни изпълнители'],
                     'contact_id': [self.MEMBER, 'Изпълнител в група'],
                     'state': True, 'internal_state': True},
                ],
                'hr.rfid.card': [
                    {'id': self.CARD_WITHOUT_OWNER,
                     'number': self.NUMBER_WITHOUT_OWNER,
                     'company_id': company, 'active': True,
                     'contact_id': [self.LOST_OWNER, 'Изчезнал собственик']},
                    {'id': self.CARD_OF_CONTACT,
                     'number': self.NUMBER_OF_CONTACT,
                     'company_id': company, 'active': True,
                     'contact_id': [self.HOLDER, 'Изпълнител с карта']},
                    {'id': self.CARD_OF_EMPLOYEE,
                     'number': self.NUMBER_OF_EMPLOYEE,
                     'company_id': company, 'active': True,
                     'employee_id': [self.EMPLOYEE, 'Пазач']},
                ],
            })
        src._set_target_id('hr.employee', self.EMPLOYEE, self.employee.id)
        src._set_target_id('hr.rfid.access.group', self.GROUP, self.group.id)
        return src

    def _card(self, number):
        return self.env['hr.rfid.card'].with_context(
            active_test=False).search([('number', '=', number),
                                       ('company_id', '=', self.company.id)])

    # ── контактът с карта пристига ────────────────────────────

    def test_a_contact_with_no_company_of_its_own_comes_across_with_its_card(self):
        """Държи карта на наемателя, значи е негов - независимо от фирмата.

        Мерено: и 11-те контакта с карти на наемателя от одоо 14 бяха без
        своя фирма, затова обхватът само по фирма не донесе нито един, а
        след тях паднаха и 400-те карти.
        """
        src = self._source()
        PeopleImporter(src)._import_partners()
        AccessImporter(src)._import_cards()

        holder_id = src._get_target_id('res.partner', self.HOLDER)
        self.assertTrue(
            holder_id,
            'Контактът, който държи карта на този наемател, не пристигна - '
            'точно 11-те контакта без фирма, останали отвъд, и 400-те карти '
            'след тях')
        card = self._card(self.NUMBER_OF_CONTACT)
        self.assertEqual(
            len(card), 1,
            'Картата на контакта не пристигна - без собственика си тя няма '
            'как да бъде създадена (картата иска точно един притежател)')
        self.assertEqual(
            card.contact_id.id, holder_id,
            'Картата пристигна, но у ДРУГ притежател - при 400 карти това е '
            'достъп, даден на когото не трябва')

    def test_the_group_membership_of_such_a_contact_comes_across_too(self):
        """Без членството контактът пристига, но врата не отваря.

        Мерено: 23 членства в групи за достъп паднаха заедно с контактите
        без фирма - тоест хората пристигаха без правата си.
        """
        src = self._source()
        PeopleImporter(src)._import_partners()
        AccessImporter(src)._import_ag_contact_rels()

        member_id = src._get_target_id('res.partner', self.MEMBER)
        self.assertTrue(
            member_id,
            'Контактът, който е член на група за достъп на този наемател, не '
            'пристигна - обхватът пак е само по фирма, а той няма своя')
        rel = self.env['hr.rfid.access.group.contact.rel'].search([
            ('access_group_id', '=', self.group.id),
            ('contact_id', '=', member_id),
        ])
        self.assertEqual(
            len(rel), 1,
            'Членството в групата за достъп не пристигна - 1 от 23-те, с '
            'които хората губят правата си, а протоколът не казва нищо')

    def test_a_contact_the_access_control_never_mentions_is_left_where_it_is(self):
        """ОТРИЦАТЕЛНИЯТ близнак: разширеният обхват не влачи чужди контакти.

        Разширението е точно и само за онези, които контролът на достъп на
        ТОЗИ наемател споменава. Иначе облакът с 27 фирми би налял в целта
        целия си адресник.
        """
        src = self._source()
        PeopleImporter(src)._import_partners()

        asked = src.ids_asked_for(src.domains.get('res.partner'))
        self.assertIn(
            self.HOLDER, asked,
            'Стъпката не поиска контакта, който държи карта на наемателя '
            '(поискани: %s) - 1 от 11-те, които останаха отвъд' % (asked,))
        self.assertIn(
            self.MEMBER, asked,
            'Стъпката не поиска контакта, който е член на група за достъп на '
            'наемателя (поискани: %s) - с него падат и 23-те членства'
            % (asked,))
        self.assertNotIn(
            self.STRANGER, asked,
            'Стъпката поиска и контакт, който контролът на достъп на този '
            'наемател не споменава никъде (поискани: %s) - при облак с 27 '
            'фирми това е целият чужд адресник' % (asked,))
        self.assertEqual(
            self.env['res.partner'].with_context(active_test=False).search_count(
                [('name', '=', self.STRANGER_NAME)]), 0,
            'Контакт, който контролът на достъп на наемателя не споменава '
            'никъде, пристигна - при облак с 27 фирми това е чужд адресник '
            'в чужда база')

    # ── неразрешим собственик коства САМО своята карта ────────

    def test_one_unresolvable_owner_costs_that_card_only(self):
        """Гръмнала стъпка коства 400 карти; пропусната - една.

        Мерено при наемателя от одоо 14: един контакт не се разреши, стъпката
        гръмна на него и не пристигна нито една от 400-те карти. Затова тук
        стъпката се вика ПРЯКО: вдигне ли грешка, тестът пада, вместо
        обвивката на фазата да я преглътне.
        """
        src = self._source()
        PeopleImporter(src)._import_partners()
        phase = AccessImporter(src)

        # Пряко извикване: реинтродуцирана грешка на неразрешим собственик
        # излиза тук, а не се превръща в един червен ред.
        phase._import_cards()

        self.assertEqual(
            len(self._card(self.NUMBER_OF_CONTACT)), 1,
            'Картата на контакта не пристигна заради ЧУЖДА карта с изчезнал '
            'собственик - точно веригата, която коства 400 карти')
        self.assertEqual(
            len(self._card(self.NUMBER_OF_EMPLOYEE)), 1,
            'Картата на служителя, която стои СЛЕД повредената, не пристигна '
            '- стъпката е спряла на първия неразрешим собственик, както при '
            '400-те карти на наемателя')
        self.assertEqual(
            len(self._card(self.NUMBER_WITHOUT_OWNER)), 0,
            'Карта с изчезнал собственик пристигна - карта без притежател не '
            'отваря на никого и може да бъде дадена тук на друг човек по '
            'погрешка')

        row = next(r for r in phase.results if r['model'] == 'hr.rfid.card')
        self.assertEqual(
            (row['imported_count'], row['skipped_count']), (2, 1),
            'Числата на реда не отговарят на случилото се (2 донесени, 1 '
            'оставена): %s' % row)
        self.assertIn(
            self.NUMBER_WITHOUT_OWNER, row['error'] or '',
            'Редът в протокола не казва КОЯ карта е останала отвъд - при 400 '
            'карти операторът няма как да я намери: %s' % (row['error'],))
