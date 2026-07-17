---
id: hr_rfid_leave_block
title: RFID Access Block on Leave
module: hr_rfid_leave_block
module_version: 19.0.1.0.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Suspend RFID cards while an employee is on approved leave
last_updated: '2026-06-03'
source_digest: sha256:524370fd3e63071c41929ff63b58aac7999190264ea1559318a7010d642cd392
depends:
- hr_rfid
- hr_holidays
entities:
  primary: hr.leave
  related:
  - hr.rfid.leave.block
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
author: Polimex
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


# RFID Access Block on Leave — `hr_rfid_leave_block` v19.0.1.0.0

Suspend RFID cards while an employee is on approved leave

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_leave_block`
- **Version**: `19.0.1.0.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `hr_holidays`

### README (verbatim)

#### RFID Access Block on Leave

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Suspend an employee's RFID cards automatically while they are on approved time off, and restore them when the leave ends.

##### 🎯 Overview

When a time-off request is approved, this module deactivates the employee's currently-active RFID cards so they cannot enter while away. It remembers the exact set of cards it suspended and re-activates only those when access is restored — the day after the leave ends, or immediately if the leave is refused or cancelled. A card the employee had already disabled before the leave, or added during it, is intentionally left untouched.

##### ✨ Key Features

- **Per-card snapshot** — records exactly which cards were active and got suspended (`hr.rfid.leave.block`), so restore never silently re-enables a card the user meant to keep off.
- **Automatic on approval** — a `hr.leave` state transition to *Approved* triggers the suspension; *Refused* / *Cancelled* / back-to-draft triggers the restore.
- **Idempotent** — re-approving a leave that already has an active block does not double-suspend or re-snapshot.
- **Scheduled restore** — a daily cron restores access for leaves whose end date has passed.
- **Self-cleaning audit** — restored audit rows are reclaimed by `@api.autovacuum` after one year, in batches.
- **Multi-company isolated** — blocks are scoped to the leave's company.

##### 📋 Requirements

- Odoo 19.0+
- `hr_rfid`
- `hr_holidays`

##### ⚙️ Configuration

No configuration is required. The behaviour is wired to the standard time-off approval flow. Two scheduled actions are created on install:

- **Restore RFID access for ended leaves** — daily.
- Restored audit rows are garbage-collected by the core *Auto-vacuum* cron (no separate schedule).

##### 🚀 Usage

1. Approve a time-off request for an employee who holds RFID cards.
2. The employee's active cards are suspended and listed under **RFID ▸ Leave Access Blocks**.
3. When the leave ends (or is refused/cancelled), the snapshotted cards are re-activated automatically.

##### 🛠️ Technical

- **Model `hr.rfid.leave.block`** — `leave_id`, related `employee_id`/`company_id`, `blocked_card_ids` (M2M snapshot read with `active_test=False` so archived cards stay visible), `state` (`active`/`restored`), `blocked_at`/`restored_at`.
- **`hr.leave.write` hook** — reacts to the `state` transition after the core write succeeds; `validate` → `_rfid_block_access`, `draft`/`confirm`/`refuse`/`cancel` → `_rfid_restore_access`.
- **`_cron_restore_expired_blocks`** — restores blocks whose `leave_id.date_to` has passed.
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

- **`write(self, vals)`** — decorators: —
  - calls `super() `write``

### `hr.rfid.leave.block` <a id='model-hr-rfid-leave-block'></a>
Python class `HrRfidLeaveBlock` in `models/hr_rfid_leave_block.py:14`.  Model.  Description: *RFID Access Block for Leave*.  Default order: `blocked_at desc`.

> Audit snapshot of RFID cards suspended for one approved leave.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `leave_id` | Many2one → \`hr.leave\` | Leave | ✓ | ✓ | The approved time-off that triggered suspending the cards. |
| `employee_id` | Many2one → \`hr.employee\` | Employee |  | ✓ | Employee whose cards were suspended (from the leave). |
| `company_id` | Many2one → \`res.company\` |  |  | ✓ | Company of the leave, for multi-company isolation. |
| `blocked_card_ids` | Many2many → \`hr.rfid.card\` | Suspended Cards |  | ✓ | Exactly the cards that were active when the leave was approved and got deactivat |
| `state` | Selection |  | ✓ | ✓ | Blocking: cards currently suspended. Restored: access was given back (leave ende |
| `blocked_at` | Datetime |  |  | ✓ | When the cards were suspended. |
| `restored_at` | Datetime |  |  | ✓ | When access was restored. |

#### Notable methods

- **`_cron_restore_expired_blocks(self)`** — decorators: `@api.model`
  - Restore access for leaves whose end date has passed.
  - effects: `log_info`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments — rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_leave.py`

- **`RESTORE_STATES`** *(collection)* = `('draft', 'confirm', 'refuse', 'cancel')`  — line 7

### `models/hr_rfid_leave_block.py`

