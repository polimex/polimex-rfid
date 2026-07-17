---
id: hr_rfid_andromeda_import
title: RFID Andromeda Data Import
module: hr_rfid_andromeda_import
module_version: 19.0.1.3.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import access control data from Polimex Andromeda Database
last_updated: '2026-05-14'
source_digest: sha256:9a0e8b6e25c272594255feed587e0df8df2ebd5e5e4c2dfe30478ad01813c719
depends:
- hr_rfid
entities:
  primary: hr.rfid.andromeda.instance
  related:
  - hr.rfid.andromeda.import.users
  - hr.rfid.andromeda.import.wiz
  - hr.rfid.andromeda.welcome.wiz
keywords:
- access
- andromeda
- control
- data
- database
- from
- import
- instance
- polimex
- rfid
- users
- welcome
- wiz
license: AGPL-3
author: Polimex
category: HR
installable: true
application: false
auto_install: false
counts:
  models: 4
  views: 2
  access_rules: 3
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:a56372719a66ebe603a8e4d1a1a9ed222c0402facb3ef699d4e24c1803c75417
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:1680b394031a0ad50145c508a550033e95a588c01d5422cacaf0484156944d66
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Andromeda Data Import — `hr_rfid_andromeda_import` v19.0.1.3.0

Import access control data from Polimex Andromeda Database

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_andromeda_import`
- **Version**: `19.0.1.3.0`
- **Category**: HR
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`
- **External python**: `fdb`

### README (verbatim)

#### Introduction
This module extends the RFID Access Control (hr_rfid) module, allowing it to import user data from Windows based Andromeda Access Control System by Polimex

#### Features
* Import all Users and cards.
* Import All Access Control Groups.
* Import all Access Users Rights.

#### Requirements

* System packs

```console
sudo apt install libfbclient2
```


* PIP envirement

```code
pip install fdb
```


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_andromeda_import --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.andromeda.instance` <a id='model-hr-rfid-andromeda-instance'></a>
Python class `AndromedaWelcomeWiz` in `models/andromeda_instance.py:11`.  Model.  Description: *Andromeda Instance for import*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ip_address` | Char | IP address | ✓ | ✓ | IP address of the Windows host running the Andromeda Firebird DB engine. |
| `database_path` | Char | Database Path | ✓ | ✓ | Absolute path to the Andromeda.fdb file as seen by the Firebird server on the Wi |
| `users_count` | Integer |  |  | ✓ | Number of users last reported by the Andromeda database. Populated by Check Conn |
| `state` | Selection | State |  | ✓ | Lifecycle of this Andromeda connection record — New: not yet probed. Confirmed:  |

#### Notable methods

- **`do_check_connection(self)`** — decorators: —
  - effects: `log_warn`, `raise:ValidationError`

