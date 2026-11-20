---
id: hr_attendance_late
title: Late Attendance
module: hr_attendance_late
module_version: 19.0.2.4.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Enhances employee attendance tracking with additional work time calculations
last_updated: '2026-11-20'
source_digest: sha256:5e16fa2bf7ee975beaca74a19001d4bc4fbb1e91ee3f56e016b1cdea19ca46c6
depends:
- hr_attendance
- digest
- hr_attendance_multi_rfid
entities:
  primary: hr.attendance.extra
  related:
  - digest.digest
  - hr.attendance
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
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 8
  views: 10
  access_rules: 5
  record_rules: 4
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


# Late Attendance - `hr_attendance_late` v19.0.2.4.0

Enhances employee attendance tracking with additional work time calculations

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_attendance_late`
- **Version**: `19.0.2.4.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
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
- Set each employee's **Timezone** (employee form, *Settings* tab): every daily figure is read in it. A stay belongs, whole, to the day it began on there; night work (22:00-06:00) is counted by that day's own clock; a day with no badge is an absence only once it is over for the person
- A stay nobody badged out of (marked **Forgotten Badge**) is counted up to the end the company's Forgotten Badge setting credits, never past the end of the schedule; hours the system estimated after a schedule are not overtime until the real check-out is entered

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

##### Legal coefficients (Legal Rates)

**Attendance -> Configuration -> Legal Rates** holds the statutory
coefficients used when attendance is costed: the overtime multipliers (working
day, rest day, public holiday) and the night-shift supplement per hour. An
attendance manager may edit them; they are grouped by code, and each one
carries a **Valid From** date.

**These are normally filled by the localisation module for your country - edit
them only to override.**

Two different things, which must not be confused:

- **The law changed.** Add a NEW row with the new Valid From date. A worked day
  is always costed with the coefficient in force on that day, so past periods
  keep what they were worth and nothing is recalculated behind your back.
- **The figure is simply wrong.** Correct it in place, on the row you already
  have. Do not add a second row for the same code and the same date - correcting
  is not a change in the law, and two rows would only make it unclear which one
  applies.

A coefficient is a multiplier of the hourly rate (1.5 = 150%, that is +50%).
The night supplement is not a multiplier but an amount per hour, in the
currency named on the row. It is shown to four decimal places, in the number
format of your language - 1,85 or 1.85 for the same figure.

A row without a company is the national one and applies everywhere; give it a
company only to override that company's figure. If nothing is configured for a
code, the cost calculation reads it as no premium at all rather than guessing.

##### 📊 Reports

###### Who sees the daily figures

The daily figures (**Attendances -> Reporting**, with the list of people who
left early) are read with the attendance rights of the person:

- **Officer: Manage attendances** - the days of the employees they are the
  attendance approver of (employee form, *Settings* tab, *Approvers* -
  *Attendance*);
- **Officer: Manage all attendances** and **Administrator** - every employee;
- the figures are the system's own: only the administrator deletes them, and
  nobody edits them by hand.

###### Which day a figure belongs to

Every daily row is the day as the employee lived it, in their own
**Timezone** (employee form, *Settings* tab). A stay belongs, whole, to the
day it began on there: in Sofia, a stay begun at 00:30 on Tuesday is
Tuesday's, measured against Tuesday's schedule, although the database
stores that moment with Monday's date. Night work (22:00-06:00) is counted
by the clock of the day worked, also when a winter day is recomputed in
summer, and a day with no badge becomes an absence only once it is over
for the person.

Rows computed before this rule keep their figures until their day is
computed again (**Recompute Extra Attendance** for those days).

###### A day nobody badged out of

A stay the system had to close by itself (marked **Forgotten Badge**) is
counted only up to the end the company's Forgotten Badge setting credits, and
that is never past the end of the schedule the person came in under. The
lateness of that morning stays on the row. Somebody in at 09:07 on an
08:00-17:00 schedule who never badged out is late by 1:07, worked 6:53 and
has no overtime. Where the person came in after their schedule had ended - in
for the evening - every credited hour is the system's estimate, and none of
it is overtime: nobody is paid a premium for an estimate. Once somebody
enters the real check-out on the attendance record, the day is measured by
it, overtime included. Other stays of the same day, badged in and out, keep
their overtime. A stay measured before the scheduled task has closed it reads
the same way.

