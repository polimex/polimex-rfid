---
id: hr_rfid_site_manager
title: RFID Site Manager
module: hr_rfid_site_manager
module_version: 19.0.1.1.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        Add classification of the access control equipment\n    "
last_updated: '2026-04-30'
source_digest: sha256:be9259493d6b47430ff73013550e036d187a57683c316283ad8f1926ba842b68
depends:
- hr_rfid
- web_hierarchy
entities:
  primary: hr.rfid.access.group
  related:
  - hr.rfid.ctrl
  - hr.rfid.ctrl.alarm.group
  - hr.rfid.door
  - hr.rfid.event.user
  - hr.rfid.site
  - hr.rfid.webstack
  - res.partner
keywords:
- access
- alarm
- classification
- control
- ctrl
- door
- equipment
- event
- group
- manager
- rfid
- site
- user
license: AGPL-3
author: Polimex Team <software@polimex.co>
category: Administration
installable: true
application: false
auto_install: false
counts:
  models: 8
  views: 18
  access_rules: 1
  record_rules: 1
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:35a97385b8ae01772270abd9102b803ab496cbeb4ac54535d98544fc199a0ac3
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:ff6647da01f7cbff307edd7410eb67a002a833edf2c032d659a018491cdcb374
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Site Manager — `hr_rfid_site_manager` v19.0.1.1.0


        Add classification of the access control equipment
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_site_manager`
- **Version**: `19.0.1.1.0`
- **Category**: Administration
- **License**: AGPL-3
- **Author**: Polimex Team <software@polimex.co>
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `web_hierarchy`

### README (verbatim)

.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
HR RFID Site Manager
======================

    TODO
Configuration
-------------
    No

Usage
-----



Wish list
---------
Title change on web client

Contributors
------------

Polimex Holding Development team

Maintainer
----------

.. image:: https://raw.githubusercontent.com/polimex/logos/5c5af675ad5d6ef12bb29664c250196c51ac2bc8/company_logo.png
   :alt: Polimex Logo
   :target: https://polimex.co

This module is created and maintained by the Polimex Dev Team.


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_site_manager --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.access.group` <a id='model-hr-rfid-access-group'></a>
Python class `HrRFIDAccessGroup` in `models/hr_rfid_access_group.py:6`.  Model.  Inherits: `hr.rfid.access.group`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Site that owns this access group. The group automatically includes all doors fro |

#### Notable methods

- **`update_door_list(self, door_ids, time_schedule=None, alarm_rights=False)`** — decorators: —
- **`unlink(self)`** — decorators: —
  - super-split (super `unlink`): pre=`raise:UserError` · post=—
  - effects: `raise:UserError`

### `hr.rfid.ctrl` <a id='model-hr-rfid-ctrl'></a>
Python class `HrRfidController` in `models/hr_rfid_ctrl.py:4`.  Model.  Inherits: `hr.rfid.ctrl`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Physical site where this controller is installed. Used for organizing controller |

### `hr.rfid.ctrl.alarm.group` <a id='model-hr-rfid-ctrl-alarm-group'></a>
Python class `HrRfidCtrlAlarmGroup` in `models/hr_rfid_ctrl_alarm_group.py:3`.  Model.  Inherits: `hr.rfid.ctrl.alarm.group`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Site where this alarm group is active. Used for organizing security systems by l |

### `hr.rfid.door` <a id='model-hr-rfid-door'></a>
Python class `HrRFIDDoor` in `models/hr_rfid_door.py:3`.  Model.  Inherits: `hr.rfid.door`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Physical site where this door is located. Doors are automatically included in si |

