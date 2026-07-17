---
id: hr_attendace_rfid_hr_hourly_cost
title: RFID Hourly Cost
module: hr_attendace_rfid_hr_hourly_cost
module_version: 19.0.1.1.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        RFID attendance hourly cost plugin\n    "
last_updated: '2026-06-03'
source_digest: sha256:898f45364c49574b960aac44247f2e9194dd34c95a7a1a3abd5c5cd59a784864
depends:
- hr_hourly_cost
- hr_attendance_late
entities:
  primary: hr.attendance.extra
  related: []
keywords:
- attendace
- attendance
- cost
- extra
- hourly
- plugin
- rfid
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: true
counts:
  models: 1
  views: 3
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:3ceabf1da5569ca9ab25c75374ff22b04ed98730f14c2d9f2f8b47cfd3ba28ae
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:6c0661d512013d6b8b9fed5006830954e3668820033f5190482313037bf3dec0
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Hourly Cost — `hr_attendace_rfid_hr_hourly_cost` v19.0.1.1.0


        RFID attendance hourly cost plugin
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_attendace_rfid_hr_hourly_cost`
- **Version**: `19.0.1.1.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: yes
- **Installable**: yes
- **Depends on**: `hr_hourly_cost`, `hr_attendance_late`

### README (verbatim)

#### RFID Hourly Cost

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Hourly cost tracking integration for RFID-based attendance records.

##### 🎯 Overview

RFID Hourly Cost bridges RFID attendance tracking with hourly cost calculations, providing accurate labor cost analysis based on actual worked hours captured through RFID access control systems. It automatically calculates labor costs for projects, departments, and cost centers.

##### ✨ Key Features

###### Cost Tracking
- **Automatic Calculation**: Real-time hourly cost computation
- **Multi-rate Support**: Different rates for regular/overtime
- **Department Costs**: Track costs by department
- **Project Allocation**: Assign costs to projects

###### Integration
- **RFID Attendance**: Seamless integration with RFID attendance
- **Payroll Ready**: Export data for payroll processing
- **Accounting Links**: Direct posting to accounting
- **Timesheet Sync**: Update timesheets automatically

###### Reporting
- **Cost Analytics**: Detailed cost breakdowns
- **Department Comparison**: Compare labor costs
- **Project Profitability**: Track project labor costs
- **Budget vs Actual**: Monitor cost overruns

##### 📋 Requirements

- Odoo 18.0+
- hr_hourly_cost module
- hr_attendance_late module
- Python 3.8+

###### Dependencies
```python
'depends': ['hr_hourly_cost', 'hr_attendance_late']
'auto_install': True  # Installs automatically when both dependencies are present
```

##### 🛠️ Installation

This module auto-installs when both dependencies are installed:

```bash
#### Install dependencies first
./odoo-bin -d your_database -i hr_hourly_cost,hr_attendance_late

#### Module will auto-install
```

##### 🔧 Configuration

###### Employee Setup

1. **Navigate to**: Employees → Employee → HR Settings tab
2. **Configure**:
   - Hourly Cost: Base hourly rate
   - Overtime Rate: Overtime multiplier
   - Currency: Cost currency
   - Cost Center: Default allocation

###### Attendance Configuration

Set up in hr_attendance_late module:
- Work schedules
- Overtime rules
- Break deductions
- Shift differentials

###### Cost Rules

Configure in Settings → Attendance → Hourly Cost:
```python
#### Example configuration
regular_hours_limit = 40  # Weekly regular hours
overtime_multiplier = 1.5  # Overtime rate multiplier
include_breaks = False  # Include breaks in cost
```

##### 📖 Usage

###### Automatic Calculation

Costs are calculated automatically when:
1. Employee checks in/out via RFID
2. Attendance records are created
3. Late attendance is processed

###### View Costs

1. **Individual Employee**
   - Employee form → Attendance tab
   - View hourly costs summary
   - Check detailed breakdown

2. **Department Level**
   - Reporting → Attendance → Department Costs
   - Select period and department
   - View aggregated costs

