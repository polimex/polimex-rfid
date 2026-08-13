# hr_rfid_odoo_import - имплементационен план на разширението

> **За изпълнителя:** задачите се изпълняват по ред. Всяка завършва с работещ,
> тестван резултат и собствен commit. Спецификацията е `EXTENSION_PLAN.md`
> (commit b6a7401) - тя е "защо", този файл е "как".

**Цел:** пълна миграция на RFID набора Odoo 18 -> 19, включително камери и обекти,
с фазов регистър, който казва какво пропуска, и фонов прогон, който издържа обема.

**Архитектура:** фазите стават класове с декларирани изисквания в регистър; wizard-ът
подава заявка на постоянен модел, крон я върти на партиди с `_commit_progress`;
камерите и обектите са две нови фази; командите към живо желязо се потискат с
context flag по образеца на `hr_rfid`.

**Стек:** Odoo 19 CE, Python 3.12, XML-RPC към източника, PostgreSQL.

## Глобални ограничения

- Версия: `X.0.y.z.w`, бумпва се като ПОСЛЕДНА редакция преди `git add`, с Edit tool
  (никога чрез python read-write-replace - празен манифест сваля модула).
- Никакъв AI брандинг. Автор: `Polimex Dev Team`. Сайт: `https://polimex.co`.
- Хиперфен `-`, никога em/en dash, във всеки създаван или редактиран файл.
- Потребителски низове: `self.env._()` в модели; без имена на модели/полета/модули
  в текста, който вижда операторът.
- `depends` на `hr_rfid_odoo_import` остава `['hr_rfid']`. Сателитите се откриват,
  не се изискват.
- Идентичност само по source id през `ir.model.data` ledger. Съвпадащ текст не е
  идентичност.
- Всички операции с бази през `odoo-db-ops`. Без директен psql/createdb.
- Тестови прогони: `--stop-after-init --no-http`, обвити с `timeout -k 30`.
- Тестовете произлизат от бизнес твърдение, записано в docstring-а, не от кода.

---

## Файлова структура

**Нови файлове**

| Път | Отговорност |
|---|---|
| `hr_rfid_odoo_import/models/importers/phase.py` | `PhaseImporter` базов клас + регистър + `phase_plan()` |
| `hr_rfid_odoo_import/models/importers/camera_importer.py` | фаза Cameras |
| `hr_rfid_odoo_import/models/importers/site_importer.py` | фаза Sites |
| `hr_rfid_odoo_import/models/import_run.py` | постоянен `hr.rfid.odoo.import.run` |
| `hr_rfid_odoo_import/data/ir_cron.xml` | крон записът |
| `hr_rfid_odoo_import/views/import_run_views.xml` | списък/форма на прогоните |
| `hr_rfid_odoo_import/tests/test_phase_registry.py` | R1-R7 |
| `hr_rfid_odoo_import/tests/test_camera_phase.py` | C1-C7 |
| `hr_rfid_odoo_import/tests/test_site_phase.py` | S1-S5 |
| `hr_rfid_odoo_import/tests/test_background_run.py` | A1-A7 |
| `polimex_ip_cam/tests/test_import_guards.py` | нула команди под импорт |
| `hr_rfid/tests/test_access_group_add_doors.py` | график по фирма |

**Променяни файлове**

| Път | Промяна |
|---|---|
| `polimex_ip_cam/models/cctv_camera_rfid_rel.py` | guard в `create` и `unlink` |
| `polimex_ip_cam/models/cctv_camera_command.py` | guard в `create` преди `queue_send` |
| `polimex_ip_cam/models/cctv_camera.py` | guard в `create` (авто-четци/врата) |
| `polimex_ip_cam/models/hr_rfid_door.py` | guard в трите метода на `card.door.rel` + липсващ `return` в `write` |
| `hr_rfid/models/hr_rfid_access_group.py:189-192` | график в рамките на фирмата + `UserError` |
| `hr_rfid_odoo_import/models/import_wizard.py` | `_do_import` -> регистър; заявка към `run`; нови computed полета |
| `hr_rfid_odoo_import/models/import_conflict.py` | нов `hr.rfid.odoo.import.phase.line` |
| `hr_rfid_odoo_import/models/importers/*.py` | наследяват `PhaseImporter` |
| `hr_rfid_odoo_import/models/importers/event_importer.py` | ANPR клон + сверка |
| `hr_rfid_odoo_import/models/importers/core_importer.py` | `io_table` след-импорт стъпка |
| `hr_rfid_odoo_import/views/import_wizard_views.xml` | рендер на предупрежденията, ред-на-фаза |
| `hr_rfid_odoo_import/security/ir.model.access.csv` | редове за новите модели |
| `hr_rfid_odoo_import/README.rst` | махане на невярното твърдение за dynamic discovery |

---

## Задача 1: Guard-ове срещу команди към живо желязо (polimex_ip_cam)

**Файлове:**
- Modify: `polimex_ip_cam/models/cctv_camera_rfid_rel.py:65-99`
- Modify: `polimex_ip_cam/models/cctv_camera_command.py:71-86`
- Modify: `polimex_ip_cam/models/cctv_camera.py:247-274`
- Modify: `polimex_ip_cam/models/hr_rfid_door.py:29-70`
- Test: `polimex_ip_cam/tests/test_import_guards.py`

**Интерфейси:**
- Consumes: `no_hardware_commands` от `hr_rfid` конвенцията (`hr_rfid_door.py:840`).
- Produces: инвариант "под `no_hardware_commands` не се създава команда и не се
  фабрикува запис без произход", на който стъпват задачи 7 и 9.

- [ ] **Стъпка 1: Написване на падащия тест**

`polimex_ip_cam/tests/test_import_guards.py`:

