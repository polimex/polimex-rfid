---
id: hr_rfid_old_cloud_import
title: RFID Polimex Old Cloud Import
module: hr_rfid_old_cloud_import
module_version: 19.0.1.2.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import access control data from my.polimex.online and schoolsafety.online
last_updated: '2026-05-14'
source_digest: sha256:61c60e35dab22043928dd3d728caa520f35f9ff7d7ce1688e1497337f988d006
depends:
- hr_rfid
entities:
  primary: hr.rfid.old.cloud.import.users
  related:
  - hr.rfid.old.cloud.import.wiz
  - hr.rfid.old.cloud.welcome.wiz
keywords:
- access
- cloud
- control
- data
- from
- import
- old
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
  models: 3
  views: 2
  access_rules: 3
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:af1063114ca00caeeb3c4d493fdc857f1bebf4372820ea6f85e40cd38d3f0906
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:17acc060e223dfc0753b4bd6d4fedf1e7871b7a63fda9ee5a7223768fcc4eb84
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Polimex Old Cloud Import — `hr_rfid_old_cloud_import` v19.0.1.2.0

Import access control data from my.polimex.online and schoolsafety.online

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_old_cloud_import`
- **Version**: `19.0.1.2.0`
- **Category**: HR
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`

### README (verbatim)

#### Introduction
This module extends the RFID Access Control (hr_rfid) module, allowing it to import user data from Cloud based Access Control System by Polimex

https://my.polimex.online

https://schoolsafety.online

#### Features
* Import all Controllers and modules.
* Import all Users and cards.
* Import All Access Control Groups.
* Import all Access Users Rights.
* Import all User Events.

#### Requirements

* No

```console

```


* PIP envirement

```code

```