3. **Project Costs**
   - Project → Labor Costs tab
   - See allocated employee costs
   - Track budget utilization

##### 📊 Reports

###### Cost Summary Report
```
Employee Cost Summary
Period: January 2024

Employee          Regular Hours    OT Hours    Total Cost
John Doe          160             10          $3,450.00
Jane Smith        155             15          $3,875.00
Department Total  315             25          $7,325.00
```

###### Detailed Analysis
- Hourly breakdown
- Cost center allocation
- Overtime analysis
- Attendance patterns vs cost

##### 🔌 API Reference

###### Cost Calculation
```python
#### Get employee hourly cost
employee = self.env['hr.employee'].browse(employee_id)
attendance = self.env['hr.attendance'].browse(attendance_id)

#### Calculate cost for attendance period
regular_cost = attendance.worked_hours * employee.hourly_cost
overtime_cost = attendance.overtime_hours * employee.hourly_cost * 1.5
total_cost = regular_cost + overtime_cost
```

###### Bulk Processing
```python
#### Process monthly costs
attendances = self.env['hr.attendance'].search([
    ('check_in', '>=', month_start),
    ('check_in', '<', month_end)
])
attendances.calculate_hourly_costs()
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Costs not calculating**
   - Check employee hourly rate is set
   - Verify attendance records exist
   - Ensure work schedule is configured

2. **Wrong cost amounts**
   - Verify hourly rates
   - Check overtime rules
   - Review calculation settings

3. **Missing in reports**
   - Check date filters
   - Verify employee is active
   - Ensure proper permissions

##### ⚙️ Advanced Features

###### Custom Cost Rules
```python
class HrAttendanceExtra(models.Model):
    _inherit = 'hr.attendance'
    
    def _compute_hourly_cost(self):
        # Add custom logic
        if self.is_holiday:
            return self.worked_hours * self.employee_id.hourly_cost * 2
        return super()._compute_hourly_cost()
```

###### Multi-Currency Support
- Configure rates per currency
- Automatic conversion
- Historical rate tracking

##### 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendace_rfid_hr_hourly_cost/)
- [Support](https://polimex.co/support)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_attendace_rfid_hr_hourly_cost --stop-after-init
```

> **Auto-install**: installed automatically when all dependencies are present.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.attendance.extra` <a id='model-hr-attendance-extra'></a>
Python class `HrAttendanceExtraCost` in `models/hr_attendance_extra.py:11`.  Model.  Inherits: `hr.attendance.extra`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `currency_id` | Many2one → \`res.currency\` | Currency |  | — | Currency for cost calculations (derived from employee).                  • Sourc |
| `hourly_cost` | Monetary | Hourly Cost |  | — | Employee's hourly cost rate (derived from employee record).                  • S |
| `actual_work_time_cost` | Monetary | Actual Work Time Cost |  | ✓ | Total labour cost for the day: regular hours plus overtime and rest-day/holiday  |
| `cost_regular` | Monetary | Regular Cost |  | ✓ | Cost of hours worked inside the schedule at the base rate (hourly cost × actual  |
| `cost_overtime` | Monetary | Overtime Cost |  | ✓ | Cost of overtime worked on a working day, at the КТ чл. 262 working-day multipli |
| `cost_extra` | Monetary | Rest-day / Holiday Cost |  | ✓ | Cost of work performed on a rest day or official holiday, at the КТ чл. 262 rest |
| `cost_night_supplement` | Monetary | Night Supplement |  | ✓ | Additive night-shift supplement (НСОРЗ чл. 8) applied to every night hour worked |

#### Notable methods

- **`_compute_actual_work_time_cost(self)`** — decorators: `@api.depends`
  - touches: `hr.legal.rate`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments — rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_attendance_extra.py`