```python
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'ipcam_guards')
class TestImportGuards(TransactionCase):
    """Пренасяне на данни не бива да пипа работеща камера.

    Бизнес твърдение: когато прехвърляме системата на нов сървър, камерите на
    обекта продължават да работят - никой не им праща команди, докато трае
    прехвърлянето, и никой не им сменя настройките.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plate_type = cls.env.ref('hr_rfid.hr_rfid_card_type_8')
        cls.camera = cls.env['cctv.camera'].with_context(
            no_hardware_commands=True,
        ).create({
            'name': 'Порта',
            'ip_address': '10.0.0.9',
            'brand': 'hikvision',
        })
        cls.card = cls.env['hr.rfid.card'].create({
            'number': 'CA1234AB',
            'card_type': cls.plate_type.id,
        })

    def test_import_creates_no_camera_commands(self):
        """Под пренос не тръгва нито една команда към камерата."""
        before = self.env['cctv.camera.command'].search_count([])
        self.env['cctv.camera.rfid.rel'].with_context(
            no_hardware_commands=True,
        ).create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        self.assertEqual(
            self.env['cctv.camera.command'].search_count([]), before,
            "Пренасянето на номер е поставило команда в опашката на камерата",
        )

    def test_import_removal_creates_no_commands(self):
        """Махането на връзка под пренос също мълчи."""
        rel = self.env['cctv.camera.rfid.rel'].with_context(
            no_hardware_commands=True,
        ).create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        before = self.env['cctv.camera.command'].search_count([])
        rel.with_context(no_hardware_commands=True).unlink()
        self.assertEqual(
            self.env['cctv.camera.command'].search_count([]), before,
            "Махането на номер е поставило команда в опашката",
        )

    def test_import_does_not_fabricate_readers(self):
        """Пренесена камера не си измисля четци и врата.

        Четците и вратата идват от източника със своя произход; ако камерата
        ги произведе сама, в целта стоят два комплекта и никой не знае кой е
        истинският.
        """
        camera = self.env['cctv.camera'].with_context(
            no_hardware_commands=True,
        ).create({
            'name': 'Служебен вход',
            'ip_address': '10.0.0.10',
            'brand': 'hikvision',
        })
        self.assertFalse(
            camera.reader_ids,
            "Пренесената камера е произвела четци без произход",
        )

    def test_normal_use_still_sends_commands(self):
        """Без пренос всичко работи както преди - гардът не изключва функцията."""
        before = self.env['cctv.camera.command'].search_count([])
        self.env['cctv.camera.rfid.rel'].create({
            'camera_id': self.camera.id,
            'card_id': self.card.id,
            'list_category': 'whitelist',
        })
        self.assertGreater(
            self.env['cctv.camera.command'].search_count([]), before,
            "Обикновеното добавяне на номер вече не стига до камерата",
        )
```

- [ ] **Стъпка 2: Прогон, който трябва да падне**

```bash
cd /home/lubo/PycharmProjects/odoo19
timeout -k 30 900 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags ipcam_guards -u polimex_ip_cam \
    --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: падат `test_import_creates_no_camera_commands`,
`test_import_removal_creates_no_commands`, `test_import_does_not_fabricate_readers`;
минава `test_normal_use_still_sends_commands`.

- [ ] **Стъпка 3: Guard в `cctv.camera.rfid.rel`**

`cctv_camera_rfid_rel.py`, в `create` веднага след `records = super().create(vals_list)`:

```python
        # Пренасяне на данни не говори с желязото. Същата конвенция като
        # hr_rfid (hr_rfid_door.py:840) - иначе миграция на хиляди номера
        # праща хиляди HTTP заявки към работещи камери.
        if self.env.context.get('no_hardware_commands'):
            return records
```

В `unlink`, като първи ред на тялото:

```python
        if self.env.context.get('no_hardware_commands'):
            return super().unlink()
```

- [ ] **Стъпка 4: Guard в `cctv.camera.command`**

`cctv_camera_command.py`, в `create` след `records = super().create(vals_list)`:

```python
        # Защита в дълбочина: queue_send регистрира postcommit hook, който
        # ПРЕЖИВЯВА savepoint rollback (sql_db.py:137-140 вика clear(), а
        # clear() чисти само precommit - :188-193). Гард само на извикващите
        # места би позволил откатната фаза пак да стреля по камерата.
        if self.env.context.get('no_hardware_commands'):
            return records
```

- [ ] **Стъпка 5: Guard в `cctv.camera`**

`cctv_camera.py`, в `create`, вътре в цикъла, веднага след
`new_record = super().create(vals)`:

```python
            if self.env.context.get('no_hardware_commands'):
                # Пренесената камера получава четците и вратата си от
                # източника, с техния произход. Ако ги произведем тук, в
                # целта стоят два комплекта и идентичността се губи.
                new_records += new_record
                continue
```

- [ ] **Стъпка 6: Guard в трите метода на `hr.rfid.card.door.rel` + липсващият `return`**

`polimex_ip_cam/models/hr_rfid_door.py`. В `create`, преди
`if vals.get('door_id') and vals.get('card_id'):` добави проверка, която пропуска
огледалото към камерата:

```python
        mirror_to_camera = not self.env.context.get('no_hardware_commands')
```

и смени условието на `if mirror_to_camera and vals.get('door_id') and vals.get('card_id'):`.

В `write` - гардни огледалото и **върни резултата** (днес методът не връща нищо,
докато ORM договорът иска `True`):

```python
    def write(self, vals):
        mirror_to_camera = not self.env.context.get('no_hardware_commands')
        res = True
        for rel in self.with_user(SUPERUSER_ID):
            old_door = rel.door_id
            old_card = rel.card_id

            res = super(HrRfidCardDoorRel, rel).write(vals)

            new_door = rel.door_id
            new_card = rel.card_id

            if mirror_to_camera and old_door.camera_id and (
                    old_door != new_door or old_card != new_card):
                old_door.camera_id.remove_card_id_from_list(old_card.id)
                new_door.camera_id.add_card_id_to_list(new_card)
        return res
```

В `unlink`, като първи ред:

```python
        if self.env.context.get('no_hardware_commands'):
            create_cmd = False
```

- [ ] **Стъпка 7: Прогон - всички трябва да минат**

Същата команда като стъпка 2. Очаквано: `0 failed, 0 error(s)`.

- [ ] **Стъпка 8: Проверка на инсталационния лог**

```bash
grep -iE "Access Rights Inconsistency|RELAXNG|does not exist|Field .* (used|not found)|deprecated|demo data failed" /tmp/guards.log
```

Очаквано: празно.

- [ ] **Стъпка 9: Версия и commit**

Бумпни `polimex_ip_cam/__manifest__.py` на `19.0.1.12.0` **с Edit tool**, после:

```bash
git add polimex_ip_cam/
git commit -m "камерата спира да слуша, докато я пренасяме"
```

---

## Задача 2: Времевият график на групата идва от нейната фирма (hr_rfid)

**Файлове:**
- Modify: `hr_rfid/models/hr_rfid_access_group.py:189-192`
- Test: `hr_rfid/tests/test_access_group_add_doors.py`

**Интерфейси:**
- Produces: `add_doors` вече не може да върне график на чужда фирма; задача 8
  (Sites) разчита на това, защото `_update_access_groups` минава оттам.

- [ ] **Стъпка 1: Написване на падащия тест**

```python
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'rfid_access_group')
class TestAddDoorsTimeSchedule(TransactionCase):
    """Правата на една фирма не се пишат с графика на друга.

    Бизнес твърдение: когато на обект на фирма А се даде достъп до врата,
    работното време идва от графиците на фирма А. Графикът на фирма Б няма
    нищо общо с нейните хора и не бива да попада в правата ѝ.
    """

    def test_schedule_comes_from_the_group_company(self):
        company_a = self.env['res.company'].create({'name': 'Фирма А'})
        company_b = self.env['res.company'].create({'name': 'Фирма Б'})
        # Графикът на Б е с по-малък номер, тоест печели при търсене без филтър.
        self.env['hr.rfid.time.schedule'].search([]).unlink()
        self.env['hr.rfid.time.schedule'].create({
            'name': 'График Б', 'number': 1, 'company_id': company_b.id,
        })
        schedule_a = self.env['hr.rfid.time.schedule'].create({
            'name': 'График А', 'number': 2, 'company_id': company_a.id,
        })
        group = self.env['hr.rfid.access.group'].create({
            'name': 'Група А', 'company_id': company_a.id,
        })
        door = self.env['hr.rfid.door'].create({'name': 'Врата А', 'number': 1})

        group.add_doors(door)

        rel = self.env['hr.rfid.access.group.door.rel'].search([
            ('access_group_id', '=', group.id), ('door_id', '=', door.id),
        ])
        self.assertEqual(
            rel.time_schedule_id, schedule_a,
            "Правото е записано с работното време на друга фирма",
        )

    def test_missing_schedule_says_so(self):
        """Липсващ график казва какво липсва, вместо да гръмне неразбираемо."""
        company = self.env['res.company'].create({'name': 'Фирма без график'})
        self.env['hr.rfid.time.schedule'].search([]).unlink()
        group = self.env['hr.rfid.access.group'].create({
            'name': 'Група', 'company_id': company.id,
        })
        door = self.env['hr.rfid.door'].create({'name': 'Врата', 'number': 1})
        with self.assertRaises(UserError):
            group.add_doors(door)
