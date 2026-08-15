# -*- coding: utf-8 -*-
"""Източник с орязани права не спира прехвърлянето.

Бизнес твърдение (собственик, жива миграция на 2026-08-14): клиентски източник,
чийто администратор няма право над ЕДНО поле, пак се мигрира целият. На живо
`company_id` на аварийните групи (видимо само за мултифирмената група, а базата
е еднофирмена) събори цялата хардуерна фаза - нула контролери, нула врати, 697
карти и 20 851 събития без нищо, за което да се закачат.

Правото над полето е на ИЗТОЧНИКА и операторът на целта не може да го поправи
оттук; съдържанието му е без значение (фирмата се решава от съответствието в
съветника). Затова: полето отпада, записите идват, а какво е изпуснато се пише
в протокола - тихото изпускане е точно дефектът, който този модул съществува
да избягва.

Всички досегашни E2E прогони четяха с пълноправен администратор - класът
"източник с орязани права" нямаше нито един тест и точно през него мина живият
провал.
"""
import xmlrpc.client

from odoo.tests.common import TransactionCase, tagged

from ..models.importers.base_importer import BaseImporter


class _RestrictedRpc:
    """Източник, който отказва определени полета - как отказва реален Odoo.

    Отказът е с fault code 4 (AccessError - odoo18
    addons/base/controllers/rpc.py:28), а текстът е нарочно на език, който
    кодът не разбира: засичането трябва да е по кода, не по думите.
    """

    def __init__(self, records, refused_fields, refuse_everything=False):
        self.records = records
        self.refused = set(refused_fields)
        self.refuse_everything = refuse_everything
        self.read_calls = 0

    def execute_kw(self, db, uid, pwd, model, method, args, kwargs=None):
        if method == 'search':
            return [r['id'] for r in self.records]
        if method == 'read':
            self.read_calls += 1
            if self.refuse_everything:
                raise xmlrpc.client.Fault(4, 'nicht erlaubt')
            ids, fields = args
            if self.refused & set(fields):
                raise xmlrpc.client.Fault(4, 'nicht erlaubt: company_id')
            return [
                {k: r[k] for k in ['id'] + list(fields) if k in r}
                for r in self.records if r['id'] in ids
            ]
        raise AssertionError('unexpected RPC method %r' % method)


