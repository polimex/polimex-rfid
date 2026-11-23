---
id: hr_attendance_multi_rfid
title: RFID Attendance
module: hr_attendance_multi_rfid
module_version: 19.0.1.6.4
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage employee attendance
last_updated: '2026-11-23'
source_digest: sha256:d0b2f8f65eb65fa66fd1efd22e2ad2d8008da99df520a25e5a9dc6fcf07cdc5b
depends:
- hr_rfid
- hr_attendance
entities:
  primary: hr.attendance.recalc.run
  related:
  - hr.attendance.recalc.log
  - hr.attendance
  - hr.employee
  - hr.rfid.event.user
  - hr.rfid.zone
  - res.company
  - res.config.settings
  - resource.calendar
  - hr.attendance.recalc.wizard
keywords:
- attendance
- employee
- event
- log
- manage
- multi
- recalc
- rfid
- run
- user
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 10
  views: 14
  access_rules: 7
  record_rules: 3
  crons: 1
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


# RFID Attendance - `hr_attendance_multi_rfid` v19.0.1.6.4

Manage employee attendance

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_attendance_multi_rfid`
- **Version**: `19.0.1.6.4`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
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
2. **Working Hours**: Set employee working schedules. On a schedule, **Hours
   for a Forgotten Badge** says what a day nobody badged out of is worth for
   the people on it (0 = the schedule's working day)
3. **PIN Codes**: Optional PIN for attendance validation

###### Where the rules live

This module reads no system parameters. What decides how passages become
attendance is on the zone: **Attendance**, **Overwrite check-in** and
**Overwrite check-out**. When a stay counts as a forgotten badge and what is
then recorded is in **Settings → Attendances**: Automatic Check-Out with its
tolerance, and Forgotten Badge right under it; a working schedule can set its
own number of hours for a forgotten day. A forgotten day is never credited
past the end of the schedule the person came in under: late in the morning and
no badge-out is credited to the end of the schedule, not a full day from the
hour they came.

- **Attendance** - passages at this zone's doors make attendance.
- **Overwrite check-in** - off (the usual setting) means a SECOND entry while
  the person is already inside changes nothing: the first entry of the day
  stands. The passage says "Already inside" in Why Not Counted. An entry after
  the limit of the working day is a new day - see "A forgotten badge".
- **Overwrite check-out** - off means an exit with no attendance open changes
  nothing; it says "Nothing open to close".

The tolerances that swallow small deviations (a few minutes late, a few
minutes of overtime) are on the DEPARTMENT, not here - see hr_attendance_late.
They work on amounts of time, not on passages: nothing there ignores a second
badge.

The days to fix by hand are found in **Attendances**: the filter **Forgotten
Badge**, next to core's Automatically Checked-Out, lists every stay the system
closed for a forgotten badge; the list shows the mark in its own column, and
the attendance form under the check-out mode. On **Overwrite check-out**, the
last exit badged within 8 hours of a stay the system recorded moves its
check-out; a check-out a person entered stays as entered.

An attendance says how it began and how it ended: the entry and the exit of a
stay made at a door read **RFID** in the mode fields of the attendance form
(in the list: the optional columns Input Mode (In) and Input Mode (Out)). A check-in or check-out
somebody types over it reads Manual from then on, a stay closed for a
forgotten badge reads Automatic Check-Out, and the kiosk and the systray keep
their own names. A badge shows no browser, address or position, also where
device tracking is on.

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

##### Rebuilding attendance from door events

When attendance for a past period is wrong - an area was only set to count
towards attendance afterwards, a reader was on the wrong side of a door, a
batch of events arrived late - it can be built again from the door events of
that period.

###### How to start one

1. Open the employee list, tick the people concerned and choose **Re-create
   Attendance records**.
2. Give the first and the last day. The last day is included whole, and a day
   ends where midnight passes for the person, not in London.
3. Press **Re-Create**. You are told at once that the work has started and
   taken to the page that shows it.

Only an attendance manager can start a rebuild.

###### What it refreshes

The attendance itself, and the daily figures of EVERY day in the period - the
days with no passage at all included. Those are most days on a real
installation, and nothing else would ever touch them again: there is no
attendance record to save, so no other calculation is triggered. Pressing
Recalculate for a period is therefore enough; there is no second thing to run
afterwards.

###### It runs in the background

A rebuild is not done while you wait. The people are worked through one at a
time, each finished before the next is begun, so a rebuild covering a whole
site is not cut short halfway. You can close the page and carry on working;
come back through **Attendance -> Attendance Rebuilds** at any time.

- The bar does not move by itself. **Continue now** refreshes what you see.
- An interrupted rebuild picks up where it stopped - nobody is done twice.
- A rebuild that has not moved for half an hour is closed by itself, so it
  cannot hold up the ones asked for after it. Everybody it had already done
  keeps their rebuilt attendance; start a new one for the rest.
- If the scheduled task that does the work has been switched off, the rebuild
  is refused on the spot rather than accepted and never done. An administrator
  is offered the task to switch back on; anyone else is told to ask for it.

###### What it does to existing attendance

For each person, the attendance the system made in that period is removed and
the door events of that period are replayed in its place. **What somebody
typed in by hand is left alone** wherever the site records why an attendance
exists. Where nothing records that, a typed-in record cannot be told from a
made one and the whole period is replaced - so on such a site, check that
nothing was entered by hand before rebuilding a period.

**A stay that began before the first day is not counted twice.** Somebody who
came in the evening before and left on the first morning keeps that one stay
as it was: the passages it already accounts for (their exit, and any entry
while they were still inside) are not replayed into a second record. Somebody
still inside when the period starts is settled at their next passage, exactly
as the door would settle them, instead of being left open under the days that
follow. Days before the first day are never changed otherwise.

###### How it ends, and what each ending means

| Result | What it means |
|---|---|
| **Finished** | The attendance of everybody on the list was replayed. |
| **Nothing to rebuild** | Nothing was put back. Either nobody had a door event between those dates - usually because no area is set to count towards attendance, which leaves no doors to read - or the events made no attendance at all, which normally means the doors they came from have no reader set as the way in. Read the message: it says which of the two it was and who it concerns. |
| **Refused** | Their attendance is not for this system to rebuild - see below. |
| **Stopped by a problem** | At least one person could not be rebuilt. Their attendance was put back exactly as it was; everybody else is done. The line for that person says so, and your administrator can see what went wrong. |

Whoever asked for the rebuild is told the result on screen when it ends, and
the same account stays on the rebuild itself. Under **What happened** there is
one line per person: how many door events were read, how much attendance came
out of them, and, where nothing did, why.

Note that **People dealt with** counts everybody the rebuild has got through -
including people who had nothing to rebuild and people it failed on. How many
were actually rebuilt is in the closing message.

###### Attendance that came from somewhere else

Attendance brought into this system by a data transfer is a copy of what the
old system recorded. It cannot be worked out again here, so a rebuild that
would touch it is refused, and the records are left untouched. The refusal
names the people concerned and says what to do instead: run the transfer again
to refresh that data, or choose a period - or a set of people - without it.

A refusal is not a breakdown and nothing is wrong: asking for the same rebuild
again gets the same answer.

###### Old rebuilds

A rebuild is kept for a week after it ends - long enough to answer "what did
yesterday's rebuild do?" while anybody still cares. The attendance itself is
the record; this log is only the receipt of the job that rebuilt it. One still
waiting or under way is never tidied away, however long ago it was asked for.


##### A forgotten badge

Crossing midnight is ordinary work: the evening that runs to 01:00 belongs,
whole, to the evening it started on, and it is counted there and nowhere else.
Counting it on both days used to turn eight hours worked into sixteen.

A stay that runs longer than the working day allows is a different thing - a
badge-out that never happened.

###### One setting, in one place

**Settings -> Attendances -> Automatic Check-Out** decides WHEN: the hours the
person's own schedule says for that day, plus the tolerance beside the switch.
An eight-hour day with four hours of tolerance means a stay is settled once it
passes twelve.

Right under it, **Forgotten badge** decides WHAT is then recorded:

| Setting | What the person gets |
|---|---|
| Credit the scheduled day | Their working day - the unpaid break included, so the day is worth exactly what a normal one is worth - and never past the end of the schedule they came in under. |
| Credit the scheduled day, minus a penalty | The same, less the hours set beside it - for companies that treat a forgotten badge as time off site. |
| Count nothing for that day | No working time at all. The stay is marked as a forgotten badge and the real hours have to be entered by hand - which is the point: the person has to say why they forgot. |

###### Never more than a day badged out of

A forgotten badge-out pays no more than a day the person badged out of when
their schedule ended. Somebody in at 08:00 on an 08:00-17:00 schedule is
credited to 17:00. Somebody in at 09:07 is credited to 17:00 as well, not to
18:07: the hour they were late is not made up by forgetting, and nothing of
the day lies after the schedule. The penalty, where the company takes one,
comes off the day as it ends with the schedule, and the schedule's own
**Hours for a Forgotten Badge** stop there too.

The day is counted from the moment the person came in only where no end of
their schedule lay ahead of them: somebody called in for the evening, after
their schedule had ended, is credited a working day from then instead of
nothing. The same holds on a day off, on a floating schedule (a frame people
may work in, with no hour to be late for) and on a schedule that runs round
the clock.

Somebody in a quarter of an hour before the schedule ends is credited that
quarter of an hour. If they really stayed on, the hours are entered by hand on
the record: it is marked **Forgotten Badge**, so it can be found.

Days settled before this rule keep their check-out; a rebuild of the period
(Re-create Attendance records) settles them again by it.

###### What a forgotten day is worth on one schedule

A working schedule can carry its own number: **Employees -> Configuration ->
Working Schedules**, open the schedule, **Hours for a Forgotten Badge**. It
replaces "the scheduled day" in the setting above for the people on that
schedule, and only for them. A floating schedule of fourteen hours describes
the frame people may work in; with 7:00 here, a day somebody forgot to badge
out of is credited seven hours, while the office on its eight-hour schedule
keeps eight. Left at 0:00, the schedule's working day is credited as before.

The number can only lower what a forgotten day pays: above the schedule's own
day it pays that day, and a negative number is refused. The company setting
still decides whether anything is credited: a penalty comes off the
schedule's number, and "Count nothing for that day" credits nothing whatever
the schedule says. The hours are hours of work: on a schedule with an unpaid
lunch break, a day worth six hours from eight ends at three, and one worth
four and a half ends at half past one. A day is judged by the schedule the
person was on that day, and so is its number - after a move to another
schedule, past days keep the old one's.

Changing the number does not touch days that are already settled; a rebuild
of the period (Re-create Attendance records) credits them again with the number set
now. On a database where forgotten days have not been settled yet, switch
Automatic Check-Out off before updating the module, set the number, and switch
it back on: the scheduled task then settles every waiting day with the new
number.

Nothing is settled at all where Automatic Check-Out is off, or where not even
the person's calendar says how long a working day is: there is nothing to
measure against, and a made-up duration would land in somebody's hours. The
log says so. On a day off, their calendar's ordinary working day stands in.

A record the system settled reads **Automatically Checked-Out**, is marked as
a **Forgotten Badge**, and - where a check-out was already there and had to be
moved - keeps in its chatter what it used to say. A number nobody can explain
is worse than a number somebody changed on purpose.

###### When the person comes in again

The scheduled task settles forgotten stays as it passes, and the next entry
does not wait for it. An entry that finds a stay already past the limit settles
it the same way, and the entry begins a new stay. Tuesday stands on its own,
whatever Monday forgot. Coming back through the door inside the limit changes
nothing: the passage says "Already inside".

The limit and the credit are for the day, not for one stay. Somebody who badged
from eight to twelve, came back at one and forgot is credited until five, so the
day is worth the eight hours it was supposed to hold.

Where nothing is credited (**Count nothing for that day**, or a penalty larger
than what is left of the day), the stay ends where it began, worth no hours and
marked. The real hours are entered on it by hand, as for any forgotten badge.

A rebuild follows the same rule, so the same doors tell the same story whichever
of the two read them. Rebuilding a period also takes apart a stay that ran across
several days under the old behaviour, provided it was not entered or corrected
by hand. An entry whose stay would run into a record typed in by hand gets no
record of its own: the person's record stands, and the passage says so.

###### When an operator enters the real hours

The check-out somebody types is their word on when the person left. The stay
stops reading as a forgotten badge, its hours count in full in the daily figures,
and neither the scheduled task nor a rebuild moves it, however long it is.

###### Overlapping attendance

An operator cannot enter a stay that overlaps another stay of the same person:
the form refuses it with Odoo's own message. An overlap breaks Odoo's overtime
calculation for that whole day, so it is stopped where it is typed. Door
passages are never refused because of this.

Earlier versions kept a second pair of hours on each zone (Maximum Hours in
Zone, Auto-close Worked Hours) that answered the same question with a
different number. They are gone; an upgrade carries what they said onto the
company, so nothing changes for an installation that had them set.

Measured on a live installation: 1827 records ran longer than a day, the
longest 361 days, and each of them lent its whole length to every day it
touched. After settling them, 551 records still cross midnight - those are the
real night shifts, and they were not touched.

##### Which day a stay belongs to

A stay belongs, whole, to the day it began on, as the person lived it: in the
employee's own **Timezone** (employee form, *Settings* tab). In Sofia,
someone who badges in at 00:30 on Tuesday worked Tuesday, and is judged by
Tuesday's schedule - although the database stores that moment with Monday's
date. Night hours, absences, the holiday rate and Form 76 read the day the
same way.

Keep each employee's Timezone and the timezone of their working schedule the
same. Days computed before this rule keep their figures until they are
computed again with **Recompute Extra Attendance**.

##### When the hours of a day look wrong

Every attendance shows the hours worked, the extra hours and the regular hours,
and the regular hours are always the worked hours minus the extra ones.

If a day shows 0 hours worked although the person was in, or regular hours that
are not worked minus extra, an attendance manager can put it right with
**Regenerate overtimes** on the overtime ruleset (**Attendances ->
Configuration -> Overtime Rulesets**, open the ruleset). Know the cost before
pressing it: it works the overtime of every employee on that ruleset out again
from the rules, so every decision already taken on an overtime line in that
period - approved or refused - has to be taken again. The hours of days that
are already right do not change.

How far back it reaches: to the earliest date from which this ruleset applies
to anybody (the first contract version that uses it), for every employee on
the ruleset.

Attendance from before that, typically the history brought over from another
system, is put right by an administrator: run the transfer again (**RFID
System -> Hardware Manager -> Import from Odoo**) with only "Import
attendance" ticked. The transfer touches only the days that are wrong, so the
decisions on the other days stay; days from before a person's first contract
version get their hours worked and no overtime.

##### Why a passage was not counted

A person walks through the door, the access is granted, and the attendance
does not change. That is usually correct - most often the person was already
checked in - but until now the event list simply said "No Info" and there was
no way to tell an ordinary second badge from something set up wrong.

Every granted passage that changes no attendance now says why, in the
**Why Not Counted** column of the User Events list (also a filter section in
the search panel, so the whole list can be narrowed to one reason at a time):

| What it says | What happened |
|---|---|
| Already inside | The person was already checked in, inside the limit of their working day, and this zone keeps the first entry of the day. Ordinary. |
| Not tracked in this zone | The zone follows only certain departments or tags, and this person is not one of them. |
| Nothing open to close | An exit arrived with no attendance open, and this zone does not reopen the previous one. |
| Covered by a manual record | The moment falls inside attendance somebody typed in by hand, which is never overwritten. |
| Replaced by a later entry | A second entry came before any exit, and the zone keeps the later one. |
| Reader direction not set | The reader is neither In nor Out, so the passage cannot be read as an arrival or a departure. Set its direction on the controller. |

An empty column on a passage the system has seen since this was installed
means the passage did count - it is the check-in or the check-out shown in the
Attendance column beside it.

Passages from BEFORE the update carry no reason: nothing was recorded at the
time and it cannot be worked out afterwards. To fill in a past period, rebuild
it (Attendances -> Configuration -> Attendance Rebuilds) - the rebuild writes a
reason on every passage it replays. Keep that in mind when filtering by reason:
the filter shows what has been marked, not the whole history.

Both the live processing and a rebuild fill this in, and they agree: a rebuild
that turns a discarded passage into a real check-out clears the old reason.
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
   - A second badge while the person is already inside creates nothing when
     the zone's "Overwrite check-in" is off - the passage says "Already
     inside" in Why Not Counted. If duplicates DO appear, that switch is on,
     or the entry came after the limit of the working day and began a new one.
   - Check whether the door belongs to more than one attendance zone: each
     zone counting the same door opens its own attendance for the same day.
   - Review the event list, filtered by Why Not Counted.

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

### `hr.attendance.recalc.run` <a id='model-hr-attendance-recalc-run'></a>
Python class `HrAttendanceRecalcRun` in `models/attendance_recalc_run.py:55`.  Model.  Inherits: `mail.thread`.  Description: *Attendance Rebuild*.  Default order: `create_date desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | Short label of this rebuild, built from the period it covers. |
| `state` | Selection | State | ✓ | ✓ | Where this rebuild has got to. It continues on its own; you can close the page. |
| `user_id` | Many2one → \`res.users\` | Started by | ✓ | ✓ | Who asked for the rebuild. The work runs in the background, so this is who gets  |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | ✓ | The company this rebuild was started for. |
| `date_from` | Date | From | ✓ | ✓ | Attendance is rebuilt from this day onwards. |
| `date_to` | Date | To | ✓ | ✓ | Last day the rebuild covers. |
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | The people whose attendance is being rebuilt, as chosen when the rebuild was ask |
| `processed_employee_id` | Integer | Processed Employee |  | ✓ | Where to carry on from. The work is done one person at a time, and this is the l |
| `current_employee_id` | Many2one → \`hr.employee\` | Working on |  | ✓ | The person being rebuilt right now. |
| `done_count` | Integer | People dealt with |  | ✓ | How many of the people on the list the rebuild has got through so far - whether  |
| `total_count` | Integer | People in total |  | ✓ | How many people this rebuild covers. |
| `progress` | Integer | Progress |  | - | How far along the rebuild is. |
| `log_ids` | One2many → \`hr.attendance.recalc.log\` | What happened |  | ✓ | One line per person, with what was rebuilt and what was not. |

#### Notable methods

- **`_compute_name(self)`** - decorators: `@api.depends`
- **`_compute_progress(self)`** - decorators: `@api.depends`
- **`action_start(self)`** - decorators: -
  - Ask for the work to begin. Returns at once.
- **`action_refresh(self)`** - decorators: -
  - Show what the rebuild has got to by now.
- **`_cron_process(self)`** - decorators: `@api.model`
  - One pass of work. Called by the scheduler.
  - effects: `log_error`
  - touches: `hr.attendance.recalc.run`
- **`_abandon_stalled_runs(self)`** - decorators: `@api.model`
  - End rebuilds that stopped being worked on.
  - effects: `log_warn`

### `hr.attendance.recalc.log` <a id='model-hr-attendance-recalc-log'></a>
Python class `HrAttendanceRecalcLog` in `models/attendance_recalc_run.py:718`.  Model.  Description: *Attendance Rebuild Line*.  Default order: `id`.

> What the rebuild did, person by person - kept, not cleaned away.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `run_id` | Many2one → \`hr.attendance.recalc.run\` | Run | ✓ | ✓ | The rebuild this line belongs to. |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company the rebuild was started for. |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | The person this line is about. |
| `status` | Selection | Status | ✓ | ✓ | Rebuilt: their attendance was replayed from the door events. No door events: the |
| `event_count` | Integer | Door events |  | ✓ | How many door events were replayed for this person. |
| `attendance_count` | Integer | Attendance records |  | ✓ | How many attendance records came out of them. |
| `error_message` | Text | Reason |  | ✓ | Why this person's attendance was not rebuilt, and what to do about it. |

### `hr.attendance` <a id='model-hr-attendance'></a>
Python class `HrAttendance` in `models/hr_attendance.py:99`.  Model.  Inherits: `hr.attendance`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `department_id` | Many2one | Department |  | ✓ | Employee's department at the time of this attendance record. This field is store |
| `check_in` | Datetime | Check In |  | ✓ | Date and time when the employee checked in to work. This is automatically record |
| `check_out` | Datetime | Check Out |  | ✓ | Date and time when the employee checked out from work. This is automatically rec |
| `in_zone_id` | Many2one → \`hr.rfid.zone\` | In Zone |  | ✓ | The RFID zone where this attendance session is taking place. Set when checking i |
| `forgotten_badge` | Boolean | Forgotten Badge |  | ✓ | Set by the system when this stay outlasted what the working schedule and the tol |
| `in_mode` | Selection | In Mode |  | ✓ |  |
| `out_mode` | Selection | Out Mode |  | ✓ |  |

#### Notable methods

- **`write(self, vals)`** - decorators: -
  - super-split (super `write`): pre=`with_context` · post=-
  - effects: `with_context`
- **`stay_is_not_credible(self)`** - decorators: -
  - Whether this record is a badge that never happened.
- **`needs_autoclose(self)`** - decorators: -
  - Kept under its old name for callers outside this module.
- **`autoclose_attendance(self)`** - decorators: -
  - Settle a forgotten stay the way the company says to.
  - effects: `message_post`, `with_context`
- **`_cron_auto_check_out(self)`** - decorators: `@api.model`
  - Core's own check-out task, with the rule this module settles by.
  - effects: `with_context`
- **`check_for_incomplete_attendances(self)`** - decorators: `@api.model`
  - Settle every forgotten stay - the open ones and the over-long ones.
  - effects: `log_warn`, `sql`, `sudo`, `with_context`
  - touches: `ir.cron`, `res.company`, `resource.calendar`
- **`_check_validity(self)`** - decorators: `@api.constrains`
  - calls `super() `_check_validity``

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:17`.  Model.  Inherits: `hr.employee`.

