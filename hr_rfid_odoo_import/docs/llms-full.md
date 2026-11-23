---
id: hr_rfid_odoo_import
title: RFID Odoo Data Import
module: hr_rfid_odoo_import
module_version: 19.0.3.1.6
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Import RFID access control data from older Odoo instances (v14-v18)
last_updated: '2026-11-23'
source_digest: sha256:6aa5dabbb84ba5a4e299c9020208831bc90ed73dcb8aa67d117389a711b185ff
depends:
- hr_rfid
entities:
  primary: hr.rfid.odoo.import.wiz
  related:
  - hr.employee
  - hr.rfid.odoo.import.conflict
  - hr.rfid.odoo.import.log
  - hr.rfid.odoo.import.company.line
  - hr.rfid.odoo.import.run
keywords:
- access
- company
- conflict
- control
- data
- employee
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
  models: 6
  views: 3
  access_rules: 5
  record_rules: 0
  crons: 1
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


# RFID Odoo Data Import - `hr_rfid_odoo_import` v19.0.3.1.6

Import RFID access control data from older Odoo instances (v14-v18)

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_odoo_import`
- **Version**: `19.0.3.1.6`
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
* **A stay is never recorded twice** - an attendance of the other system that
  would overlap one already recorded here is not brought over, by the same rule
  Odoo itself applies to two stays of one person. One that is the same to the
  second is counted as already here. One that differs is left out, and what is
  recorded here stays as it is; the protocol names the people, and the
  downloaded protocol lists every such stay with both times, in the person's
  own time zone, for the people who keep the records to look at. A later run
  checks again, so a stay left out today arrives once nothing here collides
  with it any more.
* **An account of what happened** - one line per step, including what was left
  behind and why, written in the language of the person who started the
  transfer
* **A final check against the other system** - every kind of data is counted
  on both sides, company by company. A difference counts as a problem only in
  what this transfer was asked to bring: in a kind left unticked it is shown as
  a remark, with both numbers, and the transfer still finishes. A record of a
  person (or other owner) who is not in this system, of a kind left unticked,
  is said the same way

Configuration
=============

No special configuration is needed. The module adds a menu entry under
**RFID System -> Hardware Manager -> Import from Odoo**.

Usage
=====

1. Go to **RFID System -> Hardware Manager -> Import from Odoo**.
2. Enter the address of the other system and an account that can read it. That
   account needs to be able to see everything you want moved - including the
   camera passwords, if you have cameras. The address can be typed as in a
   browser: `192.168.1.10:8069` becomes `http://192.168.1.10:8069`. A server
   reached over https needs `https://` typed in front.

   - **Source identity** on the same page is normally left empty: the transfer
     then files everything under the name of the database it read, which is
     right for a one-off move. Fill it in when you read the SAME system from
     two places - a restored backup for the bulk of it, then the live server
     for what changed since. Both transfers must carry the same identity, or
     the second one treats the live server as a different system and brings
     everything across a second time.
   - If this database already holds records from another system, you are told
     so before you start, with the name that system was filed under. Leave the
     box empty and the transfer will not start: put the earlier name in it if
     it is the same system, or type a name of your own to say it is a
     different one.

3. Press **Check Connection**. The wizard then lists the companies it found.
4. Pick which company to bring across and which company here it becomes.
5. Choose what to include. Anything the other system does not keep, or this one
   cannot receive, is shown with the reason and cannot be ticked.
6. Review the summary. Records that would clash with something already here are
   listed for you to decide about; the transfer will not start until you have.
7. Press **Start Import**. The transfer opens on its own page and continues in
   the background - close the page whenever you like.
8. Come back to **RFID System -> Hardware Manager -> Data Transfers** to see how far it got and, line by
   line, what it moved and what it did not.

What it brings across
=====================

- Equipment: communication modules, controllers, doors, readers, working times
- People: employees, contacts, departments, tags
- Zones, and who belongs to them
- Sites: the whole tree, the equipment on it, the contacts in it
- Access groups and their door, employee and contact assignments
- Cards, including vehicle plates
- Cameras: their settings, the serial numbers they are recognised by, their
  readers and doors, and their plate lists
- History: card events, system events, recognised plates, temperature logs
- Vending, attendance and visitor services, when both systems have them

Common questions
================

**Can I run it twice?** Yes, as often as you like - nothing is ever brought
across a second time. What a repeat transfer does to what is already here is
not the same for everything, and the summary page says so before you start:
the equipment and the cards are put back to what the other system holds, so a
card switched off here comes back on and a door renamed here gets its old name
back. People, contacts, departments and access groups keep the details
corrected here. A list the other system keeps - the departments of an access
group, the doors a reader serves - is rebuilt from it, so an entry added here
is taken out again. No record is deleted.

**What if a person already has attendance here for the same time?** The
attendance from the other system is not brought over - a day is never counted
twice. If it is exactly the same, it is counted as already here. If it is
different, the attendance recorded here stays as it is, and the transfer's
summary names the people; the downloaded protocol lists every such case with
both times, so the people who keep the records can look at them. A later
transfer checks again, so once the record here is put right, the next run
brings the other system's attendance across.

**I transferred only the attendance - why does the last check list people and
events?** The last check compares everything the two systems hold, company by
company, because the numbers are worth knowing. A difference in something you
did not tick is a remark, not a problem, and the transfer still ends as
finished. The same goes for an attendance of a person who is not in this
system when people were not part of the transfer: it cannot come across, and
the check says how many there are. A difference in what you did tick is a
problem, and the transfer says so.

**What language is the summary in?** The language of the person who started
the transfer.

**Transferred attendance shows 0 hours worked - what do I do?** Run the
transfer again with only "Import attendance" ticked. The attendance of the
people it brings into this company then gets its hours worked out, whatever
its date, including attendance an earlier transfer left at 0. The line "Worked
Hours" in the protocol says how many were put right.

- Days from before a person was set up here (their first contract version)
  get their hours worked, and no overtime: there is no working schedule for
  them yet, so nothing can be extra. This is also where Odoo's own
  "Regenerate overtimes" stops.
- Days from after that also get their extra and regular hours. Overtime a
  manager has already approved or refused on another day keeps that decision.
  A day, or a week under a weekly rule, that holds both a transferred stay and
  one recorded here is worked out again as a whole, as Odoo does whenever a
  stay of that day changes.
- Records already right are not changed.

If the hours of some people cannot be worked out, the same line names them,
the first day concerned and what the system answered. Put those days right,
then run the transfer again the same way.

**What if it is interrupted?** It carries on from where it stopped. A transfer
that has not moved for half an hour is closed automatically and its stored
credentials are cleared; start a new one and it will pick up the remainder.

**Why does a step say "Partly"?** Some of the records of that kind did not
arrive - usually because what they point at was left out of this transfer. The
line says how many.

**Do the cameras start working straight away?** They keep working throughout,
but they still hold their old plate lists. Refresh each camera's list once the
transfer is done.

**Nothing at all came across for one kind of record.** That is shown as a
fault. Look at the step just above it: what those records point at is probably
missing.

**Can I rebuild the attendance that came across?** No, and the attempt is
refused rather than half done. Attendance brought over is a copy of what the
other system recorded: it cannot be worked out again from door events here -
those events may not have come along, and the old system may have been
corrected by hand - and rebuilding it would break the link that lets a later
transfer recognise it, so the next transfer would bring it over a second time.
To refresh that data, run the transfer again. Attendance recorded HERE is
rebuilt as normal; the refusal names the people it concerns, so you can rebuild
a period, or a set of people, that does not include them.

**Does a big customer finish?** Yes, and that is what the passes are for: every
long read remembers where it got to, so the next pass carries on instead of
starting over. Measured on a 27-tenant cloud - 6 176 people, 289 847 access
events, 280 046 vending entries, 200 004 temperature readings - the whole of it
comes across, and each line of the protocol counts the WHOLE transfer rather
than the slice of the last pass.

**A step says the other system keeps no such thing.** Older versions really do
keep less: Odoo 14 has no daily working-time roll-ups at all, for instance. The
line says so and the transfer carries on; the attendances themselves still come
across.

**The final check names things that were already wrong.** It says which of them
the other system has as well - those are carried over as they stand, not caused
by the transfer. Anything it does NOT attribute to the other system appeared
here and is worth looking at.

