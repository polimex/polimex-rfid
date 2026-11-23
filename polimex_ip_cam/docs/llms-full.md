---
id: polimex_ip_cam
title: IP Camera Management
module: polimex_ip_cam
module_version: 19.0.1.20.3
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Module for managing IP cameras via manufacturers integration integration
last_updated: '2026-11-23'
source_digest: sha256:27cb8f32086f994e543beee81ffa8d6a8aac6c6c53f84f8e855d9dea0300534b
depends:
- hr_rfid
entities:
  primary: cctv.camera
  related:
  - cctv.camera.command
  - cctv.camera.diagnostic
  - cctv.camera.discovery.line
  - cctv.camera.discovery
  - cctv.camera.rfid.rel
  - hr.rfid.card
  - hr.rfid.command
  - hr.rfid.reader
  - hr.rfid.door
  - hr.rfid.card.door.rel
  - hr.rfid.event.system
  - hr.rfid.event.user
keywords:
- cam
- camera
- cameras
- cctv
- command
- diagnostic
- discovery
- integration
- line
- managing
- manufacturers
- module
- polimex
license: AGPL-3
author: Polimex Dev Team
category: Hidden/Tools
installable: true
application: false
auto_install: false
counts:
  models: 13
  views: 18
  access_rules: 9
  record_rules: 6
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:be961e59fbf52a48c69b6f1bd6dd022ea0bb67e556c987a7ce72d990a1befd8e
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:5bae196d52f56441943f938c722d80ec2313e2e4bc9794eb9b13658dbe35f763
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# IP Camera Management - `polimex_ip_cam` v19.0.1.20.3

