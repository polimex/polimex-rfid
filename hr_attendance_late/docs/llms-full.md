---
id: hr_attendance_late
title: Late Attendance
module: hr_attendance_late
module_version: 19.0.1.0.5
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Enhances employee attendance tracking with additional work time calculations
last_updated: '2026-08-14'
source_digest: sha256:303b98f12ea9cad9d131646a584c3bf41855bcb139a9b3c26272a01c0fbb341b
depends:
- hr_attendance
- digest
- hr_attendance_multi_rfid
entities:
  primary: digest.digest
  related:
  - hr.attendance
  - hr.attendance.extra
  - hr.department
  - hr.employee
  - hr.legal.rate
  - resource.calendar
  - hr.attendance.extra.wizard
keywords:
- additional
- attendance
- calculations
- department
- digest
- employee
- enhances
- extra
- late
- time
- tracking
- with
- work
license: AGPL-3
author: Polimex
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 8
  views: 10
  access_rules: 4
  record_rules: 2
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:d5b0f806715c08281d851abf35a537fcfb264179d413e11b4c71aa79062f6967
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:de86e3ce933bfe931bf625dd359d13da5fb09c9e1eca676897ec03acaa2d3a6d
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Late Attendance — `hr_attendance_late` v19.0.1.0.5

Enhances employee attendance tracking with additional work time calculations

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_attendance_late`
- **Version**: `19.0.1.0.5`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_attendance`, `digest`, `hr_attendance_multi_rfid`

### README (verbatim)

#### Late Attendance

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Advanced attendance calculations with late arrival tracking and department-based rules.

##### 🎯 Overview

Late Attendance extends Odoo's attendance system with sophisticated late arrival tracking, grace periods, overtime calculations, and department-specific attendance rules. It provides comprehensive reporting on attendance patterns and helps enforce attendance policies.

##### ✨ Key Features

###### Late Tracking
- **Automatic Detection**: Identifies late arrivals based on work schedules
- **Grace Periods**: Configurable tolerance before marking as late
- **Department Rules**: Different late policies per department
- **Excuse Management**: Track and approve late arrival reasons

###### Calculations
- **Work Hours**: Accurate worked time calculations
- **Overtime**: Automatic overtime detection and calculation
- **Break Time**: Configurable break deductions
- **Shift Differential**: Support for different shift timings

###### Reporting
- **Late Summary**: Daily/monthly late arrival reports
- **Department Analytics**: Compare attendance across departments
- **Individual Reports**: Employee attendance history
- **Export Options**: Excel and PDF export capabilities

###### Integration
- **RFID Events**: Works with hr_attendance_multi_rfid
- **Payroll Ready**: Late deductions for payroll
- **Email Alerts**: Automated notifications for violations
- **Manager Dashboard**: Real-time attendance monitoring

##### 📋 Requirements

- Odoo 18.0+
- hr_attendance module
- hr module
- Python 3.8+

###### Optional Dependencies
- hr_attendance_multi_rfid (for RFID integration)
- hr_payroll (for salary deductions)

##### 🛠️ Installation

1. Install the module:
```bash
./odoo-bin -d your_database -i hr_attendance_late
```

2. Configure attendance rules in Settings

##### 🔧 Configuration

###### Global Settings

Navigate to Settings → Attendance → Late Attendance:

```python
#### Attendance parameters
late_attendance_grace_minutes = 5  # Grace period in minutes
late_attendance_minimum_minutes = 15  # Minimum late to count
late_attendance_round_to = 15  # Round late minutes to
```

###### Department Configuration

1. **Go to**: Employees → Departments
2. **Edit Department**: Set attendance rules
   - Grace period (minutes)
   - Late penalty rules
   - Specific work schedules
   - Notification settings

###### Work Schedules

Configure in Settings → Technical → Resource Calendar:
- Set exact work hours
- Define break times
- Configure holidays
- Set timezone

##### 📖 Usage

###### Employee View

Employees can:
1. View their attendance history
2. See late arrival records
3. Submit late excuses
4. Check accumulated late time

###### Manager Functions

1. **Monitor Dashboard**
   - Real-time attendance status
   - Late arrivals alerts
   - Department overview