#### Notable methods

- **`attendance_action_change_with_date(self, action_date, zone_id=None)`** - decorators: -
  - Check In/Check Out action with support for out-of-order events.
  - effects: `log_warn`, `raise:UserError`, `with_context`
  - touches: `hr.attendance`
- **`_recalc_attendance_context(self)`** - decorators: `@api.model`
  - Resolve, once, what counts as an attendance door.
  - touches: `hr.rfid.zone`
- **`recalc_attendance(self, from_date=None, to_date=None)`** - decorators: -
  - Recalculate attendance records from RFID events.

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidUserEvent` in `models/hr_rfid_event_user.py:5`.  Model.  Inherits: `hr.rfid.event.user`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `in_or_out` | Selection | Attendance |  | ✓ | Indicates whether this RFID event was processed as attendance check-in or check- |
| `no_attendance_reason` | Selection | Why Not Counted |  | ✓ | Filled in when a granted passage did not change the attendance, so the reason is |

#### Notable methods

- **`button_show_employee_att_events(self)`** - decorators: -
  - effects: `i18n`

### `hr.rfid.zone` <a id='model-hr-rfid-zone'></a>
Python class `HrRfidZone` in `models/hr_rfid_zone.py:11`.  Model.  Inherits: `hr.rfid.zone`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `attendance` | Boolean | Attendance |  | ✓ | Enable automatic attendance tracking for this zone. When employees enter this zo |
| `overwrite_check_in` | Boolean | Overwrite check-in |  | ✓ | When enabled, if an employee who is already checked in enters this zone, their c |
| `overwrite_check_out` | Boolean | Overwrite check-out |  | ✓ | When enabled, if an employee who has already checked out leaves this zone, their |

#### Notable methods

- **`person_entered(self, person, event)`** - decorators: -
  - super-split (super `person_entered`): pre=- · post=`with_context`
  - effects: `with_context`
  - touches: `hr.employee`, `hr.rfid.event.user`
- **`person_left(self, person, event=None)`** - decorators: -
  - Handle person leaving a zone with improved out-of-order event support.
  - super-split (super `person_left`): pre=- · post=`log_warn`, `with_context`
  - effects: `log_warn`, `with_context`
  - touches: `hr.attendance`, `hr.employee`, `hr.rfid.event.user`
- **`attendance_for_current_zone(self)`** - decorators: -
  - effects: `i18n`

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:5`.  Model.  Inherits: `res.company`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `forgotten_badge_policy` | Selection | Forgotten Badge | ✓ | ✓ | What to record when somebody forgets to badge out and the system has to settle t |
| `forgotten_badge_penalty_hours` | Float | Penalty |  | ✓ | Hours taken off the scheduled day when a badge is forgotten. Used only with the  |

