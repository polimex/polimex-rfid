====================
RFID Hardware Import
====================

Overview
========

Most installations are built from the top down: the hardware is added, the
access control module initialises it, and the people, cards and access groups
are set up afterwards. This module does the opposite. It surveys a system that
is already working - set up by another system or by hand - **without changing
anything on the devices**, and then imports what it found into this Odoo.

The survey only ever *reads*. Every command sent to a controller is checked
against a fixed list of read commands before it leaves, and every command is
logged with its reply so the survey can prove it changed nothing. The import
creates records here and writes nothing to the controllers. Handing a module
over to this server is a separate, explicit action on the module.

Features
========

* Finds the modules on the local network with the access control module's own
  network search; modules behind a router, and modules already registered here,
  are added by address. Only a bare IP address or host name is accepted.
* Works on large sites: tens of thousands of cards are read and imported in
  small pieces that are each saved, within the time the server gives to
  background work. A survey interrupted by a restart continues where it
  stopped, also in the middle of a card table.
* Exports everything it read as a file, with or without importing: an Excel
  workbook for people (one sheet per kind of thing, raw replies included) or a
  JSON document for another system or a later import.
* Reads every controller on each module: its settings and its complete card
  table, including the time schedule and the alarm right of every card.
  Vending machine controllers are listed but left out; other non-access devices
  (fire panels, temperature and relay controllers, ...) are imported with their
  settings only.
* Matches the cards to names from a CSV or Excel file (name, card number).
  Cards without a name get a generated owner.
* Proposes access groups from the rights the controllers hold: doors that
  always go together form one group, and a card belongs to every group it
  holds.
* Takes the time schedules from the controllers; where controllers disagree on
  a slot, the operator chooses which one to take.
* Reports every conflict with records already present here; nothing is merged
  without a decision. A controller or module that could not be read is
  reported, and can be read again once the cause is fixed.
* Lets the operator merge proposed groups, and refuses a merge the access
  control module could not hold, with the reason.
* Imports modules (switched off), controllers with their doors and readers,
  people as contacts or employees, cards and access groups - every step can be
  left out. A second survey of the same site creates nothing twice.

Configuration
=============

No configuration is needed. The survey runs in the background; the scheduled
action "RFID: continue hardware surveys" must stay active.

Usage
=====

1. RFID System > Hardware Manager > **Import from Hardware** > New.
2. Find the modules on the network, or add one by address. Tick the ones to
   read and press **Read the controllers**.
3. When the reading is done, upload a names file or continue without one.
4. Review the people, the proposed access groups and the schedule slots.
   Resolve the findings marked "Must be resolved".
5. Press **Import...**, choose what to import, and start it.
6. When you are ready to hand a module over, use **Point to this server** on
   the module, then **Enable here**.

A module that requires a password gets it on its own form (**Access to the
module**), then **Check again**. A survey that stops on a problem keeps what it
read and imported; **Reopen the survey** takes it back to the step it was at.

Every command sent to the hardware opens from the **Commands sent** button on
the survey, with its reply. A workbook sheet holds about a million rows; a
survey too large for it is exported as JSON.

Technical
=========

* Persistent survey with a background worker (scheduled action), resumable per
  controller and per card table page. Each pass stops when the scheduler's job
  has used its time and hands over to a fresh job; a pass that could do
  nothing (the survey row held by someone else, a write at the same moment)
  asks the scheduler to come back at once.
* The people, cards and memberships steps of the import commit in batches with
  the position of the step, so no step is ever repeated from the start.
* Every record the import creates carries an external ID
  (``__import__.rfid_import_hw_...``), which is what makes a second import
  idempotent.
* Controllers are created through the path the access control module uses for
  a controller it already knows, so no reset or clock synchronisation is ever
  queued.

Credits
=======

* Polimex Dev Team <odoo@polimex.co>
* https://polimex.co
