---
id: hr_rfid_demo
title: RFID Demo Data
module: hr_rfid_demo
module_version: 19.0.1.2.1
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: 'A demo company that keeps working: passages, attendance, lateness and overtime for the RFID
  set, day after day'
last_updated: '2026-11-19'
source_digest: sha256:37e14f8e39d98491069e7f99040a1066b87175e9d65d7ac90c532b5698762c90
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


# RFID Demo Data - `hr_rfid_demo` v19.0.1.2.1

A demo company that keeps working: passages, attendance, lateness and overtime for the RFID set, day after day

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_demo`
- **Version**: `19.0.1.2.1`
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
* where the Vending add-on is installed, a vending machine people buy from:
  on most days a card is shown and an item bought, paid from the person's
  credit; some sales are paid in coins and fill the machine's cash; and
  somebody whose credit has run out is sold nothing until the monthly refill;
* the customer with a portal login (Joel Willis, login ``portal``) dropping by
  on some days, so the portal has recent passages under their events;
* where the Services add-ons are installed, a service that is running for the
  demo login (Marc Demo, login ``demo``): "RFID Services" in the portal shows
  it next to the ones that ended, and its badge is valid. The demo sells it
  the way the till does whenever the customer has none; they come in on some
  evenings, every entry is counted as a visit, and when the visits or the
  month run out the next one is sold.

A person on approved leave does not come in that day, nobody comes in on a
public holiday of the company, and a day somebody already has attendance
entered by hand is left to them.

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
* The vending machine (``hr_rfid_vending.demo_ctrl_vending``) and the portal
  customer joined the demo after the doors and keep a mark of their own
  (``hr_rfid_demo.vending_and_portal_simulated_until``): a demo that was
  already running gets their six weeks at its next run, and the days at the
  doors are not walked again. The machine reports through the same
  ``_hw_parse_event`` as a real one (credit request 64, sale 47), from a seed
  of its own, and a sale is reported only for a buyer who has the credit
  (``_demo_can_pay``). The demo people get their starting credit and a
  monthly refill once (``_demo_vending_credit``); the vending add-on's own
  refill task keeps them going. Without the Vending add-on, or once its demo
  machine is moved off the demo module, nothing of this runs.

* The customer of the services is the demo login
  (``rfid_service_portal.demo_portal_service_card``, the badge of
  ``base.partner_demo``). ``_demo_keep_a_service_running`` sells them
  ``rfid_service_base.demo_service_gym_combo`` through the till's own wizard
  (``rfid.service.sale.wiz``, ``write_card``) when no service of theirs runs
  or is still ahead. A refusal of the sale - the till's (``UserError``) or
  the database's one service per customer and period - is logged and the run
  goes on. Their evenings at the entrance come from a seed of their own;
  ``_demo_may_pass`` lets an entry through only with a valid badge while a
  service runs at that moment, and an exit only when they are in, so the
  system counts the visits and closes the service itself. Without the
  Services add-ons, or once the badge belongs to another contact, nothing of
  this runs.

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
Python class `HrRfidDemo` in `models/hr_rfid_demo.py:97`.  AbstractModel.  Description: *RFID demo simulation*.

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
- **`_demo_simulated_until(self, mark, until)`** - decorators: `@api.model`
  - Where a part of the demo has got to; its first run starts weeks back.
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`_demo_answer_commands(self, webstack)`** - decorators: `@api.model`
  - Close what the system asked of the demo module, as hardware would.
  - effects: `sudo`
  - touches: `hr.rfid.command`
- **`_demo_environment_readings(self, since, until)`** - decorators: `@api.model`
  - The server-room sensor of the demo reports every two hours.
  - effects: `sudo`
- **`_demo_hourly_costs(self)`** - decorators: `@api.model`
  - The demo people get an hourly cost, so the labour cost has figures.
  - effects: `sudo`
  - touches: `hr.attendance.extra`, `hr.employee`
- **`_demo_report(self, webstack, ctrl, reader, card, moment, event_n, data=NO_DATA)`** - decorators: `@api.model`
  - One report of the demo module, as the device sends it.
  - effects: `with_context`
- **`_demo_days(self, since, until)`** - decorators: `@api.model`
  - The days of a window, each with who is in on it.
  - effects: `sudo`
  - touches: `hr.attendance`
- **`_demo_passages(self, since, until)`** - decorators: `@api.model`
  - Every passage of the window, in the order the doors saw them.
- **`_demo_also(self, since, until, machine, badge)`** - decorators: `@api.model`
  - What joined the demo after the doors.
- **`_demo_people(self)`** - decorators: `@api.model`
  - (employee, card, 'day' | 'night' | 'saturday') for who has a badge.
  - touches: `hr.rfid.card`
- **`_demo_day(self, employee, kind, day, entrance, inner)`** - decorators: `@api.model`
  - The passages of one person on one day: (utc moment, ctrl, reader, code).
- **`_demo_night(self, rng, at, weekday, entrance)`** - decorators: `@api.model`
  - Monday to Friday nights, from ten in the evening to six.
- **`_demo_working_day(self, rng, at, employee, weekday, entrance, inner)`** - decorators: `@api.model`
  - A day by the person's own schedule, with its usual deviations.
- **`_demo_moving_about(self, rng, arrival, leaving, inner)`** - decorators: `@api.model`
  - Moving about inside: the inner doors, in and back out again.
- **`_demo_day_extras(self, day, entrance, inner, people)`** - decorators: `@api.model`
  - What the doors see besides people at work: refusals, a visitor, alarms.
- **`_demo_portal_guest(self, day, entrance, inner)`** - decorators: `@api.model`
  - The customer with a portal login drops by on some days.
- **`_demo_service_badge(self)`** - decorators: `@api.model`
  - The badge of the demo's service customer, or nothing.
  - touches: `hr.rfid.card`
- *11 more not listed*

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_rfid_demo.py:921`.  Model.  Inherits: `hr.employee`.


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_rfid_demo.py`

- **`BACKFILL_DAYS`** *(scalar)* = `45`  - line 30
- **`SIMULATED_UNTIL`** *(scalar)* = `'hr_rfid_demo.simulated_until'`  - line 32
- **`ALSO_SIMULATED_UNTIL`** *(scalar)* = `'hr_rfid_demo.vending_and_portal_simulated_until'`  - line 34
- **`DEMO_WEBSTACK`** *(scalar)* = `'hr_rfid.demo_module'`  - line 36
- **`ENTRANCE_CTRL`** *(scalar)* = `'hr_rfid.demo_ctrl_icon110'`  - line 37
- **`INNER_CTRL`** *(scalar)* = `'hr_rfid.demo_ctrl_icon115'`  - line 38
- **`DAY_WORKERS`** *(collection)* = `('hr.employee_admin', 'hr.employee_ngh', 'hr.employee_chs', 'hr.employee_mit', 'hr.employee_niv', 'hr.employee_stw', 'hr.employee_fme', 'hr.employee_fpi', 'hr.employee_jth', 'hr.employee_vad', 'hr.employee_han', 'hr.employee_jve', 'hr.emplo  # ...truncated`  - line 42
- **`NIGHT_WORKERS`** *(collection)* = `('hr.employee_jod', 'hr.employee_jgo')`  - line 59
- **`SATURDAY_WORKERS`** *(collection)* = `('hr.employee_han', 'hr.employee_jve')`  - line 60
- **`VISITOR_CARD`** *(scalar)* = `'hr_rfid.demo_card_2'`  - line 61
- **`PORTAL_GUEST_CARD`** *(scalar)* = `'hr_rfid_portal.demo_portal_card'`  - line 64
- **`SERVICE_CUSTOMER`** *(scalar)* = `'base.partner_demo'`  - line 68
- **`SERVICE_BADGE`** *(scalar)* = `'rfid_service_portal.demo_portal_service_card'`  - line 69
- **`SERVICE_SOLD`** *(scalar)* = `'rfid_service_base.demo_service_gym_combo'`  - line 70
- **`VENDING_MACHINE`** *(scalar)* = `'hr_rfid_vending.demo_ctrl_vending'`  - line 72
- **`SENSOR`** *(scalar)* = `'hr_rfid.demo_th_sensor_server_room'`  - line 73
- **`GRANTED`** *(scalar)* = `3`  - line 75
- **`DENIED`** *(scalar)* = `4`  - line 76
- **`EXIT_BUTTON`** *(scalar)* = `21`  - line 77
- **`DOOR_HELD_OPEN`** *(scalar)* = `25`  - line 78
- **`DOOR_FORCED`** *(scalar)* = `26`  - line 79
- **`POWER_ON`** *(scalar)* = `30`  - line 80
- **`CREDIT_REQUEST`** *(scalar)* = `64`  - line 81
- **`SALE`** *(scalar)* = `47`  - line 82
- **`CREDIT_RETURNED`** *(scalar)* = `49`  - line 83
- **`NO_DATA`** *(scalar)* = `'00000000000000'`  - line 85
- **`NO_CARD`** *(scalar)* = `'0000000000'`  - line 86
- **`VENDING_STARTING_CREDIT`** *(scalar)* = `30.0`  - line 89
- **`WAY_IN`** *(scalar)* = `1`  - line 92
- **`WAY_OUT`** *(scalar)* = `2`  - line 93
- **`SEED`** *(scalar)* = `20261113`  - line 94


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
- Source digest: `sha256:37e14f8e39d98491069e7f99040a1066b87175e9d65d7ac90c532b5698762c90`
- Generated at: `2026-11-19T16:38:03+00:00`
- Generator: `polimex_module_knowledge`