**Why are there still sixteen time schedules and not thirty-two?** Because this
system makes its own set for every company, and the transfer adopts the
schedule sitting in each slot instead of creating a second one beside it. One
record per slot is the only way a door permission can mean one thing.

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


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_odoo_import --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:51`.  Model.  Inherits: `hr.employee`.

#### Notable methods

- **`_transferred_attendance_message(self, groups, total)`** - decorators: `@api.model`
  - What the operator is told, in their own terms.

### `hr.rfid.odoo.import.conflict` <a id='model-hr-rfid-odoo-import-conflict'></a>
Python class `HrRfidOdooImportConflict` in `models/import_conflict.py:7`.  TransientModel (wizard).  Description: *RFID Odoo Import Conflict*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `wizard_id` | Many2one → \`hr.rfid.odoo.import.wiz\` | Wizard | ✓ | ✓ | Parent import-run wizard this conflict belongs to. |
| `source_model` | Char | Model |  | ✓ | Odoo model name of the conflicting record (e.g. hr.rfid.card, res.partner). |
| `source_id` | Integer | Source ID |  | ✓ | Database ID of the record on the source instance. |
| `source_name` | Char | Source Record |  | ✓ | Display name of the record on the source instance - shown so the operator can id |
| `source_ref` | Char | Unique Key |  | ✓ | The natural key that triggered the conflict (e.g. card number, EGN). Both sides  |
| `target_id` | Integer | Target ID |  | ✓ | Database ID of the matching record on this (target) instance. |
| `target_name` | Char | Existing in Target |  | ✓ | Display name of the existing target record - operator decides whether to keep it |
| `conflict_field` | Char | Conflict Field |  | ✓ | Field on which the two records collide (typically the unique constraint that fir |
| `resolution` | Selection | Resolution |  | ✓ | What to do with this conflict during the import - Link: treat the existing recor |

### `hr.rfid.odoo.import.log` <a id='model-hr-rfid-odoo-import-log'></a>
Python class `HrRfidOdooImportLog` in `models/import_conflict.py:62`.  Model.  Description: *RFID Odoo Import Log*.  Default order: `id`.

> What happened, step by step - kept, not cleaned away.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `run_id` | Many2one → \`hr.rfid.odoo.import.run\` | Run |  | ✓ | The transfer this line belongs to. |
| `phase` | Char | Phase |  | ✓ | Stage of the import pipeline (e.g. 'companies', 'access_groups', 'users', 'event |
| `model` | Char | Model |  | ✓ | Odoo model processed during this phase. |
| `source_count` | Integer | Source Count |  | ✓ | Number of records the source instance reported for this model+phase. |
| `imported_count` | Integer | Imported |  | ✓ | Number of records actually created in the target during this phase. |
| `skipped_count` | Integer | Skipped |  | ✓ | Number of records skipped (operator chose Skip in conflicts, or validation rejec |
| `rejected_count` | Integer | Rejected |  | ✓ | Number of records the database refused because another record already holds the  |
| `linked_count` | Integer | Linked |  | ✓ | Number of source records mapped to an existing target record instead of being cr |
| `status` | Selection | Status |  | ✓ | How this step ended. Done: everything the other system had came across. Partly:  |
| `duration` | Float | Duration (s) |  | ✓ | Wall-clock seconds this phase took. Useful to spot slow phases for the next run. |
| `error_message` | Text | Error |  | ✓ | Error message captured if the phase status is Error - full traceback for debuggi |

### `hr.rfid.odoo.import.company.line` <a id='model-hr-rfid-odoo-import-company-line'></a>
Python class `HrRfidOdooImportCompanyLine` in `models/import_conflict.py:153`.  TransientModel (wizard).  Description: *RFID Odoo Import Company Mapping*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `wizard_id` | Many2one → \`hr.rfid.odoo.import.wiz\` | Wizard | ✓ | ✓ | Parent import-run wizard this company mapping belongs to. |
| `source_id` | Integer | Source Company ID |  | ✓ | res.company ID on the source instance - the natural key used to match across ins |
| `source_name` | Char | Source Company |  | ✓ | Display name of the company on the source instance - shown for operator cross-ch |
| `do_import` | Boolean | Import |  | ✓ | Untick to skip this source company entirely. Useful when you only want to migrat |
| `target_company_id` | Many2one → \`res.company\` | Target Company |  | ✓ | Which company here receives this tenant's data. It must already exist - create i |

### `hr.rfid.odoo.import.run` <a id='model-hr-rfid-odoo-import-run'></a>
Python class `HrRfidOdooImportRun` in `models/import_run.py:40`.  Model.  Inherits: `mail.thread`.  Description: *RFID Data Transfer*.  Default order: `create_date desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | Short label of this transfer, built from the source it reads. |
| `state` | Selection | State | ✓ | ✓ | Where this transfer has got to. It continues on its own; you can close the page. |
| `user_id` | Many2one → \`res.users\` | Started by | ✓ | ✓ | Who started the transfer. The work runs in the background, so this is who gets t |
| `source_url` | Char | Source Url | ✓ | ✓ | Address of the system being read. |
| `source_db` | Char | Source Db |  | ✓ | Which database on that system. |
| `source_login` | Char | Source Login | ✓ | ✓ | Account used to read it. |
| `source_password` | Char | Source Password |  | ✓ | Password for that account. Kept only while the transfer runs and cleared the mom |
| `source_uid` | Integer | Source Uid |  | ✓ | Internal id of that account, from the login. |
| `source_slug` | Char | Source Slug |  | ✓ | Which source system these records are recorded against. Left empty it follows th |
| `installed_modules_json` | Text | Installed Modules Json |  | ✓ | What the other system was found to keep. |
| `options_json` | Text | Options Json |  | ✓ | What the operator chose to bring across. |
| `company_map_json` | Text | Company Map Json |  | ✓ | Which company on the other side becomes which here. |
| `resolution_json` | Text | Resolution Json |  | ✓ | Decisions the operator made about records that clash with existing ones. |
| `done_phases_json` | Text | Done Phases Json |  | ✓ | Which steps have already finished, so a resumed transfer does not repeat them. |
| `read_cursors_json` | Text | Read Cursors Json |  | ✓ | How far each long read got, so the next pass carries on instead of reading the s |
| `step_totals_json` | Text | Step Totals Json |  | ✓ | Running totals of the resumable steps. A pass counts only the slice it read itse |
| `current_phase` | Char | Current Phase |  | ✓ | The step being worked on right now. |
| `done_count` | Integer | Done Count |  | ✓ | Steps finished. |
| `total_count` | Integer | Total Count |  | ✓ | Steps in total. |
| `progress` | Integer | Progress |  | - | How far along the transfer is. |
| `log_ids` | One2many → \`hr.rfid.odoo.import.log\` | What happened |  | ✓ | One line per step, with what came across and what did not. |

#### Notable methods

- **`_compute_name(self)`** - decorators: `@api.depends`
- **`_compute_progress(self)`** - decorators: `@api.depends`
- **`action_start(self)`** - decorators: -
  - Ask for the work to begin. Returns at once.
- **`action_refresh(self)`** - decorators: -
  - Show what the worker has done since the page was opened.
- **`action_download_protocol(self)`** - decorators: -
  - The whole protocol as one plain-text file the operator can send.
  - touches: `ir.attachment`
- **`_cron_process(self)`** - decorators: `@api.model`
  - One pass of work. Called by the scheduler.
  - effects: `log_error`
  - touches: `hr.rfid.odoo.import.run`
- **`_abandon_stalled_runs(self)`** - decorators: `@api.model`
  - End transfers that stopped being worked on, and drop their password.
  - effects: `log_warn`

### `hr.rfid.odoo.import.wiz` <a id='model-hr-rfid-odoo-import-wiz'></a>
Python class `HrRfidOdooImportWiz` in `models/import_wizard.py:32`.  TransientModel (wizard).  Description: *Import RFID Data from Odoo*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `state` | Selection | State | ✓ | ✓ | Step the wizard is currently on - Connection: enter source URL + creds. Configur |
| `source_url` | Char | Source URL | ✓ | ✓ | Full URL of the source Odoo server, e.g. https://erp.example.com |
| `source_db` | Char | Source Database |  | ✓ | Leave empty if the source server hosts a single database - it will be auto-detec |
| `source_slug` | Char | Source Identity |  | ✓ | Which system the records come from. Leave it empty and it follows the name of th |
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
| `import_sites` | Boolean | Import sites |  | ✓ | Include the tree of sites, the equipment assigned to them and the contacts that  |
| `import_cameras` | Boolean | Import cameras |  | ✓ | Include ANPR cameras, the readers and doors that belong to them, and the plate l |
| `import_leaves` | Boolean | Import leaves |  | ✓ | Include leave types, approved allocations and the absences themselves (approved  |
| `import_all_partners` | Boolean | Import all partners |  | ✓ | Import all partners from selected companies, not just RFID-linked ones. |
| `import_all_employees` | Boolean | Import all employees |  | ✓ | Import all employees from selected companies, not just RFID-linked ones. |
| `import_images` | Boolean | Import photos |  | ✓ | Import employee and partner photos (may slow down import). |
| `import_users` | Boolean | Create users |  | ✓ | Create res.users for imported employees (matched by login or created with temp p |
| `import_user_groups` | Boolean | Transfer user groups |  | ✓ | Copy security group assignments from source users (matched by xml_id). |
| `import_user_events` | Boolean | Import user events |  | ✓ | Include the historical hr.rfid.event.user log. Can be large - disable for first  |
| `import_system_events` | Boolean | Import system events |  | ✓ | Include the historical hr.rfid.event.system log (controller power loss, tamper,  |
| `import_th_logs` | Boolean | Import temperature/humidity logs |  | ✓ | Include temperature-controller log records. Disable unless the source actually u |
| `event_date_from` | Date | Events from date |  | ✓ | Only import events newer than this date. Leave empty for all events. |
| `orphan_event_cutoff` | Date | Module-only events from date |  | ✓ | Some system events are recorded against the communication module alone, with no  |
| `import_vending` | Boolean | Import vending data |  | ✓ | Include vending balances, history and events. Only visible if both source and ta |
| `import_attendance` | Boolean | Import attendance |  | ✓ | Include hr.attendance records linked to RFID events. |
| `import_attendance_extra` | Boolean | Import attendance extra |  | ✓ | Include the daily roll-ups produced by hr_attendance_late (late/overtime/extra t |
| `import_service` | Boolean | Import service data |  | ✓ | Include rfid.service catalog and rfid.service.sale records from the source. |
| `source_has_vending` | Boolean | Source Has Vending |  | ✓ | Source instance has the hr_rfid_vending module installed (detected from Test Con |
| `source_has_attendance` | Boolean | Source Has Attendance |  | ✓ | Source instance has hr_attendance_multi_rfid installed. |
| `source_has_attendance_late` | Boolean | Source Has Attendance Late |  | ✓ | Source instance has hr_attendance_late installed. |
| `source_has_service` | Boolean | Source Has Service |  | ✓ | Source instance has rfid_service_base installed. |
| `target_has_vending` | Boolean | Target Has Vending |  | - | This (target) instance has hr_rfid_vending installed - the related import_vendin |
| `target_has_attendance` | Boolean | Target Has Attendance |  | - | This (target) instance has hr_attendance_multi_rfid installed. |
| `target_has_attendance_late` | Boolean | Target Has Attendance Late |  | - | This (target) instance has hr_attendance_late installed. |
| `target_has_service` | Boolean | Target Has Service |  | - | This (target) instance has rfid_service_base installed. |
| `warnings` | Json | Warnings |  | - | Pre-flight warnings calculated from the configuration (e.g. asked to import vend |
| `has_blocking` | Boolean | Has Blocking |  | - | True while something must be sorted out before the transfer can start. |
| `has_advisory` | Boolean | Has Advisory |  | - | True when there is something worth knowing that does not stop the transfer. |
| `blocking_html` | Html | Blocking Html |  | - | What must be sorted out first, written for the operator to read. |
| `advisory_html` | Html | Advisory Html |  | - | What is worth knowing before starting, written for the operator to read. |
| `preview_text` | Text | Preview |  | ✓ | Human-readable summary of what will be created/linked if the operator confirms.  |
| `conflict_ids` | One2many → \`hr.rfid.odoo.import.conflict\` | Conflicts |  | ✓ | Per-record collisions detected against the target. Operator must pick a resoluti |
| `dry_run` | Boolean | Full dry-run |  | ✓ | Execute full import + rollback to verify everything works. |
| `progress_text` | Text | Progress |  | ✓ | Live status of the running import job (current phase, processed records). Update |
| `progress_percent` | Float | Progress % |  | ✓ | Estimated completion percentage. Driven by the phase log - useful for the operat |
| `error_message` | Text | Error |  | ✓ | Top-level error captured if the run aborted mid-way. Individual phase errors are |

#### Notable methods

- **`_compute_warning_render(self)`** - decorators: `@api.depends`
  - Render the warnings as something a person can read.
- **`_compute_warnings(self)`** - decorators: `@api.depends`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
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
  - effects: `raise:UserError`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_employee.py`