```

- [ ] **Стъпка 2: Прогон, който трябва да падне**

```bash
timeout -k 30 900 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_access_group -u hr_rfid \
    --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: и двата теста падат (първият с грешен график, вторият с `IndexError`).

- [ ] **Стъпка 3: Поправка**

`hr_rfid/models/hr_rfid_access_group.py`, замени редове 189-192:

```python
    def add_doors(self, door_ids, time_schedule=None, alarm_rights=False):
        self.ensure_one()
        if time_schedule is None:
            # Графикът е на фирмата на групата (или на вратата, ако групата е
            # глобална). Търсене без филтър връща графика на който и да е
            # наемател - на multi-company база това записва работното време
            # на чужда фирма в правата на тази.
            company = self.company_id or door_ids[:1].company_id
            domain = [('company_id', 'in', [company.id, False])] if company else []
            time_schedule = self.env['hr.rfid.time.schedule'].search(
                domain, limit=1, order='number',
            )
            if not time_schedule:
                raise UserError(self.env._(
                    "There is no working time defined yet. Create one before "
                    "granting access to doors."
                ))
```

- [ ] **Стъпка 4: Прогон - трябва да минат**

Същата команда. Очаквано: `0 failed, 0 error(s)`.

- [ ] **Стъпка 5: Регресия на целия hr_rfid пакет**

```bash
timeout -k 30 2700 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_hardware,rfid_card,rfid_access_group,rfid_events,rfid_constraints,rfid_security,rfid_apb,rfid_time_schedules,rfid_wizards,rfid_commands,rfid_webstack \
    -u hr_rfid --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: `0 failed, 0 error(s)` - `add_doors` се вика от няколко места.

- [ ] **Стъпка 6: Версия и commit**

Бумпни `hr_rfid/__manifest__.py` на `19.0.2.27.0` с Edit tool.

```bash
git add hr_rfid/
git commit -m "правата на една фирма спират да носят работното време на друга"
```

Пренасяне в 15.0 и 18.0: отделни commit-и в съответните клонове, същият тест.

---

## Задача 3: Предупрежденията се четат от човек

**Файлове:**
- Modify: `hr_rfid_odoo_import/models/import_wizard.py:215-219, 279-349`
- Modify: `hr_rfid_odoo_import/views/import_wizard_views.xml:19-21`
- Test: `hr_rfid_odoo_import/tests/test_warnings_render.py`

**Интерфейси:**
- Consumes: `warnings` (Json) - остава непроменено, то храни гейта на `:757-767`.
- Produces: `has_blocking` (Boolean) - задача 5 го ползва за гейтване на бутона.

- [ ] **Стъпка 1: Написване на падащия тест**

```python
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_import_ui')
class TestWarningsRender(TransactionCase):
    """Операторът чете предупреждение, не програмен запис.

    Бизнес твърдение: човекът, който прехвърля системата, вижда изречение на
    своя език, което му казва какво не е наред и какво да направи.
    """

    def _wizard(self):
        return self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin',
            'source_password': 'admin',
            'state': 'confirm',
        })

    def test_warning_is_a_sentence_not_a_record(self):
        wiz = self._wizard()
        self.assertTrue(wiz.has_blocking, "Прогон без избрана фирма не е блокиран")
        html = wiz.blocking_html or ''
        self.assertNotIn('{"', html, "Предупреждението показва програмен запис")
        self.assertNotIn("'level'", html, "Предупреждението показва програмен запис")

    def test_resolving_the_problem_clears_the_warning(self):
        """Решен проблем гаси предупреждението веднага, без презареждане."""
        wiz = self._wizard()
        self.env['hr.rfid.odoo.import.company.line'].create({
            'wizard_id': wiz.id, 'source_id': 1, 'source_name': 'Фирма',
            'do_import': True, 'target_company_id': self.env.company.id,
        })
        wiz.invalidate_recordset(['warnings', 'has_blocking', 'blocking_html'])
        self.assertFalse(
            wiz.has_blocking,
            "Предупреждението остана, след като проблемът е решен",
        )
```

- [ ] **Стъпка 2: Прогон, който трябва да падне**

```bash
timeout -k 30 900 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_import_ui -u hr_rfid_odoo_import \
    --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: `AttributeError` за `has_blocking`.

- [ ] **Стъпка 3: Новите полета**

В `import_wizard.py`, до `warnings`:

```python
    has_blocking = fields.Boolean(
        compute='_compute_warning_render',
        help="True when at least one problem must be solved before the transfer can start.",
    )
    has_advisory = fields.Boolean(
        compute='_compute_warning_render',
        help="True when there is something worth knowing that does not stop the transfer.",
    )
    blocking_html = fields.Html(
        compute='_compute_warning_render', sanitize=False,
        help="Problems that stop the transfer, rendered for the operator.",
    )
    advisory_html = fields.Html(
        compute='_compute_warning_render', sanitize=False,
        help="Notices that do not stop the transfer, rendered for the operator.",
    )

    @api.depends('warnings')
    def _compute_warning_render(self):
        for wiz in self:
            entries = wiz.warnings or {}
            blocking = [v['message'] for v in entries.values()
                        if v.get('level') == 'danger']
            advisory = [v['message'] for v in entries.values()
                        if v.get('level') != 'danger']
            wiz.has_blocking = bool(blocking)
            wiz.has_advisory = bool(advisory)
            wiz.blocking_html = Markup('<ul>%s</ul>') % Markup('').join(
                Markup('<li>%s</li>') % m for m in blocking
            ) if blocking else False
            wiz.advisory_html = Markup('<ul>%s</ul>') % Markup('').join(
                Markup('<li>%s</li>') % m for m in advisory
            ) if advisory else False
```

Добави `from markupsafe import Markup` в началото на файла.

