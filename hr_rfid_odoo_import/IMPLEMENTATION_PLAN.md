# Implementation Plan: hr_rfid_odoo_import

## Обзор

Модул за импорт на RFID данни от стари Odoo инстанции (14, 15, 16, 17, 18) в Odoo 19.
Следва конвенцията на `hr_rfid_andromeda_import` и `hr_rfid_old_cloud_import`.

**Име:** `hr_rfid_odoo_import`
**Версия:** 19.0.1.0.0
**Зависимости:** `hr_rfid`
**Лиценз:** AGPL-3

---

## 1. Метод на връзка: XML-RPC API

### Защо API, а не psycopg2

| Критерий | psycopg2 (отхвърлен) | XML-RPC (избран) |
|----------|---------------------|------------------|
| Портативност | Само локален PostgreSQL | Всяка Odoo инстанция (локална/отдалечена) |
| Schema абстракция | Ръчно четене на DB schema | `fields_get()` с метаданни |
| ORM валидация | Суров SQL, без валидация | Source Odoo разбира computed fields |
| Бъдещо-устойчив | Обвързан с DB engine | Работи за всяка Odoo версия |
| Сигурност | Директен DB достъп | HTTP с автентикация |
| Computed fields | Не се виждат | Достъпни чрез API |
| Binary fields | base64 encode ръчно | Автоматично base64 |

### XML-RPC Connection Pattern

```python
import xmlrpc.client

# Connection parameters
url = 'http://localhost:8015'   # Source Odoo URL
db = '15_dev_cloud'             # Source database name
login = 'admin'                 # Source username
password = 'admin'              # Source password

# Step 1: Authenticate
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, login, password, {})
# Returns: user_id (int) or False

# Step 2: Execute API calls
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# search_read — основна операция за четене
records = models.execute_kw(db, uid, password,
    'hr.rfid.webstack', 'search_read',
    [[('company_id', '=', 1)]],                          # domain
    {'fields': ['name', 'serial', 'key'], 'limit': 100}  # kwargs
)

# fields_get — за schema discovery
fields = models.execute_kw(db, uid, password,
    'hr.rfid.card', 'fields_get',
    [],
    {'attributes': ['string', 'type', 'required', 'readonly', 'relation']}
)
# Returns: {'number': {'string': 'Number', 'type': 'char', ...}, ...}
```

### Version Detection чрез API

```python
base_mod = models.execute_kw(db, uid, password,
    'ir.module.module', 'search_read',
    [[('name', '=', 'base'), ('state', '=', 'installed')]],
    {'fields': ['latest_version'], 'limit': 1}
)
version = base_mod[0]['latest_version']  # '14.0.1.3' → major = 14
```

### Schema Discovery чрез fields_get()

Вместо `_has_column(table, column)` (psycopg2), използваме:

```python
def _has_field(self, model, field_name):
    """Check if field exists in source model via API."""
    if model not in self._field_cache:
        self._field_cache[model] = self.rpc_models.execute_kw(
            self.db, self.uid, self.password,
            model, 'fields_get', [],
            {'attributes': ['type']}
        )
    return field_name in self._field_cache[model]
```

**Предимство:** `fields_get()` връща ВСИЧКИ полета включително computed, related, inherited.

### XML-RPC Pagination за големи данни

```python
def _read_all(self, model, domain, fields, batch_size=1000):
    """ID-based pagination — reliable for large datasets."""
    all_records = []
    last_id = 0
    while True:
        batch_domain = [('id', '>', last_id)] + domain
        records = self.rpc_models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read',
            [batch_domain],
            {'fields': fields, 'limit': batch_size, 'order': 'id asc'}
        )
        if not records:
            break
        all_records.extend(records)
        last_id = records[-1]['id']
    return all_records
```

**Performance estimate (275K events):**
- 275 batches × ~200ms/call ≈ 55 секунди за четене
- Приемливо за еднократен импорт

### XML-RPC Deprecation Note

XML-RPC е deprecated в Odoo 19 (планирано за премахване в v20). JSON-2 API е новият стандарт.
Но за source инстанции v14-v18, XML-RPC е **единственият** наличен протокол.
За бъдещи source v19+, може да се добави JSON-2 support.

### Изисквания към Source Odoo

**Source Odoo инстанцията ТРЯБВА да работи** (HTTP server) по време на импорта.
- Локално: `./odoo-bin -c odoo.conf` (с правилния порт)
- Отдалечено: достъпен URL + credentials

---

## 2. Мулти-компания

Source базата може да има много компании. Потребителят избира кои да импортира.

**Mapping таблица:**

| Source ID | Source Name | Import? | Target Company |
|-----------|------------|---------|----------------|
| 1 | Полимекс Холдинг ЕООД | ✓ | [Избери/Нова] |
| 2 | Subsidiary A | ☐ | — |

**Филтриране по компания:**
- Директно: `hr_rfid_webstack.company_id`, `hr_rfid_card.company_id`, `hr_rfid_access_group.company_id`
- Чрез chain: `hr_rfid_door` → `controller_id` → `webstack_id` → `company_id`
  (v14/v15 нямат `company_id` на door — chain е задължителен)
- Чрез employee: `hr_attendance.employee_id` → `hr_employee.company_id`

**Реални бройки per company (15_dev_cloud, company 1 vs ALL):**

| Модел | Company 1 | ALL | Коефициент |
|-------|-----------|-----|------------|
| event_user | 7,568 | 275,471 | 2.7% |
| event_system | 5,225 | 375,107 | 1.4% |
| attendance | 997 | 133,500 | 0.7% |
| att_extra | 1,014 | 98,699 | 1.0% |
| vending_balance | 15,407 | 250,399 | 6.2% |
| vending_event | 2,089 | 34,976 | 6.0% |
| th_log | 170,669 | 170,669 | 100% |

**Извод:** Per-company обемите са значително по-малки. Най-голям е th_log (170K).

---

## 3. Card Activation Chain (Критично разбиране)

### Пълен chain при Card.create():

```
Card.create()                                             # hr_rfid_card.py:282
  └→ update_card_rels(card)                               # hr_rfid_door.py:771
      └→ card.get_potential_access_doors(access_group)     # hr_rfid_card.py:190
          └→ owner.hr_rfid_access_group_ids                # employee/partner rels
              └→ _filter_active()                          # [B] AG rel active check
                  └→ activate_on <= now AND expiration > now
          └→ access_groups.all_door_ids                    # [C] AG door rels
      └→ check_relevance_fast(card, door, ts)              # hr_rfid_door.py:832
          └→ _check_compat_n_rdy(card, door)               # hr_rfid_door.py:895
              ├→ card.door_compatible(door)                 # [D] card_type match
              └→ card.card_ready()                         # [E] active + dates
          └→ create_rel(card, door, ts)                    # hr_rfid_door.py:849
              └→ HrRfidCardDoorRel.create()                # hr_rfid_door.py:923
                  └→ _create_add_card_command()             # [F] hr_rfid_door.py:898
                      └→ hr.rfid.command.add_card()        # [G] HW COMMAND
```

### Точки за прекъсване (натурални):

| Точка | Условие за прекъсване | Ефект |
|-------|----------------------|-------|
| [B] | AG rel няма / не е active | Няма doors → chain спира |
| [C] | AG няма door rels | Празен списък → chain спира |
| [D] | card_type != door.card_type | Несъвместимост → спира |
| [E] | card.active=False / dates | card_ready()=False → спира |
| [F] | Винаги се вика | HW команда |

### Друг chain — AG Door Rel.create():

```
AGDoorRel.create()                                         # hr_rfid_access_group.py:499
  └→ update_door_rels(door, access_group)                  # [A1]
      └→ door.get_cards(access_group)
          └→ ... cards ... → check_relevance_fast → CardDoorRel.create → HW CMD
  └→ door.controller_id.write_ts_id(time_schedule)         # [A2] HW CMD директно
```

