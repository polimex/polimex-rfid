---
id: hr_rfid_odoo_import
title: RFID Odoo Data Import
module: hr_rfid_odoo_import
module_version: 19.0.2.5.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import RFID access control data from older Odoo instances (v14-v18)
last_updated: '2026-08-14'
source_digest: sha256:4d8f8551927ad0bb4e338792941413e2537158e211256d3f41f5176285fdb380
depends:
- hr_rfid
entities:
  primary: hr.rfid.odoo.import.run
  related:
  - hr.rfid.odoo.import.log
  - hr.rfid.odoo.import.company.line
  - hr.rfid.odoo.import.wiz
keywords:
- access
- company
- conflict
- control
- data
- from
- import
- instances
- line
- log
- odoo
- older
- rfid
- wiz
license: AGPL-3
author: Polimex Dev Team
category: HR
installable: true
application: false
auto_install: false
counts:
  models: 4
  views: 1
  access_rules: 4
  record_rules: 0
  crons: 0
  images: 1
images:
- path: static/description/icon.png
  sha256: sha256:a56372719a66ebe603a8e4d1a1a9ed222c0402facb3ef699d4e24c1803c75417
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Odoo Data Import - `hr_rfid_odoo_import` v19.0.1.2.0

Import RFID access control data from older Odoo instances (v14-v18)

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_odoo_import`
- **Version**: `19.0.1.2.0`
- **Category**: HR
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`

### README (verbatim)

========================
RFID Odoo Data Import
========================

..
   :target: https://polimex.co
   :alt: License: AGPL-3

Import RFID access control data from older Odoo instances (v14-v18) into Odoo 19
via XML-RPC API.

Overview
========

This module provides a multi-step wizard for migrating RFID access control data
from older Odoo instances into Odoo 19. It connects to the source Odoo via
XML-RPC API, reads configuration and historical data, and recreates it in the
target database.

Features
========

* **XML-RPC connection** - works with any Odoo instance (local or remote, v14-v18)
* **Version-tolerant reads** - each phase names the fields it wants and checks
  them against the source with ``fields_get()``, so a field that only exists in
  some versions is used where present and skipped where absent
* **Multi-company support** - select which company to import
* **Runs in the background** - the transfer is handed to a scheduled job and
  continues after the dialog is closed. A real site carries tens of thousands of
  events, which is far more than a single web request is allowed to spend. Work
  is done in committed pieces; an interrupted transfer continues where it
  stopped instead of starting over.
