---
id: polimex_ip_cam
title: IP Camera Management
module: polimex_ip_cam
module_version: 19.0.1.9.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Module for managing IP cameras via manufacturers integration integration
last_updated: '2026-08-14'
source_digest: sha256:5e04b818dc6208b79c78ff5b149171c2e492a40285ced080a2dc7bc91fc9ee86
depends:
- hr_rfid
entities:
  primary: cctv.camera
  related:
  - cctv.camera.command
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
- discovery
- integration
- line
- managing
- manufacturers
- module
- polimex
- rel
- rfid
license: AGPL-3
author: Polimex Dev Team
category: Hidden/Tools
installable: true
application: false
auto_install: false
counts:
  models: 12
  views: 16
  access_rules: 8
  record_rules: 3
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


# IP Camera Management — `polimex_ip_cam` v19.0.1.9.0

Module for managing IP cameras via manufacturers integration integration

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `polimex_ip_cam`
- **Version**: `19.0.1.9.0`
- **Category**: Hidden/Tools
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`
- **External python**: `defusedxml`

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
  end) window and ``operationType``/``operation``. The upsert merges by plate;
  success is HTTP 200 with ``statusCode 1`` — any other status is a failure, so
  a plate the camera rejected is not marked done in Odoo.
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
Python class `CctvCamera` in `models/cctv_camera.py:30`.  Model.  Inherits: `mail.thread`, `mail.activity.mixin`, `balloon.mixin`.  Description: *CCTV Camera Management*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Camera name for easy identification |
| `active` | Boolean | Active |  | ✓ | Uncheck to archive the camera. Inactive cameras no longer receive commands or ac |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the camera. Cameras are isolated per company; record rules pre |
| `tz` | Selection | Timezone |  | ✓ | The timezone of the camera. Used to display dates and times in the correct timez |
| `tz_offset` | Char | Timezone offset |  | — | UTC offset string derived from the timezone above. Sent to the camera when synch |
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
| `last_heart_beat` | Datetime | Last Heartbeat |  | ✓ | Last successful received HeartBeat from the camera |
| `reader_ids` | Many2many → \`hr.rfid.reader\` | Reader |  | ✓ | RFID reader linked to this camera |
| `door_id` | One2many → \`hr.rfid.door\` |  |  | ✓ | RFID doors whose readers are wired to this camera. Card assignments on these doo |
| `rfid_rel_ids` | One2many → \`cctv.camera.rfid.rel\` | RFID Card Relations |  | ✓ | Relations linking this camera with RFID cards and their list types |
| `rfid_card_ids` | Many2many → \`hr.rfid.card\` | RFID Cards |  | — | Flat view of every RFID card registered with this camera, across all list catego |
| `rfid_whitelist_count` | Integer | Whitelist Count |  | ✓ | Live count of plates classified as Whitelist (auto-grant). Used by the smart but |
| `rfid_blacklist_count` | Integer | Blacklist Count |  | ✓ | Live count of plates classified as Blacklist (auto-deny). Used by the smart butt |

#### Notable methods

- **`_compute_tz_offset(self)`** — decorators: `@api.depends`
- **`_compute_rfid_card_ids(self)`** — decorators: `@api.depends`
- **`_compute_list_counts(self)`** — decorators: `@api.depends`
- **`_compute_display_name(self)`** — decorators: `@api.depends`
- **`action_show_reader(self)`** — decorators: —
- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
  - effects: `sudo`
  - touches: `cctv.camera`, `hr.rfid.door`, `hr.rfid.reader`
- **`get_api(self)`** — decorators: —
- **`_resolve_anpr_camera(self, device_uuid, src_ip, source_verify_on)`** — decorators: `@api.model`
  - Map an ANPR webhook event to its cctv.camera.
  - effects: `log_error`, `log_info`
- **`action_check_connection(self)`** — decorators: —
  - When the camera brand is hikvision, instantiate the HikvisionCamera API class and use it.
  - effects: `log_info`, `log_warn`, `message_post`
- **`action_get_http_host(self)`** — decorators: —
  - Retrieve the camera's HTTP host configuration, store it in server_setup as param=value lines,
  - effects: `message_post`
- **`action_set_http_host(self)`** — decorators: —
  - Задава HTTP host конфигурация на камерата, като използва стойностите от server_setup.
  - effects: `message_post`
- **`action_get_entrance_param(self)`** — decorators: —
  - Извлича entrance параметрите от камерата и ги записва във rec.entrance_setup във формат 'param=value'.
  - effects: `message_post`
- **`action_set_entrance_param(self)`** — decorators: —
  - Задава entrance параметрите на камерата чрез API, като прочита конфигурацията от
  - effects: `message_post`
- **`action_get_snapshot(self)`** — decorators: —
  - Get a snapshot from the camera (base64 encoded) and store it in the snapshot field.
  - effects: `message_post`
- **`action_control_barrier(self, operation, gate_num)`** — decorators: —
  - Control the camera's barrier gate by sending an open/close command.
  - effects: `message_post`
- **`update_plate_in_list(self, plate_number, new_list_type)`** — decorators: —
  - Change the type in the list for a given registration number.
- **`notify_by_discuss(self, recipients, msg, attachments=None)`** — decorators: —
  - effects: `message_post`
  - touches: `discuss.channel`
- **`parse_event(self, files_data)`** — decorators: —
  - Parse the event data received from the camera.
  - effects: `log_warn`, `sudo`, `with_context`
  - touches: `hr.rfid.card`, `hr.rfid.event.system`, `hr.rfid.event.user`
- **`add_plate_to_cam(self, plate_number, list_type)`** — decorators: —
  - Add a plate number to the camera's list.
  - effects: `message_post`
- **`remove_plate_from_cam(self, plate_number)`** — decorators: —
  - Remove a plate number from the camera's list.
  - effects: `message_post`

### `cctv.camera.diagnostic` <a id='model-cctv-camera-diagnostic'></a>

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

#### Plate-record write ladder (self-healing)

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
| `camera_id` | Many2one → \`cctv.camera\` |  | ✓ | ✓ | Camera this command targets. If the camera is deleted, queued commands cascade-d |
| `retry_count` | Integer | Retry Count |  | ✓ | How many times this command has been retried. Capped at 5 — beyond that the comm |
| `state` | Selection | State |  | ✓ | Lifecycle of the command — New: queued, not yet sent. In Progress: handler is cu |

#### Notable methods

- **`_check_retry_count(self)`** — decorators: `@api.constrains`
  - effects: `raise:UserError`
- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`queue_send(self)`** — decorators: —
  - effects: `sudo`
- **`action_execute(self)`** — decorators: —
  - Изпълнява командата. Методът променя състоянието на командата на 'in_progress',
  - effects: `log_error`, `raise:UserError`

### `cctv.camera.discovery.line` <a id='model-cctv-camera-discovery-line'></a>
Python class `CctvCameraDiscoveryLine` in `models/cctv_camera_discovery_wizard.py:22`.  TransientModel (wizard).  Description: *Discovered Camera*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `discovery_id` | Many2one → \`cctv.camera.discovery\` |  |  | ✓ | Discovery run that found this camera. |
| `name` | Char | Camera Name |  | ✓ | Name the camera will be created with. Pre-filled from the model and address; edi |
| `ip_address` | Char |  |  | ✓ | Address the camera reported on the local segment. |
| `brand` | Selection |  |  | ✓ | Detected from the discovery reply (SADP/ONVIF). Generic ONVIF for non-Hikvision  |
| `model` | Char |  |  | ✓ | Hardware model as reported by the device. |
| `serial_number` | Char |  |  | ✓ | Device serial number from the discovery reply. |
| `mac_address` | Char |  |  | ✓ | Hardware (MAC) address — stable identity across DHCP changes. |
| `http_port` | Char |  |  | ✓ | HTTP/ISAPI port the device serves on (default 80). |
| `discovery_method` | Char |  |  | ✓ | Which probe found it: SADP, ONVIF, or both. |
| `activated` | Boolean |  |  | ✓ | Hikvision cameras must be activated (password set) before use. Unchecked devices |

### `cctv.camera.discovery` <a id='model-cctv-camera-discovery'></a>
Python class `CctvCameraDiscovery` in `models/cctv_camera_discovery_wizard.py:55`.  TransientModel (wizard).  Description: *Camera Discovery*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `found_camera_ids` | One2many → \`cctv.camera.discovery.line\` | Discovered Cameras |  | ✓ | Cameras found on the local network. Remove the ones you do not want, then click  |

#### Notable methods

- **`action_create_cameras(self)`** — decorators: —
  - Create a cctv.camera per remaining line, then open the camera list
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

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - super-split (super `create`): pre=— · post=`log_error`
  - effects: `log_error`
  - touches: `cctv.camera.command`
- **`unlink(self)`** — decorators: —
  - super-split (super `unlink`): pre=`log_error` · post=—
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

- **`_compute_camera_count(self)`** — decorators: `@api.depends`

### `hr.rfid.command` <a id='model-hr-rfid-command'></a>
Python class `HrRfidCommands` in `models/hr_rfid_command.py:5`.  Model.  Inherits: `hr.rfid.command`.

#### Notable methods

- **`add_card(self, door_id, ts_id, pin_code, card_id, alarm_right)`** — decorators: `@api.model`
  - calls `super() `add_card``
  - touches: `hr.rfid.card`, `hr.rfid.door`, `hr.rfid.time.schedule`
- **`remove_card(self, door_id, pin_code, card_number=None, card_id=None)`** — decorators: `@api.model`
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

- **`compute_company_id(self)`** — decorators: `@api.depends`

### `hr.rfid.card.door.rel` <a id='model-hr-rfid-card-door-rel'></a>
Python class `HrRfidCardDoorRel` in `models/hr_rfid_door.py:26`.  Model.  Inherits: `hr.rfid.card.door.rel`.

#### Notable methods

- **`create(self, vals_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.card.door.rel`, `hr.rfid.door`
- **`write(self, vals)`** — decorators: —
  - calls `super() `write``
- **`unlink(self, create_cmd=True)`** — decorators: —
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

UPPER_CASE module-level assignments — rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `controllers/anpr_controller.py`

- **`HEARTBEAT_CLOCK_DRIFT_TOLERANCE`** *(scalar)* = `300`  — line 15

### `helpers/camera_api.py`

- **`ISAPI_VER20_NS`** *(scalar)* = `'http://www.isapi.org/ver20/XMLSchema'`  — line 14
- **`DEFAULT_HEARTBEAT`** *(scalar)* = `30`  — line 21
- **`FALLBACK_MAX_HEARTBEAT`** *(scalar)* = `180`  — line 22
- **`LP_AUDIT_CHANNEL`** *(scalar)* = `1`  — line 30
- **`LP_RECORD_LISTTYPE`** *(collection)* = `{'0': 'allowList', '1': 'blockList'}`  — line 36
- **`LP_READ_TYPE_TO_CATEGORY`** *(collection)* = `{'whiteList': 'whitelist', 'blackList': 'blacklist'}`  — line 37
- **`LP_DEFAULT_START_TIME`** *(scalar)* = `'2000-01-01T00:00:00'`  — line 41
- **`LP_DEFAULT_END_TIME`** *(scalar)* = `'2099-12-31T23:59:59'`  — line 42
- **`VEHICLE_LOGO_MAP`** *(collection)* = `{1026: 'ALFAROMEO', 1027: 'ASTONMARTIN', 1028: 'AUDI', 1030: 'PORSCHE', 1031: 'BUICK', 1032: 'BJQICHE', 1033: 'BQZHIDAO', 1034: 'BQWEIWANG', 1035: 'BQYINXIANG', 1036: 'BENZ', 1037: 'BMW', 1038: 'BAOJUN', 1039: 'BAOLONG', 1040: 'BENTLEY', 10  # ...truncated`  — line 49

### `helpers/ipcam_discovery.py`

- **`SADP_GROUP`** *(scalar)* = `'239.255.255.250'`  — line 30
- **`SADP_PORT`** *(scalar)* = `37020`  — line 31
- **`WSD_GROUP`** *(scalar)* = `'239.255.255.250'`  — line 32
- **`WSD_PORT`** *(scalar)* = `3702`  — line 33
- **`MULTICAST_LISTEN`** *(scalar)* = `3`  — line 37
- **`SWEEP_LISTEN`** *(scalar)* = `3`  — line 38
- **`RECV_BUFFER`** *(scalar)* = `65535`  — line 39
- **`MULTICAST_TTL`** *(scalar)* = `2`  — line 40
- **`BRAND_HIKVISION`** *(scalar)* = `'hikvision'`  — line 43
- **`BRAND_ONVIF_GENERIC`** *(scalar)* = `'onvif_generic'`  — line 44

### `models/cctv_camera.py`

- **`BARRIER_GATE_IN_LIST`** *(scalar)* = `'1'`  — line 22

### `models/cctv_camera_rfid_rel.py`

- **`LIST_TYPE_MAP`** *(collection)* = `{'whitelist': '0', 'blacklist': '1'}`  — line 10

### `tests/test_discovery.py`

- **`SADP_MATCH`** *(scalar)* = `'<?xml version="1.0" encoding="utf-8"?><ProbeMatch><Uuid>X</Uuid><Types>inquiry</Types><IPv4Address>192.168.74.76</IPv4Address><DeviceDescription>DS-TCG406-E</DeviceDescription><DeviceSN>DS-TCG406-E 20250322AIFX8693470</DeviceSN><MAC>e8-a0-`  — line 7
- **`SADP_INACTIVE`** *(expression)* = `SADP_MATCH.replace('<Activated>true</Activated>', '<Activated>false</Activated>')`  — line 17
- **`WSD_MATCH_HIK`** *(scalar)* = `'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope"><SOAP-ENV:Body><d:ProbeMatches xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"><d:ProbeMatch><d:Types>dn:NetworkVideoTransmitter</d:Types><d:Scopes>onvif`  — line 19
- **`WSD_MATCH_GENERIC`** *(expression)* = `WSD_MATCH_HIK.replace('/name/HIKVISION', '/name/AcmeCam').replace('/hardware/DS-TCG406-E', '/hardware/AC-9000').replace('192.168.74.57', '192.168.74.90')`  — line 31

### `tests/test_discovery_tour.py`

- **`CANNED`** *(collection)* = `[{'ip_address': '192.168.74.76', 'brand': 'hikvision', 'model': 'DS-TCG406-E', 'serial_number': 'DS-TCG406-E 20250322AIFX8693470', 'mac_address': 'e8-a0-ed-30-57-1b', 'http_port': '88', 'activated': True, 'discovery_method': 'SADP'}, {'ip_a  # ...truncated`  — line 7

### `tests/test_http_host_config.py`

- **`NS`** *(collection)* = `{'ns': 'http://www.isapi.org/ver20/XMLSchema'}`  — line 8
- **`CAPABILITIES_XML`** *(scalar)* = `'<HttpHostNotificationCap version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema"><id min="1" max="1"/><SubscribeEvent><heartbeat min="0" max="180">20</heartbeat><eventMode opt="all,alarm,none"/></SubscribeEvent></HttpHostNotificationCap`  — line 13
- **`CURRENT_HTTP_HOST_XML`** *(scalar)* = `'<HttpHostNotification version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema"><id>1</id><url>/</url><protocolType>HTTP</protocolType><parameterFormatType>XML</parameterFormatType><addressingFormatType>ipaddress</addressingFormatType><ip`  — line 28


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`IpcamController.parse_xml_to_dict(self, element)`** — `controllers/anpr_controller.py:35`
- **`IpcamController.validate_files(self, files)`** — `controllers/anpr_controller.py:70`
  - effects: `log_error`
- **`IpcamController.receive_anpr_event(self, camera_token=None, **kwargs)`** (`@route`) — `controllers/anpr_controller.py:83`
  - effects: `log_debug`, `log_error`, `log_info`, `log_warn`, `sudo`
  - touches: `cctv.camera`, `cctv.camera.command`
- **`BaseCamera.check_connection(self)`** — `helpers/camera_api.py:307`
- **`BaseCamera.set_http_host(self, host_ip, port_no, url_path)`** — `helpers/camera_api.py:310`
- **`BaseCamera.add_plate_to_list(self, plate_number, list_type)`** — `helpers/camera_api.py:313`
- **`BaseCamera.delete_plate_from_list(self, plate_number)`** — `helpers/camera_api.py:316`
- **`BaseCamera.barrier_gate_control(self, operation, gate_num)`** — `helpers/camera_api.py:319`
- **`BaseCamera.get_snapshot(self)`** — `helpers/camera_api.py:322`
- **`HikvisionCamera.check_connection(self)`** — `helpers/camera_api.py:354`
  - Проверява връзката към камерата и извлича основна информация за устройството.
  - effects: `http_get`, `log_debug`, `log_error`
- **`HikvisionCamera.get_http_host(self)`** — `helpers/camera_api.py:420`
  - Извлича текущата HTTP host конфигурация от камерата.
  - effects: `http_get`, `log_debug`, `log_error`
- **`HikvisionCamera.set_http_host(self, config)`** — `helpers/camera_api.py:478`
  - Конфигурира HTTP host настройките на камерата.
  - effects: `http_put`, `log_debug`, `log_error`, `log_warn`
- **`HikvisionCamera.get_http_host_capabilities(self)`** — `helpers/camera_api.py:640`
  - Read the allowed HTTP-host configuration ranges from the camera.
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera.add_plate_to_list(self, plate_entries)`** — `helpers/camera_api.py:716`
  - Add/update one or more plates on the camera's white/black list.
- **`HikvisionCamera.delete_plate_from_list(self, plate_entries)`** — `helpers/camera_api.py:821`
  - Remove one or more plates. Routes to the LP-audit JSON delete
- **`HikvisionCamera.search_lp_audit(self, max_results=50, position=0, search_id='0')`** — `helpers/camera_api.py:878`
  - Read the plates currently stored on the camera's LP-audit list.
  - effects: `http_post`, `log_debug`, `log_error`
- **`HikvisionCamera.barrier_gate_control(self, operation, gate_num)`** — `helpers/camera_api.py:955`
  - Управлява бариерната врата чрез изпращане на команда към камерата.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_snapshot(self)`** — `helpers/camera_api.py:994`
  - Извлича снимка от камерата.
  - effects: `http_get`, `log_debug`, `log_error`
- **`HikvisionCamera.get_plate_list(self, list_type='whitelist')`** — `helpers/camera_api.py:1020`
- **`HikvisionCamera.set_time_config(self, time_config)`** — `helpers/camera_api.py:1024`
  - Задава конфигурация на времето на камерата чрез /ISAPI/System/time.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_time_config(self)`** — `helpers/camera_api.py:1092`
  - Извлича конфигурацията на времето от камерата чрез /ISAPI/System/time.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.get_dst_config(self)`** — `helpers/camera_api.py:1123`
  - Прочита DST (Daylight Saving Time) настройките на камерата.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.set_dst_config(self, enable=False, mode='Offset', offset_minutes=60, start_time='2025-03-31T02:00:00', end_time='2025-10-30T03:00:00')`** — `helpers/camera_api.py:1200`
  - Активира/деактивира DST (Daylight Saving Time) в камерата.
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera.get_entrance_param(self)`** — `helpers/camera_api.py:1268`
  - Извлича конфигурацията на Entrance параметрите.
  - effects: `http_get`, `log_error`
- **`HikvisionCamera.set_entrance_param(self, config)`** — `helpers/camera_api.py:1368`
  - Задава Entrance параметрите.
  - effects: `http_put`, `log_error`
- **`CameraDiscoverer.parse_sadp(cls, payload, src_ip=None)`** (`@classmethod`) — `helpers/ipcam_discovery.py:119`
  - Parse a SADP ProbeMatch into a normalised record, or None if the
  - effects: `log_debug`
- **`CameraDiscoverer.parse_wsd(cls, payload, src_ip=None)`** (`@classmethod`) — `helpers/ipcam_discovery.py:146`
  - Parse an ONVIF WS-Discovery ProbeMatch into a normalised record, or
- **`CameraDiscoverer.discover_sadp(self)`** — `helpers/ipcam_discovery.py:248`
- **`CameraDiscoverer.discover_onvif(self)`** — `helpers/ipcam_discovery.py:251`
- **`CameraDiscoverer.discover(self)`** — `helpers/ipcam_discovery.py:254`
  - Run every transport and merge by IP (a device seen by SADP and ONVIF
  - effects: `log_info`
- **`simulate_request(log_file_path, controller_url)`** — `helpers/sim_event_from_camera.py:8`
  - effects: `http_post`
- **`migrate(cr, version)`** — `migrations/19.0.1.5.0/post-migration.py:6`
  - Collapse the legacy 5-bucket list_category down to the two buckets the
  - effects: `log_info`, `sql`
- **`TestAnprAccessDecision.setUpClass(cls)`** (`@classmethod`) — `tests/test_anpr_access_decision.py:16`
  - calls `super()`
  - touches: `cctv.camera`
- **`TestAnprAccessDecision.test_whitelist_plate_is_granted(self)`** — `tests/test_anpr_access_decision.py:60`
- **`TestAnprAccessDecision.test_blacklist_plate_is_denied(self)`** — `tests/test_anpr_access_decision.py:71`
- **`TestAnprAccessDecision.test_known_card_without_relation_is_denied(self)`** — `tests/test_anpr_access_decision.py:79`
- **`TestAnprAccessDecision.test_blacklist_wins_over_whitelist_conflict(self)`** — `tests/test_anpr_access_decision.py:89`
- **`TestAnprAccessDecision.test_barrier_ctrl_type_does_not_override_blacklist(self)`** — `tests/test_anpr_access_decision.py:102`
- **`TestAnprWebhookAuth.test_forged_event_from_wrong_source_is_rejected(self)`** — `tests/test_anpr_auth.py:54`
  - Default (verification ON): a request whose source IP does not match
- **`TestAnprWebhookAuth.test_event_from_matching_source_is_accepted(self)`** — `tests/test_anpr_auth.py:63`
  - A request whose source IP matches the camera's configured IP is
- **`TestAnprWebhookAuth.test_verification_off_allows_any_source(self)`** — `tests/test_anpr_auth.py:72`
  - With the system parameter disabled (NAT escape hatch), any source is
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`TestAnprDirection.setUpClass(cls)`** (`@classmethod`) — `tests/test_anpr_direction.py:14`
  - calls `super()`
  - touches: `cctv.camera`
- **`TestAnprDirection.test_forward_uses_in_reader(self)`** — `tests/test_anpr_direction.py:44`
  - touches: `hr.rfid.event.user`
- **`TestAnprDirection.test_reverse_uses_out_reader(self)`** — `tests/test_anpr_direction.py:53`
  - touches: `hr.rfid.event.user`
- **`TestAnprDirection.test_system_event_records_real_direction(self)`** — `tests/test_anpr_direction.py:63`
  - touches: `hr.rfid.event.system`
- **`TestHttpHostUrlToken.setUp(self)`** — `tests/test_anpr_direction.py:79`
  - calls `super()`
  - touches: `cctv.camera`
- **`TestHttpHostUrlToken.test_url_embeds_sub_serial(self)`** — `tests/test_anpr_direction.py:87`
- **`TestHikvisionTimezone.test_positive_offset_is_inverted(self)`** — `tests/test_anpr_identity_time.py:10`
- **`TestHikvisionTimezone.test_negative_offset_is_inverted(self)`** — `tests/test_anpr_identity_time.py:15`
- **`TestHikvisionTimezone.test_half_hour_offset(self)`** — `tests/test_anpr_identity_time.py:18`
- **`TestHikvisionTimezone.test_utc_and_empty(self)`** — `tests/test_anpr_identity_time.py:21`
- **`TestResolveAnprCamera.test_match_by_sub_serial(self)`** — `tests/test_anpr_identity_time.py:45`
  - touches: `cctv.camera`
- **`TestResolveAnprCamera.test_legacy_match_by_full_serial(self)`** — `tests/test_anpr_identity_time.py:50`
  - touches: `cctv.camera`
- **`TestResolveAnprCamera.test_match_by_trusted_ip_learns_uuid(self)`** — `tests/test_anpr_identity_time.py:56`
  - touches: `cctv.camera`
- **`TestResolveAnprCamera.test_no_ip_fallback_when_source_verify_off(self)`** — `tests/test_anpr_identity_time.py:64`
  - touches: `cctv.camera`
- **`TestResolveAnprCamera.test_no_match_returns_empty(self)`** — `tests/test_anpr_identity_time.py:71`
  - touches: `cctv.camera`
- **`TestResolveAnprCamera.test_ambiguous_sub_serial_refuses_to_guess(self)`** — `tests/test_anpr_identity_time.py:76`
  - touches: `cctv.camera`
- **`TestAnprSsrf.setUp(self)`** — `tests/test_anpr_ssrf.py:19`
  - super-split (super): pre=— · post=`sudo`
  - effects: `sudo`
  - touches: `cctv.camera`, `ir.config_parameter`
- **`TestAnprSsrf.test_event_body_ip_does_not_overwrite_stored_ip(self)`** — `tests/test_anpr_ssrf.py:50`
  - A forged ANPR event reporting an attacker IP must NOT change the
- **`TestAnprSsrf.test_unknown_device_uuid_is_not_found(self)`** — `tests/test_anpr_ssrf.py:66`
  - An event for an unknown camera UUID is rejected (404), creating no
- **`TestAnprSsrf.test_missing_datetime_does_not_crash_webhook(self)`** — `tests/test_anpr_ssrf.py:78`
  - An ANPR event without a dateTime must not 500 the public webhook —
  - effects: `sudo`
  - touches: `hr.rfid.event.system`
- **`TestDiscoveryParsers.test_parse_sadp(self)`** — `tests/test_discovery.py:43`
- **`TestDiscoveryParsers.test_parse_sadp_inactive(self)`** — `tests/test_discovery.py:54`
- **`TestDiscoveryParsers.test_parse_sadp_rejects_non_match(self)`** — `tests/test_discovery.py:57`
- **`TestDiscoveryParsers.test_parse_wsd_hikvision(self)`** — `tests/test_discovery.py:61`
- **`TestDiscoveryParsers.test_parse_wsd_generic_brand(self)`** — `tests/test_discovery.py:69`
- **`TestDiscoveryParsers.test_parse_wsd_rejects_non_match(self)`** — `tests/test_discovery.py:75`
- **`TestDiscoveryWizard.setUpClass(cls)`** (`@classmethod`) — `tests/test_discovery.py:86`
  - calls `super()`
  - touches: `cctv.camera`, `cctv.camera.discovery`
- **`TestDiscoveryWizard.test_wizard_lists_and_creates(self)`** — `tests/test_discovery.py:106`
- **`TestDiscoveryWizard.test_wizard_dedup_skips_registered(self)`** — `tests/test_discovery.py:124`
- **`TestDiscoveryWizard.test_wizard_brand_agnostic(self)`** — `tests/test_discovery.py:136`
- **`TestDiscoveryWizard.test_wizard_rejects_out_of_range_port(self)`** — `tests/test_discovery.py:142`
- **`TestDiscoveryWizard.test_wizard_empty_closes(self)`** — `tests/test_discovery.py:149`
- **`TestDiscoveryTour.test_discovery_wizard_tour(self)`** — `tests/test_discovery_tour.py:24`
  - touches: `cctv.camera`
- **`TestHeartbeatClamp.test_clamp_above_max_returns_max(self)`** — `tests/test_http_host_config.py:59`
- **`TestHeartbeatClamp.test_clamp_below_min_returns_min(self)`** — `tests/test_http_host_config.py:62`
- **`TestHeartbeatClamp.test_clamp_within_range_is_unchanged(self)`** — `tests/test_http_host_config.py:65`
- **`TestHeartbeatClamp.test_clamp_non_numeric_uses_default(self)`** — `tests/test_http_host_config.py:68`
- **`TestHeartbeatClamp.test_clamp_none_default_then_clamped_up_to_min(self)`** — `tests/test_http_host_config.py:73`
- **`TestHeartbeatClamp.test_parse_capabilities_reads_min_max(self)`** — `tests/test_http_host_config.py:77`
- **`TestHeartbeatClamp.test_parse_capabilities_missing_element_returns_none(self)`** — `tests/test_http_host_config.py:83`
- **`TestHeartbeatClamp.test_parse_capabilities_missing_attrs_returns_none(self)`** — `tests/test_http_host_config.py:91`
- **`TestSetHttpHostBuild.setUp(self)`** — `tests/test_http_host_config.py:104`
  - calls `super()`
- **`TestSetHttpHostBuild.test_clamps_heartbeat_and_preserves_check_response(self)`** — `tests/test_http_host_config.py:136`
- **`TestSetHttpHostBuild.test_capabilities_unreadable_uses_conservative_cap(self)`** — `tests/test_http_host_config.py:156`
- **`TestSetHttpHostBuild.test_current_get_fails_falls_back_to_rebuild(self)`** — `tests/test_http_host_config.py:167`
- **`TestSetHttpHostBuild.test_config_check_response_overrides_camera_value(self)`** — `tests/test_http_host_config.py:183`
- **`TestGetHttpHost.setUp(self)`** — `tests/test_http_host_config.py:212`
  - calls `super()`
- **`TestGetHttpHost.test_get_http_host_parses_check_response_enabled(self)`** — `tests/test_http_host_config.py:216`
- **`TestListCategoryTwoBuckets.setUpClass(cls)`** (`@classmethod`) — `tests/test_list_category.py:12`
  - calls `super()`
  - touches: `cctv.camera`
- **`TestListCategoryTwoBuckets.test_selection_has_exactly_two_values(self)`** — `tests/test_list_category.py:40`
  - touches: `cctv.camera.rfid.rel`
- **`TestListCategoryTwoBuckets.test_default_is_whitelist(self)`** — `tests/test_list_category.py:49`
  - touches: `cctv.camera.rfid.rel`
- **`TestListCategoryTwoBuckets.test_compute_list_counts(self)`** — `tests/test_list_category.py:55`
- **`TestListCategoryTwoBuckets.test_list_type_mapping_is_zero_one(self)`** — `tests/test_list_category.py:65`
- **`TestLpRecordBody.test_listtype_and_plate_mapping(self)`** — `tests/test_lp_audit_api.py:27`
- **`TestLpRecordBody.test_default_validity_window(self)`** — `tests/test_lp_audit_api.py:34`
- **`TestLpRecordBody.test_cardno_and_times_passthrough(self)`** — `tests/test_lp_audit_api.py:40`
- **`TestLpAuditRouting.setUp(self)`** — `tests/test_lp_audit_api.py:57`
  - calls `super()`
- **`TestLpAuditRouting.test_add_uses_lp_audit_record_when_vcl_unsupported(self)`** — `tests/test_lp_audit_api.py:69`
- **`TestLpAuditRouting.test_add_reports_failure_on_non_success_status(self)`** — `tests/test_lp_audit_api.py:90`
- **`TestLpAuditRouting.test_add_uses_vcl_when_supported(self)`** — `tests/test_lp_audit_api.py:103`
- **`TestLpAuditRouting.test_search_lp_audit_posts_and_parses_real_response(self)`** — `tests/test_lp_audit_api.py:140`
- **`TestLpAuditRouting.test_search_lp_audit_unparseable_body_is_empty(self)`** — `tests/test_lp_audit_api.py:166`
- **`TestLpAuditRouting.test_delete_uses_del_endpoint_on_lp_audit(self)`** — `tests/test_lp_audit_api.py:173`
- **`TestCameraEventCompanyResolution.setUpClass(cls)`** (`@classmethod`) — `tests/test_refresh_company.py:16`
  - calls `super()`
  - touches: `cctv.camera`
- **`TestCameraEventCompanyResolution.setUp(self)`** — `tests/test_refresh_company.py:26`
  - calls `super()`
  - touches: `hr.rfid.event.system`
- **`TestCameraEventCompanyResolution.test_system_event_resolves_company_via_camera_door(self)`** — `tests/test_refresh_company.py:44`
  - touches: `hr.rfid.event.system`
- **`TestCameraEventCompanyResolution.test_system_event_create_emits_refresh_notice(self)`** — `tests/test_refresh_company.py:55`
  - touches: `bus.bus`
- **`TestPolimexIpCamSmoke.setUpClass(cls)`** (`@classmethod`) — `tests/test_smoke.py:9`
  - calls `super()`
- **`TestPolimexIpCamSmoke.test_create_camera(self)`** — `tests/test_smoke.py:24`
- **`TestPolimexIpCamSmoke.test_camera_command_create(self)`** — `tests/test_smoke.py:30`
  - touches: `cctv.camera.command`
- **`TestPolimexIpCamSmoke.test_rfid_card_extension_loaded(self)`** — `tests/test_smoke.py:39`
  - touches: `hr.rfid.card`, `res.partner`
- **`TestPolimexIpCamSmoke.test_camera_tz_default_is_set(self)`** — `tests/test_smoke.py:51`

### Private helpers

- **`_hikvision_timezone(iso_offset)`** — `controllers/anpr_controller.py:18`
  - Build a Hikvision <timeZone> string from an ISO offset.
- **`IpcamController._source_ip_verification_on(self)`** — `controllers/anpr_controller.py:43`
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`IpcamController._verify_camera_source(self, camera)`** — `controllers/anpr_controller.py:47`
  - Authenticate the webhook: the request must originate from the
  - effects: `log_warn`
- **`_ver20_tag(tag)`** — `helpers/camera_api.py:45`
  - Qualify a local tag name with the ISAPI ver20 namespace.
- **`BaseCamera.__init__(self, ip_address, port, username, password, timeout=5)`** — `helpers/camera_api.py:292`
- **`BaseCamera.__enter__(self)`** — `helpers/camera_api.py:299`
- **`HikvisionCamera._extract_error(self, response_text)`** — `helpers/camera_api.py:335`
  - Опитва се да извлече детайлите за грешката от XML отговора на камерата.
- **`HikvisionCamera._clamp_heartbeat(value, min_v, max_v)`** (`@staticmethod`) — `helpers/camera_api.py:583`
  - Clamp a desired heartbeat (seconds) into the camera's [min, max].
- **`HikvisionCamera._parse_heartbeat_capabilities(xml_text)`** (`@staticmethod`) — `helpers/camera_api.py:596`
  - Parse the httpHosts/capabilities document for the heartbeat range.
- **`HikvisionCamera._set_child(parent, tag, text)`** (`@staticmethod`) — `helpers/camera_api.py:621`
  - Upsert a ver20-namespaced child element under ``parent``.
- **`HikvisionCamera._get_or_create_child(parent, tag)`** (`@staticmethod`) — `helpers/camera_api.py:632`
  - Return the ver20-namespaced child ``tag``, creating it if absent.
- **`HikvisionCamera._fetch_current_http_host_tree(self)`** — `helpers/camera_api.py:666`
  - Return the camera's current httpHosts/1 document as an Element.
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera._uses_lp_audit_api(self)`** — `helpers/camera_api.py:691`
  - True when this camera manages the plate list via the newer LP-audit
  - effects: `http_get`, `log_warn`
- **`HikvisionCamera._lp_record_info(entry)`** (`@staticmethod`) — `helpers/camera_api.py:729`
  - Build one LicensePlateInfoList element for the JSON record upsert,
- **`HikvisionCamera._lp_audit_json_ok(response)`** (`@staticmethod`) — `helpers/camera_api.py:762`
  - An LP-audit JSON endpoint reports success as HTTP 200 + statusCode 1.
- **`HikvisionCamera._lp_audit_add(self, plate_entries)`** — `helpers/camera_api.py:772`
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera._vcl_add(self, plate_entries)`** — `helpers/camera_api.py:792`
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera._lp_audit_delete(self, plate_entries)`** — `helpers/camera_api.py:829`
  - effects: `http_put`, `log_debug`, `log_error`
- **`HikvisionCamera._vcl_delete(self, plate_entries)`** — `helpers/camera_api.py:851`
  - effects: `http_delete`, `log_debug`, `log_error`
- **`HikvisionCamera._parse_lp_search(body)`** (`@staticmethod`) — `helpers/camera_api.py:916`
  - Parse an LP-audit search response into (records, total_matches).
- **`CameraDiscoverer.__init__(self, timeout=MULTICAST_LISTEN)`** — `helpers/ipcam_discovery.py:55`
- **`CameraDiscoverer._record(ip, brand, model=None, serial=None, mac=None, http_port=None, onvif_url=None, activated=None, method=None)`** (`@staticmethod`) — `helpers/ipcam_discovery.py:62`
  - One discovered device, keyed to cctv.camera field names where they
- **`CameraDiscoverer._sadp_probe()`** (`@staticmethod`) — `helpers/ipcam_discovery.py:82`
- **`CameraDiscoverer._wsd_probe()`** (`@staticmethod`) — `helpers/ipcam_discovery.py:91`
- **`CameraDiscoverer._local_text(root, name)`** (`@staticmethod`) — `helpers/ipcam_discovery.py:111`
  - Find the first element whose tag (namespace stripped) equals *name*.
- **`CameraDiscoverer._open_socket(self, bind_ip, bind_port, join_group=None)`** — `helpers/ipcam_discovery.py:182`
- **`CameraDiscoverer._collect(self, sock, parse, seen, deadline)`** — `helpers/ipcam_discovery.py:201`
  - Drain replies until *deadline*, parsing each into *seen* keyed by ip.
  - effects: `log_debug`
- **`CameraDiscoverer._discover(self, group, port, probe_bytes, parse)`** — `helpers/ipcam_discovery.py:220`
  - multicast probe + IGMP-proof unicast /24 sweep; returns records.
  - effects: `log_warn`
- **`_tz_get(self)`** — `models/cctv_camera.py:26`
- **`TestAnprAccessDecision._files(self, plate, barrier='0')`** — `tests/test_anpr_access_decision.py:26`
- **`TestAnprAccessDecision._card(self, plate)`** — `tests/test_anpr_access_decision.py:42`
  - touches: `hr.rfid.card`, `res.partner`
- **`TestAnprAccessDecision._rel(self, card, category)`** — `tests/test_anpr_access_decision.py:49`
  - touches: `cctv.camera.rfid.rel`
- **`TestAnprAccessDecision._last_user_event(self, plate)`** — `tests/test_anpr_access_decision.py:55`
  - touches: `hr.rfid.event.user`
- **`TestAnprWebhookAuth._make_camera(self, ip)`** — `tests/test_anpr_auth.py:19`
  - touches: `cctv.camera`
- **`TestAnprWebhookAuth._anpr_xml(self)`** — `tests/test_anpr_auth.py:31`
- **`TestAnprWebhookAuth._post(self)`** — `tests/test_anpr_auth.py:42`
- **`TestAnprWebhookAuth._events_for(self, camera)`** — `tests/test_anpr_auth.py:48`
  - effects: `sudo`
  - touches: `hr.rfid.event.system`, `hr.rfid.event.user`
- **`TestAnprDirection._files(self, plate, direction)`** — `tests/test_anpr_direction.py:24`
- **`TestAnprDirection._card(self, plate)`** — `tests/test_anpr_direction.py:37`
  - touches: `hr.rfid.card`, `res.partner`
- **`TestResolveAnprCamera._make_camera(self, name, ip, serial=False, sub=False)`** — `tests/test_anpr_identity_time.py:33`
  - touches: `cctv.camera`
- **`TestAnprSsrf._anpr_xml(self, device_uuid, reported_ip)`** — `tests/test_anpr_ssrf.py:38`
- **`TestDiscoveryWizard._results(self)`** — `tests/test_discovery.py:92`
- **`TestDiscoveryWizard._wizard(self, results)`** — `tests/test_discovery.py:103`
  - effects: `with_context`
- **`_FakeResponse.__init__(self, status_code=200, text='')`** — `tests/test_http_host_config.py:49`
- **`TestSetHttpHostBuild._dispatch_get(capabilities=None, current=None)`** (`@staticmethod`) — `tests/test_http_host_config.py:109`
  - Return a requests.get side_effect that answers by URL.
- **`TestSetHttpHostBuild._run_set(self, get_side_effect)`** — `tests/test_http_host_config.py:121`
- **`TestListCategoryTwoBuckets._make_plate_rel(self, plate, category)`** — `tests/test_list_category.py:26`
  - touches: `cctv.camera.rfid.rel`, `hr.rfid.card`, `res.partner`
- **`_Resp.__init__(self, status_code=200, text='', content=b'')`** — `tests/test_lp_audit_api.py:14`
- **`TestLpAuditRouting._vcl_caps(self, supported)`** — `tests/test_lp_audit_api.py:61`
- **`TestCameraEventCompanyResolution._files(self, plate)`** — `tests/test_refresh_company.py:33`
- **`TestPolimexIpCamSmoke._make_camera(self, name='Cam-1', ip='10.0.0.10')`** — `tests/test_smoke.py:13`
  - touches: `cctv.camera`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `view_cctv_camera_command_form` | `cctv.camera.command` | — |  | `views/cctv_camera_command_views.xml` |
| `view_cctv_camera_command_list` | `cctv.camera.command` | — |  | `views/cctv_camera_command_views.xml` |
| `view_cctv_camera_command_search` | `cctv.camera.command` | — |  | `views/cctv_camera_command_views.xml` |
| `view_cctv_camera_discovery_form` | `cctv.camera.discovery` | — |  | `views/cctv_camera_discovery_wizard.xml` |
| `cctv_camera_rfid_rel_view_tree` | `cctv.camera.rfid.rel` | — |  | `views/cctv_camera_rfid_rel.xml` |
| `view_cctv_camera_list` | `cctv.camera` | — |  | `views/cctv_camera_views.xml` |
| `view_cctv_camera_form` | `cctv.camera` | — |  | `views/cctv_camera_views.xml` |
| `view_cctv_camera_filter` | `cctv.camera` | — |  | `views/cctv_camera_views.xml` |
| `inherited_hr_rfid_card_view_form_cctv` | `hr.rfid.card` | — | hr_rfid.hr_rfid_card_view_form | `views/hr_rfid_card_views.xml` |
| `hr_rfid_door_view_form_camera` | `hr.rfid.door` | — | hr_rfid.hr_rfid_door_view_form | `views/hr_rfid_door.xml` |
| `hr_rfid_sys_ev_view_form_anpr_ext` | `hr.rfid.event.system` | — | hr_rfid.hr_rfid_sys_ev_view_form | `views/hr_rfid_event_system.xml` |
| `view_hr_rfid_sys_ev_list_anpr_ext` | `hr.rfid.event.system` | — | hr_rfid.hr_rfid_sys_ev_view_list | `views/hr_rfid_event_system.xml` |
| `view_hr_rfid_user_ev_form_anpr_ext` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_form | `views/hr_rfid_event_user.xml` |
| `view_hr_rfid_user_ev_list_anpr_ext` | `hr.rfid.event.user` | — | hr_rfid.hr_rfid_user_ev_view_list | `views/hr_rfid_event_user.xml` |
| `hr_rfid_reader_view_list` | `hr.rfid.reader` | — | hr_rfid.hr_rfid_reader_view_list | `views/hr_rfid_reader.xml` |
| `hr_rfid_reader_view_form_camera` | `hr.rfid.reader` | — | hr_rfid.hr_rfid_reader_view_form | `views/hr_rfid_reader.xml` |

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


### Access rights (ir.model.access)

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


### Record rules (ir.rule)

- **`ir_rule_cctv_camera_multi_company`** on `model_cctv_camera` — perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`
- **`hr_rfid.ir_rule_hr_rfid_reader_multi_company`** on `model_hr_rfid_reader` — perms=`RWCD`, groups=`global`, domain=`['|', ('camera_id.company_id', 'in', company_ids), ('webstack_id.company_id',
                'in', company_ids)]
            `
- **`hr_rfid.ir_rule_hr_rfid_event_system_multi_company`** on `model_hr_rfid_event_system` — perms=`RWCD`, groups=`global`, domain=`['|', ('camera_id.company_id', 'in', company_ids), ('controller_id.webstack_id.company_id', 'in', company_ids)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `cctv.camera`: 1 record(s)
- `hr.rfid.card`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


## Diagrams & Screenshots <a id='images'></a>
Visual assets shipped with the module. Captions generated by VLM; review before production.

<figure id='fig-static-description-icon-png'>

![Icon](static/description/icon.png)

<figcaption>[Placeholder caption] Image at `icon.png`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`

<figure id='fig-static-description-icon-svg'>

![Icon](static/description/icon.svg)

<figcaption>[Placeholder caption] Image at `icon.svg`. A vision-language model has not been configured yet. Replace this caption with a real description (VLM-generated or manual) to improve retrieval quality.</figcaption>
</figure>

> Tags: `icon`


## FAQ & Troubleshooting <a id='faq'></a>
Candidate entries mined from code comments, git history and past Claude Code sessions. Review before publishing; `<!-- source: ... -->` markers should be removed after vetting.

### From `code_comments` (1)

#### TODO: - set a default image
<!-- source: code_comments ref: models/cctv_camera.py:110 occ: 1 conf: 0.50 -->

**TODO** in `models/cctv_camera.py:110`

> - set a default image

### From `gotchas` (19)

#### Gotcha: **Dotted domain `('a.b', '=', False)` НЕ матчва записи със счупена вер
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.80 -->

From **ORM / Domains** in odoo19-gotchas.md:

> **Dotted domain `('a.b', '=', False)` НЕ матчва записи със счупена верига (`a = NULL`).** В v19 всяка dotted кондиция се декомпозира до `any` оператора (`odoo/orm/domains.py:937-941`) = EXISTS subquery — никога не матчва NULL междинен M2O. Доказано емпирично (hr_rfid, юни 2026): `['|', ('controller_id.webstack_id.company_id','=',False), ...]` в ir.rule НЕ направи controller-less събития видими. За всеки ОПЦИОНАЛЕН линк по веригата трябва изричен клон `('a','=',False)`; required линковете не могат да се счупят → без клон. ВИНАГИ тествай broken-chain записа отделно от terminal-NULL записа — вторият тест минава, докато първият още е скрит.

Matched tokens: `ir.rule, a.b, controller_id.webstack_id.company_id, any`

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `@api.model_create_multi, _compute, api.model_create_multi`

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `httpcase, readonly_enabled, _registry_readonly_enabled = false`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `<p>, %(name)s, help=`

#### Gotcha: **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Security & Constraints** in odoo19-gotchas.md:

> **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res.groups.privilege`, който има `category_id`). Pattern: създаваш `res.groups.privilege` с `category_id=ref('module_category_X')`, после групите имат `privilege_id=ref('res_groups_privilege_X')`.

Matched tokens: `category_id, res.groups.privilege, privilege_id`

#### Gotcha: **Multi-company ir.rule на модел с ОПЦИОНАЛЕН company_id ТРЯБВА да тол
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **ORM / Domains** in odoo19-gotchas.md:

> **Multi-company ir.rule на модел с ОПЦИОНАЛЕН company_id ТРЯБВА да толерира False** — `[('company_id','in',company_ids + [False])]` (v19 core канон, 61 срещания; OCA helpdesk_mgmt upstream също). `[('company_id','in',company_ids)]` скрива всеки глобален запис от всички не-superuser-и; `default=env.company` НЕ прави NULL невъзможен (полето се чисти от UI). За строго company-scoped модели (финансови) правилният fix е `required=True` на полето, не разхлабване. → `odoo-multicompany-checker` skill.

Matched tokens: `required=true, ir.rule, env.company`

#### Gotcha: **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api.constrains` или action-based gating, премахни clickable за да форсираш потребителя през action бутон.

Matched tokens: `@api.constrains, api.constrains`

#### Gotcha: **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай cus
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`html_sanitize()` маха непознати тагове от mail body — НЕ слагай custom XML тагове в имейл маркери.** Odoo sanitize-ва всяко съхранено `body_html`/`body` (mail.mail, mail.message), вкл. съдържанието на HTML коментари които приличат на conditional comment (`<!--[...]-->`). Непознат таг като `<payload encoding="base64">` се изтрива (отварящият таг), но оставя висящ `</payload>` → целият XML маркер става unparseable, дори простите тагове (`<auth>`, `<ticket>`) които оцеляват не се четат. **Решения:** (1) tolerant parse — при `ET.ParseError` salvage-вай само нужните прости блокове в синтетичен валиден документ; (2) по-робустно — base64-encode целия маркер в един blob (без вътрешни тагове за sanitize да пипа). **Как се хваща**: `from odoo.tools import html_sanitize; assert '<payload' in html_sanitize(body)` — ще fail-не. Винаги тествай маркер round-trip ПРЕЗ `html_sanitize`, не само build→parse.

Matched tokens: `body, et.parseerror`

#### Gotcha: **Correlation/round-trip ключ между две инстанции трябва да е със същи
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **Correlation/round-trip ключ между две инстанции трябва да е със същия ТИП от двете страни.** Ако модул А праща `local_id = record.number` (Char стринг "PST-00076") в маркер/payload, а модул Б го чете в `fields.Integer` с `int(local_id)` → `ValueError` на първия реален номер. Маскира се ако тестовете подават числов fixture (`42`) вместо реалния формат. **Винаги** тествай correlation с реалния номеров формат (prefix+padding), не с гол integer. При несъответствие — изравни типа (обикновено Char, защото човешкият номер е стринг), не cast-вай.

Matched tokens: `valueerror, fields.integer`

#### Gotcha: **`message_post(body=...)` / `_message_log` / `mail.activity` третират
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`message_post(body=...)` / `_message_log` / `mail.activity` третират plain `str` като ТЕКСТ и го HTML-escape-ват — HTML в chatter иска `markupsafe.Markup`.** В Odoo 17+ ако подадеш `self.env._("... <b>%s</b> ...", val)` (връща plain `str`), `<b>` се escape-ва → потребителят вижда буквално `<b>resolve</b>` (в raw body: `&lt;b&gt;`). Динамичните стойности ТРЯБВА да се escape-ват (XSS защита), затова canonical pattern е `Markup(self.env._("... <b>%(x)s</b> ...")) % {"x": val}` — `Markup.__mod__` escape-ва само substituted-ите стойности, литералните тагове остават HTML. За чист plain-text note plain `str` е правилен (и по-безопасен — не пъхай HTML където не трябва). Core: `Markup("<b>%s</b>") % name` навсякъде в `mail/`. **Как се хваща**: rendирай note-а и assert `'<b>' in body and '&lt;b&gt;' not in body`; grep adversarial: `grep -rn 'message_post(' models/ | xargs grep -l '<b>\|<br\|<p>'` после провери за `Markup`.

Matched tokens: `str, mail.activity`

#### Gotcha: **Маркер/HTML-коментар сложен в `mail.mail.body_html` на CREATE-time с
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **Маркер/HTML-коментар сложен в `mail.mail.body_html` на CREATE-time се мангълва от `_prepare_outgoing_body`→`_replace_local_links` (lxml re-serialise) на SEND-time.** `html_sanitize` (на store) ГО ЗАПАЗВА, но core `mail.mail._prepare_outgoing_body()` вика `mail.render.mixin._replace_local_links(body_html)`, който парсва+пресериализира HTML-а през lxml и чупи `<!--[...]-->` comment-а (маха отварящия `<!--`, оставя `]--&gt;`). Затова маркерът ТРЯБВА да се embed-ва в override на `_prepare_outgoing_body` **СЛЕД** `super()` (post-`_replace_local_links`), НЕ в `body_html`. За thread-less mail (без model/res_id — за да не цапа клиентския chatter с празно `email_outgoing` "message removed" phantom; `mail.mail` `_inherits` mail.message → model/res_id са на делегата → показва се в chatter) идентифицирай записа през друг канал (напр. `mail.mail.headers` sentinel, парсва се с `ast.literal_eval`) и embed-вай post-super. **Как се хваща**: assert `parse_metadata_xml(mail._prepare_outgoing_body())`, НЕ само `parse_metadata_xml(mail.body_html)` — body_html минава sanitize, но `_prepare_outgoing_body` лови lxml мангъла.

Matched tokens: `<!--, super()`

#### Gotcha: **Button handler (`type="object"`) трябва да върне action dict или Fal
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Бутони и actions** in odoo19-gotchas.md:

> **Button handler (`type="object"`) трябва да върне action dict или False — НИКОГА recordset или lazy обект.** Web клиентът изпълнява върнатото като action: recordset / `filter()` / generator в `"views"` оцелява всички Python тестове (то Е валиден Python обект) и гърми чак в браузъра с `TypeError: action.views.map is not a function` (production PST-00030, product_contract v19.0.1.2.0: `"views": filter(...)` + `return contract_model.browse(...)`). **Как се хваща**: тест за ВСЕКИ бутонен метод: `assert isinstance(action, dict)` + `json.dumps(action)` round-trip + `isinstance(action["views"], list)` — виж `product_contract/tests/test_ui_actions.py` за каноничния клас. Конвенция: UI методът `action_*` връща action; програмната логика живее в `_*` helper, който връща recordset.

Matched tokens: `json.dumps, type="object"`

#### Gotcha: `account.account` **НЯМА** `company_id` — ползвай уникални кодове (нап
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `account.account` **НЯМА** `company_id` — ползвай уникални кодове (напр. `411.NRA`)

Matched tokens: `company_id`

#### Gotcha: `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчита
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `size=N` на `fields.Char` е **UI hint**, не DB constraint — не разчитай на него за валидация

Matched tokens: `fields.char`

#### Gotcha: **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_g
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> **`res.users.groups_id` е преименуван на `group_ids` в v19** (+ `all_group_ids` за implied groups, compute). Старото `groups_id` гърми с `ValueError: Invalid field 'groups_id' in 'res.users'` — често в test setUp при `create({'group_ids': [(4, ref)]})`. Същото важи навсякъде където създаваш/филтрираш users по групи.

Matched tokens: `group_ids`

#### Gotcha: **Search view: `<group>` без атрибути** — `expand="0"` и `string="Grou
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Search view: `<group>` без атрибути** — `expand="0"` и `string="Group By"` са премахнати. Стария път гърми с `RELAXNG_ERR_INVALIDATTR`.

Matched tokens: `<group>`

#### Gotcha: **Form view inline x2many: `default_X: id` НЕ `active_id`** — `active_
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Form view inline x2many: `default_X: id` НЕ `active_id`** — `active_id` е действие-context, не form-context. Често по-чисто е да не подаваш context изобщо — Odoo автоматично попълва inverse FK.

Matched tokens: `active_id`

#### Gotcha: **`mail.template.body_html` се рендира с QWeb (`<t t-out>`), НЕ с inli
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Mail / Templates** in odoo19-gotchas.md:

> **`mail.template.body_html` се рендира с QWeb (`<t t-out>`), НЕ с inline `{{ }}`.** Полето е `fields.Html(render_engine='qweb')`. Само КЪСИТЕ полета (`subject`, `email_from`, `email_to`, `reply_to`, `scheduled_date`) ползват `inline_template` engine-а с `{{ expr }}`. Ако напишеш body с `{{ object.number }}`, placeholder-ите се пращат **буквално** в имейла (получателят вижда `{{ object.number }}`), а evaluation никога не става → латентните грешки в израза (несъществуващо поле/метод) не се виждат докато не мигрираш на t-out и QWeb не ги валидира при write. Canonical: helpdesk_mgmt/data templates ползват `<t t-out="object.X"/>`. Поправка на съществуващи `noupdate="1"` templates → migration който презаписва body-то per-lang. **Как се хваща**: рендирай `template._render_field('body_html', ids)[id]` в тест и assert `'{{' not in body`.

Matched tokens: `subject`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `type="object"`

### From `git_log` (15)

#### Fix: [FIX] polimex_ip_cam: ANPR access decision from Odoo lists, not barrierG
<!-- source: git_log ref: ec459a58c3152bd878a01c28f0b34475d8791091 occ: 1 conf: 0.60 -->

Commit `ec459a58c3` (2026-06-18): [FIX] polimex_ip_cam: ANPR access decision from Odoo lists, not barrierGateCtrlType

#### Fix: [FIX] refresh layer: camera events never refreshed the realtime dashboar
<!-- source: git_log ref: 139e5c19da65d911fc6137b5b59cfe56acebb6bc occ: 1 conf: 0.60 -->

Commit `139e5c19da` (2026-06-17): [FIX] refresh layer: camera events never refreshed the realtime dashboard

#### Fix: [IMP] polimex_ip_cam: NAT-proof camera identity + travel-direction fix
<!-- source: git_log ref: 102d541b072783f9973e792e616ad94561efa738 occ: 1 conf: 0.60 -->

Commit `102d541b07` (2026-06-16): [IMP] polimex_ip_cam: NAT-proof camera identity + travel-direction fix

#### Fix: [FIX] polimex_ip_cam: plate-list write via capability-detected LP-audit 
<!-- source: git_log ref: 616206886c05d5120c9e7d4cbcf0a8ef40e5dae2 occ: 1 conf: 0.60 -->

Commit `616206886c` (2026-06-16): [FIX] polimex_ip_cam: plate-list write via capability-detected LP-audit API

#### Fix: [FIX] polimex_ip_cam: ANPR event identity, Hikvision timezone loop, sear
<!-- source: git_log ref: 4d7c8a07b853f0e1391042a4490add5aa842eee8 occ: 1 conf: 0.60 -->

Commit `4d7c8a07b8` (2026-06-15): [FIX] polimex_ip_cam: ANPR event identity, Hikvision timezone loop, search filter

#### Fix: [FIX] polimex_ip_cam: clamp ANPR HTTP-host heartbeat to camera capabilit
<!-- source: git_log ref: 412c21eb62bf3702a3cbe31d0a87dcf678362a68 occ: 1 conf: 0.60 -->

Commit `412c21eb62` (2026-06-15): [FIX] polimex_ip_cam: clamp ANPR HTTP-host heartbeat to camera capabilities

#### Fix: [FIX] ip_cam/elections: authenticate ANPR webhook & lock public vote-clo
<!-- source: git_log ref: 887641ab5a205bfbc319fe40e637c21c8f9f2389 occ: 1 conf: 0.60 -->

Commit `887641ab5a` (2026-06-12): [FIX] ip_cam/elections: authenticate ANPR webhook & lock public vote-close

#### Fix: [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks
<!-- source: git_log ref: 93125c7183286c0e295bda9ff90e795855c23c9a occ: 1 conf: 0.60 -->

Commit `93125c7183` (2026-06-11): [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

#### Fix: [FIX] drop test-framework import from module __init__ (A1)
<!-- source: git_log ref: d3925400454543d7999e8b92bce72f95f1a84e03 occ: 1 conf: 0.60 -->

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [FIX] polimex_ip_cam: Odoo 19 view inheritance (tree→list)
<!-- source: git_log ref: b5a41cb2226b041242eac3dd2dc09bcb0b1c390b occ: 1 conf: 0.60 -->

Commit `b5a41cb222` (2026-04-20): [FIX] polimex_ip_cam: Odoo 19 view inheritance (tree→list)

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context
<!-- source: git_log ref: c2b001ba20353637d0a0b6541fa6df7d479636e6 occ: 1 conf: 0.60 -->

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: Fix create loop argument
<!-- source: git_log ref: 9902b01b32ecf0087fa75c31f013c3b36f849841 occ: 1 conf: 0.60 -->

Commit `9902b01b32` (2025-05-21): Fix create loop argument

#### Fix: Fix camera bug for unknown plate number handling
<!-- source: git_log ref: f30b193421331f684ee446f5662a5de5828d5e02 occ: 1 conf: 0.60 -->

Commit `f30b193421` (2025-05-01): Fix camera bug for unknown plate number handling

#### Fix: Fix typo in hr_rfid_event_system.xml and update dependencies in __manife
<!-- source: git_log ref: 8b3982b342f4adb7390bbc1c7d63e1f876e920d6 occ: 1 conf: 0.60 -->

Commit `8b3982b342` (2025-04-23): Fix typo in hr_rfid_event_system.xml and update dependencies in __manifest__.py

#### Fix: Fix typo in method name for danger balloon notification
<!-- source: git_log ref: 5613cc9c064f5865b6404dba62265623acbdcd7e occ: 1 conf: 0.60 -->

Commit `5613cc9c06` (2025-03-28): Fix typo in method name for danger balloon notification


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/polimex_ip_cam`
- Source digest: `sha256:5e04b818dc6208b79c78ff5b149171c2e492a40285ced080a2dc7bc91fc9ee86`
- Generated at: `2026-06-19T17:55:54+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)

## Silence during a data transfer <a id='no-hardware-commands'></a>

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
