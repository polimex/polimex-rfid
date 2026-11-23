---
id: hr_rfid_andromeda_import
title: RFID Andromeda Data Import
module: hr_rfid_andromeda_import
module_version: 19.0.1.4.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import access control data from Polimex Andromeda Database
last_updated: '2026-11-23'
source_digest: sha256:ac5bbfb25af5026261791ef3f8217541593c809ab2dc5a25a45738591a0c3a2f
depends:
- hr_rfid
entities:
  primary: hr.rfid.andromeda.import.wiz
  related:
  - hr.rfid.andromeda.import.users
  - hr.rfid.andromeda.welcome.wiz
keywords:
- access
- andromeda
- control
- data
- database
- from
- import
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
  models: 3
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


# RFID Andromeda Data Import - `hr_rfid_andromeda_import` v19.0.1.4.0

Import access control data from Polimex Andromeda Database

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_andromeda_import`
- **Version**: `19.0.1.4.0`
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

#### Running the import again

The import can be run as often as you like. Everything it creates is marked
with the Andromeda record it came from, so a later run finds that work instead
of doing it a second time:

- Somebody already imported is not offered in the list again.
- A company, a department, a person or a card that is already here is used as
  it is - no second copy is made.
- An access group somebody already has is not given to them again.
- A card that was switched off in Andromeda is not handed out again as a
  working one.

Nothing is deleted and nothing already corrected here is overwritten: a name
you have put right in Odoo stays as you left it.

**One thing to check first.** Databases filled by a version of this import from
before August 2026 were marked in a different way, which the current version
does not read. On such a database the people imported back then are offered
again and would come in as new records. If you are not sure which case you are
in, import one person first and see whether a second copy appears before doing
the rest.

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

### `hr.rfid.andromeda.import.users` <a id='model-hr-rfid-andromeda-import-users'></a>
Python class `AndromedaImportusers` in `models/import_wizard.py:45`.  TransientModel (wizard).  Description: *Andromeda Import Users*.

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
| `import_id` | Many2one → \`hr.rfid.andromeda.import.wiz\` | Import |  | ✓ | Parent import-run wizard this user row belongs to. Set automatically when the wi |

#### Notable methods

- **`get_full_name(self)`** - decorators: -
- **`get_record_for_note(self)`** - decorators: -
- **`import_row(self)`** - decorators: -
  - effects: `log_debug`

### `hr.rfid.andromeda.import.wiz` <a id='model-hr-rfid-andromeda-import-wiz'></a>
Python class `AndromedaImportWiz` in `models/import_wizard.py:149`.  TransientModel (wizard).  Inherits: `hr.rfid.andromeda.welcome.wiz`.  Description: *Import*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `company_list` | Selection | Company List |  | ✓ |  |
| `default_department` | Many2one → \`hr.department\` | Default Department |  | ✓ | Use this department if Employee have no Company and Department |
| `force_default_department` | Boolean | Force Default Department |  | ✓ | Force use only this department for selected import |
| `default_company` | Many2one → \`res.partner\` | Default Company |  | ✓ | Use this company if Contact have no Company and Department |
| `force_default_company` | Boolean | Force Default Company |  | ✓ | Force use only this company for selected import |
| `users_ids` | One2many → \`hr.rfid.andromeda.import.users\` | Users |  | ✓ | Users discovered in the Andromeda DB. Operator picks per-row which ones to impor |
| `import_as` | Selection | Import As |  | ✓ | Bulk-applied default for the per-row Import As column. Changing this rewrites ev |
| `select_all` | Boolean | Select All |  | ✓ | Master toggle that ticks/un-ticks the do_import flag on every users_ids row. |

#### Notable methods

- **`go_back(self)`** - decorators: -
- **`default_get(self, fields_list)`** - decorators: `@api.model`
  - calls `super() `default_get``
  - touches: `hr.rfid.andromeda.import.users`
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
- **`do_fb_sql_context(self, sql)`** - decorators: `@api.model`
  - effects: `log_warn`, `raise:ValidationError`

### `hr.rfid.andromeda.welcome.wiz` <a id='model-hr-rfid-andromeda-welcome-wiz'></a>
Python class `AndromedaWelcomeWiz` in `models/welcome_wizard.py:11`.  TransientModel (wizard).  Description: *Andromeda Import Welcome*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ip_address` | Char | IP address | ✓ | ✓ | IP address of the Windows host running the Andromeda Firebird DB engine. Reachab |
| `database_path` | Char | Database Path | ✓ | ✓ | Absolute path to the Andromeda.fdb file as seen by the Firebird server (Windows  |
| `users_count` | Integer | Users Count |  | ✓ | Number of users discovered in the Andromeda DB after Test Connection — informati |
| `company_dict` | Char | Company Dict |  | ✓ | Internal JSON mapping (Andromeda company ID → Odoo res.company ID) populated aft |
| `ag_dict` | Char | Ag Dict |  | ✓ | Internal JSON mapping (Andromeda access group → Odoo hr.rfid.access.group) popul |
| `connection_checked` | Boolean | Connection Checked |  | ✓ | True after a successful Firebird login and structural probe. Gates the Import bu |
| `default_import_as` | Selection | Default Import As |  | ✓ | Where Andromeda users land in Odoo by default — hr.employee for staff, res.partn |
| `import_access_groups` | Boolean | Import Access Groups |  | ✓ | Include Andromeda access groups and their door bindings in the import. |
| `import_users` | Boolean | Import Users |  | ✓ | Include Andromeda users (with cards) in the import. Disable to import only struc |

#### Notable methods

- **`do_check_connection(self)`** - decorators: -
  - effects: `log_warn`, `raise:ValidationError`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/import_wizard.py`

- **`USERS_SQL`** *(scalar)* = `'select\n            u_id, U_CODE, u_name, u_fname, u_sname, u_lname,D_id, D_NAME, c_id, C_NAME\n            from USERS\n            left join USER_JOB UJ on USERS.U_ID = UJ.USERS_U_ID\n            left join COMPANY C on UJ.COMPANY_C_ID = C`  - line 11
- **`AG_USER_SQL`** *(scalar)* = `'select users_u_id, access_groups_ag_id, agu_start_timestamp,\n            agu_expire_timestamp, agu_active from AG_USERS\n            where agu_active=1 and USERS_U_ID=%d'`  - line 18
- **`LEDGER_MODULE`** *(scalar)* = `'__import__'`  - line 26
- **`SOURCE_SLUG`** *(scalar)* = `'andromeda'`  - line 32
- **`SRC_USER`** *(scalar)* = `'u'`  - line 36
- **`SRC_COMPANY`** *(scalar)* = `'c'`  - line 37
- **`SRC_DEPARTMENT`** *(scalar)* = `'d'`  - line 38
- **`SRC_ACCESS_GROUP`** *(scalar)* = `'ag'`  - line 39
- **`SRC_TAG`** *(scalar)* = `'tag'`  - line 40
- **`SRC_AG_USER`** *(scalar)* = `'agu'`  - line 41
- **`SRC_PLACEHOLDER_AG`** *(scalar)* = `'placeholder'`  - line 42


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `andromeda_import_wizard_form` | `hr.rfid.andromeda.import.wiz` | - |  | `views/import_wizard.xml` |
| `andromeda_welcome_wizard_form` | `hr.rfid.andromeda.welcome.wiz` | - |  | `views/welcome_wizard.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_andromeda_welcome_wiz` | `model_hr_rfid_andromeda_welcome_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_andromeda_import_wiz` | `model_hr_rfid_andromeda_import_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_andromeda_import_users` | `model_hr_rfid_andromeda_import_users` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |


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
metadata (`ir.model.data`), against the Andromeda record it came from. That
register is what makes a second run find the first run's work instead of
creating it again - identity is the SOURCE ID, never a name, a code or a card
number.

###### The name

```
__import__.rfid_import_andromeda_{target_model}_{source_table}_{source_id}
```

built by `_xml_id_name(model, source_ref)`; `source_ref` is
`{SRC_*}_{andromeda id}`. The target model is part of the name because one
Andromeda user can land as BOTH an `hr.employee` and a `res.partner`, and both
have to be recognised separately.

###### Helpers on `hr.rfid.andromeda.import.wiz`

| Method | Does |
|---|---|
| `_source_slug()` | The source identity (`SOURCE_SLUG`). Override it if an installation ever needs to keep two Andromeda sources apart. |
| `_xml_id_name(model, source_ref)` / `_xml_id(model, source_ref)` | The name, and the full external ID. |
| `_find_imported(model, source_ref)` | The record an earlier run created for this source record, or an empty recordset. `env.ref(..., raise_if_not_found=False)`. |
| `_mark_imported(record, source_ref)` | Registers a freshly created record. Called on EVERY create path: company, contact, department, employee, card, placeholder access group, access-group membership. |
| `_already_imported_user_ids()` | The Andromeda user ids an earlier run brought in, so they are not offered for import again. Looks under both `hr.employee` and `res.partner` prefixes; the `SRC_USER` token keeps companies (also `res.partner`) out. |

###### Memberships have TWO guards

`_add_ag_membership` skips a membership when its external ID exists **or** when
the (person, access group) pair is already there. The second guard is not
redundant: memberships created before this module wrote external IDs at all
carry nothing that says they came from here, and without it the first run after
the change would duplicate every one of them.

###### Placeholder access group

A department with no default access group gets a placeholder, registered
against the source access group that made it necessary
(`SRC_PLACEHOLDER_AG`), so a second run reuses it instead of leaving another
one behind.

###### Records marked by an earlier version

Versions before 19.0.1.3.0 registered their work under `__export__` with names
like `andromeda_u_id_7`. Those names are NOT read any more, and there is no
conversion step: on a database imported with an older version, the users
concerned are offered again and accepted as new. A site in that position should
be checked before a repeat import is run.

###### Tests

`tests/test_import_wizard.py` - the create paths and their repeats (company,
department, employee, contact), an access group is not given twice (by external
ID, and by the pair guard for memberships that predate it), the placeholder is
reused, one badge stays one card, a door keeps exactly one way in, a visitor's
badge is not handed out twice, and a card switched off in Andromeda is not
reissued as a second working copy. The Firebird calls are patched out
(`do_fb_sql_context`), so no server is needed - and none is needed for any of
this logic.

##### What the constants of the import mean

- **`LEDGER_MODULE`** = `'__import__'` - the `ir.model.data` module every record
  created here is registered under. It is what core's own `BaseModel.load()`
  writes for imported rows, so a second run recognises the first run's work
  exactly the way core would.
- **`SOURCE_SLUG`** = `'andromeda'` - the source identity inside the external
  ID. One slug for every Andromeda source: the Firebird connection exposes no
  stable installation identifier (the IP can change between runs and the
  database path is the same on every default install).
- **`SRC_USER`/`SRC_COMPANY`/`SRC_DEPARTMENT`/`SRC_ACCESS_GROUP`/`SRC_TAG`/`SRC_AG_USER`/`SRC_PLACEHOLDER_AG`**
  = `'u'`/`'c'`/`'d'`/`'ag'`/`'tag'`/`'agu'`/`'placeholder'` - source TABLE
  tokens. USERS and COMPANY both land in `res.partner`, so the reference has to
  say which Andromeda table an id came from, or user 7 and company 7 are the
  same record.
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (4)

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [FIX] hr_rfid_andromeda_import: drop @api.returns decorators ...

Commit `5f1c3fa934` (2026-05-03): [FIX] hr_rfid_andromeda_import: drop @api.returns decorators (removed in v19)

#### Fix: v2.1 Added portal functionality, barcode generation and RFID ...

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: fix from 14.0

Commit `8a074b5388` (2022-05-12): fix from 14.0


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_andromeda_import`
- Source digest: `sha256:ac5bbfb25af5026261791ef3f8217541593c809ab2dc5a25a45738591a0c3a2f`
- Generated at: `2026-11-23T10:04:47+00:00`
- Generator: `polimex_module_knowledge`