### `res.config.settings` <a id='model-res-config-settings'></a>
Python class `ResConfigSettings` in `models/res_config_settings.py:5`.  TransientModel (wizard).  Inherits: `res.config.settings`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `forgotten_badge_policy` | Selection | *from company_id.forgotten_badge_policy* |  | - |  |
| `forgotten_badge_penalty_hours` | Float | *from company_id.forgotten_badge_penalty_hours* |  | - |  |

### `resource.calendar` <a id='model-resource-calendar'></a>
Python class `ResourceCalendar` in `models/resource_calendar.py:4`.  Model.  Inherits: `resource.calendar`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `forgotten_badge_hours` | Float | Hours for a Forgotten Badge |  | ✓ | How many hours a day is worth when somebody on this schedule forgets to badge ou |

### `hr.attendance.recalc.wizard` <a id='model-hr-attendance-recalc-wizard'></a>
Python class `WizardHrRecalcAttendanceEmployee` in `wizards/hr_recalc_attendance_wizard.py:6`.  TransientModel (wizard).  Description: *Wizard for re-create attendance records based on RFID events*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | Select employees whose attendance records will be recalculated from RFID events. |
| `start_date` | Date | Start Date |  | ✓ | Starting date for attendance recalculation. Only attendance records from this da |
| `end_date` | Date | End Date |  | ✓ | Ending date for attendance recalculation. Attendance records will be processed u |

