---
id: l10n_bg_hr_attendance_overtime_rates
title: Bulgaria — Attendance Overtime Rates
module: l10n_bg_hr_attendance_overtime_rates
module_version: 19.0.1.0.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Bulgarian statutory overtime/night coefficients and public holidays
last_updated: '2026-06-03'
source_digest: sha256:73c06219d3138dbb79864df737a40919973cab9ad0be2eb7becdd10a09b86c98
depends:
- hr_attendance_late
- hr_holidays
entities:
  primary: res.company
  related:
  - l10n.bg.generate.holidays.wizard
keywords:
- attendance
- bulgarian
- coefficients
- company
- generate
- holidays
- l10n
- overtime
- public
- rates
- res
- statutory
- wizard
license: AGPL-3
author: Polimex
category: Human Resources/Attendances
installable: true
application: false
auto_install: false
counts:
  models: 2
  views: 1
  access_rules: 1
  record_rules: 0
  crons: 1
  images: 0
images: []
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Bulgaria — Attendance Overtime Rates — `l10n_bg_hr_attendance_overtime_rates` v19.0.1.0.0

Bulgarian statutory overtime/night coefficients and public holidays

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `l10n_bg_hr_attendance_overtime_rates`
- **Version**: `19.0.1.0.0`
- **Category**: Human Resources/Attendances
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_attendance_late`, `hr_holidays`

### README (verbatim)

#### Bulgaria — Attendance Overtime Rates & Public Holidays

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Bulgarian localisation seed for the attendance cost layer: statutory overtime coefficients, the night-shift supplement, and official public holidays.

##### 🎯 Overview

`hr_attendance_late` provides a generic, dated legal-rate table (`hr.legal.rate`) used when costing attendance. This module fills it with the Bulgarian Labour Code values and adds the country's public holidays as global calendar leaves, so the cost bridge in `hr_attendace_rfid_hr_hourly_cost` can tell a rest-day from a public holiday.

##### ✨ Key Features

- **КТ overtime coefficients (dated)** — work-day overtime ×1.5, rest-day ×1.75, public-holiday ×2.0 (КТ чл. 262 minimums), seeded with a historical effective date so future law changes are added as new dated rows.
- **Night-shift supplement** — an additive per-hour amount (НСОРЗ чл. 8), seeded at 0.51 EUR effective 2026-01-01 (eurozone). Additive, not a multiplier.
- **Public-holiday generation** — computes the year's official Bulgarian holidays, including the movable Orthodox Easter dates (`dateutil.easter` with `EASTER_ORTHODOX`), as global `resource.calendar.leaves`. Idempotent.
- **Wizard + annual cron** — generate holidays for a chosen year on demand, or let the yearly cron roll the next year forward.

##### 📋 Requirements

- Odoo 19.0+
- `hr_attendance`
- `hr_holidays`
- `hr_attendance_late` (provides the `hr.legal.rate` table the seed targets)

##### ⚙️ Configuration

- The legal rates are seeded on install (`noupdate`, so local overrides survive upgrades). Review or override them under **Attendances ▸ Configuration ▸ Legal Rates**.
- Generate public holidays via **Attendances** → the *Generate Bulgarian Public Holidays* wizard, or rely on the annual cron.

##### 🚀 Usage

1. Install — КТ coefficients and the night supplement appear in **Legal Rates**.
2. Run the holiday wizard for the current/next year (or wait for the cron).
3. The attendance cost bridge reads these rates and the public-holiday calendar automatically; no further setup is needed.

> When the law changes a coefficient, add a **new** Legal Rate row with the new *Valid From* date — past worked days keep their historical value.

##### 🛠️ Technical

- **`data/legal_rates.xml`** — seeds `hr.legal.rate` rows (`overtime_workday`, `overtime_weekend`, `overtime_holiday`, `night_supplement`).
- **`res.company._generate_bg_public_holidays(year)`** — idempotent batched creation of global `resource.calendar.leaves`; fixed dates + Orthodox-Easter-derived Good Friday / Holy Saturday / Easter Monday.
- **`_cron_generate_bg_public_holidays`** — annual roll-forward.
- **`generate.bg.holidays.wizard`** — on-demand generation for a chosen year.

##### 👥 Credits

**Polimex Holding Ltd.** — https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i l10n_bg_hr_attendance_overtime_rates --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:29`.  Model.  Inherits: `res.company`.

#### Notable methods

- **`_cron_generate_bg_public_holidays(self)`** — decorators: `@api.model`
  - Yearly cron: seed next year's BG public holidays for every company
  - touches: `res.company`, `resource.calendar.leaves`

