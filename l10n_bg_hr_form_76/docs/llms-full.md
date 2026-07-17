---
id: l10n_bg_hr_form_76
title: Attendance Form 76 Bulgaria
module: l10n_bg_hr_form_76
module_version: 19.0.1.0.2
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Form 76 for Bulgaria
last_updated: '2026-04-29'
source_digest: sha256:3dc726145ed218680f8acf3eafae61e2abfd1fbc7c91d8a1a22fb21c2c6336b1
depends:
- hr_attendance_late
- hr_holidays
entities:
  primary: hr.employee
  related:
  - hr.leave.type
  - hr.attendance.form76.wizard
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
author: Polimex Holding Ltd.
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


# Attendance Form 76 Bulgaria — `l10n_bg_hr_form_76` v19.0.1.0.2

Form 76 for Bulgaria

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `l10n_bg_hr_form_76`
- **Version**: `19.0.1.0.2`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Holding Ltd.
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_attendance_late`, `hr_holidays`


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i l10n_bg_hr_form_76 --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:6`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `corporate_internal_number` | Char |  |  | ✓ |  |

#### Notable methods

- **`f76_intervals(self, specific_date)`** — decorators: —
  - Check if a specific date is a non-working day for the employee.

### `hr.leave.type` <a id='model-hr-leave-type'></a>
Python class `HolidaysType` in `models/hr_leave_type.py:4`.  Model.  Inherits: `hr.leave.type`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `form76_code` | Char | Код за форма 76 |  | ✓ |  |
| `form76_law_reason` | Char | Основание за оптуска |  | ✓ |  |
| `form76_description` | Text | Описание |  | ✓ |  |

### `hr.attendance.form76.wizard` <a id='model-hr-attendance-form76-wizard'></a>
Python class `WizardHrForm76` in `wizards/report_form_76_wizard.py:5`.  TransientModel (wizard).  Description: *Wizard for generation Form 76 in Bulgaria*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `department_ids` | Many2many → \`hr.department\` | Departments | ✓ | ✓ | Generate report for this Department/s |
| `report_year` | Integer | Calendar Year | ✓ | ✓ |  |
| `report_month` | Selection |  | ✓ | ✓ |  |
| `precision` | Integer |  | ✓ | ✓ | Round the hours to exact precision. Precision=2 (0.00) means 2 digits after deci |
| `set_hours_to` | Integer |  | ✓ | ✓ | Replace hours with this hours.  This operation will replace real hours per day w |

#### Notable methods

- **`report_print(self)`** — decorators: —
- **`report_view(self)`** — decorators: —


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestForm76Common.setUpClass(cls)`** (`@classmethod`) — `tests/test_form_76.py:11`
  - calls `super()`
  - touches: `hr.department`, `hr.employee`, `hr.leave.type`
- **`TestLeaveType.test_form76_code_default(self)`** — `tests/test_form_76.py:62`
  - touches: `hr.leave.type`
- **`TestLeaveType.test_form76_law_reason_default(self)`** — `tests/test_form_76.py:69`
  - touches: `hr.leave.type`
- **`TestLeaveType.test_form76_custom_code(self)`** — `tests/test_form_76.py:76`
- **`TestEmployee.test_corporate_internal_number(self)`** — `tests/test_form_76.py:85`
- **`TestEmployee.test_f76_intervals_working_day(self)`** — `tests/test_form_76.py:89`
  - Monday should be a working day.
- **`TestEmployee.test_f76_intervals_weekend(self)`** — `tests/test_form_76.py:103`
  - Saturday should be non-working.
- **`TestEmployee.test_f76_intervals_string_date(self)`** — `tests/test_form_76.py:113`
  - Test with string date input.
- **`TestEmployee.test_f76_intervals_invalid_input(self)`** — `tests/test_form_76.py:123`
  - Test with invalid input raises ValueError.