2. **Approve Excuses**
   - Review late reasons
   - Approve/reject excuses
   - Add manager notes

3. **Generate Reports**
   - Late attendance summary
   - Department comparison
   - Individual employee reports

###### HR Functions

1. **Policy Management**
   - Set attendance rules
   - Configure penalties
   - Define grace periods

2. **Bulk Operations**
   - Approve multiple excuses
   - Export attendance data
   - Generate payroll deductions

##### 📊 Reports

###### Standard Reports

1. **Late Attendance Summary**
   - Employee name
   - Department
   - Late occurrences
   - Total late minutes
   - Excused/unexcused

2. **Department Analysis**
   - Average late per department
   - Trends over time
   - Comparison charts

3. **Individual Report**
   - Detailed attendance history
   - Late patterns
   - Excuse history

###### Custom Reports

Create custom reports using:
```python
#### Get late attendance data
late_records = self.env['hr.attendance'].search([
    ('employee_id', '=', employee_id),
    ('late_minutes', '>', 0),
    ('check_in', '>=', date_from),
    ('check_in', '<=', date_to)
])
```

##### 🔧 Advanced Configuration

###### Calculation Methods

```python
#### In attendance settings
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    attendance_calculation_method = fields.Selection([
        ('actual', 'Actual Time'),
        ('scheduled', 'Scheduled Time'),
        ('flexible', 'Flexible Hours')
    ])
```

###### Notifications

Configure automated emails:
```xml
<!-- Email template for late arrival -->
<record id="email_template_late_arrival" model="mail.template">
    <field name="name">Late Arrival Notification</field>
    <field name="model_id" ref="hr_attendance.model_hr_attendance"/>
    <field name="subject">Late Arrival on ${object.check_in}</field>
</record>
```

###### Integration Hooks

