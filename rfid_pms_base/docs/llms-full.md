---
id: rfid_pms_base
title: RFID PMS Base
module: rfid_pms_base
module_version: 19.0.0.11.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: RFID PMS system Base structures
last_updated: '2026-08-14'
source_digest: sha256:c62b009d4388adfc9875d68038831797fe93f475216234b61e40d5d2f7561e6e
depends:
- hr_rfid
- onboarding
entities:
  primary: rfid_pms_base.card_encode_wiz
  related:
  - onboarding.onboarding
  - onboarding.onboarding.step
  - rfid_pms_base.room
  - rfid_pms_base.room_move_wiz
keywords:
- base
- card_encode_wiz
- onboarding
- pms
- rfid
- rfid_pms_base
- room
- room_move_wiz
- step
- structures
- system
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: true
application: true
auto_install: false
counts:
  models: 5
  views: 7
  access_rules: 6
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:1657dd036d568e1434c3be8bd88f7fe07e79ff131efed976f6afae8f5c917e6c
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:4200a80d6063bad6648320dd581c1d1df22599b974979103631568ee49900157
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID PMS Base — `rfid_pms_base` v19.0.0.11.0

RFID PMS system Base structures

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_pms_base`
- **Version**: `19.0.0.11.0`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: yes
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `onboarding`

### README (verbatim)

#### RFID PMS Base

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.1.0-green.svg)](https://apps.odoo.com)

Property Management System integration for RFID access control.

##### 🎯 Overview

RFID PMS Base bridges the gap between property management and access control, providing seamless integration for hotels, student accommodation, serviced apartments, and residential complexes. It manages room assignments, guest check-ins, and automatically configures RFID access based on room bookings.

##### ✨ Key Features

###### Room Management
- **Room Registry**: Complete room database
- **Status Tracking**: Available, occupied, cleaning, maintenance
- **Multi-property**: Support for multiple buildings
- **Room Types**: Single, double, suite configurations

###### Guest Integration
- **Check-in/out**: Streamlined guest processing
- **Card Encoding**: Instant RFID card programming
- **Room Moves**: Easy guest relocation
- **Group Bookings**: Handle multiple guests

###### Access Control
- **Automatic Rights**: Room-based access configuration
- **Time Limits**: Check-in to check-out access
- **Common Areas**: Gym, pool, parking access
- **Master Keys**: Staff and emergency access

###### Status Indicators
- **Occupancy Status**: Real-time room status
- **Cleaning Flags**: Housekeeping coordination
- **DND Indicators**: Do not disturb tracking
- **Maintenance Mode**: Block room access

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- Python 3.8+

###### Dependencies
```python
'depends': ['hr_rfid']
```

##### 🛠️ Installation

1. Install hr_rfid module first

2. Install PMS base module:
```bash
./odoo-bin -d your_database -i rfid_pms_base
```

3. Configure rooms and access rules

##### 🔧 Configuration

###### Initial Setup

1. **Building Configuration**
   - Create building records
   - Set address and details
   - Configure access zones

2. **Room Setup**
   - Add rooms to buildings
   - Set room numbers and types
   - Assign doors to rooms
   - Configure amenity access

3. **Access Templates**
   - Guest room access
   - Common area access
   - Time-based restrictions
   - Emergency procedures

###### Room Types

Configure different room categories:
```python
#### Room type examples
room_types = [
    ('single', 'Single Room'),
    ('double', 'Double Room'),
    ('suite', 'Suite'),
    ('dormitory', 'Dormitory'),
    ('apartment', 'Apartment'),
]
```

###### Door Assignment

Link rooms to physical doors:
1. Navigate to room record
2. Assign primary door (room entrance)
3. Add common area doors
4. Set access schedules

##### 📖 Usage

###### Guest Check-in

1. **Create/Select Guest**
   - New guest registration
   - Or select existing guest
   - Enter stay details

2. **Assign Room**
   - Select available room
   - Set check-in/out dates
   - Configure access level

3. **Encode Card**
   - Insert blank RFID card
   - Click "Encode Card"
   - Card automatically configured
   - Hand to guest

###### Room Status Management

###### Status Types
- 🟢 **Available**: Ready for guests
- 🔴 **Occupied**: Guest checked in
- 🟡 **Cleaning**: Housekeeping in progress
- 🔧 **Maintenance**: Under repair
- 🚫 **Blocked**: Temporarily unavailable

###### Status Changes
```python
#### Automatic status updates
room.state = 'occupied'  # On check-in
room.state = 'cleaning'  # On check-out
room.state = 'available' # After cleaning
```

###### Card Management

###### Card Encoding Wizard
1. **From Room View**
   - Open room record
   - Click "Encode Card"
   - Select guest
   - Program card

2. **Batch Encoding**
   - Select multiple rooms
   - Action → Encode Cards
   - Process group bookings

###### Access Rights
- Room door access
- Floor elevator access
- Common areas (configurable)
- Parking (if assigned)

###### Room Moves

Handle guest relocations:
1. **Initiate Move**
   - Current room → Move Guest
   - Select new room
   - Choose move time

2. **Access Update**
   - Old room access revoked
   - New room access granted
   - Card reprogrammed if needed

##### 🏨 Hotel-Specific Features

###### Housekeeping Integration
```python
#### Cleaning workflow
room.request_cleaning()  # After checkout
room.start_cleaning()    # Housekeeper begins
room.complete_cleaning() # Ready for next guest
```

###### Mini-bar & Services
- Link to POS for charges
- Room service ordering
- Amenity usage tracking

###### Group Management
- Tour groups
- Conference attendees  
- Corporate bookings

##### 🏢 Other Verticals

###### Student Accommodation
- Semester-long access
- Shared room management
- Study room bookings
- Meal plan integration

###### Corporate Housing
- Long-term assignments
- Visitor management
- Maintenance requests
- Utility tracking

###### Residential Complexes
- Tenant management
- Visitor passes
- Amenity bookings
- Package notifications

##### 🔌 API Extensions

###### Custom Check-in
```python
class CustomPMSRoom(models.Model):
    _inherit = 'pms.room'
    
    def custom_checkin(self, guest_data):
        # Pre-checkin validation
        self.validate_guest(guest_data)
        
        # Standard check-in
        res = super().checkin(guest_data)
        
        # Post-checkin actions
        self.send_welcome_message()
        self.activate_room_features()
        
        return res