Module for managing IP cameras via manufacturers integration integration

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `polimex_ip_cam`
- **Version**: `19.0.1.20.3`
- **Category**: Hidden/Tools
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`

### README (verbatim)

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
.. image:: https://img.shields.io/badge/odoo-19.0-blue.svg
   :target: https://www.odoo.com
   :alt: Odoo 19.0

Overview
--------

The **Polimex ANPR** module for Odoo 19 provides a robust solution for managing IP cameras with Automatic Number Plate Recognition (ANPR) functionality. This module integrates with Hikvision cameras via the ISAPI protocol and offers seamless synchronization between camera settings and Odoo records.

Key features include:

- **Camera Management:** Store and update camera details (IP, port, credentials, brand, etc.), check connection status, and retrieve snapshots. Connection check also records the model, serial number and the short *sub-serial* (the identifier the camera reports as ``deviceUUID`` in ANPR events).
- **HTTP Host Configuration:** Configure and read the camera's HTTP host (event-notification) settings. The ``SubscribeEvent`` heartbeat is **clamped to the camera's advertised range** (read from the device capabilities) so an out-of-range value can no longer be rejected with *"Invalid XML Content"*; the host document is updated read-modify-write so fields the module does not manage (e.g. ``checkResponseEnabled``) are preserved.
- **Plate List Management:** Add and remove license plates in the camera's two hardware lists — **Whitelist** (allow) and **Blacklist** (deny). The transport is **capability-detected**: legacy cameras use ``/ISAPI/ITC/Entrance/VCL``; TCG/7-series firmware that dropped VCL uses the LP-audit API (JSON record upsert + JSON delete). See *Hikvision ISAPI Compatibility* below.
- **ANPR Event Handling:** The public webhook records plate detections as RFID events. Cameras are identified by their stored sub-serial (``deviceUUID``) with a trusted source-IP fallback that learns the sub-serial on first contact; the request source IP (honoured via ``proxy_mode`` behind a reverse proxy) is the authentication anchor.
- **Clock Sync:** Heartbeats drive an automatic time-sync; the camera time zone is sent using Hikvision's POSIX/inverted sign convention to avoid an endless ``set_time`` loop.
- **RFID & ANPR Integration:** Link HR RFID cards (whose number is the license plate) to cameras; creating/removing a relation queues the matching add/remove command automatically.
- **Asynchronous Command Execution:** A dedicated command model queues and executes operations (retry + state tracking), serialising commands per camera.

Table of Contents
-----------------
.. contents::
   :local:
   :depth: 2

Installation
------------

1. **Dependencies:**

   - Odoo 19.0
   - HR RFID module
   - Python package: ``defusedxml`` (ships with Odoo's own ``requirements.txt``).

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

While data is being brought over from another system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A data transfer says nothing to the cameras. No plate is added or removed on a
camera, no barrier is moved, and no readers or door are made up for a camera
that is being brought across - it arrives with the ones the other system had,
so its history keeps pointing at the right door.

The consequence is that each camera still holds the plate list it held before
the transfer. **Refresh each camera's list once the transfer has finished**
(Reload whitelist on the camera). The transfer says so on its own page as well.

The cameras keep watching and keep letting people through throughout: only the
writing of new lists is held back, and that is the point - a transfer of a few
hundred plates would otherwise fire a few hundred requests at cameras that are
guarding a live site.

Camera self-test
~~~~~~~~~~~~~~~~

Open a camera and press "Self-Test" (managers only). One run checks
everything this system uses from the camera and shows every problem first,
every detail below: who answers at the address (model, serial, firmware),
the picture, the clock difference, where the camera sends its recognitions,
how many plates it holds against how many are recorded here, and whether a
plate can be written to it. The write check uses one test plate (TEST0001)
that is added and removed again - a working camera is left exactly as it
was, and the barrier is deliberately never touched. When writing fails, the
test also tries a record shaped like your real data and names the exact
part the camera refuses, quoting the camera's own answer - send that report
to support. The report lives in the dialog - copy it if you need to keep it.
The clock check compares the camera's wall clock in its own time zone; the
zone offset the camera claims is ignored, because these firmwares misstate
it.

If a plate-list reload keeps failing, the queue stops itself after three
identical refusals from the same camera and marks the remaining commands
with one explanation, instead of repeating the same error for every plate.

API Details
-----------

The module talks to Hikvision cameras through the ``HikvisionCamera`` helper
(``helpers/camera_api.py``) over ISAPI with HTTP Digest auth:

- **Connection & Snapshot:** ``check_connection()`` (also stores ``serialNumber`` and ``subSerialNumber``) and ``get_snapshot()``.
- **HTTP Host Configuration:** ``set_http_host(config)`` / ``get_http_host()`` — heartbeat is clamped to ``get_http_host_capabilities()``; the document is updated read-modify-write.
- **Plate List Commands:** ``add_plate_to_list(plate_entries)`` / ``delete_plate_from_list(plate_entries)`` — routed by ``_uses_lp_audit_api()`` to the VCL or LP-audit implementation (see below).
- **Time Sync:** ``set_time_config(...)`` driven from the ANPR webhook on heartbeat drift.

Hikvision ISAPI Compatibility
-----------------------------

Hikvision changed the plate-list API across camera generations, so the module
detects the supported one per camera (probing ``/ISAPI/ITC/Entrance/VCL/capabilities``)
and routes accordingly. Both paths are exercised by the test suite; the
LP-audit contract below was verified live against a **DS-TCG406-E (firmware
V5.4.4)**.

**Legacy — VCL** (``/ISAPI/ITC/Entrance/VCL``, older cameras):

- Add: ``PUT`` ``<SetVCLData>`` with ``<singleVCLData>`` rows (``listType`` ``0`` whitelist / ``1`` blacklist).
- Delete: ``DELETE`` ``<VCLDelCond>`` by ``plateNum``.

**Current — LP-audit** (``/ISAPI/Traffic/channels/<n>/...``, TCG / 7-series
firmware that returns *notSupport* for VCL):

- Read: ``POST searchLPListAudit`` (XML ``<LPListAuditSearchDescription>``)
  returns the plates currently stored on the camera, paged.
- Add / update: ``PUT licensePlateAuditData/record?format=json`` with a JSON
  body ``{"LicensePlateInfoList": [{...}]}``. Each record carries
  ``LicensePlate``, ``listType`` (``allowList``/``blockList``), ``cardNo`` /
  ``cardID``, a ``createTime`` (validity start) / ``effectiveTime`` (validity
  end) window and ``operationType``/``operation``. Success is HTTP 200 with
  ``statusCode 1`` - any other status is a failure, so a plate the camera
  rejected is not marked done in Odoo. **Proven live on V5.5.0 (build
  260328, self-test on site, 2026-08-16):** this firmware REFUSES a record
  write onto a plate it already holds (badParameters / "Invalid XML
  Content"), while accepting a fresh plate - the write ladder therefore
  withdraws the exact plate and writes it again (the replace step) before
  degrading anything else. V5.4.4 merged by plate directly.
- Delete: ``PUT DelLicensePlateAuditData?format=json`` with
  ``{"deleteAllEnabled": false, "CompoundCond": {"plateColor": "", "licensePlate": "<plate>"}}``.

**Camera identification (NAT-proof):** ``action_set_http_host`` embeds the
camera's sub-serial (deviceUUID) in the callback URL —
``/ipcam/anpr/event/<sub_serial>``. Every notification (ANPR event *and*
heartbeat, whose body carries no UUID) therefore arrives with the camera
identity in the path, which is stable even when the camera is behind NAT and
its source/body IPs do not match the stored address. The webhook resolves the
camera by this URL token first; when so identified, the token is the
authentication and the source-IP check (which cannot work behind NAT) is
skipped. Note: the token is the camera sub-serial, not a secret — on an
untrusted segment, prefer a per-camera random token. Body-reported IP is never
used for identification (informational/debug only).

**Travel direction:** read from ``<direction>`` inside the ``<ANPR>`` block
(``forward`` / ``reverse``) — forward books the In reader, reverse the Out
reader. The companion ``detectDir`` / ``carDirectionType`` are recorded in the
event description for diagnosis.

**Operational notes:**

- Behind a reverse proxy, enable Odoo ``proxy_mode = True`` and forward
  ``X-Forwarded-For`` so the IP fallback (legacy, no-token) still sees the
  camera's real source IP. With the URL token, identification no longer
  depends on the IP.
- ``server_setup`` accepts ``param=value`` lines that override the HTTP-host
  defaults (e.g. ``SubscribeEvent.heartbeat=30``); values are still clamped to
  the camera's advertised range.

For the full XML/JSON structures refer to the official Hikvision ISAPI guides
(the TCG ANPR integration guide for the LP-audit endpoints).

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


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i polimex_ip_cam --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `cctv.camera` <a id='model-cctv-camera'></a>
Python class `CctvCamera` in `models/cctv_camera.py:41`.  Model.  Inherits: `mail.thread`, `mail.activity.mixin`, `balloon.mixin`.  Description: *CCTV Camera Management*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Camera name for easy identification |
| `active` | Boolean | Active |  | ✓ | Uncheck to archive the camera. Inactive cameras no longer receive commands or ac |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the camera. Cameras are isolated per company; record rules pre |
| `tz` | Selection | Timezone |  | ✓ | The timezone of the camera's location. The camera's on-screen clock (burned onto |
| `tz_offset` | Char | Timezone offset |  | - | UTC offset string derived from the timezone above. Sent to the camera when synch |
| `behind_nat` | Boolean | Behind NAT |  | ✓ | Camera is behind a NAT (Network Address Translation) router |
| `ip_address` | Char | IP Address | ✓ | ✓ | Camera IP address |
| `port` | Integer | Port |  | ✓ | Camera port (usually 80 or 8000) |
| `username` | Char | Username |  | ✓ | Camera access username |
| `password` | Char | Password |  | ✓ | Camera access password. Restricted to CCTV managers — it is the credential an at |
| `brand` | Selection | Brand | ✓ | ✓ | Camera brand. 'ONVIF (generic)' is set by network discovery for a non-Hikvision  |
| `model` | Char | Model |  | ✓ | Camera model (obtained via ISAPI) |
| `serial_number` | Char | Serial Number |  | ✓ | Camera serial number |
| `sub_serial_number` | Char | Sub-Serial (Device UUID) |  | ✓ | Short device serial the camera reports as 'deviceUUID' in ANPR events (ISAPI sub |
| `firmware` | Char | Firmware |  | ✓ | Camera firmware version |
| `description` | Text | Description |  | ✓ | Additional camera information |
| `server_setup` | Text | Server Setup |  | ✓ | Camera server setup configuration (param=value per line) |
| `entrance_setup` | Text | Entrance Setup |  | ✓ | Camera entrance setup configuration (param=value per line) |
| `snapshot` | Image | Snapshot |  | ✓ | Camera snapshot image (base64 encoded) |
| `integration_type` | Selection | Integration Type |  | ✓ | Type of integration logic used for this camera |
| `connection_status` | Selection | Connection Status |  | ✓ | Latest connection check result |
| `connection_message` | Char | Connection Details |  | - | Plain-language explanation of the latest connection status and what to do about  |
| `last_seen` | Datetime | Last Seen Online |  | ✓ | When the camera last answered a connection check successfully. |
| `connection_error_detail` | Text | Technical Details |  | ✓ | Raw error returned by the last failed connection check (for support/diagnostics) |
| `last_heart_beat` | Datetime | Last Heartbeat |  | ✓ | Last successful received HeartBeat from the camera |
| `reader_ids` | Many2many → \`hr.rfid.reader\` | Reader |  | ✓ | RFID reader linked to this camera |
| `door_id` | One2many → \`hr.rfid.door\` | Door |  | ✓ | RFID doors whose readers are wired to this camera. Card assignments on these doo |
| `rfid_rel_ids` | One2many → \`cctv.camera.rfid.rel\` | RFID Card Relations |  | ✓ | Relations linking this camera with RFID cards and their list types |
| `rfid_card_ids` | Many2many → \`hr.rfid.card\` | RFID Cards |  | - | Flat view of every RFID card registered with this camera, across all list catego |
| `rfid_whitelist_count` | Integer | Whitelist Count |  | ✓ | Live count of plates classified as Whitelist (auto-grant). Used by the smart but |
| `rfid_blacklist_count` | Integer | Blacklist Count |  | ✓ | Live count of plates classified as Blacklist (auto-deny). Used by the smart butt |
| `lp_record_shape` | Selection | Lp Record Shape | ✓ | ✓ | What a plate record sent to this camera may contain. Filled in automatically: wh |

#### Notable methods

- **`_compute_tz_offset(self)`** - decorators: `@api.depends`
- **`_compute_connection_message(self)`** - decorators: `@api.depends`
- **`_compute_rfid_card_ids(self)`** - decorators: `@api.depends`
- **`_compute_list_counts(self)`** - decorators: `@api.depends`
- **`_compute_display_name(self)`** - decorators: `@api.depends`
- **`action_show_reader(self)`** - decorators: -
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - effects: `sudo`
  - touches: `cctv.camera`, `hr.rfid.door`, `hr.rfid.reader`
- **`get_api(self)`** - decorators: -
- **`_resolve_anpr_camera(self, device_uuid, src_ip, source_verify_on)`** - decorators: `@api.model`
  - Map an ANPR webhook event to its cctv.camera.
  - effects: `log_error`, `log_info`
- **`action_check_connection(self)`** - decorators: -
  - When the camera brand is hikvision, instantiate the HikvisionCamera API class and use it. Update the record's connection_status and, if available, update the camera's model and serial number. Also…
- **`action_get_http_host(self)`** - decorators: -
  - Retrieve the camera's HTTP host configuration, store it in server_setup as param=value lines, and display a user-friendly balloon message with bullet points.
  - effects: `message_post`
- **`action_set_http_host(self)`** - decorators: -
  - Задава HTTP host конфигурация на камерата, като използва стойностите от server_setup. server_setup трябва да бъде във формат "param=value" на отделни редове. Ключовете с точкова нотация се…
  - effects: `message_post`
- **`action_get_entrance_param(self)`** - decorators: -
  - Извлича entrance параметрите от камерата и ги записва във rec.entrance_setup във формат 'param=value'. При това вложената структура се представя с точкова нотация.
  - effects: `message_post`
- **`action_set_entrance_param(self)`** - decorators: -
  - Задава entrance параметрите на камерата чрез API, като прочита конфигурацията от rec.entrance_setup (форматирана като "param=value" на редове), възстановява вложената структура с unflatten_dict и…
  - effects: `message_post`
- **`action_get_snapshot(self)`** - decorators: -
  - Get a snapshot from the camera (base64 encoded) and store it in the snapshot field.
  - effects: `message_post`
- **`action_control_barrier(self, operation, gate_num)`** - decorators: -
  - Control the camera's barrier gate by sending an open/close command. :param operation: Стрингово описание на операцията(напр.'on', 'off', 'stop', 'locked') :param gate_num: Номер на бариерата
  - effects: `message_post`
- **`update_plate_in_list(self, plate_number, new_list_type)`** - decorators: -
  - Change the type in the list for a given registration number.
- **`notify_by_discuss(self, recipients, msg, attachments=None)`** - decorators: -
  - touches: `hr.rfid.notification`
- **`parse_event(self, files_data)`** - decorators: -
  - Parse the event data received from the camera. {'ANPR': {'ADRNo': 'unknown', 'CRIndex': '26', 'alarmDataType': '0', 'barrierGateCtrlType': '0', 'confidenceLevel': '100', 'country': '26', 'dangmark'…
  - effects: `log_warn`, `sudo`, `with_context`
  - touches: `hr.rfid.card`, `hr.rfid.event.system`, `hr.rfid.event.user`
- **`add_plate_to_cam(self, plate_number, list_type)`** - decorators: -
  - Add a plate number to the camera's list.
  - effects: `message_post`
- *5 more not listed*

### `cctv.camera.command` <a id='model-cctv-camera-command'></a>
Python class `CctvCameraCommand` in `models/cctv_camera_command.py:12`.  Model.  Inherits: `mail.thread`, `mail.activity.mixin`.  Description: *Camera Command for Execution*.  Default order: `create_date desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Command Reference |  | ✓ |  |
| `command_type` | Selection | Command Type | ✓ | ✓ |  |
| `execution_time` | Datetime | Execution Time |  | ✓ | Timestamp the command was successfully delivered to the camera. Empty while the  |
| `request_data` | Text | Request Data |  | ✓ | Data sent to the camera as part of the command, e.g. in param=value per line for |
| `response_data` | Text | Response Data |  | ✓ | Raw response returned by the camera, kept for audit / debugging. |
| `camera_id` | Many2one → \`cctv.camera\` | Camera | ✓ | ✓ | Camera this command targets. If the camera is deleted, queued commands cascade-d |
| `retry_count` | Integer | Retry Count |  | ✓ | How many times this command has been retried. Capped at 5 — beyond that the comm |
| `state` | Selection | State |  | ✓ | Lifecycle of the command — New: queued, not yet sent. In Progress: handler is cu |

#### Notable methods

- **`_check_retry_count(self)`** - decorators: `@api.constrains`
  - effects: `raise:UserError`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`queue_send(self)`** - decorators: -
  - effects: `sudo`
- **`action_execute(self)`** - decorators: -
  - Изпълнява командата. Методът променя състоянието на командата на 'in_progress', записва времето на изпълнение и извиква съответния API метод според command_type. При успех, състоянието се задава на…
  - effects: `log_error`, `log_warn`, `message_post`, `raise:UserError`, `sudo`

### `cctv.camera.diagnostic` <a id='model-cctv-camera-diagnostic'></a>
Python class `CctvCameraDiagnostic` in `models/cctv_camera_diagnostic.py:5`.  TransientModel (wizard).  Description: *Camera Self-Test Report*.

> The result screen of the camera self-test.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera | ✓ | ✓ | The camera this self-test was run against. |
| `report` | Text | Report |  | ✓ | Every problem found first, then every detail the camera reported. Copy it if you |

### `cctv.camera.discovery.line` <a id='model-cctv-camera-discovery-line'></a>
Python class `CctvCameraDiscoveryLine` in `models/cctv_camera_discovery_wizard.py:22`.  TransientModel (wizard).  Description: *Discovered Camera*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `discovery_id` | Many2one → \`cctv.camera.discovery\` | Discovery |  | ✓ | Discovery run that found this camera. |
| `name` | Char | Camera Name |  | ✓ | Name the camera will be created with. Pre-filled from the model and address; edi |
| `ip_address` | Char | Ip Address |  | ✓ | Address the camera reported on the local segment. |
| `brand` | Selection | Brand |  | ✓ | Detected from the discovery reply (SADP/ONVIF). Generic ONVIF for non-Hikvision  |
| `model` | Char | Model |  | ✓ | Hardware model as reported by the device. |
| `serial_number` | Char | Serial Number |  | ✓ | Device serial number from the discovery reply. |
| `mac_address` | Char | Mac Address |  | ✓ | Hardware (MAC) address — stable identity across DHCP changes. |
| `http_port` | Char | Http Port |  | ✓ | HTTP/ISAPI port the device serves on (default 80). |
| `discovery_method` | Char | Discovery Method |  | ✓ | Which probe found it: SADP, ONVIF, or both. |
| `existing_camera_id` | Many2one → \`cctv.camera\` | Existing Camera |  | ✓ | The camera record this device already is, recognised by its serial number (or, f |
| `status` | Selection | Status |  | ✓ | Whether this device is already registered here. The scan recognises registered c |
| `activated` | Boolean | Activated |  | ✓ | Hikvision cameras must be activated (password set) before use. Unchecked devices |

### `cctv.camera.discovery` <a id='model-cctv-camera-discovery'></a>
Python class `CctvCameraDiscovery` in `models/cctv_camera_discovery_wizard.py:68`.  TransientModel (wizard).  Description: *Camera Discovery*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `found_camera_ids` | One2many → \`cctv.camera.discovery.line\` | Discovered Cameras |  | ✓ | Cameras found on the local network. Remove the ones you do not want, then click  |

#### Notable methods

- **`action_create_cameras(self)`** - decorators: -
  - Create a cctv.camera per remaining line, then open the camera list filtered to what was just added. Connection details (sub-serial, firmware) are filled later by Check Connection.
  - effects: `log_info`, `log_warn`
  - touches: `cctv.camera`, `ir.actions.actions`

### `cctv.camera.rfid.rel` <a id='model-cctv-camera-rfid-rel'></a>
Python class `CctvCameraRfidRel` in `models/cctv_camera_rfid_rel.py:16`.  Model.  Description: *CCTV Camera - RFID Card Relation*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera | ✓ | ✓ | Camera to which this card relation belongs |
| `card_id` | Many2one → \`hr.rfid.card\` | RFID Card | ✓ | ✓ | Linked license plate or other vehicle identifier |
| `list_category` | Selection | List Category | ✓ | ✓ | The type of list this relation represents |

#### Notable methods

- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - super-split (super `create`): pre=- · post=`log_error`
  - effects: `log_error`
  - touches: `cctv.camera.command`
- **`unlink(self)`** - decorators: -
  - super-split (super `unlink`): pre=- · post=`log_error`
  - effects: `log_error`
  - touches: `cctv.camera.command`

### `hr.rfid.card` <a id='model-hr-rfid-card'></a>
Python class `HrRfidCard` in `models/hr_rfid_card.py:3`.  Model.  Inherits: `hr.rfid.card`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_rel_ids` | One2many → \`cctv.camera.rfid.rel\` | Camera Relations |  | ✓ | List of cameras in which this card is included |
| `camera_count` | Integer | Camera Count |  | ✓ | Number of ANPR cameras this card (license plate) is registered with. Drives the  |

#### Notable methods

- **`_compute_camera_count(self)`** - decorators: `@api.depends`

### `hr.rfid.command` <a id='model-hr-rfid-command'></a>
Python class `HrRfidCommands` in `models/hr_rfid_command.py:5`.  Model.  Inherits: `hr.rfid.command`.

#### Notable methods

- **`add_card(self, door_id, ts_id, pin_code, card_id, alarm_right)`** - decorators: `@api.model`
  - calls `super() `add_card``
  - touches: `hr.rfid.card`, `hr.rfid.door`, `hr.rfid.time.schedule`
- **`remove_card(self, door_id, pin_code, card_number=None, card_id=None)`** - decorators: `@api.model`
  - calls `super() `remove_card``
  - touches: `hr.rfid.card`, `hr.rfid.door`

### `hr.rfid.reader` <a id='model-hr-rfid-reader'></a>
Python class `HrRfidReader` in `models/hr_rfid_ctrl_reader.py:4`.  Model.  Inherits: `hr.rfid.reader`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera |  | ✓ | ANPR camera assigned to this reader. When set, the door inherits the camera link |

### `hr.rfid.door` <a id='model-hr-rfid-door'></a>
Python class `HrRfidDoor` in `models/hr_rfid_door.py:4`.  Model.  Inherits: `hr.rfid.door`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera |  | ✓ | ANPR camera bound to this door's reader (inherited via the reader). When set, ca |

#### Notable methods

- **`compute_company_id(self)`** - decorators: `@api.depends`

### `hr.rfid.card.door.rel` <a id='model-hr-rfid-card-door-rel'></a>
Python class `HrRfidCardDoorRel` in `models/hr_rfid_door.py:26`.  Model.  Inherits: `hr.rfid.card.door.rel`.

#### Notable methods

- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.card.door.rel`, `hr.rfid.door`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self, create_cmd=True)`** - decorators: -
  - calls `super() `unlink``

### `hr.rfid.event.system` <a id='model-hr-rfid-event-system'></a>
Python class `HrRfidSystemEvent` in `models/hr_rfid_event_system.py:10`.  Model.  Inherits: `hr.rfid.event.system`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera |  | ✓ | Camera to use |
| `license_plate` | Char | License Plate |  | ✓ | The license plate recognized by the camera |
| `snapshot` | Image | Snapshot |  | ✓ | The snapshot of the camera |
| `anpr_confidence` | Integer | Confidence Level |  | ✓ | The confidence level of the event |

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidEventUser` in `models/hr_rfid_event_user.py:5`.  Model.  Inherits: `hr.rfid.event.user`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `camera_id` | Many2one → \`cctv.camera\` | Camera |  | ✓ | Camera to use |
| `license_plate` | Char | License Plate |  | ✓ | The license plate recognized by the camera |
| `snapshot` | Image | Snapshot |  | ✓ | The snapshot of the camera |
| `anpr_confidence` | Integer | Confidence Level |  | ✓ | The confidence level of the event |


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `controllers/anpr_controller.py`

- **`HEARTBEAT_CLOCK_DRIFT_TOLERANCE`** *(scalar)* = `300`  - line 16

### `helpers/camera_api.py`

- **`ISAPI_VER20_NS`** *(scalar)* = `'http://www.isapi.org/ver20/XMLSchema'`  - line 24
- **`DEFAULT_HEARTBEAT`** *(scalar)* = `30`  - line 31
- **`FALLBACK_MAX_HEARTBEAT`** *(scalar)* = `180`  - line 32
- **`LP_AUDIT_CHANNEL`** *(scalar)* = `1`  - line 40
- **`LP_RECORD_LISTTYPE`** *(collection)* = `{'0': 'allowList', '1': 'blockList'}`  - line 46
- **`LP_READ_TYPE_TO_CATEGORY`** *(collection)* = `{'whiteList': 'whitelist', 'blackList': 'blacklist'}`  - line 47
- **`LP_DEFAULT_START_TIME`** *(scalar)* = `'2000-01-01T00:00:00'`  - line 51
- **`LP_DEFAULT_END_TIME`** *(scalar)* = `'2099-12-31T23:59:59'`  - line 52
- **`LP_RECORD_SHAPES`** *(collection)* = `('full', 'no_card', 'no_times')`  - line 60
- **`VEHICLE_LOGO_MAP`** *(collection)* = `{1026: 'ALFAROMEO', 1027: 'ASTONMARTIN', 1028: 'AUDI', 1030: 'PORSCHE', 1031: 'BUICK', 1032: 'BJQICHE', 1033: 'BQZHIDAO', 1034: 'BQWEIWANG', 1035: 'BQYINXIANG', 1036: 'BENZ', 1037: 'BMW', 1038: 'BAOJUN', 1039: 'BAOLONG', 1040: 'BENTLEY', 10  # ...truncated`  - line 67

### `helpers/ipcam_discovery.py`

- **`SADP_GROUP`** *(scalar)* = `'239.255.255.250'`  - line 32
- **`SADP_PORT`** *(scalar)* = `37020`  - line 33
- **`WSD_GROUP`** *(scalar)* = `'239.255.255.250'`  - line 34
- **`WSD_PORT`** *(scalar)* = `3702`  - line 35
- **`MULTICAST_LISTEN`** *(scalar)* = `3`  - line 39
- **`SWEEP_LISTEN`** *(scalar)* = `3`  - line 40
- **`RECV_BUFFER`** *(scalar)* = `65535`  - line 41
- **`MULTICAST_TTL`** *(scalar)* = `2`  - line 42
- **`BRAND_HIKVISION`** *(scalar)* = `'hikvision'`  - line 45
- **`BRAND_ONVIF_GENERIC`** *(scalar)* = `'onvif_generic'`  - line 46

### `models/cctv_camera.py`

- **`BARRIER_GATE_IN_LIST`** *(scalar)* = `'1'`  - line 25
- **`PLATE_SYNC_BATCH`** *(scalar)* = `50`  - line 38

### `models/cctv_camera_rfid_rel.py`

- **`LIST_TYPE_MAP`** *(collection)* = `{'whitelist': '0', 'blacklist': '1'}`  - line 10


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`IpcamController.parse_xml_to_dict(self, element)`** - `controllers/anpr_controller.py:36`
- **`IpcamController.validate_files(self, files)`** - `controllers/anpr_controller.py:71`
  - effects: `log_error`
- **`IpcamController.receive_anpr_event(self, camera_token=None, **kwargs)`** (`@route`) - `controllers/anpr_controller.py:84`
  - effects: `log_debug`, `log_error`, `log_info`, `log_warn`, `sudo`
  - touches: `cctv.camera`, `cctv.camera.command`
- **`BaseCamera.check_connection(self)`** - `helpers/camera_api.py:335`
- **`BaseCamera.set_http_host(self, host_ip, port_no, url_path)`** - `helpers/camera_api.py:338`
- **`BaseCamera.add_plate_to_list(self, plate_number, list_type)`** - `helpers/camera_api.py:341`
- **`BaseCamera.delete_plate_from_list(self, plate_number)`** - `helpers/camera_api.py:344`
- **`BaseCamera.barrier_gate_control(self, operation, gate_num)`** - `helpers/camera_api.py:347`
- **`BaseCamera.get_snapshot(self)`** - `helpers/camera_api.py:350`
- **`HikvisionCamera.check_connection(self)`** - `helpers/camera_api.py:382`
  - Проверява връзката към камерата и извлича основна информация за устройството.
  - effects: `http_get`, `log_debug`
- **`HikvisionCamera.get_http_host(self)`** - `helpers/camera_api.py:457`
  - Извлича текущата HTTP host конфигурация от камерата.
  - effects: `http_get`, `log_debug`, `log_error`
- **`HikvisionCamera.set_http_host(self, config)`** - `helpers/camera_api.py:515`
  - Конфигурира HTTP host настройките на камерата.
  - effects: `http_put`, `log_debug`, `log_error`, `log_warn`
- **`HikvisionCamera.get_http_host_capabilities(self)`** - `helpers/camera_api.py:677`
  - Read the allowed HTTP-host configuration ranges from the camera.
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera.add_plate_to_list(self, plate_entries)`** - `helpers/camera_api.py:762`
  - Add/update one or more plates on the camera's white/black list.
- **`HikvisionCamera.delete_plate_from_list(self, plate_entries)`** - `helpers/camera_api.py:968`
  - Remove one or more plates. Routes to the LP-audit JSON delete (DelLicensePlateAuditData) or the legacy VCL delete (VCLDelCond). Entry dict requires 'plateNum'.
- **`HikvisionCamera.search_lp_audit(self, max_results=50, position=0, search_id='0')`** - `helpers/camera_api.py:1027`
  - Read the plates currently stored on the camera's LP-audit list.
  - effects: `http_post`, `log_debug`, `log_error`
- **`HikvisionCamera.probe_vcl_capabilities(self)`** - `helpers/camera_api.py:1104`
  - SAFE read-only probe of the legacy VCL capabilities, kept verbatim.
  - effects: `http_get`
- **`HikvisionCamera.export_lp_list_xml(self)`** - `helpers/camera_api.py:1121`
  - SAFE read-only export of the plate list as the camera's own XML.
  - effects: `http_get`
- **`HikvisionCamera.barrier_gate_control(self, operation, gate_num)`** - `helpers/camera_api.py:1141`
  - Управлява бариерната врата чрез изпращане на команда към камерата.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_snapshot(self)`** - `helpers/camera_api.py:1180`
  - Извлича снимка от камерата.
  - effects: `http_get`, `log_debug`, `log_error`
- **`HikvisionCamera.get_plate_list(self, list_type='whitelist')`** - `helpers/camera_api.py:1206`
- **`HikvisionCamera.set_time_config(self, time_config)`** - `helpers/camera_api.py:1210`
  - Задава конфигурация на времето на камерата чрез /ISAPI/System/time.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_time_config(self)`** - `helpers/camera_api.py:1278`
  - Извлича конфигурацията на времето от камерата чрез /ISAPI/System/time.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.get_dst_config(self)`** - `helpers/camera_api.py:1309`
  - Прочита DST (Daylight Saving Time) настройките на камерата.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.set_dst_config(self, enable=False, mode='Offset', offset_minutes=60, start_time='2025-03-31T02:00:00', end_time='2025-10-30T03:00:00')`** - `helpers/camera_api.py:1386`
  - Активира/деактивира DST (Daylight Saving Time) в камерата.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_entrance_param(self)`** - `helpers/camera_api.py:1454`
  - Извлича конфигурацията на Entrance параметрите. Използва GET заявка към: /ISAPI/ITC/Entrance/entranceParam Връща речник с парсирана информация.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.set_entrance_param(self, config)`** - `helpers/camera_api.py:1554`
  - Задава Entrance параметрите. Параметър config трябва да е речник със структура, съответстваща на EntranceParamList. Използва PUT заявка към: /ISAPI/ITC/Entrance/entranceParam
  - effects: `http_put`, `log_error`
- **`CameraDiscoverer.parse_sadp(cls, payload, src_ip=None)`** (`@classmethod`) - `helpers/ipcam_discovery.py:121`
  - Parse a SADP ProbeMatch into a normalised record, or None if the payload is not a SADP match. *payload* is bytes or str.
  - effects: `log_debug`
- **`CameraDiscoverer.parse_wsd(cls, payload, src_ip=None)`** (`@classmethod`) - `helpers/ipcam_discovery.py:148`
  - Parse an ONVIF WS-Discovery ProbeMatch into a normalised record, or None if not a match.
- **`CameraDiscoverer.discover_sadp(self)`** - `helpers/ipcam_discovery.py:250`
- **`CameraDiscoverer.discover_onvif(self)`** - `helpers/ipcam_discovery.py:253`
- **`CameraDiscoverer.discover(self)`** - `helpers/ipcam_discovery.py:256`
  - Run every transport and merge by IP (a device seen by SADP and ONVIF is one record). SADP is probed FIRST so its richer identity — Hikvision brand, serial, activation — wins the merge over the ONVIF reply (whose brand…
  - effects: `log_info`
- **`parse_untrusted_xml(data)`** - `helpers/safe_xml.py:40`
  - Safely parse untrusted XML and return an ``lxml.etree._Element``.
- **`parse_untrusted_xml_stdlib(data)`** - `helpers/safe_xml.py:52`
  - Safely parse untrusted XML and return a stdlib ``ElementTree.Element``.

### Private helpers

- **`_hikvision_timezone(iso_offset)`** - `controllers/anpr_controller.py:19`
  - Build a Hikvision <timeZone> string from an ISO offset.
- **`IpcamController._source_ip_verification_on(self)`** - `controllers/anpr_controller.py:44`
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`IpcamController._verify_camera_source(self, camera)`** - `controllers/anpr_controller.py:48`
  - Authenticate the webhook: the request must originate from the camera's configured IP.
  - effects: `log_warn`
- **`_ver20_tag(tag)`** - `helpers/camera_api.py:63`
  - Qualify a local tag name with the ISAPI ver20 namespace.
- **`BaseCamera.__init__(self, ip_address, port, username, password, timeout=5, tz=None, record_shape='full')`** - `helpers/camera_api.py:310`
- **`BaseCamera.__enter__(self)`** - `helpers/camera_api.py:327`
- **`HikvisionCamera._extract_error(self, response_text)`** - `helpers/camera_api.py:363`
  - Опитва се да извлече детайлите за грешката от XML отговора на камерата. Ако успее, връща низ с информация за statusCode, statusString и subStatusCode. В противен случай, връща оригиналния текст.
- **`HikvisionCamera._clamp_heartbeat(value, min_v, max_v)`** (`@staticmethod`) - `helpers/camera_api.py:620`
  - Clamp a desired heartbeat (seconds) into the camera's [min, max].
- **`HikvisionCamera._parse_heartbeat_capabilities(xml_text)`** (`@staticmethod`) - `helpers/camera_api.py:633`
  - Parse the httpHosts/capabilities document for the heartbeat range.
- **`HikvisionCamera._set_child(parent, tag, text)`** (`@staticmethod`) - `helpers/camera_api.py:658`
  - Upsert a ver20-namespaced child element under ``parent``.
- **`HikvisionCamera._get_or_create_child(parent, tag)`** (`@staticmethod`) - `helpers/camera_api.py:669`
  - Return the ver20-namespaced child ``tag``, creating it if absent.
- **`HikvisionCamera._fetch_current_http_host_tree(self)`** - `helpers/camera_api.py:703`
  - Return the camera's current httpHosts/1 document as an Element.
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera._uses_lp_audit_api(self)`** - `helpers/camera_api.py:728`
  - True when this camera manages the plate list via the newer LP-audit API (Traffic channel) rather than the legacy VCL endpoint.
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera._lp_time(self, value)`** - `helpers/camera_api.py:774`
  - A validity moment in the camera's own wall clock, no zone suffix.
- **`HikvisionCamera._lp_record_info(self, entry, shape='full')`** - `helpers/camera_api.py:799`
  - Build one LicensePlateInfoList element for the JSON record upsert, mirroring the field set the camera web UI sends. Optional fields are passed as empty strings (the firmware rejects a record with keys omitted); the…
- **`HikvisionCamera._request_failed(operation, exc)`** (`@staticmethod`) - `helpers/camera_api.py:843`
  - The failure dict for a request that never got an answer.
  - effects: `log_error`, `log_warn`
- **`HikvisionCamera._lp_audit_json_ok(response)`** (`@staticmethod`) - `helpers/camera_api.py:863`
  - An LP-audit JSON endpoint reports success as HTTP 200 + statusCode 1. Returns True only when both hold.
- **`HikvisionCamera._lp_audit_add(self, plate_entries)`** - `helpers/camera_api.py:873`
  - JSON record upsert, walking the shape ladder when refused.
  - effects: `http_put`, `log_debug`, `log_error`, `log_info`, `log_warn`
- **`HikvisionCamera._vcl_add(self, plate_entries)`** - `helpers/camera_api.py:940`
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera._lp_audit_delete(self, plate_entries)`** - `helpers/camera_api.py:976`
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera._vcl_delete(self, plate_entries)`** - `helpers/camera_api.py:1001`
  - effects: `http_delete`, `log_debug`, `log_error`
- **`HikvisionCamera._parse_lp_search(body)`** (`@staticmethod`) - `helpers/camera_api.py:1065`
  - Parse an LP-audit search response into (records, total_matches).
- **`CameraDiscoverer.__init__(self, timeout=MULTICAST_LISTEN)`** - `helpers/ipcam_discovery.py:57`
- **`CameraDiscoverer._record(ip, brand, model=None, serial=None, mac=None, http_port=None, onvif_url=None, activated=None, method=None)`** (`@staticmethod`) - `helpers/ipcam_discovery.py:64`
  - One discovered device, keyed to cctv.camera field names where they map directly (ip_address/brand/model/serial_number).
- **`CameraDiscoverer._sadp_probe()`** (`@staticmethod`) - `helpers/ipcam_discovery.py:84`
- **`CameraDiscoverer._wsd_probe()`** (`@staticmethod`) - `helpers/ipcam_discovery.py:93`
- **`CameraDiscoverer._local_text(root, name)`** (`@staticmethod`) - `helpers/ipcam_discovery.py:113`
  - Find the first element whose tag (namespace stripped) equals *name*.
- **`CameraDiscoverer._open_socket(self, bind_ip, bind_port, join_group=None)`** - `helpers/ipcam_discovery.py:184`
- **`CameraDiscoverer._collect(self, sock, parse, seen, deadline)`** - `helpers/ipcam_discovery.py:203`
  - Drain replies until *deadline*, parsing each into *seen* keyed by ip.
  - effects: `log_debug`
- **`CameraDiscoverer._discover(self, group, port, probe_bytes, parse)`** - `helpers/ipcam_discovery.py:222`
  - multicast probe + IGMP-proof unicast /24 sweep; returns records.
  - effects: `log_warn`
- **`_safe_parser()`** - `helpers/safe_xml.py:18`
  - Build a hardened lxml parser.
- **`_tz_get(self)`** - `models/cctv_camera.py:29`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `view_cctv_camera_command_form` | `cctv.camera.command` | - |  | `views/cctv_camera_command_views.xml` |
| `view_cctv_camera_command_list` | `cctv.camera.command` | - |  | `views/cctv_camera_command_views.xml` |
| `view_cctv_camera_command_search` | `cctv.camera.command` | - |  | `views/cctv_camera_command_views.xml` |
| `cctv_camera_diagnostic_view_form` | `cctv.camera.diagnostic` | - |  | `views/cctv_camera_diagnostic.xml` |
| `view_cctv_camera_discovery_form` | `cctv.camera.discovery` | - |  | `views/cctv_camera_discovery_wizard.xml` |
| `cctv_camera_rfid_rel_view_tree` | `cctv.camera.rfid.rel` | - |  | `views/cctv_camera_rfid_rel.xml` |
| `view_cctv_camera_list` | `cctv.camera` | - |  | `views/cctv_camera_views.xml` |
| `view_cctv_camera_form` | `cctv.camera` | - |  | `views/cctv_camera_views.xml` |
| `view_cctv_camera_filter` | `cctv.camera` | - |  | `views/cctv_camera_views.xml` |
| `cctv_camera_view_kanban` | `cctv.camera` | - |  | `views/cctv_camera_views.xml` |
| `inherited_hr_rfid_card_view_form_cctv` | `hr.rfid.card` | - | hr_rfid.hr_rfid_card_view_form | `views/hr_rfid_card_views.xml` |
| `hr_rfid_door_view_form_camera` | `hr.rfid.door` | - | hr_rfid.hr_rfid_door_view_form | `views/hr_rfid_door.xml` |
| `hr_rfid_sys_ev_view_form_anpr_ext` | `hr.rfid.event.system` | - | hr_rfid.hr_rfid_sys_ev_view_form | `views/hr_rfid_event_system.xml` |
| `view_hr_rfid_sys_ev_list_anpr_ext` | `hr.rfid.event.system` | - | hr_rfid.hr_rfid_sys_ev_view_list | `views/hr_rfid_event_system.xml` |
| `view_hr_rfid_user_ev_form_anpr_ext` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_form | `views/hr_rfid_event_user.xml` |
| `view_hr_rfid_user_ev_list_anpr_ext` | `hr.rfid.event.user` | - | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_event_user.xml` |
| `hr_rfid_reader_view_list` | `hr.rfid.reader` | - | hr_rfid.hr_rfid_reader_view_list | `views/hr_rfid_reader.xml` |
| `hr_rfid_reader_view_form_camera` | `hr.rfid.reader` | - | hr_rfid.hr_rfid_reader_view_form | `views/hr_rfid_reader.xml` |

#### Sample XPath operations

- In `inherited_hr_rfid_card_view_form_cctv`:
  - `//div[@name='button_box'] [inside]`

- In `hr_rfid_door_view_form_camera`:
  - `//field[@name='controller_id'] [after]`
  - `//field[@name='card_type'] [attributes]`
  - `//field[@name='controller_id'] [attributes]`
  - `//field[@name='apb_mode'] [attributes]`
  - `//field[@name='lock_time'] [attributes]`

- In `hr_rfid_sys_ev_view_form_anpr_ext`:
  - `//field[@name='webstack_id'] [after]`
  - `//div[@name='button_box'] [after]`
  - `//field[@name='controller_id'] [attributes]`
  - `//field[@name='webstack_id'] [attributes]`

- In `view_hr_rfid_sys_ev_list_anpr_ext`:
  - `//list [inside]`

- In `view_hr_rfid_user_ev_form_anpr_ext`:
  - `//group[@id='card_data'] [inside]`
  - `//div[@name='button_box'] [after]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_cctv_user`, `group_cctv_manager`


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_cctv_camera_user` | `model_cctv_camera` | `polimex_ip_cam.group_cctv_user` | ✓ |  |  |  |

| `access_cctv_camera_manager` | `model_cctv_camera` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_cctv_camera_rfid_rel_user` | `model_cctv_camera_rfid_rel` | `polimex_ip_cam.group_cctv_user` | ✓ |  |  |  |

| `access_cctv_camera_rfid_rel_manager` | `model_cctv_camera_rfid_rel` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_cctv_camera_command_user` | `model_cctv_camera_command` | `polimex_ip_cam.group_cctv_user` | ✓ |  |  |  |

| `access_cctv_camera_command_manager` | `model_cctv_camera_command` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ |  | ✓ |

| `access_cctv_camera_discovery_manager` | `model_cctv_camera_discovery` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_cctv_camera_discovery_line_manager` | `model_cctv_camera_discovery_line` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_cctv_camera_diagnostic_manager` | `model_cctv_camera_diagnostic` | `polimex_ip_cam.group_cctv_manager` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_cctv_camera_multi_company`** on `model_cctv_camera` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`
- **`hr_rfid.ir_rule_hr_rfid_reader_multi_company`** on `model_hr_rfid_reader` - perms=`R`, groups=`global`, domain=`['|', '|', '|', '|', ('camera_id.company_id', 'in', company_ids), ('controller_id', '=', False), ('webstack_id.company_id', '=', False), ('webstack_id.company_id', 'in', company_ids), ('webstack_id.shared_company_ids', 'in', company_ids)]`
- **`hr_rfid.ir_rule_hr_rfid_reader_multi_company_write`** on `model_hr_rfid_reader` - perms=`WCD`, groups=`global`, domain=`['|', '|', '|', ('camera_id.company_id', 'in', company_ids), ('controller_id', '=', False), ('webstack_id.company_id', '=', False), ('webstack_id.company_id', 'in', company_ids)]`
- **`hr_rfid.ir_rule_hr_rfid_event_system_multi_company`** on `model_hr_rfid_event_system` - perms=`R`, groups=`global`, domain=`['|', '|', '|', '|', ('camera_id.company_id', 'in', company_ids), ('controller_id', '=', False), ('controller_id.webstack_id.company_id', '=', False), ('controller_id.webstack_id.company_id', 'in', company_ids), ('controller_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`hr_rfid.ir_rule_hr_rfid_event_system_multi_company_write`** on `model_hr_rfid_event_system` - perms=`WCD`, groups=`global`, domain=`['|', '|', '|', ('camera_id.company_id', 'in', company_ids), ('controller_id', '=', False), ('controller_id.webstack_id.company_id', '=', False), ('controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`hr_rfid.ir_rule_hr_rfid_event_user_multi_company`** on `model_hr_rfid_event_user` - perms=`R`, groups=`global`, domain=`[
                '|', '|',
                '|', ('employee_id.company_id', 'in', company_ids),
                ('employee_id.company_id', '=', False),
                '|', ('contact_id.company_id', 'in', company_ids),
                ('contact_id.company_id', '=', False),
                '&', ('employee_id', '=', False),
                '&', ('contact_id', '=', False),
                '|', '|', '|', '|', '|', '|',
                ('camera_id.company_id', 'in', company_ids),
                ('reader_id.camera_id.company_id', 'in', company_ids),
                ('reader_id.controller_id.webstack_id.company_id', 'in', company_ids),
                ('reader_id.controller_id.webstack_id.shared_company_ids', 'in', company_ids),
                '&', ('reader_id', '=', False), ('camera_id', '=', False),
                '&', ('reader_id.controller_id', '=', False),
                ('reader_id.camera_id', '=', False),
                ('reader_id.controller_id.webstack_id.company_id', '=', False)
            ]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `ir.actions.act_window`: 6 record(s)
- `hr.rfid.card`: 4 record(s)
- `cctv.camera`: 3 record(s)
- `cctv.camera.rfid.rel`: 3 record(s)
- `ir.actions.server`: 3 record(s)
- `cctv.camera.command`: 2 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (1): `static/tests/tours/ipcam_discovery_tour.js`



## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>Icon</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>

### Curated (docs/faq.md)

##### Plate-record write ladder (self-healing)

`HikvisionCamera._lp_audit_add` normalises validity times at the wire
boundary (`_lp_time`: UTC / 'Z'-suffixed values are converted to the
camera's own zone and sent without a suffix - the live-validated format)
and, when the firmware refuses a record as `badParameters`, retries it down
the `LP_RECORD_SHAPES` ladder: `full` -> `no_card` (linked card number
blanked) -> `no_times` (permanent window). The accepted shape is returned
as `shape_used`; the command executor persists it to
`cctv.camera.lp_record_shape` and posts one chatter note, so every later
record starts at the shape this camera speaks. The degradation is safe by
construction: entry/exit decisions are taken by the Odoo lists on each
event, not by the camera-side record details.
##### Silence during a data transfer

`hr_rfid_odoo_import` carries `no_hardware_commands=True` in its
`IMPORT_CONTEXT` for every write it makes. This module honours it in FOUR
places, and all four are needed:

| Where | Without the guard |
|---|---|
| `cctv.camera.rfid.rel.create` | every plate brought across queues an `add_plate` at the camera - a few hundred HTTP requests at cameras that are guarding a live site |
| `cctv.camera.rfid.rel.unlink` | the same, as `remove_plate` |
| `cctv.camera.create` | two readers and a door are manufactured here, while the transfer also brings the source's own - two sets in the target and no way to tell which one the historical events belong to |
| `cctv.camera.command.create` | see below |

The guard on the COMMAND itself is not belt-and-braces. `queue_send` registers
a **postcommit** hook, and a postcommit hook SURVIVES a savepoint rollback:
`rollback()` calls `cr.clear()` (`odoo/sql_db.py`), and `clear()` drops only
the PREcommit callbacks. Guarding just the callers would still let a phase that
was rolled back fire at the hardware.

`hr.rfid.card.door.rel._mirrors_to_camera()` is the fifth guard, on the mirror
that pushes card-to-door changes into a camera's plate list. It is switched off
under the same context for a second reason as well as the traffic: the mirror
CREATES `cctv.camera.rfid.rel` rows of its own, which carry no source id, and
those collide with the ones the transfer brings across - afterwards nobody can
say which link is the real one.

This is `hr_rfid`'s own convention (`hr_rfid_door.py`), and **any new write in
an importer must carry the context**. The site phase originally did not, and
its access-group cascade reached live cameras through three separate paths.

Consequence, stated in both guides: after a transfer each camera still holds
the plate list it held before, and the operator has to reload them.

Tests: `tests/test_import_guards.py` - no commands during a transfer, none on
removal either, no manufactured readers, no invented card-camera links, and the
reverse: ordinary use still sends its commands unchanged.

##### The self-test record (`cctv.camera.diagnostic`)

TransientModel holding the result of `cctv.camera.action_camera_diagnostics`
(the "Self-Test" button, `group_cctv_manager` only). The action runs the full
map of what the module uses from the camera - identity (`check_connection`,
serial compared against the record), snapshot, clock (read-only drift check
anchored in `camera.tz`), event destination (`get_http_host`), plate list
read (`search_lp_audit`, count vs `rfid_rel_ids`), the list schema as the
camera itself speaks it (`probe_vcl_capabilities` + `export_lp_list_xml` -
the export is written in exactly the schema the firmware's import accepts),
and one write round-trip with `DIAG_TEST_PLATE` ('TEST0001', added then
removed). When the minimal record passes but a record shaped like the real
data fails, the test bisects the shape (linked card number, 'Z'-suffixed
validity times, no times) and the report names the refused part, quoting the
camera verbatim. The clock check mirrors the heartbeat canon: the offset the
camera claims is dropped (the inverted Hikvision convention misstates it)
and the wall clock is compared in the camera's own zone, against the same
HEARTBEAT_CLOCK_DRIFT_TOLERANCE. The barrier is deliberately never
exercised. The report lives in the dialog only - the chatter is for
conversation, not for logs. Fields: `camera_id` (M2O `cctv.camera`),
`report` (Text).
Entries derived from the module's own code comments and bug-fix commit history.

### From `code_comments` (1)

#### TODO: - set a default image

**TODO** in `models/cctv_camera.py:124`

> - set a default image

### From `git_log` (17)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: [FIX] revert malformed manual bg.po appends (broke web translation ...

Commit `fdb5eabb0c` (2026-06-24): [FIX] revert malformed manual bg.po appends (broke web translation loading)

#### Fix: [IMP] polimex_ip_cam: fix set_time loop + clear camera connection health

Commit `da1fcd71ba` (2026-06-24): [IMP] polimex_ip_cam: fix set_time loop + clear camera connection health

#### Fix: [FIX] polimex_ip_cam: ANPR access decision from Odoo lists, not ...

Commit `ec459a58c3` (2026-06-18): [FIX] polimex_ip_cam: ANPR access decision from Odoo lists, not barrierGateCtrlType

#### Fix: [FIX] refresh layer: camera events never refreshed the realtime ...

Commit `139e5c19da` (2026-06-17): [FIX] refresh layer: camera events never refreshed the realtime dashboard

#### Fix: [IMP] polimex_ip_cam: NAT-proof camera identity + travel-direction fix

Commit `102d541b07` (2026-06-16): [IMP] polimex_ip_cam: NAT-proof camera identity + travel-direction fix

#### Fix: [FIX] polimex_ip_cam: plate-list write via capability-detected ...

Commit `616206886c` (2026-06-16): [FIX] polimex_ip_cam: plate-list write via capability-detected LP-audit API

#### Fix: [FIX] polimex_ip_cam: ANPR event identity, Hikvision timezone loop ...

Commit `4d7c8a07b8` (2026-06-15): [FIX] polimex_ip_cam: ANPR event identity, Hikvision timezone loop, search filter

#### Fix: [FIX] polimex_ip_cam: clamp ANPR HTTP-host heartbeat to camera ...

Commit `412c21eb62` (2026-06-15): [FIX] polimex_ip_cam: clamp ANPR HTTP-host heartbeat to camera capabilities

#### Fix: [FIX] ip_cam/elections: authenticate ANPR webhook & lock public ...

Commit `887641ab5a` (2026-06-12): [FIX] ip_cam/elections: authenticate ANPR webhook & lock public vote-close

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [FIX] polimex_ip_cam: Odoo 19 view inheritance (tree→list)

Commit `b5a41cb222` (2026-04-20): [FIX] polimex_ip_cam: Odoo 19 view inheritance (tree→list)

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: Fix create loop argument

Commit `9902b01b32` (2025-05-21): Fix create loop argument

#### Fix: Fix camera bug for unknown plate number handling

Commit `f30b193421` (2025-05-01): Fix camera bug for unknown plate number handling

#### Fix: Fix typo in hr_rfid_event_system.xml and update dependencies in ...

Commit `8b3982b342` (2025-04-23): Fix typo in hr_rfid_event_system.xml and update dependencies in __manifest__.py

#### Fix: Fix typo in method name for danger balloon notification

Commit `5613cc9c06` (2025-03-28): Fix typo in method name for danger balloon notification


## Source provenance <a id='provenance'></a>

- Module: `polimex_ip_cam`
- Source digest: `sha256:27cb8f32086f994e543beee81ffa8d6a8aac6c6c53f84f8e855d9dea0300534b`
- Generated at: `2026-11-23T10:05:54+00:00`
- Generator: `polimex_module_knowledge`
