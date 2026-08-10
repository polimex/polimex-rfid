RFID Terminal Lookup
====================

Overview
--------

Display terminals mounted next to an access controller need one thing the
existing ``hr_rfid`` device API does not provide: turning a card number into
the employee's name so the terminal can greet the person who just presented
their card.

This module adds exactly that - a single read-only lookup endpoint. It does
not create events, does not open doors and does not write attendance; the
existing zone pipeline in ``hr_attendance_multi_rfid`` remains the only way
attendance is recorded.

Configuration
-------------

Terminals authenticate with the same credentials as any other device on the
bus: the module serial (``convertor``) and its key, verified against
``hr.rfid.webstack`` with a constant-time compare. Register the terminal as a
webstack record (or let the standard auto-discovery do it) before use.

Usage
-----

``POST /hr/rfid/terminal/lookup`` (JSON in, JSON out)::

    {"convertor": "123456", "key": "...", "card": "0012345678"}

Response::

    {"found": true, "name": "Иван Петров", "employee_id": 42}

Unknown cards answer ``{"found": false}`` - never an error, so the terminal can
simply show "Unknown card".

Technical
---------

The card is matched on ``hr.rfid.card.number`` (the 10-digit form the readers
report) within the webstack's company, then resolved through the card's owner.
Lookups are read-only and rate-limited per module serial.

Credits
-------

Polimex Holding Ltd. - https://polimex.co