- **`GC_RESTORED_BLOCK_DAYS`** *(scalar)* = `365`  — line 11


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestRfidLeaveBlock.setUpClass(cls)`** (`@classmethod`) — `tests/test_leave_block.py:20`
  - calls `super()`
  - touches: `hr.employee`, `hr.leave.type`, `hr.rfid.card`, `hr.rfid.leave.block`
- **`TestRfidLeaveBlock.test_validate_blocks_active_cards_only(self)`** — `tests/test_leave_block.py:48`
  - Headline: 2 active + 1 inactive → only the 2 active are suspended.
- **`TestRfidLeaveBlock.test_restore_reactivates_only_snapshot(self)`** — `tests/test_leave_block.py:64`
  - On restore, only the snapshotted cards come back — not the third.
- **`TestRfidLeaveBlock.test_cancel_restores_access(self)`** — `tests/test_leave_block.py:78`
- **`TestRfidLeaveBlock.test_idempotent_revalidate(self)`** — `tests/test_leave_block.py:86`
  - Re-approving must not create a second block or re-snapshot.
- **`TestRfidLeaveBlock.test_cron_restores_expired(self)`** — `tests/test_leave_block.py:99`
  - Cron restores access for a leave whose end date has passed.
- **`TestRfidLeaveBlock.test_no_active_cards_no_block(self)`** — `tests/test_leave_block.py:110`
  - Employee with no active cards → no block row created.
- **`TestRfidLeaveBlock.test_gc_restored_blocks(self)`** — `tests/test_leave_block.py:117`
  - Autovacuum drops old restored rows, keeps fresh + active ones.
- **`TestLeaveBlockTour.setUpClass(cls)`** (`@classmethod`) — `tests/test_tours.py:14`
  - calls `super()`
  - touches: `hr.employee`, `hr.leave`, `hr.leave.type`, `hr.rfid.card`, `res.users`
- **`TestLeaveBlockTour.test_leave_approval_blocks_cards_tour(self)`** — `tests/test_tours.py:54`
  - Process: officer approves a leave → cards suspended + block logged.
  - effects: `with_context`
  - touches: `hr.rfid.leave.block`

### Private helpers

- **`TestRfidLeaveBlock._card(self, number, active=True)`** — `tests/test_leave_block.py:32`
- **`TestRfidLeaveBlock._leave(self, days_from_today=1, length=3)`** — `tests/test_leave_block.py:39`
  - touches: `hr.leave`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_leave_block_view_list` | `hr.rfid.leave.block` | — |  | `views/hr_rfid_leave_block_views.xml` |
| `hr_rfid_leave_block_view_form` | `hr.rfid.leave.block` | — |  | `views/hr_rfid_leave_block_views.xml` |
| `hr_rfid_leave_block_view_search` | `hr.rfid.leave.block` | — |  | `views/hr_rfid_leave_block_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_rfid_leave_block_user` | `model_hr_rfid_leave_block` | `hr_holidays.group_hr_holidays_user` | ✓ |  |  |  |

| `access_hr_rfid_leave_block_manager` | `model_hr_rfid_leave_block` | `hr_holidays.group_hr_holidays_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_rfid_leave_block_multi_company`** on `model_hr_rfid_leave_block` — perms=`R`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`ir_cron_restore_expired_leave_blocks`** (RFID: Restore access after leave ends) on `model_hr_rfid_leave_block`, runs every 1 days, active=True

### Data records summary

- `ir.cron`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>

No images, diagrams or screenshots are shipped with this module.


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `gotchas` (7)

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `_registry_readonly_enabled = false, readonly_enabled, httpcase`

#### Gotcha: **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_g
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_group_ids` за implied groups, compute). Старото `groups_id` гърми с `ValueError: Invalid field 'groups_id' in 'res.users'` — често в test setUp при `create({'group_ids': [(4, ref)]})`. Същото важи навсякъде където създаваш/филтрираш users по групи.

Matched tokens: `group_ids, res.users`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `help=, <p>`

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

#### Gotcha: **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай cus
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай custom XML тагове в имейл маркери.** Odoo sanitize-ва всяко съхранено `body_html`/`body` (mail.mail, mail.message), вкл. съдържанието на HTML коментари които приличат на conditional comment (`<!--[...]-->`). Непознат таг като `<payload encoding="base64">` се изтрива (отварящият таг), но оставя висящ `</payload>` → целият XML маркер става unparseable, дори простите тагове (`<auth>`, `<ticket>`) които оцеляват не се четат. **Решения:** (1) tolerant parse — при `ET.ParseError` salvage-вай само нужните прости блокове в синтетичен валиден документ; (2) по-робустно — base64-encode целия маркер в един blob (без вътрешни тагове за sanitize да пипа). **Как се хваща**: `from odoo.tools import html_sanitize; assert '<payload' in html_sanitize(body)` — ще fail-не. Винаги тествай маркер round-trip ПРЕЗ `html_sanitize`, не само build→parse.

Matched tokens: `odoo.tools`


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_leave_block`
- Source digest: `sha256:524370fd3e63071c41929ff63b58aac7999190264ea1559318a7010d642cd392`
- Generated at: `2026-06-03T08:31:34+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