def _importer(env, rpc):
    """BaseImporter с реалното четене, но с подменен транспорт."""
    imp = BaseImporter.__new__(BaseImporter)
    imp.env = env
    imp.source_db = 'src'
    imp.source_uid = 1
    imp.source_password = 'x'
    imp.rpc_models = rpc
    imp.refused_fields = {}
    # Всеки двойник носи идентичност на източника: резолюцията и диагнозата
    # строят външни идентификатори от нея.
    imp.source_slug = 'srcdb'
    imp.time_is_up = None
    imp.stopped_early = False
    imp.read_cursors = {}
    imp._field_cache = {}
    # Пробата за 'active' пита източника за полетата му - тук не е на фокус.
    imp._has_field = lambda model, field: False
    return imp


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_rights')
class TestSourceRefusesAField(TransactionCase):

    def test_a_field_the_source_hides_does_not_cost_the_records(self):
        """Скрито поле = изпуснато поле, никога изпуснати записи."""
        rpc = _RestrictedRpc(
            [{'id': 7, 'name': 'Fire brigade', 'company_id': 1},
             {'id': 8, 'name': 'Guards', 'company_id': 1}],
            refused_fields={'company_id'},
        )
        imp = _importer(self.env, rpc)

        records = imp._search_read(
            'hr.rfid.ctrl.emergency.group', [], ['name', 'company_id'])

        self.assertEqual(
            [r['name'] for r in records], ['Fire brigade', 'Guards'],
            "Записите трябва да дойдат въпреки скритото поле")
        self.assertNotIn('company_id', records[0],
                         "Скритото поле не бива да се преструва на прочетено")
        self.assertEqual(
            imp.refused_fields, {'hr.rfid.ctrl.emergency.group': {'company_id'}},
            "Изпуснатото трябва да е записано, за да стигне до протокола")

    def test_later_pages_do_not_probe_again(self):
        """Веднъж намерено, скритото поле не струва нови проби на всяка
        страница - при 20 851 събития това са хиляди излишни запитвания."""
        rpc = _RestrictedRpc(
            [{'id': 7, 'name': 'Fire brigade', 'company_id': 1}],
            refused_fields={'company_id'},
        )
        imp = _importer(self.env, rpc)

        imp._search_read('m', [], ['name', 'company_id'])
        first = rpc.read_calls
        imp._search_read('m', [], ['name', 'company_id'])

        self.assertLessEqual(
            rpc.read_calls - first, 2,
            "Втората страница трябва да чете направо без полето, без да "
            "преоткрива отказа поле по поле")

    def test_a_source_that_refuses_the_records_still_fails_loudly(self):
        """Отказани САМИТЕ записи (а не поле) не се преглъщат - стъпката пада
        и изолацията ѝ го записва. Иначе 'няма права изобщо' би заприличало
        на 'няма данни'."""
        rpc = _RestrictedRpc([{'id': 7, 'name': 'x'}], refused_fields=set(),
                             refuse_everything=True)
        imp = _importer(self.env, rpc)

        with self.assertRaises(xmlrpc.client.Fault):
            imp._search_read('m', [], ['name'])

    def test_other_faults_are_not_swallowed(self):
        """Паднала връзка или счупен източник не е 'скрито поле' - минава
        нагоре веднага, без проби."""
        class _Broken(_RestrictedRpc):
            def execute_kw(self, db, uid, pwd, model, method, args, kwargs=None):
                if method == 'search':
                    return [7]
                raise xmlrpc.client.Fault(1, 'boom')

        imp = _importer(self.env, _Broken([], set()))
        with self.assertRaises(xmlrpc.client.Fault):
            imp._search_read('m', [], ['name'])


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_rights')
class TestProtocolLinesDoNotPileUp(TransactionCase):
    """Пас, който продължава фаза, заменя нейните редове, не ги трупа."""

    def test_a_resumed_phase_replaces_its_own_lines_only(self):
        run = self.env['hr.rfid.odoo.import.run'].create({
            'source_url': 'http://localhost:1',
            'source_login': 'admin',
            'source_password': 'x',
        })
        Log = self.env['hr.rfid.odoo.import.log']
        for phase, model in [('Phase 5', 'hr.rfid.event.user'),
                             ('Phase 5', 'hr.rfid.event.system'),
                             ('Phase 2', 'res.partner')]:
            Log.create({'run_id': run.id, 'phase': phase, 'model': model,
                        'status': 'partial'})

        class _Phase5:
            PHASE_ID = 'Phase 5'

        run._drop_stale_phase_lines(_Phase5)

        self.assertFalse(
            run.log_ids.filtered(lambda l: l.phase == 'Phase 5'),
            "Редовете на подновената фаза трябва да изчезнат преди новите")
        self.assertEqual(
            run.log_ids.mapped('model'), ['res.partner'],
            "Редовете на другите фази не бива да пострадат")


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_rights')
class TestSourceRefusesAFilter(TransactionCase):
    """Отказът може да дойде и от ФИЛТЪРА, не само от четенето.

    Живата миграция падна втори път точно така: полето вече отпадаше при
    четене, но стъпката ФИЛТРИРА по същото поле - и отказът дойде от
    търсенето. На еднофирмен източник филтърът по фирма без друго избира
    всичко, а правата на самия акаунт продължават да важат.
    """

    def test_a_hidden_field_in_the_filter_does_not_stop_the_search(self):
        class _Rpc(_RestrictedRpc):
            def execute_kw(self, db, uid, pwd, model, method, args, kwargs=None):
                if method == 'search':
                    domain = args[0]
                    if any(isinstance(l, (list, tuple)) and l
                           and str(l[0]).split('.')[0] in self.refused
                           for l in domain):
                        raise xmlrpc.client.Fault(4, 'verboten: company_id')
                    return [r['id'] for r in self.records]
                return super().execute_kw(db, uid, pwd, model, method, args, kwargs)

        rpc = _Rpc([{'id': 7, 'name': 'Fire brigade'}],
                   refused_fields={'company_id'})
        imp = _importer(self.env, rpc)

        records = imp._search_read(
            'hr.rfid.ctrl.emergency.group',
            [('company_id', 'in', [1])], ['name'])

        self.assertEqual([r['name'] for r in records], ['Fire brigade'],
                         "Филтър по скрито поле не бива да спира записите")
        # Отказът се ДОКЛАДВА в протоколния ред, но НЕ се помни: запомнянето
        # веднъж отряза камерния крак на всяко следващо четене и 20 851
        # разпознати номера станаха невидими при чист протокол.
        result = imp._make_result('m', 1, 1)
        self.assertIn('company_id', result['error'],
                      "Редът казва кой клон на филтъра е отказан")
        self.assertNotIn(
            'company_id',
            imp.refused_fields.get('hr.rfid.ctrl.emergency.group', set()),
            "И не се запомня - следващото четене пробва пълния филтър")

    def test_the_m2o_shape_from_the_source_never_crashes_the_reader(self):
        """Живата миграция: 'int' object is not subscriptable свали цялата
        фаза Хора - четенето връща голо число, кодът индексираше [0]."""
        base = _importer(self.env, _RestrictedRpc([], set()))
        self.assertEqual(base._m2o_id(13), 13)
        self.assertEqual(base._m2o_id([13, 'Name']), 13)
        self.assertEqual(base._m2o_id(False), False)
        self.assertEqual(base._m2o_id([]), False)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_rights')