- **`ATTENDANCE_MODEL`** *(scalar)* = `'hr.attendance'`  - line 33
- **`EXTERNAL_ID_NAME_PATTERN`** *(expression)* = `'%s%%_%s_%%' % (EXTERNAL_ID_PREFIX, ATTENDANCE_MODEL.replace('.', '_'))`  - line 40
- **`NAMES_SHOWN`** *(scalar)* = `3`  - line 44
- **`DEFAULT_LOOKBACK_DAYS`** *(scalar)* = `30`  - line 48

### `models/import_run.py`

- **`PASS_SECONDS`** *(scalar)* = `5.0`  - line 32
- **`STALLED_MINUTES`** *(scalar)* = `30`  - line 37

### `models/importers/attendance_importer.py`

- **`ATTENDANCE_CURSOR`** *(scalar)* = `'attendance:hr.attendance'`  - line 21
- **`FIGURES_KEY`** *(scalar)* = `'attendance:figures'`  - line 24
- **`FIGURE_TOLERANCE`** *(scalar)* = `0.0005`  - line 27
- **`REGULAR_HOURS_DISAGREE`** *(expression)* = `SQL('abs(COALESCE(a.expected_hours, 0) - (a.worked_hours - COALESCE(a.overtime_hours, 0))) > %s', FIGURE_TOLERANCE)`  - line 32
- **`PEOPLE_NAMED`** *(scalar)* = `5`  - line 38
- **`FIGURES_DATA_ERRORS`** *(collection)* = `(UserError, psycopg2.IntegrityError, psycopg2.DataError)`  - line 42
- **`FIGURES_TIMES`** *(collection)* = `['check_in', 'check_out']`  - line 45
- **`SAME_HERE_KEY`** *(scalar)* = `'same_here'`  - line 49
- **`DIFFERS_KEY`** *(scalar)* = `'differs'`  - line 53
- **`EXTRA_OPTIONAL_FIELDS`** *(collection)* = `['for_date', 'shift_number', 'actual_work_time', 'actual_work_time_day', 'actual_work_time_night', 'theoretical_work_time', 'late_time', 'early_come_time', 'early_leave_time', 'overtime', 'overtime_night', 'extra_time', 'extra_night']`  - line 103

### `models/importers/base_importer.py`

- **`EXTERNAL_ID_MODULE`** *(scalar)* = `'__import__'`  - line 15
- **`EXTERNAL_ID_PREFIX`** *(scalar)* = `'rfid_import_'`  - line 20
- **`MAX_REJECT_PROBES`** *(scalar)* = `10`  - line 25
- **`IMPORT_CONTEXT`** *(collection)* = `{'no_hardware_commands': True, 'tracking_disable': True, 'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_activity_automation_skip': True, 'no_reset_password': True}`  - line 39

### `models/importers/camera_importer.py`

- **`SAFE_LIST_CATEGORY`** *(scalar)* = `'blacklist'`  - line 27
- **`KNOWN_LIST_CATEGORIES`** *(collection)* = `('whitelist', 'blacklist')`  - line 28

### `models/importers/consistency_importer.py`

- **`NAMED_OFFENDERS`** *(scalar)* = `8`  - line 23

### `models/importers/core_importer.py`

- **`CTRL_OPTIONAL_FIELDS`** *(collection)* = `['serial_number', 'hw_version', 'sw_version', 'mode', 'external_db', 'max_cards_count', 'max_events_count', 'readers', 'time_schedules', 'io_table_lines', 'alarm_lines', 'temperature', 'humidity', 'system_voltage', 'input_voltage', 'emergen  # ...truncated`  - line 23

### `models/importers/leave_importer.py`

- **`LEAVE_STATES`** *(collection)* = `('confirm', 'validate1', 'validate')`  - line 26
- **`NEEDS_BALANCE_WORDS`** *(collection)* = `{'yes': True, 'true': True, '1': True, 'no': False, 'false': False, '0': False, '': False, 'fixed': True, 'fixed_allocation': True, 'unlimited': False}`  - line 36

### `models/importers/phase.py`

- **`_REGISTRY`** *(scalar)* = `None`  - line 226

### `models/importers/reconcile_importer.py`

- **`NAMED_TENANTS`** *(scalar)* = `6`  - line 43
- **`KIND_LABELS`** *(collection)* = `{'hr.rfid.webstack': _lt('communication modules'), 'hr.rfid.ctrl': _lt('controllers'), 'hr.rfid.door': _lt('doors'), 'hr.rfid.reader': _lt('readers'), 'hr.rfid.time.schedule': _lt('time schedules'), 'hr.rfid.access.group': _lt('access group  # ...truncated`  - line 50
- **`CARRYABLE_LEAVE_STATES`** *(collection)* = `['confirm', 'validate1', 'validate']`  - line 75
- **`RECONCILED`** *(collection)* = `[('hr.rfid.webstack', '', 'import_hardware'), ('hr.rfid.ctrl', 'webstack_id', 'import_hardware'), ('hr.rfid.door', 'controller_id.webstack_id', 'import_hardware'), ('hr.rfid.reader', 'controller_id.webstack_id', 'import_hardware'), ('hr.rfi  # ...truncated`  - line 94
- **`CARRIED_BY`** *(expression)* = `{entry[0]: entry[2] for entry in RECONCILED}`  - line 125
- **`OWNED_BY`** *(collection)* = `{'hr.rfid.access.group.employee.rel': [('employee_id', 'hr.employee')], 'hr.rfid.access.group.contact.rel': [('contact_id', 'res.partner')], 'hr.rfid.card': [('employee_id', 'hr.employee'), ('contact_id', 'res.partner')], 'hr.attendance': [  # ...truncated`  - line 133
- **`OWNER_CARRIED_BY`** *(collection)* = `{'hr.employee': 'import_people', 'res.partner': 'import_people'}`  - line 146
- **`OWNER_LABELS`** *(collection)* = `{'hr.employee': KIND_LABELS['hr.employee'], 'res.partner': _lt('contacts')}`  - line 149

### `models/importers/vending_importer.py`

- **`EMPLOYEE_VENDING_FIELDS`** *(collection)* = `['hr_rfid_vending_in_attendance', 'hr_rfid_vending_limit', 'hr_rfid_vending_balance', 'hr_rfid_vending_auto_refill', 'hr_rfid_vending_refill_amount', 'hr_rfid_vending_refill_type', 'hr_rfid_vending_refill_max', 'hr_rfid_vending_negative_bal  # ...truncated`  - line 20
- **`AUTO_REFILL_OPTIONAL_FIELDS`** *(collection)* = `['auto_refill_total', 'create_date']`  - line 32


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`source_address(value)`** - `models/import_wizard.py:15`
  - The address of the other server, as the connection needs it.
- **`AccessImporter.run(self, wizard)`** - `models/importers/access_importer.py:29`
  - Execute Phase 4. Each step stands on its own.
- **`DoorRelFinisher.run(self, wizard)`** - `models/importers/access_importer.py:712`
- **`refused_beside(start, stop, other_start, other_stop)`** - `models/importers/attendance_importer.py:56`
  - Whether core refuses a stay of a person beside another of theirs.
- **`people_by_id(env, ids)`** - `models/importers/attendance_importer.py:83`
  - {id: employee} for the protocol: archived people included, deleted ones left out.
  - effects: `with_context`
- **`AttendanceImporter.run(self, wizard)`** - `models/importers/attendance_importer.py:131`
  - Execute Phase 6b.
- **`normalise_source_slug(value)`** - `models/importers/base_importer.py:28`
  - The source identity as it appears inside an external ID.
- **`BaseImporter.accumulate(self, key, **counts)`** - `models/importers/base_importer.py:401`
  - Add this pass's slice to the step's running totals; return them.
- **`BaseImporter.read_is_finished(self, cursor_key)`** - `models/importers/base_importer.py:413`
  - Whether that read has reached the end of the source.
- **`BaseImporter.accumulated_result(self, cursor_key, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='', rejected_count=0)`** - `models/importers/base_importer.py:422`
  - One protocol row for a RESUMABLE step - counting the whole transfer.
- **`BaseImporter.progress_snapshot(self)`** - `models/importers/base_importer.py:448`
  - Where every read got to and what every step has counted, copied.
- **`BaseImporter.restore_progress(self, snapshot)`** - `models/importers/base_importer.py:460`
  - Put the reading position and the counts back where they were.
- **`BaseImporter.rewind_cursors(self, *cursor_keys)`** - `models/importers/base_importer.py:468`
  - Forget where the named reads got to, so they start over.
- **`BaseImporter.already_imported(self, model, source_ids)`** - `models/importers/base_importer.py:698`
  - Map source ids that were already imported to their target ids.
  - effects: `sql`
- **`BaseImporter.prefetch_external_ids(self, model, source_ids)`** - `models/importers/base_importer.py:765`
  - Load what a previous pass already imported into the in-memory map.
- **`BaseImporter.find_by_external_id(self, model, source_id, expect_text=None, text_field='name')`** - `models/importers/base_importer.py:782`
  - The only identity allowed: the source id, through its external ID.
  - effects: `log_warn`, `with_context`
