---
id: hr_attendance_multi_rfid
title: RFID Attendance
module: hr_attendance_multi_rfid
module_version: 19.0.1.0.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage employee attendance
last_updated: '2026-08-14'
source_digest: sha256:fba71369265be1500bbdcac39b04096b2b03bc6204a695e6fa698151e653a08d
depends:
- hr_rfid
- hr_attendance
entities:
  primary: hr.attendance
  related:
  - hr.employee
  - hr.rfid.event.user
  - hr.rfid.zone
  - hr.attendance.recalc.wizard
  - hr.attendance.recalc.run
  - hr.attendance.recalc.log
keywords:
- attendance
- employee
- event
- manage
- multi
- recalc
- rfid
- user
- wizard
- zone
license: AGPL-3
author: Polimex
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 7
  views: 11
  access_rules: 7
  record_rules: 3
  crons: 2
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:d70a216007d467e90f778f75562ea2f2b6d65b2f2ab424c6bff67cf842e31217
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:0a47a90dd7a8e09f66ab579ccce74cae6dba5a4749ea1ba18eb2dcbfca369b25
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Attendance — `hr_attendance_multi_rfid` v19.0.1.0.0

Manage employee attendance

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_attendance_multi_rfid`
- **Version**: `19.0.1.0.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `hr_attendance`

### README (verbatim)