class TestUnmatchedDoorIsDiagnosedFromTheSource(TransactionCase):
    """Ред за несъпоставена врата казва КАКВО е тя, попитал източника на живо.

    Собственикът, след три протокола с "no match here" (2026-08-15): при
    грешка логът сам носи детайла, за да се разбере какво се е случило.
    Трите случая искат три различни действия - изтрита врата (окончателно,
    не е грешка), врата на невключена фирма (операторът решава), врата в
    обхват, която не е дошла (истинска грешка).
    """

    def _base(self, records_by_model):
        rpc = _RestrictedRpc([], set())
        imp = _importer(self.env, rpc)
        def _search_read(model, domain, fields, **kw):
            rows = records_by_model.get(model, [])
            if domain and domain[0][0] == 'id':
                rows = [r for r in rows if r['id'] == domain[0][2]]
            elif domain and domain[0][0] == 'door_id':
                rows = [r for r in rows if r.get('door_id') == domain[0][2]]
            return [dict(r) for r in rows]
        imp._search_read = _search_read
        imp._has_model = lambda m: 'cctv.camera' in records_by_model
        imp.company_map = {101: self.env.company.id}
        return imp

    def test_a_deleted_door_is_final_not_an_error(self):
        imp = self._base({'hr.rfid.door': []})
        sentence, is_real = imp.describe_unmatched_door(5)
        self.assertFalse(is_real, "Изтритата врата е окончателен изход")
        self.assertIn("deleted", sentence)

    def test_a_door_of_an_excluded_company_names_the_company(self):
        imp = self._base({
            'hr.rfid.door': [{'id': 5, 'name': 'Barrier', 'controller_id': 9}],
            'hr.rfid.ctrl': [{'id': 9, 'webstack_id': 3}],
            'hr.rfid.webstack': [{'id': 3, 'company_id': 202}],
            'res.company': [{'id': 202, 'name': 'Other Tenant'}],
        })
        sentence, is_real = imp.describe_unmatched_door(5)
        self.assertFalse(is_real, "Невключена фирма е решение на оператора")
        self.assertIn("Other Tenant", sentence,
                      "Редът трябва да назове фирмата, не да остави гадаене")

    def test_a_door_in_scope_that_did_not_arrive_stays_a_real_error(self):
        imp = self._base({
            'hr.rfid.door': [{'id': 5, 'name': 'Front', 'controller_id': 9}],
            'hr.rfid.ctrl': [{'id': 9, 'webstack_id': 3}],
            'hr.rfid.webstack': [{'id': 3, 'company_id': 101}],
        })
        sentence, is_real = imp.describe_unmatched_door(5)
        self.assertTrue(is_real, "Врата в обхват без съответствие е дефект")
        self.assertIn("hardware step", sentence)


@tagged('post_install', '-at_install', 'rfid_odoo_import', 'rfid_import_rights')
class TestEveryLeftBehindRowNamesItsReason(TransactionCase):
    """Никой не гадае по протокола: всеки оставен ред казва защо.

    Собственикът (2026-08-15): "искам точен лог какво има за прехвърляне и
    причината защо не си могъл - В ЛОГА". Отчитането е в самите канали за
    съпоставяне, затова важи за всяка стъпка, без 59-те места за пропуск да
    трябва да си го спомнят поотделно.
    """

    def _imp(self):
        imp = _importer(self.env, _RestrictedRpc([], set()))
        imp.company_map = {101: self.env.company.id}
        imp.id_map = {}
        imp._pending_skips = {}
        # Резолюцията по външен идентификатор чете source_slug - двойникът
        # без __init__ трябва да си го носи, както прави и _FakeSource.
        imp.source_slug = 'srcdb'
        return imp

    def test_a_missing_pointer_is_named_with_its_number(self):
        imp = self._imp()
        self.assertFalse(imp._map_m2o('hr.rfid.door', 5))
        self.assertFalse(imp._map_m2o('hr.rfid.door', 5))
        result = imp._make_result('x', 2, 0, 0, 2)
        self.assertIn('№5', result['error'],
                      "Редът трябва да назове номера от източника")
        self.assertIn('2', result['error'],
                      "И колко реда е коствал този пропуск")

    def test_an_excluded_company_is_a_named_reason_not_a_mystery(self):
        imp = self._imp()
        self.assertFalse(imp._map_company(202))
        result = imp._make_result('x', 1, 0, 0, 1)
        self.assertIn('№202', result['error'])

    def test_reasons_do_not_leak_into_the_next_line(self):
        imp = self._imp()
        imp._map_m2o('hr.rfid.door', 5)
        imp._make_result('x', 1, 0, 0, 1)
        clean = imp._make_result('y', 3, 3, 0, 0)
        self.assertFalse(clean['error'],
                         "Причините принадлежат на СВОЯ ред, не на следващия")