### Друг chain — AG Employee Rel.create():

```
AGEmployeeRel.create()                                     # hr_rfid_access_group.py:738
  └→ super().create()                                       # Записва в DB
  └→ records.mapped('employee_id').check_access_group()     # Проверка за дубликати
  └→ records.mapped('state')                                # Trigger _compute_state
      └→ _compute_state()                                   # hr_rfid_access_group.py:617
          └→ _active_state_change(new_state)                # :608
              └→ _activate()                                # :732
                  └→ cards = employee.hr_rfid_card_ids.filtered(card_ready)
                  └→ update_card_rels(card, access_group)   # → chain по-горе
```

### Друг chain — Employee.create():

```
Employee.create()                                          # hr_employee.py:262
  └→ rec.add_acc_gr(department.hr_rfid_default_access_group)  # :267
      └→ AGEmployeeRel.create()                                # → chain по-горе
```

---

## 4. Стратегия за избягване на HW команди

### Решение: Context flag `no_hardware_commands`

**5 минимални guard-а на крайните HW точки:**

#### Guard 1-2: `hr_rfid_door.py` — HrRfidCardDoorRel

```python
# hr_rfid_door.py line 898-905
def _create_add_card_command(self):
    if self.env.context.get('no_hardware_commands'):
        return
    # ... existing code: hr.rfid.command.add_card() ...

# hr_rfid_door.py line 907-916
def _create_remove_card_command(self, number=None, door_id=None):
    if self.env.context.get('no_hardware_commands'):
        return
    # ... existing code: hr.rfid.command.remove_card() ...
```

#### Guard 3-4: `hr_rfid_ctrl.py` — HrRfidCtrl

```python
# hr_rfid_ctrl.py line 1276-1280
def write_ts_id(self, ts):
    if self.env.context.get('no_hardware_commands'):
        return
    # ... existing code: _base_command() → D3 ...

# hr_rfid_ctrl.py line 1282-1290
def delete_ts_id(self, ts):
    if self.env.context.get('no_hardware_commands'):
        return
    # ... existing code: _base_command() → D3 ...
```

#### Guard 5: `hr_employee.py` — auto add_acc_gr skip

```python
# hr_employee.py line 262-269
@api.model_create_multi
def create(self, vals_list):
    records = super(HrEmployee, self).create(vals_list)
    if not self.env.context.get('no_hardware_commands'):
        for rec in records:
            rec.add_acc_gr(rec.department_id.hr_rfid_default_access_group)
    return records
```

### Какво остава да работи нормално:

- ✅ `card_ready()` — проверява exact active state от source
- ✅ `_compute_state()` — изчислява correct AG rel state
- ✅ `check_relevance_fast()` — създава card-door rels (ORM)
- ✅ `door_compatible()` — проверява card_type compatibility
- ✅ Constraints — валидация на данните
- ✅ Computed fields — name, internal_number, state
- ✅ `ir.model.data` — нативен dedup

### Какво се потиска:

- ❌ `hr.rfid.command.add_card()` — D1 команда (line 553-576)
- ❌ `hr.rfid.command.remove_card()` — D1 команда (line 603-622)
- ❌ `ctrl.write_ts_id()` — D3 команда за time schedule (line 1276)
- ❌ `ctrl.delete_ts_id()` — D3 команда за time schedule (line 1282)
- ❌ `employee.add_acc_gr()` — auto default AG assignment (line 267)

### Card-door rels: Регенериране (НЕ импорт)

**Решение: Регенериране.** Card-door rels са derivative data.
Те произлизат от: cards + AG employee rels + AG door rels.
Chain-ът автоматично ги пресъздава при import на cards (step 21).

**Защо не импортираме:**
- Card-door rels може да са inconsistent в source (стар бъг, ръчна промяна)
- Регенерирането гарантира консистентност спрямо текущите AG rels/doors
- ORM chain-ът валидира card_type compatibility и card_ready() състояние

---

## 5. Ред на импорт (Dependency Graph)

### Phase 1: Фундамент (без зависимости)
```
1. hr.rfid.card.type         — match by card_type field, create if missing
2. hr.employee.category       — match by name, create if missing (за zone M2M)
3. hr.department              — filtered by company, TWO PASSES:
                                Pass 1: create all без parent_id
                                Pass 2: update parent_id с mapped IDs
4. hr.rfid.workcode           — filtered by company
5. hr.rfid.time.schedule      — match by number + company, create if missing
```

### Phase 2: Хора (зависи от Phase 1)

**Dependency chain (Odoo 19 auto-creation):**
```
res.users.create()      → AUTO: res.partner (via _inherits)
hr.employee.create()    → AUTO: resource.resource (via resource.mixin)
                        → AUTO: hr.version (via _inherits, НОВО в v19!)
                        → AUTO: res.partner (work_contact)
```

**НЕ импортираме отделно:** `resource.resource`, `hr.version` — auto-created.
**address_home_id НЕ СЪЩЕСТВУВА в v19!** Заменено с flat полета на hr.version.

```
5.  res.partner               — FIRST. Scope зависи от потребителски избор:
                                Option A: Само partners с RFID карти (default)
                                Option B: Всички partners от компанията
                                ★ Контактите трябва да съществуват ПРЕДИ users/employees

6.  res.users                 — (OPTIONAL, ако "Create users" е включено)
                                Match by login → link. Иначе:
                                create с partner_id → existing imported partner
                                (prevents auto-create на duplicate partner)
                                Temp password + force_reset_password=True
                                Groups mapping по xml_id (ако "Transfer groups")

7.  hr.employee               — scope зависи от потребителски избор:
                                Option A: Само employees с RFID карти (default)
                                Option B: Всички employees от компанията
                                user_id → matched/created user
                                resource.resource → auto-created (не импортираме)
                                hr.version → auto-created (не импортираме)
                                work_contact_id = user.partner_id (ако user_id)
                                (no_hardware_commands → skip add_acc_gr)
```

**Забележка за Employee.create():**
- Guard 5 предотвратява `add_acc_gr(department.hr_rfid_default_access_group)`
- AG employee rels ще бъдат импортирани точно от source в Phase 4

**Забележка за res.users.create():**
- Подаваме `partner_id=imported_partner_id` за да НЕ auto-create-ва нов partner
- Подаваме `create_employee=False` (default) за да НЕ auto-create-ва employee
- Context: `no_reset_password=True` за да не праща email веднага

### Phase 3: Хардуер (независимо от Phase 2)

**Dependency chain:**
```
emergency_group ← ctrl ← door ← reader, alarm, th
alarm_group (self-ref) ← alarm ← (ctrl + door)
zone ← (doors + departments + employees + partners)
```

```
8.  hr.rfid.ctrl.alarm.group      — TWO PASSES (parent_id self-ref):
                                     Pass 1: create all без parent_id
                                     Pass 2: update parent_id
9.  hr.rfid.ctrl.emergency.group  — company-level (NO deps except company)
10. hr.rfid.webstack              — filtered by company
11. hr.rfid.ctrl                  — filtered by webstack
                                    emergency_group_id → step 9 (вече съществува)
12. hr.rfid.door                  — filtered by ctrl→ws→company chain
13. hr.rfid.reader                — filtered by ctrl + reader_door_rel M2M
14. hr.rfid.ctrl.input.mask       — per controller
15. hr.rfid.ctrl.output.ts        — per controller, depends on time.schedule (step 4)
16. hr.rfid.ctrl.alarm            — depends on ctrl (11) + door (12) + alarm_group (8)
17. hr.rfid.ctrl.th               — depends on ctrl (11) + door (12)
18. hr.rfid.zone                  — M2M: door_ids, permitted_department_ids,
                                     permitted_employee_category_ids,
                                     employee_ids, contact_ids
19. hr.rfid.notification          — depends on zone (18) + notify_partner_ids M2M
```