#### Notable methods

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`unlink(self)`** — decorators: —
  - calls `super() `unlink``

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidUserEvent` in `models/hr_rfid_event_user.py:4`.  Model.  Inherits: `hr.rfid.event.user`.  Description: *RFID User Event*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Site where this RFID event occurred, computed automatically from the door, contr |

#### Notable methods

- **`_compute_site_id(self)`** — decorators: `@api.depends`

### `hr.rfid.site` <a id='model-hr-rfid-site'></a>
Python class `HrRFIDSite` in `models/hr_rfid_site.py:6`.  Model.  Inherits: `mail.thread`, `avatar.mixin`.  Description: *Building manager site classification*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  | ✓ | ✓ | Name of the site (building, floor, room, etc.). Must be unique within the parent |
| `active` | Boolean | Active |  | ✓ | Uncheck to archive this site. Archived sites are hidden from most views but pres |
| `color` | Integer | Color Index |  | ✓ | Color coding for visual identification in hierarchy view. Choose different color |
| `company_id` | Many2one → \`res.company\` |  |  | ✓ | Company that owns this site. Used for multi-company access control and data sepa |
| `make_access_group` | Boolean | Make access group |  | ✓ | Automatically create and maintain an access group for this site.          • When |
| `parent_path` | Char |  |  | ✓ |  |
| `parent_id` | Many2one → \`hr.rfid.site\` | Parent site |  | ✓ | Parent site in the hierarchy. For example: Building > Floor > Room. Leave empty  |
| `child_ids` | One2many → \`hr.rfid.site\` | Child sites |  | ✓ | Sites that are hierarchically below this site. For example: floors within a buil |
| `webstack_ids` | One2many → \`hr.rfid.webstack\` | Modules |  | ✓ | RFID communication modules (webstacks) installed at this site. Each module can m |
| `controller_ids` | One2many → \`hr.rfid.ctrl\` | Controllers |  | ✓ | RFID controllers located at this site. Controllers manage individual doors and r |
| `door_ids` | One2many → \`hr.rfid.door\` | Doors |  | ✓ | Physical doors and access points at this site. Each door can have entry and exit |
| `child_door_ids` | One2many → \`hr.rfid.door\` | Child doors |  | — | All doors from child sites, computed automatically. Used for hierarchical access |
| `access_group_ids` | One2many → \`hr.rfid.access.group\` | Access groups |  | ✓ | Access control groups automatically created for this site. Groups contain all do |
| `alarm_line_group_ids` | One2many → \`hr.rfid.ctrl.alarm.group\` | Alarm Groups |  | ✓ | Security alarm groups configured for this site. Used for arming/disarming securi |
| `state` | Selection | Alarm Group State |  | — | Current security state of alarm groups at this site. Shows whether security syst |
| `child_count` | Integer | Child Count |  | — | Number of child sites under this site in the hierarchy. |
| `webstack_count` | Integer | Module Count |  | — | Number of RFID communication modules (webstacks) at this site. |
| `controller_count` | Integer | Controller Count |  | — | Number of RFID controllers at this site. |
| `door_count` | Integer | Door Count |  | — | Number of doors and access points at this site. |
| `access_group_count` | Integer | Access Group Count |  | — | Number of access control groups created for this site. |
| `alarm_line_group_count` | Integer | Alarm Line Group Count |  | — | Number of security alarm groups configured for this site. |

#### Notable methods

- **`_compute_count(self)`** — decorators: `@api.depends`
- **`_compute_display_name(self)`** — decorators: `@api.depends`
- **`_compute_child_door_ids(self)`** — decorators: `@api.depends`
  - touches: `hr.rfid.door`
- **`create_child(self)`** — decorators: —
- **`get_child_access_groups(self)`** — decorators: —
  - touches: `hr.rfid.access.group`
- **`create(self, vals_list)`** — decorators: —
  - calls `super() `create``
- **`partner_access_group(self)`** — decorators: —
  - touches: `hr.rfid.access.group`
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`get_children_site_ids(self)`** — decorators: —
  - touches: `hr.rfid.site`
- **`get_site_hierarchy(self)`** — decorators: —
- **`open_child_site_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`open_door_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`open_controller_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`open_webstack_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`open_access_group_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`open_alarm_line_group_list_action(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`arm(self)`** — decorators: —
- **`disarm(self)`** — decorators: —

### `hr.rfid.webstack` <a id='model-hr-rfid-webstack'></a>
Python class `HrRFIDWebStack` in `models/hr_rfid_webstack.py:4`.  Model.  Inherits: `hr.rfid.webstack`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_id` | Many2one → \`hr.rfid.site\` | Site |  | ✓ | Physical site where this communication module (webstack) is installed. Used for  |

### `res.partner` <a id='model-res-partner'></a>
Python class `ResPartner` in `models/res_partner.py:4`.  Model.  Inherits: `res.partner`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `site_ids` | Many2many → \`hr.rfid.site\` | Sites |  | ✓ | Sites where this person has access or is responsible for.          • For employe |

#### Notable methods

- **`onchange_site_ids(self)`** — decorators: `@api.onchange`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_access_group_view_form_inherit` | `hr.rfid.access.group` | — | hr_rfid.hr_rfid_access_group_view_form | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_view_tree_inherit` | `hr.rfid.access.group` | — | hr_rfid.hr_rfid_access_group_view_list | `views/hr_rfid_access_group.xml` |
| `hr_rfid_ctrl_view_form_inherit` | `hr.rfid.ctrl` | — | hr_rfid.hr_rfid_controller_view_form | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_search` | `hr.rfid.ctrl` | — | hr_rfid.hr_rfid_controller_view_search | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_kanban` | `hr.rfid.ctrl` | — | hr_rfid.hr_rfid_controller_view_kanban | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_ctrl_alarm_group_form_view_inherit` | `hr.rfid.ctrl.alarm.group` | — | hr_rfid.hr_rfid_ctrl_alarm_group_form_view | `views/hr_rfid_ctrl_alarm_line.xml` |
| `hr_rfid_door_view_form_inherit` | `hr.rfid.door` | — | hr_rfid.hr_rfid_door_view_form | `views/hr_rfid_door.xml` |
| `hr_rfid_door_view_kanban_inherit` | `hr.rfid.door` | — | hr_rfid.hr_rfid_door_view_kanban | `views/hr_rfid_door.xml` |
| `hr_rfid_user_ev_view_form_inherit` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_form | `views/hr_rfid_event_user.xml` |
| `hr_rfid_user_ev_view_tree_inherit` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_event_user.xml` |
| `hr_rfid_site_view_tree` | `hr.rfid.site` | — |  | `views/hr_rfid_site.xml` |
| `hr_rfid_site_view_form` | `hr.rfid.site` | — |  | `views/hr_rfid_site.xml` |
| `view_site_filter` | `hr.rfid.site` | — |  | `views/hr_rfid_site.xml` |
| `hr_rfid_site_hierarchy_view` | `hr.rfid.site` | — |  | `views/hr_rfid_site.xml` |
| `hr_rfid_webstack_view_form_inherit` | `hr.rfid.webstack` | — | hr_rfid.hr_rfid_webstack_view_form | `views/hr_rfid_webstack.xml` |
| `webstack_view_search_inherit` | `hr.rfid.webstack` | — | hr_rfid.webstack_view_search | `views/hr_rfid_webstack.xml` |
| `hr_rfid_webstack_view_kanban` | `hr.rfid.webstack` | — | hr_rfid.hr_rfid_webstack_view_kanban | `views/hr_rfid_webstack.xml` |
| `hr_view_partner_form_inherit_rfid_site` | `res.partner` | — | hr_rfid.hr_view_partner_form_inherit_hr_rfid | `views/res_partner_views.xml` |

#### Sample XPath operations

- In `hr_rfid_access_group_view_form_inherit`:
  - `//form/sheet/group [inside]`