### `hr.rfid.andromeda.import.users` <a id='model-hr-rfid-andromeda-import-users'></a>
Python class `AndromedaImportusers` in `models/import_wizard.py:22`.  TransientModel (wizard).  Description: *Andromeda Import Users*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `do_import` | Boolean | Import This User |  | ✓ | Select whether to import this specific user.                  • When enabled: Us |
| `import_as` | Selection | Import As |  | ✓ | Choose how to import this user into Odoo.                  • Contact: Creates a  |
| `u_id` | Integer | Internal ID |  | ✓ | Unique user identifier from Andromeda system.                  • Source: Androme |
| `u_code` | Char | User Code |  | ✓ | User identification code from Andromeda system.                  • Usage: Employ |
| `u_name` | Char | Username |  | ✓ | Username from Andromeda access control system.                  • Login: Origina |
| `u_fname` | Char | First Name |  | ✓ | First name field from the Andromeda DB. Maps to the Odoo record's structured nam |
| `u_sname` | Char | Second Name |  | ✓ | Middle / second name from the Andromeda DB. |
| `u_lname` | Char | Last Name |  | ✓ | Last name from the Andromeda DB. |
| `d_id` | Integer | Department ID |  | ✓ | Numeric department ID from Andromeda. Translated to a local hr.department throug |
| `d_name` | Char | Department Name |  | ✓ | Department display name from Andromeda — shown for human cross-check. |
| `c_id` | Integer | Company ID |  | ✓ | Numeric company ID from Andromeda. Translated to a local res.company via company |
| `c_name` | Char | Company Name |  | ✓ | Company display name from Andromeda — shown for human cross-check. |
| `import_id` | Many2one → \`hr.rfid.andromeda.import.wiz\` |  |  | ✓ | Parent import-run wizard this user row belongs to. Set automatically when the wi |

#### Notable methods

- **`get_full_name(self)`** — decorators: —
- **`get_record_for_note(self)`** — decorators: —
- **`import_row(self)`** — decorators: —

### `hr.rfid.andromeda.import.wiz` <a id='model-hr-rfid-andromeda-import-wiz'></a>
Python class `AndromedaImportWiz` in `models/import_wizard.py:125`.  TransientModel (wizard).  Inherits: `hr.rfid.andromeda.welcome.wiz`.  Description: *Import*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `company_list` | Selection |  |  | ✓ |  |
| `default_department` | Many2one → \`hr.department\` |  |  | ✓ | Use this department if Employee have no Company and Department |
| `force_default_department` | Boolean |  |  | ✓ | Force use only this department for selected import |
| `default_company` | Many2one → \`res.partner\` |  |  | ✓ | Use this company if Contact have no Company and Department |
| `force_default_company` | Boolean |  |  | ✓ | Force use only this company for selected import |
| `users_ids` | One2many → \`hr.rfid.andromeda.import.users\` |  |  | ✓ | Users discovered in the Andromeda DB. Operator picks per-row which ones to impor |
| `import_as` | Selection |  |  | ✓ | Bulk-applied default for the per-row Import As column. Changing this rewrites ev |
| `select_all` | Boolean |  |  | ✓ | Master toggle that ticks/un-ticks the do_import flag on every users_ids row. |

#### Notable methods

- **`go_back(self)`** — decorators: —
- **`default_get(self, fields_list)`** — decorators: `@api.model`
  - super-split (super `default_get`): pre=— · post=`sudo`
  - effects: `sudo`
  - touches: `hr.rfid.andromeda.import.users`, `ir.model.data`
- **`get_context_list(self, field)`** — decorators: `@api.model`
- **`get_user_data_as_dict(self, u_data, import_id, import_as)`** — decorators: `@api.model`
- **`create_res_partner_company(self, user_id)`** — decorators: —
  - effects: `message_post`, `sudo`, `with_context`
  - touches: `ir.model.data`, `res.partner`
- **`create_res_partner(self, user_id)`** — decorators: —
  - effects: `create`, `message_post`, `sudo`, `with_context`
  - touches: `ir.model.data`, `res.partner`
- **`create_department(self, d_id, d_name)`** — decorators: —
  - effects: `message_post`, `sudo`, `with_context`
  - touches: `hr.department`, `ir.model.data`
- **`create_employee(self, user_id, department_id)`** — decorators: —
  - effects: `message_post`, `sudo`, `with_context`
  - touches: `hr.employee`, `ir.model.data`
- **`create_tags(self, user_id, employee_id=None, partner_id=None)`** — decorators: —
  - effects: `message_post`, `raise:ValidationError`, `sudo`, `with_context`
  - touches: `hr.rfid.card`, `ir.model.data`
- **`create_user_ag_relation(self, user_id, employee_id=None, partner_id=None)`** — decorators: —
  - effects: `log_info`, `raise:ValidationError`
  - touches: `hr.rfid.access.group`
- **`do_import_user_as_employee(self, user_id)`** — decorators: —
  - effects: `create`
- **`do_import_user_as_contact(self, user_id)`** — decorators: —
  - effects: `create`
- **`import_ags(self)`** — decorators: —
  - effects: `message_post`, `sudo`, `with_context`
  - touches: `hr.rfid.access.group`, `ir.model.data`
- **`import_u(self, selected=False)`** — decorators: —
  - effects: `log_info`
- **`do_import(self)`** — decorators: —
- **`do_fb_sql_context(self, sql)`** — decorators: `@api.model`
  - effects: `log_warn`, `raise:ValidationError`

### `hr.rfid.andromeda.welcome.wiz` <a id='model-hr-rfid-andromeda-welcome-wiz'></a>
Python class `AndromedaWelcomeWiz` in `models/welcome_wizard.py:11`.  TransientModel (wizard).  Description: *Andromeda Import Welcome*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ip_address` | Char | IP address | ✓ | ✓ | IP address of the Windows host running the Andromeda Firebird DB engine. Reachab |
| `database_path` | Char | Database Path | ✓ | ✓ | Absolute path to the Andromeda.fdb file as seen by the Firebird server (Windows  |
| `users_count` | Integer |  |  | ✓ | Number of users discovered in the Andromeda DB after Test Connection — informati |
| `company_dict` | Char |  |  | ✓ | Internal JSON mapping (Andromeda company ID → Odoo res.company ID) populated aft |
| `ag_dict` | Char |  |  | ✓ | Internal JSON mapping (Andromeda access group → Odoo hr.rfid.access.group) popul |
| `connection_checked` | Boolean |  |  | ✓ | True after a successful Firebird login and structural probe. Gates the Import bu |
| `default_import_as` | Selection |  |  | ✓ | Where Andromeda users land in Odoo by default — hr.employee for staff, res.partn |
| `import_access_groups` | Boolean |  |  | ✓ | Include Andromeda access groups and their door bindings in the import. |
| `import_users` | Boolean |  |  | ✓ | Include Andromeda users (with cards) in the import. Disable to import only struc |

#### Notable methods

- **`do_check_connection(self)`** — decorators: —
  - effects: `log_warn`, `raise:ValidationError`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments — rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/import_wizard.py`

- **`USERS_SQL`** *(scalar)* = `'select\n            u_id, U_CODE, u_name, u_fname, u_sname, u_lname,D_id, D_NAME, c_id, C_NAME\n            from USERS\n            left join USER_JOB UJ on USERS.U_ID = UJ.USERS_U_ID\n            left join COMPANY C on UJ.COMPANY_C_ID = C`  — line 11
- **`AG_USER_SQL`** *(scalar)* = `'select users_u_id, access_groups_ag_id, agu_start_timestamp,\n            agu_expire_timestamp, agu_active from AG_USERS\n            where agu_active=1 and USERS_U_ID=%d'`  — line 18


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestAndromedaImportWizard.setUpClass(cls)`** (`@classmethod`) — `tests/test_import_wizard.py:17`
  - calls `super()`
  - touches: `hr.rfid.andromeda.import.users`
- **`TestAndromedaImportWizard.test_create_res_partner_company_creates_record(self)`** — `tests/test_import_wizard.py:44`
- **`TestAndromedaImportWizard.test_create_res_partner_company_is_idempotent(self)`** — `tests/test_import_wizard.py:51`
- **`TestAndromedaImportWizard.test_create_department_creates_record(self)`** — `tests/test_import_wizard.py:60`
- **`TestAndromedaImportWizard.test_create_department_is_idempotent(self)`** — `tests/test_import_wizard.py:65`
- **`TestAndromedaImportWizard.test_create_employee_creates_record(self)`** — `tests/test_import_wizard.py:75`
- **`TestAndromedaImportWizard.test_create_employee_is_idempotent(self)`** — `tests/test_import_wizard.py:84`
- **`TestAndromedaImportWizard.test_create_res_partner_uses_default_company_when_forced(self)`** — `tests/test_import_wizard.py:91`
  - touches: `res.partner`

### Private helpers

- **`TestAndromedaImportWizard._fake_user(**overrides)`** (`@staticmethod`) — `tests/test_import_wizard.py:23`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `andromeda_import_wizard_form` | `hr.rfid.andromeda.import.wiz` | — |  | `views/import_wizard.xml` |
| `andromeda_welcome_wizard_form` | `hr.rfid.andromeda.welcome.wiz` | — |  | `views/welcome_wizard.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_andromeda_welcome_wiz` | `model_hr_rfid_andromeda_welcome_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_andromeda_import_wiz` | `model_hr_rfid_andromeda_import_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_andromeda_import_users` | `model_hr_rfid_andromeda_import_users` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |


## Data & Automation <a id='data'></a>

No XML data records or cron jobs are declared by this module.


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module. Captions generated by VLM; review before production.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>[Placeholder caption] Image at `icon.png`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>[Placeholder caption] Image at `icon.svg`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `gotchas` (7)

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `ir.model.data, <p>, help=`

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `api.onchange, @api.onchange`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `type="object", res_id`

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчита
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчитай на него за валидация

Matched tokens: `fields.char`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `validationerror`

#### Gotcha: **Search view: `<group>` без атрибути** — `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** — `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

### From `git_log` (3)

#### Fix: [FIX] hr_rfid_andromeda_import: drop @api.returns decorators (removed in
<!-- source: git_log ref: 5f1c3fa934519b81bff07b53099e297d7324b901 occ: 1 conf: 0.60 -->

Commit `5f1c3fa934` (2026-05-03): [FIX] hr_rfid_andromeda_import: drop @api.returns decorators (removed in v19)

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M
<!-- source: git_log ref: 3c84986ac48326833d2f41e4de1d121e3c526130 occ: 1 conf: 0.60 -->

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: fix from 14.0
<!-- source: git_log ref: 8a074b53884675ad0ff284f9880f2c2b29fc3e0e occ: 1 conf: 0.60 -->

Commit `8a074b5388` (2022-05-12): fix from 14.0


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_andromeda_import`
- Source digest: `sha256:9a0e8b6e25c272594255feed587e0df8df2ebd5e5e4c2dfe30478ad01813c719`
- Generated at: `2026-05-14T11:16:44+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