#### Notable methods

- **`execute(self)`** - decorators: -
  - Record the request and hand the screen back.
  - touches: `hr.attendance.recalc.run`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/attendance_recalc_run.py`

- **`PASS_SECONDS`** *(scalar)* = `5.0`  - line 39
- **`STALLED_MINUTES`** *(scalar)* = `30`  - line 44
- **`NAMES_SHOWN`** *(scalar)* = `8`  - line 48
- **`FINISHED_STATES`** *(collection)* = `('done', 'nothing', 'refused', 'failed')`  - line 52

### `models/hr_attendance.py`

- **`SETTLING_REFUSED`** *(collection)* = `(UserError, ValueError)`  - line 30
- **`UNPAID_TIME_A_CREDITED_DAY_MAY_SPAN`** *(expression)* = `timedelta(hours=24)`  - line 35
- **`A_SCHEDULE_REACHES_MIDNIGHT_WITHIN`** *(expression)* = `timedelta(minutes=1)`  - line 41

### `models/hr_employee.py`

- **`STILL_OPEN`** *(expression)* = `datetime.max`  - line 14


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`stay_outlasts(start, end, allowed, earlier=0.0)`** - `models/hr_attendance.py:44`
  - Whether a stay from start to end ran past what the person's day allows.
- **`reaches_midnight(moment, midnight)`** - `models/hr_attendance.py:62`
  - Whether a scheduled end is that midnight, as core writes one.
- **`last_scheduled_moment(intervals)`** - `models/hr_attendance.py:71`
  - Where the scheduled work in core's intervals of a day ends.
- **`work_goes_on_until(intervals, moment, breaks=())`** - `models/hr_attendance.py:76`
  - Where the scheduled work that goes straight on from a moment ends.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_attendance_recalc_run_list` | `hr.attendance.recalc.run` | - |  | `views/attendance_recalc_run_views.xml` |
