---
id: hr_rfid_old_cloud_import
title: RFID Polimex Old Cloud Import
module: hr_rfid_old_cloud_import
module_version: 19.0.1.3.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import access control data from my.polimex.online and schoolsafety.online
last_updated: '2026-11-23'
source_digest: sha256:fe1f4b4cba2c05b127016658ea8bee28d3bfad698d411f62d6ef6b71c6af96ec
depends:
- hr_rfid
entities:
  primary: hr.rfid.old.cloud.import.wiz
  related:
  - hr.rfid.old.cloud.import.users
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


# RFID Polimex Old Cloud Import - `hr_rfid_old_cloud_import` v19.0.1.3.0

Import access control data from my.polimex.online and schoolsafety.online

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_old_cloud_import`
- **Version**: `19.0.1.3.0`
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

#### Running the import again

The import can be run as often as you like. Everything it creates is marked
with the cloud record it came from, so a later run finds that work instead of
doing it a second time:

- Somebody already imported is not offered in the list again.
- A customer, a department, a person or a card that is already here is used as
  it is - no second copy is made.
- An access group somebody already has is not given to them again.

The two clouds are kept apart, so the same record number on
my.polimex.online and on schoolsafety.online is never taken for the same
person. Nothing is deleted, and nothing already corrected here is overwritten.

**One thing to check first.** Databases filled by a version of this import from
before August 2026 were marked in a different way, which the current version
does not read. On such a database the people imported back then are offered
again and would come in as new records. If you are not sure which case you are
in, import one person first and see whether a second copy appears before doing
the rest.

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
Python class `OldCloudImportusers` in `models/import_wizard.py:38`.  TransientModel (wizard).  Description: *Old Cloud Import Users*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `do_import` | Boolean | Do Import |  | ✓ | Tick the user to include them in the import run. Auto-set to True when you chang |
| `import_as` | Selection | Import As |  | ✓ | Whether this particular user becomes an hr.employee or a res.partner in Odoo. De |
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
| `import_id` | Many2one → \`hr.rfid.old.cloud.import.wiz\` | Import |  | ✓ | Parent import-run wizard this user row belongs to. Set automatically when the wi |

#### Notable methods

- **`get_full_name(self)`** - decorators: -
- **`get_record_for_note(self)`** - decorators: -
- **`import_row(self)`** - decorators: -
  - effects: `log_debug`

### `hr.rfid.old.cloud.import.wiz` <a id='model-hr-rfid-old-cloud-import-wiz'></a>
Python class `OldCloudImportWiz` in `models/import_wizard.py:119`.  TransientModel (wizard).  Inherits: `hr.rfid.old.cloud.welcome.wiz`, `balloon.mixin`.  Description: *Import*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `default_department` | Many2one → \`hr.department\` | Default Department |  | ✓ | Use this department if Employee have no Company and Department |
| `force_default_department` | Boolean | Force Default Department |  | ✓ | Force use only this department for selected import |
| `default_company` | Many2one → \`res.partner\` | Default Company |  | ✓ | Use this company if Contact have no Company and Department |
| `force_default_company` | Boolean | Force Default Company |  | ✓ | Force use only this company for selected import |
| `users_ids` | One2many → \`hr.rfid.old.cloud.import.users\` | Users |  | ✓ | Users discovered in the source cloud. Operator picks per-row which ones to impor |
| `import_as` | Selection | Import As |  | ✓ | Bulk-applied default for the per-row Import As column. Changing this rewrites ev |
| `select_all` | Boolean | Select All |  | ✓ | Master toggle that ticks/un-ticks the do_import flag on every users_ids row. |
| `user_data` | Char | User Data |  | ✓ | Raw payload received from the source cloud's user list endpoint, kept for diagno |

#### Notable methods

- **`go_back(self)`** - decorators: -
- **`default_get(self, fields_list)`** - decorators: `@api.model`
  - calls `super() `default_get``
  - touches: `hr.rfid.old.cloud.import.users`
- **`get_context_list(self, field)`** - decorators: `@api.model`
- **`get_user_data_as_dict(self, u_data, import_id, import_as)`** - decorators: `@api.model`
- **`create_res_partner_company(self, user_id)`** - decorators: -
  - effects: `message_post`, `with_context`
  - touches: `res.partner`
- **`create_res_partner(self, user_id)`** - decorators: -
  - effects: `create`, `message_post`, `with_context`
  - touches: `res.partner`
- **`create_department(self, d_id, d_name)`** - decorators: -
  - effects: `message_post`, `with_context`
  - touches: `hr.department`
- **`create_employee(self, user_id, department_id)`** - decorators: -
  - effects: `message_post`, `with_context`
  - touches: `hr.employee`
- **`create_tags(self, user_id, employee_id=None, partner_id=None)`** - decorators: -
  - effects: `message_post`, `raise:ValidationError`, `with_context`
  - touches: `hr.rfid.card`
- **`create_user_ag_relation(self, user_id, employee_id=None, partner_id=None)`** - decorators: -
  - effects: `log_info`, `raise:ValidationError`
- **`do_import_user_as_employee(self, user_id)`** - decorators: -
  - effects: `create`
- **`do_import_user_as_contact(self, user_id)`** - decorators: -
  - effects: `create`
- **`import_ags(self)`** - decorators: -
  - effects: `message_post`, `with_context`
  - touches: `hr.rfid.access.group`
- **`import_u(self, selected=False)`** - decorators: -
  - effects: `log_info`
- **`do_import(self)`** - decorators: -

### `hr.rfid.old.cloud.welcome.wiz` <a id='model-hr-rfid-old-cloud-welcome-wiz'></a>
Python class `OldCloudWelcomeWiz` in `models/welcome_wizard.py:11`.  TransientModel (wizard).  Description: *Old Polimex Cloud Import Welcome*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `url_domain` | Selection | Url Domain |  | ✓ | Which legacy cloud to import from — the public Polimex cloud or the School Safet |
| `url_token` | Char | Access token | ✓ | ✓ | Bearer token that authenticates this Odoo instance with the legacy cloud's REST  |
| `users_count` | Integer | Users Count |  | ✓ | Number of users discovered in the source cloud after Test Connection — informati |
| `company_dict` | Char | Company Dict |  | ✓ | Internal mapping JSON (source-cloud company ID → local res.company ID) cached af |
| `ag_dict` | Char | Ag Dict |  | ✓ | Internal mapping JSON (source-cloud access-group ID → local hr.rfid.access.group |
| `connection_checked` | Boolean | Connection Checked |  | ✓ | True after Test Connection succeeded and the mapping dictionaries are populated. |
| `default_import_as` | Selection | Default Import As |  | ✓ | How users from the source cloud become Odoo records — Employees: imported into h |
| `import_hardware` | Boolean | Import Hardware |  | ✓ | Include webstacks, controllers, doors and readers in the import. |
| `import_access_groups` | Boolean | Import Access Groups |  | ✓ | Include access groups and their door bindings in the import. |
| `import_users` | Boolean | Import Users |  | ✓ | Include users (employees or contacts depending on Default Import As) and their c |
| `import_events` | Boolean | Import Events |  | ✓ | Include the historical access-event log. May be large — disable for a faster fir |

#### Notable methods

- **`do_check_connection(self)`** - decorators: -
  - effects: `log_warn`, `raise:ValidationError`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/import_wizard.py`