Rows computed before this rule keep their figures until their day is computed
again (**Recompute Extra Attendance** for those days).

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
   - Verify the employee's **Timezone** (Settings tab): it decides which day a stay belongs to
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
| `kpi_hr_rfid_att_early_come_value` | Integer | Kpi Hr Rfid Att Early Come Value |  | - | Live count of employees who checked in before their schedule start during the di |
| `kpi_hr_rfid_att_late_value` | Integer | Kpi Hr Rfid Att Late Value |  | - | Live count of employees who checked in after their schedule start during the dig |
| `kpi_hr_rfid_att_leave_value` | Integer | Kpi Hr Rfid Att Leave Value |  | - | Live count of employees who checked out before their schedule end during the dig |
| `kpi_hr_rfid_att_overtime_value` | Integer | Kpi Hr Rfid Att Overtime Value |  | - | Live count of employees with recorded overtime during the digest window. |
| `kpi_hr_rfid_att_extra_value` | Integer | Kpi Hr Rfid Att Extra Value |  | - | Live count of employees with extra unrecorded time during the digest window. |
| `kpi_hr_rfid_att_no_show_value` | Integer | Kpi Hr Rfid Att No Show Value |  | - | Live count of scheduled employees with no attendance (no-show) during the digest |

### `hr.attendance` <a id='model-hr-attendance'></a>
Python class `HrAttendance` in `models/hr_attendance.py:6`.  Model.  Inherits: `hr.attendance`.

#### Notable methods

- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self)`** - decorators: -
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
| `first_in` | Float | First In |  | ✓ | Time of the first badge-in for the day, in the employee's local time.          • |
| `last_out` | Float | Last Out |  | ✓ | Time of the last badge-out for the day, in the employee's local time.          • |
| `overtime` | Float | Overtime Hours |  | ✓ | Additional hours worked beyond the scheduled work time.                  • Calcu |
| `overtime_night` | Float | Night Overtime Hours |  | ✓ | Overtime hours worked during night shift period.                  • Period: Nigh |
| `extra_time` | Float | Extra Time |  | ✓ | Additional work time that doesn't qualify as standard overtime.                  |
| `extra_night` | Float | Extra Night Time |  | ✓ | Extra work time performed during night shift hours.                  • Period: N |
| `shift_number` | Integer | Shift Number |  | ✓ | Identifier for the work shift on this date.                  • Purpose: Distingu |
| `attendance_count` | Char | Attendance Records |  | - | Number of check-in/check-out records for this date.                  • Computati |

#### Notable methods

- **`open_attendance_logs(self)`** - decorators: -
  - touches: `ir.actions.act_window`

### `hr.department` <a id='model-hr-department'></a>
Python class `Department` in `models/hr_department.py:5`.  Model.  Inherits: `hr.department`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ignore_early_come_time` | Float | Ignore Early Come Time |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_late_time` | Float | Ignore Late Time |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_early_leave_time` | Float | Ignore Early Leave Time |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_overtime` | Float | Ignore Overtime |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |
| `ignore_extra_time` | Float | Ignore Extra Time |  | ✓ | Times smaller than this will be ignored in the calculations on a daily basis. |

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:10`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `attendance_extra_ids` | One2many → \`hr.attendance.extra\` | Attendance Extra |  | ✓ | Daily roll-up records computed for this employee by the Recompute Extra Attendan |

#### Notable methods

- **`_total_time(self, time_ranges)`** - decorators: `@api.model`
  - Calculate total time from a list of time ranges.
- **`_intersection_time(self, time_ranges1, time_ranges2)`** - decorators: `@api.model`
  - Find intersections between two lists of time ranges.
- **`update_extra_attendance_data(self, from_datetime, to_datetime=None, overwrite_existing=False)`** - decorators: -
  - Update attendance extra records for employees in date range.
  - effects: `log_error`, `log_info`, `log_warn`, `sudo`
  - touches: `hr.attendance`, `hr.attendance.extra`
- **`get_work_time_details(self, for_date, work_time_ranges, attendance_ranges, day_period=(time(6, 0), time(22, 0)), owed_ranges=None, overtime_ranges=None)`** - decorators: `@api.model`
  - Calculate detailed work time metrics for a specific date.
  - effects: `log_debug`

### `hr.legal.rate` <a id='model-hr-legal-rate'></a>
Python class `HrLegalRate` in `models/hr_legal_rate.py:6`.  Model.  Description: *Dated Legal Rate / Coefficient*.  Default order: `code, date_from desc`.

> Dated legal coefficient (labour-law rate or supplement).

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `code` | Char | Code | ✓ | ✓ | Stable identifier referenced by the cost calculation, e.g. 'overtime_workday', ' |
| `name` | Char | Name |  | ✓ | Human label for this coefficient, shown in the settings list (e.g. 'Overtime — r |
| `date_from` | Date | Valid From | ✓ | ✓ | Date this value takes legal effect. The cost calculation for a worked day uses t |
| `value` | Float | Value | ✓ | ✓ | Numeric coefficient. For overtime classes this is a multiplier of the hourly rat |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Leave empty for a national/global rate that applies to every company. Set a comp |
| `currency_id` | Many2one → \`res.currency\` | Currency |  | ✓ | Relevant only for additive amount coefficients (e.g. the night-shift supplement  |

#### Notable methods

- **`_get_rate(self, code, date, company_id=None)`** - decorators: `@api.model`, `@tools.ormcache`
  - Return the coefficient for ``code`` effective on ``date``.
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self)`** - decorators: -
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