### Phase 4: Access Control (зависи от Phase 1-3)

**Оптимален ред — chain работи естествено:**

```
20. hr.rfid.access.group                — TWO PASSES:
                                          Pass 1: create all без inherited_ids M2M
                                          Pass 2: update inherited_ids + department_ids M2M
21. hr.rfid.access.group.door.rel       — AG↔Door relations
    → update_door_rels() се вика → но НЯМА AG employee rels все още
    → door.get_cards(AG) → празно → chain спира
    → write_ts_id() → ПОТИСКА СЕ от no_hardware_commands

22. hr.rfid.access.group.employee.rel   — exact copy от source
    → _compute_state() → _activate() → update_card_rels()
    → Но: employees все още НЯМАТ карти → chain спира на _activate

23. hr.rfid.access.group.contact.rel    — exact copy от source
    → Същата логика — contacts нямат карти → chain спира

24. hr.rfid.card                         — RFID cards (с EXACT active state!)
    → update_card_rels() → owner.hr_rfid_access_group_ids → вече има от step 22/23
    → _filter_active() → AG door rels вече има от step 21
    → check_relevance_fast() → card_ready() с exact state от source
    → create_rel() → CardDoorRel.create() → _create_add_card_command()
    → ПОТИСКА СЕ от no_hardware_commands
    ★ Card-door rels се РЕГЕНЕРИРАТ тук автоматично!

25. hr.department SECOND PASS     — update back-references към AG:
                                    hr_rfid_default_access_group → mapped AG
                                    hr_rfid_allowed_access_groups → mapped AG M2M
```

**Така chain-ът е 100% естествен — единственото изкуствено е `no_hardware_commands`.**

**event_user.command_id:** Сочи към `hr.rfid.command` който НЕ мигрираме → set NULL.

### Phase 5: Events (всеки тип е отделна опция + date filter)
```
26. hr.rfid.event.user          — (ако import_user_events=True)
                                  Direct SQL batch, command_id = NULL
                                  Filtered by event_date_from
27. hr.rfid.event.system        — (ако import_system_events=True)
                                  Direct SQL batch
                                  Filtered by event_date_from
28. hr.rfid.ctrl.th.log         — (ако import_th_logs=True)
                                  Direct SQL batch
                                  Filtered by event_date_from
```

**hr.rfid.command — НЕ СЕ МИГРИРА.** Командите са транзиентни хардуерни инструкции,
специфични за конкретния контролер и момент. Нямат стойност в нова система.

**Четене от source:** XML-RPC API (search_read с pagination)
**Писане в target:** Direct SQL INSERT (bypass ORM — исторически данни без side effects)

**Mapping на M2O полета в events:**
Всеки event има `door_id`, `card_id`, `employee_id` и т.н. които трябва да се map-нат
чрез `id_map` от предишни фази. Ако mapping липсва — това е **бъг в предишна фаза**,
не нормален сценарий. Импортът спира с грешка:

```python
target_door_id = self._get_target_id('hr.rfid.door', event['door_id'])
if not target_door_id:
    raise UserError(_(
        "Cannot map door_id=%d for event #%d. "
        "This indicates a bug in a previous import phase.",
        event['door_id'], event['id']
    ))
```

**Принцип:** Fail hard на broken mapping. Никога skip, никога NULL.

### Phase 6: Подмодули (опционално, ако инсталирани)

**Vending** (ако `hr_rfid_vending` инсталиран в source И target):
```
29. product.template              — match by default_code, fallback name
                                    create if no match (products за vending rows)
                                    conflicts → Conflict Resolution UI
30. hr.rfid.ctrl.vending.row      — depends on ctrl + product.template
31. hr.rfid.ctrl.vending.settings — depends on ctrl + vending.row M2M
32. hr.rfid.vending.auto.refill   — company-level
33. hr.rfid.vending.event         — ОТДЕЛНА таблица (prototype inherit от event.user)
                                    Direct SQL batch, command_id = NULL
34. hr.rfid.vending.balance.history — Direct SQL batch (15K за co=1)
                                      depends on employee, vending_event, auto_refill
35. Employee vending fields        — update employees с vending balance полета
                                    (12 полета: balance, limit, pin, etc.)
```

**Attendance** (ако `hr_attendance_multi_rfid` инсталиран в source И target):
```
36. hr.attendance                — Direct SQL batch (997 за co=1)
                                  in_zone_id → mapped zone (ако rfid_service)
```

**Attendance Late** (ако `hr_attendance_late` инсталиран в source И target):
```
37. hr.attendance.extra          — Direct SQL batch (1,014 за co=1)
                                  Модел от hr_attendance_late (НЕ hr_attendance_multi_rfid!)
                                  depends on employee, department
```

**Service** (ако `rfid_service_base` инсталиран в source И target):
```
38. rfid.service.tags            — ORM create (малък обем)
39. rfid.service                 — depends on AG, zone, partner, card_type,
                                   tag_ids M2M
                                   mail_template_id → match by xml_id, else False + warning
                                   print_template_id → match by xml_id, else False + warning
40. rfid.service.sale            — depends on service, partner, card,
                                   AG contact rel. Direct SQL batch
```

### Phase 7: Финализация
```
41. Валидация: сравнение на бройки source vs target per model
42. Лог с резултати
```

---

## 6. Context flags при импорт

```python
IMPORT_CONTEXT = {
    # Suppress hardware commands (our custom flag in hr_rfid)
    'no_hardware_commands': True,
    # Suppress ALL mail.thread features (Odoo core)
    'tracking_disable': True,
    # Skip creation log message
    'mail_create_nolog': True,
    # Skip auto-subscription
    'mail_create_nosubscribe': True,
    # Skip automated activities
    'mail_activity_automation_skip': True,
    # Skip password reset emails (for res.users)
    'no_reset_password': True,
}
```

---

## 7. Bulk creation с XML IDs

### Source → Target Data Flow

```
Source Odoo (v14-v18)          Target Odoo 19
  │                              │
  │ XML-RPC search_read()        │
  │ ──────────────────────→      │
  │   records: [dict, dict, ...]  │
  │                              │
  │                              │ _load_records() / Direct SQL
  │                              │ ←─────────────────────────
  │                              │   ORM create + ir.model.data
```

### Structured data: `_load_records()`

```python
db_slug = source_db.replace('-', '_').replace('.', '_')
data_list = [{
    'xml_id': f'__import__.rfid_import_{db_slug}_{model_prefix}_{source_id}',
    'values': mapped_vals,
    'noupdate': True,
}]
records = Model.with_context(**IMPORT_CONTEXT)._load_records(data_list)
```

**Предимства:**
- Batch `create()` (ORM batches по 100)
- Batch `ir.model.data` upsert чрез `_update_xmlids()`
- Deduplication — safe re-run (ако xml_id вече съществува → update)
- Computed fields работят
- Constraints се проверяват

### Historical data: Direct SQL INSERT

За масови данни без side effects (events, th_log, commands, attendance):

```python
# Четене от source чрез XML-RPC
source_records = self._read_all('hr.rfid.event.user', domain, fields)

# Писане в target чрез Direct SQL
rows = [(val1, val2, ...) for row in batch]
self.env.cr.execute(
    "INSERT INTO hr_rfid_event_user (col1, col2, ...) VALUES %s",
    [tuple(rows)]
)
# + Manual ir.model.data upsert за dedup
```

### Many2Many Relations

M2M полета се обработват по два начина:

**A) Чрез ORM (при _load_records):** Ако M2M е стандартен field в модела:
```python
vals = {'zone_door_ids': [(6, 0, [target_door_id1, target_door_id2])]}
```

**B) Чрез Direct SQL:** За M2M без ORM model (чисти relation tables):
```python
self.env.cr.execute("""
    INSERT INTO hr_rfid_zone_door_rel (zone_id, door_id)
    VALUES %s ON CONFLICT DO NOTHING
""", [tuple(pairs)])
```