- **`LEDGER_MODULE`** *(scalar)* = `'__import__'`  - line 16
- **`SOURCE_SLUG_BY_DOMAIN`** *(collection)* = `{'pc': 'old_cloud_pc', 'ss': 'old_cloud_ss'}`  - line 21
- **`DEFAULT_SOURCE_DOMAIN`** *(scalar)* = `'pc'`  - line 25
- **`SRC_USER`** *(scalar)* = `'u'`  - line 29
- **`SRC_COMPANY`** *(scalar)* = `'c'`  - line 30
- **`SRC_DEPARTMENT`** *(scalar)* = `'d'`  - line 31
- **`SRC_ACCESS_GROUP`** *(scalar)* = `'ag'`  - line 32
- **`SRC_TAG`** *(scalar)* = `'tag'`  - line 33
- **`SRC_AG_USER`** *(scalar)* = `'agu'`  - line 34
- **`SRC_PLACEHOLDER_AG`** *(scalar)* = `'placeholder'`  - line 35


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `old_cloud_import_wizard_form` | `hr.rfid.old.cloud.import.wiz` | - |  | `views/import_wizard.xml` |
| `old_cloud_welcome_wizard_form` | `hr.rfid.old.cloud.welcome.wiz` | - |  | `views/welcome_wizard.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_old_cloud_welcome_wiz` | `model_hr_rfid_old_cloud_welcome_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_old_cloud_import_wiz` | `model_hr_rfid_old_cloud_import_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_old_cloud_import_users` | `model_hr_rfid_old_cloud_import_users` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `ir.actions.act_window`: 2 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>

### Curated (docs/faq.md)

##### How an imported record is recognised again