- **`execute(self)`** - decorators: -
  - touches: `ir.actions.act_window`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `digest_digest_view_form` | `digest.digest` | - | digest.digest_digest_view_form | `views/digest_views.xml` |
| `hr_attendance_extra_view_form` | `hr.attendance.extra` | - |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_pivot` | `hr.attendance.extra` | - |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_tree` | `hr.attendance.extra` | - |  | `views/hr_attendance_extra.xml` |
| `hr_attendance_extra_view_search` | `hr.attendance.extra` | - |  | `views/hr_attendance_extra.xml` |
| `view_department_form_extend` | `hr.department` | - | hr.view_department_form | `views/hr_department.xml` |
| `hr_legal_rate_view_list` | `hr.legal.rate` | - |  | `views/hr_legal_rate_views.xml` |
| `hr_legal_rate_view_form` | `hr.legal.rate` | - |  | `views/hr_legal_rate_views.xml` |
| `hr_legal_rate_view_search` | `hr.legal.rate` | - |  | `views/hr_legal_rate_views.xml` |
| `resource_calendar_form_inherit` | `resource.calendar` | - | resource.resource_calendar_form | `views/resource_calendar.xml` |

#### Sample XPath operations

- In `digest_digest_view_form`:
  - `//group[@name='kpi_general'] [after]`

- In `view_department_form_extend`:
  - `//group [after]`

- In `resource_calendar_form_inherit`:
  - `//field[@name='tz'] [after]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `hr_attendance_late.access_hr_attendance_extra` | `hr_attendance_late.model_hr_attendance_extra` | `hr_attendance.group_hr_attendance_manager` | ✓ |  |  | ✓ |

| `hr_attendance_late.access_hr_attendance_extra_wizard` | `hr_attendance_late.model_hr_attendance_extra_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |

| `hr_attendance_late.access_hr_legal_rate_user` | `hr_attendance_late.model_hr_legal_rate` | `hr_attendance.group_hr_attendance_user` | ✓ |  |  |  |

| `hr_attendance_late.access_hr_legal_rate_manager` | `hr_attendance_late.model_hr_legal_rate` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `hr_attendance_late.access_hr_attendance_extra_officer` | `hr_attendance_late.model_hr_attendance_extra` | `hr_attendance.group_hr_attendance_officer` | ✓ |  |  |  |


### Record rules (ir.rule)

- **`hr_attendance_extra_rule_officer_of_all`** on `model_hr_attendance_extra` - perms=`RWCD`, groups=`hr_attendance.group_hr_attendance_user`, domain=`[(1, '=', 1)]`
- **`hr_attendance_extra_rule_officer`** on `model_hr_attendance_extra` - perms=`RWCD`, groups=`hr_attendance.group_hr_attendance_officer`, domain=`[('employee_id.attendance_manager_id', '=', user.id)]`
- **`ir_rule_hr_attendance_late_multi_company`** on `model_hr_attendance_extra` - perms=`R`, groups=`global`, domain=`[
                '|', ('employee_id.company_id', 'in', company_ids),
                ('employee_id.company_id', '=', False),
                ]
            `