- **`BaseImporter.link_existing(self, model, source_id, target_id)`** - `models/importers/base_importer.py:824`
  - Record a source->target mapping for a record we did NOT create.
  - effects: `sql`
- **`BaseImporter.adopt_existing(self, model, source_id, record)`** - `models/importers/base_importer.py:1089`
  - Attach the transfer identity to a record the TARGET's own automation created - instead of building a twin next to it.
  - effects: `log_info`
  - touches: `ir.model.data`
- **`BaseImporter.describe_unmatched_door(self, source_id)`** - `models/importers/base_importer.py:1135`
  - One sentence from the SOURCE about a door we could not match.
  - effects: `log_warn`, `with_context`
  - touches: `hr.rfid.door`
- **`BaseImporter.note_skip(self, model, source_id, count=1)`** - `models/importers/base_importer.py:1376`
  - Remember why a row was left behind, for the current protocol line.
- **`BaseImporter.note_skip_reason(self, text, count=1)`** - `models/importers/base_importer.py:1388`
  - Free-text variant for causes that are not a missing record.
- **`BaseImporter.first_few(self, items, describe, limit, separator='; ')`** - `models/importers/base_importer.py:1421`
  - ``items`` described one by one up to ``limit``, then "and N more".
- **`CameraImporter.run(self, wizard)`** - `models/importers/camera_importer.py:54`
- **`ConsistencyImporter.run(self, wizard)`** - `models/importers/consistency_importer.py:70`
  - effects: `log_warn`
- **`CoreImporter.run(self, wizard)`** - `models/importers/core_importer.py:48`
  - Execute Phase 1 + Phase 3.
- **`ZoneImporter.run(self, wizard)`** - `models/importers/core_importer.py:1230`
- **`IoTableImporter.run(self, wizard)`** - `models/importers/core_importer.py:1258`
  - effects: `log_warn`
- **`EventImporter.run(self, wizard)`** - `models/importers/event_importer.py:33`
  - Execute Phase 5.
- **`LeaveImporter.run(self, wizard)`** - `models/importers/leave_importer.py:59`
- **`PeopleImporter.run(self, wizard)`** - `models/importers/people_importer.py:27`
  - Execute Phase 2.
- **`PhaseImporter.run(self, wizard)`** - `models/importers/phase.py:80`
- **`PhaseImporter.steps(self, *steps)`** - `models/importers/phase.py:83`
  - Run the steps of this phase, each one on its own.
  - effects: `log_warn`
- **`registry()`** - `models/importers/phase.py:121`
  - The phases, built on first use.
- **`phase_plan(env, options, source_modules)`** - `models/importers/phase.py:150`
  - [(phase class, reason it is skipped or None)] in execution order.
- **`source_probe_modules()`** - `models/importers/phase.py:163`
  - Every module the source is asked about, derived from the phases.
- **`total_weight()`** - `models/importers/phase.py:169`
  - Sum of the phase weights, for turning them into a progress range.
- **`build_registry()`** - `models/importers/phase.py:174`
  - The phases, in the order they must run.
- **`capabilities_the_target_lacks(env, options, source_modules)`** - `models/importers/phase.py:229`
  - [(phase class, wanted)] - data the source keeps but this system cannot take over yet.
- **`ReconcileImporter.run(self, wizard)`** - `models/importers/reconcile_importer.py:168`
  - effects: `log_warn`
- **`ServiceImporter.run(self, wizard)`** - `models/importers/service_importer.py:26`
  - Execute Phase 6c.
- **`SiteImporter.run(self, wizard)`** - `models/importers/site_importer.py:48`
- **`SiteGroupImporter.run(self, wizard)`** - `models/importers/site_importer.py:257`
  - effects: `with_context`
- **`VendingImporter.run(self, wizard)`** - `models/importers/vending_importer.py:50`
  - Execute Phase 6a: Vending.

### Private helpers

- **`AccessImporter._import_access_groups(self)`** - `models/importers/access_importer.py:40`
  - Step 20: hr.rfid.access.group - TWO PASSES (inherited_ids M2M self-ref).
  - effects: `with_context`
- **`AccessImporter._import_ag_door_rels(self)`** - `models/importers/access_importer.py:127`
  - Step 21: hr.rfid.access.group.door.rel - AG↔Door relations.
- **`AccessImporter._import_ag_employee_rels(self)`** - `models/importers/access_importer.py:234`
  - Step 22: hr.rfid.access.group.employee.rel - exact copy from source.
- **`AccessImporter._copy_ag_rels_verbatim(self, model, owner_column, refused)`** - `models/importers/access_importer.py:317`
  - Copy memberships the v19 model layer refuses to create (D41).
  - effects: `log_debug`, `log_warn`, `with_context`
- **`AccessImporter._import_ag_contact_rels(self)`** - `models/importers/access_importer.py:411`
  - Step 23: hr.rfid.access.group.contact.rel - exact copy from source.
- **`AccessImporter._import_cards(self)`** - `models/importers/access_importer.py:487`
  - Step 24: hr.rfid.card - with EXACT active state from source.
- **`AccessImporter._department_second_pass(self)`** - `models/importers/access_importer.py:616`
  - Step 25: hr.department SECOND PASS - update AG back-references.
  - effects: `with_context`
- **`AttendanceImporter._import_attendance(self)`** - `models/importers/attendance_importer.py:149`
  - Step 36: hr.attendance - Direct SQL batch.
  - effects: `log_error`
- **`AttendanceImporter._leave_out_stays_recorded_here(self, columns, rows, src_ids)`** - `models/importers/attendance_importer.py:259`
  - Leave out every stay core would refuse beside what is recorded here.
- **`AttendanceImporter._stays_recorded_here(self, people, pending)`** - `models/importers/attendance_importer.py:326`
  - {person: [(check-in, check-out)]} of what this system holds near them.
  - effects: `sql`
  - touches: `hr.attendance`
- **`AttendanceImporter._companies_of(self, people)`** - `models/importers/attendance_importer.py:357`
  - {person: company} here, read once for a page.
  - effects: `sql`
- **`AttendanceImporter._remember_left_out(self, page_ids, same, differs)`** - `models/importers/attendance_importer.py:363`
  - Put a landed page's verdicts into the transfer's running totals.
- **`AttendanceImporter._differs_note(self)`** - `models/importers/attendance_importer.py:381`
  - The protocol's word on the stays left out, over the whole transfer.
- **`AttendanceImporter._person_tz(employee)`** (`@staticmethod`) - `models/importers/attendance_importer.py:413`
  - The zone core cuts this person's overtime days and weeks in.
- **`AttendanceImporter._attendance_date(self, employee_id, check_in, zones)`** - `models/importers/attendance_importer.py:423`
  - The date core gives an attendance that began at this moment.
  - effects: `sudo`
  - touches: `hr.employee`
- **`AttendanceImporter._settle_attendance_figures(self)`** - `models/importers/attendance_importer.py:444`
  - Give the transferred attendance the figures the ORM would have.
- **`AttendanceImporter._settle_people(self)`** - `models/importers/attendance_importer.py:473`
  - Work through the people whose figures do not hold, as time allows.
  - effects: `log_info`, `with_context`
  - touches: `hr.attendance`, `hr.employee`
- **`AttendanceImporter._next_person_to_settle(self, after)`** - `models/importers/attendance_importer.py:505`
  - The next person of this transfer whose figures do not hold.
  - effects: `sql`
- **`AttendanceImporter._settle_person(self, Attendance, employee)`** - `models/importers/attendance_importer.py:536`
  - Put one person's figures right. False when their rows are busy.
  - effects: `log_warn`
- **`AttendanceImporter._figures_to_settle(self, employee)`** - `models/importers/attendance_importer.py:600`
  - This person's rows whose figures do not hold, split by their cure.
  - effects: `sql`, `with_context`
- **`AttendanceImporter._note_unfigured(self, employee, rows, exc)`** - `models/importers/attendance_importer.py:649`
  - Remember, with the cursors, whose figures could not be worked out.
- **`AttendanceImporter._figures_result(self, duration)`** - `models/importers/attendance_importer.py:672`
  - The protocol line for the hours worked, over the whole transfer.
- **`AttendanceImporter._name_unfigured(self, failed)`** - `models/importers/attendance_importer.py:690`
  - Who, from which day, and what the system said - the first few.
- **`AttendanceImporter._drop_days_already_summed_here(self, columns, rows, src_ids)`** - `models/importers/attendance_importer.py:706`
  - Leave out the days this system has already summed up itself.
  - effects: `sudo`
  - touches: `hr.attendance.extra`
- **`AttendanceImporter._import_attendance_extra(self)`** - `models/importers/attendance_importer.py:768`
  - Step 37: hr.attendance.extra - Direct SQL batch.
  - effects: `log_error`
- **`BaseImporter.__init__(self, env, source_url, source_db, source_uid, source_password, company_map, options, source_slug=None)`** - `models/importers/base_importer.py:56`
- **`BaseImporter._search_read(self, model, domain, fields, order='id asc', limit=0, include_archived=True)`** - `models/importers/base_importer.py:128`
  - Read records from source via XML-RPC, as ``search`` + ``read``.
- **`BaseImporter._search_dropping_refused_filters(self, model, domain, search_kwargs)`** - `models/importers/base_importer.py:189`
  - Search, and when the source refuses a FIELD used in the filter, drop that filter - never the whole step.
  - effects: `log_warn`
- **`BaseImporter._domain_fields(domain)`** (`@staticmethod`) - `models/importers/base_importer.py:242`
  - Field names a domain filters by, dotted paths by their first hop.
- **`BaseImporter._domain_without_fields(domain, fields_)`** (`@staticmethod`) - `models/importers/base_importer.py:253`
  - The same domain minus every leaf on the given fields.
- **`BaseImporter._read_dropping_refused_fields(self, model, ids, fields, read_kwargs)`** - `models/importers/base_importer.py:274`
  - Read, and when the source refuses a FIELD, leave the field - never the records.
  - effects: `log_warn`
