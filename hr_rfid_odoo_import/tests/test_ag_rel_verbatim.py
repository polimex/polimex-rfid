# -*- coding: utf-8 -*-
"""Memberships the v19 model layer refuses are copied, not dropped (D41).

Both relation classes hold legacy rows in the live Odoo 15 cloud that today's
code would no longer create - the checks are word for word identical in v15,
so the source could not recreate them either:

* 234 employee memberships whose employee has NO department, so
  ``check_access_group`` matches them against an empty set of allowed groups.
  210 of those employees are active, 176 hold a live card and 2 120 card->door
  permissions hang off them - dropping the rows costs 176 people their access.
* 3 contact memberships with overlapping active periods for the same group
  (two of them expiring BEFORE they activate).

The bulk insert is NOT stubbed here: the row has to land in the real table,
under the real constraints, or the test proves nothing.
"""

from uuid import uuid4

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.importers import base_importer
from ..models.importers.access_importer import AccessImporter
from ..models.importers.base_importer import BaseImporter

SRC_DB = "verbatim_src"


class _FakeSource(BaseImporter):
    """BaseImporter reading in-memory fixtures; the TARGET side stays real."""

    def __init__(self, env, company_map, data):
        self.env = env
        self.source_db = SRC_DB
        # Двойникът не минава през `super().__init__` - идентичността на
        # източника трябва да се зададе изрично, иначе `_xml_id` гърми.
        self.source_slug = SRC_DB
        self.source_url = "http://localhost:1"
        self.source_uid = 1
        self.source_password = "x"
        self.company_map = company_map
        self.id_map = {}
        self.options = {"import_cards": False}
        self._field_cache = {}
        self._data = data

    def _has_model(self, model):
        return model in self._data

    def _get_source_fields(self, model):
        keys = set()
        for rec in self._data.get(model, []):
            keys |= set(rec)
        return {k: {} for k in keys}

    def _has_field(self, model, field_name):
        return field_name in self._get_source_fields(model)

    def _search_read(self, model, domain, fields, order="id asc", limit=0,
                     include_archived=True):
        return [dict(rec) for rec in self._data.get(model, [])]

    def _read_all(self, model, domain, fields, batch_size=1000):
        return self._search_read(model, domain, fields)


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_verbatim")
class TestAccessGroupRelVerbatim(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Verbatim Tenant"})
        cls.group = cls.env["hr.rfid.access.group"].create({
            "name": "Verbatim AG", "company_id": cls.company.id,
        })
        cls.other_group = cls.env["hr.rfid.access.group"].create({
            "name": "Verbatim AG 2", "company_id": cls.company.id,
        })
        # The employee that reproduces the defect: NO department at all.
        cls.orphan = cls.env["hr.employee"].create({
            "name": "No Department", "company_id": cls.company.id,
        })
        # ...and one whose department allows the group, for the normal path.
        cls.dept = cls.env["hr.department"].create({
            "name": "Verbatim Dept", "company_id": cls.company.id,
            "hr_rfid_allowed_access_groups": [(6, 0, [cls.group.id])],
        })
        cls.placed = cls.env["hr.employee"].create({
            "name": "With Department", "company_id": cls.company.id,
            "department_id": cls.dept.id,
        })
        cls.contact = cls.env["res.partner"].create({
            "name": "Verbatim Contact", "company_id": cls.company.id,
        })

    def _run(self, data, id_map_seed):
        base = _FakeSource(self.env, {101: self.company.id}, data)
        for model, mapping in id_map_seed.items():
            base.id_map[model] = dict(mapping)
        importer = AccessImporter(base)
        return base, importer

    def _result(self, importer, model):
        for res in importer.results:
            if res.get("model") == model:
                return res
        self.fail("no result reported for %s" % model)

    def _external_id_of(self, model, source_id, base):
        xid = base._xml_id_name(model.replace(".", "_"), source_id)
        return self.env["ir.model.data"].search([
            ("module", "=", "__import__"), ("model", "=", model),
            ("name", "=", xid),
        ], limit=1)

    # ------------------------------------------------------------- employees
    def test_membership_of_department_less_employee_is_copied(self):
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7001, "access_group_id": [55, "AG"],
                      "employee_id": [900, "No Department"],
                      "state": True, "internal_state": True}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {900: self.orphan.id}},
        )
        importer._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1, "the membership must exist in the target")
        self.assertEqual(rel.access_group_id, self.group)
        self.assertTrue(self._external_id_of(model, 7001, base),
                        "a copied row still needs its external ID, or a re-run "
                        "duplicates it and reconciliation counts it missing")
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 1)
        self.assertEqual(res["skipped_count"], 0,
                         "a copied membership is migrated, not skipped")

    def test_the_orm_path_is_still_used_when_it_works(self):
        """The fallback must not swallow the normal path (and its side effects)."""
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7002, "access_group_id": [55, "AG"],
                      "employee_id": [901, "With Department"], "state": True}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {901: self.placed.id}},
        )
        calls = []
        original = importer._copy_ag_rels_verbatim
        importer._copy_ag_rels_verbatim = lambda m, c, r: (
            calls.append(r) or original(m, c, r))
        importer._import_ag_employee_rels()

        self.assertEqual(calls, [[]], "nothing should have been refused")
        rel = self.env[model].search([("employee_id", "=", self.placed.id)])
        self.assertEqual(len(rel), 1)
        self.assertEqual(self._result(importer, model)["imported_count"], 1)

    def test_a_copied_row_carries_the_source_values(self):
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7003, "access_group_id": [55, "AG"],
                      "employee_id": [900, "No Department"], "state": True,
                      "activate_on": "2025-03-01 08:00:00",
                      "expiration": "2025-09-01 08:00:00",
                      "visits_counting": True, "permitted_visits": 12,
                      "visits_counter": 5}]},
            {"hr.rfid.access.group": {55: self.group.id},
             "hr.employee": {900: self.orphan.id}},
        )
        importer._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1)
        self.assertEqual(rel.permitted_visits, 12)
        self.assertEqual(rel.visits_counter, 5)
        self.assertTrue(rel.visits_counting)
        self.assertEqual(str(rel.activate_on), "2025-03-01 08:00:00")
        self.assertEqual(str(rel.expiration), "2025-09-01 08:00:00")

    def test_second_run_does_not_duplicate_a_copied_row(self):
        model = "hr.rfid.access.group.employee.rel"
        data = {model: [{"id": 7004, "access_group_id": [55, "AG"],
                         "employee_id": [900, "No Department"], "state": True}]}
        seed = {"hr.rfid.access.group": {55: self.group.id},
                "hr.employee": {900: self.orphan.id}}
        _, first = self._run(data, seed)
        first._import_ag_employee_rels()
        _, second = self._run(data, seed)
        second._import_ag_employee_rels()

        rel = self.env[model].search([("employee_id", "=", self.orphan.id)])
        self.assertEqual(len(rel), 1, "the external ID must make the copy idempotent")
        self.assertEqual(self._result(second, model)["imported_count"], 1)

    def test_unmapped_employee_is_skipped_not_copied(self):
        """A row we cannot place is a gap to report - never a row to force in."""
        model = "hr.rfid.access.group.employee.rel"
        base, importer = self._run(
            {model: [{"id": 7005, "access_group_id": [55, "AG"],
                      "employee_id": [999, "Never imported"], "state": True}]},
            {"hr.rfid.access.group": {55: self.group.id}, "hr.employee": {}},
        )
        importer._import_ag_employee_rels()

        self.assertFalse(self._external_id_of(model, 7005, base))
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 0)
        self.assertEqual(res["skipped_count"], 1)

    # -------------------------------------------------------------- contacts
    def test_overlapping_contact_periods_are_copied(self):
        model = "hr.rfid.access.group.contact.rel"
        base, importer = self._run(
            {model: [
                {"id": 7101, "access_group_id": [55, "AG"],
                 "contact_id": [700, "Verbatim Contact"], "state": False,
                 "activate_on": "2024-10-30 05:00:00",
                 "expiration": "2024-12-30 05:00:00"},
                # Overlaps the first one - the v19 model layer refuses it.
                {"id": 7102, "access_group_id": [55, "AG"],
                 "contact_id": [700, "Verbatim Contact"], "state": False,
                 "activate_on": "2024-11-26 05:00:00",
                 "expiration": "2025-01-26 05:00:00"},
            ]},
            {"hr.rfid.access.group": {55: self.group.id},
             "res.partner": {700: self.contact.id}},
        )
        importer._import_ag_contact_rels()

        rels = self.env[model].search([("contact_id", "=", self.contact.id)])
        self.assertEqual(len(rels), 2,
                         "both source periods belong in the target audit trail")
        self.assertTrue(self._external_id_of(model, 7102, base))
        res = self._result(importer, model)
        self.assertEqual(res["imported_count"], 2)
        self.assertEqual(res["skipped_count"], 0)


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_identity")
class TestSourceIdentity(TransactionCase):
    """Записът се води по СИСТЕМАТА, не по файла, от който е прочетена.

    Пълният внос чете възстановен бекъп, делтата - живия сървър. Това са две
    различни имена на база за ЕДНА И СЪЩА система. Ако вторият прогон се води
    под друго име, нищо не съвпада и всичко влиза втори път - за о15 облака
    това са 298 937 събития в дубликат.
    """

    def _importer(self, source_db, source_slug=None):
        return BaseImporter(
            env=self.env, source_url="http://localhost:1", source_db=source_db,
            source_uid=1, source_password="x", company_map={}, options={},
            source_slug=source_slug,
        )

    def test_same_source_read_from_two_places_is_one_system(self):
        backup = self._importer("15_cloud_src", source_slug="15_cloud_src")
        live = self._importer("15_polimex.cloud", source_slug="15_cloud_src")
        self.assertEqual(backup._xml_id_name("hr_rfid_event_user", 42),
                         live._xml_id_name("hr_rfid_event_user", 42))

    def test_default_follows_the_database_name(self):
        imp = self._importer("15_cloud_src")
        self.assertEqual(imp._xml_id_name("hr_employee", 5),
                         "rfid_import_15_cloud_src_hr_employee_5")

    def test_dots_and_dashes_are_normalised(self):
        imp = self._importer("x", source_slug="15_polimex.cloud-eu")
        self.assertEqual(imp._xml_id_name("hr_employee", 1),
                         "rfid_import_15_polimex_cloud_eu_hr_employee_1")


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_identity")
class TestOperatorIsWarnedBeforeASecondSystem(TransactionCase):
    """Операторът е спрян, преди един и същи източник да влезе два пъти.

    Бизнес твърдение (собственик, 2026-08-14): прехвърлянето може да се пуска
    неограничен брой пъти и никога не бива да дублира данни. Възстановеният
    бекъп и живият сървър са ДВЕ ИМЕНА НА ЕДНА система - ако операторът остави
    полето празно и двата пъти, вторият прогон се води под друго име, нищо не
    съвпада и всеки човек, врата, зона, членство и събитие влиза повторно.
    Досега това се случваше мълчаливо; сега екранът го казва предварително.
    """

    def setUp(self):
        super().setUp()
        # Тестът твърди нещо за база, в която ПРЕДИ него няма пренесени данни,
        # а екипът работи върху копия на работещи бази, където такива има.
        # Затова прехвърлянето получава СОБСТВЕНО име на записите си за времето
        # на теста: истинските пренесени редове престават да съвпадат с него, а
        # засадените тук съвпадат. Проверяваната логика е същата - сменя се
        # само пространството, в което гледа. Пропускането на теста беше
        # по-лошото решение: точно на базите, които значат нещо, твърдението
        # оставаше недоказано и се четеше като „минал".
        self.identity_space = 'rfid_import_test_%s_' % uuid4().hex
        self.patch(base_importer, 'EXTERNAL_ID_PREFIX', self.identity_space)

    def _wizard(self, **values):
        wiz = self.env['hr.rfid.odoo.import.wiz'].create(dict({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin',
            'source_password': 'admin',
            'source_db': 'live_server',
            'state': 'confirm',
        }, **values))
        self.env['hr.rfid.odoo.import.company.line'].create({
            'wizard_id': wiz.id,
            'source_id': 1,
            'source_name': 'Клиент',
            'do_import': True,
            'target_company_id': self.env.company.id,
        })
        return wiz

    def _pretend_records_are_here_from(self, slug):
        """Един запис, докаран от система на име `slug`."""
        employee = self.env['hr.employee'].create({'name': 'Пренесен човек'})
        self.env['ir.model.data'].create({
            'module': '__import__',
            'name': '%s%s_hr_employee_%s' % (
                self.identity_space, slug, employee.id),
            'model': 'hr.employee',
            'res_id': employee.id,
        })
        return employee

    def _pretend_transferred_from(self, slug):
        """Предишно прехвърляне от система на име `slug`: и запис, и следа."""
        self.env['hr.rfid.odoo.import.run'].create({
            'source_url': 'http://localhost:8069',
            'source_db': slug,
            'source_login': 'admin',
            'state': 'done',
        })
        return self._pretend_records_are_here_from(slug)

    def _warning(self, wiz):
        return (wiz.warnings or {}).get('other_source_identity')

    def test_a_second_name_for_the_same_system_is_blocked(self):
        """Прогон под ново име при вече пренесени данни спира преди старта."""
        self._pretend_transferred_from('restored_backup')
        wiz = self._wizard()

        warning = self._warning(wiz)
        self.assertTrue(warning, "Операторът не е предупреден изобщо")
        self.assertEqual(warning['level'], 'danger',
                         "Предупреждението трябва да спре прогона, не само да мига")
        self.assertTrue(wiz.has_blocking)
        with self.assertRaises(UserError):
            wiz.action_import()

    def test_the_warning_names_both_systems(self):
        """Операторът вижда КОЕ име вече е тук и КОЕ ще се ползва сега."""
        self._pretend_transferred_from('restored_backup')
        message = self._warning(self._wizard())['message']

        self.assertIn('restored_backup', message,
                      "Не се вижда под какво име са вече пренесените данни")
        self.assertIn('live_server', message,
                      "Не се вижда под какво име ще се води този прогон")
        for leak in ('ir.model.data', 'external ID', 'xml_id', 'slug'):
            self.assertNotIn(leak, message,
                             "Текстът е за оператора, не за програмист")

    def test_naming_the_same_system_lets_the_transfer_through(self):
        """Изходът от блокировката: операторът казва коя е системата."""
        self._pretend_transferred_from('restored_backup')
        wiz = self._wizard(source_slug='restored_backup')

        self.assertIsNone(self._warning(wiz),
                          "Същата система не е втора система")
        self.assertFalse(wiz.has_blocking)

    def test_a_genuinely_different_system_can_be_confirmed(self):
        """Втора система е законен случай - операторът я потвърждава сам."""
        self._pretend_transferred_from('restored_backup')
        wiz = self._wizard(source_slug='another_customer')

        warning = self._warning(wiz)
        self.assertTrue(warning, "Предупреждението остава - има данни от друга система")
        self.assertEqual(warning['level'], 'warning',
                         "Съзнателното решение не бива да блокира прогона")
        self.assertFalse(wiz.has_blocking)

    def test_a_first_ever_transfer_is_not_warned_about(self):
        """Отрицателното твърдение: чиста база не показва нищо излишно."""
        self.assertIsNone(self._warning(self._wizard()))

    def test_a_repeat_of_the_same_transfer_is_not_warned_about(self):
        """Повторният прогон на СЪЩИЯ източник не е втора система."""
        self._pretend_transferred_from('live_server')
        wiz = self._wizard()

        self.assertIsNone(self._warning(wiz),
                          "Собствените записи на този източник не са чужди")
        self.assertFalse(wiz.has_blocking)

    def test_data_brought_by_another_tool_does_not_stop_a_first_transfer(self):
        """Отрицателното твърдение: чужд инструмент не спира първото прехвърляне.

        Трите вноса - този, „Андромеда" и старият облак - записват донесеното по
        един и същ начин. Ако това се четеше като „тук вече има данни от друга
        система", първото прехвърляне от Odoo щеше да се спре с предупреждение
        за система, която операторът никога не е избирал. По-лошото е съветът в
        него: „напишете нейното име" - под името на Андромеда стоят НЕЙНИТЕ
        номера на записи, тоест хората щяха да се слеят с чужди.
        """
        self._pretend_records_are_here_from('andromeda')
        wiz = self._wizard()

        self.assertIsNone(
            self._warning(wiz),
            "Първото прехвърляне се спира заради данни на друг инструмент",
        )
        self.assertFalse(wiz.has_blocking)

    def test_the_warning_names_only_systems_this_transfer_has_read(self):
        """Назовава се системата, която значи нещо, а не всичко наоколо.

        Операторът трябва да разпознае името и да го напише - затова в текста
        влиза само система, от която ТОВА прехвърляне вече е чело. Име на чужд
        инструмент между тях би било покана за точно грешното действие.
        """
        self._pretend_records_are_here_from('andromeda')
        self._pretend_transferred_from('restored_backup')
        message = self._warning(self._wizard())['message']

        self.assertIn('restored_backup', message)
        self.assertNotIn(
            'andromeda', message,
            "Предупреждението сочи система, която операторът не може да ползва",
        )


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_identity")
class TestOperatorKnowsARepeatRefreshes(TransactionCase):
    """Операторът знае предварително какво прави повторният прогон.

    Бизнес твърдение (собственик, 2026-08-14): вторият прогон опреснява от
    другата система. Това е решението на собственика - и точно затова трябва
    да е казано на екрана ПРЕДИ старта, не открито след него.

    Само че прогонът НЕ прави едно и също с всичко: оборудването и картите се
    връщат както са в другата система, а хората, контактите, отделите и групите
    за достъп се разпознават и остават както са тук. Обещанието на екрана
    твърдеше първото за ВСИЧКО - затова тук се проверяват двете половини
    поотделно, всяка с името на това, което доказва. Поведението, което те
    описват, се доказва върху истинските фази в
    `test_second_run_changes_nothing.py`.
    """

    def _notice(self):
        wiz = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin',
            'source_password': 'admin',
            'source_db': 'live_server',
            'state': 'confirm',
        })
        notice = (wiz.warnings or {}).get('refresh_on_rerun')
        self.assertTrue(notice, "Последицата не се казва на оператора изобщо")
        self.assertNotEqual(
            notice['level'], 'danger',
            "Това е предупреждение, не пречка - прогонът е позволен",
        )
        for leak in ('noupdate', 'ir.model.data', '_load_records', 'external ID'):
            self.assertNotIn(leak, notice['message'],
                             "Текстът е за оператора, не за програмист")
        return notice['message']

    def test_the_confirm_page_says_the_equipment_and_cards_are_put_back(self):
        """Първата половина: върху оборудването и картите печели източникът."""
        message = self._notice()

        self.assertIn('again', message)
        self.assertIn('card switched off', message,
                      "Липсва конкретният пример, който операторът разпознава")
        self.assertIn('door renamed', message,
                      "Не се вижда, че поправка по оборудването не се пази")

    def test_the_confirm_page_says_corrections_to_people_are_kept(self):
        """Втората половина - тази, която обещанието твърдеше наопаки.

        Поправено име на човек НЕ се връща от другата система. Докато екранът
        казваше обратното, операторът или се отказваше от поправките си, или
        отлагаше следващото прехвърляне без нужда.
        """
        message = self._notice()

        self.assertIn('People', message,
                      "Не се казва, че хората не се презаписват")
        self.assertIn('keep', message,
                      "Не се казва, че поправеното тук остава")
        self.assertNotIn(
            "what came across is put back to the other system's version",
            message,
            "Обещанието пак твърди едно и също за всичко",
        )
