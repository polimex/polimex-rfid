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
