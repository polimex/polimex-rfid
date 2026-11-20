---
id: hr_rfid_leave_block
title: RFID Access Block on Leave
module: hr_rfid_leave_block
module_version: 19.0.1.0.2
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Suspend RFID cards while an employee is on approved leave
last_updated: '2026-11-20'
source_digest: sha256:ea878fc613ed9cc0bd2044fbb922740634fef802297faeac5702d50221d86edf
depends:
- hr_rfid
- hr_holidays
entities:
  primary: hr.rfid.leave.block
  related:
  - hr.leave
keywords:
- approved
- block
- cards
- employee
- leave
- rfid
- suspend
- while
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 2
  views: 3
  access_rules: 2
  record_rules: 1
  crons: 1
  images: 0
images: []
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Access Block on Leave - `hr_rfid_leave_block` v19.0.1.0.2

Suspend RFID cards while an employee is on approved leave

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_leave_block`
- **Version**: `19.0.1.0.2`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `hr_holidays`

### README (verbatim)

#### RFID Access Block on Leave

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Suspend an employee's RFID cards automatically while their approved time off goes on, and restore them when the leave ends.

##### 🎯 Overview

When an approved time off begins, this module deactivates the employee's currently-active RFID cards so they cannot enter while away; a leave approved ahead of time leaves the person working until it begins. It remembers the exact set of cards it suspended and re-activates only those when access is restored - when the leave ends, or immediately if the leave is refused or cancelled. A card the employee had already disabled before the leave, or added during it, is intentionally left untouched.

##### ✨ Key Features

- **Per-card snapshot** — records exactly which cards were active and got suspended (`hr.rfid.leave.block`), so restore never silently re-enables a card the user meant to keep off.
- **Automatic, from the start of the leave** - approving a leave that already goes on suspends the cards at once; a leave approved for later is suspended by the scheduled action when it begins. *Refused* / *Cancelled* / back-to-draft triggers the restore.
- **Idempotent** — re-approving a leave that already has an active block does not double-suspend or re-snapshot.
- **Scheduled follow-up** - every 15 minutes a scheduled action suspends the cards of the approved leaves that have begun and restores them for the leaves that have ended.
- **Self-cleaning audit** — restored audit rows are reclaimed by `@api.autovacuum` after one year, in batches.
- **Multi-company isolated** — blocks are scoped to the leave's company.

##### 📋 Requirements

- Odoo 19.0+
- `hr_rfid`
- `hr_holidays`

##### ⚙️ Configuration

No configuration is required. The behaviour is wired to the standard time-off approval flow. Two scheduled actions are created on install:

- **RFID: Follow time off (stop and give back access)** - every 15 minutes.
- Restored audit rows are garbage-collected by the core *Auto-vacuum* cron (no separate schedule).

##### 🚀 Usage

1. Approve a time-off request for an employee who holds RFID cards.
2. When the leave begins (at once, if it already goes on), the employee's active cards are suspended and listed under **RFID ▸ Leave Access Blocks**.
3. When the leave ends (or is refused/cancelled), the snapshotted cards are re-activated automatically.

##### 🛠️ Technical

- **Model `hr.rfid.leave.block`** — `leave_id`, related `employee_id`/`company_id`, `blocked_card_ids` (M2M snapshot read with `active_test=False` so archived cards stay visible), `state` (`active`/`restored`), `blocked_at`/`restored_at`.
- **`hr.leave.write` hook** — reacts to the `state` transition after the core write succeeds; `validate` → `_rfid_block_access` for the leaves that go on now (`_rfid_going_on`), `draft`/`confirm`/`refuse`/`cancel` → `_rfid_restore_access`.
- **`_cron_follow_the_leaves`** - suspends the cards of approved leaves that have begun and have no active block, and restores the blocks of the leaves that have ended (`date_to` reached); `_cron_restore_expired_blocks` (restore only, by date) is kept for callers of the old scheduled action.
- **`_gc_restored_blocks`** — batched `@api.autovacuum` returning `(done, has_more)`.

##### 👥 Credits

**Polimex Holding Ltd.** — https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_leave_block --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.leave` <a id='model-hr-leave'></a>
Python class `HrLeave` in `models/hr_leave.py:10`.  Model.  Inherits: `hr.leave`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `rfid_block_ids` | One2many → \`hr.rfid.leave.block\` | RFID Access Blocks |  | ✓ | Snapshots of RFID cards suspended while this leave is approved. |

#### Notable methods

- **`write(self, vals)`** - decorators: -
  - calls `super() `write``

### `hr.rfid.leave.block` <a id='model-hr-rfid-leave-block'></a>
Python class `HrRfidLeaveBlock` in `models/hr_rfid_leave_block.py:14`.  Model.  Description: *RFID Access Block for Leave*.  Default order: `blocked_at desc`.

> Audit snapshot of RFID cards suspended for one approved leave.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `leave_id` | Many2one → \`hr.leave\` | Leave | ✓ | ✓ | The approved time-off that triggered suspending the cards. |
| `employee_id` | Many2one → \`hr.employee\` | Employee |  | ✓ | Employee whose cards were suspended (from the leave). |
| `company_id` | Many2one → \`res.company\` | *from leave_id.company_id* |  | ✓ | Company of the leave, for multi-company isolation. |
| `blocked_card_ids` | Many2many → \`hr.rfid.card\` | Suspended Cards |  | ✓ | Exactly the cards that were active when the leave was approved and got deactivat |
| `state` | Selection | State | ✓ | ✓ | Blocking: cards currently suspended. Restored: access was given back (leave ende |
| `blocked_at` | Datetime | Blocked At |  | ✓ | When the cards were suspended. |
| `restored_at` | Datetime | Restored At |  | ✓ | When access was restored. |

#### Notable methods

- **`_cron_follow_the_leaves(self)`** - decorators: `@api.model`
  - Stop the cards of the approved leaves that have begun, and give them back for the leaves that are over.
  - effects: `log_info`
  - touches: `hr.leave`
- **`_cron_restore_expired_blocks(self)`** - decorators: `@api.model`
  - Restore access for leaves whose end date has passed.
  - effects: `log_info`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_leave.py`