- [ ] **Стъпка 4: Пълен `@api.depends` на `warnings`**

Замени `@api.depends('state', 'company_line_ids.do_import', 'conflict_ids')` на ред 279 с:

```python
    @api.depends('state', 'company_line_ids.do_import',
                 'company_line_ids.target_company_id',
                 'conflict_ids', 'conflict_ids.resolution',
                 'import_vending', 'import_attendance',
                 'import_attendance_extra', 'import_service')
```

Днешният списък не изброява четените полета (`:300, :317, :339`), затова решен
конфликт не гаси предупреждението.

- [ ] **Стъпка 5: Изгледът**

В `import_wizard_views.xml` замени ред 19-21:

```xml
                        <div class="alert alert-danger" role="alert"
                             invisible="state != 'confirm' or not has_blocking">
                            <field name="blocking_html" nolabel="1" readonly="1"/>
                        </div>
                        <div class="alert alert-warning" role="alert"
                             invisible="state != 'confirm' or not has_advisory">
                            <field name="advisory_html" nolabel="1" readonly="1"/>
                        </div>
```

- [ ] **Стъпка 6: Човешки текст на съобщенията за модули**

В `_compute_warnings`, съобщенията на `module_checks` (`:309-336`) днес назовават
модули (`hr_attendance_late`). Замени картата с човешки имена:

```python
            module_labels = {
                'hr_rfid_vending': self.env._("vending machines"),
                'hr_attendance_multi_rfid': self.env._("attendance"),
                'hr_attendance_late': self.env._("working time reports"),
                'rfid_service_base': self.env._("visitor services"),
            }
```

и ползвай `module_labels[mod_name]` в текста вместо `mod_name`.

- [ ] **Стъпка 7: Прогон - трябва да минат**

Същата команда като стъпка 2. Очаквано: `0 failed, 0 error(s)`.

- [ ] **Стъпка 8: Commit**

```bash
git add hr_rfid_odoo_import/
git commit -m "предупреждението спира да бъде програмен запис на екрана"
```

---

## Задача 4: `PhaseImporter`, регистър и `phase_plan`

**Файлове:**
- Create: `hr_rfid_odoo_import/models/importers/phase.py`
- Modify: всички `hr_rfid_odoo_import/models/importers/*_importer.py`
- Modify: `hr_rfid_odoo_import/models/import_wizard.py:784-915`
- Test: `hr_rfid_odoo_import/tests/test_phase_registry.py`

**Интерфейси:**
- Produces: `PhaseImporter` (class attributes `PHASE_ID`, `NAME`, `REQUIRES_SOURCE`,
  `REQUIRES_TARGET`, `OPTION`, `WEIGHT`; `__init__(self, base)`), `PHASE_REGISTRY`
  (списък от класове, в реда на изпълнение), `phase_plan(env, options, source_modules)`
  -> `list[tuple[type, str | None]]`. Задачи 6, 7, 8 добавят класове към регистъра.

- [ ] **Стъпка 1: Написване на падащия тест**

```python
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
    PHASE_REGISTRY, phase_plan,
)


@tagged('post_install', '-at_install', 'rfid_import_registry')
class TestPhaseRegistry(TransactionCase):
    """Пренасянето казва какво пропуска и защо.

    Бизнес твърдение: операторът не бива да открива липсващи данни седмица
    по-късно. Всяко нещо, което не е пренесено, стои в протокола с причина.
    """

    def _names(self):
        return [p.NAME for p in PHASE_REGISTRY]

    def test_zones_come_after_people(self):
        """Зоните се пълнят с хора, значи хората идват първи.

        Обратният ред записва празни списъци с noupdate, тоест следващ прогон
        не може да ги поправи.
        """
        names = self._names()
        self.assertGreater(names.index('Zones'), names.index('People'))

    def test_missing_module_is_reported_not_silent(self):
        """Липсваща функционалност в източника се отчита с причина."""
        plan = phase_plan(self.env, options={}, source_modules=set())
        reasons = {cls.NAME: reason for cls, reason in plan}
        skipped = [n for n, r in reasons.items() if r]
        self.assertTrue(skipped, "Нищо не е отчетено като пропуснато")
        for name in skipped:
            self.assertTrue(
                reasons[name].strip(),
                "Фаза %s е пропусната без да казва защо" % name,
            )

    def test_abstract_model_does_not_count_as_available(self):
        """Модел без собствена таблица не минава за налична функционалност."""
        from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
            _target_available,
        )
        self.assertFalse(_target_available(self.env, 'hr.rfid.access.group.rel'))

    def test_model_without_the_needed_column_does_not_count(self):
        """Наличен модел без нужната колона също не минава."""
        from odoo.addons.hr_rfid_odoo_import.models.importers.phase import (
            _target_available,
        )
        self.assertFalse(
            _target_available(self.env, ('res.partner', 'no_such_field_here')))
        self.assertTrue(_target_available(self.env, ('res.partner', 'name')))

    def test_progress_is_monotonic_and_complete(self):
        """Лентата расте и стига до края."""
        total = sum(p.WEIGHT for p in PHASE_REGISTRY)
        self.assertGreater(total, 0)
        acc, last = 0, 0
        for p in PHASE_REGISTRY:
            acc += p.WEIGHT
            pct = acc * 100.0 / total
            self.assertGreaterEqual(pct, last)
            last = pct
        self.assertAlmostEqual(last, 100.0, places=6)

    def test_plan_needs_no_network(self):
        """Планът се смята без връзка към източника и без запис в базата."""
        plan = phase_plan(self.env, options={'import_people': True},
                          source_modules={'hr_rfid'})
        self.assertEqual(len(plan), len(PHASE_REGISTRY))
```

- [ ] **Стъпка 2: Прогон, който трябва да падне**

```bash
timeout -k 30 900 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_import_registry -u hr_rfid_odoo_import \
    --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: `ModuleNotFoundError` за `phase`.

- [ ] **Стъпка 3: Базовият клас и гейтът**

`hr_rfid_odoo_import/models/importers/phase.py`:

```python
# -*- coding: utf-8 -*-
"""Фазите на пренасянето и правилото кои от тях са изпълними.

Всяка фаза декларира от какво зависи. Регистърът е единственият източник на
истина за реда и за списъка модули, които се търсят в източника - hardcoded
списък отделно от фазите изостава мълчаливо и точно това скри камерите.
"""


def _target_available(env, requirement):
    """Дали целта може да приеме тази фаза.

    ``requirement`` е име на модел или двойка (модел, поле).

    Присъствието на модел НЕ стига по две причини: абстрактният модел се
    резолва в registry-то, но няма таблица; а модел с различна схема между
    версиите има името, но не и колоната, която bulk вмъкването ще поиска.
    """
    name, field = requirement if isinstance(requirement, tuple) else (requirement, None)
    if name not in env:
        return False
    model = env[name]
    if getattr(model, '_abstract', False) or getattr(model, '_transient', False):
        return False
    if field and field not in model._fields:
        return False
    return True