Every record this wizard creates is registered in Odoo's own external-ID
metadata (`ir.model.data`), against the cloud record it came from. That register
is what makes a second run find the first run's work instead of creating it
again - identity is the SOURCE ID, never a name, a code or a card number.

###### The name

```
__import__.rfid_import_{old_cloud_pc|old_cloud_ss}_{target_model}_{source_table}_{source_id}
```

built by `_xml_id_name(model, source_ref)`; `source_ref` is
`{SRC_*}_{cloud id}`. The target model is part of the name because one cloud
holder can land as BOTH an `hr.employee` and a `res.partner`, and both have to
be recognised separately. The cloud is part of it because the two clouds number
their records independently - `tests/test_import_idempotency.py::test_the_two_clouds_never_share_an_external_id`
pins exactly that.

###### Helpers on `hr.rfid.old.cloud.import.wiz`

| Method | Does |
|---|---|
| `_source_slug()` | The identity of the cloud this run reads, from `url_domain` through `SOURCE_SLUG_BY_DOMAIN`. |
| `_xml_id_name(model, source_ref)` / `_xml_id(model, source_ref)` | The name, and the full external ID. |
| `_find_imported(model, source_ref)` | The record an earlier run created for this source record, or an empty recordset. `env.ref(..., raise_if_not_found=False)` - which is NOT filtered by `active`, so an archived record is still recognised. |
| `_mark_imported(record, source_ref)` | Registers a freshly created record. Called on EVERY create path: customer, contact, department, employee, card, placeholder access group, access-group membership. |
| `_already_imported_user_ids()` | The cloud user ids an earlier run brought in, so they are not offered for import again. Looks under both `hr.employee` and `res.partner` prefixes; the `SRC_USER` token keeps customers (also `res.partner`) out. |

###### Memberships have TWO guards

`_add_ag_membership` skips a membership when its external ID exists **or** when
the (person, access group) pair is already there. The second guard is not
redundant: memberships created before this module wrote external IDs at all
carry nothing that says they came from here, and without it the first run after
the change would duplicate every one of them.

###### Records marked by an earlier version

Versions before 19.0.1.2.0 registered their work under `__export__` with names
like `old_cloud_u_id_7`. Those names are NOT read any more, and there is no
conversion step: on a database imported with an older version, the holders
concerned are offered again and accepted as new. A site in that position should
be checked before a repeat import is run.

###### Tests

`tests/test_import_idempotency.py` - a second run creates no second employee or
contact, gives no access group twice (by external ID, and by the pair guard for
memberships that predate it), reuses the placeholder group, keeps one badge as
one card, leaves a door with exactly one way in, does not hand a visitor the
same badge twice, and keeps the two clouds apart. The cloud HTTP calls are
patched out, so nothing goes to the network.

##### What the constants of the import mean

- **`LEDGER_MODULE`** = `'__import__'` - the `ir.model.data` module every record
  created here is registered under. It is what core's own `BaseModel.load()`
  writes for imported rows, so a second run recognises the first run's work
  exactly the way core would.
- **`SOURCE_SLUG_BY_DOMAIN`** = `{'pc': 'old_cloud_pc', 'ss': 'old_cloud_ss'}`,
  **`DEFAULT_SOURCE_DOMAIN`** = `'pc'` - the source identity inside the external
  ID. The two legacy clouds (my.polimex.online and schoolsafety.online) are
  separate installations with their own record numbering, so each gets its own
  slug and holder 7 on one is never taken for holder 7 on the other. An
  unrecognised domain falls back to `old_cloud_{domain}`.
- **`SRC_USER`/`SRC_COMPANY`/`SRC_DEPARTMENT`/`SRC_ACCESS_GROUP`/`SRC_TAG`/`SRC_AG_USER`/`SRC_PLACEHOLDER_AG`**
  = `'u'`/`'c'`/`'d'`/`'ag'`/`'tag'`/`'agu'`/`'placeholder'` - source TABLE
  tokens. Holders and customers both land in `res.partner`, so the reference has
  to say which of them an id came from.
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (2)

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [FIX] hr_rfid_old_cloud_import: smoke test must supply url_token now

Commit `f2078ff86c` (2026-05-14): [FIX] hr_rfid_old_cloud_import: smoke test must supply url_token now


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_old_cloud_import`
- Source digest: `sha256:fe1f4b4cba2c05b127016658ea8bee28d3bfad698d411f62d6ef6b71c6af96ec`
- Generated at: `2026-11-23T10:04:46+00:00`
- Generator: `polimex_module_knowledge`