* **Phases, each declaring what it needs** - a phase states which feature the
  source must have and which models this system must provide. A phase that
  cannot run is recorded with the reason, rather than leaving a silent gap:

  - Core & Hardware (webstacks, controllers, doors, readers, time schedules)
  - People (employees, partners, departments, categories)
  - Zones (after People - membership lists are the people)
  - Sites (the tree of locations, the equipment on it, the contacts in it)
  - Access Control (access groups, relations, cards -> card-door regeneration)
  - Site Groups (a site's own access group, restored after the real ones)
  - Cameras (ANPR cameras, their readers and doors, their plate lists)
  - Events (user events, system events, temperature/humidity logs)
  - Vending (rows, events, balance history, auto-refill)
  - Attendance (hr.attendance, hr.attendance.extra)
  - Services (rfid.service, rfid.service.sale, tags)

* **Deduplication** via ``ir.model.data`` with ``__import__`` prefix
* **Nothing is said to the hardware** - no controller and no camera receives a
  command while a transfer is running. The site stays guarded throughout.
* **Conflict detection** - a record that would break an existing unique
  constraint is reported for the operator to decide, never merged silently
* **Direct SQL batch insert** for large datasets (events, attendance, balance history)
* **An account of what happened** - one line per step, including what was left
  behind and why

Configuration
=============

No special configuration is needed. The module adds a menu entry under
**RFID -> Import -> Import from Odoo**.

Usage
=====

1. Go to **RFID -> Import -> Import from Odoo**
2. Enter the source Odoo connection details (URL, database, login, password)
3. Click **Check Connection** to verify connectivity
4. Select the source company to import
5. Choose which optional data to include (events, vending, attendance, services)
6. Click **Start Import** and monitor progress
7. The transfer opens on its own page and continues in the background. Close it
   whenever you like; come back to **RFID -> Data Transfers** to see how far it
   has got and what it moved.

Requirements
============

* The source Odoo instance must be running and accessible via HTTP/HTTPS
* The source user must have admin-level access to read all RFID data
* Target database must have ``hr_rfid`` installed
* For vending/attendance/service import, the corresponding modules must be
  installed in the target

Credits
=======

Authors
-------

* Polimex Holding Ltd.

Website: https://polimex.co


## Transfer contract <a id='contract'></a>

What a caller and a reviewer can rely on. Written by hand; the sections around
it are generated from the code.

**Every long read is resumable, and that is enforced.** `BaseImporter._read_all`
takes a mandatory `cursor_key`, unique to the STEP (two steps reading the same
model through different domains must not share one). The key remembers where
the read got to, on the run record, so the next pass carries on; it is set to
`CURSOR_FINISHED` when the source is exhausted, and a finished read is not
repeated. A step that cannot name its cursor raises rather than silently
restarting from the beginning on every pass - which is what stalled a 6 176
person tenant at 1 001 people for good.

**A step reports the RUN, not the pass.** `BaseImporter.accumulated_result`
takes the same key as the cursor and adds this pass's slice to the running
totals, so a finished step whose last pass legitimately read nothing still
reports what the whole transfer moved.

**Rows, cursors and totals move together.** `progress_snapshot()` /
`restore_progress()` are taken around every step (`PhaseImporter.steps`) and
every phase (`run._run_one_phase`, and the synchronous path in the wizard): when
a savepoint takes the rows back, the reading position and the counts go back
with them, so the next pass does not skip records that never landed.

**A phase declares what it needs, and what it merely ASKS about.**
`REQUIRES_SOURCE` gates the phase; `PROBE_SOURCE` only adds module names to the
list the wizard asks the source about, for data that has its own switch. Both
feed `source_probe_modules()`, so no list is kept by hand.

**Field names are read from BOTH schemas, never assumed.** Each step intersects
its candidates with the source's `fields_get` and the target's columns, so a
name that exists in neither is dropped WITHOUT A WORD. Four such lists shipped
with names that existed in neither version - the controller's capacities
(`readers`, `time_schedules`), the daily roll-up's numbers, the vending profile
of a person, and a refill run's total - and each one cost real data on a live
cloud. When adding a field, check it against both sides.

**What the automation here already made is ADOPTED, not duplicated.**
Controllers, doors and readers by their device key; cameras by their chain; time
schedules by (company, slot). Every one of those exists before a transfer runs,
because this system creates them itself.

**The final check separates inherited from introduced.** Phase 9 asks the source
whether it has the same shape; equal numbers are reported as carried over
rather than as a fault of the transfer.

## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_odoo_import --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.odoo.import.conflict` <a id='model-hr-rfid-odoo-import-conflict'></a>
Python class `HrRfidOdooImportConflict` in `models/import_conflict.py:5`.  TransientModel (wizard).  Description: *RFID Odoo Import Conflict*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `wizard_id` | Many2one → \`hr.rfid.odoo.import.wiz\` |  | ✓ | ✓ | Parent import-run wizard this conflict belongs to. |
| `source_model` | Char | Model |  | ✓ | Odoo model name of the conflicting record (e.g. hr.rfid.card, res.partner). |
| `source_id` | Integer | Source ID |  | ✓ | Database ID of the record on the source instance. |
| `source_name` | Char | Source Record |  | ✓ | Display name of the record on the source instance - shown so the operator can id |
| `source_ref` | Char | Unique Key |  | ✓ | The natural key that triggered the conflict (e.g. card number, EGN). Both sides  |
| `target_id` | Integer | Target ID |  | ✓ | Database ID of the matching record on this (target) instance. |
| `target_name` | Char | Existing in Target |  | ✓ | Display name of the existing target record - operator decides whether to keep it |
| `conflict_field` | Char | Conflict Field |  | ✓ | Field on which the two records collide (typically the unique constraint that fir |
| `resolution` | Selection | Resolution |  | ✓ | What to do with this conflict during the import - Link / Create / Skip. Deliberat |

### `hr.rfid.odoo.import.log` <a id='model-hr-rfid-odoo-import-log'></a>
Python class `HrRfidOdooImportLog` in `models/import_conflict.py:54`.  TransientModel (wizard).  Description: *RFID Odoo Import Log*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `wizard_id` | Many2one → \`hr.rfid.odoo.import.wiz\` |  | ✓ | ✓ | Parent import-run wizard this log entry belongs to. |
| `phase` | Char | Phase |  | ✓ | Stage of the import pipeline (e.g. 'companies', 'access_groups', 'users', 'event |
| `model` | Char | Model |  | ✓ | Odoo model processed during this phase. |
| `source_count` | Integer | Source Count |  | ✓ | Number of records the source instance reported for this model+phase. |
| `imported_count` | Integer | Imported |  | ✓ | Number of records actually created in the target during this phase. |
| `skipped_count` | Integer | Skipped |  | ✓ | Number of records skipped (operator chose Skip in conflicts, or validation rejec |
| `linked_count` | Integer | Linked |  | ✓ | Number of source records mapped to an existing target record instead of being cr |
| `status` | Selection | Status |  | ✓ | Outcome of this phase - Pending: not yet executed. Done: completed without error |
| `duration` | Float | Duration (s) |  | ✓ | Wall-clock seconds this phase took. Useful to spot slow phases for the next run. |
| `error_message` | Text | Error |  | ✓ | Error message captured if the phase status is Error - full traceback for debuggi |

### `hr.rfid.odoo.import.company.line` <a id='model-hr-rfid-odoo-import-company-line'></a>
Python class `HrRfidOdooImportCompanyLine` in `models/import_conflict.py:108`.  TransientModel (wizard).  Description: *RFID Odoo Import Company Mapping*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `wizard_id` | Many2one → \`hr.rfid.odoo.import.wiz\` |  | ✓ | ✓ | Parent import-run wizard this company mapping belongs to. |
| `source_id` | Integer | Source Company ID |  | ✓ | res.company ID on the source instance - the natural key used to match across ins |
| `source_name` | Char | Source Company |  | ✓ | Display name of the company on the source instance - shown for operator cross-ch |
| `do_import` | Boolean | Import |  | ✓ | Untick to skip this source company entirely. Useful when you only want to migrat |
| `target_company_id` | Many2one → \`res.company\` | Target Company |  | ✓ | Existing res.company on this instance to merge the source data into. Leave empty |

### `hr.rfid.odoo.import.wiz` <a id='model-hr-rfid-odoo-import-wiz'></a>
Python class `HrRfidOdooImportWiz` in `models/import_wizard.py:13`.  TransientModel (wizard).  Description: *Import RFID Data from Odoo*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `state` | Selection | State | ✓ | ✓ | Step the wizard is currently on - Connection: enter source URL + creds. Configur |
| `source_url` | Char | Source URL | ✓ | ✓ | Full URL of the source Odoo server, e.g. https://erp.example.com |
| `source_db` | Char | Source Database |  | ✓ | Leave empty if the source server hosts a single database - it will be auto-detec |
| `source_slug` | Char | Source Identity |  | ✓ | Which system the records come from, inside their external IDs. Empty = the source database name. Set it when the SAME system is read from two places (backup, then live) - both transfers must carry the same value or everything arrives twice. See "Identity of a transferred record". |
| `source_login` | Char | Username | ✓ | ✓ | Login of an admin-level user on the source Odoo instance - the user must have re |
| `source_password` | Char | Password | ✓ | ✓ | Password for the source user above. Use an API key if the source enforces 2FA. S |
| `source_version` | Char | Source Odoo Version |  | ✓ | Major Odoo version detected on the source instance (e.g. '14.0', '15.0'). Used t |
| `source_uid` | Integer | Source UID |  | ✓ | res.users ID of the connected source user. Cached after Test Connection. |
| `installed_modules_json` | Text | Installed Modules (JSON) |  | ✓ | JSON list of installed modules on the source instance. |
| `company_line_ids` | One2many → \`hr.rfid.odoo.import.company.line\` | Company Mapping |  | ✓ | One row per company discovered on the source. Operator picks which to import and |
| `import_hardware` | Boolean | Import Hardware |  | ✓ | Include webstacks, controllers, doors, readers and time schedules. |
| `import_people` | Boolean | Import People |  | ✓ | Include employees and partner contacts referenced by the imported access groups  |
| `import_access` | Boolean | Import Access Control |  | ✓ | Include access groups (and their door/department bindings) and zones. |
| `import_cards` | Boolean | Import Cards |  | ✓ | Include hr.rfid.card records, including their owner and access-group memberships |
| `import_all_partners` | Boolean | Import all partners |  | ✓ | Import all partners from selected companies, not just RFID-linked ones. |
| `import_all_employees` | Boolean | Import all employees |  | ✓ | Import all employees from selected companies, not just RFID-linked ones. |
| `import_images` | Boolean | Import photos |  | ✓ | Import employee and partner photos (may slow down import). |
| `import_users` | Boolean | Create users |  | ✓ | Create res.users for imported employees (matched by login or created with temp p |
| `import_user_groups` | Boolean | Transfer user groups |  | ✓ | Copy security group assignments from source users (matched by xml_id). |
| `import_user_events` | Boolean | Import user events |  | ✓ | Include the historical hr.rfid.event.user log. Can be large - disable for first  |
| `import_system_events` | Boolean | Import system events |  | ✓ | Include the historical hr.rfid.event.system log (controller power loss, tamper,  |
| `import_th_logs` | Boolean | Import temperature/humidity logs |  | ✓ | Include temperature-controller log records. Disable unless the source actually u |
| `event_date_from` | Date | Events from date |  | ✓ | Only import events newer than this date. Leave empty for all events. |
| `import_vending` | Boolean | Import vending data |  | ✓ | Include vending balances, history and events. Only visible if both source and ta |
| `import_attendance` | Boolean | Import attendance |  | ✓ | Include hr.attendance records linked to RFID events. |
| `import_attendance_extra` | Boolean | Import attendance extra |  | ✓ | Include the daily roll-ups produced by hr_attendance_late (late/overtime/extra t |
| `import_service` | Boolean | Import service data |  | ✓ | Include rfid.service catalog and rfid.service.sale records from the source. |
| `source_has_vending` | Boolean |  |  | ✓ | Source instance has the hr_rfid_vending module installed (detected from Test Con |
| `source_has_attendance` | Boolean |  |  | ✓ | Source instance has hr_attendance_multi_rfid installed. |
| `source_has_attendance_late` | Boolean |  |  | ✓ | Source instance has hr_attendance_late installed. |
| `source_has_service` | Boolean |  |  | ✓ | Source instance has rfid_service_base installed. |
| `target_has_vending` | Boolean |  |  | - | This (target) instance has hr_rfid_vending installed - the related import_vendin |
| `target_has_attendance` | Boolean |  |  | - | This (target) instance has hr_attendance_multi_rfid installed. |
| `target_has_attendance_late` | Boolean |  |  | - | This (target) instance has hr_attendance_late installed. |
| `target_has_service` | Boolean |  |  | - | This (target) instance has rfid_service_base installed. |
| `warnings` | Json | Warnings |  | - | Pre-flight warnings calculated from the configuration (e.g. asked to import vend |
| `preview_text` | Text | Preview |  | ✓ | Human-readable summary of what will be created/linked if the operator confirms.  |
| `conflict_ids` | One2many → \`hr.rfid.odoo.import.conflict\` | Conflicts |  | ✓ | Per-record collisions detected against the target. Operator must pick a resoluti |
| `dry_run` | Boolean | Full dry-run |  | ✓ | Execute full import + rollback to verify everything works. |
| `progress_text` | Text | Progress |  | ✓ | Live status of the running import job (current phase, processed records). Update |
| `progress_percent` | Float | Progress % |  | ✓ | Estimated completion percentage. Driven by the phase log - useful for the operat |
| `log_ids` | One2many → \`hr.rfid.odoo.import.log\` | Import Log |  | ✓ | Per-phase result rows (counts of imported / skipped / linked, plus any error). T |
| `error_message` | Text | Error |  | ✓ | Top-level error captured if the run aborted mid-way. Individual phase errors are |

#### Notable methods

- **`_compute_warnings(self)`** - decorators: `@api.depends`
- **`action_test_connection(self)`** - decorators: -
  - Step 1 → Step 2: Test connection and load companies.
  - effects: `raise:UserError`, `write`
  - touches: `hr.rfid.odoo.import.company.line`
- **`action_preview(self)`** - decorators: -
  - Step 2 → Step 3: Generate preview with counts and detect conflicts.
  - effects: `raise:UserError`, `write`
- **`action_back(self)`** - decorators: -
  - Navigate back one step.
- **`action_import(self)`** - decorators: -
  - Step 3 → Step 4 → Step 5: Execute the import.
  - effects: `log_error`, `raise:UserError`
- **`_effective_source_identity(self)`** - decorators: -
  - `normalise_source_slug(source_slug or source_db)` - the name this transfer
    will file its records under. Everything that compares identities must go
    through it, or it compares one spelling with another.
- **`_identities_this_transfer_has_read(self)`** / **`_holds_records_from(self, identity)`** / **`_other_source_identities(self)`** - decorators: -
  - The other-source check, asked per identity rather than by sampling what is
    already here. See "Recognising another system's records".
- **`_warn_about_other_source_identity(self)`** / **`_warn_about_refresh_on_rerun(self)`** - decorators: -
  - The two warnings whose wording is load-bearing: the operator decides
    whether to start on the strength of them, so every clause has to be true of
    the code (and is covered by a behaviour test).

### `hr.rfid.odoo.import.run` <a id='model-hr-rfid-odoo-import-run'></a>
Python class `HrRfidOdooImportRun` in `models/import_run.py:39`.  Model.  Inherits: `mail.thread`.  Description: *RFID Data Transfer*.  Default order: `create_date desc`.

The permanent record of a transfer - the wizard is transient and would take the
job with it. It carries what the work needs to continue in another process:
the connection (`source_url`, `source_db`, `source_login`, `source_password`,
`source_uid`), the identity (`source_slug`), the operator's choices
(`options_json`, `company_map_json`, `resolution_json`), and the cursors
(`done_phases_json`, `read_cursors_json`, `current_phase`, `done_count`,
`total_count`). `state` is `queued` / `running` / `done` / `failed`; `log_ids`
is one line per phase, and a phase that stopped early is `partial` ("Partly"),
not `done`.

`hr_attendance_multi_rfid.hr.attendance.recalc.run` is deliberately the same
shape - one pattern for long jobs in this codebase, not two.

Key methods: `action_start`, `_cron_process` (one pass; closes stalled runs and
COMMITS that before starting a pass), `_process_pass`, `_run_one_phase`,
`_save_progress` (`ir.cron._commit_progress`), `_abandon_stalled_runs` (returns
what it closed; clears the stored credentials), `_finish_reporting_failures`.


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/importers/base_importer.py`

- **`IMPORT_CONTEXT`** *(collection)* = `{'no_hardware_commands': True, 'tracking_disable': True, 'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_activity_automation_skip': True, 'no_reset_password': True}`
- **`EXTERNAL_ID_MODULE`** = `'__import__'` - the `ir.model.data` module every
  transferred record is registered under, the same one core's own
  `BaseModel.load()` writes.
- **`EXTERNAL_ID_PREFIX`** = `'rfid_import_'` - start of every external-ID name
  this transfer writes. Read by anything that has to recognise a transferred
  record (`models/hr_employee.py` builds its pattern from it).

### `models/hr_employee.py`

- **`ATTENDANCE_MODEL`** = `'hr.attendance'`
- **`EXTERNAL_ID_NAME_PATTERN`** = `'rfid_import_%_hr_attendance_%'` (built from
  the two constants above, source installation wildcarded)
- **`NAMES_SHOWN`** = `3`, **`DEFAULT_LOOKBACK_DAYS`** = `30` (the same window
  the rebuild starts from when no date is given)


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`AccessImporter.run(self, wizard)`** - `models/importers/access_importer.py:26`
  - Execute Phase 4.
- **`AttendanceImporter.run(self, wizard)`** - `models/importers/attendance_importer.py:23`
  - Execute Phase 6b.
- **`CoreImporter.run(self, wizard)`** - `models/importers/core_importer.py:26`
  - Execute Phase 1 + Phase 3.
- **`EventImporter.run(self, wizard)`** - `models/importers/event_importer.py:25`
  - Execute Phase 5.
- **`PeopleImporter.run(self, wizard)`** - `models/importers/people_importer.py:24`
  - Execute Phase 2.
- **`ServiceImporter.run(self, wizard)`** - `models/importers/service_importer.py:23`
  - Execute Phase 6c.
- **`VendingImporter.run(self, wizard)`** - `models/importers/vending_importer.py:25`
  - Execute Phase 6a: Vending.
- **`TestOdooImportSmoke.setUpClass(cls)`** (`@classmethod`) - `tests/test_smoke.py:12`
  - calls `super()`
  - touches: `hr.rfid.odoo.import.wiz`
- **`TestOdooImportSmoke.test_wizard_create_starts_in_connection_state(self)`** - `tests/test_smoke.py:21`
- **`TestOdooImportSmoke.test_log_record_persists(self)`** - `tests/test_smoke.py:27`
  - touches: `hr.rfid.odoo.import.log`
- **`TestOdooImportSmoke.test_conflict_record_can_be_created(self)`** - `tests/test_smoke.py:33`
  - touches: `hr.rfid.odoo.import.conflict`
- **`TestOdooImportSmoke.test_company_line_create(self)`** - `tests/test_smoke.py:39`
  - touches: `hr.rfid.odoo.import.company.line`

### Private helpers

- **`AccessImporter.__init__(self, base)`** - `models/importers/access_importer.py:21`
- **`AccessImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/access_importer.py:37`
- **`AccessImporter._import_access_groups(self)`** - `models/importers/access_importer.py:50`
  - Step 20: hr.rfid.access.group - TWO PASSES (inherited_ids M2M self-ref).
  - effects: `with_context`
- **`AccessImporter._import_ag_door_rels(self)`** - `models/importers/access_importer.py:134`
  - Step 21: hr.rfid.access.group.door.rel - AG↔Door relations.
- **`AccessImporter._import_ag_employee_rels(self)`** - `models/importers/access_importer.py:194`
  - Step 22: hr.rfid.access.group.employee.rel - exact copy from source.
- **`AccessImporter._import_ag_contact_rels(self)`** - `models/importers/access_importer.py:262`
  - Step 23: hr.rfid.access.group.contact.rel - exact copy from source.
- **`AccessImporter._import_cards(self)`** - `models/importers/access_importer.py:333`
  - Step 24: hr.rfid.card - with EXACT active state from source.
- **`AccessImporter._department_second_pass(self)`** - `models/importers/access_importer.py:447`
  - Step 25: hr.department SECOND PASS - update AG back-references.
  - effects: `with_context`
- **`AttendanceImporter.__init__(self, base)`** - `models/importers/attendance_importer.py:18`
- **`AttendanceImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/attendance_importer.py:31`
- **`AttendanceImporter._import_attendance(self)`** - `models/importers/attendance_importer.py:44`
  - Step 36: hr.attendance - Direct SQL batch.
  - effects: `log_error`
- **`AttendanceImporter._import_attendance_extra(self)`** - `models/importers/attendance_importer.py:117`
  - Step 37: hr.attendance.extra - Direct SQL batch.
  - effects: `log_error`
- **`BaseImporter.__init__(self, env, source_url, source_db, source_uid, source_password, company_map, options)`** - `models/importers/base_importer.py:29`
- **`BaseImporter._search_read(self, model, domain, fields, order='id asc', limit=0, include_archived=True)`** - `models/importers/base_importer.py:50`
  - Read records from source via XML-RPC.
- **`BaseImporter._read_all(self, model, domain, fields, batch_size=1000)`** - `models/importers/base_importer.py:72`
  - ID-based pagination for large datasets.
- **`BaseImporter._search_count(self, model, domain)`** - `models/importers/base_importer.py:87`
  - Count records in source (including archived).
- **`BaseImporter._has_field(self, model, field_name)`** - `models/importers/base_importer.py:98`
  - Check if field exists in source model via fields_get().
- **`BaseImporter._get_source_fields(self, model)`** - `models/importers/base_importer.py:108`
  - Get all source fields metadata (cached).
- **`BaseImporter._has_model(self, model)`** - `models/importers/base_importer.py:114`
  - Check if model exists in source.
- **`BaseImporter._load_records(self, model_name, data_list)`** - `models/importers/base_importer.py:127`
  - Use Odoo 19 _load_records() for batch create + XML ID.
  - effects: `with_context`
- **`BaseImporter._try_load_records(self, model_name, data_list)`** - `models/importers/base_importer.py:142`
  - Load records with savepoint - skip silently on failure.
  - effects: `log_warn`
- **`BaseImporter._direct_sql_insert(self, table, columns, rows, batch_size=5000)`** - `models/importers/base_importer.py:160`
  - Direct SQL INSERT into target DB - bypass ORM.
- **`BaseImporter._xml_id(self, model_prefix, source_id)`** - `models/importers/base_importer.py:184`
  - Generate XML ID for ir.model.data.
- **`BaseImporter._get_target_id(self, model, source_id)`** - `models/importers/base_importer.py:193`
  - Get target ID from previously imported record.
- **`BaseImporter._set_target_id(self, model, source_id, target_id)`** - `models/importers/base_importer.py:205`
  - Store source → target ID mapping.
- **`BaseImporter._require_target_id(self, model, source_id, context_msg='')`** - `models/importers/base_importer.py:209`
  - Get target ID or raise error if not found (fail hard).
  - effects: `raise:UserError`
- **`BaseImporter._resolve_from_imd(self, model, source_id)`** - `models/importers/base_importer.py:243`
  - Try to resolve target ID from ir.model.data.
  - effects: `sudo`
  - touches: `ir.model.data`
- **`BaseImporter._map_company(self, source_company_id)`** - `models/importers/base_importer.py:262`
  - Map source company ID to target company ID.
- **`BaseImporter._company_domain(self)`** - `models/importers/base_importer.py:269`
  - Return domain filter for source companies being imported.
- **`BaseImporter._source_company_ids(self)`** - `models/importers/base_importer.py:276`
  - Return list of source company IDs being imported.
- **`BaseImporter._map_m2o(self, model, source_val)`** - `models/importers/base_importer.py:282`
  - Map Many2one field: [id, name] or id → target_id or False.
- **`BaseImporter._map_m2m(self, model, source_ids)`** - `models/importers/base_importer.py:295`
  - Map Many2many field: [id1, id2, ...] → [(6, 0, [target_ids])].
- **`BaseImporter._common_fields(self, source_model, target_model)`** - `models/importers/base_importer.py:306`
  - Get fields that exist in both source and target.
- **`BaseImporter._log(self, msg, *args)`** - `models/importers/base_importer.py:331`
  - Log a message.
  - effects: `log_info`
- **`CoreImporter.__init__(self, base)`** - `models/importers/core_importer.py:21`
- **`CoreImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/core_importer.py:52`
- **`CoreImporter._import_card_types(self)`** - `models/importers/core_importer.py:69`
  - Step 1: hr.rfid.card.type - match by name.
- **`CoreImporter._import_employee_categories(self)`** - `models/importers/core_importer.py:104`
  - Step 2: hr.employee.category - match by name.
- **`CoreImporter._import_departments(self)`** - `models/importers/core_importer.py:139`
  - Step 3: hr.department - TWO PASSES (parent_id self-ref).
  - effects: `with_context`
- **`CoreImporter._import_workcodes(self)`** - `models/importers/core_importer.py:207`
  - Step 4: hr.rfid.workcode - filtered by company.
- **`CoreImporter._import_time_schedules(self)`** - `models/importers/core_importer.py:254`
  - Step 5: hr.rfid.time.schedule - match by number + company.
  - effects: `with_context`
- **`CoreImporter._import_alarm_groups(self)`** - `models/importers/core_importer.py:314`
  - Step 8: hr.rfid.ctrl.alarm.group - TWO PASSES (parent_id self-ref).
  - effects: `with_context`
- **`CoreImporter._import_emergency_groups(self)`** - `models/importers/core_importer.py:364`
  - Step 9: hr.rfid.ctrl.emergency.group - company-level.
- **`CoreImporter._import_webstacks(self)`** - `models/importers/core_importer.py:400`
  - Step 10: hr.rfid.webstack - filtered by company.
- **`CoreImporter._import_controllers(self)`** - `models/importers/core_importer.py:467`
  - Step 11: hr.rfid.ctrl - filtered by webstack.
- **`CoreImporter._import_doors(self)`** - `models/importers/core_importer.py:546`
  - Step 12: hr.rfid.door - filtered by ctrl→ws→company chain.
- **`CoreImporter._import_readers(self)`** - `models/importers/core_importer.py:603`
  - Step 13: hr.rfid.reader - filtered by ctrl.
- **`CoreImporter._import_input_masks(self)`** - `models/importers/core_importer.py:657`
  - Step 14: hr.rfid.ctrl.input.mask - per controller.
- **`CoreImporter._import_output_ts(self)`** - `models/importers/core_importer.py:700`
  - Step 15: hr.rfid.ctrl.output.ts - per controller.
- **`CoreImporter._import_alarms(self)`** - `models/importers/core_importer.py:748`
  - Step 16: hr.rfid.ctrl.alarm - depends on ctrl + door + alarm_group.
- **`CoreImporter._import_th_sensors(self)`** - `models/importers/core_importer.py:811`
  - Step 17: hr.rfid.ctrl.th - depends on ctrl + door.
- **`CoreImporter._import_zones(self)`** - `models/importers/core_importer.py:857`
  - Step 18: hr.rfid.zone - M2M: door_ids, departments, categories, employees, contacts.
- **`CoreImporter._import_notifications(self)`** - `models/importers/core_importer.py:915`
  - Step 19: hr.rfid.notification - depends on zone + notify_partner_ids.
- **`EventImporter.__init__(self, base)`** - `models/importers/event_importer.py:20`
- **`EventImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/event_importer.py:35`
- **`EventImporter._event_date_domain(self)`** - `models/importers/event_importer.py:48`
  - Build date filter domain for events.
- **`EventImporter._import_user_events(self)`** - `models/importers/event_importer.py:55`
  - Step 26: hr.rfid.event.user - Direct SQL batch.
  - effects: `log_error`
- **`EventImporter._import_system_events(self)`** - `models/importers/event_importer.py:139`
  - Step 27: hr.rfid.event.system - Direct SQL batch.
  - effects: `log_error`
- **`EventImporter._import_th_logs(self)`** - `models/importers/event_importer.py:225`
  - Step 28: hr.rfid.ctrl.th.log - Direct SQL batch.
  - effects: `log_error`
- **`PeopleImporter.__init__(self, base)`** - `models/importers/people_importer.py:19`
- **`PeopleImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/people_importer.py:32`
- **`PeopleImporter._import_partners(self)`** - `models/importers/people_importer.py:45`
  - Step 5: res.partner - scope depends on user choice.
  - effects: `log_warn`, `with_context`
  - touches: `res.country`
- **`PeopleImporter._import_users(self)`** - `models/importers/people_importer.py:187`
  - Step 6: res.users - optional, match by login.
  - effects: `log_warn`, `with_context`
- **`PeopleImporter._transfer_groups(self, user, source_group_ids)`** - `models/importers/people_importer.py:259`
  - Transfer user groups from source by matching xml_id.
  - effects: `with_context`
- **`PeopleImporter._import_employees(self)`** - `models/importers/people_importer.py:282`
  - Step 7: hr.employee - scope depends on user choice.
  - effects: `with_context`
- **`ServiceImporter.__init__(self, base)`** - `models/importers/service_importer.py:18`
- **`ServiceImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/service_importer.py:30`
- **`ServiceImporter._import_service_tags(self)`** - `models/importers/service_importer.py:43`
  - Step 38: rfid.service.tags - ORM create.
- **`ServiceImporter._import_services(self)`** - `models/importers/service_importer.py:80`
  - Step 39: rfid.service - depends on AG, zone, partner, card_type, tags.
  - effects: `log_warn`
- **`ServiceImporter._resolve_template_by_xmlid(self, source_val, model)`** - `models/importers/service_importer.py:168`
  - Resolve template M2O by xml_id from source ir.model.data.
  - effects: `log_warn`
- **`ServiceImporter._import_service_sales(self)`** - `models/importers/service_importer.py:192`
  - Step 40: rfid.service.sale - Direct SQL batch.
  - effects: `log_error`
- **`VendingImporter.__init__(self, base)`** - `models/importers/vending_importer.py:20`
- **`VendingImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='')`** - `models/importers/vending_importer.py:36`
- **`VendingImporter._import_products(self)`** - `models/importers/vending_importer.py:49`
  - Step 29: product.template - match by default_code, fallback name.
- **`VendingImporter._import_vending_rows(self)`** - `models/importers/vending_importer.py:119`
  - Step 30: hr.rfid.ctrl.vending.row - depends on ctrl + product.
- **`VendingImporter._import_vending_settings(self)`** - `models/importers/vending_importer.py:175`
  - Step 31: hr.rfid.ctrl.vending.settings - depends on ctrl.
- **`VendingImporter._import_auto_refill(self)`** - `models/importers/vending_importer.py:215`
  - Step 32: hr.rfid.vending.auto.refill - company-level.
- **`VendingImporter._import_vending_events(self)`** - `models/importers/vending_importer.py:263`
  - Step 33: hr.rfid.vending.event - Direct SQL batch (separate table).
  - effects: `log_error`
- **`VendingImporter._import_balance_history(self)`** - `models/importers/vending_importer.py:348`
  - Step 34: hr.rfid.vending.balance.history - Direct SQL batch.
  - effects: `log_error`
- **`VendingImporter._update_employee_vending_fields(self)`** - `models/importers/vending_importer.py:421`
  - Step 35: Update employees with vending balance fields.
  - effects: `with_context`
  - touches: `hr.employee`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_odoo_import_wiz_form` | `hr.rfid.odoo.import.wiz` | - |  | `views/import_wizard_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_odoo_import_wiz` | `model_hr_rfid_odoo_import_wiz` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_company_line` | `model_hr_rfid_odoo_import_company_line` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_conflict` | `model_hr_rfid_odoo_import_conflict` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_log` | `model_hr_rfid_odoo_import_log` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |


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


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `gotchas` (9)

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` - само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` - само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `_compute, create()`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `help=, ir.model.data`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` - следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) - modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `res_id, type="object"`

#### Gotcha: `account.account` **НЯМА** `company_id` - ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` - ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: `size=N` на `fields.Char` е **UI hint**, не DB constraint - не разчита
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `size=N` на `fields.Char` е **UI hint**, не DB constraint - не разчитай на него за валидация

Matched tokens: `fields.char`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `validationerror`

#### Gotcha: `l10n_bg_document_type` е computed - задавай с `write()` след създаван
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Accounting специфики (l10n_bg)** in odoo19-gotchas.md:

> `l10n_bg_document_type` е computed - задавай с `write()` след създаване, не при `create()`

Matched tokens: `create()`

#### Gotcha: **Search view: `<group>` без атрибути** - `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** - `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

#### Gotcha: **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Security & Constraints** in odoo19-gotchas.md:

> **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res.groups.privilege`, който има `category_id`). Pattern: създаваш `res.groups.privilege` с `category_id=ref('module_category_X')`, после групите имат `privilege_id=ref('res_groups_privilege_X')`.

Matched tokens: `category_id`

### From `git_log` (2)

#### Fix: [IMP] hr_rfid,hr_rfid_portal: Update translations and fix alert roles
<!-- source: git_log ref: 0a2d81d00b460beeae9cf92591d50a5dfe2accd8 occ: 1 conf: 0.60 -->

Commit `0a2d81d00b` (2026-03-25): [IMP] hr_rfid,hr_rfid_portal: Update translations and fix alert roles

#### Fix: [FIX] hr_rfid_odoo_import: Improve data completeness and fix multi-compa
<!-- source: git_log ref: b839ce5dc2833045ca8a15ed9f7a5ab2d67cd6fd occ: 1 conf: 0.60 -->

Commit `b839ce5dc2` (2026-03-19): [FIX] hr_rfid_odoo_import: Improve data completeness and fix multi-company import


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_odoo_import`
- Source digest: `sha256:86334d3d301325831b66950d340668e21d02ad47b8ffe17b5d658ec29db2f443`
- Generated at: `2026-05-14T11:16:45+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)

## The phase registry

Phases are classes in `models/importers/`, each declaring what it needs:

| Attribute | Meaning |
|---|---|
| `PHASE_ID`, `NAME` | identity in the transfer log |
| `REQUIRES_SOURCE` | module names the SOURCE must have installed |
| `REQUIRES_TARGET` | model names, or `(model, field)` pairs, this system needs |
| `OPTION` / `OPTION_ANY` | key(s) in the options dict that switch it on |
| `WEIGHT` | share of the progress range |

`registry()` returns them in execution order; the order carries meaning and is
asserted by tests, not by comments. `phase_plan(env, options, source_modules)`
is a pure function returning `[(class, skip_reason_or_None)]` - no network, no
writes - which is what makes the gate testable without a source system.

`source_probe_modules()` derives the list of modules asked of the source from
the phases themselves. A list maintained anywhere else falls behind: that is
how the camera module went unqueried and the whole camera dataset was silently
left behind while the run reported success.

`_target_available` refuses abstract and transient models (they resolve in the
registry but own no table) and accepts a `(model, field)` pair, because a model
present under the same name may still lack the column a bulk insert will write.

### Adding a phase

1. Subclass `PhaseImporter` in `models/importers/`, set the metadata, implement
   `run(wizard)` returning a list of `_make_result` dicts.
2. Add it to `build_registry()` in the position its dependencies require.
3. Add the option field to the wizard and to `_build_options`.

Nothing in the wizard needs to learn its name.

## Background execution

`hr.rfid.odoo.import.run` is a permanent record; the wizard only fills it in
and triggers the scheduler. The work cannot happen in the HTTP request - it is
cut off at `limit_time_real` (120 s by default) - and the cron thread is NOT
exempt either: `limit_time_real_cron` only replaces the limit when positive,
and exceeding it restarts the server rather than just failing the job. Hence
`PASS_SECONDS`, a safety parameter rather than a tuning knob.

Each pass works through whole phases and commits between them via
`ir.cron._commit_progress`, which also reports how much is left so core
reschedules itself. Long reads stop between pages (`BaseImporter.time_is_up`)
and the phase is marked `partial` rather than done.

Resuming safely rests on two things:

- every write path goes through an external ID, so a repeated read creates
  nothing twice;
- `_map_m2o` falls back to `ir.model.data` when the in-memory map is empty,
  which it always is in a new process. Without that fallback every relation in
  every later pass resolves to nothing and is counted as skipped - a transfer
  that loses its data and reports success.

A run untouched for `STALLED_MINUTES` is closed automatically and its stored
credentials cleared. `_abandon_stalled_runs()` RETURNS what it closed and
`_cron_process` commits that before starting the next pass: a pass rolls the
transaction back when it fails, which would otherwise undo exactly the closures
that unblock the queue, leaving the same dead runs in the way on every wake-up.

## Identity of a transferred record

**A record is recognised by its source id, carried in Odoo's own external-ID
metadata (`ir.model.data`) - never by name, serial, e-mail or card number.**
There is no separate register: the "ledger" of earlier versions was always
`ir.model.data`, and the word has been dropped because it named a thing that
does not exist.

| Piece | Where | Value |
|---|---|---|
| `EXTERNAL_ID_MODULE` | `models/importers/base_importer.py` | `'__import__'` - what core's own `BaseModel.load()` writes for imported rows |
| `EXTERNAL_ID_PREFIX` | same | `'rfid_import_'` |
| `_xml_id_name(model_prefix, source_id)` | `BaseImporter` | `rfid_import_{source_slug}_{model_prefix}_{source_id}` |
| `normalise_source_slug(value)` | module-level function | `-` and `.` to `_`; an external-ID name may not carry dots, so every producer and every reader must apply the SAME rule or a check answers about one spelling while the transfer writes another |

`source_slug` is the identity of the SOURCE SYSTEM. It defaults to the source
database name and is overridable on the wizard (`source_slug`, "Source
Identity") for the case that made it necessary: the same installation read from
two places - a restored backup for the bulk, then the live server for the
delta - must write ONE set of ids. Two names for one system means nothing
matches and everything arrives twice; measured on the o15 cloud, 298 937
duplicated events alone.

Helpers (renamed from the `*_ledger` names, same behaviour):

- `find_by_external_id(model, source_id, expect_text=None, text_field='name')` -
  the only identity lookup. `expect_text` is a SECOND check on the record
  already found by id: a mismatch is reported, never used to search elsewhere.
  `find_by_ledger` remains as a temporary alias for the camera, people and
  service importers, which have not been renamed yet.
- `prefetch_external_ids(model, source_ids)` - reads the durable half of the
  in-memory map back in one query. A new process starts with `id_map` empty, so
  without this every relation resolves to False and the row is counted as
  skipped while the protocol reads as a clean run.
- `link_existing`, `_bulk_insert_with_xmlid`, `_match_by_external_id` - all
  write or read the same names.

### What a second run does

`_load_records` looks the external ID up first and WRITES to the record it
names, so a second run **refreshes from the source**. The `'noupdate': True`
carried in `data_list` is recorded on the metadata row but changes nothing
here: core honours it only when called with `update=True`
(`if not (update and d_noupdate)`), and this call does not. That is the owner's
decision, not an accident - so the wizard says it out loud before the start
(`_warn_about_refresh_on_rerun`), in three parts that are each true of the code:

- equipment and cards are written again (put back to the source's version);
- people, contacts, departments, staff tags, card types, access groups and
  sites are recognised and left alone (the write is never reached);
- a list the source keeps as a whole - an access group's DEPARTMENTS, the
  groups it inherits, the doors a reader serves - is written back whole, so an
  entry added here is taken out again. The DOORS of an access group are not
  such a list: they are permissions of their own and are only ever added.

Regression tests for each clause:
`tests/test_second_run_changes_nothing.py`.

### Recognising another system's records

`_warn_about_other_source_identity` asks the question the only way that can be
answered: for each identity a transfer started IN THIS DATABASE has read
(`hr.rfid.odoo.import.run` is the permanent account of that), is anything from
it still here (`_holds_records_from`, one `=like` per identity). It does NOT
sample what is already present - a sample answers with whichever rows it meets
first, so in a database that also holds a large import from another tool the
one name that matters can fall outside it. Reading a sample also cannot tell
this module's records from the Andromeda or old-cloud imports, which write the
same module with names of their own; asking "which systems have WE read" can.

Empty box + records from another identity = `danger`, which blocks the start.
Filling the box IS the decision, so it drops to `warning` and the transfer
proceeds.

## Attendance brought over is never rebuilt

`models/hr_employee.py` implements `hr.employee._check_recalc_allowed` (the
hook declared in `hr_rfid`) and refuses when the requested window holds
attendance carrying this transfer's external ID.

- Detection is ONE query: the external IDs are used as a sub-select
  (`ir.model.data` has no link back to attendance), matched on
  `EXTERNAL_ID_NAME_PATTERN` = `rfid_import_%_hr_attendance_%` - the module
  alone would also match an ordinary spreadsheet import.
- The window comes from the rebuild itself (`_recalc_window`), so the two
  cannot drift; people are grouped by timezone to keep it to one query.
- The `ir.model.data` side is read `sudo()` (not readable by whoever runs a
  rebuild); the attendance side is read with the CALLER's rights, so the
  refusal is about exactly the records the rebuild would have deleted and no
  name from another company leaks into the message.
- Why refuse at all: the rebuild deletes the record together with its metadata
  row, so the next transfer no longer recognises the row it already brought
  over and adds it a second time. The message tells the operator to run the
  transfer again instead.

Tests: `tests/test_recalc_guard.py` - refused at the wizard button with nothing
queued, and a run driven through `_cron_process` ending `refused` with the
attendance AND its `ir.model.data` row untouched.

## Reference data vs migrated data

Records shipped with a module - card types being the case in point - exist on
both sides under the same external id. `_match_by_external_id` links them
instead of creating copies. Creating a second "License Plate" makes plate
numbers land on a type the card validation does not recognise as plates, and
every plate is then refused for "digits must be from 0 to 9", taking the camera
links with them.

## Talking to hardware

`IMPORT_CONTEXT` carries `no_hardware_commands`, honoured by `hr_rfid` and, as
of 19.0.1.12.0, by `polimex_ip_cam`. The guard sits on `cctv.camera.command`
itself as well as on the callers, because `queue_send` registers a postcommit
hook and postcommit hooks survive a savepoint rollback - a rolled-back phase
would otherwise still have fired at the cameras.

Any new write in an importer must carry this context. The site phase originally
did not, and its access-group cascade reached live cameras through three
separate paths.