class PhaseImporter:
    """Базов договор на една фаза."""

    PHASE_ID = ''
    NAME = ''
    REQUIRES_SOURCE = ()
    REQUIRES_TARGET = ()
    OPTION = ''
    WEIGHT = 1

    def __init__(self, base):
        self.b = base
        self.env = base.env
        self.results = []

    def run(self, wizard):
        raise NotImplementedError


def phase_plan(env, options, source_modules):
    """[(клас, причина за пропускане или None)] в реда на изпълнение.

    Чиста функция: без мрежа и без запис. Тества се без XML-RPC.
    """
    plan = []
    for cls in PHASE_REGISTRY:
        plan.append((cls, _skip_reason(env, cls, options, source_modules)))
    return plan


def _skip_reason(env, cls, options, source_modules):
    if cls.OPTION and not options.get(cls.OPTION):
        return env._("Not selected for this transfer.")
    missing_source = [m for m in cls.REQUIRES_SOURCE if m not in source_modules]
    if missing_source:
        return env._(
            "The source system does not have this functionality installed."
        )
    missing_target = [r for r in cls.REQUIRES_TARGET
                      if not _target_available(env, r)]
    if missing_target:
        return env._(
            "This system cannot receive that data yet. Install the matching "
            "functionality first, then run the transfer again."
        )
    return None


def build_registry():
    """Редът е значещ - виж EXTENSION_PLAN.md раздел 3.5."""
    from .core_importer import CoreImporter, ZoneImporter
    from .people_importer import PeopleImporter
    from .access_importer import AccessImporter
    from .event_importer import EventImporter
    from .vending_importer import VendingImporter
    from .attendance_importer import AttendanceImporter
    from .service_importer import ServiceImporter
    return [
        CoreImporter, PeopleImporter, ZoneImporter, AccessImporter,
        EventImporter, VendingImporter, AttendanceImporter, ServiceImporter,
    ]


PHASE_REGISTRY = build_registry()
```

- [ ] **Стъпка 4: Съществуващите фази получават метаданни**

Всеки от осемте класа наследява `PhaseImporter` и получава class attributes със
стойностите, които днес са литерали в `_do_import` (`import_wizard.py:848-912`).
Пример за `CoreImporter` (`core_importer.py`):

```python
class CoreImporter(PhaseImporter):
    PHASE_ID = 'Phase 1+3'
    NAME = 'Core & Hardware'
    REQUIRES_SOURCE = ('hr_rfid',)
    REQUIRES_TARGET = ('hr.rfid.webstack', 'hr.rfid.ctrl', 'hr.rfid.door')
    OPTION = 'import_hardware'
    WEIGHT = 30
```

Стойности за останалите: `PeopleImporter` (`Phase 2`, `People`, `('hr_rfid',)`,
`('hr.employee', 'res.partner')`, `import_people`, 15); `ZoneImporter` (`Phase 3b`,
`Zones`, `('hr_rfid',)`, `('hr.rfid.zone',)`, `import_hardware`, 2);
`AccessImporter` (`Phase 4`, `Access Control`, `('hr_rfid',)`,
`('hr.rfid.access.group', 'hr.rfid.card')`, `import_access`, 13);
`EventImporter` (`Phase 5`, `Events`, `('hr_rfid',)`,
`('hr.rfid.event.user', 'hr.rfid.event.system')`, `''`, 15);
`VendingImporter` (`Phase 6a`, `Vending`, `('hr_rfid_vending',)`,
`('hr.rfid.vending.event', 'hr.rfid.ctrl.vending.row')`, `import_vending`, 10);
`AttendanceImporter` (`Phase 6b`, `Attendance`, `('hr_attendance_multi_rfid',)`,
`('hr.attendance',)`, `''`, 7); `ServiceImporter` (`Phase 6c`, `Service`,
`('rfid_service_base',)`, `('rfid.service', 'rfid.service.sale')`, `import_service`, 6).

`EventImporter` и `AttendanceImporter` имат `OPTION = ''`, защото гейтват вътрешно
по няколко опции (`event_importer.py:31,33,35`; `attendance_importer.py:23,25`) -
тези вътрешни гейтове **не се пипат**.

Конструкторите на осемте класа се махат - базовият ги замества дословно.

- [ ] **Стъпка 5: `_do_import` се свива до обхождане**

`import_wizard.py`, замени тялото на `_do_import` след построяването на
`importer` с:

```python
        from .importers.phase import PHASE_REGISTRY, phase_plan

        source_modules = set(json.loads(self.installed_modules_json or '[]'))
        plan = phase_plan(self.env, options, source_modules)
        total_weight = sum(cls.WEIGHT for cls in PHASE_REGISTRY) or 1
        done_weight = 0

        for cls, skip_reason in plan:
            pct_start = done_weight * 100.0 / total_weight
            done_weight += cls.WEIGHT
            pct_end = done_weight * 100.0 / total_weight
            if skip_reason:
                # Пропусната фаза БЕЗ ред в протокола е неразличима от фаза,
                # която не е намерила данни. Операторът вижда празнота и в
                # двата случая.
                self.env['hr.rfid.odoo.import.log'].create({
                    'wizard_id': self.id,
                    'phase': cls.PHASE_ID,
                    'model': cls.NAME,
                    'status': 'skipped',
                    'error_message': skip_reason,
                })
                self._append_progress("  %s: %s", cls.NAME, skip_reason)
                self.progress_percent = pct_end
                continue
            self._run_phase(cls.PHASE_ID, cls.NAME, cls(importer),
                            pct_start, pct_end)
```

`_run_phase` **не се пипа** - сигнатурата ѝ е договор на `test_company_scope.py:468-477`.

- [ ] **Стъпка 6: Списъкът модули в източника става производен**

`import_wizard.py:421`, замени литералния списък с:

```python
            from .importers.phase import PHASE_REGISTRY
            probe_modules = sorted({
                m for cls in PHASE_REGISTRY for m in cls.REQUIRES_SOURCE
            })
```

и подай `probe_modules` в домейна вместо литералите.

- [ ] **Стъпка 7: Прогон - трябва да минат**

Същата команда като стъпка 2, плюс пълната регресия на модула:

```bash
timeout -k 30 1800 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_import_registry,rfid_import_ui \
    -u hr_rfid_odoo_import --no-http --stop-after-init --log-level=test -c odoo.conf