```python
#### Override to add custom logic
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    def _compute_late_minutes(self):
        # Custom late calculation
        super()._compute_late_minutes()
        # Add your logic here
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Late not calculated**
   - Check work schedule configuration
   - Verify timezone settings
   - Ensure calendar is assigned to employee

2. **Wrong late minutes**
   - Check grace period settings
   - Verify break time configuration
   - Review calculation method

3. **Reports missing data**
   - Ensure attendance records exist
   - Check date range filters
   - Verify employee permissions

###### Debug Mode

Enable detailed logging:
```python
#### In Odoo config
log_handler = hr_attendance_late:DEBUG
```

##### 📈 Best Practices

1. **Set Realistic Grace Periods**
   - Consider commute variations
   - Account for clock synchronization
   - Balance strictness with fairness

2. **Regular Monitoring**
   - Review reports weekly
   - Address patterns early
   - Provide feedback to employees

3. **Clear Policies**
   - Document attendance rules
   - Communicate changes
   - Apply consistently

##### 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

##### 📄 License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/late-attendance)
- [Support](https://polimex.co/support)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendance_late/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_attendance_late --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `digest.digest` <a id='model-digest-digest'></a>
Python class `Digest` in `models/digest.py:8`.  Model.  Inherits: `digest.digest`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `kpi_hr_rfid_att_early_come` | Boolean | Early come |  | ✓ | Include a 'Count of employees who arrived early today' KPI in the digest email. |
| `kpi_hr_rfid_att_late` | Boolean | Late |  | ✓ | Include a 'Count of late arrivals' KPI in the digest email. |
| `kpi_hr_rfid_att_leave` | Boolean | Early leave |  | ✓ | Include a 'Count of employees who left early' KPI in the digest email. |
| `kpi_hr_rfid_att_overtime` | Boolean | Overtime |  | ✓ | Include a 'Count of employees who stayed past contract hours' KPI in the digest  |
| `kpi_hr_rfid_att_extra` | Boolean | Extra time |  | ✓ | Include a 'Count of employees with extra unrecorded time' KPI in the digest emai |
| `kpi_hr_rfid_att_no_show` | Boolean | No-show |  | ✓ | Include a 'Count of employees who were scheduled but did not show up' KPI in the |
| `kpi_hr_rfid_att_early_come_value` | Integer |  |  | — | Live count of employees who checked in before their schedule start during the di |
| `kpi_hr_rfid_att_late_value` | Integer |  |  | — | Live count of employees who checked in after their schedule start during the dig |
| `kpi_hr_rfid_att_leave_value` | Integer |  |  | — | Live count of employees who checked out before their schedule end during the dig |
| `kpi_hr_rfid_att_overtime_value` | Integer |  |  | — | Live count of employees with recorded overtime during the digest window. |
| `kpi_hr_rfid_att_extra_value` | Integer |  |  | — | Live count of employees with extra unrecorded time during the digest window. |
| `kpi_hr_rfid_att_no_show_value` | Integer |  |  | — | Live count of scheduled employees with no attendance (no-show) during the digest |

### `hr.attendance` <a id='model-hr-attendance'></a>
Python class `HrAttendance` in `models/hr_attendance.py:6`.  Model.  Inherits: `hr.attendance`.

#### Notable methods

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`unlink(self)`** — decorators: —
  - calls `super() `unlink``

### `hr.attendance.extra` <a id='model-hr-attendance-extra'></a>
Python class `HrAttendanceExtra` in `models/hr_attendance_extra.py:6`.  Model.  Description: *Extra work time calculations*.  Default order: `for_date`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `for_date` | Date | Date | ✓ | ✓ | The specific date for which attendance calculations are performed.          • Fo |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | The employee for whom attendance calculations are performed.                  •  |
| `department_id` | Many2one | Department |  | ✓ | The department of the employee (automatically filled).                  • Source |
| `actual_work_time` | Float | Actual Work Time |  | ✓ | Total hours actually worked on this date (including day and night time).         |
| `actual_work_time_day` | Float | Actual Day Time |  | ✓ | Hours worked during standard daytime period.                  • Format: Hours in |
| `actual_work_time_night` | Float | Actual Night Time |  | ✓ | Hours worked during night shift period.                  • Format: Hours in deci |
| `theoretical_work_time` | Float | Theoretical Work Time |  | ✓ | Expected work hours according to employee's work schedule.                  • So |
| `late_time` | Float | Late Arrival Time |  | ✓ | Hours the employee arrived late to work.                  • Calculation: Time be |
| `early_leave_time` | Float | Early Departure Time |  | ✓ | Hours the employee left work early.                  • Calculation: Time between |
| `early_come_time` | Float | Early Arrival Time |  | ✓ | Hours the employee arrived before scheduled start time.                  • Calcu |
| `overtime` | Float | Overtime Hours |  | ✓ | Additional hours worked beyond the scheduled work time.                  • Calcu |
| `overtime_night` | Float | Night Overtime Hours |  | ✓ | Overtime hours worked during night shift period.                  • Period: Nigh |
| `extra_time` | Float | Extra Time |  | ✓ | Additional work time that doesn't qualify as standard overtime.                  |
| `extra_night` | Float | Extra Night Time |  | ✓ | Extra work time performed during night shift hours.                  • Period: N |
| `shift_number` | Integer | Shift Number |  | ✓ | Identifier for the work shift on this date.                  • Purpose: Distingu |
| `attendance_count` | Char | Attendance Records |  | — | Number of check-in/check-out records for this date.                  • Computati |

#### Notable methods

- **`open_attendance_logs(self)`** — decorators: —
  - touches: `ir.actions.act_window`

### `hr.department` <a id='model-hr-department'></a>
Python class `Department` in `models/hr_department.py:5`.  Model.  Inherits: `hr.department`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ignore_early_come_time` | Float |  |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_late_time` | Float |  |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_early_leave_time` | Float |  |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_overtime` | Float |  |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_extra_time` | Float |  |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:14`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `attendance_extra_ids` | One2many → \`hr.attendance.extra\` |  |  | ✓ | Daily roll-up records computed for this employee by the Recompute Extra Attendan |

#### Notable methods

- **`_total_time(self, time_ranges)`** — decorators: `@api.model`
  - Calculate total time from a list of time ranges.
- **`_intersection_time(self, time_ranges1, time_ranges2)`** — decorators: `@api.model`
  - Find intersections between two lists of time ranges.
- **`update_extra_attendance_data(self, from_datetime, to_datetime=None, overwrite_existing=False)`** — decorators: —
  - Update attendance extra records for employees in date range.
  - effects: `log_error`, `log_info`, `log_warn`, `sudo`
  - touches: `hr.attendance`, `hr.attendance.extra`
- **`get_work_time_details(self, for_date, work_time_ranges, attendance_ranges, day_period=(time(6, 0), time(22, 0)))`** — decorators: `@api.model`
  - Calculate detailed work time metrics for a specific date.
  - effects: `log_debug`

### `hr.legal.rate` <a id='model-hr-legal-rate'></a>
Python class `HrLegalRate` in `models/hr_legal_rate.py:6`.  Model.  Description: *Dated Legal Rate / Coefficient*.  Default order: `code, date_from desc`.

> Dated legal coefficient (labour-law rate or supplement).

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `code` | Char |  | ✓ | ✓ | Stable identifier referenced by the cost calculation, e.g. 'overtime_workday', ' |
| `name` | Char |  |  | ✓ | Human label for this coefficient, shown in the settings list (e.g. 'Overtime — r |
| `date_from` | Date | Valid From | ✓ | ✓ | Date this value takes legal effect. The cost calculation for a worked day uses t |
| `value` | Float |  | ✓ | ✓ | Numeric coefficient. For overtime classes this is a multiplier of the hourly rat |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Leave empty for a national/global rate that applies to every company. Set a comp |
| `currency_id` | Many2one → \`res.currency\` | Currency |  | ✓ | Relevant only for additive amount coefficients (e.g. the night-shift supplement  |

#### Notable methods

- **`_get_rate(self, code, date, company_id=None)`** — decorators: `@api.model`, `@tools.ormcache`
  - Return the coefficient for ``code`` effective on ``date``. Company row
    first, then global - NOT one ordered query, because in PostgreSQL
    `ORDER BY company_id DESC` puts NULL (global) first and a global row would
    shadow a company override. Missing = `0.0` (no premium), never a guessed
    `1.0`.

#### Correcting a rate vs. superseding it

Two operations that look alike and must not be confused:

- **The law changed** -> CREATE a new row with the new `date_from`. The lookup
  takes the latest `date_from` on or before the worked day, so historical
  periods keep their historical coefficient.
- **The stored figure is wrong** -> WRITE on the existing row. This must NOT
  leave a second dated row for the same code: two rows effective on the same
  day make the lookup depend on which one wins. The partial unique indexes stop
  the exact duplicate (`(code, date_from, company_id) WHERE company_id IS NOT
  NULL` and `(code, date_from) WHERE company_id IS NULL` - a plain 3-column
  UNIQUE would NOT stop duplicate GLOBAL rows, because PostgreSQL treats NULL
  as distinct), and `test_legal_rate_edit_tour` asserts the count after an
  inline correction.

`create` / `write` / `unlink` all call `self.env.registry.clear_cache()`,
because the lookup is `ormcache`d on (code, date, company_id).

#### Presentation, and what a test may assert

`value` carries `digits=(16, 4)`, so it renders with four decimals AND with the
decimal mark of the user's language: **1,8500** in Bulgarian, **1.8500** in
English. A customer database typically has only `bg_BG` installed, and a
fixture that writes `admin.lang = 'en_US'` does NOT change that - core
`res.users.context_get` drops a language that is not installed and falls back
to the company's. So a UI test must assert the VALUE, not its rendering:
`:contains(/1[.,]85/)`, scoped to the edited row
(`.o_data_row:has(.o_data_cell[name='code']:contains(zz_tour_rate))`).
- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`unlink(self)`** — decorators: —
  - calls `super() `unlink``

### `resource.calendar` <a id='model-resource-calendar'></a>
Python class `ResourceCalendar` in `models/resource_calendar.py:3`.  Model.  Inherits: `resource.calendar`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `daily_ranges_are_shifts` | Boolean | Daily Ranges Are Shifts |  | ✓ | Treat each daily time range as a separate shift for attendance calculations.     |

### `hr.attendance.extra.wizard` <a id='model-hr-attendance-extra-wizard'></a>
Python class `WizardHrEmployee` in `wizards/hr_attendance_extra_wizard.py:5`.  TransientModel (wizard).  Description: *Wizard for attendance extra calculations*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | Select employees for attendance calculation recalculation.                  • Se |
| `start_date` | Date | Start Date |  | ✓ | Start date for the attendance calculation period.                  • Range: Begi |
| `end_date` | Date | End Date |  | ✓ | End date for the attendance calculation period.                  • Range: Final  |
| `overwrite_existing` | Boolean | Overwrite Existing |  | ✓ | Control how existing attendance calculations are handled.                  • Whe |

#### Notable methods

- **`execute(self)`** — decorators: —
  - touches: `ir.actions.act_window`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestAttendanceLateCommon.setUpClass(cls)`** (`@classmethod`) — `tests/common.py:12`
  - calls `super()`
  - touches: `hr.department`, `hr.employee`, `hr.rfid.zone`, `res.company`, `resource.calendar`