#### RFID Attendance

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.0.0-green.svg)](https://apps.odoo.com)

Seamless integration between RFID access control and Odoo HR attendance tracking.

##### 🎯 Overview

RFID Attendance bridges the gap between physical access control and time tracking, automatically creating attendance records from RFID door events. It supports multiple check-in/out locations, zone-based attendance, and automatic session closure.

##### ✨ Key Features

###### Attendance Automation
- **Automatic Check-in/out**: Convert RFID events to attendance records
- **Zone-based Tracking**: Different zones for different attendance types
- **Multi-location Support**: Track attendance across multiple sites
- **Flexible Rules**: Configure which doors/zones create attendance

###### Smart Processing
- **Event Filtering**: Ignore rapid consecutive events
- **Session Management**: Automatic session closure after timeout
- **Break Handling**: Support for multiple check-ins/outs per day
- **Overtime Calculation**: Automatic overtime tracking

###### Integration Features
- **Real-time Sync**: Instant attendance from access events
- **Bulk Processing**: Handle high-volume event streams
- **Error Recovery**: Resilient to network/system issues
- **Multi-company**: Separate attendance per company

###### Reporting
- **Attendance Reports**: Standard Odoo attendance reports
- **RFID Event Correlation**: Link attendance to access events
- **Exception Reporting**: Missing check-outs, anomalies
- **Export Capabilities**: Excel, CSV exports

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module installed and configured
- hr_attendance module (Odoo standard)

###### Dependencies
```python
'depends': ['hr_rfid', 'hr_attendance']
```

##### 🛠️ Installation

1. Install the hr_rfid module first (if not already installed)

2. Install this module:
```bash
./odoo-bin -d your_database -i hr_attendance_multi_rfid
```

3. Configure attendance zones in existing RFID setup

##### 🔧 Configuration

###### Zone Configuration

1. **Navigate to**: RFID → Configuration → Zones
2. **Enable Attendance**: Check "Attendance Zone" on relevant zones
3. **Set Type**: Choose attendance behavior:
   - `auto`: Automatic in/out detection
   - `in`: Always check-in
   - `out`: Always check-out
   - `toggle`: Alternate between in/out

###### Door Assignment

1. **Assign Zones to Doors**: RFID → Doors → Edit
2. **Select Zone**: Choose attendance-enabled zone
3. **Save**: Doors in this zone will generate attendance

###### Employee Setup

1. **RFID Cards**: Ensure employees have active RFID cards
2. **Working Hours**: Set employee working schedules
3. **PIN Codes**: Optional PIN for attendance validation

###### System Parameters

Configure in Settings → Technical → System Parameters:

```
#### Minimum time between attendance events (seconds)
hr_attendance_multi_rfid.min_time_between_events: 60

#### Auto check-out after hours
hr_attendance_multi_rfid.auto_checkout_hours: 12

#### Allow multiple check-ins per day
hr_attendance_multi_rfid.allow_multiple_sessions: True
```

##### 📖 Usage

###### Automatic Attendance

1. **Employee enters**: Scans card at entrance
2. **System creates**: Check-in record automatically
3. **Employee exits**: Scans card at exit
4. **System creates**: Check-out record

###### Manual Overrides

Managers can still:
- Edit attendance records
- Add missing entries
- Correct errors
- Override automatic entries

###### Monitoring

1. **Real-time View**: Attendance → Dashboard
2. **Who's Present**: See current on-site employees
3. **Event History**: Track all RFID events
4. **Anomalies**: Review attendance exceptions

##### 🔌 API Extension

###### Custom Event Processing

```python
class CustomAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    def process_rfid_event(self, event):
        # Custom logic before standard processing
        if self.custom_validation(event):
            return super().process_rfid_event(event)
```

###### Zone Handlers

```python
#### Custom zone attendance logic
class CustomZone(models.Model):
    _inherit = 'hr.rfid.zone'
    
    def get_attendance_action(self, employee, last_attendance):
        # Custom logic for check-in/out decision
        return 'check_in' or 'check_out'
```

##### 🐛 Troubleshooting

###### Common Issues

1. **No attendance created**
   - Check zone configuration
   - Verify door has attendance zone
   - Confirm employee has valid card
   - Check system parameters

2. **Duplicate entries**
   - Increase min_time_between_events
   - Check for multiple doors in same zone
   - Review event processing logs

3. **Wrong in/out detection**
   - Verify zone type settings
   - Check last attendance state
   - Review employee schedule

###### Debug Mode

Enable detailed logging:
```python
#### In Odoo config
log_handler = hr_attendance_multi_rfid:DEBUG
```

##### ⚙️ Advanced Features

###### Multi-Zone Attendance

Configure complex scenarios:
- Entry zones (parking → building → office)
- Break areas with different rules
- Restricted zones with no attendance

###### Shift Management

Integration with hr_attendance features:
- Shift planning
- Overtime rules
- Break policies
- Holiday handling

###### Notifications

Set up alerts for:
- Missing check-outs
- Overtime threshold
- Unusual patterns
- System errors

##### 📊 Reports

###### Standard Reports
- Daily attendance summary
- Monthly timesheets
- Overtime analysis
- Late arrival tracking

###### Custom Reports
- RFID event correlation
- Zone utilization
- Access vs attendance comparison
- Exception reports

##### 🤝 Contributing

We welcome contributions! Please:
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

- [Documentation](https://polimex.co/docs/rfid-attendance)
- [Support](https://polimex.co/support)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_attendance_multi_rfid/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_attendance_multi_rfid --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.attendance` <a id='model-hr-attendance'></a>
Python class `HrAttendance` in `models/hr_attendance.py:7`.  Model.  Inherits: `hr.attendance`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `department_id` | Many2one |  |  | ✓ | Employee's department at the time of this attendance record. This field is store |
| `check_in` | Datetime |  |  | ✓ | Date and time when the employee checked in to work. This is automatically record |
| `check_out` | Datetime |  |  | ✓ | Date and time when the employee checked out from work. This is automatically rec |
| `in_zone_id` | Many2one → \`hr.rfid.zone\` |  |  | ✓ | The RFID zone where this attendance session is taking place. Set when checking i |

#### Notable methods

- **`_compute_checkin_zone(self)`** — decorators: `@api.depends`
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`needs_autoclose(self)`** — decorators: —
- **`autoclose_attendance(self, reason)`** — decorators: —
  - effects: `write`
- **`check_for_incomplete_attendances(self)`** — decorators: `@api.model`

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:11`.  Model.  Inherits: `hr.employee`.

#### Notable methods

- **`attendance_action_change_with_date(self, action_date, zone_id=None)`** — decorators: —
  - Check In/Check Out action with support for out-of-order events.
  - effects: `log_warn`, `raise:UserError`, `with_context`
  - touches: `hr.attendance`
- **`recalc_attendance(self, from_date=None, to_date=None)`** — decorators: —
  - Rebuild attendance for this recordset in ONE transaction. Calls
    `_check_recalc_allowed` once (the chokepoint every caller passes through),
    then `_recalc_attendance_one` per employee. Anything larger than a handful
    of people belongs on `hr.attendance.recalc.run` instead.
  - effects: `log_warn`, `with_context`
  - touches: `hr.attendance`, `hr.rfid.event.user`, `hr.rfid.zone`
- **`_recalc_attendance_one(self, from_date, to_date, ctx)`** - decorators: -
  - One employee, the smallest piece that can be committed on its own: the
    period is cleared and replayed as a whole. Asks `_check_recalc_allowed`
    again, because the background job calls this directly and a rebuild may
    have become forbidden while it was queued. Returns
    `{'event_count': N, 'attendance_count': M}` - the numbers the rebuild
    reports per person.
  - touches: `hr.attendance`, `hr.rfid.event.user`
- **`_recalc_attendance_context(self)`** - decorators: `@api.model`
  - Resolves once what counts as an attendance door: `{'zones', 'doors',
    'in_readers', 'out_readers'}`. Passed to every `_recalc_attendance_one` of
    a run so the same searches are not repeated per person.
- **`_recalc_window(self, from_date, to_date)`** - decorators: -
  - The two chosen DAYS as the two naive-UTC MOMENTS bounding them, in the
    employee's own timezone, last day included whole (bound is "before", not
    "up to"). Both the events replayed and the attendance deleted are cut to
    this window, so no day is cleared that is not also replayed.
- **`_recalc_clear_domain(self, period_start, period_end)`** - decorators: -
  - **Extension point.** Which of this person's attendance a rebuild may
    remove. Default: everything the system made in the window, never what a
    person typed in - it asks only for records carrying no reason, or the one
    from `_recalc_manual_attendance_reason`.
- **`_recalc_manual_attendance_reason(self)`** - decorators: -
  - **Extension point.** The reason this system puts on attendance it closed
    itself, read from `res.company.hr_attendance_autoclose_reason` when an
    add-on provides that field. Returns `False` where nothing records the
    reason - a typed-in record then cannot be told from a made one, the whole
    period is cleared, and the loss is logged rather than passed over.

#### Settling a stay nobody could have had

`hr.attendance` (models/hr_attendance.py):

- **`MAX_PLAUSIBLE_STAY_HOURS`** = `24.0` (module constant) - crossing midnight
  is ordinary work; a span longer than one whole day is a badge-out that never
  happened.
- **`stay_is_not_credible(self)`** - true for an OPEN record past its zone's
  limit, and for a CLOSED one whose `check_out - check_in` exceeds
  `MAX_PLAUSIBLE_STAY_HOURS`.
- **`_settled_stay_hours(self)`** - what such a record is credited: the zone's
  `auto_close_time_for_zone`, else its `max_time_in_zone`, else the employee's
  `resource_calendar_id.hours_per_day`; `0.0` when nothing can say, and the
  record is then left alone with a warning.
- **`needs_autoclose(self)`** - kept for callers outside this module: open
  records only.
- **`check_for_incomplete_attendances(self)`** - settles both shapes. The
  over-long ones are found by a raw-SQL span query, NOT by `worked_hours`:
  that field is paid time with the unpaid break already deducted, so it reads
  under a day for a record that spans more than one (measured: 1827 real cases,
  `worked_hours > 24` matched none of them).

Day ownership (hr_attendance_late/models/hr_employee.py): a day's presence is
the records whose `check_in` falls on that day, counted in full. A record that
started earlier no longer contributes to later days.

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidUserEvent` in `models/hr_rfid_event_user.py:6`.  Model.  Inherits: `hr.rfid.event.user`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `in_or_out` | Selection | Attendance |  | ✓ | Indicates whether this RFID event was processed as attendance check-in or check- |
| `no_attendance_reason` | Selection | Why Not Counted |  | ✓ | Why a granted passage changed no attendance: `already_inside`, `not_tracked_here`, `nothing_to_close`, `manual_record`, `superseded`, `direction_unknown` |

#### Notable methods

- **`_mark_attendance(self, direction)`** - this passage IS the check-in / check-out;
  clears `no_attendance_reason` so the two columns cannot contradict each other.
- **`_mark_no_attendance(self, reason)`** - LIVE: records WHY the passage changed
  no attendance, but never over a passage another zone already counted (a door
  can belong to several zones, answered one after another).
- **`_rewrite_no_attendance(self, reason)`** - REBUILD: the same, replacing any
  earlier answer, because a replay is authoritative for its period. Two methods
  rather than one method and a flag: a forgotten flag would have looked like
  nothing at all.
- **`_write_no_attendance(self, reason)`** - the shared write; tolerates the
  empty recordset, so callers need no guard.
- **`button_show_employee_att_events(self)`** — decorators: —
  - effects: `i18n`

Both markers are used by the two machines that turn events into attendance -
`hr.rfid.zone` (live, as people walk through) and
`hr.employee._recalc_attendance_one` (replay) - so the two always tell the
operator the same thing about the same passage.

### `hr.rfid.zone` <a id='model-hr-rfid-zone'></a>
Python class `HrRfidZone` in `models/hr_rfid_zone.py:8`.  Model.  Inherits: `hr.rfid.zone`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `attendance` | Boolean | Attendance |  | ✓ | Enable automatic attendance tracking for this zone. When employees enter this zo |
| `overwrite_check_in` | Boolean | Overwrite check-in |  | ✓ | When enabled, if an employee who is already checked in enters this zone, their c |
| `overwrite_check_out` | Boolean | Overwrite check-out |  | ✓ | When enabled, if an employee who has already checked out leaves this zone, their |
| `max_time_in_zone` | Float | Maximum Hours in Zone |  | ✓ | Maximum hours an employee can stay in the zone before attendance is automaticall |
| `auto_close_time_for_zone` | Float | Auto-close Worked Hours |  | ✓ | When attendance is automatically closed (due to max_time_in_zone), this value wi |
| `delete_attendance_if_late_more_than` | Float | Delete if Late More Than (Hours) |  | ✓ | Automatically delete attendance records if the employee is late by more than thi |

#### Notable methods

- **`person_entered(self, person, event)`** — decorators: —
  - super-split (super `person_entered`): pre=— · post=`with_context`
  - effects: `with_context`
  - touches: `hr.employee`
- **`person_left(self, person, event=None)`** — decorators: —
  - Handle person leaving a zone with improved out-of-order event support.
  - super-split (super `person_left`): pre=— · post=`log_warn`, `with_context`
  - effects: `log_warn`, `with_context`
  - touches: `hr.attendance`, `hr.employee`
- **`attendance_for_current_zone(self)`** — decorators: —
  - effects: `i18n`

### `hr.attendance.recalc.wizard` <a id='model-hr-attendance-recalc-wizard'></a>
Python class `WizardHrRecalcAttendanceEmployee` in `wizards/hr_recalc_attendance_wizard.py:5`.  TransientModel (wizard).  Description: *Wizard for re-create attendance records based on RFID events*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | Select employees whose attendance records will be recalculated from RFID events. |
| `start_date` | Date | Start Date |  | ✓ | Starting date for attendance recalculation. Only attendance records from this da |
| `end_date` | Date | End Date |  | ✓ | Ending date for attendance recalculation. Attendance records will be processed u |

#### Notable methods

- **`execute(self)`** - decorators: -
  - Writes the request down and hands the screen back: asks
    `_check_recalc_allowed` (so a refusal is shown on the screen the operator
    is looking at, not in a report they must go and find), checks the
    scheduled task is switched on, creates one `hr.attendance.recalc.run` and
    triggers it. Returns a `display_notification` whose `next` opens that run.
  - effects: `raise:UserError`, `raise:RedirectWarning`
  - touches: `hr.attendance.recalc.run`
- **`_check_background_worker_available(self)`** - decorators: -
  - Refuses rather than accepting a request nothing will ever pick up: an
    inactive `ir.cron` drops triggers silently
    (`odoo/addons/base/models/ir_cron.py`), so the run would sit queued for
    ever. `RedirectWarning` to the cron form for `base.group_system`, plain
    `UserError` for anybody else.

### `hr.attendance.recalc.run` <a id='model-hr-attendance-recalc-run'></a>
Python class `HrAttendanceRecalcRun` in `models/attendance_recalc_run.py:55`.  Model.  Inherits: `mail.thread`.  Description: *Attendance Rebuild*.  Default order: `create_date desc`.

The permanent half of a rebuild. The wizard is transient and the vacuum removes
it within the hour, which would take the job with it; core splits the same way
(`account.move.send.batch.wizard` transient, `account.move.sending_data`
permanent). Deliberately the same shape as
`hr_rfid_odoo_import/models/import_run.py` - one pattern for long jobs, not two.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  |  | ✓ | Computed from the period (`_compute_name`). |
| `state` | Selection |  | ✓ | ✓ | `queued` / `running` / `done` / `nothing` / `refused` / `failed`. Tracked, indexed. |
| `user_id` | Many2one → \`res.users\` | Started by | ✓ | ✓ | Whose rights the work runs with, and who is notified when it ends. |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | ✓ | The company the work runs for (decides which attendance is cleared). |
| `date_from` | Date | From | ✓ | ✓ | First day rebuilt. |
| `date_to` | Date | To | ✓ | ✓ | Last day rebuilt, included whole. |
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | The list as chosen; changing it mid-run applies from the next person on. |
| `processed_employee_id` | Integer |  |  | ✓ | Resume cursor - the last id finished. Monotone, index-backed. |
| `current_employee_id` | Many2one → \`hr.employee\` | Working on |  | ✓ | Who is being rebuilt right now. |
| `done_count` | Integer | People dealt with |  | ✓ | Everybody got through, INCLUDING no-op and failed people - not "succeeded". |
| `total_count` | Integer | People in total |  | ✓ | Size of the list. |
| `progress` | Integer |  |  | - | `done_count * 100 / total_count`. |
| `log_ids` | One2many → \`hr.attendance.recalc.log\` | What happened |  | ✓ | One line per person. |

#### Notable methods

- **`action_start(self)`** - the "Continue now" button; sets `queued` and wakes the cron.
- **`_cron_process(self)`** - decorators: `@api.model`
  - One pass. Called from a request (the button) it only re-triggers the cron -
    doing the work inside the HTTP request would hit `limit_time_real`. Closes
    stalled runs first and **commits that** before starting a pass, because the
    pass rolls back on failure and would otherwise undo exactly the closures
    that unblock the queue. A pass that raises is caught, rolled back and the
    run ends `failed` - otherwise the oldest run is picked again on every
    wake-up and blocks every later one.
- **`_process_pass(self)`** - takes `try_lock_for_update()` and READS the result
  (an empty return means another worker holds the run), resumes at
  `id > processed_employee_id`, and stops at `PASS_SECONDS` or when
  `ir.cron._commit_progress` reports no time left.
- **`_run_one_employee(self, employee, ctx)`** - asks `_check_recalc_allowed`
  FIRST and on its own, then splits by exception TYPE: `AccessError` is a
  breakdown, `UserError` is the documented refusal. Never by message text -
  that stops working the moment it is translated. The rebuild itself runs in a
  `cr.savepoint()`; a plain `cr.rollback()` here would discard every person
  already committed in the pass.
- **`_outcome_of(result)`** (static) - three outcomes, not two: `done`
  (attendance written), `no_result` (events but nothing written - the period
  was cleared and left empty), `no_events` (nothing to replay).
- **`_finish_reporting_outcome(self)`** - picks the closing state and message;
  `_also_cleared` / `_also_left_alone` / `_also_refused` add the people the
  chosen sentence does not already account for.
- **`_abandon_stalled_runs(self)`** - decorators: `@api.model`
  - Closes runs untouched for `STALLED_MINUTES` and RETURNS them, so the caller
    knows there is something worth committing.
- **`_as_the_operator_would(self)`** - `hr.employee` `with_user(user_id)` +
  `with_company(company_id)`; `None` when the account is archived - except the
  superuser, which is archived by design and is the account every rebuild
  started outside a browser runs under.
- **`_tell_the_operator(self, state, message)`** - `_bus_send('simple_notification')`
  to `user_id`, green only for `done`, sticky for everything else.
- **`_for_the_operator(self)`** - the record in `user_id.lang`; the work runs as
  the scheduler's user, so without it every message reaches the operator in
  somebody else's language.
- **`_gc_recalc_runs(self)`** - decorators: `@api.autovacuum`
  - Deletes finished runs (`FINISHED_STATES`) older than `GC_DAYS`, at most
    `GC_LIMIT` per pass, returning `(count, count == GC_LIMIT)` so the vacuum
    re-queues itself.

### `hr.attendance.recalc.log` <a id='model-hr-attendance-recalc-log'></a>
Python class `HrAttendanceRecalcLog` in `models/attendance_recalc_run.py:668`.  Model.  Description: *Attendance Rebuild Line*.  Default order: `id`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `run_id` | Many2one → \`hr.attendance.recalc.run\` |  | ✓ | ✓ | `ondelete='cascade'`, indexed. |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | `related='run_id.company_id'`, stored - the record rule needs it in SQL. |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | `ondelete='cascade'`. |
| `status` | Selection |  | ✓ | ✓ | `done` / `no_events` / `no_result` / `refused` / `error`. |
| `event_count` | Integer | Door events |  | ✓ | How many events were replayed. |
| `attendance_count` | Integer | Attendance records |  | ✓ | How many records came out of them. |
| `error_message` | Text | Reason |  | ✓ | Kept WHOLE for a refusal - the refusing add-on wrote it for the operator. |


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - tuning and safety parameters.

### `models/attendance_recalc_run.py`

- **`PASS_SECONDS`** = `5.0` - how long one pass may spend rebuilding. A safety
  parameter, not a tuning knob: `limit_time_real_cron` only replaces the limit
  when positive, and overrunning restarts the server rather than failing the job.
- **`STALLED_MINUTES`** = `30` - after this a run is treated as dead and closed.
- **`NAMES_SHOWN`** = `8` - people named in a summary before it switches to a count.
- **`FINISHED_STATES`** = `('done', 'nothing', 'refused', 'failed')` - drives the
  vacuum and the "Continue now" / banner visibility. Anything else is still on
  its way and must never be tidied away.
- **`HrAttendanceRecalcRun.GC_LIMIT`** = `500`, **`GC_DAYS`** = `7` (class
  attributes) - bounded deletion; a year of history in one transaction locks
  the table.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`RFIDAttendanceTests.setUp(self)`** — `tests/test_functional.py:17`
  - calls `super()`
- **`RFIDAttendanceTests.test_functionality(self)`** — `tests/test_functional.py:20`
  - effects: `log_info`

### Private helpers

- **`RFIDAttendanceTests._test_attendance_zone(self)`** — `tests/test_functional.py:25`
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`, `hr.rfid.zone`


## Rebuilding attendance: the background job <a id='recalc-run'></a>

### Why it is a job and not a click

Rebuilding one person means deleting their attendance for a period and
replaying every door event in it; a site has hundreds of people. Inside the
request the operator pressed, that is cut off at `limit_time_real` (120 s by
default), leaving attendance half deleted and never rebuilt. The scheduler
thread is NOT exempt: `limit_time_real_cron` only replaces the limit when it is
positive, and exceeding it **restarts the server** rather than merely stopping
the job. Hence `PASS_SECONDS` - a safety parameter.

One employee is the unit of work because the clear-and-replay is only
consistent as a whole. Each person ends in `_save_progress`, which writes the
resume cursor and calls `ir.cron._commit_progress(processed=1, remaining=N)` -
committing, and telling core how much is left so it reschedules itself instead
of computing zero remaining and calling the job done.

### Refusing a rebuild: `hr.employee._check_recalc_allowed`

The hook is DECLARED in `hr_rfid` (`models/hr_employee.py`), not here, and that
placement is load-bearing: Odoo composes one class per model from every add-on
that extends it, last loaded outermost, and two unrelated add-ons that both
declared the method would be in no fixed order - the one that only allows would
silently cancel the one that refuses. Declared in the module underneath both,
it cannot be cancelled that way.

- An override MUST call `super()` FIRST, or every objection underneath is lost.
- Raise `UserError` with an operator-readable reason to refuse; return to allow.
- It is asked at three points, deliberately: in the wizard (so a refusal lands
  on the screen the operator is looking at), in `_run_one_employee` (so one
  refused person does not stop the rest), and again inside
  `_recalc_attendance_one` (a rebuild may become forbidden while it is queued,
  and every programmatic caller passes through there).

`hr_rfid_odoo_import` is the implementer: attendance carrying the transfer's
external ID cannot be worked out again here, and rebuilding would delete the
record together with the metadata row that identifies it, so the next transfer
would no longer recognise it and would bring it over a second time.

A refusal is NOT a failure and the two are told apart by exception TYPE, never
by message text (which stops working the moment it is translated):
`AccessError` -> `error` line + `failed`; `UserError` -> `refused` line, logged
at INFO with no traceback, reason kept whole and posted through
`plaintext2html` so its paragraphs survive.

### Five outcomes, not two

`done`, `no_events`, `no_result`, `refused`, `error` per person; `done`,
`nothing`, `refused`, `failed` for the run. `no_result` exists because a period
that was cleared and produced no attendance reads as "Rebuilt" under a two-way
status and is never looked at again - the operator finds out at the end of the
month when payroll does not add up.

`done_count` counts everybody got through, including no-ops and failures; the
number actually rebuilt is in the closing message. The label says so ("People
dealt with") rather than the counter being narrowed, because a progress bar
whose numerator counted only successes would sit at 67% for ever on a finished
run.

### Tests

`tests/test_recalc_background.py` (lifecycle, resume, outcomes),
`tests/test_recalc_security.py` (officer vs manager, company isolation),
`hr_rfid/tests/test_recalc_hook.py` (the hook allows by default),
`hr_rfid_odoo_import/tests/test_recalc_guard.py` (the refusal, driven through
the wizard button and through `_cron_process`).


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_attendance_calendar_view` | `hr.attendance` | — |  | `views/hr_attendance.xml` |
| `view_attendance_list_inherit` | `hr.attendance` | — | hr_attendance.view_attendance_tree | `views/hr_attendance.xml` |
| `hr_attendance_view_filter_inherit` | `hr.attendance` | — | hr_attendance.hr_attendance_view_filter | `views/hr_attendance.xml` |
| `rfid_hr_employee_view_search` | `hr.employee` | — | hr.view_employee_filter | `views/hr_employee.xml` |
| `hr_rfid_view_user_ev_form_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_form | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_user_ev_tree_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_zone_form_inherit_hr_attendance_multi_rfid` | `hr.rfid.zone` | — | hr_rfid.hr_rfid_zone_view_form | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_zone_tree_inherit_hr_attendance_multi_rfid` | `hr.rfid.zone` | — | hr_rfid.hr_rfid_zone_view_list | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_user_ev_view_search_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_search | `views/hr_rfid_webstack_views.xml` |
| `hr_attendance_recalc_run_list` | `hr.attendance.recalc.run` | list | | `views/attendance_recalc_run_views.xml` |
| `hr_attendance_recalc_run_form` | `hr.attendance.recalc.run` | form | | `views/attendance_recalc_run_views.xml` |

Plus `hr_attendance_recalc_run_action` and the menu **Attendance -> Attendance
Rebuilds** (`hr_attendance.group_hr_attendance_manager`). The form has no
`create` and no auto-refresh; the header carries **Continue now**
(`action_start`) because a progress bar that never moves reads as a stalled job
and the operator starts a second rebuild. Three banners spell out the endings
that are neither success nor failure (`nothing`, `refused`).

#### Sample XPath operations

- In `view_attendance_list_inherit`:
  - `//field[@name='worked_hours'] [after]`

- In `hr_attendance_view_filter_inherit`:
  - `//group [before]`
  - `//group [inside]`
  - `//group [after]`

- In `rfid_hr_employee_view_search`:
  - `//filter[@name='inactive'] [after]`

- In `hr_rfid_view_user_ev_form_inherit_hr_attendance_multi_rfid`:
  - `//div[hasclass('oe_button_box')] [inside]`
  - `//group [inside]`

- In `hr_rfid_view_user_ev_tree_inherit_hr_attendance_multi_rfid`:
  - `//list [attributes]`
  - `//field[@name='door_id'] [after]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_attendance_recalc_wizard` | `model_hr_attendance_recalc_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |

| `access_hr_attendance_recalc_run_officer` | `model_hr_attendance_recalc_run` | `hr_attendance.group_hr_attendance_officer` | ✓ |  |  |  |

| `access_hr_attendance_recalc_run_manager` | `model_hr_attendance_recalc_run` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_attendance_recalc_log_officer` | `model_hr_attendance_recalc_log` | `hr_attendance.group_hr_attendance_officer` | ✓ |  |  |  |

| `access_hr_attendance_recalc_log_manager` | `model_hr_attendance_recalc_log` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_resource_calendar_hr_attendance_manager` | `resource.model_resource_calendar` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_resource_calendar_attendance_hr_attendance_manager` | `resource.model_resource_calendar_attendance` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

An officer READS rebuilds and their lines and nothing more: they cannot create
the wizard, write a run directly, restart a finished one, edit a line or delete
a run. Asserted in `tests/test_recalc_security.py`, from a restricted user - a
security test that runs as superuser proves nothing, because
`ir.model.access.check` returns True on its first line.

### Record rules (ir.rule)

- **`ir_rule_hr_rfid_card_multi_company`** on `resource.model_resource_calendar` - perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_attendance_recalc_run_multi_company`** on `model_hr_attendance_recalc_run` - groups=`global`, domain=`['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]`
- **`ir_rule_hr_attendance_recalc_log_multi_company`** on `model_hr_attendance_recalc_log` - groups=`global`, same domain; the line carries `company_id` as a STORED related of its run, because a record rule is evaluated in SQL.

The `('company_id', '=', False)` branch is deliberate (same form as
`hr_rfid_leave_block`): a record without a company must stay visible rather
than disappear from everybody.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_attendance_multi_rfid_autoclose_cron`** (HR RFID Multi Attendance: Auto-close incomplete attendances) on `model_hr_attendance`, runs every 1 minutes, active=True
- **`hr_attendance_multi_rfid_recalc_cron`** (HR RFID Multi Attendance: Continue attendance rebuilds) on `model_hr_attendance_recalc_run`, code `model._cron_process()`, runs every 1 days, priority 20, active=True, `noupdate="1"`.
  - The daily interval is a floor, not the cadence: every request for a rebuild
    triggers it (`ir.cron._trigger()`), and each pass that runs out of time
    triggers the next. It ships ACTIVE because an inactive cron drops triggers
    silently, which is why the wizard refuses when it is off.
  - Priority is below the auto-close cron (5, every minute) on purpose: a long
    rebuild must never hold up the job that closes people's open attendance.

### Data records summary

- `ir.cron`: 2 record(s)


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

### From `code_comments` (3)

#### TODO: multiple zone not proccessed!!!
<!-- source: code_comments ref: models/hr_attendance.py:69 occ: 1 conf: 0.50 -->

**TODO** in `models/hr_attendance.py:69`

> multiple zone not proccessed!!!

#### TODO: multiple zone not proccessed!!!
<!-- source: code_comments ref: models/hr_attendance.py:79 occ: 1 conf: 0.50 -->

**TODO** in `models/hr_attendance.py:79`

> multiple zone not proccessed!!!

#### TODO: Need to added .with_context(no_validity_check=True) for attendance man
<!-- source: code_comments ref: models/hr_rfid_zone.py:61 occ: 1 conf: 0.50 -->

**TODO** in `models/hr_rfid_zone.py:61`

> Need to added .with_context(no_validity_check=True) for attendance management!!!

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

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `httpcase`

#### Gotcha: При `ev64` хардуерни събития: хардуерът изпраща follow-up Granted even
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Общи** in odoo19-gotchas.md:

> При `ev64` хардуерни събития: хардуерът изпраща follow-up Granted event след grant — симулирай с `event_code=3`

Matched tokens: `event_code=3`

### From `git_log` (23)

#### Fix: [IMP][FIX] Optimize batch attendance processing and fix boolean comparis
<!-- source: git_log ref: 510764a4f824e0eb4da212e08fe5021b3b51b5c9 occ: 1 conf: 0.60 -->

Commit `510764a4f8` (2025-10-22): [IMP][FIX] Optimize batch attendance processing and fix boolean comparisons

#### Fix: FIX: Bug in relative delta call
<!-- source: git_log ref: 15998e70edb489e995097d9d718b954d71c11e2f occ: 1 conf: 0.60 -->

Commit `15998e70ed` (2023-11-20): FIX: Bug in relative delta call

#### Fix: fixes from 14.0
<!-- source: git_log ref: 679dec5fa47da3f66e559dc178f06f23ed3784ed occ: 1 conf: 0.60 -->

Commit `679dec5fa4` (2023-06-16): fixes from 14.0

#### Fix: re-write extra data calcs and fixes in attendance_multi
<!-- source: git_log ref: 0b5798ff91793ad7e7598cd727f837cb56f9dee8 occ: 1 conf: 0.60 -->

Commit `0b5798ff91` (2023-06-06): re-write extra data calcs and fixes in attendance_multi

#### Fix: Fixes for Toni
<!-- source: git_log ref: f96d2b4fc1b2cfa9606336afc69c06d0eede7390 occ: 1 conf: 0.60 -->

Commit `f96d2b4fc1` (2022-11-15): Fixes for Toni

#### Fix: attendance fix from 14.0
<!-- source: git_log ref: 93171012f20e945f18f619ede5f7840ce35f7427 occ: 1 conf: 0.60 -->

Commit `93171012f2` (2022-06-18): attendance fix from 14.0

#### Fix: Fix from 14.0
<!-- source: git_log ref: 3df14c626d3b05a69d06cb6805d8ce5b2376459d occ: 1 conf: 0.60 -->

Commit `3df14c626d` (2022-06-09): Fix from 14.0

#### Fix: Fix from 14.0
<!-- source: git_log ref: 37f4b63de90821f6bbb150e2e101742cc64ccf2b occ: 1 conf: 0.60 -->

Commit `37f4b63de9` (2022-06-08): Fix from 14.0

#### Fix: [FIX] Calculations work time
<!-- source: git_log ref: 4a0d0731d7915f64eb35dc32a2de4f258bd953e6 occ: 1 conf: 0.60 -->

Commit `4a0d0731d7` (2021-04-09): [FIX] Calculations work time

#### Fix: [FIX] Fixes
<!-- source: git_log ref: 3d695ce265499043c345863ade49aa0b415fa36f occ: 1 conf: 0.60 -->

Commit `3d695ce265` (2021-04-09): [FIX] Fixes

#### Fix: [FIX] auto close with OCA autoclose
<!-- source: git_log ref: 3e7d332314cd7ea65c204fc564d28623c960c6a5 occ: 1 conf: 0.60 -->

Commit `3e7d332314` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: [FIX] auto close with OCA autoclose
<!-- source: git_log ref: d59bb7b2f9fc4e7d201d585263269ac51f610f17 occ: 1 conf: 0.60 -->

Commit `d59bb7b2f9` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: [FIX] auto close with OCA autoclose
<!-- source: git_log ref: e72c49bc8942b0fba557d0afd573e0b82e08778f occ: 1 conf: 0.60 -->

Commit `e72c49bc89` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: zone attendance fix
<!-- source: git_log ref: bcfe7be6ee25014bad67ebe2bf32b298e2edc6c0 occ: 1 conf: 0.60 -->

Commit `bcfe7be6ee` (2021-03-09): zone attendance fix

#### Fix: BG Translation & minor fixes
<!-- source: git_log ref: aeef6b44a0cb38d66ffe58fbb3c90dc0e6ff5e0b occ: 1 conf: 0.60 -->

Commit `aeef6b44a0` (2020-06-25): BG Translation & minor fixes

#### Fix: Zone check in fix
<!-- source: git_log ref: 82567edcf3cc72d5235089f9c1b0b8d201d0b4e2 occ: 1 conf: 0.60 -->

Commit `82567edcf3` (2020-01-28): Zone check in fix

#### Fix: Zone overwrite check_in/out and F0 renaming things fixed
<!-- source: git_log ref: 077d26773147aa81b29f4750b9a6450cbb7e5e78 occ: 1 conf: 0.60 -->

Commit `077d267731` (2020-01-28): Zone overwrite check_in/out and F0 renaming things fixed

#### Fix: Bug fixes (workcode menu doesn't show up??)
<!-- source: git_log ref: 7b254dc48fd140d2ca5feb97a1a882f07d3e1c62 occ: 1 conf: 0.60 -->

Commit `7b254dc48f` (2019-06-24): Bug fixes (workcode menu doesn't show up??)

#### Fix: Bug fixes
<!-- source: git_log ref: b5d4d17ed5f1336ad1a92426e842c4d72360dd8a occ: 1 conf: 0.60 -->

Commit `b5d4d17ed5` (2019-06-06): Bug fixes

#### Fix: Bug fix
<!-- source: git_log ref: 36b57db7f1b9a04c6c4bc7d21077b94242d6e9a3 occ: 1 conf: 0.60 -->

Commit `36b57db7f1` (2019-06-06): Bug fix

#### Fix: hr_attendance_multi_rfid: Implement the theoretical time module into our
<!-- source: git_log ref: 7dae7c9f005a9831c5093447dddb795c5b7e2e73 occ: 1 conf: 0.60 -->

Commit `7dae7c9f00` (2019-06-06): hr_attendance_multi_rfid: Implement the theoretical time module into ours, some bug fixes

#### Fix: hr_rfid and hr_attendance_multi_rfid: Bug fixes
<!-- source: git_log ref: 8003939a6635fe5bec9b8b79d6cb796747b50e25 occ: 1 conf: 0.60 -->

Commit `8003939a66` (2019-05-11): hr_rfid and hr_attendance_multi_rfid: Bug fixes

#### Fix: Fix create methods to use the new "model_create_multi" decorator
<!-- source: git_log ref: 805151030b078022440298acb5676832237cba35 occ: 1 conf: 0.60 -->

Commit `805151030b` (2019-03-22): Fix create methods to use the new "model_create_multi" decorator


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/hr_attendance_multi_rfid`
- Source digest: `sha256:fba71369265be1500bbdcac39b04096b2b03bc6204a695e6fa698151e653a08d`
- Generated at: `2026-04-29T07:30:41+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
