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
  on some days, so the portal has recent passages under their events.

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

Credits
=======

Authors
-------

* Polimex Dev Team

Maintainers
-----------

This module is maintained by Polimex Holding Ltd. - https://polimex.co
