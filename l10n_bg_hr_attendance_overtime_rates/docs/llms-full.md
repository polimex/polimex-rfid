---
id: l10n_bg_hr_attendance_overtime_rates
title: Bulgaria — Attendance Overtime Rates
module: l10n_bg_hr_attendance_overtime_rates
module_version: 19.0.1.0.6
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Bulgarian statutory overtime/night coefficients and public holidays
last_updated: '2026-11-19'
source_digest: sha256:4d972331eba215c904431cab34c20e664f2fe625ad85489d2ff8a82b62a9b884
depends:
- hr_attendance_late
- hr_holidays
entities:
  primary: l10n.bg.generate.holidays.wizard
  related:
  - res.company
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
author: Polimex Dev Team
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


# Bulgaria — Attendance Overtime Rates - `l10n_bg_hr_attendance_overtime_rates` v19.0.1.0.6

Bulgarian statutory overtime/night coefficients and public holidays

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `l10n_bg_hr_attendance_overtime_rates`
- **Version**: `19.0.1.0.6`
- **Category**: Human Resources/Attendances
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_attendance_late`, `hr_holidays`

### README (verbatim)

#### Bulgaria - Attendance Overtime Rates & Public Holidays

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Bulgarian localisation seed for the attendance cost layer: statutory overtime coefficients, the night-shift supplement, and official public holidays.

##### 🎯 Overview

`hr_attendance_late` provides a generic, dated legal-rate table (`hr.legal.rate`) used when costing attendance. This module fills it with the Bulgarian Labour Code values and adds the country's public holidays as global calendar leaves, so the cost bridge in `hr_attendace_rfid_hr_hourly_cost` can tell a rest-day from a public holiday.

##### ✨ Key Features

- **КТ overtime coefficients (dated)** - work-day overtime ×1.5, rest-day ×1.75, public-holiday ×2.0 (КТ чл. 262 minimums), seeded with a historical effective date so future law changes are added as new dated rows.
- **Night-shift supplement** - an additive per-hour amount (НСОРЗ чл. 8), seeded at 0.51 EUR effective 2026-01-01 (eurozone). Additive, not a multiplier.
- **Public-holiday generation** - computes the year's official Bulgarian holidays, including the movable Orthodox Easter dates (`dateutil.easter` with `EASTER_ORTHODOX`), as public holidays with no working schedule, so they hold for everybody in the company whatever schedule a person is on (shifts, part time, nights). A day the company already holds is left as it is.
- **Wizard + annual cron** - generate holidays for a chosen year on demand, or let the yearly cron roll the next year forward for every company in Bulgaria that keeps public holidays.

##### 📋 Requirements

- Odoo 19.0+
- `hr_attendance`
- `hr_holidays`
- `hr_attendance_late` (provides the `hr.legal.rate` table the seed targets)

##### ⚙️ Configuration

- The legal rates are seeded on install (`noupdate`, so local overrides survive upgrades). Review or override them under **Attendances ▸ Configuration ▸ Legal Rates**.
- Generate public holidays via **Attendances** → the *Generate Bulgarian Public Holidays* wizard, or rely on the annual cron.

##### 🚀 Usage

1. Install - КТ coefficients and the night supplement appear in **Legal Rates**.
2. Run the holiday wizard for the current/next year (or wait for the cron).
3. The attendance cost bridge reads these rates and the public-holiday calendar automatically; no further setup is needed.

> When the law changes a coefficient, add a **new** Legal Rate row with the new *Valid From* date - past worked days keep their historical value.

##### The holidays it creates

Each generated public holiday is a day off for everybody in the company,
whatever working schedule a person is on: shifts, part time or nights. It is
the whole day, midnight to midnight, in the timezone of the company's working
schedule - whoever generates the year: an HR officer, or the yearly scheduled
action, which has no timezone of its own. This is the shape
**Time Off -> Configuration -> Public Holidays** creates when *Working Hours*
is left empty, so the days it makes and the days typed in by hand read alike.
A day the company already holds as a public holiday is left as it is.

##### 🛠️ Technical

- **`data/legal_rates.xml`** - seeds `hr.legal.rate` rows (`overtime_workday`, `overtime_weekend`, `overtime_holiday`, `night_supplement`).
- **`res.company._generate_bg_public_holidays(year)`** - idempotent batched creation of `resource.calendar.leaves` with no schedule and no resource (core applies them to every schedule of the company); fixed dates + Orthodox-Easter-derived Good Friday / Holy Saturday / Easter Monday.
- **`_cron_generate_bg_public_holidays`** - annual roll-forward, only for companies whose country is Bulgaria.
- **Upgrade to 19.0.1.0.6** - for companies in Bulgaria, official days from today on that earlier versions tied to one schedule are released to every schedule (`_hand_bg_public_holidays_to_everyone`); days already over, closures of several days and closing days on ordinary dates keep their schedule, and a day core refuses to release is logged and left.
- **`generate.bg.holidays.wizard`** - on-demand generation for a chosen year.

##### 👥 Credits

**Polimex Holding Ltd.** - https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i l10n_bg_hr_attendance_overtime_rates --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:62`.  Model.  Inherits: `res.company`.

