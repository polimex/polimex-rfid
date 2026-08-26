=====================
Labour Cost Dashboard
=====================

Adds a ready-made **Labour Cost** board to the standard Odoo *Dashboards*
application, under the *Human Resources* section. Install the module and the
board appears for attendance managers - no configuration required.

Overview
========

The board surfaces labour-cost KPIs derived from the RFID attendance cost layer
(``hr.attendance.extra`` cost fields):

* **Total Cost** - actual worked-time cost in the period
* **Overtime Cost** and **Night Supplement** - premium components
* **Avg Hourly Cost** - blended hourly rate
* Charts: cost and overtime cost by department, cost trend, cost share by department

Interactive filters at the top of the board: **Period**, **Department** and
**Company**. Monetary values are shown in the company currency (EUR).

Configuration
=============

None. The dashboard is published on install and is visible to members of the
*Attendance / Manager* group (cost figures are management-only).

Technical
=========

A thin bridge module shipping one ``spreadsheet.dashboard`` record whose
``spreadsheet_binary_data`` is a pre-built o-spreadsheet document
(``data/files/labour_cost_dashboard.json``). Depends on ``spreadsheet_dashboard``
and ``hr_attendace_rfid_hr_hourly_cost``; auto-installs whenever the latter is present.

Credits
=======

* Polimex Holding Ltd. <https://polimex.co>