- In `hr_rfid_access_group_view_tree_inherit`:
  - `//field[@name='company_id'] [before]`
  - `//list [attributes]`

- In `hr_rfid_controller_view_search`:
  - `//field[@name='sw_version'] [after]`

- In `hr_rfid_controller_view_kanban`:
  - `//field[@name='emergency_state'] [after]`
  - `//ul[hasclass('list-unstyled', 'text-muted', 'small')] [inside]`

- In `hr_rfid_ctrl_alarm_group_form_view_inherit`:
  - `//group [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_guard`, `group_own_sites`, `group_`


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `hr_rfid_site_manager.access_hr_rfid_site` | `model_hr_rfid_site` | `hr_rfid_site_manager.group_guard` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_rfid_site_multi_company`** on `model_hr_rfid_site` — perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `hr.rfid.site`: 7 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**OWL components**: `SiteChart`


**JS files** (1): `static/src/components/site_chart/site_chart.js`


**SCSS files** (1): `static/src/components/site_chart/site_chart.scss`


**QWeb templates** (1): `static/src/components/site_chart/site_chart.xml`



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

### From `gotchas` (4)

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.90 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `api.onchange, api.model_create_multi, _compute, @api.onchange, @api.model_create_multi`

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

Matched tokens: `models.constraint`

### From `git_log` (1)

#### Fix: [FIX] hr_rfid_site_manager: Fix XPath inheritance and improve documentat
<!-- source: git_log ref: 50d27edfbb4367cdcfc5c12b93018a1ca350d4b9 occ: 1 conf: 0.60 -->

Commit `50d27edfbb` (2025-11-03): [FIX] hr_rfid_site_manager: Fix XPath inheritance and improve documentation


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_rfid_site_manager`
- Source digest: `sha256:be9259493d6b47430ff73013550e036d187a57683c316283ad8f1926ba842b68`
- Generated at: `2026-04-30T10:42:51+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
