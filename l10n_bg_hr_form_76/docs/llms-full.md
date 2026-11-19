---
id: l10n_bg_hr_form_76
title: Attendance Form 76 Bulgaria
module: l10n_bg_hr_form_76
module_version: 19.0.1.0.10
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Form 76 for Bulgaria
last_updated: '2026-11-19'
source_digest: sha256:6b4f1df0d51ae09ff1ff3826f6cff99d8fa487d8b95e81d7ea61a5b4d14c0072
depends:
- hr_attendance_late
- hr_holidays
entities:
  primary: hr.attendance.form76.wizard
  related:
  - hr.employee
  - hr.leave.type
keywords:
- attendance
- bulgaria
- employee
- form
- form76
- l10n
- leave
- type
- wizard
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 3
  views: 4
  access_rules: 1
  record_rules: 0
  crons: 0
  images: 1
images:
- path: static/description/icon.png
  sha256: sha256:8afd0e6e2b069f3ecd707ab21f3dd1e1c5ac6f4b38f02fe6557a634979a1fa42
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Attendance Form 76 Bulgaria - `l10n_bg_hr_form_76` v19.0.1.0.10

Form 76 for Bulgaria

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `l10n_bg_hr_form_76`
- **Version**: `19.0.1.0.10`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_attendance_late`, `hr_holidays`

### README (verbatim)

===========================
Attendance Form 76 Bulgaria
===========================

The attendance sheet of a department for a month (form 76, "Таблица за
отчитане явяването/неявяването на работа"): every person under contract in
the month, a cell per day with the hours worked or the letter of the
absence, and the totals the NSI template asks for.

Usage
=====

Print the sheet from **Attendances -> Reporting -> Generate Form 76**: pick
the year, the month and the departments.

Which days Form 76 marks
------------------------

Leave is marked on the days it was asked for. Non-working days ("Н") are
the days off of the employee's schedule and the public holidays of the
employee's own company, as they live them, in their own
**Timezone** (employee form, *Settings* tab) - the same days the worked
hours in the form are filed under. A night shift that begins at midnight
is therefore marked on its own day, not on the evening before.

What the columns hold
---------------------

The columns follow the NSI template of the attendance sheet
("Таблица за отчитане явяването/неявяването на работа").

- **Who is on the sheet:** everybody under contract on at least one day of
  the month, including a person who left during the month and was archived,
  and a person hired during it; nobody who left before the month or was hired
  after it. The days outside the contract are blank, not absences, and the
  norm counts only the working days of the contract. This needs the
  **Contract Start Date** (and the end date for a person who left) on the
  employee; an employee without contract dates is on every month's sheet
  while active.
- **Days off ("Н")** are those of the working schedule the person had in that
  month, so a schedule changed later does not change the sheet of a past
  month.
- **Days of leave** show the Form 76 letter of the time-off type. With the
  Bulgarian time-off catalog installed, a time-off type has two Form 76
  letter fields; the letter filled in the catalog's field is printed, the
  sheet's own field is used when the catalog's one is empty.
- **Position and department** are those of the employee's contract version
  in force on the last day of the month, so the sheet of a past month shows
  the position held then, not today's.
- **A working day** shows every hour worked that day, overtime included.
- **"Всичко"** (hours worked) holds the hours of the working days plus the
  hours worked on days off and holidays; **"в т.ч. извънредни"** is the part
  of it that is overtime: overtime on working days plus the hours on days off
  and holidays.
- Hours are rounded day by day, half up, as the day cells are; with
  precision 0 every column prints whole numbers.
- **"Частични"** (under "Неотработени човекочасове") holds the scheduled hours
  not worked on days the person came - arriving late, leaving early, a gap in
  the day (a lunch break is not one of them) - and approved time off
  for part of the day (half a day or some hours) - leave is not worked time.
- **"в т.ч. целодневен престой"** stays empty: standstill caused by the
  employer is not recorded in the system; fill it in by hand if there was
  any.
- With **fixed hours per day** set in the wizard, every worked day shows that
  figure, and neither the overtime nor the missed hours of a working day are
  counted; hours worked on a day off still are.

Credits
=======

Authors
-------

* Polimex Holding Ltd. - https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i l10n_bg_hr_form_76 --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:12`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `corporate_internal_number` | Char | Corporate Internal Number |  | ✓ | Вътрешен корпоративен номер на служителя в дружеството (например табелен/служебе |

#### Notable methods

- **`f76_intervals(self, specific_date)`** - decorators: -
  - Check if a specific date is a non-working day for the employee.

### `hr.leave.type` <a id='model-hr-leave-type'></a>
Python class `HolidaysType` in `models/hr_leave_type.py:4`.  Model.  Inherits: `hr.leave.type`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `form76_code` | Char | Код за форма 76 |  | ✓ | Буквата, с която Форма 76 отбелязва дните на този отпуск, на кирилица: О - редов |
| `form76_law_reason` | Char | Основание за оптуска |  | ✓ | Правното основание за този тип отпуск (член/алинея от КТ или друг нормативен акт |
| `form76_description` | Text | Описание |  | ✓ | Свободен текст за вътрешни нужди — пояснява в кои ситуации да се ползва този тип |

### `hr.attendance.form76.wizard` <a id='model-hr-attendance-form76-wizard'></a>
Python class `WizardHrForm76` in `wizards/report_form_76_wizard.py:5`.  TransientModel (wizard).  Description: *Wizard for generation Form 76 in Bulgaria*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `department_ids` | Many2many → \`hr.department\` | Departments | ✓ | ✓ | Generate report for this Department/s |
| `report_year` | Integer | Calendar Year | ✓ | ✓ | Календарна година за която се генерира Форма 76. Приема стойности от 2020 нататъ |
| `report_month` | Selection | Report Month | ✓ | ✓ | Месец, за който се генерира Форма 76 в комбинация с годината по-горе. |
| `precision` | Integer | Precision | ✓ | ✓ | Round the hours to exact precision. Precision=2 (0.00) means 2 digits after deci |
| `set_hours_to` | Integer | Set Hours To | ✓ | ✓ | Replace hours with this hours.  This operation will replace real hours per day w |

#### Notable methods

- **`report_print(self)`** - decorators: -
- **`report_view(self)`** - decorators: -


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_employee.py`

- **`PUBLIC_HOLIDAYS`** *(collection)* = `[('time_type', '=', 'leave'), ('resource_id', '=', False)]`  - line 9

### `reports/report_form_76_bg.py`

- **`OUT_OF_CONTRACT`** *(scalar)* = `''`  - line 14


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Private helpers

- **`_month_days(first, last)`** - `reports/report_form_76_bg.py:17`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_employee_form_inherit_form76` | `hr.employee` | - | hr.view_employee_form | `views/hr_employee.xml` |
| `view_employee_filter_inherit` | `hr.employee` | - | hr.view_employee_filter | `views/hr_employee.xml` |
| `f76_edit_holiday_status_form` | `hr.leave.type` | - | hr_holidays.edit_holiday_status_form | `views/hr_leave_type_views.xml` |
| `f76_view_holiday_status_normal_tree` | `hr.leave.type` | - | hr_holidays.view_holiday_status_normal_tree | `views/hr_leave_type_views.xml` |

#### Sample XPath operations

- In `hr_employee_form_inherit_form76`:
  - `//field[@name='work_email'] [after]`

- In `view_employee_filter_inherit`:
  - `//field[@name='job_id'] [after]`

- In `f76_edit_holiday_status_form`:
  - `//group[@name='visual'] [before]`

- In `f76_view_holiday_status_normal_tree`:
  - `//field[@name='leave_validation_type'] [after]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_attendance_form76_wizard` | `model_hr_attendance_form76_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `hr.attendance.extra`: 60 record(s)
- `hr.leave.type`: 12 record(s)
- `hr.employee`: 3 record(s)
- `hr.leave`: 3 record(s)
- `ir.actions.report`: 2 record(s)
- `report.paperformat`: 1 record(s)
- `hr.leave.allocation`: 1 record(s)
- `ir.actions.act_window`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**QWeb templates in XML data, rendered by the server** (6): `hr_holiday_request`, `hr_holidays_request_document`, `report_f76_header`, `report_form_76`, `report_f76_department`, `report_f76_footer`



## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (1)

#### Fix: [FIX] manifest validator issues flagged by Odoo Apps

Commit `9a3d488b20` (2026-04-21): [FIX] manifest validator issues flagged by Odoo Apps


## Source provenance <a id='provenance'></a>

- Module: `l10n_bg_hr_form_76`
- Source digest: `sha256:6b4f1df0d51ae09ff1ff3826f6cff99d8fa487d8b95e81d7ea61a5b4d14c0072`
- Generated at: `2026-11-19T16:38:03+00:00`
- Generator: `polimex_module_knowledge`