- **`BaseImporter._read_all(self, model, domain, fields, cursor_key, batch_size=1000)`** - `models/importers/base_importer.py:343`
  - ID-based pagination for large datasets.
  - effects: `log_info`
- **`BaseImporter._search_count(self, model, domain)`** - `models/importers/base_importer.py:480`
  - Count records in source (including archived - see SOURCE_READ_CONTEXT).
- **`BaseImporter._has_field(self, model, field_name)`** - `models/importers/base_importer.py:496`
  - Check if field exists in source model via fields_get().
- **`BaseImporter._has_stored_field(self, model, field_name)`** - `models/importers/base_importer.py:506`
  - Whether the source can actually READ that field back.
- **`BaseImporter._readable_fields(self, model, candidates)`** - `models/importers/base_importer.py:524`
  - The subset of ``candidates`` this source can actually hand over.
  - effects: `log_warn`
- **`BaseImporter._can_read_fields(self, model, fields)`** - `models/importers/base_importer.py:561`
  - Whether one row of ``model`` can be read with exactly these fields.
- **`BaseImporter._get_source_fields(self, model)`** - `models/importers/base_importer.py:579`
  - Get all source fields metadata (cached).
- **`BaseImporter._has_model(self, model)`** - `models/importers/base_importer.py:585`
  - Check if model exists in source.
- **`BaseImporter._load_records(self, model_name, data_list)`** - `models/importers/base_importer.py:598`
  - Create by external ID, or refresh what that external ID already names.
  - effects: `with_context`
- **`BaseImporter._try_load_records(self, model_name, data_list, note=True)`** - `models/importers/base_importer.py:626`
  - Load records with savepoint - skip silently on failure.
  - effects: `log_warn`
- **`BaseImporter._try_load_records_quiet_env(self, model_env, data_list)`** - `models/importers/base_importer.py:652`
  - _try_load_records on a caller-prepared environment.
  - effects: `log_warn`
- **`BaseImporter._direct_sql_insert(self, table, columns, rows, batch_size=5000)`** - `models/importers/base_importer.py:669`
  - Direct SQL INSERT into target DB - bypass ORM.
- **`BaseImporter._match_by_external_id(self, model, source_ids)`** - `models/importers/base_importer.py:729`
  - Map source records to the SAME records shipped with our modules.
  - effects: `log_warn`
- **`BaseImporter._direct_sql_insert_tracked(self, table, columns, rows, model, source_ids, batch_size=5000)`** - `models/importers/base_importer.py:845`
  - Idempotent bulk INSERT: SQL speed + ``ir.model.data`` external ID.
  - effects: `log_info`, `log_warn`, `raise:UserError`, `sql`
- **`BaseImporter._explain_refused_rows(self, table, columns, model, refused)`** - `models/importers/base_importer.py:957`
  - Name the exact constraint behind every refused row, in the protocol.
  - effects: `log_warn`, `sql`
- **`BaseImporter._xml_id_name(self, model_prefix, source_id)`** - `models/importers/base_importer.py:1006`
  - Name part of the external ID (without the module prefix).
- **`BaseImporter._xml_id(self, model_prefix, source_id)`** - `models/importers/base_importer.py:1016`
  - Full XML ID for ir.model.data.
- **`BaseImporter._get_target_id(self, model, source_id)`** - `models/importers/base_importer.py:1023`
  - Get target ID from previously imported record.
- **`BaseImporter._set_target_id(self, model, source_id, target_id)`** - `models/importers/base_importer.py:1035`
  - Store source → target ID mapping.
- **`BaseImporter._require_target_id(self, model, source_id, context_msg='')`** - `models/importers/base_importer.py:1039`
  - Get target ID or raise error if not found (fail hard).
  - effects: `raise:UserError`
- **`BaseImporter._resolve_from_imd(self, model, source_id)`** - `models/importers/base_importer.py:1073`
  - Try to resolve target ID from ir.model.data.
  - effects: `sudo`
  - touches: `ir.model.data`
- **`BaseImporter._map_company(self, source_company_id)`** - `models/importers/base_importer.py:1236`
  - Map source company ID to target company ID.
- **`BaseImporter._company_domain(self)`** - `models/importers/base_importer.py:1246`
  - Return domain filter for source companies being imported.
- **`BaseImporter._target_columns(self, model)`** - `models/importers/base_importer.py:1253`
  - Real database columns of a target model.
- **`BaseImporter._scoped_domain(self, path='')`** - `models/importers/base_importer.py:1268`
  - Domain restricting a model to the companies in scope.
- **`BaseImporter._source_company_ids(self)`** - `models/importers/base_importer.py:1290`
  - Return list of source company IDs being imported.
- **`BaseImporter._m2o_id(value)`** (`@staticmethod`) - `models/importers/base_importer.py:1297`
  - Bare id of a Many2one value, whichever shape the read returned.
- **`BaseImporter._map_m2o(self, model, source_val)`** - `models/importers/base_importer.py:1311`
  - Map Many2one field: [id, name] or id → target_id or False.
- **`BaseImporter._map_m2m(self, model, source_ids)`** - `models/importers/base_importer.py:1337`
  - Map Many2many field: [id1, id2, ...] → [(6, 0, [target_ids])].
- **`BaseImporter._common_fields(self, source_model, target_model)`** - `models/importers/base_importer.py:1351`
  - Get fields that exist in both source and target.
- **`BaseImporter._drain_skip_summary(self)`** - `models/importers/base_importer.py:1396`
  - The reasons collected since the last line, as one sentence.
- **`BaseImporter._make_result(self, model, source_count, imported_count, linked_count=0, skipped_count=0, duration=0, status='done', error='', rejected_count=0)`** - `models/importers/base_importer.py:1433`
  - One row of the import protocol.
- **`BaseImporter._log(self, msg, *args)`** - `models/importers/base_importer.py:1475`
  - Log a message.
  - effects: `log_info`
- **`CameraImporter._check_credentials_are_readable(self)`** - `models/importers/camera_importer.py:67`
  - Stop early if the other system will not hand over the passwords.
  - effects: `raise:UserError`
- **`CameraImporter._retarget_server_setup(setup_text, local_ip)`** (`@staticmethod`) - `models/importers/camera_importer.py:92`
  - The notification address, re-aimed at the server that now runs.
- **`CameraImporter._import_cameras(self)`** - `models/importers/camera_importer.py:116`
- **`CameraImporter._import_camera_readers(self)`** - `models/importers/camera_importer.py:175`
  - Readers bound to a camera rather than to a controller.
  - effects: `with_context`
- **`CameraImporter._import_camera_doors(self)`** - `models/importers/camera_importer.py:242`
  - Doors whose readers belong to a camera.
  - effects: `with_context`
- **`CameraImporter._link_camera_readers(self)`** - `models/importers/camera_importer.py:327`
  - The camera's own reader list - the field the event handler reads.
  - effects: `sudo`, `with_context`
  - touches: `hr.rfid.reader`
- **`CameraImporter._import_plate_links(self)`** - `models/importers/camera_importer.py:377`
  - Which plate sits in which bucket on which camera.
  - effects: `log_warn`
- **`CameraImporter._say_what_is_left_to_do(self)`** - `models/importers/camera_importer.py:437`
  - Tell the operator what the transfer deliberately did NOT do.
- **`ConsistencyImporter._same_shape_on_the_source(self, name)`** - `models/importers/consistency_importer.py:41`
  - effects: `log_warn`
- **`ConsistencyImporter._source_controllers_behind_archived_module(self)`** - `models/importers/consistency_importer.py:58`
- **`ConsistencyImporter._source_readers_without_door(self)`** - `models/importers/consistency_importer.py:66`
- **`ConsistencyImporter._name_them(self, offenders)`** - `models/importers/consistency_importer.py:131`
- **`ConsistencyImporter._target_companies(self)`** - `models/importers/consistency_importer.py:139`
- **`ConsistencyImporter._cameras_without_reader_list(self)`** - `models/importers/consistency_importer.py:144`
  - The event handler reads the camera's OWN reader list; readers merely pointing at the camera do not count. Empty list = every recognition dropped - the live defect this phase was born from.
  - effects: `with_context`
  - touches: `cctv.camera`
- **`ConsistencyImporter._controllers_behind_archived_module(self)`** - `models/importers/consistency_importer.py:158`
  - An archived module hides everything under it from every dotted company scope (an EXISTS never matches through it) - the equipment looks gone while it is merely veiled. Measured on a live source: one door, four readers…
  - effects: `with_context`
  - touches: `hr.rfid.ctrl`
- **`ConsistencyImporter._doors_off_the_chain(self)`** - `models/importers/consistency_importer.py:175`
  - A door reaches a company through its controller's module - or, with cameras installed, through a camera. One with neither is unattributable: invisible to scopes, unfixable from the UI.
  - effects: `with_context`
  - touches: `hr.rfid.door`
- **`ConsistencyImporter._readers_without_door(self)`** - `models/importers/consistency_importer.py:187`
  - A reader records passages through its door; without one its events have nowhere to belong. ``door_id`` is computed, not stored - the walk is in Python, over the readers reachable through either chain.
  - effects: `with_context`
  - touches: `hr.rfid.reader`
- **`ConsistencyImporter._chain_company_mismatch(self)`** - `models/importers/consistency_importer.py:202`
  - Every link of module -> controller -> door must stay inside ONE company; a mixed chain shows different equipment to different people and record rules quietly hide the mismatch itself.
  - effects: `with_context`
  - touches: `hr.rfid.door`
- **`ConsistencyImporter._cards_with_foreign_owner(self)`** - `models/importers/consistency_importer.py:222`
  - A card of one company held by a person of another crosses the record rules: the card works, but the people managing that company cannot see why.
  - effects: `with_context`
  - touches: `hr.rfid.card`
- **`ConsistencyImporter._doors_without_readers(self)`** - `models/importers/consistency_importer.py:241`
  - A door nobody reads for cannot grant or refuse anyone.
  - effects: `with_context`
  - touches: `hr.rfid.door`
- **`ConsistencyImporter._readers_without_owner(self)`** - `models/importers/consistency_importer.py:249`
  - Every reader hangs off a controller or (with cameras installed) a camera; one with neither answers to nothing and its events can never be attributed.
  - effects: `with_context`
  - touches: `hr.rfid.reader`