- **`TestAttendanceLateCommon.create_attendance(self, employee, check_in, check_out=None, zone=None)`** — `tests/common.py:131`
  - Helper method to create attendance records
  - touches: `hr.attendance`
- **`TestAttendanceAutoClose.setUpClass(cls)`** (`@classmethod`) — `tests/test_attendance_auto_close.py:15`
  - calls `super()`
- **`TestAttendanceAutoClose.test_auto_close_uses_max_time_not_fixed_duration(self)`** — `tests/test_attendance_auto_close.py:20`
  - Test that auto-close uses max_time_in_zone instead of auto_close_time_for_zone
  - touches: `hr.attendance`, `hr.attendance.extra`
- **`TestAttendanceAutoClose.test_auto_close_within_max_time_uses_current_time(self)`** — `tests/test_attendance_auto_close.py:58`
  - Test that attendance within max_time_in_zone uses current time (not closed)
  - touches: `hr.attendance`, `hr.attendance.extra`
- **`TestAttendanceAutoClose.test_no_extra_record_without_attendance(self)`** — `tests/test_attendance_auto_close.py:94`
  - Test that no hr.attendance.extra is created without real attendance
  - touches: `hr.attendance.extra`
- **`TestAttendanceAutoClose.test_no_extra_record_recreated_after_deletion(self)`** — `tests/test_attendance_auto_close.py:112`
  - Test that deleted invalid records are not recreated
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_01_normal_attendance(self)`** — `tests/test_attendance_calculation.py:14`
  - Test normal attendance calculation
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_02_missing_checkout_current_day(self)`** (`@freeze_time`) — `tests/test_attendance_calculation.py:39`
  - Test attendance with missing check-out on current day.
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_03_missing_checkout_with_zone_autoclose(self)`** — `tests/test_attendance_calculation.py:67`
  - Test attendance with missing check-out exceeding max zone time
  - effects: `create`, `with_context`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_04_late_arrival_within_tolerance(self)`** — `tests/test_attendance_calculation.py:98`
  - Test late arrival within department tolerance
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_05_multi_day_attendance(self)`** — `tests/test_attendance_calculation.py:117`
  - Test attendance spanning multiple days (night shift)
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_06_overtime_calculation(self)`** — `tests/test_attendance_calculation.py:154`
  - Test overtime calculation
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_07_multiple_attendances_same_day(self)`** — `tests/test_attendance_calculation.py:172`
  - Test multiple attendance records on the same day
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestAttendanceCalculation.test_09_attendance_recalculation_on_update(self)`** — `tests/test_attendance_calculation.py:196`
  - Test automatic recalculation when attendance is updated
  - effects: `create`
  - touches: `hr.attendance.extra`
