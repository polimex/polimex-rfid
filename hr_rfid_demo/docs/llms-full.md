---
id: hr_rfid_demo
title: RFID Demo Data
module: hr_rfid_demo
module_version: 19.0.1.0.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: 'A demo company that keeps working: passages, attendance, lateness and overtime for the RFID
  set, day after day'
last_updated: '2026-11-13'
source_digest: sha256:3c6bd1174600ebc018021bae161a2068a56b29e82df7d29a2e4218cbed217d76
depends:
- hr_rfid
- hr_attendance_multi_rfid
- hr_attendance_late
- hr_attendace_rfid_hr_hourly_cost
entities:
  primary: hr.rfid.demo
  related:
  - hr.employee
keywords:
- after
- attendance
- company
- demo
- employee
- keeps
- lateness
- overtime
- passages
- rfid
- that
- working
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: false
auto_install: false
counts:
  models: 2
  views: 0
  access_rules: 0
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


# RFID Demo Data - `hr_rfid_demo` v19.0.1.0.0

A demo company that keeps working: passages, attendance, lateness and overtime for the RFID set, day after day

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_demo`
- **Version**: `19.0.1.0.0`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `hr_attendance_multi_rfid`, `hr_attendance_late`, `hr_attendace_rfid_hr_hourly_cost`

### README (verbatim)

==============
RFID Demo Data
==============

Overview
========

A demo company whose doors keep being used. Installed on a demo database, it
walks the demo staff through the demo doors for the six weeks before today and
then, every quarter of an hour, for whatever has happened since. Attendance,
lateness, early arrivals and departures, overtime and night work, the access
and security dashboards and the environment readings all come out of those
passages - through the same entry a real access-control module reports to.

It never works on a database with real hardware. One module that is not the
demo one, or the demo one having been reached by a real device, and the demo
writes nothing at all.

Configuration
=============

Nothing to configure. Install it on a database with demo data. It uses the
demo hardware of RFID Access Control's demo data and the employees of the
Employees demo; without them it does nothing.

The scheduled task "RFID Demo: simulate the passages since the last run" runs
every 15 minutes. Switch it off to freeze the demo where it is.

Usage
=====

Open Attendances, the Dashboards or RFID Access Control on the demo database:

* about six weeks of attendance made from door passages, today included;
* people who come late, early, leave early, stay on, work nights and some
  Saturdays, and a few who forget to badge out or do not come in;
* refused cards, a visitor, doors held open or forced, exit buttons and the
  Monday power-up of the controllers;
* the server-room sensor reporting every two hours;
* an hourly cost for each person of the demo, for the labour cost figures.

A person on approved leave does not come in that day, and a day somebody
already has attendance entered by hand is left to them.

Technical
=========

* ``hr.rfid.demo._demo_simulate_until(until)`` - draws every passage between
  the last run (``ir.config_parameter`` ``hr_rfid_demo.simulated_until``) and
  ``until``, in time order, and hands each to
  ``hr.rfid.webstack._hw_parse_event`` with ``ws_skip_piggyback`` (the
  websocket path's seam: queued commands are not answered per event).
* Each person's day is drawn from a seed of the person and the date, so a day
  comes out the same whichever run reaches it first. The working day comes
  from the person's own schedule.
* ``hr.rfid.demo._demo_hardware()`` - the guard: the demo module
  (``hr_rfid.demo_module``) when it is the only module and was never reached
  by a device; otherwise nothing.

Credits
=======

Authors
-------

* Polimex Dev Team

Maintainers
-----------

This module is maintained by Polimex Holding Ltd. - https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_demo --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.demo` <a id='model-hr-rfid-demo'></a>
Python class `HrRfidDemo` in `models/hr_rfid_demo.py:71`.  AbstractModel.  Description: *RFID demo simulation*.

#### Notable methods

- **`_demo_backfill(self)`** - decorators: `@api.model`
  - At install: the weeks before today, so the demo has a history.
- **`_cron_simulate(self)`** - decorators: `@api.model`
  - The scheduled task: everything that happened since the last run.
- **`_demo_hardware(self)`** - decorators: `@api.model`
  - The demo module, or nothing when the database has real hardware.
  - effects: `with_context`
  - touches: `hr.rfid.webstack`
- **`_demo_simulate_until(self, until)`** - decorators: `@api.model`
  - effects: `log_info`
  - touches: `ir.config_parameter`