```

###### Integration Webhooks
```python
#### Notify external PMS
@api.model
def create_booking_webhook(self, booking_data):
    webhook_url = self.env['ir.config_parameter'].get_param('pms.webhook.url')
    requests.post(webhook_url, json={
        'room': booking_data['room_id'],
        'guest': booking_data['guest_name'],
        'checkin': booking_data['checkin_date'],
        'checkout': booking_data['checkout_date'],
    })
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Card not opening door**
   - Check room assignment
   - Verify check-in completed
   - Confirm door mapping
   - Test access schedule

2. **Wrong room status**
   - Manual status update
   - Check automation rules
   - Review housekeeping workflow

3. **Guest can't access amenities**
   - Verify access template
   - Check amenity doors configuration
   - Review time restrictions

###### Maintenance Mode

Enable for debugging:
```python
#### System parameters
pms_debug_mode = True
pms_log_door_events = True
pms_test_mode = False  # Disables actual door control
```

##### 📊 Reports

###### Occupancy Reports
- Daily occupancy rate
- Room utilization
- Average stay duration
- Revenue per room

###### Guest Reports
- Check-in/out list
- Guest history
- No-show tracking
- Repeat guest analysis

###### Access Reports
- Door usage by room
- Failed access attempts
- Emergency opens
- Master key usage

##### 🤝 Contributing

