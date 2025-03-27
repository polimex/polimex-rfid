Polimex ANPR Module
===================

.. image:: https://img.shields.io/badge/maturity-Beta-yellow.png
   :target: https://odoo-community.org/page/development-status
   :alt: Beta
.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: AGPL-3
.. image:: https://img.shields.io/badge/github-Polimex%20ANPR-lightgray.png?logo=github
   :target: https://github.com/polimex/polimex-rfid
   :alt: GitHub
.. image:: https://img.shields.io/badge/odoo-18.0-blue.svg
   :target: https://www.odoo.com
   :alt: Odoo 18.0

Overview
--------

The **Polimex ANPR** module for Odoo 18 provides a robust solution for managing IP cameras with Automatic Number Plate Recognition (ANPR) functionality. This module integrates with Hikvision cameras via the ISAPI protocol and offers seamless synchronization between camera settings and Odoo records.

Key features include:

- **Camera Management:** Store and update camera details (IP, port, credentials, brand, etc.), check connection status, and retrieve snapshots.
- **HTTP Host Configuration:** Configure and read the camera's HTTP host settings for event notifications.
- **Plate List Management:** Add, update, and remove license plate entries (whitelist, blacklist, etc.) via ISAPI commands.
- **RFID & ANPR Integration:** Link HR RFID cards (storing license plate numbers) to cameras, triggering corresponding camera commands automatically.
- **Asynchronous Command Execution:** Use a dedicated command model to queue and execute operations (with retry logic and state tracking), ensuring that each camera processes only one command at a time.

Table of Contents
-----------------
.. contents::
   :local:
   :depth: 2

Installation
------------

1. **Dependencies:**

   - Odoo 18.0
   - HR RFID module
   - Python packages: ``requests`` (plus standard libraries)

2. **Setup:**

   - Place the ``polimex_ip_cam`` folder into your Odoo addons path.
   - Update the module list in Odoo.
   - Install the **Polimex ANPR** module from the Apps menu.
   - (Optional) Load demo data from the provided demo files for testing.

Configuration
-------------

1. **Camera Configuration:**

   - Create a new camera record in the ``CCTV Camera`` model.
   - Fill in the camera's IP address, port, username, password, and brand (e.g., Hikvision).
   - Configure additional parameters such as HTTP host and integration type.

2. **HTTP Host Setup:**

   - Use the action methods to set and retrieve the camera's HTTP host configuration.
   - The configuration is stored in a field using a ``param=value`` format and is sent to the camera via ISAPI.

3. **Plate List Management:**

   - Link HR RFID cards with cameras via the ``cctv.camera.rfid.rel`` model.
   - When a relation is created or removed, the module automatically creates and executes a corresponding command
     (e.g., add_plate or remove_plate).

4. **Command Processing:**

   - Commands are recorded in the ``cctv.camera.command`` model.
   - Each command includes type, request/response data, execution time, retry count (max 5), and state (new, in_progress, done, error).
   - Commands execute automatically upon creation and can be re-executed manually if needed.

Usage
-----

- **Camera Management:** Manage cameras and view their statuses and snapshots from the standard Odoo views.
- **Plate List Synchronization:** When you link an RFID card to a camera, the module automatically updates the camera’s plate list.
- **Command Monitoring:** Use the provided form and tree views for camera commands to monitor, review, and re-execute commands.

API Details
-----------

The module uses Hikvision's ISAPI endpoints for:

- **Connection & Snapshot:** ``check_connection()`` and ``get_snapshot()`` methods verify connectivity and capture images.
- **HTTP Host Configuration:** ``set_http_host(config)`` and ``get_http_host()`` send and retrieve host settings.
- **Plate List Commands:** ``add_plate_to_list(plate_entries)`` and ``delete_plate_from_list(plate_entries)`` manage license plate entries.

For detailed XML structures and supported parameters, please refer to the official Hikvision ISAPI documentation.

Contributing
------------

Contributions are welcome! Please follow the best practices outlined in the Odoo developer guidelines.
For detailed instructions on contributing, visit the
`Odoo Community Association contribution page <https://odoo-community.org/page/Contribute>`_.

Credits
-------

- **Polimex Dev Team**
- **Contributors:** (List your contributors here)
- Special thanks to the Odoo Community Association (OCA) for their best practice guidelines.

Bug Tracker
-----------

Bugs are tracked on the GitHub Issues page:
`https://github.com/polimex/polimex-rfid/issues <https://github.com/polimex/polimex-rfid/issues>`_

License
-------

This module is licensed under the AGPL-3 license. See the
`LICENSE <http://www.gnu.org/licenses/agpl-3.0-standalone.html>`_ file for details.