- **`ConsistencyImporter._cards_without_owner(self)`** - `models/importers/consistency_importer.py:261`
  - A card with no employee and no contact opens doors for nobody - and can never be blocked through a person either.
  - effects: `with_context`
  - touches: `hr.rfid.card`
- **`ConsistencyImporter._door_rels_cross_company(self)`** - `models/importers/consistency_importer.py:270`
  - An access group granting a door of ANOTHER company is a leak the record rules will later hide from the very people managing it.
  - touches: `hr.rfid.access.group.door.rel`
- **`CoreImporter._import_card_types(self)`** - `models/importers/core_importer.py:78`
  - Step 1: hr.rfid.card.type - match by name.
- **`CoreImporter._import_employee_categories(self)`** - `models/importers/core_importer.py:128`
  - Step 2: hr.employee.category - match by name.
- **`CoreImporter._import_departments(self)`** - `models/importers/core_importer.py:167`
  - Step 3: hr.department - TWO PASSES (parent_id self-ref).
  - effects: `with_context`
- **`CoreImporter._import_workcodes(self)`** - `models/importers/core_importer.py:239`
  - Step 4: hr.rfid.workcode - filtered by company.
- **`CoreImporter._import_time_schedules(self)`** - `models/importers/core_importer.py:290`
  - Step 5: hr.rfid.time.schedule - match by number + company.
  - effects: `with_context`
- **`CoreImporter._import_alarm_groups(self)`** - `models/importers/core_importer.py:370`
  - Step 8: hr.rfid.ctrl.alarm.group - TWO PASSES (parent_id self-ref).
  - effects: `with_context`
- **`CoreImporter._import_emergency_groups(self)`** - `models/importers/core_importer.py:425`
  - Step 9: hr.rfid.ctrl.emergency.group - company-level.
- **`CoreImporter._import_webstacks(self)`** - `models/importers/core_importer.py:464`
  - Step 10: hr.rfid.webstack - filtered by company.
- **`CoreImporter._import_controllers(self)`** - `models/importers/core_importer.py:536`
  - Step 11: hr.rfid.ctrl - filtered by webstack.
  - effects: `with_context`
  - touches: `hr.rfid.ctrl`
- **`CoreImporter._import_doors(self)`** - `models/importers/core_importer.py:630`
  - Step 12: hr.rfid.door - filtered by ctrl→ws→company chain.
  - effects: `with_context`
- **`CoreImporter._import_readers(self)`** - `models/importers/core_importer.py:707`
  - Step 13: hr.rfid.reader - filtered by ctrl.
  - effects: `with_context`
- **`CoreImporter._import_input_masks(self)`** - `models/importers/core_importer.py:779`
  - Step 14: hr.rfid.ctrl.input.mask - per controller.
- **`CoreImporter._import_output_ts(self)`** - `models/importers/core_importer.py:829`
  - Step 15: hr.rfid.ctrl.output.ts - per controller.
- **`CoreImporter._import_alarms(self)`** - `models/importers/core_importer.py:881`
  - Step 16: hr.rfid.ctrl.alarm - depends on ctrl + door + alarm_group.
- **`CoreImporter._import_th_sensors(self)`** - `models/importers/core_importer.py:948`
  - Step 17: hr.rfid.ctrl.th - depends on ctrl + door.
- **`CoreImporter._import_zones(self)`** - `models/importers/core_importer.py:1009`
  - Step 18: hr.rfid.zone - M2M: door_ids, departments, categories, employees, contacts.
- **`CoreImporter._carry_forgotten_badge_settings(self, source_zones)`** - `models/importers/core_importer.py:1090`
  - What the OLD zones said about forgotten badges, said here properly.
  - effects: `log_info`
  - touches: `res.company`
- **`CoreImporter._import_notifications(self)`** - `models/importers/core_importer.py:1138`
  - Step 19: hr.rfid.notification - owned by its zone.
- **`EventImporter._event_date_domain(self, field='event_time')`** - `models/importers/event_importer.py:43`
  - Build date filter domain for events.
- **`EventImporter._read_both_legs(self, model, module_domain, fields_to_read, cursor_prefix, date_field='event_time')`** - `models/importers/event_importer.py:50`
  - Two plain reads - one per attribution leg - merged by id.
- **`EventImporter._with_camera_branch(self, model, domain)`** - `models/importers/event_importer.py:81`
  - Add the camera-side events to a controller-scoped domain.
- **`EventImporter._camera_event_fields(self, model, source_fields, target_fields)`** - `models/importers/event_importer.py:95`
  - The camera columns worth carrying over, when both sides have them.
- **`EventImporter._camera_expected(self, model, date_domain=None)`** - `models/importers/event_importer.py:106`
  - How many camera events the source holds for this run's scope.
- **`EventImporter._report_camera_events(self, model, camera_rows, expected, wanted=True)`** - `models/importers/event_importer.py:126`
  - Say in the protocol how the camera events fared, against ``expected``.
- **`EventImporter._import_user_events(self)`** - `models/importers/event_importer.py:188`
  - Step 26: hr.rfid.event.user - Direct SQL batch.
  - effects: `log_error`, `log_warn`
- **`EventImporter._import_system_events(self)`** - `models/importers/event_importer.py:351`
  - Step 27: hr.rfid.event.system - Direct SQL batch.
  - effects: `log_error`
- **`EventImporter._import_th_logs(self)`** - `models/importers/event_importer.py:521`
  - Step 28: hr.rfid.ctrl.th.log - Direct SQL batch.
  - effects: `log_error`
- **`LeaveImporter._needs_balance(value)`** (`@staticmethod`) - `models/importers/leave_importer.py:67`
  - The older system's word for it, as the yes/no box here.
  - effects: `log_warn`
- **`LeaveImporter._leave_env(self, model)`** - `models/importers/leave_importer.py:85`
  - The model, entered the way core imports leaves - quietly.
  - effects: `with_context`
- **`LeaveImporter._import_leave_types(self)`** - `models/importers/leave_importer.py:93`
  - Step 2c-1: hr.leave.type.
- **`LeaveImporter._import_allocations(self)`** - `models/importers/leave_importer.py:177`
  - Step 2c-2: hr.leave.allocation - approved balances only.
  - effects: `log_warn`, `with_context`
- **`LeaveImporter._import_leaves(self)`** - `models/importers/leave_importer.py:251`
  - Step 2c-3: hr.leave - the absences, in their real states.
- **`PeopleImporter._contacts_this_tenant_uses(self, co_domain)`** - `models/importers/people_importer.py:35`
  - Ids of the contacts this tenant's cards and access groups refer to.
- **`PeopleImporter._import_partners(self)`** - `models/importers/people_importer.py:50`
  - Step 5: res.partner - scope depends on user choice.
- **`PeopleImporter._link_partner_parents(self, model, domain)`** - `models/importers/people_importer.py:183`
  - Attach every imported contact to its parent contact.
  - effects: `log_warn`, `with_context`
- **`PeopleImporter._resolve_country(self, source_country)`** - `models/importers/people_importer.py:207`
  - ID на държавата в целта, по ISO код от external ID-то на източника.
  - effects: `log_warn`
- **`PeopleImporter._import_users(self)`** - `models/importers/people_importer.py:237`
  - Step 6: res.users - optional, match by login.
  - effects: `log_warn`, `with_context`
- **`PeopleImporter._transfer_groups(self, user, source_group_ids)`** - `models/importers/people_importer.py:337`
  - Transfer user groups from source by matching xml_id.
  - effects: `log_warn`, `with_context`
- **`PeopleImporter._import_employees(self)`** - `models/importers/people_importer.py:366`
  - Step 7: hr.employee - scope depends on user choice.
  - effects: `log_info`, `with_context`
  - touches: `hr.employee`
- **`_target_available(env, requirement)`** - `models/importers/phase.py:16`
  - Whether this system can receive that kind of data.
- **`PhaseImporter.__init__(self, base)`** - `models/importers/phase.py:75`
- **`_skip_reason(env, cls, options, source_modules)`** - `models/importers/phase.py:134`
  - Why this phase will not run, in words the operator can act on.
- **`ReconcileImporter.__init__(self, base)`** - `models/importers/reconcile_importer.py:163`
  - calls `super()`
- **`ReconcileImporter._ticked(self, option)`** - `models/importers/reconcile_importer.py:195`
  - Whether the operator asked this transfer to bring what ``option`` carries.
- **`ReconcileImporter._carried(self, model)`** - `models/importers/reconcile_importer.py:207`
  - Whether this transfer was asked to bring that kind.
- **`ReconcileImporter._reconcile(self, model, path, label, start, extra=())`** - `models/importers/reconcile_importer.py:218`
  - One protocol line for one kind: its numbers there and here.
- **`ReconcileImporter._explained_by_owners(self, model, path, source_company, extra, gap)`** - `models/importers/reconcile_importer.py:286`
  - How much of a tenant's gap the records of owners not here explain.
- **`ReconcileImporter._verdict(self, label, carried, owners, found, unplaced_total)`** - `models/importers/reconcile_importer.py:305`
  - The line's status and the sentences that explain it.
- **`ReconcileImporter._kept_here_on_purpose(self, model, target_company)`** - `models/importers/reconcile_importer.py:365`
  - Records of that tenant the transfer left out because this system has its own.
- **`ReconcileImporter._attendance_verdicts(self)`** - `models/importers/reconcile_importer.py:384`
  - What the attendance step decided, as far as this check can know it.
  - effects: `sudo`
  - touches: `hr.rfid.odoo.import.run`
- **`ReconcileImporter._count_on_the_source(self, model, path, source_company, extra=())`** - `models/importers/reconcile_importer.py:408`
  - How many the OTHER system holds for that tenant.
  - effects: `log_warn`
- **`ReconcileImporter._count_that_arrived(self, model, path, source_company, target_company)`** - `models/importers/reconcile_importer.py:426`
  - How many of that tenant's records are HERE, by transfer identity.
  - effects: `log_warn`, `with_context`