* Token from old account


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_old_cloud_import --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.old.cloud.import.users` <a id='model-hr-rfid-old-cloud-import-users'></a>
Python class `OldCloudImportusers` in `models/import_wizard.py:13`.  TransientModel (wizard).  Description: *Old Cloud Import Users*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `do_import` | Boolean |  |  | ✓ | Tick the user to include them in the import run. Auto-set to True when you chang |
| `import_as` | Selection |  |  | ✓ | Whether this particular user becomes an hr.employee or a res.partner in Odoo. De |
| `u_id` | Integer | Internal ID |  | ✓ | Numeric user ID in the source cloud. Used as the dedup key during import. |
| `u_code` | Char | User code |  | ✓ | External / facility user code from the source cloud (often the RFID card number) |
| `u_name` | Char | User name |  | ✓ | Display name as stored in the source cloud — used as Odoo record name when the s |
| `u_fname` | Char | First Name |  | ✓ | First name field from the source cloud. Maps to res.partner.firstname / hr.emplo |
| `u_sname` | Char | Second Name |  | ✓ | Middle / second name field from the source cloud. |
| `u_lname` | Char | Last Name |  | ✓ | Last name / surname field from the source cloud. |
| `d_id` | Integer | Department ID |  | ✓ | Numeric department ID from the source cloud. Translated to a local hr.department |
| `d_name` | Char | Department Name |  | ✓ | Department display name from the source cloud — shown here for human cross-check |
| `c_id` | Integer | Company ID |  | ✓ | Numeric company ID from the source cloud. Translated to a local res.company via  |
| `c_name` | Char | Company Name |  | ✓ | Company display name from the source cloud — shown here for human cross-check. |
| `json_data` | Char | Json Data |  | ✓ | Full raw JSON record from the source cloud, kept for audit and for replay if the |
| `import_id` | Many2one → \`hr.rfid.old.cloud.import.wiz\` |  |  | ✓ | Parent import-run wizard this user row belongs to. Set automatically when the wi |

#### Notable methods

- **`get_full_name(self)`** — decorators: —
- **`get_record_for_note(self)`** — decorators: —
- **`import_row(self)`** — decorators: —

### `hr.rfid.old.cloud.import.wiz` <a id='model-hr-rfid-old-cloud-import-wiz'></a>
Python class `OldCloudImportWiz` in `models/import_wizard.py:93`.  TransientModel (wizard).  Inherits: `hr.rfid.old.cloud.welcome.wiz`, `balloon.mixin`.  Description: *Import*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `default_department` | Many2one → \`hr.department\` |  |  | ✓ | Use this department if Employee have no Company and Department |
| `force_default_department` | Boolean |  |  | ✓ | Force use only this department for selected import |
| `default_company` | Many2one → \`res.partner\` |  |  | ✓ | Use this company if Contact have no Company and Department |
| `force_default_company` | Boolean |  |  | ✓ | Force use only this company for selected import |
| `users_ids` | One2many → \`hr.rfid.old.cloud.import.users\` |  |  | ✓ | Users discovered in the source cloud. Operator picks per-row which ones to impor |
| `import_as` | Selection |  |  | ✓ | Bulk-applied default for the per-row Import As column. Changing this rewrites ev |
| `select_all` | Boolean |  |  | ✓ | Master toggle that ticks/un-ticks the do_import flag on every users_ids row. |
| `user_data` | Char |  |  | ✓ | Raw payload received from the source cloud's user list endpoint, kept for diagno |

#### Notable methods

- **`go_back(self)`** — decorators: —
- **`default_get(self, fields_list)`** — decorators: `@api.model`
  - super-split (super `default_get`): pre=— · post=`sudo`
  - effects: `sudo`
  - touches: `hr.rfid.old.cloud.import.users`, `ir.model.data`
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

### `hr.rfid.old.cloud.welcome.wiz` <a id='model-hr-rfid-old-cloud-welcome-wiz'></a>
Python class `OldCloudWelcomeWiz` in `models/welcome_wizard.py:11`.  TransientModel (wizard).  Description: *Old Polimex Cloud Import Welcome*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `url_domain` | Selection |  |  | ✓ | Which legacy cloud to import from — the public Polimex cloud or the School Safet |
| `url_token` | Char | Access token | ✓ | ✓ | Bearer token that authenticates this Odoo instance with the legacy cloud's REST  |
| `users_count` | Integer |  |  | ✓ | Number of users discovered in the source cloud after Test Connection — informati |
| `company_dict` | Char |  |  | ✓ | Internal mapping JSON (source-cloud company ID → local res.company ID) cached af |
| `ag_dict` | Char |  |  | ✓ | Internal mapping JSON (source-cloud access-group ID → local hr.rfid.access.group |
| `connection_checked` | Boolean |  |  | ✓ | True after Test Connection succeeded and the mapping dictionaries are populated. |
| `default_import_as` | Selection |  |  | ✓ | How users from the source cloud become Odoo records — Employees: imported into h |
| `import_hardware` | Boolean |  |  | ✓ | Include webstacks, controllers, doors and readers in the import. |
| `import_access_groups` | Boolean |  |  | ✓ | Include access groups and their door bindings in the import. |
| `import_users` | Boolean |  |  | ✓ | Include users (employees or contacts depending on Default Import As) and their c |
| `import_events` | Boolean |  |  | ✓ | Include the historical access-event log. May be large — disable for a faster fir |

#### Notable methods

- **`do_check_connection(self)`** — decorators: —
  - effects: `log_warn`, `raise:ValidationError`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestOldCloudImportSmoke.test_welcome_wizard_create(self)`** — `tests/test_smoke.py:9`
  - touches: `hr.rfid.old.cloud.welcome.wiz`
- **`TestOldCloudImportSmoke.test_import_wiz_model_is_registered(self)`** — `tests/test_smoke.py:13`
  - touches: `hr.rfid.old.cloud.import.wiz`
- **`TestOldCloudImportSmoke.test_import_user_get_full_name(self)`** — `tests/test_smoke.py:17`
  - touches: `hr.rfid.old.cloud.import.users`
- **`TestOldCloudImportSmoke.test_import_user_get_record_for_note(self)`** — `tests/test_smoke.py:31`
  - touches: `hr.rfid.old.cloud.import.users`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `old_cloud_import_wizard_form` | `hr.rfid.old.cloud.import.wiz` | — |  | `views/import_wizard.xml` |
| `old_cloud_welcome_wizard_form` | `hr.rfid.old.cloud.welcome.wiz` | — |  | `views/welcome_wizard.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_old_cloud_welcome_wiz` | `model_hr_rfid_old_cloud_welcome_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_old_cloud_import_wiz` | `model_hr_rfid_old_cloud_import_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_old_cloud_import_users` | `model_hr_rfid_old_cloud_import_users` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |


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

Matched tokens: `<p>, ir.model.data, help=`

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `@api.onchange, api.onchange`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `res_id, type="object"`

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


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_old_cloud_import`
- Source digest: `sha256:61c60e35dab22043928dd3d728caa520f35f9ff7d7ce1688e1497337f988d006`
- Generated at: `2026-05-14T11:16:45+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