| `hr_attendance_recalc_run_form` | `hr.attendance.recalc.run` | - |  | `views/attendance_recalc_run_views.xml` |
| `hr_attendance_calendar_view` | `hr.attendance` | - |  | `views/hr_attendance.xml` |
| `view_attendance_list_inherit` | `hr.attendance` | - | hr_attendance.view_attendance_tree | `views/hr_attendance.xml` |
| `hr_attendance_view_filter_inherit` | `hr.attendance` | - | hr_attendance.hr_attendance_view_filter | `views/hr_attendance.xml` |
| `hr_attendance_view_form_forgotten_badge` | `hr.attendance` | - | hr_attendance.hr_attendance_view_form | `views/hr_attendance.xml` |
| `rfid_hr_employee_view_search` | `hr.employee` | - | hr.view_employee_filter | `views/hr_employee.xml` |
| `hr_rfid_view_user_ev_form_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_form | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_user_ev_tree_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_zone_form_inherit_hr_attendance_multi_rfid` | `hr.rfid.zone` | - | hr_rfid.hr_rfid_zone_view_form | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_view_zone_tree_inherit_hr_attendance_multi_rfid` | `hr.rfid.zone` | - | hr_rfid.hr_rfid_zone_view_list | `views/hr_rfid_webstack_views.xml` |
| `hr_rfid_user_ev_view_search_inherit_hr_attendance_multi_rfid` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_search | `views/hr_rfid_webstack_views.xml` |
| `res_config_settings_view_form_forgotten_badge` | `res.config.settings` | - | hr_attendance.res_config_settings_view_form | `views/res_config_settings_views.xml` |
| `resource_calendar_form_forgotten_badge` | `resource.calendar` | - | resource.resource_calendar_form | `views/resource_calendar_views.xml` |

#### Sample XPath operations

- In `view_attendance_list_inherit`:
  - `//field[@name='worked_hours'] [after]`

- In `hr_attendance_view_filter_inherit`:
  - `//group [before]`
  - `//filter[@name='auto_check'] [after]`
  - `//group [inside]`
  - `//group [after]`

- In `hr_attendance_view_form_forgotten_badge`:
  - `//field[@name='out_mode'] [after]`
  - `//field[@name='in_ip_address'] [attributes]`
  - `//field[@name='in_browser'] [attributes]`
  - `//field[@name='in_location']/parent::group [attributes]`
  - `//field[@name='out_ip_address'] [attributes]`

- In `rfid_hr_employee_view_search`:
  - `//filter[@name='inactive'] [after]`

- In `hr_rfid_view_user_ev_form_inherit_hr_attendance_multi_rfid`:
  - `//div[hasclass('oe_button_box')] [inside]`
  - `//group [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_attendance_recalc_wizard` | `model_hr_attendance_recalc_wizard` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ |  |

| `access_hr_attendance_recalc_run_officer` | `model_hr_attendance_recalc_run` | `hr_attendance.group_hr_attendance_officer` | ✓ |  |  |  |

| `access_hr_attendance_recalc_run_manager` | `model_hr_attendance_recalc_run` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_attendance_recalc_log_officer` | `model_hr_attendance_recalc_log` | `hr_attendance.group_hr_attendance_officer` | ✓ |  |  |  |

| `access_hr_attendance_recalc_log_manager` | `model_hr_attendance_recalc_log` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_resource_calendar_hr_attendance_manager` | `resource.model_resource_calendar` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_resource_calendar_attendance_hr_attendance_manager` | `resource.model_resource_calendar_attendance` | `hr_attendance.group_hr_attendance_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_attendance_recalc_run_multi_company`** on `model_hr_attendance_recalc_run` - perms=`RWCD`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `
- **`ir_rule_hr_attendance_recalc_log_multi_company`** on `model_hr_attendance_recalc_log` - perms=`RWCD`, groups=`global`, domain=`[
                '|', ('company_id', 'in', company_ids),
                ('company_id', '=', False),
                ]
            `