- **`ReconcileImporter._owned_by_owners_not_here(self, model, path, source_company, extra)`** - `models/importers/reconcile_importer.py:450`
  - How many of that tenant's records over there belong to an owner that is not here, of a kind this transfer did not carry. ``None`` when it cannot be told.
- **`ReconcileImporter._owners_here_of(self, owner)`** - `models/importers/reconcile_importer.py:482`
  - The other system's ids of that owner kind still here, read once a phase.
- **`ReconcileImporter._identity_prefix(self, model)`** - `models/importers/reconcile_importer.py:488`
  - How this transfer starts the identity name of a record of that model.
- **`ReconcileImporter._ledger(self, model)`** - `models/importers/reconcile_importer.py:492`
  - This transfer's identity rows for that model: [{'name', 'res_id'}].
  - effects: `sudo`
  - touches: `ir.model.data`
- **`ReconcileImporter._ids_brought_over(self, model)`** - `models/importers/reconcile_importer.py:508`
  - Target ids this transfer recorded for that model, from its own name.
- **`ReconcileImporter._source_ids_here(self, model)`** - `models/importers/reconcile_importer.py:512`
  - The other system's ids of that kind that this system still holds.
  - effects: `log_warn`, `sudo`
- **`ReconcileImporter._name_them(self, rows)`** - `models/importers/reconcile_importer.py:538`
  - touches: `res.company`
- **`ServiceImporter._import_service_tags(self)`** - `models/importers/service_importer.py:33`
  - Step 38: rfid.service.tags - ORM create.
- **`ServiceImporter._import_services(self)`** - `models/importers/service_importer.py:82`
  - Step 39: rfid.service - depends on AG, zone, partner, card_type, tags.
  - effects: `log_warn`
- **`ServiceImporter._resolve_template_by_xmlid(self, source_val, model)`** - `models/importers/service_importer.py:173`
  - Resolve template M2O by xml_id from source ir.model.data.
  - effects: `log_warn`
- **`ServiceImporter._import_service_sales(self)`** - `models/importers/service_importer.py:202`
  - Step 40: rfid.service.sale - Direct SQL batch.
  - effects: `log_error`
- **`SiteImporter._check_operator_may_write_sites(self)`** - `models/importers/site_importer.py:57`
  - Fail with an explanation rather than an access traceback.
  - effects: `raise:UserError`
  - touches: `hr.rfid.site`
- **`SiteImporter._parent_first(records)`** (`@staticmethod`) - `models/importers/site_importer.py:77`
  - Sites ordered so that a parent always precedes its children.
- **`SiteImporter._import_sites(self)`** - `models/importers/site_importer.py:100`
- **`SiteImporter._link_sites_to_hardware(self)`** - `models/importers/site_importer.py:160`
  - Fill site_id on the equipment that was imported before the sites.
  - effects: `with_context`
- **`SiteImporter._link_sites_to_partners(self)`** - `models/importers/site_importer.py:207`
  - Give the contacts back the sites they belong to.
  - effects: `with_context`
- **`VendingImporter._import_products(self)`** - `models/importers/vending_importer.py:61`
  - Step 29: product.template - match by default_code, fallback name.
- **`VendingImporter._import_vending_rows(self)`** - `models/importers/vending_importer.py:136`
  - Step 30: hr.rfid.ctrl.vending.row - depends on ctrl + product.
- **`VendingImporter._import_vending_settings(self)`** - `models/importers/vending_importer.py:194`
  - Step 31: hr.rfid.ctrl.vending.settings - depends on ctrl.
- **`VendingImporter._import_auto_refill(self)`** - `models/importers/vending_importer.py:237`
  - Step 32: hr.rfid.vending.auto.refill - company-level.
- **`VendingImporter._import_vending_events(self)`** - `models/importers/vending_importer.py:299`
  - Step 33: hr.rfid.vending.event - Direct SQL batch (separate table).
  - effects: `log_error`
- **`VendingImporter._import_balance_history(self)`** - `models/importers/vending_importer.py:400`
  - Step 34: hr.rfid.vending.balance.history - Direct SQL batch.
  - effects: `log_error`