- **`TestHrLegalRate.setUpClass(cls)`** (`@classmethod`) — `tests/test_legal_rate.py:20`
  - calls `super()`
  - touches: `hr.legal.rate`, `res.company`
- **`TestHrLegalRate.test_picks_value_effective_on_date(self)`** — `tests/test_legal_rate.py:33`
  - Latest date_from on or before the queried date wins.
- **`TestHrLegalRate.test_boundary_on_effective_date(self)`** — `tests/test_legal_rate.py:38`
  - date_from is inclusive — the value applies from that day.
- **`TestHrLegalRate.test_company_override_wins_over_global(self)`** — `tests/test_legal_rate.py:43`
  - A company-specific row beats the global one when both are effective.
- **`TestHrLegalRate.test_company_falls_back_to_global(self)`** — `tests/test_legal_rate.py:50`
  - No company row → global value is used.
- **`TestHrLegalRate.test_missing_code_returns_zero(self)`** — `tests/test_legal_rate.py:63`
- **`TestHrLegalRate.test_before_any_effective_date_returns_zero(self)`** — `tests/test_legal_rate.py:66`
- **`TestHrLegalRate.test_cache_invalidated_on_create(self)`** — `tests/test_legal_rate.py:69`
  - ormcache must not serve a stale miss after a new row is added.