- **`ir_rule_hr_rfid_card_multi_company`** on `resource.model_resource_calendar` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_attendance_multi_rfid_recalc_cron`** (HR RFID Multi Attendance: Continue attendance rebuilds) on `model_hr_attendance_recalc_run`, runs every 1 days, active=True

### Data records summary

- `hr.attendance`: 3 record(s)
- `ir.actions.act_window`: 3 record(s)
- `hr.rfid.event.user`: 2 record(s)
- `ir.cron`: 1 record(s)
- `hr.rfid.reader`: 1 record(s)
- `res.company`: 1 record(s)
- `hr.rfid.zone`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (2): `static/tests/tours/forgotten_badge_hours_tour.js`, `static/tests/tours/recalc_refresh_tour.js`



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

##### The day is the person's own

Every daily figure of the attendance set - the day a stay is filed under, the
schedule it is judged by, the night hours, an absence, the holiday rate, the
days of Form 76, the days a rebuild clears - reads the day in the employee's
own **Timezone** (employee form, *Settings* tab), through one method:
`hr.employee._local_tz()`.

Why that zone. Core 19 cuts the days of its overtime, and reads the hours a
day is worth, in the employee's own zone (`hr_attendance.py:686`,
`_get_localized_times`, whose version zone is the employee's;
`hr_employee.py:1792`, `_get_expected_attendances`). Odoo 20 removes the zone
of working hours and reads everything in the employee's zone. The only place
core 19 differs is the stored date of an attendance record
(`hr_attendance.py:90`), which goes through `_get_tz()` - the working hours'
zone first. The two agree unless an employee's zone and their schedule's zone
are set differently; check that both say the same.

What it changes for people working in Sofia, two or three hours ahead of UTC:

- a stay begun between midnight and 02:00 (03:00 in summer) belongs to that
  morning, not to the evening before, and is judged by that morning's
  schedule;
- night work (22:00-06:00) is counted by the clock of the day worked, also
  when a winter day is recomputed in summer;
- a day with no badge is an absence only once it is over for the person;
- the eve of a public holiday is not paid at the holiday rate;
- a day the clocks change is 23 or 25 hours long, and its schedule does not
  borrow an hour of the next day.

Daily rows computed before this rule keep their figures until the day is
computed again - **Recompute Extra Attendance** for the period does it.

##### Regenerating overtime keeps the day's figures right

`hr.attendance._update_overtime` is extended so that core's overtime run leaves
every figure of the affected days consistent with core's own formulas:

- Attendance written past the ORM (a transfer inserting with SQL) has no
  `worked_hours`; core's overtime run reads only the times and never fills
  them. Before calling core, the records with a check-out and no worked hours
  get `modified(['check_in', 'check_out'])` - the two fields
  `_compute_worked_hours` depends on, the idiom core uses after its own raw
  updates (l10n_gcc_invoice/models/account_move.py:61).
- After core's run, `expected_hours` (stored, worked minus overtime) is
  marked for recomputation on every attendance of the run. Core does this
  itself only since odoo/odoo 17577a1f9c6 (in 19.0 since 30.03.2026); on an
  older server a day built record by record kept stale regular hours. On a
  newer server it is the same mark twice, which is why the test for this
  shape passes on this tree with or without the module.

Core's **Regenerate overtimes** button on the ruleset
(`action_regenerate_overtimes`) runs this method. It reaches from the earliest
`date_version` of ALL versions that carry the ruleset, for every employee on
it (`hr_attendance_overtime_ruleset.py`, `_attendances_to_regenerate_for`) -
not from each employee's own version. Core deletes and recreates every
overtime line of that period, and a recreated line takes its default status
(`hr_attendance_overtime.py`, `_compute_status`), so approvals and refusals in
the period have to be given again - core's behaviour, not changed here. The
user guide says so before telling anyone to press it. History older than that
is out of the button's reach by core's design; a transfer repairs its own
history when it runs again (hr_rfid_odoo_import, "Worked Hours"), hands core
only the days that are wrong, and gives days before a person's first version
their hours without overtime.

Customer case (12.10.2026): after a transfer more than half of the closed
attendances read 0 hours worked, and about a third had regular hours that
were not worked minus extra.

Tests: `tests/test_regenerate_puts_figures_right.py`
(tag `rfid_attendance_figures`).

##### Rebuilding attendance: the background job

###### Why it is a job and not a click

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

###### Refusing a rebuild: `hr.employee._check_recalc_allowed`

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

###### Five outcomes, not two

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

###### Tests

`tests/test_recalc_background.py` (lifecycle, resume, outcomes),
`tests/test_recalc_security.py` (officer vs manager, company isolation),
`hr_rfid/tests/test_recalc_hook.py` (the hook allows by default),
`hr_rfid_odoo_import/tests/test_recalc_guard.py` (the refusal, driven through
the wizard button and through `_cron_process`).


##### Where the rules live (the technical names)


This module reads no system parameters. What decides how passages become
attendance is on `hr.rfid.zone`: `attendance`, `overwrite_check_in`,
`overwrite_check_out`. When a stay is a forgotten badge and what it is credited
is core's Automatic Check-Out with the company's `forgotten_badge_policy`, and
per schedule `resource.calendar.forgotten_badge_hours`; a forgotten day is
never credited past the end of the schedule the person came in under. The
tolerances for small deviations are on `hr.department` (hr_attendance_late:
`ignore_late_time`, `ignore_early_come_time`, `ignore_early_leave_time`,
`ignore_overtime`, `ignore_extra_time`) and work on AMOUNTS OF TIME, never on
passages.

##### How a person's attendance is rebuilt (`hr.employee`)

- **`recalc_attendance(self, from_date=None, to_date=None)`** - decorators: -
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
  - A stay with `check_in` before the period and `check_out` in it (or none)
    is not cleared, so it is settled ground: passages inside a closed one are
    skipped (an entry is rewritten `already_inside`, its own exit marked
    `out`), and the latest open rfid one is carried on - the replay starts
    with it as the presence and writes its check-out instead of creating a
    second record. A typed-in stay from before the period joins the
    preserved spans like one inside it. Before this, the entry inside such a
    stay and its exit were replayed into an overlapping record, and core's
    overtime engine raised `Expected singleton` (the person came out
    "Not rebuilt").
  - touches: `hr.attendance`, `hr.rfid.event.user`
- **`_recalc_attendance_context(self)`** - decorators: `@api.model`
  - Resolves once what counts as an attendance door: `{'zones', 'doors',
    'in_readers', 'out_readers'}`. Passed to every `_recalc_attendance_one` of
    a run so the same searches are not repeated per person.
- **`_local_tz(self)`** - decorators: -
  - The zone every day of this person is read in: their own `tz`. The one
    place the set asks it; see "The day is the person's own" below.
- **`_local_day(self, moment)`** - decorators: -
  - The date of this person's calendar a naive-UTC moment falls on.
- **`_local_days_window(self, from_date, to_date)`** - decorators: -
  - The chosen DAYS as the two naive-UTC MOMENTS bounding them, in the
    employee's own timezone, last day included whole (bound is "before", not
    "up to"); each end localized on its own, so a day the clocks change is
    23 or 25 hours long. Both the events replayed and the attendance deleted
    are cut to this window, so no day is cleared that is not also replayed;
    the daily figures, the holiday check and Form 76 read their days through
    it too.
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

###### Settling a forgotten badge

One setting, in one place. **When**: core's `res.company.auto_check_out` +
`auto_check_out_tolerance`, measured against the person's own scheduled day.
**What**: `res.company.forgotten_badge_policy` (`credit_schedule` / `penalty`
/ `ignore`) with `forgotten_badge_penalty_hours`, shown right under the core
switch in Settings -> Attendances. **Per schedule**:
`resource.calendar.forgotten_badge_hours` (Float, 0 = unset, CHECK >= 0;
models/resource_calendar.py, on the schedule form beside the hours, under the
schedule's own access rights) replaces the scheduled day in the policy for the
people on that schedule, capped at that day (`min(number, hours)`). The
schedule is the one of the stay's day, chosen as core's
`hr.employee._get_expected_attendances` chooses it
(`hr.attendance._calendar_of_the_day`: contract version in force, else the
person's, else the company's) - not `hr.attendance._get_employee_calendar`,
which Enterprise's `hr_work_entry_attendance` overrides to read `check_out`.
The policy still applies on top (penalty off the number, `ignore` credits
nothing). Settled stays are not re-credited when the number changes; a rebuild
re-credits them.

`hr.attendance` (models/hr_attendance.py):

- **`forgotten_badge`** (Boolean, indexed) - the system judged this stay a
  forgotten badge. Set under every policy, so they can all be found.
- **`_scheduled_day(self)`** - `(hours, span)` for the day of the check-in,
  from core's `hr.employee._get_expected_attendances`, so leaves, public
  holidays and two-week calendars read as they do everywhere else. `(0, 0)`
  on an unscheduled day - no answer, not a small one.
- **`_max_allowed_stay_hours(self)`** - scheduled hours + the company's
  tolerance; `0.0` when Automatic Check-Out is off or the day was not
  scheduled, and then nothing is ever settled.
- **`_end_of_the_schedule_ahead(self)`** - where the schedule the person came
  in under ends, when that still lay ahead of the check-in: the last scheduled
  minute of the stay's day (`_expected_work_on`, core's intervals, own leave
  taken off). A schedule that reaches midnight and goes straight on the next
  morning is one shift (22:00-06:00 ends at 06:00); a check-in after midnight
  while last evening's shift was still running ends with that shift, the same
  morning. `False` when the check-in is after the schedule's end, on an
  unscheduled day and on a floating schedule (core describes a stand-in
  window around noon for it, `resource_calendar.py:419`). On a schedule that
  runs round the clock the end found is a day or more ahead and holds nothing
  back. Module-level helpers: `reaches_midnight` (a row to 24:00 ends at
  23:59:59.999999 in core, and one typed as 23:59 a minute short:
  `A_SCHEDULE_REACHES_MIDNIGHT_WITHIN`), `work_goes_on_until` (a break the
  schedule declares - core's lunch rows, `_breaks_on` - does not end the
  shift), `last_scheduled_moment`. Only the END
  is read by the shift; whether a stay is forgotten at all is still judged
  by the hours of its calendar day (`_max_allowed_stay_hours`).
- **`_settled_check_out(self)`** - when the stay is taken to have ended:
  check-in + the SPAN of the scheduled day (break included, so a settled day
  is worth a normal one), or, after an earlier stay that day, what is left of
  the day's hours (`_hours_earlier_that_day`); never past
  `_end_of_the_schedule_ahead`, so a forgotten badge-out pays no more than a
  day badged out when the schedule ended (owner's decision, 16.11.2026: in at
  09:07 on an 08:00-17:00 day is credited to 17:00, not 18:07) - counted from
  the check-in alone only where no end of the schedule lies ahead; with the schedule's
  `forgotten_badge_hours` set, that number (at most the day's hours) less the
  earlier stays, ended at the first second core's own count reaches it
  (`_end_after_worked_hours`: core's `_get_worked_hours_in_range` on a probe,
  halving a window of `UNPAID_TIME_A_CREDITED_DAY_MAY_SPAN` when check-in plus
  the hours falls short, so an end inside a break moves past it), the number
  capped as well by what the schedule still held at the check-in
  (`_worth_as_core_counts` up to `_end_of_the_schedule_ahead`);
  less the penalty where the policy
  sets one, and never past `_latest_end_of_stay` (the moment judged, or the
  person's next stay, core's absence marks included, because its overtime engine
  refuses a record across one); `False` when nothing is to be credited.
- **`stay_is_not_credible(self)`** - does the stay run past
  `_max_allowed_stay_hours`? An OPEN stay counts the earlier stays of that day,
  as core's check-out rule does. A CLOSED stay with `in_mode='manual'` is an
  operator's word and is never judged. Honours the `attendance_calc_time`
  context, the module's own clock seam. The comparison itself is the
  module-level `stay_outlasts`, which the rebuild also uses for a stay that has
  no record yet.
- **`autoclose_attendance(self)`** - settles one stay and raises on failure.
  With nothing to credit, an open stay ends at its own check-in and a closed one
  only gets the mark. Writes with `no_validity_check`: the credited end stops at
  the next stay.
- **`_settle_before_new_entry(self, moment)`** - the door's wrapper, called by
  `hr.rfid.zone.person_entered`. Past the limit it settles the stay and returns
  True, and the entry begins a new one. Runs with `from_event` (no zone list or
  anti-passback change), in a savepoint. `SETTLING_REFUSED` (data failures only)
  returns False and the passage stays "Already inside"; concurrency errors reach
  Odoo's retry, for which `hr_rfid/controllers/main.py` passes them on. The
  rebuild calls `autoclose_attendance` directly, so a failure lands on the person
  in `_run_one_employee`.
- **`check_for_incomplete_attendances(self)`** - settles both shapes, oldest
  first, committing each record inside the task (`ir.cron._commit_progress`). The
  over-long CLOSED ones are found by a raw-SQL span query, NOT by
  `worked_hours`: that field is paid time with the unpaid break already
  deducted, so it reads under the limit for a record that spans more than it
  (measured: 1827 real cases, `worked_hours > 24` matched none of them). History
  brought over from another system is settled the same way (owner's decision,
  05.11.2026).
- **`_cron_auto_check_out(self)`** - core's scheduled task, running this sweep and
  NOT core's rule (owner's decision, 05.11.2026): core's rule reads no schedule on
  a day off and closes a person at work after the bare tolerance, credits the
  working day plus the tolerance whatever the Forgotten Badge setting says, and
  writes all its records in one unprotected loop.
- **`write`** - closing a stay with a zone calls `person_left` with
  `stay_being_closed`, which keeps only the zone list and anti-passback part, and
  only when no other stay of the person is open in that zone. A person's write of
  the times clears `forgotten_badge`.
- **`_check_validity`** - core's overlap check, skipped under
  `no_validity_check` (door passages, the rebuild, settling). The override repeats
  `@api.constrains`: without it Odoo does not run the check at all.

`hr.employee._recompute_daily_figures(from_date, to_date)` - hook called by
`_recalc_attendance_one` on every path, including the early return when there
were no events. Empty in `hr_attendance_multi_rfid`; `hr_attendance_late`
overrides it and calls `update_extra_attendance_data(..., overwrite_existing=
True)` for the whole period. Without it only the days whose attendance records
changed were refreshed - measured on a customer copy, 82 of 148 daily rows in
one June kept their old figures after a full rebuild, all of them days with
nothing to replay.

Day ownership (hr_attendance_late/models/hr_employee.py): a day's presence is
the records whose `check_in` falls on that day, counted in full. A record that
started earlier no longer contributes to later days. A record the system would
settle is capped at `_settled_check_out()` while measuring, and skipped
entirely under the `ignore` policy.

Migration `19.0.1.5.0/pre-migrate.py` carries the removed zone hours
(`max_time_in_zone`, `auto_close_time_for_zone`,
`delete_attendance_if_late_more_than`) onto the company: Automatic Check-Out
on, tolerance = zone limit - the company calendar's `hours_per_day`. The same
conversion runs in `hr_rfid_odoo_import`
(`core_importer._carry_forgotten_badge_settings`) when zones come from an
older instance.

##### The passage says whether it was counted (`hr.rfid.event.user`)

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
- **`button_show_employee_att_events(self)`** - decorators: -
  - effects: `i18n`

Both markers are used by the two machines that turn events into attendance -
`hr.rfid.zone` (live, as people walk through) and
`hr.employee._recalc_attendance_one` (replay) - so the two always tell the
operator the same thing about the same passage.

##### The rebuild wizard, the run and its lines

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

###### `hr.attendance.recalc.run`
Python class `HrAttendanceRecalcRun` in `models/attendance_recalc_run.py:55`.  Model.  Inherits: `mail.thread`.  Description: *Attendance Rebuild*.  Default order: `create_date desc`.

The permanent half of a rebuild. The wizard is transient and the vacuum removes
it within the hour, which would take the job with it; core splits the same way
(`account.move.send.batch.wizard` transient, `account.move.sending_data`
permanent). Deliberately the same shape as
`hr_rfid_odoo_import/models/import_run.py` - one pattern for long jobs, not two.

###### Fields

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

###### Notable methods

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

###### `hr.attendance.recalc.log`
Python class `HrAttendanceRecalcLog` in `models/attendance_recalc_run.py:668`.  Model.  Description: *Attendance Rebuild Line*.  Default order: `id`.

###### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `run_id` | Many2one → \`hr.attendance.recalc.run\` |  | ✓ | ✓ | `ondelete='cascade'`, indexed. |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | `related='run_id.company_id'`, stored - the record rule needs it in SQL. |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | `ondelete='cascade'`. |
| `status` | Selection |  | ✓ | ✓ | `done` / `no_events` / `no_result` / `refused` / `error`. |
| `event_count` | Integer | Door events |  | ✓ | How many events were replayed. |
| `attendance_count` | Integer | Attendance records |  | ✓ | How many records came out of them. |
| `error_message` | Text | Reason |  | ✓ | Kept WHOLE for a refusal - the refusing add-on wrote it for the operator. |


##### What the constants of the rebuild mean

###### `models/attendance_recalc_run.py`

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


##### Who may see and start rebuilds


An officer READS rebuilds and their lines and nothing more: they cannot create
the wizard, write a run directly, restart a finished one, edit a line or delete
a run. Asserted in `tests/test_recalc_security.py`, from a restricted user - a
security test that runs as superuser proves nothing, because
`ir.model.access.check` returns True on its first line.


##### The scheduled actions


- **`hr_attendance_multi_rfid_autoclose_cron`** (HR RFID Multi Attendance: Auto-close incomplete attendances) on `model_hr_attendance`, runs every 1 minutes, active=True
- **`hr_attendance_multi_rfid_recalc_cron`** (HR RFID Multi Attendance: Continue attendance rebuilds) on `model_hr_attendance_recalc_run`, code `model._cron_process()`, runs every 1 days, priority 20, active=True, `noupdate="1"`.
  - The daily interval is a floor, not the cadence: every request for a rebuild
    triggers it (`ir.cron._trigger()`), and each pass that runs out of time
    triggers the next. It ships ACTIVE because an inactive cron drops triggers
    silently, which is why the wizard refuses when it is off.
  - Priority is below the auto-close cron (5, every minute) on purpose: a long
    rebuild must never hold up the job that closes people's open attendance.


##### The screens of a rebuild

| `hr_attendance_recalc_run_list` | `hr.attendance.recalc.run` | list | | `views/attendance_recalc_run_views.xml` |
| `hr_attendance_recalc_run_form` | `hr.attendance.recalc.run` | form | | `views/attendance_recalc_run_views.xml` |

Plus `hr_attendance_recalc_run_action` and the menu **Attendance -> Attendance
Rebuilds** (`hr_attendance.group_hr_attendance_manager`). The form has no
`create` and no auto-refresh; the header carries **Continue now**
(`action_start`) because a progress bar that never moves reads as a stalled job
and the operator starts a second rebuild. Three banners spell out the endings
that are neither success nor failure (`nothing`, `refused`).

##### The record rules of a rebuild

- **`ir_rule_hr_rfid_card_multi_company`** on `resource.model_resource_calendar` - perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_attendance_recalc_run_multi_company`** on `model_hr_attendance_recalc_run` - groups=`global`, domain=`['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]`
- **`ir_rule_hr_attendance_recalc_log_multi_company`** on `model_hr_attendance_recalc_log` - groups=`global`, same domain; the line carries `company_id` as a STORED related of its run, because a record rule is evaluated in SQL.

