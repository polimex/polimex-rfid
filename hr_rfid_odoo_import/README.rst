========================
RFID Odoo Data Import
========================

..
   :target: https://polimex.co
   :alt: License: AGPL-3

Import RFID access control data from older Odoo instances (v14—v18) into Odoo 19
via XML-RPC API.

Overview
========

This module provides a multi-step wizard for migrating RFID access control data
from older Odoo instances into Odoo 19. It connects to the source Odoo via
XML-RPC API, reads configuration and historical data, and recreates it in the
target database.

Features
========

* **XML-RPC connection** — works with any Odoo instance (local or remote, v14—v18)
* **Dynamic schema discovery** — automatically detects source fields via ``fields_get()``
* **Multi-company support** — select which company to import
* **Phased import** with savepoint isolation per phase:

  - Phase 1+3: Hardware (webstacks, controllers, doors, readers, zones, time schedules)
  - Phase 2: People (employees, partners, departments, categories)
  - Phase 4: Access (access groups, relations, cards → automatic card-door regeneration)
  - Phase 5: Events (user events, system events, temperature/humidity logs)
  - Phase 6a: Vending (rows, events, balance history, auto-refill)
  - Phase 6b: Attendance (hr.attendance, hr.attendance.extra)
  - Phase 6c: Services (rfid.service, rfid.service.sale, tags)

* **Deduplication** via ``ir.model.data`` with ``__import__`` prefix
* **Hardware command suppression** — no commands sent to controllers during import
* **Conflict detection** — warns about duplicate cards, employees, etc.
* **Direct SQL batch insert** for large datasets (events, attendance, balance history)
* **Progress tracking** with real-time status updates

Configuration
=============

No special configuration is needed. The module adds a menu entry under
**RFID → Import → Import from Odoo**.

Usage
=====

1. Go to **RFID → Import → Import from Odoo**
2. Enter the source Odoo connection details (URL, database, login, password)
3. Click **Check Connection** to verify connectivity
4. Select the source company to import
5. Choose which optional data to include (events, vending, attendance, services)
6. Click **Start Import** and monitor progress
7. Review the import log for results and any warnings

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