---

## 8. Schema разлики: Пълна карта v14 → v15 → v19

### Динамичен подход: `fields_get()`

Вместо hardcoded version switches, за всеки модел:
```python
source_fields = rpc.execute_kw(db, uid, pwd, model, 'fields_get', [], {'attributes': ['type']})
target_fields = env[model]._fields.keys()
# Import only fields that exist in BOTH source and target
common_fields = set(source_fields) & set(target_fields)
```

### Core RFID Tables

| Таблица | Поле | v14 | v15 | v19 | Обработка |
|---------|------|-----|-----|-----|-----------|
| `hr_rfid_door` | `company_id` | ❌ | ❌ | ✅ computed stored | Auto-computed от ctrl→ws chain |
| `hr_rfid_card` | `internal_number` | ❌ | ✅ | ✅ | Computed field — пропускаме |
| `hr_rfid_card` | `card_input_type` | ❌ | ✅ | ✅ | Default 'w34s' за v14 |
| `hr_rfid_card` | `access_token` | ❌ | ✅ | ✅ | Auto-generated |
| `hr_rfid_webstack` | `last_update` | ❌ | ✅ | ✅ | Skip ако липсва |
| `hr_rfid_ctrl` | `inputs_mask` | ❌ | ✅ | ✅ | Skip ако липсва |
| `hr_rfid_ctrl` | `cash_contained` | ❌ | ✅ | ✅ | Skip ако липсва |
| `hr_rfid_ctrl` | `alarm_lines_setup` | ❌ | ❌ | ✅ | Default в v19 |
| `hr_rfid_event_user` | `in_or_out` | ✅ | ✅ | ❌ | Drop при импорт |
| `hr_rfid_zone` | `company_id` | ✅ | ✅ | ❌ | Drop при импорт (v19 няма) |

### Access Group Relations

| Таблица | Поле | v14 | v15 | v19 | Обработка |
|---------|------|-----|-----|-----|-----------|
| `hr_rfid_access_group_employee_rel` | `state` | ❌ | ✅ | ✅ | Default 'active' за v14 |
| same | `internal_state` | ❌ | ✅ | ✅ | Default 'active' за v14 |
| same | `activate_on` | ❌ | ✅ | ✅ | Default now() за v14 |
| same | `visits_counting` | ❌ | ✅ | ✅ | Default False за v14 |
| same | `permitted_visits` | ❌ | ✅ | ✅ | Default 0 за v14 |
| same | `visits_counter` | ❌ | ✅ | ✅ | Default 0 за v14 |
| `hr_rfid_access_group_contact_rel` | `permited_visits` | ✅ (typo!) | ❌ | ❌ | Map to `permitted_visits` |
| same | `permitted_visits` | ❌ | ✅ | ✅ | Standard |

**ВАЖНО v14 typo:** `permited_visits` (с едно 't') в `hr_rfid_access_group_contact_rel`. Трябва да се маппне към `permitted_visits` (с две 't').

### Command Table — НЕ СЕ МИГРИРА

`hr.rfid.command` не се импортира — транзиентни хардуерни инструкции без стойност в нова система.

### Dropped in v19

Следните полета съществуват в v14/v15 но НЕ в v19:
- `message_main_attachment_id` — drop за: webstack, ctrl, door, reader, card, access_group, zone, event_user, event_system
- `hr_rfid_event_user.in_or_out` — dropped
- `hr_rfid_zone.company_id` — dropped (v19 компютира от doors)

### Vending Module (само v15+, не v14)

| Таблица | Поле | v15 | v19 | Обработка |
|---------|------|-----|-----|-----------|
| `hr_rfid_ctrl_vending_row` | всички | ✅ | ✅ | Standard import |
| `hr_rfid_vending_event` | всички | ✅ | ✅ | Direct SQL batch |
| `hr_rfid_vending_auto_refill` | всички | ✅ | ✅ | ORM create |
| `hr_rfid_vending_balance_history` | всички | ✅ | ✅ | Direct SQL batch |

**Employee vending fields** (добавени от hr_rfid_vending):
```
hr_rfid_vending_in_attendance, hr_rfid_vending_limit,
hr_rfid_vending_balance, hr_rfid_vending_auto_refill,
hr_rfid_vending_auto_refill_amount, hr_rfid_vending_refill_amount,
hr_rfid_vending_auto_refill_action, hr_rfid_vending_limit_type,
hr_rfid_vending_limit_amount, hr_rfid_vending_limit_period,
hr_rfid_vending_pin, hr_rfid_vending_negbal
```
→ Import тези полета в hr.employee САМО ако hr_rfid_vending е инсталиран.

### Service Module (само v15+)

| Таблица | Поле | v15 | v19 | Обработка |
|---------|------|-----|-----|-----------|
| `rfid_service` | всички | ✅ | ✅ | ORM create |
| `rfid_service_sale` | всички | ✅ | ✅ | Direct SQL batch |
| `rfid_service_tags` | M2M | ✅ | ✅ | M2M import |

**Attendance + Service:** `hr_attendance.in_zone_id` — added by rfid_service module.
→ Import само ако и двата модула са инсталирани.

### M2M Relation Tables (пълен списък от одит)

**Explicitly defined (relation= param):**

| M2M таблица | Model 1 | Model 2 | col1 | col2 |
|-------------|---------|---------|------|------|
| `hr_rfid_zone_door_rel` | hr.rfid.zone | hr.rfid.door | zone_id | door_id |
| `hr_rfid_reader_door_rel` | hr.rfid.reader | hr.rfid.door | reader_id | door_id |
| `access_group_inheritance` | hr.rfid.access.group | hr.rfid.access.group | inheritor | inherited |

**Auto-generated (Odoo default naming):**

| M2M таблица | Field | Model 1 | Model 2 |
|-------------|-------|---------|---------|
| `hr_rfid_zone_hr_department_rel` | zone.permitted_department_ids | hr.rfid.zone | hr.department |
| `hr_rfid_zone_hr_employee_category_rel` | zone.permitted_employee_category_ids | hr.rfid.zone | hr.employee.category |
| `hr_rfid_zone_hr_employee_rel` | zone.employee_ids | hr.rfid.zone | hr.employee |
| `hr_rfid_zone_res_partner_rel` | zone.contact_ids | hr.rfid.zone | res.partner |
| `hr_rfid_notification_res_partner_rel` | notification.notify_partner_ids | hr.rfid.notification | res.partner |
| `hr_rfid_access_group_hr_department_rel` | AG.department_ids | hr.rfid.access.group | hr.department |
| `hr_rfid_time_schedule_hr_rfid_ctrl_rel` | TS.controller_ids | hr.rfid.time.schedule | hr.rfid.ctrl |
| `rfid_service_rfid_service_tags_rel` | service.tag_ids | rfid.service | rfid.service.tags |

**Обработка:** M2M полета се импортират чрез ORM `[(6, 0, [mapped_ids])]` при `_load_records()`.
За M2M с explicit relation table — Direct SQL INSERT ако е нужно.

---

## 9. Тестови бази

### 15_dev_cloud (Odoo 15.0, мулти-компания)
- **Company 1:** Полимекс Холдинг ЕООД
- **Инсталирани:** hr_rfid, hr_rfid_vending, rfid_service_base, hr_attendance_multi_rfid
- **Данни (co=1):** 7 ws, 11 ctrl, 110 doors, 64 cards, 37 employees, 10 AG, 7.5K events
- **XML-RPC URL:** `http://localhost:8015` (порт за Odoo 15)

