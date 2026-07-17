=====================
Working Time Dashboard
=====================

Adds a ready-made **Working Time** board to the standard Odoo *Dashboards*
application, under the *Human Resources* section. Install the module and the
board appears for attendance officers - no configuration required.

Overview
========

The board surfaces the most important working-time KPIs from the RFID
attendance measurement layer (``hr.attendance.extra``):

* **Worked Hours** - total actual worked time in the period
* **Late Arrivals** / **Early Leaves** - discipline counts
* **Overtime Hours** - recorded overtime
* **Utilization** - actual vs. theoretical work time
* Charts: worked hours and overtime by department, worked-hours trend,
  overtime share by department

Interactive filters at the top of the board: **Period**, **Department** and
**Company**.

Configuration
=============

None. The dashboard is published on install and is visible to members of the
*Attendance / Officer* group.

Technical
=========

A thin bridge module shipping one ``spreadsheet.dashboard`` record whose
``spreadsheet_binary_data`` is a pre-built o-spreadsheet document
(``data/files/working_time_dashboard.json``). Depends on ``spreadsheet_dashboard``
and ``hr_attendance_late``; auto-installs whenever ``hr_attendance_late`` is present.

Credits
=======

* Polimex Holding Ltd. <https://polimex.co>