The `('company_id', '=', False)` branch is deliberate (same form as
`hr_rfid_leave_block`): a record without a company must stay visible rather
than disappear from everybody.
Entries derived from the module's own code comments and bug-fix commit history.

### From `code_comments` (1)

#### TODO: Need to added .with_context(no_validity_check=True) for ...

**TODO** in `models/hr_rfid_zone.py:47`

> Need to added .with_context(no_validity_check=True) for attendance management!!!

### From `git_log` (23)

#### Fix: [IMP][FIX] Optimize batch attendance processing and fix boolean ...

Commit `510764a4f8` (2025-10-22): [IMP][FIX] Optimize batch attendance processing and fix boolean comparisons

#### Fix: FIX: Bug in relative delta call

Commit `15998e70ed` (2023-11-20): FIX: Bug in relative delta call

#### Fix: fixes from 14.0

Commit `679dec5fa4` (2023-06-16): fixes from 14.0

#### Fix: re-write extra data calcs and fixes in attendance_multi

Commit `0b5798ff91` (2023-06-06): re-write extra data calcs and fixes in attendance_multi

#### Fix: Fixes for Toni

Commit `f96d2b4fc1` (2022-11-15): Fixes for Toni

#### Fix: attendance fix from 14.0

Commit `93171012f2` (2022-06-18): attendance fix from 14.0