- **`VendingImporter._update_employee_vending_fields(self)`** - `models/importers/vending_importer.py:488`
  - Step 35: Update employees with vending balance fields.
  - effects: `with_context`
  - touches: `hr.employee`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_odoo_import_run_list` | `hr.rfid.odoo.import.run` | - |  | `views/import_run_views.xml` |
| `hr_rfid_odoo_import_run_form` | `hr.rfid.odoo.import.run` | - |  | `views/import_run_views.xml` |
| `hr_rfid_odoo_import_wiz_form` | `hr.rfid.odoo.import.wiz` | - |  | `views/import_wizard_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_odoo_import_wiz` | `model_hr_rfid_odoo_import_wiz` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_company_line` | `model_hr_rfid_odoo_import_company_line` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_conflict` | `model_hr_rfid_odoo_import_conflict` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_log` | `model_hr_rfid_odoo_import_log` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_odoo_import_run` | `model_hr_rfid_odoo_import_run` | `base.group_system` | ✓ | ✓ | ✓ | ✓ |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`ir_cron_import_run`** (RFID: continue data transfers) on `model_hr_rfid_odoo_import_run`, runs every 1 days, active=True

### Data records summary

- `hr.rfid.odoo.import.log`: 73 record(s)
- `ir.actions.act_window`: 2 record(s)
- `ir.cron`: 1 record(s)
- `hr.rfid.odoo.import.run`: 1 record(s)
- `mail.message`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (1): `static/tests/tours/transfer_gate_tour.js`



## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>

### Curated (docs/faq.md)

##### Transfer contract

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

##### Attendance hours after a transfer

The attendance step writes `hr.attendance` rows with SQL for speed, so the
stored figures (`worked_hours`, `overtime_hours`, `expected_hours`) are not
computed by the insert itself. The one figure it does write, the record's
`date`, is core's own rule for it (`hr_attendance.py:90`: the check-in read in
`employee._get_tz()`), so a stay begun after midnight in Sofia carries that
morning's date as a record made by the doors would; rows an earlier transfer
dated by UTC get the right date when the step below works them out. A step of its own,
`AttendanceImporter._settle_attendance_figures()`, runs after it and puts them
right. It shows in the protocol as the line "Worked Hours".

- **When.** Only once the attendance read is finished, so a person's figures
  are worked out once over all of their rows. A fault in it cannot take back
  attendance that has already landed.
- **Whose.** The people this source brought across (found by their external
  IDs) into the companies of THIS transfer, and every attendance of theirs
  whose figures do not hold, whatever its date: no worked hours at all, or
  regular hours further than `FIGURE_TOLERANCE` from worked minus extra. A new
  transfer over an earlier one therefore repairs the earlier one.
- **How.** Core's `_update_overtime` deletes and recreates every overtime line
  in the range it is given, and a recreated line loses its approval or
  refusal. It also needs the person's schedule, which core has only inside a
  version (`hr.employee._get_version_periods`): before the first version it
  counts the whole day as approved extra time (measured: 08:00-17:00 read 9
  extra and -1 regular, for a day entered by hand too). So the rows are cured
  three ways:
  - regular hours that disagree, with worked hours present: only
    `expected_hours` is recomputed, and the overtime lines are left alone;
  - no worked hours, before the first version: `modified(['check_in',
    'check_out'])` (the idiom core uses after its own raw updates) and nothing
    else - no rules apply there, exactly as core's "Regenerate overtimes"
    leaves them (`_attendances_to_regenerate_for` stops at the version);
  - no worked hours, inside a version: the same, then core's
    `_update_overtime()`, as `hr.attendance.create` does. It is handed one run
    of such rows at a time, cut at every row that has its hours and at every
    local week (MO-SU in the person's zone, as core counts weeks), so a correct
    day between them is never in its range. A day or week holding both kinds
    is worked out again as a whole, as core does on any edit of it.
  - `expected_hours` is marked explicitly in all three, because core marks it
    in the overtime run only since odoo/odoo 17577a1f9c6 (in 19.0 since
    30.03.2026).
- **Time.** Where it got to (`read_cursors['attendance:figures']`) and what it
  could not do (`step_totals['attendance:figures']`) travel with the cursors.
  A pass that runs out of time stops between people and the next pass carries
  on from there. A person whose rows another process is writing at that
  moment waits for the next pass: the step stops part-way, and
  `import_run._process_pass` returns to any phase that did not finish instead
  of ending the run without it.
- **When it cannot.** Each unit has its own savepoint. A unit that core's
  overtime run refuses stays without figures, so the next transfer finds it
  again. The line turns "partial" and names the people, the first day (in the
  person's own zone) and what the system answered, with the advice to put
  those days right and run the transfer again. Only data errors (`UserError`,
  integrity and data errors from the database) are counted this way; anything
  else is a fault in the code and shows as a failed step.
- **No history entries.** The step runs with the import context
  (`tracking_disable`), so the transferred attendances get no tracking message.
- Customer case (12.10.2026): after a transfer more than half of the closed
  attendances read 0 hours worked, and about a third had regular hours that
  were not worked minus extra.

Tests: `tests/test_transferred_attendance_has_hours.py`
(tags `rfid_odoo_import`, `rfid_import_attendance_hours`), and
`tests/test_background_run.py` for the return to an unfinished phase.

##### The phase registry

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

###### Adding a phase

1. Subclass `PhaseImporter` in `models/importers/`, set the metadata, implement
   `run(wizard)` returning a list of `_make_result` dicts.
2. Add it to `build_registry()` in the position its dependencies require.
3. Add the option field to the wizard and to `_build_options`.

Nothing in the wizard needs to learn its name.

##### Background execution

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

##### Identity of a transferred record

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

###### What a second run does

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

###### Recognising another system's records

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

##### Attendance brought over is never rebuilt

`models/hr_employee.py` implements `hr.employee._check_recalc_allowed` (the
hook declared in `hr_rfid`) and refuses when the requested window holds
attendance carrying this transfer's external ID.

- Detection is ONE query: the external IDs are used as a sub-select
  (`ir.model.data` has no link back to attendance), matched on
  `EXTERNAL_ID_NAME_PATTERN` = `rfid_import_%_hr_attendance_%` - the module
  alone would also match an ordinary spreadsheet import.
- The window comes from the rebuild itself (`_local_days_window`, in the
  person's own zone - `_local_tz`), so the two cannot drift; people are
  grouped by that zone to keep it to one query.
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

##### A stay already recorded here is kept

The attendance step inserts with SQL, past core's `hr.attendance._check_validity`
(`hr_attendance.py:206-246`), so before the insert
`AttendanceImporter._leave_out_stays_recorded_here` holds every row not yet
carried by this transfer (its source id has no external ID) to that rule:

- `refused_beside(start, stop, other_start, other_stop)` is core's check asked
  of the new stay AND of an open one at the moment it is closed: two open stays
  side by side; a stay beginning while another runs; another beginning inside a
  closed one. An open stay holds all the time from its check-in on - core
  accepts a closed stay begun after it, then refuses to close the open one (or,
  with the check bypassed, counts the time twice). The test asks core's own
  method, called directly, for every shape, and again after closing the open
  stay of the shape.
- The same stay to the second is asked first, before the rule: a stay that
  begins and ends at one moment collides with nothing, not even its twin.
- Compared with what is recorded here (`_stays_recorded_here`, one query per
  page, earliest first; a page with an open stay has no upper bound) and with
  the rows of the same read accepted before it, in source order.
- The same to the second: counted as already here (`linked`), under
  `SAME_HERE_KEY` as `{source id: company}`. Different: left out (`skipped`),
  under `DIFFERS_KEY` as `{source id: [person, company, check-in, check-out,
  check-in here, check-out here]}`. By source id, and every id of a page loses
  its earlier verdict first: a write that fails sends the read back to the
  start, and the page read again replaces what it said instead of saying it
  twice. The line is `partial`, names the first people with the first local
  day (`BaseImporter.first_few`), and
  `hr.rfid.odoo.import.run._protocol_stays_left_out` adds the whole list to the
  downloaded protocol, both times in the person's zone (`format_datetime`,
  `short`); the people are read as superuser (`people_by_id`), because the
  operator downloading it has one tenant selected.
- Both live in the step totals of `attendance:hr.attendance`, so they survive
  the passes and are undone with the rows. The reconciliation counts them as
  accounted for (`ReconcileImporter._kept_here_on_purpose`), not as lost; a
  transfer that carried no attendance takes them from the latest earlier
  transfer of the same system that did (`_attendance_verdicts`), since the
  check compares every kind whatever was ticked (see "The final check: a
  problem only in what was carried").
- Nothing links a left-out row to the record here, so every run checks again:
  a stay that collides today arrives on the run after the stay here is put
  right.

Customer case, 23.10.2026: a second transfer from an older copy of the other
system would have laid 11 116 stays over the ones rebuilt here from the door
events, 9 808 of them the same to the second. Rehearsed on a copy of that
database: 8 824 arrived (the three months the system had no attendance for),
9 808 counted as already here, 1 327 listed, no new overlap, and a second run
changed nothing.

##### The final check: a problem only in what was carried

`ReconcileImporter` (Phase 10) counts every kind of `RECONCILED` on both
sides, tenant by tenant, whatever was ticked. Each entry is `(model, path,
option[, extra domain])`; `option` is the operator's tick that asks for the
kind, a tuple when several do (cards: `import_access` or the "Import Cards"
tick `import_cards`). `CARRIED_BY` maps model to option; the label the
operator reads is `KIND_LABELS[model]`, a lazy translation.

- Asked for = `_ticked(option)`: the option itself or the operator's raw tick
  in `options['ticked']`. The wizard (`_build_options`) folds a tick with
  module availability for vending, attendance, extra attendance and services,
  so the step switch is off when this system cannot take the data; the raw
  tick keeps such data, asked for and left behind, a problem.
- A kind not asked for: no difference - `done`; any difference, either way -
  `skipped` with a remark that it was not part of this transfer, both numbers
  per tenant. A check that breaks on such a kind is `skipped` too. None of it
  makes the run fail (owner's decision, 10.11.2026).
- A kind asked for and short: before calling it a loss, the check asks the
  other system how many of those records belong to an owner that is not here
  (`_owned_by_owners_not_here`). Owners are listed explicitly in `OWNED_BY`:
  the person of an attendance, daily summary, vending balance entry, absence,
  leave balance and staff membership of an access group; the contact of a
  contact membership; the person of a card, then - only for a card with no
  person - its contact. They are tried in the order the steps try them, and
  only owners whose kind was not asked for count (`OWNER_CARRIED_BY`: both
  come with People). The same tenant filter and extra domain as the main
  count apply. "Here" is the transfer's identity of the owner with a record
  still behind it, archived included (`_source_ids_here`; a ledger row whose
  record was deleted around the ORM does not count; a name that does not end
  in the source id makes the answer unknown).
  - those records fill the gap: a remark (`partial`), with their count;
  - the other system will not say (`None`): the whole gap stays a loss and the
    line says it was not told;
  - more of them than the gap: the two counts do not describe the same records
    and explain nothing - the whole gap stays a loss;
  - what is still short after them: `error`.
  When the owner's kind WAS asked for, nothing is excused: the owner's own line
  says who is missing.
- "Arrived" is read from the transfer's own identity rows by the exact prefix
  the steps write (`_identity_prefix`, model included): the identity of one
  source must not take in another's whose name continues it ("acme" and
  "acme_old").
- `KIND_LABELS` is a separate mapping on purpose: core's term extractor
  (`odoo/tools/babel/python_extractor.py`) keeps the last NAME it saw, so the
  `(` opening a tuple right after a `_lt(...)` or `env._(...)` call is read as
  one more call, and the tuple's model names went out for translation. The
  wizard's preview counts keep their labels in a mapping for the same reason.

Customer case, 10.11.2026: a second transfer of the attendance alone carried
8 824 stays and kept 1 327 recorded here, and was reported "stopped by a
problem" over people (209 there, 208 here), access and system events, daily
summaries and one stay of a person this system does not have. With the rule it
ends as finished, with those as remarks; a second run changes nothing.

The background worker writes the protocol in the language of the person who
started the transfer (`_in_starters_language`, used by `_cron_process`, its
failure path and `_abandon_stalled_runs`), not in the scheduler's - only when
that person has a language, as core does (`mail_activity.py:422-424`).

Tests: `tests/test_reconcile_with_the_source.py` (every rule above, each with
its negative twin, and the whole pass of an attendance-only transfer ending as
finished), `tests/test_a_stay_recorded_here_is_kept.py`,
`tests/test_background_run.py::test_the_protocol_is_written_in_the_language_of_who_started_it`.

##### Reference data vs migrated data

Records shipped with a module - card types being the case in point - exist on
both sides under the same external id. `_match_by_external_id` links them
instead of creating copies. Creating a second "License Plate" makes plate
numbers land on a type the card validation does not recognise as plates, and
every plate is then refused for "digits must be from 0 to 9", taking the camera
links with them.

##### Talking to hardware

`IMPORT_CONTEXT` carries `no_hardware_commands`, honoured by `hr_rfid` and, as
of 19.0.1.12.0, by `polimex_ip_cam`. The guard sits on `cctv.camera.command`
itself as well as on the callers, because `queue_send` registers a postcommit
hook and postcommit hooks survive a savepoint rollback - a rolled-back phase
would otherwise still have fired at the cameras.

Any new write in an importer must carry this context. The site phase originally
did not, and its access-group cascade reached live cameras through three
separate paths.


##### The identity a transfer files its records under

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

##### The transfer record (`hr.rfid.odoo.import.run`)

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

##### What the constants mean

- **`EXTERNAL_ID_MODULE`** = `'__import__'` - the `ir.model.data` module every
  transferred record is registered under, the same one core's own
  `BaseModel.load()` writes.
- **`EXTERNAL_ID_PREFIX`** = `'rfid_import_'` - start of every external-ID name
  this transfer writes. Read by anything that has to recognise a transferred
  record (`models/hr_employee.py` builds its pattern from it).
- **`ATTENDANCE_MODEL`** = `'hr.attendance'`
- **`EXTERNAL_ID_NAME_PATTERN`** = `'rfid_import_%_hr_attendance_%'` (built from
  the two constants above, source installation wildcarded)
- **`NAMES_SHOWN`** = `3`, **`DEFAULT_LOOKBACK_DAYS`** = `30` (the same window
  the rebuild starts from when no date is given)
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (7)

#### Fix: [FIX] hr_rfid_odoo_import: конфликт != идентичност; архивирано ...

Commit `11cb74648d` (2026-07-27): [FIX] hr_rfid_odoo_import: конфликт != идентичност; архивирано устройство не скрива данни v19.0.1.8.0

#### Fix: [FIX] hr_rfid_odoo_import: идентичност само по ИД, никога по текст ...

Commit `fee2db0807` (2026-07-26): [FIX] hr_rfid_odoo_import: идентичност само по ИД, никога по текст v19.0.1.7.0

#### Fix: [FIX] hr_rfid_odoo_import: паднала фаза вече не трови следващите ...

Commit `6e3933e11c` (2026-07-26): [FIX] hr_rfid_odoo_import: паднала фаза вече не трови следващите v19.0.1.6.0

#### Fix: [FIX] hr_rfid_odoo_import: external ID и при СВЪРЗВАНЕ на ...

Commit `31d2dba2c5` (2026-07-26): [FIX] hr_rfid_odoo_import: external ID и при СВЪРЗВАНЕ на съществуващ запис

#### Fix: [FIX] hr_rfid_odoo_import: multi-company хардънинг (12 дефекта) ...

Commit `1ba32196af` (2026-07-26): [FIX] hr_rfid_odoo_import: multi-company хардънинг (12 дефекта) v19.0.1.4.0

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [FIX] hr_rfid_odoo_import: Improve data completeness and fix ...

Commit `b839ce5dc2` (2026-03-19): [FIX] hr_rfid_odoo_import: Improve data completeness and fix multi-company import


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_odoo_import`
- Source digest: `sha256:6aa5dabbb84ba5a4e299c9020208831bc90ed73dcb8aa67d117389a711b185ff`
- Generated at: `2026-11-23T10:07:38+00:00`
- Generator: `polimex_module_knowledge`