- **`RESTORE_STATES`** *(collection)* = `('draft', 'confirm', 'refuse', 'cancel')`  - line 7

### `models/hr_rfid_leave_block.py`

- **`GC_RESTORED_BLOCK_DAYS`** *(scalar)* = `365`  - line 11


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_leave_block_view_list` | `hr.rfid.leave.block` | - |  | `views/hr_rfid_leave_block_views.xml` |
| `hr_rfid_leave_block_view_form` | `hr.rfid.leave.block` | - |  | `views/hr_rfid_leave_block_views.xml` |
| `hr_rfid_leave_block_view_search` | `hr.rfid.leave.block` | - |  | `views/hr_rfid_leave_block_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_leave_block_user` | `model_hr_rfid_leave_block` | `hr_holidays.group_hr_holidays_user` | ✓ |  |  |  |

| `access_hr_rfid_leave_block_manager` | `model_hr_rfid_leave_block` | `hr_holidays.group_hr_holidays_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_rfid_leave_block_multi_company`** on `model_hr_rfid_leave_block` - perms=`RWCD`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`ir_cron_restore_expired_leave_blocks`** (RFID: Follow time off (stop and give back access)) on `model_hr_rfid_leave_block`, runs every 15 minutes, active=True

### Data records summary

- `hr.rfid.card`: 4 record(s)
- `hr.employee`: 2 record(s)
- `hr.leave`: 2 record(s)
- `ir.cron`: 1 record(s)
- `ir.actions.act_window`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (1): `static/tests/tours/leave_block_tour.js`



## Diagrams & Screenshots <a id='images'></a>

No images, diagrams or screenshots are shipped with this module.


## FAQ & Troubleshooting <a id='faq'></a>

No FAQ candidates have been mined yet. Run the skill with the `chat_history` miner enabled, or author `docs/faq.md` manually to populate this section.


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_leave_block`
- Source digest: `sha256:ea878fc613ed9cc0bd2044fbb922740634fef802297faeac5702d50221d86edf`
- Generated at: `2026-11-20T10:19:39+00:00`
- Generator: `polimex_module_knowledge`