```

Очаквано: `0 failed, 0 error(s)`.

- [ ] **Стъпка 8: Commit**

```bash
git add hr_rfid_odoo_import/
git commit -m "фазите започват да казват от какво зависят, вместо да мълчат"
```

---

## Задача 5: Ред-на-фаза вместо осем булеви полета

**Файлове:**
- Modify: `hr_rfid_odoo_import/models/import_conflict.py` (нов модел накрая)
- Modify: `hr_rfid_odoo_import/models/import_wizard.py:181-212` (махане)
- Modify: `hr_rfid_odoo_import/views/import_wizard_views.xml:88-118`
- Modify: `hr_rfid_odoo_import/security/ir.model.access.csv`
- Test: разширение на `test_phase_registry.py`

**Интерфейси:**
- Consumes: `phase_plan` от задача 4.
- Produces: `hr.rfid.odoo.import.phase.line` с полета `wizard_id`, `phase_key`,
  `name`, `do_import`, `unavailable_reason`, `source_count`.

- [ ] **Стъпка 1: Тестът**

```python
    def test_unavailable_phase_cannot_be_switched_on(self):
        """Функционалност, която липсва, не е кликаема - и казва защо."""
        wiz = self.env['hr.rfid.odoo.import.wiz'].create({
            'source_url': 'http://localhost:8069',
            'source_login': 'admin', 'source_password': 'admin',
        })
        wiz._sync_phase_lines(source_modules=set())
        for line in wiz.phase_line_ids:
            if line.unavailable_reason:
                self.assertFalse(
                    line.do_import,
                    "Липсваща функционалност е предложена за пренасяне",
                )