### 14_dev_mk (Odoo 14.0, single company)
- **Company 1:** МПК Плевен ЕООД
- **Инсталирани:** hr_rfid, hr_attendance_multi_rfid
- **Данни:** 4 ws, 7 ctrl, 10 doors, 295 cards, 260 employees, 4 AG, 35K events
- **XML-RPC URL:** `http://localhost:8014` (порт за Odoo 14)

---

## 10. Структура на модула

```
hr_rfid_odoo_import/
├── __init__.py
├── __manifest__.py
├── README.rst
├── IMPLEMENTATION_PLAN.md              ← ТОЗИ ФАЙЛ
├── models/
│   ├── __init__.py
│   ├── import_wizard.py                # Multi-step wizard (5 states)
│   ├── import_conflict.py              # Conflict resolution TransientModel
│   └── importers/
│       ├── __init__.py
│       ├── base_importer.py            # Базов клас — XML-RPC + ORM utilities
│       ├── core_importer.py            # Phase 1+3: foundation + hardware
│       ├── people_importer.py          # Phase 2: departments, employees, partners
│       ├── access_importer.py          # Phase 4: AG, AG rels, cards
│       ├── event_importer.py           # Phase 5: events, commands, th_log
│       ├── vending_importer.py         # Phase 6a: vending data
│       ├── attendance_importer.py      # Phase 6b: attendance data
│       └── service_importer.py         # Phase 6c: service data
├── security/
│   └── ir.model.access.csv
├── views/
│   └── import_wizard_views.xml
├── static/
│   └── description/
│       └── icon.png
└── i18n/
    └── (generated later)
```

---

## 11. Wizard Workflow — Един multi-step wizard

**Model:** `hr.rfid.odoo.import.wiz` (TransientModel)
**Pattern:** Single wizard с `statusbar` widget, 5 стъпки, Back бутон, dry-run preview.
**Референции от core:** l10n_au payroll register, account_base_import, account_secure_entries.

### State Flow

```
connection → configure → confirm → importing → done
     ↑           ↑          ↑
     └───────────┴──────────┘  (Back бутон)
```

### Полета

**Connection (step 1):**
- `source_url` — Char, required, default='http://localhost:8069'
- `source_db` — Char, required
- `source_login` — Char, required, default='admin'
- `source_password` — Char, required, password=True, default='admin'
- `source_version` — Char, readonly (попълва се при Test Connection)
- `source_uid` — Integer (authenticated user ID)
- `installed_modules_json` — Text (JSON — инсталирани RFID модули в source)

**Configuration (step 2):**
- `company_line_ids` — One2many → `hr.rfid.odoo.import.company.line`:
  - `source_id` — Integer (company id в source)
  - `source_name` — Char
  - `do_import` — Boolean
  - `target_company_id` — Many2one('res.company')
- `import_hardware` — Boolean, default True
- `import_people` — Boolean, default True
- `import_access` — Boolean, default True
- `import_cards` — Boolean, default True
- `import_all_partners` — Boolean, default False ("Import all partners, not just RFID-linked")
- `import_all_employees` — Boolean, default False ("Import all employees, not just RFID-linked")
- `import_images` — Boolean, default True ("Import employee/partner photos")
- `import_user_events` — Boolean, default False
- `import_system_events` — Boolean, default False
- `import_th_logs` — Boolean, default False
- `event_date_from` — Date (давност назад, напр. "последните 6 месеца")
- `import_vending` — Boolean (visible ако в source И target)
- `import_attendance` — Boolean (visible ако hr_attendance_multi_rfid в source И target)
- `import_attendance_extra` — Boolean (visible ако hr_attendance_late в source И target)
- `import_service` — Boolean (visible ако rfid_service_base в source И target)

**Confirm / Preview (step 3):**
- `warnings` — Json, computed (`actionable_errors` widget)
- `preview_text` — Text, readonly (бройки + проблеми)
- `dry_run` — Boolean, default False ("Full dry-run: execute + rollback")

**Progress (step 4):**
- `progress_text` — Text, readonly (натрупващ се лог)
- `progress_percent` — Float (0-100)

**Results (step 5):**
- `log_ids` — One2many → `hr.rfid.odoo.import.log`:
  - `phase` — Char
  - `model` — Char
  - `source_count` — Integer
  - `imported_count` — Integer
  - `skipped_count` — Integer
  - `status` — Selection: pending/done/error
  - `duration` — Float (секунди)
  - `error_message` — Text
- `error_message` — Text (главна грешка, ако има)

**State:**
- `state` — Selection: connection / configure / confirm / importing / done

### Бутони и Action-и

```
Step 1 (connection):
  [Test Connection →]  → action_test_connection()
                         authenticate, detect version, list companies
                         state = 'configure'
  [Cancel]

Step 2 (configure):
  [← Back]             → action_back() → state = 'connection'
  [Preview →]          → action_preview()
                         Винаги: source бройки (search_count) + actionable_errors
                         Ако dry_run=True: пълен импорт + savepoint(rollback=True)
                         попълва preview_text + warnings
                         state = 'confirm'
  [Cancel]

Step 3 (confirm):
  [← Back]             → action_back() → state = 'configure'
  [Run Dry-Run]        → action_dry_run() (visible ако dry_run=True, още не е пуснат)
                         пълен импорт + rollback, показва точни резултати
  [Start Import →]     → action_import()
                         проверява danger warnings
                         state = 'importing' → do_import()
                         state = 'done'
  [Cancel]

Step 4 (importing):
  (no buttons — spinner + progress bar + log)

Step 5 (done):
  [Close]              → special="cancel"
  [View Imported Data] → action links в log_ids
```

### actionable_errors примери (step 3)

```python
warnings = {}
# Danger — блокира импорт
if 'hr_rfid_vending' in source_modules and 'hr_rfid_vending' not in target_modules:
    warnings['missing_vending'] = {
        'level': 'danger',
        'message': _("Source has hr_rfid_vending but it's not installed in target."),
        'action_text': _("Install Module"),
        'action': install_module_action,
    }
# Warning — информативно
if source_event_count > 100000:
    warnings['large_events'] = {
        'level': 'warning',
        'message': _("Source has %d events. Import may take several minutes.", count),
    }
# Info
if no_companies_selected:
    warnings['no_companies'] = {
        'level': 'danger',
        'message': _("No companies selected for import."),
    }
```

### _keep_open() helper

```python
def _keep_open(self):
    return {
        'type': 'ir.actions.act_window',
        'res_model': self._name,
        'target': 'new',
        'views': [(False, 'form')],
        'res_id': self.id,
    }
```

### XML View структура

```xml
<form string="Import RFID Data from Odoo">
    <header>
        <field name="state" widget="statusbar" options="{'clickable': False}"/>
    </header>
    <sheet>
        <!-- Warnings (step 3) -->
        <div invisible="not warnings">
            <field name="warnings" widget="actionable_errors"/>
        </div>

        <!-- Step 1: Connection -->
        <group invisible="state != 'connection'" string="Source Odoo Connection">
            <group>
                <field name="source_url"/>
                <field name="source_db"/>
            </group>
            <group>
                <field name="source_login"/>
                <field name="source_password"/>
            </group>
        </group>

        <!-- Step 2: Configuration -->
        <group invisible="state != 'configure'">
            <field name="company_line_ids" nolabel="1">
                <list editable="bottom">...</list>
            </field>
            <group string="Import Options">
                <!-- toggles -->
            </group>
        </group>

        <!-- Step 3: Confirm / Preview -->
        <group invisible="state != 'confirm'">
            <field name="preview_text" readonly="1" widget="text"/>
        </group>

        <!-- Step 4: Importing -->
        <div invisible="state != 'importing'" class="text-center">
            <span class="spinner-border spinner-border-sm"/> Importing...
            <field name="progress_percent" widget="progressbar"/>
            <field name="progress_text" readonly="1" widget="text"/>
        </div>

        <!-- Step 5: Done -->
        <group invisible="state != 'done'">
            <field name="error_message" invisible="not error_message"
                   class="text-danger" readonly="1"/>
            <field name="log_ids" readonly="1" nolabel="1">
                <list>...</list>
            </field>
        </group>
    </sheet>
    <footer>
        <button string="Test Connection" name="action_test_connection"
                type="object" class="btn-primary"
                invisible="state != 'connection'"/>
        <button string="Preview" name="action_preview"
                type="object" class="btn-primary"
                invisible="state != 'configure'"/>
        <button string="Start Import" name="action_import"
                type="object" class="btn-primary btn-lg"
                invisible="state != 'confirm'"/>
        <button string="Close" special="cancel" class="btn-primary"
                invisible="state != 'done'"/>

        <button string="Back" name="action_back" type="object"
                class="btn-secondary"
                invisible="state not in ('configure', 'confirm')"/>
        <button string="Cancel" special="cancel" class="btn-secondary"
                invisible="state in ('importing', 'done')"/>
    </footer>
</form>
```