- **`ir_rule_hr_legal_rate_multi_company`** on `model_hr_legal_rate` - perms=`RWCD`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `ir.actions.act_window`: 7 record(s)
- `hr.attendance`: 6 record(s)
- `digest.tip`: 5 record(s)
- `hr.legal.rate`: 4 record(s)
- `hr.department`: 1 record(s)
- `resource.calendar`: 1 record(s)
- `digest.digest`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (3): `static/tests/tours/extra_period_tour.js`, `static/tests/tours/legal_rate_tour.js`, `static/tests/tours/self_leave_tour.js`



## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>

### Curated (docs/faq.md)

##### The legal rates (`hr.legal.rate`)

`_get_rate(code, date, company_id=None)`:
Returns the coefficient for ``code`` effective on ``date``. Company row
first, then global - NOT one ordered query, because in PostgreSQL
`ORDER BY company_id DESC` puts NULL (global) first and a global row would
shadow a company override. Missing = `0.0` (no premium), never a guessed
`1.0`.


###### Correcting a rate vs. superseding it

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

###### Presentation, and what a test may assert

`value` carries `digits=(16, 4)`, so it renders with four decimals AND with the
decimal mark of the user's language: **1,8500** in Bulgarian, **1.8500** in
English. A customer database typically has only `bg_BG` installed, and a
fixture that writes `admin.lang = 'en_US'` does NOT change that - core
`res.users.context_get` drops a language that is not installed and falls back
to the company's. So a UI test must assert the VALUE, not its rendering:
`:contains(/1[.,]85/)`, scoped to the edited row
(`.o_data_row:has(.o_data_cell[name='code']:contains(zz_tour_rate))`).

The tour `test_legal_rate_edit_tour` (`tests/test_tours.py`): an HR manager
corrects a wrong coefficient in the list, sees the corrected value on that rate
afterwards, and the correction lands on the rate they opened - without leaving
a second row for that code. It asserts both halves: `rate.value == 1.85` and
`search_count([('code', '=', 'zz_tour_rate')]) == 1`.
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (18)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: [IMP][FIX] Optimize batch attendance processing and fix boolean ...

Commit `510764a4f8` (2025-10-22): [IMP][FIX] Optimize batch attendance processing and fix boolean comparisons

#### Fix: fix cascade delete

Commit `ab5dd522f3` (2024-10-11): fix cascade delete

#### Fix: fix menus

Commit `d564385ec6` (2024-09-18): fix menus

#### Fix: fix license

Commit `6e49a3ef0c` (2024-09-09): fix license

#### Fix: fix loading employee attendance ranges

Commit `01056ee397` (2024-08-29): fix loading employee attendance ranges

#### Fix: fix multi company

Commit `f3638b3316` (2024-06-12): fix multi company

#### Fix: fix multi company

Commit `a4902ccbea` (2024-06-12): fix multi company

#### Fix: FIX: Safe call for attendance calculations

Commit `5e4379b36a` (2023-12-05): FIX: Safe call for attendance calculations

#### Fix: v2.1 Added portal functionality, barcode generation and RFID ...

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: fix overtime calculation

Commit `669b737cce` (2023-06-28): fix overtime calculation

#### Fix: fixes from 14.0

Commit `34628f4853` (2023-06-23): fixes from 14.0

#### Fix: fixes from 14.0

Commit `679dec5fa4` (2023-06-16): fixes from 14.0

#### Fix: small fixes from 14.0

Commit `8f061ea7bc` (2023-06-09): small fixes from 14.0

#### Fix: re-write extra data calcs and fixes in attendance_multi

Commit `0b5798ff91` (2023-06-06): re-write extra data calcs and fixes in attendance_multi

#### Fix: attendance fix from 14.0

Commit `93171012f2` (2022-06-18): attendance fix from 14.0

#### Fix: fix from 14.0

Commit `8a074b5388` (2022-05-12): fix from 14.0


## Source provenance <a id='provenance'></a>

- Module: `hr_attendance_late`
- Source digest: `sha256:5e16fa2bf7ee975beaca74a19001d4bc4fbb1e91ee3f56e016b1cdea19ca46c6`
- Generated at: `2026-11-20T09:56:52+00:00`
- Generator: `polimex_module_knowledge`