- **`_demo_environment_readings(self, since, until)`** - decorators: `@api.model`
  - The server-room sensor of the demo reports every two hours.
  - effects: `sudo`
- **`_demo_hourly_costs(self)`** - decorators: `@api.model`
  - The demo people get an hourly cost, so the labour cost has figures.
  - effects: `sudo`
  - touches: `hr.attendance.extra`, `hr.employee`
- **`_demo_report(self, webstack, ctrl, reader, card, moment, event_n)`** - decorators: `@api.model`
  - One report of the demo module, as the device sends it.
  - effects: `with_context`
- **`_demo_passages(self, since, until)`** - decorators: `@api.model`
  - Every passage of the window, in the order the doors saw them.
  - effects: `sudo`
  - touches: `hr.attendance`
- **`_demo_people(self)`** - decorators: `@api.model`
  - (employee, card, 'day' | 'night' | 'saturday') for who has a badge.
  - touches: `hr.rfid.card`
- **`_demo_day(self, employee, kind, day, entrance, inner)`** - decorators: `@api.model`
  - The passages of one person on one day: (utc moment, ctrl, reader, code).
- **`_demo_day_extras(self, day, entrance, inner, people)`** - decorators: `@api.model`
  - What the doors see besides people at work: refusals, a visitor, alarms.

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_rfid_demo.py:412`.  Model.  Inherits: `hr.employee`.


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_rfid_demo.py`

- **`BACKFILL_DAYS`** *(scalar)* = `45`  - line 26
- **`SIMULATED_UNTIL`** *(scalar)* = `'hr_rfid_demo.simulated_until'`  - line 28
- **`DEMO_WEBSTACK`** *(scalar)* = `'hr_rfid.demo_module'`  - line 30
- **`ENTRANCE_CTRL`** *(scalar)* = `'hr_rfid.demo_ctrl_icon110'`  - line 31
- **`INNER_CTRL`** *(scalar)* = `'hr_rfid.demo_ctrl_icon115'`  - line 32
- **`DAY_WORKERS`** *(collection)* = `('hr.employee_admin', 'hr.employee_ngh', 'hr.employee_chs', 'hr.employee_mit', 'hr.employee_niv', 'hr.employee_stw', 'hr.employee_fme', 'hr.employee_fpi', 'hr.employee_jth', 'hr.employee_vad', 'hr.employee_han', 'hr.employee_jve', 'hr.emplo  # ...truncated`  - line 36
- **`NIGHT_WORKERS`** *(collection)* = `('hr.employee_jod', 'hr.employee_jgo')`  - line 53
- **`SATURDAY_WORKERS`** *(collection)* = `('hr.employee_han', 'hr.employee_jve')`  - line 54
- **`VISITOR_CARD`** *(scalar)* = `'hr_rfid.demo_card_2'`  - line 55
- **`SENSOR`** *(scalar)* = `'hr_rfid.demo_th_sensor_server_room'`  - line 56
- **`GRANTED`** *(scalar)* = `3`  - line 58
- **`DENIED`** *(scalar)* = `4`  - line 59
- **`EXIT_BUTTON`** *(scalar)* = `21`  - line 60
- **`DOOR_HELD_OPEN`** *(scalar)* = `25`  - line 61
- **`DOOR_FORCED`** *(scalar)* = `26`  - line 62
- **`POWER_ON`** *(scalar)* = `30`  - line 63
- **`WAY_IN`** *(scalar)* = `1`  - line 66
- **`WAY_OUT`** *(scalar)* = `2`  - line 67
- **`SEED`** *(scalar)* = `20261113`  - line 68


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

This module does not create or extend any `ir.ui.view` records.


## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_rfid_demo_cron`** (RFID Demo: simulate the passages since the last run) on `model_hr_rfid_demo`, runs every 15 minutes, active=True

### Data records summary

- `hr.rfid.card`: 14 record(s)
- `resource.calendar`: 2 record(s)
- `hr.employee`: 2 record(s)
- `ir.cron`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>

No images, diagrams or screenshots are shipped with this module.


## FAQ & Troubleshooting <a id='faq'></a>

No FAQ candidates have been mined yet. Run the skill with the `chat_history` miner enabled, or author `docs/faq.md` manually to populate this section.


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_demo`
- Source digest: `sha256:3c6bd1174600ebc018021bae161a2068a56b29e82df7d29a2e4218cbed217d76`
- Generated at: `2026-11-13T10:32:19+00:00`
- Generator: `polimex_module_knowledge`