---

## 12. BaseImporter клас

```python
class BaseImporter:
    """Base class for all importers. Handles XML-RPC reading and ORM writing."""

    def __init__(self, env, source_url, source_db, source_uid, source_password,
                 company_map, options):
        self.env = env
        # XML-RPC connection (source — read only)
        self.source_url = source_url
        self.source_db = source_db
        self.source_uid = source_uid
        self.source_password = source_password
        self.rpc_models = xmlrpc.client.ServerProxy(
            f'{source_url}/xmlrpc/2/object', allow_none=True
        )
        # Mapping
        self.company_map = company_map      # {source_co_id: target_co_id}
        self.id_map = {}                    # {model: {source_id: target_id}}
        self.options = options              # wizard options dict
        # Cache
        self._field_cache = {}             # {model: {field_name: field_info}}

    # ── Source reading (XML-RPC) ──────────────────────────────

    def _search_read(self, model, domain, fields, order='id asc', limit=0):
        """Read records from source via XML-RPC."""
        kwargs = {'fields': fields, 'order': order}
        if limit:
            kwargs['limit'] = limit
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_read', [domain], kwargs
        )

    def _read_all(self, model, domain, fields, batch_size=1000):
        """ID-based pagination for large datasets."""
        all_records = []
        last_id = 0
        while True:
            batch_domain = [('id', '>', last_id)] + domain
            records = self._search_read(
                model, batch_domain, fields, order='id asc', limit=batch_size
            )
            if not records:
                break
            all_records.extend(records)
            last_id = records[-1]['id']
        return all_records

    def _search_count(self, model, domain):
        """Count records in source."""
        return self.rpc_models.execute_kw(
            self.source_db, self.source_uid, self.source_password,
            model, 'search_count', [domain]
        )

    def _has_field(self, model, field_name):
        """Check if field exists in source model via fields_get()."""
        if model not in self._field_cache:
            self._field_cache[model] = self.rpc_models.execute_kw(
                self.source_db, self.source_uid, self.source_password,
                model, 'fields_get', [],
                {'attributes': ['type', 'relation', 'required']}
            )
        return field_name in self._field_cache[model]

    def _get_source_fields(self, model):
        """Get all source fields metadata (cached)."""
        if model not in self._field_cache:
            self._has_field(model, '_dummy_')  # populate cache
        return self._field_cache[model]

    # ── Target writing (ORM) ──────────────────────────────────

    def _load_records(self, model_name, data_list):
        """Use Odoo 19 _load_records() for batch create + XML ID."""
        Model = self.env[model_name].with_context(**IMPORT_CONTEXT)
        return Model._load_records(data_list)

    def _direct_sql_insert(self, table, columns, rows):
        """Direct SQL INSERT into target DB — bypass ORM."""
        if not rows:
            return
        placeholders = ', '.join(['%s'] * len(columns))
        cols = ', '.join(columns)
        # Use execute_values for performance
        from psycopg2.extras import execute_values
        execute_values(
            self.env.cr._obj,
            f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING",
            rows,
            template=f"({placeholders})"
        )

    # ── ID Mapping ────────────────────────────────────────────

    def _xml_id(self, model_prefix, source_id):
        """Generate XML ID for ir.model.data.
        Includes source_db to prevent collisions between different sources."""
        db_slug = self.source_db.replace('-', '_').replace('.', '_')
        return f'__import__.rfid_import_{db_slug}_{model_prefix}_{source_id}'

    def _get_target_id(self, model, source_id):
        """Get target ID from previously imported record."""
        return self.id_map.get(model, {}).get(source_id)

    def _set_target_id(self, model, source_id, target_id):
        """Store source→target ID mapping."""
        self.id_map.setdefault(model, {})[source_id] = target_id

    def _resolve_target_id(self, model, source_id):
        """Resolve target ID, checking ir.model.data if not in cache."""
        target_id = self._get_target_id(model, source_id)
        if target_id:
            return target_id
        # Check ir.model.data
        prefix = model.replace('.', '_')
        xml_id = self._xml_id(prefix, source_id)
        imd = self.env['ir.model.data'].sudo().search([
            ('module', '=', '__import__'),
            ('name', '=', xml_id.split('.', 1)[1] if '.' in xml_id else xml_id),
        ], limit=1)
        if imd:
            self._set_target_id(model, source_id, imd.res_id)
            return imd.res_id
        return False

    # ── Company mapping ───────────────────────────────────────

    def _map_company(self, source_company_id):
        """Map source company ID to target company ID."""
        return self.company_map.get(source_company_id, False)

    def _company_domain(self):
        """Return domain filter for source companies being imported."""
        source_ids = list(self.company_map.keys())
        if len(source_ids) == 1:
            return [('company_id', '=', source_ids[0])]
        return [('company_id', 'in', source_ids)]

    # ── Utility ───────────────────────────────────────────────

    def _map_m2o(self, model, source_val):
        """Map Many2one field: [id, name] → target_id or False."""
        if not source_val:
            return False
        source_id = source_val[0] if isinstance(source_val, (list, tuple)) else source_val
        return self._get_target_id(model, source_id)

    def _map_m2m(self, model, source_ids):
        """Map Many2many field: [id1, id2, ...] → [(6, 0, [target_ids])]."""
        if not source_ids:
            return [(6, 0, [])]
        target_ids = [
            self._get_target_id(model, sid)
            for sid in source_ids
            if self._get_target_id(model, sid)
        ]
        return [(6, 0, target_ids)]
```

---

## 13. Conflict Detection & Resolution

### Принцип: НИКОГА не пропускай данни мълчаливо

При конфликт (запис в target съвпада с source по уникално поле) — **спри и покажи на потребителя**.

### Кога възникват конфликти

| Модел | Уникално поле | Конфликт сценарий |
|-------|--------------|-------------------|
| `hr.rfid.webstack` | `serial` | Webstack с такъв serial вече е в target |
| `hr.rfid.ctrl` | `serial_number` | Controller вече е в target |
| `hr.rfid.card` | `number` | Карта с такъв номер вече съществува |
| `hr.employee` | `barcode`, `identification_id` | Служител с такъв баркод/ЕГН |
| `res.partner` | `vat`, `email` | Партньор с такъв ДДС/email |
| `hr.department` | `name` + `company_id` | Отдел със същото име |
| `hr.rfid.access.group` | `name` + `company_id` | AG със същото име |
| `hr.rfid.zone` | `name` | Зона със същото име |
| `product.template` | `default_code`, `name` | Продукт със същия код/име |

### Conflict Resolution Model