We welcome contributions:
1. Fork repository
2. Add PMS features
3. Test with demo data
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-pms)
- [PMS Integration Guide](https://polimex.co/docs/pms-integration)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_pms_base/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_pms_base --stop-after-init
```

> **Application**: this module will appear as a top-level app in the Apps menu.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `rfid_pms_base.card_encode_wiz` <a id='model-rfid-pms-base-card-encode-wiz'></a>
Python class `RfidPmsBaseCardEncodeWiz` in `models/card_encode_wiz.py:7`.  TransientModel (wizard).  Description: *Base PMS Card encoding Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `room_id` | Many2one → \`rfid_pms_base.room\` |  |  | ✓ | The hotel room this card opens. Set automatically from the kanban card you click |
| `reservation` | Char |  |  | ✓ | Reservation reference used as the parent partner name (e.g. R002615). Only meani |
| `checkin_date` | Datetime | Check In |  | ✓ | Moment the card starts working. In New mode defaults to now; in Current mode inh |
| `checkout_date` | Datetime | Check Out |  | ✓ | Moment the card stops working. In New mode defaults to tomorrow at 09:00; in Cur |
| `mode` | Selection |  |  | ✓ | New = open a fresh reservation and revoke any leftover cards; Current = add anot |
| `card_number` | Char | The card number | ✓ | ✓ | Number printed on the RFID card or barcode. The wizard zero-pads to 10 digits be |

#### Notable methods

- **`write_card(self)`** — decorators: —
  - effects: `i18n`, `raise:UserError`, `with_context`
  - touches: `hr.rfid.card`, `res.partner`

### `onboarding.onboarding` <a id='model-onboarding-onboarding'></a>
Python class `OnboardingOnboarding` in `models/onboarding_onboarding.py:4`.  Model.  Inherits: `onboarding.onboarding`.

#### Notable methods

- **`action_close_panel_pms_setup(self)`** — decorators: `@api.model`
  - effects: `sudo`

### `onboarding.onboarding.step` <a id='model-onboarding-onboarding-step'></a>
Python class `OnboardingOnboardingStep` in `models/onboarding_onboarding_step.py:4`.  Model.  Inherits: `onboarding.onboarding.step`.

#### Notable methods

- **`action_open_step_pms_access_group(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_pms_first_room(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`

### `rfid_pms_base.room` <a id='model-rfid-pms-base-room'></a>
Python class `SchEncoderRoom` in `models/room.py:5`.  Model.  Description: *Rooms*.  Default order: `number`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  | ✓ | ✓ | Friendly label for the room shown to the receptionist (e.g. 'Suite 101' or 'Twin |
| `group` | Char |  |  | ✓ | Optional grouping label used to split the kanban into columns (e.g. floor or win |
| `number` | Integer | Internal number | ✓ | ✓ | Numeric identifier the controller uses to address this room's door. Must be uniq |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns the room. Hotel data is isolated per company; users only see r |
| `door_id` | Many2one → \`hr.rfid.door\` | Room door | ✓ | ✓ | The controller door wired to this room's lock. The DND, Clean and Card-present f |
| `access_group_id` | Many2one → \`hr.rfid.access.group\` | Guest Group | ✓ | ✓ | Access group the issued guest cards are added to. Defines which doors a card can |
| `all_employee_ids` | Many2many → \`hr.rfid.access.group.employee.rel\` | All employees |  | — | All employees that use this access group, including the ones from the inheritors |
| `all_contact_ids` | Many2many → \`hr.rfid.access.group.contact.rel\` | All contacts |  | — | All contacts that use this access group, including the ones from the inheritors |
| `reservation` | Many2one → \`res.partner\` | Reservation |  | — | Parent partner that groups every guest card currently issued for this room. Empt |
| `hb_dnd` | Boolean | DND button pressed |  | — | True when the guest pressed Do Not Disturb on the in-room console. Staff cards s |
| `hb_clean` | Boolean | Clean button pressed |  | — | True when the guest requested cleaning from the in-room console. Visible to hous |
| `hb_card_present` | Boolean | Present card in reader |  | — | True while a card is inserted in the room's energy-saver reader. Used by the kan |
| `last_temperature` | Float | Temperature |  | — | Room temperature reported by the BMS sensor. Currently a stub value until a BMS  |
| `last_humidity` | Float | Humidity |  | — | Room humidity reported by the BMS sensor. Currently a stub value until a BMS sen |
| `last_occupancy` | Char | Occupancy |  | — | Occupancy state reported by the BMS sensor. Currently a stub value until a BMS s |
| `last_insert_name` | Char | Last Insert Card |  | — | Name of the employee or guest whose card was last inserted at the room's energy- |

#### Notable methods

- **`_compute_last_insert_name(self)`** — decorators: `@api.depends`
  - touches: `hr.rfid.event.user`
- **`_compute_reservation(self)`** — decorators: `@api.depends`
- **`user_events_act(self)`** — decorators: —
  - effects: `with_context`
- **`toggle_hotel(self)`** — decorators: —
- **`_check_number(self)`** — decorators: `@api.constrains`
  - effects: `raise:ValidationError`

### `rfid_pms_base.room_move_wiz` <a id='model-rfid-pms-base-room-move-wiz'></a>
Python class `RoomMoveWiz` in `models/room_move_wiz.py:4`.  TransientModel (wizard).  Description: *Move customers from one room to another*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `room_from_id` | Many2one → \`rfid_pms_base.room\` |  |  | ✓ | Source room the reservation is currently registered against. Read-only — set aut |
| `room_to_id` | Many2one → \`rfid_pms_base.room\` |  | ✓ | ✓ | Destination room. Only rooms with no active reservation are offered. After confi |

#### Notable methods

- **`move_customers(self)`** — decorators: —


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestRfidPmsOnboarding.setUpClass(cls)`** (`@classmethod`) — `tests/test_onboarding.py:10`
  - calls `super()`
- **`TestRfidPmsOnboarding.test_panel_has_two_steps_in_order(self)`** — `tests/test_onboarding.py:18`
- **`TestRfidPmsOnboarding.test_step_actions_resolve_to_real_windows(self)`** — `tests/test_onboarding.py:24`
  - touches: `onboarding.onboarding.step`
- **`TestRfidPmsOnboarding.test_ag_step_completes_when_ag_with_door_exists(self)`** — `tests/test_onboarding.py:31`
  - touches: `hr.rfid.access.group`, `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.webstack`
- **`TestRfidPmsOnboarding.test_room_step_completes_when_room_exists(self)`** — `tests/test_onboarding.py:55`
  - touches: `hr.rfid.access.group`, `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.webstack`, `rfid_pms_base.room`
- **`TestRfidPmsRoom.setUpClass(cls)`** (`@classmethod`) — `tests/test_room.py:10`
  - calls `super()`
  - touches: `hr.rfid.access.group`, `hr.rfid.ctrl`, `hr.rfid.webstack`
- **`TestRfidPmsRoom.test_create_room(self)`** — `tests/test_room.py:53`
- **`TestRfidPmsRoom.test_room_default_group_value(self)`** — `tests/test_room.py:59`
  - touches: `rfid_pms_base.room`
- **`TestRfidPmsRoom.test_room_number_must_be_globally_unique(self)`** — `tests/test_room.py:70`
- **`TestRfidPmsRoom.test_room_number_must_be_within_range(self)`** — `tests/test_room.py:77`
- **`TestRfidPmsRoom.test_reservation_is_empty_when_no_contacts(self)`** — `tests/test_room.py:82`
- **`TestRfidPmsRoom.test_room_move_wiz_lists_only_free_rooms(self)`** — `tests/test_room.py:87`
  - effects: `with_context`
  - touches: `rfid_pms_base.room_move_wiz`
- **`TestRfidPmsRoom.test_room_move_wiz_default_room_from(self)`** — `tests/test_room.py:107`
  - effects: `with_context`
  - touches: `rfid_pms_base.room_move_wiz`
- **`TestRfidPmsRoom.test_compute_temperature_returns_stub_values(self)`** — `tests/test_room.py:116`
- **`TestRfidPmsRoom.test_compute_last_insert_name_unknown_when_no_event(self)`** — `tests/test_room.py:123`
- **`TestRfidPmsRoom.test_toggle_hotel_dnd_flips_door_flag(self)`** — `tests/test_room.py:127`
  - effects: `with_context`
- **`TestRfidPmsRoom.test_toggle_hotel_clean_flips_door_flag(self)`** — `tests/test_room.py:135`
  - effects: `with_context`
- **`TestRfidPmsRoom.test_toggle_hotel_unknown_btn_is_noop(self)`** — `tests/test_room.py:143`
  - effects: `with_context`
- **`TestRfidPmsRoom.test_user_events_act_returns_action_for_door(self)`** — `tests/test_room.py:150`
- **`TestRfidPmsRoomTours.setUpClass(cls)`** (`@classmethod`) — `tests/test_tours.py:13`
  - calls `super()`
  - touches: `hr.rfid.access.group`, `hr.rfid.ctrl`, `hr.rfid.webstack`
- **`TestRfidPmsRoomTours.test_room_kanban_actions_tour(self)`** — `tests/test_tours.py:49`
  - User flow: toggle DND, toggle Clean, navigate to user events.
  - touches: `rfid_pms_base.room`
- **`TestRfidPmsRoomTours.test_room_move_tour(self)`** — `tests/test_tours.py:64`
  - User flow: move the occupant from one room to another.
  - touches: `hr.rfid.access.group.contact.rel`, `res.partner`, `rfid_pms_base.room`

### Private helpers

- **`TestRfidPmsRoom._next_door(cls, label)`** (`@classmethod`) — `tests/test_room.py:33`
  - touches: `hr.rfid.door`
- **`TestRfidPmsRoom._make_room(self, name, number, group='Ungrouped')`** — `tests/test_room.py:42`
  - touches: `rfid_pms_base.room`
- **`TestRfidPmsRoomTours._make_door(cls, label)`** (`@classmethod`) — `tests/test_tours.py:40`
  - touches: `hr.rfid.door`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_card_view_list_base_pms_inherit` | `hr.rfid.card` | — | hr_rfid.hr_rfid_card_view_list | `views/hr_rfid_card.xml` |
| `rfid_pms_base_room_form` | `rfid_pms_base.room` | — |  | `views/room.xml` |
| `rfid_pms_base_room_list` | `rfid_pms_base.room` | — |  | `views/room.xml` |
| `rfid_pms_base_room_kanban` | `rfid_pms_base.room` | — |  | `views/room.xml` |
| `rfid_pms_base_room_search` | `rfid_pms_base.room` | — |  | `views/room.xml` |
| `cards_encode_wiz_view_form` | `rfid_pms_base.card_encode_wiz` | — |  | `views/wiz_card_from_room.xml` |
| `room_move_wiz_view_form` | `rfid_pms_base.room_move_wiz` | — |  | `views/wiz_room_move.xml` |

#### Sample XPath operations

- In `hr_rfid_card_view_list_base_pms_inherit`:
  - `//field[@name='card_type'] [replace]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_card_user`, `group_card_manager`


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_rfid_pms_base_room_user` | `model_rfid_pms_base_room` | `group_card_user` | ✓ |  |  |  |

| `access_rfid_pms_base_room_manager` | `model_rfid_pms_base_room` | `group_card_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_rfid_pms_base_card_encode_wiz` | `model_rfid_pms_base_card_encode_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

| `access_rfid_pms_base_hr_rfid_command` | `hr_rfid.model_hr_rfid_command` | `rfid_pms_base.group_card_user` | ✓ | ✓ |  |  |

| `access_rfid_pms_base_hr_rfid_access_group_door_rel` | `hr_rfid.model_hr_rfid_access_group_door_rel` | `rfid_pms_base.group_card_user` | ✓ | ✓ | ✓ | ✓ |

| `access_rfid_pms_base_room_move_wiz` | `model_rfid_pms_base_room_move_wiz` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `onboarding.onboarding.step`: 2 record(s)
- `ir.sequence`: 1 record(s)
- `onboarding.onboarding`: 1 record(s)


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

### From `gotchas` (12)

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `_registry_readonly_enabled = false, readonly_enabled, httpcase`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `'current', action_window, type="object"`

#### Gotcha: **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Security & Constraints** in odoo19-gotchas.md:

> **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res.groups.privilege`, който има `category_id`). Pattern: създаваш `res.groups.privilege` с `category_id=ref('module_category_X')`, после групите имат `privilege_id=ref('res_groups_privilege_X')`.

Matched tokens: `privilege_id, res.groups.privilege, category_id`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `models.constraint, validationerror`

#### Gotcha: **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Statusbar `clickable="1"` заобикаля Python gating** — ако имаш `@api.constrains` или action-based gating, премахни clickable за да форсираш потребителя през action бутон.

Matched tokens: `@api.constrains, api.constrains`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `<p>, help=`

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

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `_compute`

#### Gotcha: **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`**
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`** — v18→v19 преименуване. Стария път минава XML lint и install, но при отваряне в браузъра гърми с `OwlError: Missing 'card' template`. Структурата на content също е олекотена (без `oe_kanban_card` обвивка — директно полета + footer).

Matched tokens: `<t t-name="card">`

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

### From `git_log` (13)

#### Fix: [TEST] rfid_pms_base: add 2 kanban tours + fix v18 data-context residue
<!-- source: git_log ref: e4884525993361af357b5d49d8c0c97303d0a9c5 occ: 1 conf: 0.60 -->

Commit `e488452599` (2026-05-13): [TEST] rfid_pms_base: add 2 kanban tours + fix v18 data-context residue

#### Fix: [FIX] rfid_pms_base: v18 -> v19 migration (attrs, view-id, range check, 
<!-- source: git_log ref: 572b1708c1e5ca59812b838115b03aac07604849 occ: 1 conf: 0.60 -->

Commit `572b1708c1` (2026-05-03): [FIX] rfid_pms_base: v18 -> v19 migration (attrs, view-id, range check, tests)

#### Fix: [FIX] noupdate on user-tunable data records (3 modules)
<!-- source: git_log ref: df70ee69435fdfe180aa7565634eb91a0e62da0a occ: 1 conf: 0.60 -->

Commit `df70ee6943` (2026-05-01): [FIX] noupdate on user-tunable data records (3 modules)

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context
<!-- source: git_log ref: c2b001ba20353637d0a0b6541fa6df7d479636e6 occ: 1 conf: 0.60 -->

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M
<!-- source: git_log ref: 3c84986ac48326833d2f41e4de1d121e3c526130 occ: 1 conf: 0.60 -->

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: Port functionality and fixes from 14.0
<!-- source: git_log ref: 10637e0f69f57f10e235d43b29605161dfb78c97 occ: 1 conf: 0.60 -->

Commit `10637e0f69` (2022-03-22): Port functionality and fixes from 14.0

#### Fix: Port fixes from 14.0
<!-- source: git_log ref: 4428bc253e3f087a8debfba3c2df905fa44d05dc occ: 1 conf: 0.60 -->

Commit `4428bc253e` (2022-02-13): Port fixes from 14.0

#### Fix: [FIX] New reservation counter
<!-- source: git_log ref: f936e189f1c569b5531b04eb1aee0a73b00776bd occ: 1 conf: 0.60 -->

Commit `f936e189f1` (2021-09-19): [FIX] New reservation counter

#### Fix: [FIX] License
<!-- source: git_log ref: 5e78739c1295b262921d6d9e338d4c7f3ee01d8c occ: 1 conf: 0.60 -->

Commit `5e78739c12` (2021-09-11): [FIX] License

#### Fix: [FIX] Fix expiration encoding
<!-- source: git_log ref: 6236d5f1c67ec8347eba4fbaed59f323aede218c occ: 1 conf: 0.60 -->

Commit `6236d5f1c6` (2021-09-08): [FIX] Fix expiration encoding

#### Fix: [FIX] Fix expiration encoding
<!-- source: git_log ref: fa2c4b7f2fa5c8ecb95080ba7ed1b5620faf22aa occ: 1 conf: 0.60 -->

Commit `fa2c4b7f2f` (2021-09-07): [FIX] Fix expiration encoding

#### Fix: [FIX] Reservation Time, User rights, User event menu
<!-- source: git_log ref: d63c60bfd5ab30c582e56dbfaacacf2d2a0de21e occ: 1 conf: 0.60 -->

Commit `d63c60bfd5` (2021-09-03): [FIX] Reservation Time, User rights, User event menu

#### Fix: [FIX] Reservation Time, User rights, User event menu
<!-- source: git_log ref: f387026209dd50dc27369b696392a7d83d3b2fc5 occ: 1 conf: 0.60 -->

Commit `f387026209` (2021-09-03): [FIX] Reservation Time, User rights, User event menu


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/rfid_pms_base`
- Source digest: `sha256:c62b009d4388adfc9875d68038831797fe93f475216234b61e40d5d2f7561e6e`
- Generated at: `2026-05-14T11:16:43+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)

## The setup checklist (onboarding banner) <a id='onboarding-banner'></a>

The banner is NOT a view class of this module. It is attached by putting the
onboarding's `route_name` in the CONTEXT of the action:

```xml
<field name="context">{'onboarding_route_name': 'rfid_pms_base_setup'}</field>
```

on ``action_window_room` (Hotel Rooms, kanban/list/form)` (`views/room.xml`). That is the whole integration on this side.

Everything else lives in `hr_rfid`: the `OnboardingBanner` OWL component, the
extension of the stock `web.ListView` / `web.KanbanView` templates, and the two
server methods `onboarding.onboarding.get_onboarding_panel_html(route_name)` /
`close_onboarding_panel(route_name)` - which render and close core's own
`onboarding.onboarding_panel` template, so the banner is identical to Odoo's
native one and translated server-side.

**Do not go back to `js_class`.** It was one until August 2026, and a view
carries exactly ONE `js_class`: `hr_rfid_refresh_views` (auto_install, so on
nearly every database) writes its own over the view it inherits, and the banner
component was then never created at all - no error, no request, no banner, with
the server side rendering perfectly the whole time. Keying on the action context
removes the conflict: the view can carry any `js_class` and still show the
banner.

This module's own part is `models/onboarding_onboarding.py`:
`_prepare_rendering_values` auto-completes its two steps (an `hr.rfid.access.group` with doors exists; a `rfid_pms_base.room` exists) for the CURRENT company
before delegating to core, and `action_close_panel_pms_setup` is the close action named on the
onboarding record. Nothing here has to know how the banner is drawn.