#### Fix: Fix from 14.0

Commit `3df14c626d` (2022-06-09): Fix from 14.0

#### Fix: Fix from 14.0

Commit `37f4b63de9` (2022-06-08): Fix from 14.0

#### Fix: [FIX] Calculations work time

Commit `4a0d0731d7` (2021-04-09): [FIX] Calculations work time

#### Fix: [FIX] Fixes

Commit `3d695ce265` (2021-04-09): [FIX] Fixes

#### Fix: [FIX] auto close with OCA autoclose

Commit `3e7d332314` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: [FIX] auto close with OCA autoclose

Commit `d59bb7b2f9` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: [FIX] auto close with OCA autoclose

Commit `e72c49bc89` (2021-03-15): [FIX] auto close with OCA autoclose

#### Fix: zone attendance fix

Commit `bcfe7be6ee` (2021-03-09): zone attendance fix

#### Fix: BG Translation & minor fixes

Commit `aeef6b44a0` (2020-06-25): BG Translation & minor fixes

#### Fix: Zone check in fix

Commit `82567edcf3` (2020-01-28): Zone check in fix

#### Fix: Zone overwrite check_in/out and F0 renaming things fixed

Commit `077d267731` (2020-01-28): Zone overwrite check_in/out and F0 renaming things fixed

#### Fix: Bug fixes (workcode menu doesn't show up??)

Commit `7b254dc48f` (2019-06-24): Bug fixes (workcode menu doesn't show up??)

#### Fix: Bug fixes

Commit `b5d4d17ed5` (2019-06-06): Bug fixes

#### Fix: Bug fix

Commit `36b57db7f1` (2019-06-06): Bug fix

#### Fix: hr_attendance_multi_rfid: Implement the theoretical time module ...

Commit `7dae7c9f00` (2019-06-06): hr_attendance_multi_rfid: Implement the theoretical time module into ours, some bug fixes

#### Fix: hr_rfid and hr_attendance_multi_rfid: Bug fixes

Commit `8003939a66` (2019-05-11): hr_rfid and hr_attendance_multi_rfid: Bug fixes

#### Fix: Fix create methods to use the new "model_create_multi" decorator

Commit `805151030b` (2019-03-22): Fix create methods to use the new "model_create_multi" decorator


## Source provenance <a id='provenance'></a>

- Module: `hr_attendance_multi_rfid`
- Source digest: `sha256:d0b2f8f65eb65fa66fd1efd22e2ad2d8008da99df520a25e5a9dc6fcf07cdc5b`
- Generated at: `2026-11-23T10:09:52+00:00`
- Generator: `polimex_module_knowledge`