```python
class HrRfidOdooImportConflict(models.TransientModel):
    _name = 'hr.rfid.odoo.import.conflict'
    _description = 'Import Conflict'

    wizard_id = fields.Many2one('hr.rfid.odoo.import.wiz', required=True)
    source_model = fields.Char()           # 'hr.rfid.webstack'
    source_id = fields.Integer()           # ID в source
    source_name = fields.Char()            # Display name в source
    source_ref = fields.Char()             # Unique field value (serial, number, etc.)
    target_id = fields.Integer()           # Съществуващ ID в target
    target_name = fields.Char()            # Display name в target
    conflict_field = fields.Char()         # Полето причинило конфликт ('serial')
    resolution = fields.Selection([
        ('link', 'Link to existing'),      # Свържи source → target (не създавай нов)
        ('create', 'Create new'),          # Създай нов (ако е допустимо)
        ('skip', 'Skip this record'),      # Пропусни (потребителят решава)
    ], default='link', required=True)
```

### Workflow

**Step 3 (Preview):** По време на preview се сканират конфликти:

```python
def _detect_conflicts(self):
    """Scan source records against target for potential conflicts."""
    conflicts = []

    # Webstacks: match by serial
    source_ws = self._search_read('hr.rfid.webstack', domain, ['name', 'serial'])
    for ws in source_ws:
        existing = self.env['hr.rfid.webstack'].search([
            ('serial', '=', ws['serial'])
        ], limit=1)
        if existing:
            conflicts.append({
                'source_model': 'hr.rfid.webstack',
                'source_id': ws['id'],
                'source_name': ws['name'],
                'source_ref': ws['serial'],
                'target_id': existing.id,
                'target_name': existing.name,
                'conflict_field': 'serial',
                'resolution': 'link',  # default
            })

    # Cards: match by number
    source_cards = self._search_read('hr.rfid.card', domain, ['name', 'number'])
    for card in source_cards:
        existing = self.env['hr.rfid.card'].search([
            ('number', '=', card['number'])
        ], limit=1)
        if existing:
            conflicts.append({...})

    # ... аналогично за останалите модели
    return conflicts
```

**Показване в UI (step 3):**

```xml
<!-- Conflict resolution table -->
<group invisible="state != 'confirm'" string="Conflicts Found">
    <field name="conflict_ids" nolabel="1"
           invisible="not conflict_ids">
        <list editable="bottom">
            <field name="source_model" readonly="1"/>
            <field name="source_name" readonly="1"/>
            <field name="source_ref" readonly="1" string="Unique Key"/>
            <field name="target_name" readonly="1" string="Existing in Target"/>
            <field name="resolution" required="1"/>
        </list>
    </field>
    <div invisible="conflict_ids" class="text-success">
        No conflicts detected.
    </div>
</group>
```

**Потребителят решава за ВСЕКИ конфликт:**
- **Link to existing** — source record се map-ва към съществуващия target record (default)
- **Create new** — създава нов record (възможно само ако unique constraint позволява)
- **Skip** — не импортира този record (с warning в лога)

**При импорт:** `action_import()` проверява `conflict_ids`:

```python
def _resolve_conflict(self, conflict):
    if conflict.resolution == 'link':
        # Map source_id → target_id, don't create
        self.importer._set_target_id(
            conflict.source_model, conflict.source_id, conflict.target_id
        )
    elif conflict.resolution == 'create':
        # Proceed with normal create (may fail on unique constraint)
        pass
    elif conflict.resolution == 'skip':
        # Mark as skipped, log warning
        self.importer._set_target_id(
            conflict.source_model, conflict.source_id, None  # sentinel
        )
        self._log_warning(f"Skipped: {conflict.source_model} #{conflict.source_id}")
```

### Danger warnings за нерешени конфликти

```python
if unresolved_conflicts:
    warnings['unresolved_conflicts'] = {
        'level': 'danger',
        'message': _("%d conflicts need resolution before import.", count),
    }

# Warning ако target вече има RFID данни
existing = {
    'webstacks': env['hr.rfid.webstack'].search_count([]),
    'cards': env['hr.rfid.card'].search_count([]),
    'employees': env['hr.employee'].search_count([]),
}
if any(existing.values()):
    warnings['existing_data'] = {
        'level': 'warning',
        'message': _("Target database already has %d webstacks, %d cards, "
                     "%d employees. Conflicts were detected during preview.",
                     existing['webstacks'], existing['cards'],
                     existing['employees']),
    }
```

---

## 14. Error Handling

(предишна секция 13)

- **SAVEPOINT** per phase — ако Phase 4 гръмне, Phase 1-3 остават
- **Source connection:** read-only XML-RPC calls (само search_read, fields_get)
- **Timeout handling:** XML-RPC може да timeout-не → retry с exponential backoff
- **Batch processing:** На всеки batch → commit + progress update
- **Deduplication:** ir.model.data → safe re-run (повторно пускане не създава дубликати)
- **Progress log:** натрупва се в `progress_text` + `log_ids`
- **Error recovery:** При грешка — записва в лог, продължава със следващия record/phase

### Connection Error Handling

```python
import socket

try:
    records = self._search_read(model, domain, fields)
except xmlrpc.client.Fault as e:
    # Odoo-level error (e.g., access denied, model not found)
    self._log_error(f"XML-RPC Fault: {e.faultString}")
except socket.timeout:
    # Network timeout — retry
    self._log_warning(f"Timeout reading {model}, retrying...")
except ConnectionRefusedError:
    # Source Odoo not running
    raise UserError(_("Cannot connect to source Odoo at %s") % self.source_url)
```

---

## 14. Разрешени въпроси

### Q: Трябва ли да импортираме hr.rfid.command записи?
**A: НЕ.** Командите са транзиентни хардуерни инструкции — специфични за конкретния
контролер и момент на изпълнение. В нова система нямат стойност.
При нужда от хардуерна синхронизация, командите ще бъдат генерирани наново.

### Q: Attendance данни — опция или отделен модул?
**A: Опция в wizard** (toggle `import_attendance`). Видим само ако и двата модула
(`hr_attendance_multi_rfid`) са инсталирани в source и target.
Не е нужен отделен модул — данните са просто записи в hr.attendance.

### Q: Service module — model names между версии?
**A: Динамично чрез API.** Проверяваме `fields_get()` за наличие на модела.
В v15: `rfid.service`, `rfid.service.sale`, `rfid.service.tags`.
Ако модел не съществува → skip.

### Q: Employee resource_id / user_id mapping?
**A: resource_id** се създава автоматично от Odoo ORM при Employee.create().

**user_id — три нива на импорт (потребителят избира):**

**Ниво 1 (default): Match by login**
- Ако в target вече съществува user с такъв login → link employee → user
- Ако не → `user_id = False`

**Ниво 2 (опция): Create users**
- Checkbox "Create missing users" в wizard
- Създава `res.users` с данни от source (name, login, email, lang, tz)
- **Парола:** Временна генерирана + `force_reset_password=True`
  (XML-RPC не позволява четене на password hash от source)
- **Без права** по подразбиране — само `base.group_user` (Internal User)
- **Warning в UI:** "Потребителите ще бъдат създадени без права за достъп.
  Ще получат email за смяна на парола при първи вход.
  Администраторът трябва ръчно да зададе правата."

**Ниво 3 (допълнителна опция): Transfer groups**
- Checkbox "Transfer user groups" (visible само ако "Create users" е включено)
- Mapping по `xml_id`: `base.group_user`, `hr.group_hr_manager`, etc.
- Групи с xml_id в source, които съществуват и в target → assign
- Групи без xml_id или несъществуващи в target → skip + warning в лога
- **Warning в UI:** "Някои групи може да не съществуват в Odoo 19
  или да имат различни права. Проверете ръчно след импорт."

### Q: Трябва ли да импортираме attachments?
**A: Снимки ДА (опция), файлове НЕ.**
- `hr.employee.image_1920` — import чрез XML-RPC (base64 encoded), toggle в wizard
- `res.partner.image_1920` — import чрез XML-RPC
- Другите attachments (ir.attachment) — skip