### `l10n.bg.generate.holidays.wizard` <a id='model-l10n-bg-generate-holidays-wizard'></a>
Python class `GenerateBgHolidaysWizard` in `wizards/generate_bg_holidays_wizard.py:6`.  TransientModel (wizard).  Description: *Generate Bulgarian Public Holidays*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `year` | Integer |  | ✓ | ✓ | Calendar year to generate the official Bulgarian public holidays for. Fixed date |
| `company_id` | Many2one → \`res.company\` |  | ✓ | ✓ | Company whose working calendar receives the holidays. |

#### Notable methods

- **`action_generate(self)`** — decorators: —


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments — rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/res_company.py`

- **`BG_FIXED_HOLIDAYS`** *(collection)* = `[(1, 1, "New Year's Day"), (3, 3, 'Liberation Day'), (5, 1, 'Labour Day'), (5, 6, "St. George's Day / Day of Valour"), (5, 24, 'Day of Bulgarian Education and Culture'), (9, 6, 'Unification Day'), (9, 22, 'Independence Day'), (12, 24, 'Chri  # ...truncated`  — line 15


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestBgPublicHolidays.setUpClass(cls)`** (`@classmethod`) — `tests/test_public_holidays.py:14`
  - calls `super()`
  - touches: `resource.calendar`
- **`TestBgPublicHolidays.test_seeded_legal_rates(self)`** — `tests/test_public_holidays.py:22`
  - КТ чл. 262 multipliers are seeded and resolvable.
  - touches: `hr.legal.rate`
- **`TestBgPublicHolidays.test_night_supplement_dated_at_2026(self)`** — `tests/test_public_holidays.py:31`
  - Night supplement only effective from euro adoption (2026-01-01).
  - touches: `hr.legal.rate`
- **`TestBgPublicHolidays.test_generates_fixed_and_moving_holidays(self)`** — `tests/test_public_holidays.py:37`
  - Fixed dates + Orthodox-Easter cluster created as global leaves.
- **`TestBgPublicHolidays.test_generation_is_idempotent(self)`** — `tests/test_public_holidays.py:54`
  - Re-running the same year creates nothing new.
- **`TestBgPublicHolidays.test_easter_differs_by_year(self)`** — `tests/test_public_holidays.py:61`
  - Moving cluster tracks the year (regression vs hardcoded dates).


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `generate_bg_holidays_wizard_form` | `l10n.bg.generate.holidays.wizard` | — |  | `views/hr_public_holidays_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_l10n_bg_generate_holidays_wizard` | `model_l10n_bg_generate_holidays_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`ir_cron_generate_bg_public_holidays`** (Bulgaria: Generate next year's public holidays) on `base.model_res_company`, runs every 1 months, active=True

### Data records summary

- `hr.legal.rate`: 4 record(s)
- `ir.cron`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>

No images, diagrams or screenshots are shipped with this module.


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `gotchas` (6)

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `<p>, help=`

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: **Search view: `<group>` без атрибути** — `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** — `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

#### Gotcha: **`mail.template.body_html` се рендира с QWeb (`<t t-out>`), НЕ с inli
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`mail.template.body_html` се рендира с QWeb (`<t t-out>`), НЕ с inline `{{ }}`.** Полето е `fields.Html(render_engine='qweb')`. Само КЪСИТЕ полета (`subject`, `email_from`, `email_to`, `reply_to`, `scheduled_date`) ползват `inline_template` engine-а с `{{ expr }}`. Ако напишеш body с `{{ object.number }}`, placeholder-ите се пращат **буквално** в имейла (получателят вижда `{{ object.number }}`), а evaluation никога не става → латентните грешки в израза (несъществуващо поле/метод) не се виждат докато не мигрираш на t-out и QWeb не ги валидира при write. Canonical: helpdesk_mgmt/data templates ползват `<t t-out="object.X"/>`. Поправка на съществуващи `noupdate="1"` templates → migration който презаписва body-то per-lang. **Как се хваща**: рендирай `template._render_field('body_html', ids)[id]` в тест и assert `'{{' not in body`.

Matched tokens: `noupdate="1"`

#### Gotcha: **Correlation/round-trip ключ между две инстанции трябва да е със същи
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **Correlation/round-trip ключ между две инстанции трябва да е със същия ТИП от двете страни.** Ако модул А праща `local_id = record.number` (Char стринг "PST-00076") в маркер/payload, а модул Б го чете в `fields.Integer` с `int(local_id)` → `ValueError` на първия реален номер. Маскира се ако тестовете подават числов fixture (`42`) вместо реалния формат. **Винаги** тествай correlation с реалния номеров формат (prefix+padding), не с гол integer. При несъответствие — изравни типа (обикновено Char, защото човешкият номер е стринг), не cast-вай.

Matched tokens: `fields.integer`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `type="object"`


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/l10n_bg_hr_attendance_overtime_rates`
- Source digest: `sha256:73c06219d3138dbb79864df737a40919973cab9ad0be2eb7becdd10a09b86c98`
- Generated at: `2026-06-03T08:31:34+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