- **`TestWizard.test_wizard_defaults(self)`** — `tests/test_form_76.py:142`
- **`TestWizard.test_wizard_prepare_report_data(self)`** — `tests/test_form_76.py:147`
- **`TestWizard.test_wizard_invalid_year(self)`** — `tests/test_form_76.py:158`
- **`TestWizard.test_wizard_future_year(self)`** — `tests/test_form_76.py:163`
- **`TestWizard.test_wizard_report_print(self)`** — `tests/test_form_76.py:168`
- **`TestWizard.test_wizard_report_view_preview(self)`** — `tests/test_form_76.py:180`
- **`TestWizard.test_wizard_preview_does_not_modify_db(self)`** — `tests/test_form_76.py:187`
  - Preview should NOT modify the ir.actions.report record.
- **`TestReportForm76.test_get_attendance_data_returns_correct_structure(self)`** — `tests/test_form_76.py:217`
  - SQL query should return rows with correct number of columns.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_attendance_data_february(self)`** — `tests/test_form_76.py:233`
  - February should have 28 or 29 days.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_attendance_data_filters_by_department(self)`** — `tests/test_form_76.py:242`
  - Only employees in specified department should be returned.
  - touches: `hr.department`, `hr.employee`, `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_attendance_data_company_filter(self)`** — `tests/test_form_76.py:266`
  - SQL query should filter by company_id.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_holiday_map(self)`** — `tests/test_form_76.py:276`
  - Holiday map should identify weekends correctly.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_holiday_map_multiple_employees(self)`** — `tests/test_form_76.py:297`
  - Holiday map should handle multiple employees.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_report_values_structure(self)`** — `tests/test_form_76.py:310`
  - Report values should contain all required keys.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_report_values_line_structure(self)`** — `tests/test_form_76.py:328`
  - Each line in departments should have all named keys.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_report_values_no_data_raises(self)`** — `tests/test_form_76.py:350`
  - Report without data should raise UserError.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_get_report_values_with_leave(self)`** — `tests/test_form_76.py:357`
  - Approved leave should appear with correct form76 code.
  - touches: `hr.leave`, `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_vertical_text(self)`** — `tests/test_form_76.py:389`
  - vertical_text should join characters with <br/>.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestReportForm76.test_set_hours_to_replaces_actual(self)`** — `tests/test_form_76.py:395`
  - When set_hours_to > 0, actual hours should be replaced.
  - touches: `report.l10n_bg_hr_form_76.report_form_76`
- **`TestHolidayRequestReport.test_report_action_exists(self)`** — `tests/test_form_76.py:415`
  - Holiday request report action should exist.
- **`TestHolidayRequestReport.test_form76_report_action_exists(self)`** — `tests/test_form_76.py:425`
  - Form 76 report action should exist.

### Private helpers

- **`TestWizard._create_wizard(self, **kwargs)`** — `tests/test_form_76.py:133`
  - touches: `hr.attendance.form76.wizard`
- **`TestReportForm76._get_report_data(self, **kwargs)`** — `tests/test_form_76.py:205`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_employee_form_inherit_form76` | `hr.employee` | — | hr.view_employee_form | `views/hr_employee.xml` |
| `view_employee_filter_inherit` | `hr.employee` | — | hr.view_employee_filter | `views/hr_employee.xml` |
| `f76_edit_holiday_status_form` | `hr.leave.type` | — | hr_holidays.edit_holiday_status_form | `views/hr_leave_type_views.xml` |
| `f76_view_holiday_status_normal_tree` | `hr.leave.type` | — | hr_holidays.view_holiday_status_normal_tree | `views/hr_leave_type_views.xml` |

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


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_attendance_form76_wizard` | `model_hr_attendance_form76_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `hr.leave.type`: 12 record(s)
- `report.paperformat`: 1 record(s)


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

### From `gotchas` (2)

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

### From `git_log` (1)

#### Fix: [FIX] manifest validator issues flagged by Odoo Apps
<!-- source: git_log ref: 9a3d488b201a3d36dd71ae01c4b394d2ee8b8caf occ: 1 conf: 0.60 -->

Commit `9a3d488b20` (2026-04-21): [FIX] manifest validator issues flagged by Odoo Apps


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/l10n_bg_hr_form_76`
- Source digest: `sha256:3dc726145ed218680f8acf3eafae61e2abfd1fbc7c91d8a1a22fb21c2c6336b1`
- Generated at: `2026-04-29T07:30:42+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