### Q: address_home_id в source → какво в target?
**A: `address_home_id` НЕ СЪЩЕСТВУВА в Odoo 19!**
Заменено с flat полета на `hr.version` (auto-created via _inherits):
- `private_street`, `private_city`, `private_zip`, `private_state_id`, `private_country_id`
- При импорт: четем `address_home_id` от source → read partner fields → map към flat полета

### Q: resource.resource и hr.version — импортираме ли ги?
**A: НЕ.** И двата се auto-create-ват от `hr.employee.create()`:
- `resource.resource` — via `resource.mixin.create()` (винаги)
- `hr.version` — via `_inherits = {'hr.version': 'version_id'}` (ново в v19)

### Q: Как обработваме Binary fields (images)?
**A:** XML-RPC автоматично кодира binary fields в base64.
```python
records = self._search_read('hr.employee', domain, ['name', 'image_1920'])
# records[0]['image_1920'] е вече base64 string → директно в vals
```

### Q: hr.rfid.ctrl.CardDoorRel.write() — Guard needed?
**A: НЕ.** Write на CardDoorRel (line 934-951) проверява за промяна на ts_id
и извиква add_card/remove_card. При импорт не правим write на CardDoorRel —
те се създават от chain-а с correct ts_id от първия път.

---

## 15. Критични файлове за reference

| Файл | Защо | Точни линии |
|------|------|-------------|
| `hr_rfid/models/hr_rfid_door.py` | CardDoorRel create → D1 HW commands | create:923, _create_add_card_cmd:898, _create_remove_card_cmd:907 |
| `hr_rfid/models/hr_rfid_door.py` | update_card_rels chain entry | update_card_rels:771, check_relevance_fast:832, _check_compat_n_rdy:895 |
| `hr_rfid/models/hr_rfid_card.py` | Card create → update_card_rels cascade | create:282, card_ready:210, get_potential_access_doors:190 |
| `hr_rfid/models/hr_rfid_access_group.py` | AG rels create → chain cascade | AGDoorRel.create:499, AGEmployeeRel.create:738, _activate:732, _compute_state:617 |
| `hr_rfid/models/hr_rfid_ctrl.py` | write_ts_id/delete_ts_id D3 commands | write_ts_id:1276, delete_ts_id:1282, _base_command:972 |
| `hr_rfid/models/hr_rfid_command.py` | add_card/remove_card D1 commands | add_card:553, remove_card:603, add_remove_card:473, create_d1_cmd:447 |
| `hr_rfid/models/hr_employee.py` | Employee create → auto add_acc_gr | create:262, add_acc_gr:118 |
| `hr_rfid_old_cloud_import/models/import_wizard.py` | Pattern: wizard + context passing | do_import(), context['defs'] |
| `hr_rfid_old_cloud_import/models/welcome_wizard.py` | Pattern: do_check_connection() | check_connection() |

---

## 16. Имплементационен ред

1. ✅ **Guards в hr_rfid** (5 places в 3 файла) — prerequisite
2. ✅ **Module skeleton** (__init__, __manifest__, security, icon, README.rst)
3. ✅ **base_importer.py** — XML-RPC + ORM utilities + `_try_load_records()` savepoint
4. ✅ **import_wizard.py + views** — multi-step wizard (5 states) + company lines
5. ✅ **core_importer.py** (Phase 1+3: card_type, department, workcode, ts, hardware) — dynamic fields
6. ✅ **people_importer.py** (Phase 2: employees, partners + images) — dynamic fields
7. ✅ **access_importer.py** (Phase 4: AG, AG rels, cards → chain regeneration) — dynamic fields
8. ✅ **event_importer.py** (Phase 5: events, commands, th_log → Direct SQL batch) — dynamic fields
9. ✅ **vending_importer.py** (Phase 6a: vending rows, events, balance) — dynamic fields
10. ✅ **attendance_importer.py** (Phase 6b: hr.attendance, attendance.extra)
11. ✅ **service_importer.py** (Phase 6c: rfid.service, rfid.service.sale)
12. ⏳ **Тест с 14_dev_mk** (single company, small dataset) — blocked: python3.10 venv
13. ✅ **Тест с 15_dev_cloud** (multi-company, company 1 only) — **FULL PASS 2026-03-16**
    - **Phase 1+3 (Core):** 7 webstacks, 11 ctrl, 21 doors, 26 readers, 9 zones, 3 alarms
    - **Phase 2 (People):** 8 partners, 22 employees, 72 employee categories, 5 departments
    - **Phase 4 (Access):** 10 AG, 23 AG-door rels, 54 AG-emp rels, 10 AG-contact rels, 55 cards
    - **Phase 5 (Events):** 6,388 user events (240K src, 234K other companies), 121,132 system events, 0 TH logs (schema)
    - **Phase 6a (Vending):** 36 vending rows, 1,775 vending events, 14,395 balance history, 22 emp vending fields
    - **Phase 6b (Attendance):** 997 attendance records (133K src, rest no employee mapping)
    - **Known:** input_mask(0/89), output_ts(0/10), th(0/1) — schema incompatible, auto-regenerated by HW
    - **Duration:** 110s total (incl. events from 2025-10-01, 250K balance history)
    - **Error handling:** Savepoints per phase — failed phases don't block subsequent ones
14. ⏳ **Тест с 14_dev_mk** (single company, small dataset) — blocked: python3.10 venv
15. ✅ **Преводи** (bg, es, el_GR, ro, de, it) — 140 strings × 6 languages = 100%
16. ⏳ **Commit & push**

---

## 17. Тестване

### Test 1: 14_dev_mk → 19_import_test

```bash
# 1. Стартиране на Odoo 14 source
cd /path/to/odoo14 && ./odoo-bin -c odoo.conf --http-port=8014

# 2. Създаване тестова target база
cd /home/lubo/PycharmProjects/odoo19
./venv/bin/python odoo/odoo-bin db init 19_import_test --language bg_BG --country BG \
    --addons-path=odoo/addons,addons

# 3. Инсталиране на модула
./venv/bin/python odoo/odoo-bin -d 19_import_test -i hr_rfid_odoo_import \
    --no-http --stop-after-init --addons-path=odoo/addons,addons

# 4. Run wizard:
#    URL: http://localhost:8014
#    DB: 14_dev_mk
#    Login: admin / admin
#    → Check Connection → Select company → Start Import → Verify
```

### Test 2: 15_dev_cloud → 19_import_test

```bash
# 1. Стартиране на Odoo 15 source
cd /path/to/odoo15 && ./odoo-bin -c odoo.conf --http-port=8015

# 2. Инсталиране допълнителни модули в target
./venv/bin/python odoo/odoo-bin -d 19_import_test \
    -i hr_rfid_vending,hr_attendance_multi_rfid,rfid_service_base \
    --no-http --stop-after-init --addons-path=odoo/addons,addons

# 3. Run wizard:
#    URL: http://localhost:8015
#    DB: 15_dev_cloud
#    Login: admin / admin
#    → Check Connection → Select "Полимекс Холдинг" → Enable all submodules
#    → Start Import → Verify
```

### Verification Script (Odoo Shell)

```python
# Сравнение на бройки source vs target
import xmlrpc.client

source = xmlrpc.client.ServerProxy('http://localhost:8015/xmlrpc/2/object')
db, uid, pwd = '15_dev_cloud', 2, 'admin'

models_to_check = [
    'hr.rfid.webstack', 'hr.rfid.ctrl', 'hr.rfid.door',
    'hr.rfid.card', 'hr.employee', 'hr.rfid.access.group',
    'hr.rfid.event.user', 'hr.rfid.event.system',
]
for model in models_to_check:
    src_count = source.execute_kw(db, uid, pwd, model, 'search_count',
        [[('company_id', '=', 1)]])
    tgt_count = env[model].search_count([])
    status = '✅' if src_count == tgt_count else '❌'
    print(f"{status} {model}: source={src_count}, target={tgt_count}")
```