#### Notable methods

- **`_bg_companies(self)`** - decorators: `@api.model`
  - The companies in Bulgaria - by the country of their address, the way core's localisations tell their companies apart.
- **`_hand_bg_public_holidays_to_everyone(self)`** - decorators: `@api.model`
  - Make the official days held for one working schedule hold for everybody in the company, from today on.
  - effects: `log_info`, `log_warn`, `with_company`
  - touches: `resource.calendar.leaves`
- **`_cron_generate_bg_public_holidays(self)`** - decorators: `@api.model`
  - Yearly cron: seed next year's official days for every company in Bulgaria that keeps public holidays at all.
  - touches: `resource.calendar.leaves`

### `l10n.bg.generate.holidays.wizard` <a id='model-l10n-bg-generate-holidays-wizard'></a>
Python class `GenerateBgHolidaysWizard` in `wizards/generate_bg_holidays_wizard.py:6`.  TransientModel (wizard).  Description: *Generate Bulgarian Public Holidays*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `year` | Integer | Year | ✓ | ✓ | Calendar year to generate the official Bulgarian public holidays for. Fixed date |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | ✓ | Company whose people get the holidays - everybody in it, whatever working schedu |

#### Notable methods

- **`action_generate(self)`** - decorators: -
  - Fill the year in and show the company's public holidays of it.


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/res_company.py`

- **`BG_FIXED_HOLIDAYS`** *(collection)* = `[(1, 1, "New Year's Day"), (3, 3, 'Liberation Day'), (5, 1, 'Labour Day'), (5, 6, "St. George's Day / Day of Valour"), (5, 24, 'Day of Bulgarian Education and Culture'), (9, 6, 'Unification Day'), (9, 22, 'Independence Day'), (12, 24, 'Chri  # ...truncated`  - line 17
- **`ONE_DAY`** *(expression)* = `timedelta(days=1)`  - line 31


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Private helpers

- **`_bg_public_holiday_days(year)`** - `models/res_company.py:34`
  - The official days of that year as (date, name): the fixed dates and the moving Orthodox-Easter cluster.
- **`_day_bounds(day, tz)`** - `models/res_company.py:47`
  - A whole day in that zone, its first and last moment, as stored (naive UTC).
- **`_overlap(a_from, a_to, b_from, b_to)`** - `models/res_company.py:57`
  - Two stretches of time share at least a moment.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `generate_bg_holidays_wizard_form` | `l10n.bg.generate.holidays.wizard` | - |  | `views/hr_public_holidays_views.xml` |


## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

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
- `ir.actions.act_window`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>

No images, diagrams or screenshots are shipped with this module.


## FAQ & Troubleshooting <a id='faq'></a>
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (1)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them


## Source provenance <a id='provenance'></a>

- Module: `l10n_bg_hr_attendance_overtime_rates`
- Source digest: `sha256:4d972331eba215c904431cab34c20e664f2fe625ad85489d2ff8a82b62a9b884`
- Generated at: `2026-11-19T16:38:03+00:00`
- Generator: `polimex_module_knowledge`
