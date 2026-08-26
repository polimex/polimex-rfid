========================
Access Control Dashboard
========================

Adds a ready-made **Access Control** board to the standard Odoo *Dashboards*
application, under the *Human Resources* section. No configuration is needed:
install the module and the board appears for RFID access-control officers.

Overview
========

The board surfaces the most important access-control KPIs from the RFID event
log (``hr.rfid.event.user``):

* **Total Events** - all access events in the period
* **Denied** - blocked attempts (invalid rights, time schedule, anti-passback)
* **Unique People** - distinct employees and visitors seen
* **Grant Rate** - granted vs. total access attempts
* Charts: events by action, busiest doors, daily access trend, access share by door

Every card and chart is driven by three interactive filters shown at the top of
the board: **Period**, **Company** and **Door**.

Configuration
=============

None. The dashboard is published on install and is visible to members of the
*RFID Access Control / Officer* group.

Technical
=========

This is a thin bridge module: it ships a single ``spreadsheet.dashboard`` record
whose ``spreadsheet_binary_data`` is a pre-built o-spreadsheet document
(``data/files/access_control_dashboard.json``). It depends on the core
``spreadsheet_dashboard`` app and on ``hr_rfid``; it auto-installs whenever
``hr_rfid`` is present.

Credits
=======

* Polimex Holding Ltd. <https://polimex.co>