- **`TestHrLegalRate.test_cache_invalidated_on_write(self)`** — `tests/test_legal_rate.py:76`
- **`TestHrLegalRate.test_unique_constraint(self)`** — `tests/test_legal_rate.py:82`
  - Same code + date_from + company cannot be duplicated.
- **`TestNoShowDigestKpi.setUpClass(cls)`** (`@classmethod`) — `tests/test_no_show_digest.py:16`
  - calls `super()`
  - touches: `digest.digest`, `hr.employee`
- **`TestNoShowDigestKpi.test_counts_distinct_absent_employees(self)`** — `tests/test_no_show_digest.py:44`
- **`TestNoShowDigestKpi.test_same_employee_counted_once(self)`** — `tests/test_no_show_digest.py:49`
- **`TestNoShowDigestKpi.test_real_attendance_not_counted(self)`** — `tests/test_no_show_digest.py:54`
  - A genuine (non-technical) attendance is not a no-show.
  - touches: `hr.attendance`
- **`TestAttendanceLateTours.setUpClass(cls)`** (`@classmethod`) — `tests/test_tours.py:14`
  - calls `super()`
  - touches: `hr.attendance.extra`, `hr.employee`, `hr.legal.rate`, `res.users`
- **`TestAttendanceLateTours.test_legal_rate_edit_tour(self)`** - `tests/test_tours.py`
  - An HR manager corrects a wrong coefficient in the list, sees the corrected
    value on that rate afterwards, and the correction lands on the rate they
    opened - without leaving a second row for that code.
  - Asserts BOTH halves: `rate.value == 1.85` and
    `search_count([('code', '=', 'zz_tour_rate')]) == 1`.
- **`TestAttendanceLateTours.test_self_leave_review_tour(self)`** — `tests/test_tours.py:54`
  - Process: officer reviews early departures grouped by employee.

### Private helpers

- **`TestNoShowDigestKpi._technical(self, employee, day_offset)`** — `tests/test_no_show_digest.py:26`
  - Mimic core absence detection: 1-second technical attendance.
  - touches: `hr.attendance`
- **`TestNoShowDigestKpi._kpi(self)`** — `tests/test_no_show_digest.py:36`
  - effects: `with_context`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `digest_digest_view_form` | `digest.digest` | — | digest.digest_digest_view_form | `views/digest_views.xml` |
| `hr_attendance_extra_view_form` | `hr.attendance.extra` | — |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_pivot` | `hr.attendance.extra` | — |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_tree` | `hr.attendance.extra` | — |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_search` | `hr.attendance.extra` | — |  | `views/hr_attendance_extra.xml` |
| `view_department_form_extend` | `hr.department` | — | hr.view_department_form | `views/hr_department.xml` |
| `hr_legal_rate_view_list` | `hr.legal.rate` | — |  | `views/hr_legal_rate_views.xml` |
| `hr_legal_rate_view_form` | `hr.legal.rate` | — |  | `views/hr_legal_rate_views.xml` |
| `hr_legal_rate_view_search` | `hr.legal.rate` | — |  | `views/hr_legal_rate_views.xml` |
| `resource_calendar_form_inherit` | `resource.calendar` | — | resource.resource_calendar_form | `views/resource_calendar.xml` |

#### Sample XPath operations

- In `digest_digest_view_form`:
  - `//group[@name='kpi_general'] [after]`

- In `view_department_form_extend`:
  - `//group [after]`