- **`RATE_OVERTIME_WORKDAY`** *(scalar)* = `'overtime_workday'`  — line 5
- **`RATE_OVERTIME_WEEKEND`** *(scalar)* = `'overtime_weekend'`  — line 6
- **`RATE_OVERTIME_HOLIDAY`** *(scalar)* = `'overtime_holiday'`  — line 7
- **`RATE_NIGHT_SUPPLEMENT`** *(scalar)* = `'night_supplement'`  — line 8


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestAttendanceCostRates.setUpClass(cls)`** (`@classmethod`) — `tests/test_cost.py:16`
  - calls `super()`
  - touches: `hr.employee`, `hr.legal.rate`, `resource.calendar`
- **`TestAttendanceCostRates.test_workday_overtime(self)`** — `tests/test_cost.py:46`
- **`TestAttendanceCostRates.test_weekend_extra(self)`** — `tests/test_cost.py:52`
- **`TestAttendanceCostRates.test_holiday_extra_uses_higher_rate(self)`** — `tests/test_cost.py:58`
- **`TestAttendanceCostRates.test_night_supplement_additive(self)`** — `tests/test_cost.py:64`
- **`TestAttendanceCostRates.test_night_supplement_on_overtime_and_extra(self)`** — `tests/test_cost.py:70`
  - Night supplement covers night hours regardless of class.
- **`TestAttendanceCostRates.test_no_rates_falls_back_to_flat(self)`** — `tests/test_cost.py:77`
  - With multipliers missing for a class, premium defaults to base (1.0).
- **`TestAttendanceCostRates.test_historical_rate_preserved(self)`** — `tests/test_cost.py:85`
  - A later night-rate row must not change a past day's cost on recompute.
- **`TestHourlyCostSmoke.test_hr_attendance_extra_fields_exist(self)`** — `tests/test_smoke.py:9`
  - touches: `hr.attendance.extra`
- **`TestHourlyCostSmoke.test_currency_field_resolves_to_company_currency(self)`** — `tests/test_smoke.py:15`

### Private helpers

- **`TestAttendanceCostRates._ensure_rate(cls, code, date_from, value)`** (`@classmethod`) — `tests/test_cost.py:35`
  - touches: `hr.legal.rate`
- **`TestAttendanceCostRates._mk(self, for_date, **kw)`** — `tests/test_cost.py:42`
  - touches: `hr.attendance.extra`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `view_hr_attendance_extra_form_inherit` | `hr.attendance.extra` | — | hr_attendance_late.hr_attendance_extra_view_form | `views/hr_attendance_extra.xml` |
| `view_hr_attendance_extra_pivot_inherit` | `hr.attendance.extra` | — | hr_attendance_late.hr_attendance_extra_view_pivot | `views/hr_attendance_extra.xml` |
| `view_hr_attendance_extra_list_inherit` | `hr.attendance.extra` | — | hr_attendance_late.hr_attendance_extra_view_tree | `views/hr_attendance_extra.xml` |

#### Sample XPath operations

- In `view_hr_attendance_extra_form_inherit`:
  - `//field[@name='actual_work_time_night'] [after]`

- In `view_hr_attendance_extra_pivot_inherit`:
  - `//field[@name='shift_number'] [after]`

- In `view_hr_attendance_extra_list_inherit`:
  - `//field[@name='shift_number'] [after]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


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

### From `gotchas` (4)

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `_compute`

#### Gotcha: **НЕ сменяй** `company.currency_id` в тестове — "journal items already
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Тестове** in odoo19-gotchas.md:

> **НЕ сменяй** `company.currency_id` в тестове — "journal items already exist" грешка. Ползвай `cls.company.currency_id`

Matched tokens: `company.currency_id`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `help=`

### From `git_log` (2)

#### Fix: [FIX] drop test-framework import from module __init__ (A1)
<!-- source: git_log ref: d3925400454543d7999e8b92bce72f95f1a84e03 occ: 1 conf: 0.60 -->

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: fix license
<!-- source: git_log ref: 6e49a3ef0cee2364b143dcd71a33030362365dd1 occ: 1 conf: 0.60 -->

Commit `6e49a3ef0c` (2024-09-09): fix license


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_attendace_rfid_hr_hourly_cost`
- Source digest: `sha256:898f45364c49574b960aac44247f2e9194dd34c95a7a1a3abd5c5cd59a784864`
- Generated at: `2026-06-03T08:31:34+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