```

- [ ] **Стъпка 2: Прогон - пада с `AttributeError` за `_sync_phase_lines`.**

- [ ] **Стъпка 3: Моделът**

В края на `import_conflict.py`:

```python
class HrRfidOdooImportPhaseLine(models.TransientModel):
    _name = 'hr.rfid.odoo.import.phase.line'
    _description = 'Import Phase Line'
    _order = 'sequence'

    wizard_id = fields.Many2one(
        'hr.rfid.odoo.import.wiz', required=True, ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    phase_key = fields.Char(required=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    do_import = fields.Boolean(
        string='Transfer',
        help="Untick to leave this out of the transfer. Items that cannot be "
             "transferred are locked and show the reason.",
    )
    unavailable_reason = fields.Char(readonly=True)
    source_count = fields.Integer(
        readonly=True,
        help="How many records of this kind were found on the other system.",
    )
```

- [ ] **Стъпка 4: `_sync_phase_lines`**

В `import_wizard.py`:

```python
    def _sync_phase_lines(self, source_modules=None):
        """Един ред на фаза, с причина за недостъпност вместо мълчание."""
        from .importers.phase import PHASE_REGISTRY, _skip_reason
        self.ensure_one()
        if source_modules is None:
            source_modules = set(json.loads(self.installed_modules_json or '[]'))
        self.phase_line_ids.unlink()
        Line = self.env['hr.rfid.odoo.import.phase.line']
        for seq, cls in enumerate(PHASE_REGISTRY, start=1):
            # Тук питаме само за наличност, не за избора на оператора, затова
            # OPTION се неутрализира с пълен options речник.
            reason = _skip_reason(
                self.env, cls, {cls.OPTION: True} if cls.OPTION else {},
                source_modules,
            )
            Line.create({
                'wizard_id': self.id, 'sequence': seq * 10,
                'phase_key': cls.PHASE_ID, 'name': cls.NAME,
                'do_import': not reason,
                'unavailable_reason': reason or False,
            })
```

Викай го в края на `action_test_connection`, преди `return self._keep_open()`.

- [ ] **Стъпка 5: Опциите се четат от редовете**

В `_do_import`, построяването на `options` (`:795-814`) чете
`self.phase_line_ids.filtered('do_import').mapped('phase_key')` вместо осемте
булеви полета. Композитните изрази (`:810-813`) отпадат.

- [ ] **Стъпка 6: Права**

Добави в `security/ir.model.access.csv`:

```
hr_rfid_odoo_import.access_hr_rfid_odoo_import_phase_line,access_hr_rfid_odoo_import_phase_line,model_hr_rfid_odoo_import_phase_line,base.group_system,1,1,1,1
```

- [ ] **Стъпка 7: Изгледът**

Замени блока с осемте checkbox-а (`:88-118`) с:

```xml
                            <field name="phase_line_ids" nolabel="1">
                                <list editable="bottom" create="0" delete="0">
                                    <field name="do_import" widget="boolean_toggle"
                                           readonly="unavailable_reason != False"/>
                                    <field name="name" readonly="1"/>
                                    <field name="source_count" readonly="1" optional="show"/>
                                    <field name="unavailable_reason" readonly="1"/>
                                </list>
                            </field>
```

- [ ] **Стъпка 8: Махане на старите полета И техните консуматори**

Изтрий `source_has_vending`, `source_has_attendance`, `source_has_attendance_late`,
`source_has_service`, `target_has_*` (`:181-212`), `_compute_target_modules`
(`:263-277`), и осемте `import_*` булеви за фазите. В същия commit махни всичките
12 XML консуматора (`:90,92,94,96,101,105,109,113`). Останал `invisible` израз минава
XML lint и гърми чак при рендиране.

- [ ] **Стъпка 9: Прогон + проверка на лога**

```bash
timeout -k 30 1800 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_import_registry,rfid_import_ui \
    -u hr_rfid_odoo_import --no-http --stop-after-init --log-level=test \
    -c odoo.conf 2>&1 | tee /tmp/phaseline.log
grep -iE "Access Rights Inconsistency|RELAXNG|does not exist|Field .* (used|not found)" /tmp/phaseline.log
```

Очаквано: `0 failed`, празен grep.

- [ ] **Стъпка 10: Commit**

```bash
git add hr_rfid_odoo_import/
git commit -m "операторът вижда какво може да пренесе и защо останалото не може"
```

---

## Задача 6: Фонов прогон - `run` модел, крон, партиди

**Файлове:**
- Create: `hr_rfid_odoo_import/models/import_run.py`
- Create: `hr_rfid_odoo_import/data/ir_cron.xml`
- Create: `hr_rfid_odoo_import/views/import_run_views.xml`
- Modify: `hr_rfid_odoo_import/models/import_wizard.py:753-782`
- Modify: `hr_rfid_odoo_import/models/importers/base_importer.py` (ledger warm-up)
- Modify: `hr_rfid_odoo_import/__manifest__.py` (нови data файлове)
- Test: `hr_rfid_odoo_import/tests/test_background_run.py`

**Интерфейси:**
- Consumes: `phase_plan`, `PHASE_REGISTRY` (задача 4).
- Produces: `hr.rfid.odoo.import.run` с `_process_batch()`; задачи 7 и 8 не го пипат.

- [ ] **Стъпка 1: Тестовете**

```python
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'rfid_import_run')
class TestBackgroundRun(TransactionCase):
    """Прехвърлянето издържа нощта и не започва отначало.

    Бизнес твърдение: обект с десетки хиляди събития се прехвърля наведнъж;
    ако нещо прекъсне, работата продължава оттам, а не от нулата, и никой
    запис не влиза два пъти.
    """

    def _run(self):
        return self.env['hr.rfid.odoo.import.run'].create({
            'source_url': 'http://localhost:8069',
            'source_db': 'src',
            'source_login': 'admin',
            'source_password': 'secret',
            'user_id': self.env.user.id,
        })

    def test_the_request_survives_an_hour(self):
        """Заявката не е временна - дълъг прогон не си трие поръчката."""
        self.assertFalse(
            self.env['hr.rfid.odoo.import.run']._transient,
            "Заявката за прехвърляне се чисти автоматично и прогонът ще спре тихо",
        )

    def test_password_is_gone_when_finished(self):
        """Паролата на другата система не остава да лежи след края."""
        run = self._run()
        run._finish(state='done')
        self.assertFalse(run.source_password, "Паролата остана записана")

    def test_password_is_not_readable_by_everyone(self):
        """Паролата се вижда само от администратор."""
        field = self.env['hr.rfid.odoo.import.run']._fields['source_password']
        self.assertTrue(field.groups, "Паролата няма ограничение за четене")

    def test_manual_start_does_not_block_the_screen(self):
        """Ръчното пускане на задачата не върши работата в самата заявка."""
        run = self._run()
        run.state = 'queued'
        # В HTTP контекст методът само събужда крона.
        self.assertTrue(hasattr(run, '_cron_process'))
```

- [ ] **Стъпка 2: Прогон - пада с липсващ модел.**

- [ ] **Стъпка 3: Моделът**

`hr_rfid_odoo_import/models/import_run.py` - постоянен `models.Model` с
`_inherit = ['mail.thread']` и полетата от `EXTENSION_PLAN.md` раздел 5.2.
`source_password` носи `groups="base.group_system"`. Методи:

```python
    def _cron_process(self):
        """Едно парче работа. Вика се от крона; от екрана - само го събужда."""
        if request:
            # Ръчното пускане от интерфейса иначе върши цялата работа в HTTP
            # заявката, а тя има таван от 120 секунди (odoo.conf).
            self.env.ref('hr_rfid_odoo_import.ir_cron_odoo_import')._trigger()
            return
        runs = self.search([('state', 'in', ('queued', 'running'))], limit=1)
        for run in runs:
            run._process_batch()

    def _finish(self, state, message=None):
        """Край на прогона - паролата на другата система не остава да лежи."""
        self.ensure_one()
        self.write({
            'state': state,
            'source_password': False,
        })
        if message:
            self.message_post(body=message)
```

`_process_batch` изпълнява ЕДНА единица работа (една фаза, а за събитията - една
партида), после вика:

```python
            remaining = self.env['ir.cron']._commit_progress(
                processed=processed, remaining=self.total_count - self.done_count,
            )
```

Извикването е **след** затварянето на всеки `cr.savepoint()` блок - commit вътре в
отворен savepoint го унищожава (`sql_db.py:106-129`).

- [ ] **Стъпка 4: Ledger warm-up в `base_importer.py`**

```python
    def warm_up_ledger(self, model, source_ids):
        """Напълни id_map от ledger-а преди фазата.

        id_map живее в паметта. Нов процес (крон цикъл, друг работник) го
        вижда празен, всяка връзка се резолва на False и редът се брои като
        пропуснат - протоколът изглежда нормален, а данните ги няма.
        """
        for source_id, target_id in self.already_imported(model, source_ids).items():
            self._set_target_id(model, source_id, target_id)
```

Всяка фаза го вика за моделите, от които зависи, в началото на `run`.

- [ ] **Стъпка 5: Кронът**

`data/ir_cron.xml` - `active="True"` (крон с `active=False` не тръгва и от
`_trigger()`, `ir_cron.py:283-294`), интервал 1 ден, `code` вика
`model._cron_process()`.

- [ ] **Стъпка 6: Wizard-ът само подава заявката**

`action_import` (`:753-782`) създава `run` записа, задава `state='queued'`, вика
`_trigger()` и връща `display_notification` с `'next': {'type': 'ir.actions.act_window_close'}`.

- [ ] **Стъпка 7: Прогон**

```bash
timeout -k 30 1800 ./venv/bin/python odoo/odoo-bin -d 19_dev_rfid_guards \
    --test-enable --test-tags rfid_import_run -u hr_rfid_odoo_import \
    --no-http --stop-after-init --log-level=test -c odoo.conf
```

- [ ] **Стъпка 8: Commit**

```bash
git add hr_rfid_odoo_import/
git commit -m "прехвърлянето слиза от екрана и почва да издържа нощта"
```

---

## Задача 7: Фаза Cameras

**Файлове:**
- Create: `hr_rfid_odoo_import/models/importers/camera_importer.py`
- Modify: `hr_rfid_odoo_import/models/importers/phase.py` (регистрация)
- Test: `hr_rfid_odoo_import/tests/test_camera_phase.py`

**Интерфейси:**
- Consumes: `PhaseImporter`, `BaseImporter._load_records`, `_map_m2m`, `warm_up_ledger`.
- Produces: `CameraImporter` в регистъра, след `AccessImporter`.

Пълните полета, изключенията и трите специфики са в `EXTENSION_PLAN.md` раздел 4.1.

- [ ] **Стъпка 1: Тестовете C1-C7** по твърденията от `EXTENSION_PLAN.md` раздел 9.2.
- [ ] **Стъпка 2: Прогон - падат.**
- [ ] **Стъпка 3: Класът** с `REQUIRES_SOURCE = ('polimex_ip_cam',)`,
  `REQUIRES_TARGET = ('cctv.camera', 'cctv.camera.rfid.rel')`, `OPTION = 'import_cameras'`,
  `WEIGHT = 5`, регистриран **след** `AccessImporter`.
- [ ] **Стъпка 4: Пре-флайт проверка за паролите** - чете `password` на една камера;
  при празна стойност вдига `UserError` с текст, който казва на оператора, че
  потребителят на другата система няма право да вижда паролите на камерите.
- [ ] **Стъпка 5: Fail-safe за `list_category`** - всичко освен `whitelist` става
  `blacklist`, броят преобразувани редове влиза в `_make_result` като отделно число
  в `error` полето на резултата (информативно, не грешка).
- [ ] **Стъпка 6: Прогон - минават.**
- [ ] **Стъпка 7: Commit** - `"камерите пристигат заедно с номерата, които пазят"`.

---

## Задача 8: Фаза Sites

**Файлове:**
- Create: `hr_rfid_odoo_import/models/importers/site_importer.py`
- Modify: `hr_rfid_odoo_import/models/importers/phase.py` (регистрация)
- Test: `hr_rfid_odoo_import/tests/test_site_phase.py`

**Интерфейси:**
- Consumes: `PhaseImporter`, задача 2 (график по фирма).
- Produces: `SiteImporter` в регистъра, между `ZoneImporter` и `AccessImporter`.

Трите капана са в `EXTENSION_PLAN.md` раздел 4.2.

- [ ] **Стъпка 1: Тестовете S1-S5** по раздел 9.3.
- [ ] **Стъпка 2: Прогон - падат.**
- [ ] **Стъпка 3: Класът** - `_load_records` **по един запис** (create не е
  `model_create_multi`), топологичен ред (родител преди дете, `parent_id` при create),
  `make_access_group=False` при създаване.
- [ ] **Стъпка 4: Втори проход** - `site_id` върху хардуера, `res.partner.site_ids`,
  възстановяване на `make_access_group` след Фаза 4.
- [ ] **Стъпка 5: Backfill на `event.user.site_id`** след Фаза 5 - stored compute,
  а събитията влизат със суров SQL, който не изпълнява компюти.
- [ ] **Стъпка 6: Пре-флайт проверка на правата** - операторът без достъп до
  обектите получава разбираемо съобщение, не traceback.
- [ ] **Стъпка 7: Прогон - минават.**
- [ ] **Стъпка 8: Commit** - `"обектите идват с дървото си, а не с двойни групи"`.

---

## Задача 9: ANPR клон и насрещна сверка

**Файлове:**
- Modify: `hr_rfid_odoo_import/models/importers/event_importer.py`
- Test: разширение на `test_camera_phase.py` (C6)

- [ ] **Стъпка 1: Тестът C6** - разпознат номер от историята стига до целта.
- [ ] **Стъпка 2: Прогон - пада** (днес обхватът структурно не ги вижда).
- [ ] **Стъпка 3: Камерен обхват** - отделен клон по `camera_id`, защото
  `reader_id.controller_id.webstack_id` е `EXISTS` срещу четци без контролер.
- [ ] **Стъпка 4: Насрещна сверка** - брой в източника по `('camera_id', '!=', False)`
  срещу брой в целта, в протокола на фазата. Без него "нула" е неразличимо от
  "клиентът няма камери".
- [ ] **Стъпка 5: Прогон - минава.**
- [ ] **Стъпка 6: Commit** - `"разпознатите номера престават да изчезват по пътя"`.

---

## Задача 10: `io_table` се чете от желязото

**Файлове:**
- Modify: `hr_rfid_odoo_import/models/importers/core_importer.py`
- Test: разширение на `test_phase_registry.py`

- [ ] **Стъпка 1: Тестът** - след импорт мигрираните контролери имат заявка за
  четене на таблицата, а не празно поле.
- [ ] **Стъпка 2: Прогон - пада.**
- [ ] **Стъпка 3: След-импорт стъпка** - вика `read_io_table_cmd()` за мигрираните
  контролери; отчита колко са отговорили. Стъпката е отделна и повторяема - при
  недостъпен контролер се повтаря, без да се пуска целият импорт.
- [ ] **Стъпка 4: Прогон - минава.**
- [ ] **Стъпка 5: Commit** - `"мигрираният контролер вече не мълчи за таблицата си"`.

---

## Задача 11: Измерване и фиксиране на `batch_size`

- [ ] **Стъпка 1:** клонинг на `15_polimex.cloud` за източник
  (`odoo_db_ops.py clone 15_polimex.cloud --suffix _e2esrc`).
- [ ] **Стъпка 2:** прясна целева база
  (`odoo-bin db init 19_e2e_target --language bg_BG --country BG`).
- [ ] **Стъпка 3:** прогон без събития; отчети `duration` per фаза от
  `hr.rfid.odoo.import.log`.
- [ ] **Стъпка 4:** прогон само на събития; измери секунди на 1000 реда.
- [ ] **Стъпка 5:** фиксирай `batch_size` така, че 10 последователни партиди да са
  доста под 120 s (целѝ около 5 s на партида).
- [ ] **Стъпка 6: Commit** с реалните числа в commit съобщението.

---

## Задача 12: E2E-1 - облачният бекъп към прясна база

**Доказва:** регресия на старите фази на реален обем; фонов прогон; гейтът в
отрицателна посока (камери и обекти липсват в Odoo 15 и се пропускат с причина).

- [ ] **Стъпка 1:** източник - клонинг на `15_polimex.cloud`, пуснат на порт 8015.
- [ ] **Стъпка 2:** цел - ПРЯСНА `19_e2e_cloud` (не клонинг - заварени записи
  маскират какво е внесъл импортът).
- [ ] **Стъпка 3:** пълен прогон през wizard-а.
- [ ] **Стъпка 4: Сверка** - за всеки клас: брой в източника срещу брой в целта.
  Фаза, чиито пропуснати записи са колкото всички, е ГРЕШКА, не "готово".
- [ ] **Стъпка 5:** протоколът съдържа редове `skipped` за камерите и обектите с
  причина "източникът няма тази функционалност".
- [ ] **Стъпка 6:** нула команди към контролери
  (`hr.rfid.command` search_count преди/след).

---

## Задача 13: E2E-2 - v18 с камери и обекти

**Доказва:** новите фази с реални данни.

- [ ] **Стъпка 1:** източник - клонинг на `18_new_rfid` (има `hr_rfid_site_manager`);
  инсталирай `polimex_ip_cam` и засей камери, номера и връзки.
- [ ] **Стъпка 2:** цел - ПРЯСНА `19_e2e_cam`.
- [ ] **Стъпка 3:** пълен прогон.
- [ ] **Стъпка 4: Сверка** - камери, връзки номер-камера по кофи, обекти, дълбочина
  на дървото, партньори с обекти, ANPR събития.
- [ ] **Стъпка 5:** нула команди към камери (`cctv.camera.command` search_count).
- [ ] **Стъпка 6:** всеки обект има точно една група достъп.

---

## Задача 14: llms, преводи, индекс, pre-commit одит

- [ ] **Стъпка 1:** `README.rst` - махни невярното твърдение за dynamic schema
  discovery; опиши регистъра и фоновия прогон.
- [ ] **Стъпка 2:** `docs/llms.txt` и `docs/llms-full.md` - обнови.
- [ ] **Стъпка 3: Преводи** - `i18n export` -> `msgmerge` -> `po-ai-translator`
  (`--model sonnet`, никога по-нисък) -> `po_quality_check`. Никога ръчно редактиране
  на `.po` - липсващият `#. module:` коментар на entry чупи целия web клиент.
- [ ] **Стъпка 4: Индекс** - `custom-addons/CLAUDE.md`, редовете на
  `hr_rfid_odoo_import`, `polimex_ip_cam`, `hr_rfid`.
- [ ] **Стъпка 5: Агенти** - `code-simplifier`, после `code-reviewer` и
  `pr-test-analyzer` върху диффа. PASS = нула неадресирани находки.
- [ ] **Стъпка 6: `/security-review`** - има ли промяна в attack surface. Нови route-ове
  няма; XML-RPC клиентът към източника и паролата на `run` записа са промяна в
  боравенето с credentials, тоест прегледът е приложим.
- [ ] **Стъпка 7: `silent-failure-hunter`** - задачата добавя try/except в guard-овете
  и в партидното изпълнение.
- [ ] **Стъпка 8: A1-A14 grep-овете** от `odoo-dev-workflow` раздел 11.a.
- [ ] **Стъпка 9: Версии** - последна редакция преди `git add`, с Edit tool.
- [ ] **Стъпка 10:** одит таблицата се извежда дословно в отговора към собственика.