- In `resource_calendar_form_inherit`:
  - `//field[@name='tz'] [after]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `hr_attendance_late.access_hr_attendance_extra` | `hr_attendance_late.model_hr_attendance_extra` | `hr_attendance.group_hr_attendance_manager` | ✓ |  |  | ✓ |

| `hr_attendance_late.access_hr_attendance_extra_wizard` | `hr_attendance_late.model_hr_attendance_extra_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |

| `hr_attendance_late.access_hr_legal_rate_user` | `hr_attendance_late.model_hr_legal_rate` | `hr_attendance.group_hr_attendance_user` | ✓ |  |  |  |

| `hr_attendance_late.access_hr_legal_rate_manager` | `hr_attendance_late.model_hr_legal_rate` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_attendance_late_multi_company`** on `model_hr_attendance_extra` — perms=`R`, groups=`global`, domain=`[
                '|', ('employee_id.company_id', 'in', company_ids),
                ('employee_id.company_id', '=', False),
                ]
            `
- **`ir_rule_hr_legal_rate_multi_company`** on `model_hr_legal_rate` — perms=`R`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `digest.tip`: 5 record(s)


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

### From `gotchas` (12)

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `_compute, @api.model_create_multi, api.model_create_multi`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `integrityerror, models.constraint, validationerror`

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `httpcase, _registry_readonly_enabled = false, readonly_enabled`

#### Gotcha: **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_g
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_group_ids` за implied groups, compute). Старото `groups_id` гърми с `ValueError: Invalid field 'groups_id' in 'res.users'` — често в test setUp при `create({'group_ids': [(4, ref)]})`. Същото важи навсякъде където създаваш/филтрираш users по групи.

Matched tokens: `group_ids, res.users`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `<p>, help=`

#### Gotcha: **Correlation/round-trip ключ между две инстанции трябва да е със същи
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **Correlation/round-trip ключ между две инстанции трябва да е със същия ТИП от двете страни.** Ако модул А праща `local_id = record.number` (Char стринг "PST-00076") в маркер/payload, а модул Б го чете в `fields.Integer` с `int(local_id)` → `ValueError` на първия реален номер. Маскира се ако тестовете подават числов fixture (`42`) вместо реалния формат. **Винаги** тествай correlation с реалния номеров формат (prefix+padding), не с гол integer. При несъответствие — изравни типа (обикновено Char, защото човешкият номер е стринг), не cast-вай.

Matched tokens: `valueerror, fields.integer`

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

#### Gotcha: **Search view: `<group>` без атрибути** — `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** — `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

#### Gotcha: **Form view inline x2many: `default_X: id` НЕ `active_id`** — `active_
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Form view inline x2many: `default_X: id` НЕ `active_id`** — `active_id` е действие-context, не form-context. Често по-чисто е да не подаваш context изобщо — Odoo автоматично попълва inverse FK.

Matched tokens: `active_id`

#### Gotcha: **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай cus
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай custom XML тагове в имейл маркери.** Odoo sanitize-ва всяко съхранено `body_html`/`body` (mail.mail, mail.message), вкл. съдържанието на HTML коментари които приличат на conditional comment (`<!--[...]-->`). Непознат таг като `<payload encoding="base64">` се изтрива (отварящият таг), но оставя висящ `</payload>` → целият XML маркер става unparseable, дори простите тагове (`<auth>`, `<ticket>`) които оцеляват не се четат. **Решения:** (1) tolerant parse — при `ET.ParseError` salvage-вай само нужните прости блокове в синтетичен валиден документ; (2) по-робустно — base64-encode целия маркер в един blob (без вътрешни тагове за sanitize да пипа). **Как се хваща**: `from odoo.tools import html_sanitize; assert '<payload' in html_sanitize(body)` — ще fail-не. Винаги тествай маркер round-trip ПРЕЗ `html_sanitize`, не само build→parse.

Matched tokens: `odoo.tools`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `type="object"`

### From `git_log` (17)

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context
<!-- source: git_log ref: c2b001ba20353637d0a0b6541fa6df7d479636e6 occ: 1 conf: 0.60 -->

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: [IMP][FIX] Optimize batch attendance processing and fix boolean comparis
<!-- source: git_log ref: 510764a4f824e0eb4da212e08fe5021b3b51b5c9 occ: 1 conf: 0.60 -->

