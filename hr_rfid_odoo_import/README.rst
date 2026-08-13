========================
RFID Odoo Data Import
========================

..
   :target: https://polimex.co
   :alt: License: AGPL-3

Import RFID access control data from older Odoo instances (v14-v18) into Odoo 19
via XML-RPC API.

Overview
========

This module provides a multi-step wizard for migrating RFID access control data
from older Odoo instances into Odoo 19. It connects to the source Odoo via
XML-RPC API, reads configuration and historical data, and recreates it in the
target database.

Features
========

* **XML-RPC connection** - works with any Odoo instance (local or remote, v14-v18)
* **Version-tolerant reads** - each phase names the fields it wants and checks
  them against the source with ``fields_get()``, so a field that only exists in
  some versions is used where present and skipped where absent
* **Multi-company support** - select which company to import
* **Runs in the background** - the transfer is handed to a scheduled job and
  continues after the dialog is closed. A real site carries tens of thousands of
  events, which is far more than a single web request is allowed to spend. Work
  is done in committed pieces; an interrupted transfer continues where it
  stopped instead of starting over.
* **Phases, each declaring what it needs** - a phase states which feature the
  source must have and which models this system must provide. A phase that
  cannot run is recorded with the reason, rather than leaving a silent gap:

  - Core & Hardware (webstacks, controllers, doors, readers, time schedules)
  - People (employees, partners, departments, categories)
  - Zones (after People - membership lists are the people)
  - Sites (the tree of locations, the equipment on it, the contacts in it)
  - Access Control (access groups, relations, cards -> card-door regeneration)
  - Site Groups (a site's own access group, restored after the real ones)
  - Cameras (ANPR cameras, their readers and doors, their plate lists)
  - Events (user events, system events, temperature/humidity logs)
  - Vending (rows, events, balance history, auto-refill)
  - Attendance (hr.attendance, hr.attendance.extra)
  - Services (rfid.service, rfid.service.sale, tags)

* **Deduplication** via ``ir.model.data`` with ``__import__`` prefix
* **Nothing is said to the hardware** - no controller and no camera receives a
  command while a transfer is running. The site stays guarded throughout.
* **Conflict detection** - a record that would break an existing unique
  constraint is reported for the operator to decide, never merged silently
* **Direct SQL batch insert** for large datasets (events, attendance, balance history)
* **An account of what happened** - one line per step, including what was left
  behind and why

Configuration
=============

No special configuration is needed. The module adds a menu entry under
**RFID -> Import -> Import from Odoo**.

Usage
=====

1. Go to **RFID -> Import -> Import from Odoo**
2. Enter the source Odoo connection details (URL, database, login, password)
3. Click **Check Connection** to verify connectivity
4. Select the source company to import
5. Choose which optional data to include (events, vending, attendance, services)
6. Click **Start Import** and monitor progress
7. The transfer opens on its own page and continues in the background. Close it
   whenever you like; come back to **RFID -> Data Transfers** to see how far it
   has got and what it moved.

Requirements
============

* The source Odoo instance must be running and accessible via HTTP/HTTPS
* The source user must have admin-level access to read all RFID data
* Target database must have ``hr_rfid`` installed
* For vending/attendance/service import, the corresponding modules must be
  installed in the target

Credits
=======

Authors
-------

* Polimex Holding Ltd.

Website: https://polimex.co