Commit `510764a4f8` (2025-10-22): [IMP][FIX] Optimize batch attendance processing and fix boolean comparisons

#### Fix: fix cascade delete
<!-- source: git_log ref: ab5dd522f3ab4818c1e4bcdee4a8797e40bfa634 occ: 1 conf: 0.60 -->

Commit `ab5dd522f3` (2024-10-11): fix cascade delete

#### Fix: fix menus
<!-- source: git_log ref: d564385ec67f86b600dce2269a8b5e7bd3d79f51 occ: 1 conf: 0.60 -->

Commit `d564385ec6` (2024-09-18): fix menus

#### Fix: fix license
<!-- source: git_log ref: 6e49a3ef0cee2364b143dcd71a33030362365dd1 occ: 1 conf: 0.60 -->

Commit `6e49a3ef0c` (2024-09-09): fix license

#### Fix: fix loading employee attendance ranges
<!-- source: git_log ref: 01056ee397f5328a582ab6e9fcaa1b8037253ecc occ: 1 conf: 0.60 -->

Commit `01056ee397` (2024-08-29): fix loading employee attendance ranges

#### Fix: fix multi company
<!-- source: git_log ref: f3638b3316b803a062bef55c2a6a9c87ba7d37a7 occ: 1 conf: 0.60 -->

Commit `f3638b3316` (2024-06-12): fix multi company

#### Fix: fix multi company
<!-- source: git_log ref: a4902ccbea8d8b9feacd9682910187a8db6a5974 occ: 1 conf: 0.60 -->

Commit `a4902ccbea` (2024-06-12): fix multi company

#### Fix: FIX: Safe call for attendance calculations
<!-- source: git_log ref: 5e4379b36a27870423c6386a09c8d6640db4f1e1 occ: 1 conf: 0.60 -->

Commit `5e4379b36a` (2023-12-05): FIX: Safe call for attendance calculations

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M
<!-- source: git_log ref: 3c84986ac48326833d2f41e4de1d121e3c526130 occ: 1 conf: 0.60 -->

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: fix overtime calculation
<!-- source: git_log ref: 669b737cced1ae75a5b84f3024fa06d3c51a591e occ: 1 conf: 0.60 -->

Commit `669b737cce` (2023-06-28): fix overtime calculation

#### Fix: fixes from 14.0
<!-- source: git_log ref: 34628f48538377f472074cb7a07748e76b4bbbc4 occ: 1 conf: 0.60 -->

Commit `34628f4853` (2023-06-23): fixes from 14.0

#### Fix: fixes from 14.0
<!-- source: git_log ref: 679dec5fa47da3f66e559dc178f06f23ed3784ed occ: 1 conf: 0.60 -->

Commit `679dec5fa4` (2023-06-16): fixes from 14.0

#### Fix: small fixes from 14.0
<!-- source: git_log ref: 8f061ea7bc61c242581c00cb95abef7eb4e7f6f8 occ: 1 conf: 0.60 -->

Commit `8f061ea7bc` (2023-06-09): small fixes from 14.0

#### Fix: re-write extra data calcs and fixes in attendance_multi
<!-- source: git_log ref: 0b5798ff91793ad7e7598cd727f837cb56f9dee8 occ: 1 conf: 0.60 -->

Commit `0b5798ff91` (2023-06-06): re-write extra data calcs and fixes in attendance_multi

#### Fix: attendance fix from 14.0
<!-- source: git_log ref: 93171012f20e945f18f619ede5f7840ce35f7427 occ: 1 conf: 0.60 -->

Commit `93171012f2` (2022-06-18): attendance fix from 14.0

#### Fix: fix from 14.0
<!-- source: git_log ref: 8a074b53884675ad0ff284f9880f2c2b29fc3e0e occ: 1 conf: 0.60 -->

Commit `8a074b5388` (2022-05-12): fix from 14.0


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_attendance_late`
- Source digest: `sha256:303b98f12ea9cad9d131646a584c3bf41855bcb139a9b3c26272a01c0fbb341b`
- Generated at: `2026-06-03T07:56:26+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
