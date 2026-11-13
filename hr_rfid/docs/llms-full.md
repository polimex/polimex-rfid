---
id: hr_rfid
title: RFID Access Control
module: hr_rfid
module_version: 19.0.2.33.4
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage employee access control
last_updated: '2026-11-09'
source_digest: sha256:8fae63ae5f5fdba8a7d7220c4629c62c3c8431043cc7cba8a1f624338cfaa506
depends:
- hr
- contacts
- digest
- onboarding
- polimex_ws
entities:
  primary: hr.rfid.ctrl
  related:
  - balloon.mixin
  - digest.digest
  - hr.department
  - hr.department.acc.grs
  - hr.department.def.acc.gr
  - hr.department.mass.wiz
  - hr.department.add.def.acc.grs
  - hr.employee
  - hr.rfid.access.group
  - hr.rfid.access.group.door.rel
  - hr.rfid.access.group.rel
  - hr.rfid.access.group.employee.rel
  - hr.rfid.access.group.contact.rel
  - hr.rfid.access.group.wizard
keywords:
- acc
- access
- balloon
- control
- ctrl
- department
- digest
- employee
- grs
- manage
- mixin
- rfid
license: AGPL-3
author: Polimex Dev Team
category: Human Resources
installable: true
application: true
auto_install: false
counts:
  models: 58
  views: 95
  access_rules: 70
  record_rules: 32
  crons: 5
  images: 8
images:
- path: static/description/icon.png
  sha256: sha256:8d07250043550a38be851cfb310332825e2735fc99316eb868f829854dff8105
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:9bcb8e4e06bd559dff8e4cecbace6509d9146fcd14b2b30294498fe489fa6daa
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/how_to_fold_1.png
  sha256: sha256:d60b57818cd7c22cc78a51b7dd30f149bdd24e7f6cbbf5827dfc3fe80fd58673
  alt: How To Fold 1
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/how_to_fold_2.png
  sha256: sha256:66492a31ce494cf01c5d0767e3bfa7eff37c93b8a5ac68b9874108721eb76ff2
  alt: How To Fold 2
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/how_to_fold_3.png
  sha256: sha256:29798e669745e3b29b3b145402e271801ea22d0cb956191dc522fb7689d25d94
  alt: How To Fold 3
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/how_to_fold_4.png
  sha256: sha256:04d0b5f5785fa141bc900fd414ea3223201fcaf11f567b47e6227c62b712093d
  alt: How To Fold 4
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/report_foldable_badge_background.png
  sha256: sha256:67c28f16a3c53303dff5e5f38a4c0a7bec2f18ec4db95b07f3a1a517bacc5696
  alt: Report Foldable Badge Background
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/src/img/report_full_page_ticket_background.png
  sha256: sha256:9babcc149f8f693eaa3ee62cf8f891eb880a6d48f45f0f562779580af7cd47ae
  alt: Report Full Page Ticket Background
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Access Control - `hr_rfid` v19.0.2.33.4

Manage employee access control

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid`
- **Version**: `19.0.2.33.4`
- **Category**: Human Resources
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: yes
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr`, `contacts`, `digest`, `onboarding`, `polimex_ws`

### README (verbatim)

#### HR RFID Access Control

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.2.2.1-green.svg)](https://apps.odoo.com)

The main RFID Access Control module for Odoo, providing comprehensive hardware integration and access management capabilities.

##### 🎯 Overview

HR RFID is the core module of the Polimex RFID Suite, offering enterprise-grade access control management integrated with Odoo's HR system. It supports various RFID controllers and provides real-time monitoring, advanced access rules, and comprehensive reporting.

##### ✨ Key Features

###### Hardware Management
- **Multi-Controller Support**: iCON50, iCON110, iCON115, iCON130, iCON180
- **Webstack Communication**: HTTP-based controller management
- **Real-time Events**: Live event processing and monitoring
- **Hardware Discovery**: Automatic detection of controllers on network

###### Access Control
- **Access Groups**: Define who can access which doors
- **Time Schedules**: Configure access based on time periods
- **Zone Management**: Group doors into logical zones
- **Emergency Groups**: Special access during emergencies
- **Anti-passback**: Prevent card sharing and enforce area occupancy

###### Card Management
- **Multiple Card Types**: RFID, Barcode, PIN support
- **Card Lifecycle**: Issue, activate, deactivate, expire
- **Bulk Operations**: Import/export card data
- **Card Templates**: Predefined card configurations

###### Security Features
- **Duress PIN**: Silent alarm triggering
- **Alarm Management**: Door forced, door open too long
- **Audit Trail**: Complete event logging
- **Multi-Company**: Data isolation between companies

###### Integration
- **HR Integration**: Link cards to employees
- **Partner Integration**: Visitor and contractor management
- **Event Webhooks**: External system notifications
- **REST API**: For third-party integrations

##### 📋 Requirements

- Odoo 18.0+
- Python 3.8+
- PostgreSQL 12+
- Compatible RFID hardware

###### Python Dependencies
```
- Standard Odoo dependencies
```

###### Odoo Dependencies
- `base`
- `mail`
- `hr`
- `digest`

##### 🛠️ Installation

1. Copy the module to your Odoo addons directory:
```bash
cp -r hr_rfid /path/to/odoo/addons/
```

2. Update the module list:
```bash
./odoo-bin -d your_database -u hr_rfid
```

3. Install via Odoo Apps interface or command line:
```bash
./odoo-bin -d your_database -i hr_rfid
```

##### 🔧 Configuration

###### Initial Setup

1. **System Parameters**
   - Navigate to Settings → Technical → System Parameters
   - Configure `hr_rfid.*` parameters as needed

2. **Webstack Configuration**
   - Go to RFID → Configuration → Webstacks
   - Add your webstack with IP and port
   - Test connection using the "Test" button

3. **Controller Setup**
   - Controllers will auto-appear after webstack connection
   - Configure each controller's settings
   - Map readers to doors

4. **Access Groups**
   - Create access groups under RFID → Access Groups
   - Define time schedules if needed
   - Assign doors to groups

###### Hardware Setup

###### Network Configuration
```
Webstack Default Port: 80
Controller Communication: HTTP
Event Endpoint: /hr/rfid/event
```

###### Controller Types
- **iCON50**: 1 door, 1 readers
- **iCON110**: 1-2 door, 2 readers, IO support
- **iCON115**: 1-2 door, 2 readers, IO support, alarm support
- **iCON130**: 2-4 doors, 4 readers, IO support
- **turnstile**: 1 doors, 4 readers, IO support with specific turnstile features
- **iCON180**: 4 doors, 8 readers, IO support, alarm support
- **Relay**: up to 512 door, 2 readers, IO support with relays for elevator control and etc.
- **Fire**: IO support with fire alarm control panel with 4 analog fire line inputs
- **iTemp**: up to 90 temperature sensors, IO support with temperature monitoring

##### 📖 Usage

###### Managing Cards

1. **Issue New Card**
   - Go to RFID → Cards → Create
   - Enter card number (or scan)
   - Assign to employee/partner
   - Select access groups

2. **Bulk Import**
   - RFID → Cards → Import
   - Use Excel template provided
   - Map columns and import

###### Monitoring Access

1. **Live Events**
   - RFID → Events → User Events
   - Real-time event stream
   - Filter by door, person, or time
   - Type part of a person's, contact's or door's name, or an action as it
     reads in the list (e.g. "Card Denied"), in the search box and press Enter

2. **Door Status**
   - RFID → Doors
   - View current door states
   - Remote open/close doors

###### Reports

- Access logs by person
- Door usage statistics
- Failed access attempts
- Alarm history

##### 🔌 API Reference

###### Event Processing
```python
#### Event endpoint: /hr/rfid/event
POST /hr/rfid/event
{
    "controller_id": "ctrl_serial",
    "event_type": "card_read",
    "reader_id": 1,
    "card_number": "1234567890",
    "timestamp": "2024-01-01 12:00:00"
}
```

###### Remote Commands
```python
#### Open door remotely
door.remote_open(user_id)

#### Add card to controller
card.add_to_controllers()

#### Emergency open all doors
access_group.emergency_open()
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Webstack not connecting**
   - Check network connectivity
   - Verify firewall rules
   - Confirm webstack service is running

2. **Cards not working**
   - Verify card is active
   - Check access group assignments
   - Confirm time schedules

3. **Events not appearing**
   - Check controller online status
   - Verify event processing cron job
   - Review system logs

###### Debug Mode

Enable debug logging:
```python
#### In configuration
log_level = debug
log_handler = hr_rfid:DEBUG
```

##### 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

##### 📄 License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid)
- [Issue Tracker](https://github.com/polimex/odoo-apps/issues)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid --stop-after-init
```

> **Application**: this module will appear as a top-level app in the Apps menu.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `balloon.mixin` <a id='model-balloon-mixin'></a>
Python class `AliasMixin` in `models/balloon_mixin.py:4`.  AbstractModel.  Description: *Balloon Messages Mixin*.

> A mixin for models that need to return balloon msg in backend.

#### Notable methods

- **`balloon_success(self, title, message, links=None, sticky=False)`** - decorators: `@api.model`
- **`balloon_success_sticky(self, title, message, links=None)`** - decorators: `@api.model`
- **`balloon_warning(self, title, message, links=None, sticky=False)`** - decorators: `@api.model`
- **`balloon_warning_sticky(self, title, message, links=None)`** - decorators: `@api.model`
- **`balloon_danger(self, title, message, links=None, sticky=False)`** - decorators: `@api.model`
- **`balloon_danger_sticky(self, title, message, links=None)`** - decorators: `@api.model`
- **`balloon(self, title, message, links=None, type='success', sticky=False)`** - decorators: `@api.model`
  - Return action for message in balloon. Required: title, message Optional: links like: [{'label': cmd_id.name, 'model': 'hr.rfid.command', 'res_id': cmd.id, 'action': 'hr_rfid.hr_rfid_command_action'…

### `digest.digest` <a id='model-digest-digest'></a>
Python class `Digest` in `models/digest.py:8`.  Model.  Inherits: `digest.digest`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `kpi_hr_rfid_denied` | Boolean | Denied Events |  | ✓ | Include a 'Count of denied card swipes' KPI in the digest email — covers card-no |
| `kpi_hr_rfid_granted` | Boolean | Granted Events |  | ✓ | Include a 'Count of granted accesses' KPI in the digest email — covers normal an |
| `kpi_hr_rfid_system` | Boolean | System Events |  | ✓ | Include a 'Count of system events' KPI (controller power loss, tamper, etc.) in  |
| `kpi_hr_rfid_command` | Boolean | Commands executed |  | ✓ | Include a 'Count of commands sent to controllers' KPI in the digest email — usef |
| `kpi_hr_rfid_card` | Boolean | Active cards |  | ✓ | Include a 'Count of cards created this period' KPI in the digest email. |
| `kpi_hr_rfid_denied_value` | Integer | Kpi Hr Rfid Denied Value |  | - | Live count of denied access events during the digest window. |
| `kpi_hr_rfid_granted_value` | Integer | Kpi Hr Rfid Granted Value |  | - | Live count of granted access events during the digest window. |
| `kpi_hr_rfid_system_value` | Integer | Kpi Hr Rfid System Value |  | - | Live count of system events during the digest window. |
| `kpi_hr_rfid_command_value` | Integer | Kpi Hr Rfid Command Value |  | - | Live count of commands executed against controllers during the digest window. |
| `kpi_hr_rfid_card_value` | Integer | Kpi Hr Rfid Card Value |  | - | Live count of new cards created during the digest window. |

### `hr.department` <a id='model-hr-department'></a>
Python class `HrDepartment` in `models/hr_department.py:8`.  Model.  Inherits: `hr.department`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `hr_rfid_default_access_group` | Many2one → \`hr.rfid.access.group\` | Default Access Group |  | ✓ | New employees in this department will automatically receive this access group. T |
| `hr_rfid_allowed_access_groups` | Many2many → \`hr.rfid.access.group\` | Available Access Groups |  | ✓ | Define which access groups can be assigned to employees in this department. This |

#### Notable methods

- **`_check_hr_rfid_default_access_group(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.access.group.employee.rel`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``

### `hr.department.acc.grs` <a id='model-hr-department-acc-grs'></a>
Python class `HrDepartmentAccGrWizard` in `models/hr_department.py:92`.  TransientModel (wizard).  Description: *Department Access Group Configuration*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `dep_id` | Many2one → \`hr.department\` | Department | ✓ | ✓ | Department this wizard run targets. Set automatically from the selected record(s |
| `acc_grs` | Many2many → \`hr.rfid.access.group\` | Department Access Groups |  | ✓ | Select all access groups that should be available for employees in this departme |

#### Notable methods

- **`add_acc_grs(self)`** - decorators: -

### `hr.department.def.acc.gr` <a id='model-hr-department-def-acc-gr'></a>
Python class `HrDepartmentDefAccGrWizard` in `models/hr_department.py:131`.  TransientModel (wizard).  Description: *Set Department Default Access Group*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `dep_id` | Many2one → \`hr.department\` | Department | ✓ | ✓ | Department this wizard run targets. Set automatically from the selected record(s |
| `def_acc_gr` | Many2one → \`hr.rfid.access.group\` | New Default Access Group | ✓ | ✓ | Choose the access group that new employees will automatically receive. This shou |

#### Notable methods

- **`change_default_access_group(self)`** - decorators: -
- **`change_and_apply_def_acc_gr(self)`** - decorators: -

### `hr.department.mass.wiz` <a id='model-hr-department-mass-wiz'></a>
Python class `HrDepartmentMassAccGrsWiz` in `models/hr_department.py:170`.  TransientModel (wizard).  Description: *Bulk Access Group Management for Department*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `dep_id` | Many2one → \`hr.department\` | Department | ✓ | ✓ | Department this wizard run targets. Set automatically from the selected record(s |
| `acc_gr_ids` | Many2many → \`hr.rfid.access.group\` | Access Groups |  | ✓ | Select one or more access groups to add or remove from department employees. Thi |
| `expiration` | Datetime | Access Expiration |  | ✓ | Set an expiration date for these access rights (optional). Perfect for temporary |
| `exclude_ids` | Many2many → \`hr.employee\` | Exclude Employees |  | ✓ | Select specific employees who should NOT receive these access changes. Useful wh |

#### Notable methods

- **`add_acc_grs(self)`** - decorators: -
- **`remove_acc_grs(self)`** - decorators: -

### `hr.department.add.def.acc.grs` <a id='model-hr-department-add-def-acc-grs'></a>
Python class `HrDepartmentAddDefAccGrWizard` in `models/hr_department.py:230`.  TransientModel (wizard).  Description: *Add and Set Default Access Group*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `dep_id` | Many2one → \`hr.department\` | Department | ✓ | ✓ | Department this wizard run targets. Set automatically from the selected record(s |
| `acc_gr` | Many2one → \`hr.rfid.access.group\` | New Access Group | ✓ | ✓ | This access group will be added to the department's available groups AND set as  |

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:7`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `hr_rfid_pin_code` | Char | User pin code |  | ✓ | 4-digit PIN code for secure door access. Used in combination with RFID cards for |
| `hr_rfid_access_group_ids` | One2many → \`hr.rfid.access.group.employee.rel\` | Access Groups |  | ✓ | RFID access groups determine which doors and areas this employee can access. Acc |
| `hr_rfid_card_ids` | One2many → \`hr.rfid.card\` | RFID Card |  | ✓ | RFID cards assigned to this employee for access control. Multiple cards can be a |
| `hr_rfid_event_ids` | One2many → \`hr.rfid.event.user\` | RFID Events |  | ✓ | Access events log for this employee including door entries/exits, access denials |
| `in_zone_ids` | Many2many → \`hr.rfid.zone\` | Current Zones |  | - | Security zones where this employee is currently present. Automatically updated b |
| `employee_event_count` | Char | Event Count |  | - | Total number of RFID events recorded for this employee. Click to view detailed e |
| `employee_doors_count` | Char | Accessible Doors Count |  | - | Number of doors this employee can access based on their assigned access groups.  |

#### Notable methods

- **`button_employee_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_doors_list(self)`** - decorators: -
  - effects: `i18n`
- **`add_acc_gr(self, access_groups, expiration=None)`** - decorators: -
  - Add access groups to employees with optional expiration date.
  - touches: `hr.rfid.access.group.employee.rel`
- **`remove_acc_gr(self, access_groups)`** - decorators: -
  - Remove access groups from employees.
  - touches: `hr.rfid.access.group.employee.rel`
- **`get_doors(self, excluding_acc_grs=None, including_acc_grs=None)`** - decorators: -
  - Get all doors accessible by the employee based on their access groups.
  - touches: `hr.rfid.access.group`
- **`check_for_ts_inconsistencies_when_adding(self, new_acc_grs)`** - decorators: -
  - touches: `hr.rfid.access.group.door.rel`
- **`check_for_ts_inconsistencies(self)`** - decorators: -
  - touches: `hr.rfid.access.group.door.rel`
- **`check_access_group(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.door`
- **`_check_pin_code(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`generate_random_barcode_card(self)`** - decorators: -
  - Generate a new random barcode card for the employee.
  - effects: `write`
  - touches: `hr.rfid.card`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
- **`log_person_out(self, sids=None)`** - decorators: -

### `hr.rfid.access.group` <a id='model-hr-rfid-access-group'></a>
Python class `HrRfidAccessGroup` in `models/hr_rfid_access_group.py:15`.  Model.  Inherits: `mail.thread`.  Description: *Access Group*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | A descriptive name for this access group. This helps you identify and organize d |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company this access group belongs to. In multi-company environments, access  |
| `delay_between_events` | Integer | Delay Between Events |  | ✓ | Anti-passback feature: Sets the minimum time (in seconds) that must pass between |
| `employee_ids` | One2many → \`hr.rfid.access.group.employee.rel\` | Users |  | ✓ | Employees who are directly assigned to this access group. Each employee can have |
| `contact_ids` | One2many → \`hr.rfid.access.group.contact.rel\` | Contacts |  | ✓ | External contacts (visitors, contractors, service providers) who are assigned to |
| `door_ids` | One2many → \`hr.rfid.access.group.door.rel\` | Doors |  | ✓ | The physical doors that members of this access group can open. Each door can hav |
| `default_department_ids` | One2many → \`hr.department\` | Department (Default) |  | ✓ | Departments where this access group is automatically assigned to all employees.  |
| `department_ids` | Many2many → \`hr.department\` | Departments |  | ✓ | Departments that can optionally use this access group. While not automatically a |
| `inherited_ids` | Many2many → \`hr.rfid.access.group\` | Inherited access groups |  | ✓ | Other access groups whose permissions are included in this group. This creates a |
| `inheritor_ids` | Many2many → \`hr.rfid.access.group\` | Inheritors |  | ✓ | Access groups that inherit permissions from this group. Changes to this group's  |
| `all_door_ids` | Many2many → \`hr.rfid.access.group.door.rel\` | All doors |  | - | Complete list of doors accessible with this group, including both directly assig |
| `all_employee_ids` | Many2many → \`hr.rfid.access.group.employee.rel\` | All employees |  | - | Complete list of employees who have access to this group's doors, including both |
| `all_contact_ids` | Many2many → \`hr.rfid.access.group.contact.rel\` | All contacts |  | - | Complete list of external contacts who have access to this group's doors, includ |

#### Notable methods

- **`access_group_generate_name(self)`** - decorators: -
  - touches: `hr.rfid.access.group`
- **`check_doors(self)`** - decorators: -
  - effects: `log_error`, `raise:ValidationError`, `sudo`
  - touches: `ir.config_parameter`
- **`add_doors(self, door_ids, time_schedule=None, alarm_rights=False)`** - decorators: -
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.access.group.door.rel`, `hr.rfid.time.schedule`
- **`del_doors(self, door_ids)`** - decorators: -
  - touches: `hr.rfid.access.group.door.rel`
- **`get_all_doors(self)`** - decorators: -
- **`get_all_employees(self)`** - decorators: -
- **`get_all_contacts(self)`** - decorators: -
- **`door_ids_constrains(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.door`
- **`_compute_all_doors(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.door.rel`
- **`_compute_all_employees(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`_compute_all_contacts(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`_check_all_doors_rec(self, door_ids, checked_ids, acc_gr)`** - decorators: `@api.model`
  - touches: `hr.rfid.access.group`
- **`_check_all_employees_rec(self, emp_ids, checked_ids, acc_gr)`** - decorators: `@api.model`
  - touches: `hr.rfid.access.group`
- **`_check_all_contacts_rec(self, contact_ids, checked_ids, acc_gr)`** - decorators: `@api.model`
  - touches: `hr.rfid.access.group`
- **`check_for_ts_inconsistencies(self)`** - decorators: -
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.door.rel`
- **`_check_inherited_ids(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.access.group`
- **`_check_inherited_ids_rec(self, acc_gr, visited_groups, group_order, orig_id=None)`** - decorators: `@api.model`
  - touches: `hr.rfid.access.group`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.access.group`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``

### `hr.rfid.access.group.door.rel` <a id='model-hr-rfid-access-group-door-rel'></a>
Python class `HrRfidAccessGroupDoorRel` in `models/hr_rfid_access_group.py:453`.  Model.  Description: *Relation between access groups and doors*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `access_group_id` | Many2one → \`hr.rfid.access.group\` | Access Group | ✓ | ✓ | The access group that defines which doors can be accessed. This links doors to u |
| `door_id` | Many2one → \`hr.rfid.door\` | Door | ✓ | ✓ | The physical door or access point that members of this access group can open. Ea |
| `card_type` | Many2one → \`hr.rfid.card.type\` | *from door_id.card_type* |  | - | The type of RFID card required for this door (automatically determined by the do |
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` | Time schedule | ✓ | ✓ | Defines when this door can be accessed by this group. For example: "Monday-Frida |
| `alarm_rights` | Boolean | Alarm Rights | ✓ | ✓ | Allow users in this group to arm/disarm the door's alarm system. This is typical |

#### Notable methods

- **`_check_schedule_fits_the_controller(self)`** - decorators: `@api.constrains('door_id', 'time_schedule_id')`
  - Refuses a schedule above what the door's controller holds for a card: `hr.rfid.ctrl._card_schedule_max()` from `controllers/polimex.py` `CARD_SCHEDULE_MAX` (protocol D47: iCON130/iCON180/hotel 0-3, iCON110/iCON115/turnstile 0-15, others no known limit). The controller would otherwise refuse the whole card write (e=4). A controller that refuses a card anyway is explained in its system events by `hr.rfid.command._explain_a_refused_card_schedule()` (D1 with error 4 and a schedule above the limit).
  - effects: `raise:ValidationError`
- **`_check_shared_module_grant(self)`** - decorators: `@api.constrains`
  - A company the module is shared with may include its doors in its own access groups, but only with the unrestricted schedule: the controller's schedule slots belong to the owner company, and writing a…
  - effects: `raise:ValidationError`
- **`check_for_ts_inconsistencies(self, rels1, rels2)`** - decorators: `@api.model`
  - effects: `raise:ValidationError`
- **`create(self, vals)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.card.door.rel`
- **`write(self, vals)`** - decorators: -
  - effects: `raise:ValidationError`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
  - touches: `hr.rfid.card.door.rel`

### `hr.rfid.access.group.rel` <a id='model-hr-rfid-access-group-rel'></a>
Python class `HrRfidAccessGroupRelations` in `models/hr_rfid_access_group.py:577`.  AbstractModel.  Description: *Relation between access groups and employees*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `state` | Boolean | Active |  | ✓ | Indicates if this access group assignment is currently active. Automatically cal |
| `internal_state` | Boolean | Internal State |  | ✓ | Internal field used to track state changes and trigger card updates. This is man |
| `access_group_id` | Many2one → \`hr.rfid.access.group\` | Access Group | ✓ | ✓ | The access group that provides door permissions to the employee or contact. Mult |
| `activate_on` | Datetime | Activation Date |  | ✓ | The date and time when this access group becomes active for the user. Access wil |
| `expiration` | Datetime | Expiration Date |  | ✓ | The date and time when this access group expires and access is revoked. Leave em |
| `visits_counting` | Boolean | Enable Visit Counting |  | ✓ | Enable visit counting to limit the number of times this access can be used. Usef |
| `permitted_visits` | Integer | Permitted Visits |  | ✓ | Maximum number of visits allowed with this access group. After reaching this lim |
| `visits_counter` | Integer | Visit Counter |  | ✓ | Current number of visits used. When this reaches the permitted visits limit, acc |

#### Notable methods

- **`active_for_visits(self)`** - decorators: -
  - Whether every relation in ``self`` still grants access from the visits standpoint: counting disabled, unlimited (``permitted_visits`` <= 0) or visits remaining (``visits_counter < permitted_visits``).
- **`inc_visits(self)`** - decorators: -
- **`_compute_state(self)`** - decorators: `@api.depends`
- **`_check_expirations(self)`** - decorators: `@api.model`
- **`filter_by_door(self, door_id, active_only=True)`** - decorators: -
- **`ag_ready(self)`** - decorators: -
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``

### `hr.rfid.access.group.employee.rel` <a id='model-hr-rfid-access-group-employee-rel'></a>
Python class `HrRfidAccessGroupEmployeeRel` in `models/hr_rfid_access_group.py:749`.  Model.  Inherits: `hr.rfid.access.group.rel`.  Description: *Relation between access groups and employees*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | The employee who is assigned to this access group. Access rights are synchronize |

#### Notable methods

- **`_check_constrains_contacts(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - super-split (super `write`): pre=`raise:ValidationError` · post=-
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card.door.rel`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``

### `hr.rfid.access.group.contact.rel` <a id='model-hr-rfid-access-group-contact-rel'></a>
Python class `HrRfidAccessGroupContactRel` in `models/hr_rfid_access_group.py:832`.  Model.  Inherits: `hr.rfid.access.group.rel`.  Description: *Relation between access groups and contacts*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `contact_id` | Many2one → \`res.partner\` | Contact | ✓ | ✓ | The external contact (visitor, contractor, service provider) who is assigned to  |

#### Notable methods

- **`_check_constrains_contacts(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - super-split (super `write`): pre=`raise:ValidationError` · post=-
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card.door.rel`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``

### `hr.rfid.access.group.wizard` <a id='model-hr-rfid-access-group-wizard'></a>
Python class `HrRfidAccessGroupWizard` in `models/hr_rfid_access_group.py:917`.  TransientModel (wizard).  Description: *Add or remove doors to the access group*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `acc_gr_id` | Many2one → \`hr.rfid.access.group\` | Access Group | ✓ | ✓ | The access group you are currently configuring. This field is automatically set  |
| `door_ids` | Many2many → \`hr.rfid.door\` | Doors | ✓ | ✓ | Select the doors you want to add to this access group. You can select multiple d |
| `acc_gr_doors` | Many2many → \`hr.rfid.door\` | All access group doors |  | ✓ | This field stores the current doors in the access group, used internally to filt |
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` | Time Schedule | ✓ | ✓ | Select when these doors can be accessed. This schedule will apply to all selecte |
| `alarm_rights` | Boolean | Grant Alarm Rights | ✓ | ✓ | Enable this to allow users to arm/disarm the alarm system on these doors. Typica |

#### Notable methods

- **`add_doors(self)`** - decorators: -
- **`del_doors(self)`** - decorators: -

### `hr.rfid.card` <a id='model-hr-rfid-card'></a>
Python class `HrRfidCard` in `models/hr_rfid_card.py:17`.  Model.  Inherits: `mail.thread`.  Description: *Card*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | - | Display name of the card - shows either the card reference or card number |
| `internal_number` | Char | Internal Number |  | ✓ | Internal representation of the card number used by the system. This is automatic |
| `number` | Char | Card Number | ✓ | ✓ | The unique 10-digit number printed on or associated with the RFID card. This is  |
| `card_input_type` | Selection | Card Input Type |  | ✓ | Technical format of how the card number is encoded. Wiegand 34 bit (5d+5d) split |
| `card_reference` | Char | Card reference |  | ✓ | A friendly name or ID for this card, such as a badge number printed on the physi |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company this card belongs to. Cards are isolated between companies for secur |
| `card_type` | Many2one → \`hr.rfid.card.type\` | Card type |  | ✓ | Defines what kind of card this is (e.g., Employee Card, Visitor Card, Service Ca |
| `employee_id` | Many2one → \`hr.employee\` | Card Owner (Employee) |  | ✓ | The employee who owns this card. Each card must have either an employee or a con |
| `contact_id` | Many2one → \`res.partner\` | Card Owner (Partner) |  | ✓ | The external contact (visitor, contractor, supplier) who owns this card. Each ca |
| `activate_on` | Datetime | Activate on |  | ✓ | The date and time when this card becomes active and can be used. Perfect for tem |
| `deactivate_on` | Datetime | Deactivate on |  | ✓ | The date and time when this card will automatically expire and stop working. Use |
| `active` | Boolean | Active |  | ✓ | Controls whether this card is currently enabled. Inactive cards will not open an |
| `cloud_card` | Boolean | Cloud Card | ✓ | ✓ | Cloud cards are managed centrally by the system and work with online controllers |
| `door_rel_ids` | One2many → \`hr.rfid.card.door.rel\` | Door list |  | ✓ | Technical field linking this card to doors. The actual door access is determined |
| `door_ids` | Many2many → \`hr.rfid.door\` | Doors |  | - | List of all doors this card currently has access to, based on the owner's access |
| `door_count` | Char | Door Count |  | - | Total number of doors this card can open. Shown as a statistic on the card form. |
| `pin_code` | Char | Pin Code |  | - | The PIN code associated with this card's owner. Used for doors that require both |
| `barcode_number` | Char | Barcode Number |  | - | Hexadecimal representation of the card number, used for barcode printing and sca |
| `is_barcode` | Boolean | Is Barcode |  | - | Indicates if this card is configured as a barcode card type. |

#### Notable methods

- **`_compute_internal_number(self)`** - decorators: `@api.depends`
- **`get_import_templates(self)`** - decorators: `@api.model`
- **`get_owner(self, event_dict=None)`** - decorators: -
  - effects: `log_warn`
- **`get_potential_access_doors(self, access_groups=None)`** - decorators: -
  - Returns a list of tuples (door, time_schedule, alarm_rights) the card potentially has access to
  - effects: `sudo`
- **`door_compatible(self, door_id)`** - decorators: -
- **`card_ready(self)`** - decorators: -
- **`_compute_pin_code(self)`** - decorators: `@api.depends`
- **`_compute_barcode_number(self)`** - decorators: `@api.depends`
- **`_check_user(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_number(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_shared_module_collisions(self)`** - decorators: `@api.constrains`
- **`_compute_card_name(self)`** - decorators: `@api.depends`
- **`_compute_door_ids(self)`** - decorators: `@api.depends`
- **`create(self, vals)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card`, `hr.rfid.card.door.rel`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card.door.rel`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
- **`hex_to_w34(self, bc)`** - decorators: `@api.model`
- **`w34_to_hex(self, w34)`** - decorators: `@api.model`
- **`create_bc_card(self)`** - decorators: `@api.model`
  - effects: `raise:UserError`
  - touches: `hr.rfid.card`
- **`_update_cards(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.card`
- *2 more not listed*

### `hr.rfid.card.type` <a id='model-hr-rfid-card-type'></a>
Python class `HrRfidCardType` in `models/hr_rfid_card.py:466`.  Model.  Inherits: `mail.thread`.  Description: *Card Type*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Type Name | ✓ | ✓ | Name for this card type (e.g., "Employee Card", "Visitor Pass", "Contractor Badg |
| `card_ids` | One2many → \`hr.rfid.card\` | Cards |  | ✓ | All RFID cards that belong to this card type. You can see which cards are using  |
| `door_ids` | One2many → \`hr.rfid.door\` | Doors |  | ✓ | Doors that are configured to accept this card type. Only cards of this type will |

#### Notable methods

- **`check_and_fix_card_numer(self, number)`** - decorators: -
  - effects: `raise:UserError`
- **`unlink(self)`** - decorators: -
  - super-split (super `unlink`): pre=`raise:ValidationError` · post=-
  - effects: `raise:ValidationError`
- **`list_cards_from_this_type(self)`** - decorators: -

### `hr.rfid.command` <a id='model-hr-rfid-command'></a>
Python class `HrRfidCommands` in `models/hr_rfid_command.py:30`.  Model.  Inherits: `balloon.mixin`.  Description: *Command to controller*.  Default order: `create_date desc, id desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | - | User-friendly name combining command code and description |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module | ✓ | ✓ | The communication module (webstack) that connects to the physical controller. Th |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | The physical RFID controller device that manages card readers and access control |
| `cmd` | Selection | Command | ✓ | ✓ | The type of operation to perform on the controller. Commands starting with "F" r |
| `cmd_data` | Char | Command data |  | ✓ | Additional parameters or values sent with the command. This might include card n |
| `status` | Selection | Status |  | ✓ | Current execution state of the command: • Wait: Command is queued and waiting to |
| `error` | Selection | Error |  | ✓ | Detailed error information when a command fails. Common errors include: • Commun |
| `create_date` | Datetime | Create Date |  | ✓ |  |
| `ex_timestamp` | Datetime | Execution Time |  | ✓ | The exact date and time when the controller completed processing this command an |
| `request` | Char | Request |  | ✓ | Technical details: The raw JSON data sent to the module. This is mainly used for |
| `response` | Char | Response |  | ✓ | Technical details: The raw JSON response received from the module. Contains the  |
| `card_number` | Char | Card |  | ✓ | The RFID card number this command is related to. For example, when adding or rem |
| `retries` | Integer | Command retries |  | ✓ | Number of times the system has attempted to resend this command after failures.  |
| `pin_code` | Char | Pin Code (debug info) |  | ✓ | PIN code associated with the card for this command. Used for debugging purposes. |
| `ts_code` | Char | TS Code (debug info) |  | ✓ | Time Schedule code that defines when the card has access. Used for debugging pur |
| `rights_data` | Char | Rights Data (debug info) |  | ✓ | Binary representation of access rights being granted. Used for debugging purpose |
| `rights_mask` | Char | Rights Mask (debug info) |  | ✓ | Binary mask indicating which access rights are being modified. Used for debuggin |
| `alarm_right` | Boolean | Alarm Data (debug info) |  | ✓ | Indicates if this command includes alarm-related access rights. Used for debuggi |

#### Notable methods

- **`_compute_cmd_name(self)`** - decorators: `@api.depends`
- **`resend_action(self)`** - decorators: -
- **`read_controller_information_cmd(self, controller)`** - decorators: `@api.model`
- **`read_cards_cmd(self, controller, position=0, count=0)`** - decorators: `@api.model`
- **`read_readers_mode_cmd(self, controller)`** - decorators: `@api.model`
  - effects: `create`
- **`read_anti_pass_back_mode_cmd(self, controller)`** - decorators: `@api.model`
  - effects: `create`
- **`_system_init(self, controller, data)`** - decorators: `@api.model`
  - Data = 1, 2, 3, 4 ..type of system event operation
  - effects: `create`
- **`delete_all_cards_cmd(self, controller)`** - decorators: `@api.model`
- **`delete_all_events_cmd(self, controller)`** - decorators: `@api.model`
- **`create_d1_cmd(self, ws_id, ctrl_id, card_num, pin_code, ts_code, rights_data, rights_mask, alarm_right)`** - decorators: `@api.model`
  - effects: `create`
- **`_create_d1_cmd_relay(self, ws_id, ctrl_id, card_num, rights_data, rights_mask)`** - decorators: `@api.model`
  - effects: `create`
- **`add_remove_card(self, card_number, ctrl_id, pin_code, ts_code, rights_data, rights_mask, alarm_right)`** - decorators: `@api.model`
  - effects: `create`
  - touches: `hr.rfid.command`, `hr.rfid.ctrl`
- **`_add_remove_card_relay(self, card_number, ctrl_id, rights_data, rights_mask)`** - decorators: `@api.model`
  - touches: `hr.rfid.command`, `hr.rfid.ctrl`
- **`add_card(self, door_id, ts_id, pin_code, card_id, alarm_right)`** - decorators: `@api.model`
  - touches: `hr.rfid.card`, `hr.rfid.door`, `hr.rfid.time.schedule`
- **`_add_card_to_relay(self, door_id, card_id)`** - decorators: `@api.model`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card`, `hr.rfid.door`
- **`remove_card(self, door_id, pin_code, card_number=None, card_id=None)`** - decorators: `@api.model`
  - touches: `hr.rfid.card`, `hr.rfid.door`
- **`_remove_card_from_relay(self, door_id, card_number)`** - decorators: `@api.model`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.door`
- **`change_apb_flag(self, door, card, can_exit=True)`** - decorators: `@api.model`
  - touches: `hr.rfid.card.door.rel`
- **`_next_waiting(self, webstack)`** - decorators: `@api.model`
  - The next command to hand to a module: the oldest in `Wait`. The one rule
    for both deliveries - `hr.rfid.webstack.check_for_unsent_cmd` (the reply
    to a module's report) and the real-time channel
    (`_ws_publish_next_command`, `_ws_on_connect_sync`).
- **`_is_still_awaited(self)`** - decorators: -
  - True while less than `CMD_ANSWER_TIMEOUT_S` (15 s, `controllers/polimex.py`)
    has passed since `sent_at`: the module may still be carrying the command
    out. A command with no `sent_at` (from before the field existed) counts
    as overdue.
- **`_may_be_sent_again(self)`** - decorators: -
  - False for a `single_attempt` command and once `retries` reached
    `CMD_MAX_RETRIES` (5).
- **`_close_unanswered(self, error='30')`** - decorators: -
  - Gives a command up: `status='Failure'`, the reason in `error` ('30' no
    answer from the module, '20' the module said the controller was silent),
    `ex_timestamp`. The controller's log gets a system event naming the
    command, the card and the number of attempts ("No answer came to ..." -
    whether the controller carried it out is not known). Routine upkeep
    (`ROUTINE_COMMANDS`: D7, B3) gets its event once, when the controller
    stops answering (`_controller_was_answering`), not at every failure after
    it. The event is written inside a savepoint: a failure to write it is
    logged and never keeps the command open.
- **`_controller_was_answering(self)`** - decorators: -
  - True unless the controller's previous finished command was closed for no
    answer ('30' or '20'); True when there is none before.
  - effects: `write`
  - touches: `hr.rfid.event.system`
- **`_sync_clocks(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.webstack`
- *9 more not listed*

### `hr.rfid.command` <a id='model-hr-rfid-command'></a>
Python class `HrRfidCommandWs` in `models/hr_rfid_command_ws.py:29`.  Model.  Inherits: `hr.rfid.command`.

#### Notable methods

- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - super-split (super `create`): pre=- · post=`log_warn`, `sudo`
  - effects: `log_warn`, `sudo`
- **`_ws_republish_cron(self)`** - decorators: `@api.model`
  - Re-publish commands stuck in Process on real-time-online modules.
  - effects: `log_warn`, `sudo`

### `hr.rfid.ctrl.output.ts` <a id='model-hr-rfid-ctrl-output-ts'></a>
Python class `HrRfidControllerOutputTS` in `models/hr_rfid_ctrl.py:11`.  Model.  Description: *Output TS for Controllers*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `output_number` | Integer | Output number | ✓ | ✓ | Physical output number on the controller (1, 2, 3, etc.). Each output can contro |
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` | Time Schedule | ✓ | ✓ | Time schedule that controls when this output will be active. The output will aut |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | Controller that owns this output-to-time-schedule binding. Cascade on delete — t |
| `output_count` | Integer | *from controller_id.outputs* |  | - | Number of physical outputs reported by the controller. Used to validate that out |
| `max_ts` | Integer | *from controller_id.time_schedules* |  | - | Highest time-schedule slot the controller supports. Used to validate that the as |
| `time_schedule_number` | Integer | *from time_schedule_id.number* |  | - | Numeric slot of the linked time schedule, shown for quick reference in lists. |

#### Notable methods

- **`_constrains_output_number_ts(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`name_get(self)`** - decorators: -

### `hr.rfid.ctrl.input.mask` <a id='model-hr-rfid-ctrl-input-mask'></a>
Python class `HrRfidCtrlInputMask` in `models/hr_rfid_ctrl.py:67`.  Model.  Description: *Input Mask for Controllers*.  Default order: `i_number`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `i_number` | Integer | Number | ✓ | ✓ | Physical input number on the controller. Each input can monitor different sensor |
| `i_mask` | Boolean | Mask (NC/NO) | ✓ | ✓ | Input type configuration: Checked = Normally Closed (NC), Unchecked = Normally O |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | Controller that owns this input-mask row. Cascade on delete — the row disappears |
| `input_count` | Integer | *from controller_id.inputs* |  | - | Total number of physical inputs on the controller — used to display only the mas |

#### Notable methods

- **`_generate_input_masks(self, ctrl_id, masks)`** - decorators: `@api.model`
  - effects: `sudo`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``

### `hr.rfid.ctrl` <a id='model-hr-rfid-ctrl'></a>
Python class `HrRfidController` in `models/hr_rfid_ctrl.py:120`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Controller*.  Default order: `webstack_id, ctrl_id`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | A descriptive name for this controller (e.g., "Main Entrance Controller", "2nd F |
| `ctrl_id` | Integer | ID behind IP Module |  | ✓ | Unique identifier for this controller when multiple controllers are connected to |
| `hw_version` | Selection | Hardware Type |  | ✓ | Hardware model of the controller. Different models support different features: d |
| `serial_number` | Char | Serial |  | ✓ | Factory-assigned unique serial number. This 4-character code is used for hardwar |
| `sw_version` | Char | Version |  | ✓ | Firmware version running on the controller. Format: X.YZ where X is major versio |
| `inputs` | Integer | Inputs |  | ✓ | Number of physical input connections available on this controller. Inputs are us |
| `inputs_mask` | Integer | Inputs Mask |  | ✓ | Binary mask that defines the type of each input (NC/NO). Each bit represents one |
| `input_mask_ids` | One2many → \`hr.rfid.ctrl.input.mask\` | Input Masks |  | ✓ | Per-input NC/NO configuration. One row per physical input. Toggling a row sends  |
| `input_states` | Integer | Input States |  | ✓ | Current state of all inputs as a binary value. Each bit represents one input: 1  |
| `outputs` | Integer | Outputs |  | ✓ | Number of physical output connections (relays) available on this controller. Out |
| `output_states` | Integer | Output States |  | ✓ | Current state of all outputs as a binary value. Each bit represents one output:  |
| `output_ts_ids` | One2many → \`hr.rfid.ctrl.output.ts\` | Output's Time schedules |  | ✓ | Control the Output's Time schedules of the controller. You can add PLC-like logi |
| `relay_output_mask` | Boolean | Relay Output Mask |  | ✓ | Relay output configuration for relay controllers. When enabled, relay outputs op |
| `readers` | Integer | Readers |  | ✓ | Number of RFID card readers that can be connected to this controller. Each reade |
| `time_schedules` | Integer | Time Schedules |  | ✓ | Maximum number of time schedules this controller can store. Time schedules defin |
| `io_table_lines` | Integer | IO Table Lines |  | ✓ | Number of programmable logic lines in the I/O table. Each line can contain rules |
| `alarm_lines` | Integer | Alarm Lines |  | ✓ | Number of dedicated alarm zone inputs on this controller. Each zone can monitor  |
| `alarm_line_states` | Char | Alarm Line States |  | ✓ | Real-time status of each alarm zone as hexadecimal values. Shows if zones are ar |
| `alarm_lines_setup` | Char | Alarm Lines Setup |  | ✓ | Configuration data for alarm zones in hexadecimal format. Defines which zones ar |
| `alarm_sensor_events` | Boolean | Alarm Sensor Events |  | ✓ | When enabled, the controller reports all sensor state changes as events, even wh |
| `siren_state` | Boolean | Siren State |  | - | Current state of the alarm siren. True = Siren is active/sounding, False = Siren |
| `emergency_group_id` | Many2one → \`hr.rfid.ctrl.emergency.group\` | Emergency Group |  | ✓ | Emergency group this controller belongs to. When any controller in the group ent |
| `emergency_state` | Selection | Emergency State |  | - | Emergency mode status: - No Emergency: Normal operation - Group Emergency: Activ |
| `mode` | Integer | Controller Mode |  | ✓ | Operating mode that defines how many doors/devices this controller manages and h |
| `mode_selection` | Selection | Controller mode | ✓ | - | Door control mode for standard access controllers. One door mode uses all resour |
| `mode_selection_4` | Selection | Doors mode | ✓ | - | Door control mode for advanced access controllers that support up to 4 doors. Ea |
| `mode_selection_31` | Selection | Relays mode | ✓ | - | Relay configuration mode: - 1 x 32: Single bank of 32 relays - 2 x 16: Two indep |
| `external_db` | Boolean | External DB |  | ✓ | External database mode. When on, the controller does not keep the card list in i |
| `relay_time_factor` | Selection | Relay Time Factor |  | ✓ | Time unit for relay activation duration. When set to "1 second", relay timers co |
| `dual_person_mode` | Boolean | Dual Person Mode |  | ✓ | Security feature requiring two authorized persons to badge within a time window  |
| `interlocking_mode` | Boolean | Interlocking Mode |  | ✓ | Interlocking (mantrap): only one of the controller's doors may be open at a time |
| `max_cards_count` | Integer | Maximum Cards |  | ✓ | Maximum number of access cards this controller can store in its internal memory. |
| `cards_count` | Integer | Cards Count |  | ✓ | Current number of access cards stored in the controller's memory. When this appr |
| `max_events_count` | Integer | Maximum Events |  | ✓ | Maximum number of access events (card swipes, door openings, alarms) the control |
| `hotel_readers` | Integer | Hotel readers |  | ✓ | Number of hotel-style card readers connected. These readers support card inserti |
| `hotel_readers_card_presence` | Integer | Hotel readers card presence |  | ✓ | Binary representation of which hotel readers currently have a card inserted. Eac |
| `hotel_readers_buttons_pressed` | Integer | Hotel readers buttons pressed |  | ✓ | Binary representation of which service buttons are currently pressed on hotel re |
| `io_table` | Char | Input/Output Table |  | ✓ | Programmable logic table in hexadecimal format. Defines automated responses link |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module | ✓ | ✓ | IP communication module (webstack) this controller is connected to. The webstack |
| `door_ids` | One2many → \`hr.rfid.door\` | Controlled Doors |  | ✓ | Doors managed by this controller. Each door has its own reader, lock, and access |
| `reader_ids` | One2many → \`hr.rfid.reader\` | Controlled Readers |  | ✓ | RFID card readers connected to this controller. Readers scan access cards and se |
| `alarm_line_ids` | One2many → \`hr.rfid.ctrl.alarm\` | Controlled Alarm Lines |  | ✓ | Security alarm zones monitored by this controller. Each line can connect to diff |
| `read_b3_cmd` | Boolean | Read Controller Status |  | ✓ | When enabled, the system will periodically read the controller status (inputs, o |
| `sensor_ids` | One2many → \`hr.rfid.ctrl.th\` | Sensors |  | ✓ | Temperature and humidity sensors connected to this controller. Used for environm |
| `temperature` | Float | Temperature |  | ✓ | Current temperature reading from the controller's internal or primary external s |
| `humidity` | Float | Humidity |  | ✓ | Current relative humidity percentage from the controller's internal or primary e |
| `event_interval` | Integer | Event Interval |  | - | Interval in minutes for automatic temperature/humidity event reporting. Set to 0 |
| `high_temperature` | Float | High Temperature |  | ✓ | Upper temperature threshold in Celsius. When exceeded, the controller triggers a |
| `low_temperature` | Float | Low Temperature |  | ✓ | Lower temperature threshold in Celsius. When temperature drops below this value, |
| `hysteresis` | Float | Hysteresis |  | ✓ | Temperature hysteresis (dead band) in Celsius to prevent alarm flickering. The t |
| `system_voltage` | Float | System Voltage |  | ✓ | Current voltage level of the controller's internal power supply in VDC. Normal r |
| `input_voltage` | Float | Input Voltage |  | ✓ | Voltage level supplied to the controller from the external power source in VDC.  |
| `last_f0_read` | Datetime | Last System Information Update |  | ✓ | Date and time when the controller's system information (hardware details, capabi |
| `commands_count` | Char | Commands count |  | - | Total number of commands (pending and executed) for this controller. High number |
| `system_event_count` | Char | System Events count |  | - | Number of system events (errors, status changes, communication issues) logged by |
| `user_event_count` | Char | User events count |  | - | Number of user access events (card swipes, access granted/denied, door forced) r |
| `readers_count` | Char | Readers count |  | - | Number of card readers configured for this controller. Typically matches the num |
| `doors_count` | Char | Doors count |  | - | Number of doors managed by this controller. Depends on the controller mode: sing |
| `alarm_line_count` | Char | Alarm line count |  | - | Number of alarm zones configured for this controller. Each zone can monitor diff |
| `default_io_table` | Char | Default Io Table |  | - | Factory default I/O table configuration for this controller model and mode. Used |

#### Notable methods

- **`_compute_event_interval(self)`** - decorators: `@api.depends`
- **`_check_value(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_value(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_value(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_value(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_mode(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_compute_emergency_state(self)`** - decorators: `@api.depends`
- **`_compute_controller_mode(self)`** - decorators: `@api.depends`
- **`_compute_controller_mode_31(self)`** - decorators: `@api.depends`
- **`_compute_counts(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.command`, `hr.rfid.event.system`, `hr.rfid.event.user`
- **`_compute_siren_state(self)`** - decorators: `@api.depends`
- **`_compute_default_io_table(self)`** - decorators: `@api.depends`
- **`return_action_to_open(self)`** - decorators: -
  - This opens the xml view specified in xml_id for the current app
  - touches: `ir.actions.act_window`
- **`update_ctrl_alarm_lines(self)`** - decorators: `@api.model`
  - effects: `sudo`
  - touches: `hr.rfid.ctrl`
- **`button_reload_cards(self)`** - decorators: -
  - touches: `hr.rfid.card.door.rel`, `hr.rfid.command`
- **`change_io_table(self, new_io_table, line=0, no_command=False)`** - decorators: -
  - effects: `raise:ValidationError`
- **`is_alarm_ctrl(self, hw_version=None)`** - decorators: -
- **`is_relay_ctrl(self, hw_version=None)`** - decorators: -
- **`is_vending_ctrl(self, hw_version=None)`** - decorators: -
- **`is_turnstile_ctrl(self, hw_version=None)`** - decorators: -
- *40 more not listed*

### `hr.rfid.ctrl.alarm` <a id='model-hr-rfid-ctrl-alarm'></a>
Python class `HrRfidCtrlAlarm` in `models/hr_rfid_ctrl_alarm.py:6`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Controller Alarm Lines*.  Default order: `controller_id, line_number`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Enter a descriptive name for this alarm sensor (e.g., 'Main Entrance Motion Dete |
| `line_number` | Integer | Line Number |  | ✓ | The physical input number on the controller where this sensor is connected (1-16 |
| `state` | Selection | State |  | - | Current status of the alarm sensor: • Unknown - Communication lost with sensor • |
| `armed` | Selection | Armed |  | ✓ | Security status of this alarm line: • No Alarm functionality - This line is not  |
| `enableAC` | Boolean | Integrate with Access control |  | ✓ | When enabled, this alarm line will work together with door access control: • Aut |
| `enableDC` | Boolean | Include Door contact |  | ✓ | Monitor the door's open/closed status as part of this alarm: • When armed, an op |
| `enabled` | Boolean | Enabled |  | ✓ | Master switch for this alarm line: • ON - The sensor is active and can trigger a |
| `siren_state` | Boolean | *from controller_id.siren_state* |  | - | Shows whether the alarm siren is currently sounding: • ON - Siren is active (lou |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | The RFID controller device that monitors this alarm sensor. Each controller can  |
| `control_output` | Integer | Control Output |  | ✓ | Technical field: The output number used to arm/disarm this line remotely |
| `door_id` | Many2one → \`hr.rfid.door\` | Door |  | ✓ | Link this alarm to a specific door for integrated security: • The alarm can auto |
| `user_event_count` | Integer | User Event Count |  | - | Number of alarm events triggered by user actions (e.g., motion detected, door op |
| `system_event_count` | Integer | System Event Count |  | - | Number of technical events for this alarm line (e.g., sensor faults, communicati |
| `alarm_group_id` | Many2one → \`hr.rfid.ctrl.alarm.group\` | Alarm Group |  | ✓ | Assign this alarm to a group for easier management: • Arm/disarm multiple alarms |

#### Notable methods

- **`_compute_states(self)`** - decorators: `@api.depends`
- **`_compute_armed(self)`** - decorators: `@api.depends`
- **`return_action_to_open(self)`** - decorators: -
  - touches: `ir.actions.act_window`
- **`disarm(self)`** - decorators: -
- **`arm(self)`** - decorators: -
- **`siren_off(self)`** - decorators: -
- **`siren_on(self)`** - decorators: -
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``

### `hr.rfid.ctrl.alarm.group` <a id='model-hr-rfid-ctrl-alarm-group'></a>
Python class `HrRfidCtrlAlarmGroup` in `models/hr_rfid_ctrl_alarm_group.py:4`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Alarm system groups*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Enter a descriptive name for this alarm group (e.g., 'First Floor Alarms', 'Ware |
| `color` | Integer | Color Index |  | ✓ | Choose a color to visually distinguish this group in the hierarchy view. This he |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company that owns this alarm group. Used in multi-company setups to separate |
| `state` | Selection | State |  | ✓ | Overall security status of all alarms in this group: • No Alarm functionality -  |
| `parent_id` | Many2one → \`hr.rfid.ctrl.alarm.group\` | Parent |  | ✓ | Parent group for creating hierarchical alarm structures. For example: • Building |
| `child_ids` | One2many → \`hr.rfid.ctrl.alarm.group\` | Child |  | ✓ | Sub-groups under this group. When you arm/disarm this group, all child groups wi |
| `alarm_line_ids` | One2many → \`hr.rfid.ctrl.alarm\` | Alarm Line | ✓ | ✓ | Individual alarm sensors that belong to this group. You can: • Add multiple sens |

#### Notable methods

- **`create_child(self)`** - decorators: -
- **`open_alarm_line_list_action(self)`** - decorators: -
- **`_compute_states(self)`** - decorators: `@api.depends`
- **`disarm(self)`** - decorators: -
- **`arm(self)`** - decorators: -

### `hr.rfid.ctrl.emergency.group` <a id='model-hr-rfid-ctrl-emergency-group'></a>
Python class `EmergencyGroup` in `models/hr_rfid_ctrl_emergency_group.py:4`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Emergency signal distribution group*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | Name of the emergency group (e.g., 'Emergency Floor 1', 'Building A Emergency'). |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns this emergency group. Used to separate emergency groups betwee |
| `controller_ids` | One2many → \`hr.rfid.ctrl\` | Controller |  | ✓ | List of controllers that belong to this emergency group. When emergency mode is  |
| `state` | Selection | State |  | - | Current state of the emergency group: • Normal: All controllers operating normal |

#### Notable methods

- **`_compute_state(self)`** - decorators: `@api.depends`
- **`emergency_on(self)`** - decorators: -
- **`emergency_off(self)`** - decorators: -

### `hr.rfid.ctrl.io.table.row` <a id='model-hr-rfid-ctrl-io-table-row'></a>
Python class `HrRfidCtrlIoTableRow` in `models/hr_rfid_ctrl_iotable.py:5`.  TransientModel (wizard).  Description: *Controller IO Table row*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `event_number` | Selection | Event Number | ✓ | ✓ | What the outs are set to when this event occurs |
| `out8` | Integer | Out8 | ✓ | ✓ | Output #8 setting for this event (0-99). Bound to a relay / output by the contro |
| `out7` | Integer | Out7 | ✓ | ✓ | Output #7 setting for this event (0-99). |
| `out6` | Integer | Out6 | ✓ | ✓ | Output #6 setting for this event (0-99). |
| `out5` | Integer | Out5 | ✓ | ✓ | Output #5 setting for this event (0-99). |
| `out4` | Integer | Out4 | ✓ | ✓ | Output #4 setting for this event (0-99). |
| `out3` | Integer | Out3 | ✓ | ✓ | Output #3 setting for this event (0-99). |
| `out2` | Integer | Out2 | ✓ | ✓ | Output #2 setting for this event (0-99). |
| `out1` | Integer | Out1 | ✓ | ✓ | Output #1 setting for this event (0-99). |

### `hr.rfid.ctrl.io.table.wiz` <a id='model-hr-rfid-ctrl-io-table-wiz'></a>
Python class `HrRfidCtrlIoTableWiz` in `models/hr_rfid_ctrl_iotable.py:83`.  TransientModel (wizard).  Description: *Controller IO Table Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | Controller being edited. Set automatically from the active record when the wizar |
| `io_row_ids` | Many2many → \`hr.rfid.ctrl.io.table.row\` | IO Table |  | ✓ | One row per event code (Duress, Card OK, etc.) with the values written to each o |
| `outs` | Integer | Outs |  | ✓ | Number of output columns shown in the table (4 for relay controllers, otherwise  |

#### Notable methods

- **`load_system_defaults(self)`** - decorators: -
  - effects: `sudo`
- **`save_table(self)`** - decorators: -
  - effects: `raise:ValidationError`

### `hr.rfid.reader` <a id='model-hr-rfid-reader'></a>
Python class `HrRfidReader` in `models/hr_rfid_ctrl_reader.py:4`.  Model.  Inherits: `mail.thread`.  Description: *Reader*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Reader name |  | ✓ | Give this reader a descriptive name to easily identify it. For example: "Main En |
| `number` | Integer | Number |  | ✓ | The physical reader number on the controller device (1-4). This corresponds to t |
| `reader_type` | Selection | Reader type | ✓ | ✓ | Defines the direction of access: • In: Entry reader - used when entering an area |
| `mode` | Selection | Reader mode | ✓ | ✓ | Defines the authentication method required: • Card Only: Just scan your RFID car |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller |  | ✓ | The access control device that manages this reader. Controllers handle communica |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module |  | - | The network module (webstack) that connects this reader's controller to the syst |
| `user_event_ids` | One2many → \`hr.rfid.event.user\` | Events |  | ✓ | History of all access events (card scans, entries, exits) that occurred at this  |
| `door_ids` | Many2many → \`hr.rfid.door\` | Doors |  | ✓ | Select which doors this reader can control. When access is granted, these doors  |
| `door_id` | Many2one → \`hr.rfid.door\` | Door |  | - | The primary door controlled by this reader. This field is shown when the reader  |
| `door_count` | Char | Door Count |  | - | Number of doors controlled by this reader. |
| `user_event_count` | Char | Event Count |  | - | Total number of access events recorded by this reader. |

#### Notable methods

- **`_compute_counts(self)`** - decorators: `@api.depends`
- **`_compute_reader_name(self)`** - decorators: `@api.depends`
- **`_compute_reader_door(self)`** - decorators: `@api.depends`
- **`write(self, vals)`** - decorators: -
  - super-split (super `write`): pre=`raise:ValidationError` · post=-
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.command`
- **`button_door_list(self)`** - decorators: -
  - effects: `i18n`
- **`button_event_list(self)`** - decorators: -
  - effects: `i18n`

### `hr.rfid.ctrl.th` <a id='model-hr-rfid-ctrl-th'></a>
Python class `CtrlTemperatureAndHumidity` in `models/hr_rfid_ctrl_th.py:13`.  Model.  Inherits: `mail.thread`.  Description: *Temperature and Humidity Sensor*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `active` | Boolean | Active |  | ✓ | When unchecked, this sensor will be hidden and stop recording data. You can reac |
| `name` | Char | Sensor Name | ✓ | ✓ | Give this sensor a descriptive name (e.g., "Server Room Temperature", "Warehouse |
| `uid` | Char | Serial Number |  | ✓ | The unique serial number of this temperature/humidity sensor. This is set by the |
| `internal_number` | Char | Internal ID |  | ✓ | The internal identification number assigned by the controller. This is used for  |
| `temperature` | Float | Current Temperature |  | ✓ | The most recent temperature reading from this sensor (in Celsius). This value up |
| `humidity` | Float | Current Humidity |  | ✓ | The most recent humidity reading from this sensor (as a percentage). This value  |
| `sensor_number` | Integer | Sensor Number | ✓ | ✓ | The position number of this sensor in the controller's sensor list. This is auto |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | The RFID controller that manages this temperature/humidity sensor. Each sensor m |
| `door_id` | Many2one → \`hr.rfid.door\` | Associated Door |  | ✓ | Link this sensor to a specific door to monitor its environmental conditions. Thi |
| `th_log_ids` | One2many → \`hr.rfid.ctrl.th.log\` | Sensor Logs |  | ✓ | Historical temperature and humidity readings from this sensor. Use the "View Log |
| `log_every_read` | Boolean | Log All Readings |  | ✓ | Check this box to save every reading from the sensor, even if values haven't cha |

#### Notable methods

- **`button_log(self)`** - decorators: -
  - effects: `i18n`
- **`create_d1_temperature_cmd(self)`** - decorators: -
  - touches: `hr.rfid.command`
- **`write(self, vals)`** - decorators: -
  - super-split (super `write`): pre=`sudo` · post=-
  - effects: `sudo`
  - touches: `hr.rfid.ctrl.th.log`
- **`write_log(self, timestamp, values)`** - decorators: -
  - effects: `sudo`, `with_context`
  - touches: `hr.rfid.ctrl.th.log`

### `hr.rfid.ctrl.th.log` <a id='model-hr-rfid-ctrl-th-log'></a>
Python class `CtrlTemperatureAndHumidityLog` in `models/hr_rfid_ctrl_th_log.py:4`.  Model.  Description: *Temperature and Humidity Reading History*.  Default order: `event_time desc, id`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `temperature` | Float | Temperature (°C) |  | ✓ | The temperature reading at this point in time (in Celsius). These historical val |
| `humidity` | Float | Humidity (%) |  | ✓ | The humidity reading at this point in time (as a percentage). Track changes over |
| `th_id` | Many2one → \`hr.rfid.ctrl.th\` | Sensor | ✓ | ✓ | The temperature/humidity sensor that recorded this reading. Each log entry is li |
| `event_time` | Datetime | Reading Time |  | ✓ | The exact date and time when this temperature/humidity reading was taken. Use th |

### `hr.rfid.time.schedule` <a id='model-hr-rfid-time-schedule'></a>
Python class `HrRfidTimeSchedule` in `models/hr_rfid_ctrl_time_schedule.py:17`.  Model.  Inherits: `mail.thread`.  Description: *Time Schedule*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Give this time schedule a descriptive name that helps identify when it's used. F |
| `number` | Integer | TS Number | ✓ | ✓ | System-assigned time schedule number (0-15). TS 0 is reserved for "Not using TS" |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company this time schedule belongs to. Time schedules are company-specific a |
| `is_empty` | Boolean | Is Empty |  | - | Indicates whether this time schedule has any active time periods defined. Empty  |
| `ts_data` | Char | Ts Data |  | ✓ | Internal representation of the time schedule data in hexadecimal format. Contain |
| `access_group_door_ids` | One2many → \`hr.rfid.access.group.door.rel\` | Access Group/Door Combinations |  | ✓ | Shows all doors and access groups that use this time schedule. This helps you un |
| `controller_ids` | Many2many → \`hr.rfid.ctrl\` | Controller |  | ✓ | RFID controllers that have this time schedule programmed. The schedule is automa |

#### Notable methods

- **`_compute_is_empty(self)`** - decorators: `@api.depends`
- **`reset_ts_data(self)`** - decorators: -
- **`unlink(self)`** - decorators: -
  - effects: `raise:ValidationError`
- **`_default_for_company(self, company=None)`** - decorators: `@api.model`
  - The working time to offer, from the right company.
  - effects: `raise:UserError`
- **`set_company_ts(self)`** - decorators: `@api.model`
  - effects: `sudo`
  - touches: `hr.rfid.time.schedule`, `res.company`

### `hr.rfid.ctrl.ts.line` <a id='model-hr-rfid-ctrl-ts-line'></a>
Python class `HrRfidTimeScheduleWizDayLine` in `models/hr_rfid_ctrl_time_schedule.py:139`.  TransientModel (wizard).  Description: *Time Schedule line Wizard*.  Default order: `day`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `display_name` | Char | Display Name |  | - | Display name showing the day and interval number for easy identification. |
| `begin` | Float | Begin |  | ✓ | Start time for this access period. Enter in 24-hour format (e.g., 8.5 for 8:30 A |
| `end` | Float | End |  | ✓ | End time for this access period. Enter in 24-hour format (e.g., 17.5 for 5:30 PM |
| `number` | Integer | Number |  | ✓ | Interval number (1-4). Each day can have up to 4 separate access periods. For ex |
| `day_number` | Integer | Day Number |  | ✓ | Internal day number (0-7) used for data processing. |
| `day` | Selection | Day |  | ✓ | Day of the week or Holiday. The Holiday setting applies to all dates marked as h |
| `week_id` | Many2one → \`hr.rfid.ctrl.ts.week.wiz\` | Week |  | ✓ | Reference to the parent time schedule week wizard. |

#### Notable methods

- **`_check_description(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_compute_display_name(self)`** - decorators: `@api.depends`
- **`_get_float_to_str(self, f)`** - decorators: `@api.model`
- **`get_interval_str(self)`** - decorators: -
- **`get_set_str(self)`** - decorators: -

### `hr.rfid.ctrl.ts.week.wiz` <a id='model-hr-rfid-ctrl-ts-week-wiz'></a>
Python class `HrRfidTimeScheduleWizWeek` in `models/hr_rfid_ctrl_time_schedule.py:218`.  TransientModel (wizard).  Description: *Time Schedule Week Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `ts_id` | Many2one → \`hr.rfid.time.schedule\` | Time Schedule |  | ✓ | The time schedule being edited. This wizard allows you to configure when access  |
| `interval_ids` | One2many → \`hr.rfid.ctrl.ts.line\` | Interval |  | ✓ | Define up to 4 time periods per day when access is allowed. The schedule works a |

#### Notable methods

- **`_default_interval_ids(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.ctrl.ts.line`, `hr.rfid.time.schedule`
- **`_check_interval_ids(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`save_ts(self)`** - decorators: -
  - effects: `sudo`

### `hr.rfid.door` <a id='model-hr-rfid-door'></a>
Python class `HrRfidDoor` in `models/hr_rfid_door.py:15`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Door*.  Default order: `controller_id,number`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Enter a descriptive name for this door (e.g. "Main Entrance", "Server Room", "Wa |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company that owns or manages this door. This is automatically determined fro |
| `number` | Integer | Number | ✓ | ✓ | The door number as configured in the physical controller (1-4). This must match  |
| `card_type` | Many2one → \`hr.rfid.card.type\` | Card type |  | ✓ | Select which type of RFID cards can open this door (e.g. Employee cards, Visitor |
| `apb_mode` | Boolean | APB Mode |  | ✓ | Enable Anti-Passback (APB) mode to prevent card sharing. When active, a person m |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller |  | ✓ | The physical RFID controller device that manages this door. This is set automati |
| `hotel_readers` | Integer | *from controller_id.hotel_readers* |  | - | Number of hotel-mode readers connected to the controller. Used for hotel room ma |
| `access_group_ids` | One2many → \`hr.rfid.access.group.door.rel\` | Door Access Groups |  | ✓ | Access groups that include this door. Members of these groups will have access t |
| `reader_ids` | Many2many → \`hr.rfid.reader\` | Readers |  | ✓ | RFID card readers that control this door. Typically includes one reader on each  |
| `card_rel_ids` | One2many → \`hr.rfid.card.door.rel\` | Cards |  | ✓ | All RFID cards that currently have access to this door. This list is automatical |
| `zone_ids` | Many2many → \`hr.rfid.zone\` | Zones |  | ✓ | Security zones that include this door. Zones are used to group doors by area (e. |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module |  | - | The webstack module that connects this door's controller to the system. This man |
| `lock_time` | Integer | Lock Time |  | - | How long the door stays unlocked after a valid card is presented (in seconds). C |
| `lock_state` | Boolean | Lock State |  | - | Current state of the door lock. When checked, the door is unlocked. When uncheck |
| `lock_output` | Integer | Lock Output |  | - | The physical output number on the controller that controls this door's lock mech |
| `alarm_line_ids` | One2many → \`hr.rfid.ctrl.alarm\` | Alarm Lines |  | ✓ | Alarm sensors connected to this door (e.g. door forced open sensor, door held op |
| `alarm_state` | Selection | Alarm State |  | - | Current alarm status of this door. Armed: alarms are active and will trigger ale |
| `siren_state` | Boolean | Siren State |  | - | Indicates if the alarm siren is currently active. When checked, the siren is sou |
| `emergency_state` | Selection | Emergency State |  | - | Emergency unlock status. Off: normal operation. Soft: doors unlocked via softwar |
| `th_id` | One2many → \`hr.rfid.ctrl.th\` | Temperature/Humidity Sensor |  | ✓ | Temperature and humidity sensor associated with this door. Used for environmenta |
| `temperature` | Float | Temperature |  | - | Current temperature reading from the door's environmental sensor (in Celsius). U |
| `humidity` | Float | Humidity |  | - | Current humidity reading from the door's environmental sensor (percentage). Impo |
| `hb_dnd` | Boolean | DND button pressed |  | - | Do Not Disturb status for hotel mode. When checked, indicates the room occupant  |
| `hb_clean` | Boolean | Clean button pressed |  | - | Room cleaning request for hotel mode. When checked, indicates the room occupant  |
| `hb_card_present` | Boolean | Present card in reader |  | - | Hotel mode indicator showing if a card is currently inserted in the room's energ |
| `access_group_count` | Char | Access Group Count |  | - | Number of access groups that include this door. Click to see all access groups. |
| `reader_count` | Char | Reader Count |  | - | Number of card readers connected to this door. Typically 2 (one for entry, one f |
| `card_count` | Char | Card Count |  | - | Total number of RFID cards that have access to this door. Click to see all autho |
| `zone_count` | Char | Zone Count |  | - | Number of security zones this door belongs to. Click to see all zones. |
| `alarm_lines_count` | Char | Alarm Lines Count |  | - | Number of alarm sensors connected to this door. Click to view alarm configuratio |
| `user_event_count` | Char | User Event Count |  | - | Total number of user access events (card swipes, entries, exits) for this door.  |
| `system_event_count` | Char | System Event Count |  | - | Total number of system events (alarms, errors, configuration changes) for this d |

#### Notable methods

- **`compute_company_id(self)`** - decorators: `@api.depends`
- **`_compute_counts(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.event.system`, `hr.rfid.event.user`
- **`_compute_hotel_buttons(self)`** - decorators: `@api.depends`
- **`_compute_alarm_state(self)`** - decorators: `@api.depends`
- **`_compute_lock_time(self)`** - decorators: `@api.depends`
- **`_compute_lock_output(self)`** - decorators: `@api.depends`
- **`_compute_lock_status(self)`** - decorators: `@api.depends`
- **`process_event(self, event)`** - decorators: -
- **`get_cards(self, access_groups=None, all=True)`** - decorators: -
  - Returns a list of tuples (card, time_schedule) for which the card potentially has access to this door
  - touches: `hr.rfid.access.group.door.rel`
- **`open_door(self)`** - decorators: -
- **`close_door(self)`** - decorators: -
- **`arm_door(self)`** - decorators: -
- **`disarm_door(self)`** - decorators: -
- **`siren_off(self)`** - decorators: -
- **`siren_on(self)`** - decorators: -
- **`log_door_change(self, action, time, cmd=False)`** - decorators: -
  - :param action: 1 for door open, 0 for door close :param time: Range: [0, 99] :param cmd: If the command was created instead of
  - effects: `message_post`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.card.door.rel`, `hr.rfid.command`
- **`button_act_window(self)`** - decorators: -
  - effects: `i18n`
- **`change_apb_flag(self, card, can_exit=True)`** - decorators: -
  - touches: `hr.rfid.card.door.rel`, `hr.rfid.command`

### `hr.rfid.door.open.close.wiz` <a id='model-hr-rfid-door-open-close-wiz'></a>
Python class `HrRfidDoorOpenCloseWiz` in `models/hr_rfid_door.py:631`.  TransientModel (wizard).  Inherits: `balloon.mixin`.  Description: *Open or close door*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `doors` | Many2many → \`hr.rfid.door\` | Doors to open/close | ✓ | ✓ | The doors that will be opened or closed. You can select multiple doors to contro |
| `time` | Integer | Time | ✓ | ✓ | Duration in seconds for the door action. For opening: how long the door stays un |

#### Notable methods

- **`open_doors(self)`** - decorators: -
- **`close_doors(self)`** - decorators: -

### `hr.rfid.card.door.rel` <a id='model-hr-rfid-card-door-rel'></a>
Python class `HrRfidCardDoorRel` in `models/hr_rfid_door.py:670`.  Model.  Description: *Card and door relation model*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `card_id` | Many2one → \`hr.rfid.card\` | Card | ✓ | ✓ | The RFID card that has access to this door. This relationship is automatically m |
| `door_id` | Many2one → \`hr.rfid.door\` | Door | ✓ | ✓ | The door that this card can access. When the card is presented to this door's re |
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` | Time Schedule | ✓ | ✓ | Defines when this card can access this door. For example, "Business Hours" might |
| `alarm_right` | Boolean | Alarm Rights | ✓ | ✓ | When enabled, this card can arm/disarm the alarm system for this door. Typically |

#### Notable methods

- **`get_ts_code_string(self)`** - decorators: -
  - The card's schedule for each of the four readers, every reader of the door included. The card write itself does not read it: `hr.rfid.command.add_card` sends one D1 per reader, merged per slot by `hr.rfid.ctrl.add_remove_card`.
- **`update_card_rels(self, card_id, access_group=None)`** - decorators: `@api.model`
  - Checks all card-door relations and updates them :param card_id: Card for which the relations to be checked :param access_group: Which access groups to go through when searching for the doors. If None…
- **`update_door_rels(self, door_id, access_group=None)`** - decorators: `@api.model`
  - Checks all card-door relations and updates them :param door_id: Door for which the relations to be checked :param access_group: Which access groups to go through when searching for the cards. If None…
- **`reload_door_rels(self, door_id)`** - decorators: `@api.model`
- **`check_relevance_slow(self, card_id, door_id, ts_id=None)`** - decorators: `@api.model`
  - Check if card has access to door. If it does, create relation or do nothing if it exists, and if not remove relation or do nothing if it does not exist. :param card_id: Recordset containing a single…
  - effects: `create`, `raise:ValidationError`
- **`check_relevance_fast(self, card_id, door_id, ts_id=None, alarm_right=False)`** - decorators: `@api.model`
  - Check if card is compatible with the door. If it is, create relation or do nothing if it exists, and if not remove relation or do nothing if it does not exist. :param card_id: Recordset containing a…
  - effects: `create`
- **`create_rel(self, card_id, door_id, ts_id=None, alarm_right=False)`** - decorators: `@api.model`
  - effects: `create`, `raise:ValidationError`
- **`check_rel_relevance(self)`** - decorators: -
- **`time_schedule_changed(self, new_ts)`** - decorators: -
- **`pin_code_changed(self)`** - decorators: -
- **`card_number_changed(self, old_number)`** - decorators: -
- **`reload_add_card_command(self)`** - decorators: -
- **`_check_compat_n_rdy(self, card_id, door_id)`** - decorators: `@api.model`
- **`_door_constrains(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`_check_shared_module_card_collision(self)`** - decorators: `@api.constrains`
  - On a module shared between companies the controller stores bare card numbers with no company attached, so two granted cards carrying the same number would make events impossible to attribute. Block…
  - effects: `raise:ValidationError`, `sudo`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.card.door.rel`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self, create_cmd=True)`** - decorators: -
  - calls `super() `unlink``

### `hr.rfid.event` <a id='model-hr-rfid-event'></a>
Python class `HRRFIDEvent` in `models/hr_rfid_event.py:4`.  AbstractModel.  Description: *Helper for RFID Events*.

#### Notable methods

- **`get_event_action_text(self)`** - decorators: -

### `hr.rfid.event.system` <a id='model-hr-rfid-event-system'></a>
Python class `HrRfidSystemEvent` in `models/hr_rfid_event_system.py:76`.  Model.  Inherits: `hr.rfid.event`, `mail.thread`.  Description: *RFID System Event*.  Default order: `timestamp desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | - | Auto-generated system event description combining event type and location |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module |  | ✓ | The RFID webstack module (network interface) where this system event occurred. W |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller |  | ✓ | The RFID controller device that generated this system event. Controllers manage  |
| `door_id` | Many2one → \`hr.rfid.door\` | Door |  | ✓ | The specific door involved in this system event (e.g., forced open, overtime). M |
| `alarm_line_id` | Many2one → \`hr.rfid.ctrl.alarm\` | Alarm line |  | ✓ | The alarm input/output line that triggered this event. Used for security sensors |
| `siren` | Boolean | Siren |  | ✓ | Indicates whether the siren/alarm is currently active. True = Siren ON (alarm co |
| `timestamp` | Datetime | Timestamp | ✓ | ✓ | Exact date and time when this system event was detected. Critical for security a |
| `occurrences` | Integer | Occurrences |  | ✓ | Count of how many times this identical event has occurred. System groups repeate |
| `last_occurrence` | Datetime | Last occurrence |  | ✓ | Date and time of the most recent occurrence when the same event happened multipl |
| `event_action` | Selection | Event Type |  | ✓ | Type of system event: • Power On: Controller started • Door Overtime: Door held  |
| `error_description` | Char | Description |  | ✓ | Detailed explanation of the error or event condition. Provides context for troub |
| `card_number` | Char | Card number from this event |  | ✓ | RFID card number that triggered this system event. Only populated for card-relat |
| `input_js` | Char | Input JSON |  | ✓ | Raw JSON data received from the controller. Contains technical details for debug |
| `is_card_event` | Boolean | Is Card Event |  | - | Indicates if this system event is related to an unknown/denied card, allowing ca |

#### Notable methods

- **`_compute_is_card_event(self)`** - decorators: `@api.depends`
- **`_compute_sys_ev_name(self)`** - decorators: `@api.depends`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - effects: `with_context`
  - touches: `hr.rfid.event.system`
- **`zone_process_event(self)`** - decorators: -
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``

### `hr.rfid.event.sys.wiz` <a id='model-hr-rfid-event-sys-wiz'></a>
Python class `HrRfidSystemEventWizard` in `models/hr_rfid_event_system.py:486`.  TransientModel (wizard).  Description: *Add card to employee/contact*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `sys_ev_id` | Many2one → \`hr.rfid.event.system\` | System event | ✓ | ✓ | The system event containing the unknown card information to be registered. |
| `employee_id` | Many2one → \`hr.employee\` | Card owner (employee) |  | ✓ | Select the employee who will own this card. Choose either an employee OR a conta |
| `contact_id` | Many2one → \`res.partner\` | Card owner (contact) |  | ✓ | Select the external contact (visitor/contractor) who will own this card. Choose  |
| `card_number` | Char | Card Number |  | ✓ | The RFID card number extracted from the system event. This will be registered in |
| `card_type` | Many2one → \`hr.rfid.card.type\` | Card type |  | ✓ | Select the card technology type (e.g., Mifare, EM, HID). Only doors configured f |
| `activate_on` | Datetime | Activate on |  | ✓ | Date and time when the card becomes active. Set to a future date for scheduled a |
| `deactivate_on` | Datetime | Deactivate on |  | ✓ | Optional expiration date for the card. Leave empty for permanent cards. Useful f |
| `active` | Boolean | Active |  | ✓ | Enable this card immediately. Uncheck to create an inactive card that can be act |
| `cloud_card` | Boolean | Cloud Card | ✓ | ✓ | Cloud cards are managed centrally by the server. They work with online controlle |

#### Notable methods

- **`add_card(self)`** - decorators: -
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.card`

### `hr.rfid.event.user` <a id='model-hr-rfid-event-user'></a>
Python class `HrRfidUserEvent` in `models/hr_rfid_event_user.py:35`.  Model.  Inherits: `hr.rfid.event`, `mail.thread`.  Description: *RFID User Event*.  Default order: `event_time desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | - | Auto-generated event description combining person name, action, and location |
| `ctrl_addr` | Integer | Controller ID |  | ✓ | Unique identifier for the controller within its webstack network. Used for inter |
| `workcode` | Char | Workcode (Raw) |  | ✓ | Raw workcode number received from the RFID reader. This appears when the workcod |
| `workcode_id` | Many2one → \`hr.rfid.workcode\` | Workcode |  | ✓ | Associated workcode defining the type of work activity (e.g., start work, break, |
| `employee_id` | Many2one → \`hr.employee\` | Employee |  | ✓ | The employee who triggered this access event. Automatically populated from the c |
| `contact_id` | Many2one → \`res.partner\` | Contact |  | ✓ | The external contact (visitor, contractor) who triggered this access event. Used |
| `department_id` | Many2one → \`hr.department\` | Department |  | ✓ | Department of the employee at the time this event was recorded. Stored copy lets |
| `door_id` | Many2one → \`hr.rfid.door\` | Door |  | ✓ | The access door where this event occurred. Represents the physical entry/exit po |
| `reader_id` | Many2one → \`hr.rfid.reader\` | Reader | ✓ | ✓ | The RFID card reader device that captured this event. Can be an entry or exit re |
| `alarm_line_id` | Many2one → \`hr.rfid.ctrl.alarm\` | Alarm line |  | ✓ | The alarm input/output line involved in this event. Used for security zone armin |
| `card_id` | Many2one → \`hr.rfid.card\` | Card |  | ✓ | The RFID card used to trigger this event. Links to the card's configuration and  |
| `card_number` | Char | Card Number |  | - | The unique identification number of the RFID card used in this event. |
| `command_id` | Many2one → \`hr.rfid.command\` | Response |  | ✓ | System command sent in response to this event (e.g., open door, deny access). Us |
| `event_time` | Datetime | Timestamp | ✓ | ✓ | Exact date and time when the access event occurred at the reader. Used for atten |
| `event_action` | Selection | Action | ✓ | ✓ | The type of access event: • Card Granted: Access allowed • Card Denied: Access b |
| `action_string` | Char | Action String |  | - | Human-readable description of the event action for display purposes. |
| `more_json` | Char | More info about event in JSON |  | ✓ | Additional technical details about the event in JSON format. Used for debugging  |

#### Notable methods

- **`_compute_user_ev_name(self)`** - decorators: `@api.depends`
- **`_search_name(self, operator, value)`** - search method of the computed,
  unstored `name` (first field of the events' search view and part of
  `_rec_names_search`, so also the name search of an event link): `like` /
  `ilike` become an OR over `employee_id.name`, `contact_id.name`,
  `door_id.name` and the `event_action` keys whose label, in the searcher's
  language, contains the text (`_search_name_actions`); `in` (what `=` and
  "is set" arrive as) reads each exact name back into action, owner and door
  (`_search_name_equal`), and `False` matches nothing because every name
  holds the action; a negative operator returns `NotImplemented` and the ORM
  negates the positive search. `hr.rfid.vending.event` inherits it and
  overrides `_search_name_containing` / `_search_name_equal` for sales, whose
  name is "product - buyer". Without it every text search in that box raised "Cannot convert
  hr.rfid.event.user.name to SQL because it is not stored" (client case,
  10.11.2026).
- **`_compute_user_ev_action_str(self)`** - decorators: `@api.depends`
  - effects: `i18n`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - Create RFID events with duplicate prevention.
  - super-split (super `create`): pre=`log_info`, `log_warn` · post=`log_warn`, `with_context`
  - effects: `log_info`, `log_warn`, `with_context`
- **`zone_process_event(self)`** - decorators: -
- **`button_show_employee_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_show_contact_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_show_card_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_show_door_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_show_reader_events(self)`** - decorators: -
  - effects: `i18n`
- **`last_event(self, door_ids=None, partner_id=None, employee_id=None, event_action=None, domain=None, limit=1)`** - decorators: `@api.model`
  - Get last event for user

### `hr.rfid.notification` <a id='model-hr-rfid-notification'></a>
Python class `RFIDNotification` in `models/hr_rfid_notification.py:11`.  Model.  Description: *RFID Notification*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | - | Computed display label combining the event type and notification channel (e.g. ' |
| `zone_id` | Many2one → \`hr.rfid.zone\` | Zone | ✓ | ✓ | The zone or area where this notification rule applies. When events occur in this |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | - | Company that owns this notification. Automatically set based on the selected zon |
| `notification_type` | Selection | Notification Type |  | ✓ | How to send the notification: • System Chat: Send instant message through Odoo's |
| `user_event` | Selection | User Event |  | ✓ | Select a user-related event that will trigger this notification. Examples: Acces |
| `system_event` | Selection | System Event |  | ✓ | Select a system-related event that will trigger this notification. Examples: Con |
| `notify_followers` | Boolean | Notify Followers |  | ✓ | Send notifications to all users who follow this zone. This is useful for securit |
| `notify_partner_ids` | Many2many → \`res.partner\` | Notify Partner |  | ✓ | Specific people to notify when this event occurs. You can add multiple recipient |

#### Notable methods

- **`get_notification_type_text(self)`** - decorators: -
- **`get_user_event_text(self)`** - decorators: -
- **`get_system_event_text(self)`** - decorators: -
- **`_default_name(self)`** - decorators: `@api.depends`
- **`make_message(self, event, partner_id)`** - decorators: -
- **`generate_recipients(self)`** - decorators: -
  - touches: `res.partner`
- **`process_event(self, event)`** - decorators: -
  - effects: `with_context`
- **`notify_by_discuss(self, recipients, msg)`** - decorators: -
  - effects: `message_post`
  - touches: `discuss.channel`
- **`notify_by_email(self, recipients, subject, body)`** - decorators: -
- **`notify_by_sms(self, recipients, msg)`** - decorators: -
  - touches: `ir.model.data`
- **`check_recipients(self)`** - decorators: `@api.constrains`
  - effects: `raise:UserError`

### `res.config.settings` <a id='model-res-config-settings'></a>
Python class `ResConfigSettings` in `models/hr_rfid_settings.py:4`.  TransientModel (wizard).  Inherits: `res.config.settings`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `event_lifetime` | Integer | Event life time |  | - | Number of days to keep access events in the system. Events older than this will  |
| `save_new_webstacks` | Boolean | Accept new Modules |  | ✓ | Allow the system to automatically register new hardware modules when they connec |
| `save_webstack_communications` | Boolean | Debug JSON communication |  | ✓ | Save all communication between the system and hardware controllers to logs. Only |
| `module_hr_attendance_multi_rfid` | Boolean | Time & Attendance control |  | ✓ | Enable time tracking features using RFID cards. Employees can check in/out by sc |
| `module_hr_attendance_late` | Boolean | Time & Attendance additional calculation |  | ✓ | Add advanced attendance calculations like late arrivals, early departures, and o |
| `module_hr_rfid_vending` | Boolean | Vending Control |  | ✓ | Control vending machines with RFID cards. Allows employees to purchase items fro |
| `module_hr_rfid_realtime_dashboard` | Boolean | Realtime Dashboards |  | ✓ | Display live dashboards showing current access activity, who's in each area, and |
| `module_rfid_pms_base` | Boolean | PMS Base functionality |  | ✓ | Property Management System integration. Allows using RFID system for hotel room  |
| `module_hr_rfid_andromeda_import` | Boolean | Andromeda Import |  | ✓ | Import data from Andromeda access control systems. Use this to migrate from an e |

#### Notable methods

- **`get_values(self)`** - decorators: `@api.model`
  - calls `super() `get_values``
- **`set_values(self)`** - decorators: -
  - calls `super() `set_values``

### `hr.rfid.webstack` <a id='model-hr-rfid-webstack'></a>
Python class `HrRfidWebstack` in `models/hr_rfid_webstack.py:72`.  Model.  Inherits: `mail.activity.mixin`, `mail.thread`, `balloon.mixin`.  Description: *Module*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | Enter a descriptive name to identify this module (e.g., "Main Building Module" o |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Select which company this module belongs to. Controllers and access rights will  |
| `shared_company_ids` | Many2many → \`res.company\` | Shared With |  | ✓ | Other companies that use this module together with the owner company. They can s |
| `tz` | Selection | Timezone |  | ✓ | Select the timezone where this module is physically located. This ensures accura |
| `tz_offset` | Char | Timezone offset |  | - | Automatically calculated timezone offset from UTC (e.g., +0200 for UTC+2). Used  |
| `time_format` | Char | Time Format |  | - | Time format used by this module based on its hardware version. Automatically det |
| `serial` | Char | Serial number |  | ✓ | Unique 6-digit serial number printed on the module hardware. This is automatical |
| `active` | Boolean | Active |  | ✓ | Enable this to allow the module to communicate with Odoo. When disabled, the mod |
| `version` | Char | Version |  | ✓ | Firmware version running on the module. This is automatically detected. Contact  |
| `hw_version` | Char | Hardware Version |  | ✓ | Hardware model/version of the module (e.g., 10.3, 50.1, 100.1). This determines  |
| `behind_nat` | Boolean | Behind NAT | ✓ | ✓ | Enable if the module is behind a firewall/router (most common). When enabled, th |
| `last_ip` | Char | Last IP |  | ✓ | The IP address the module last connected from. For modules behind NAT, this is t |
| `updated_at` | Datetime | Last Update |  | ✓ | Last time this module communicated with Odoo. If this is more than 10 minutes ag |
| `controllers` | One2many → \`hr.rfid.ctrl\` | Controllers |  | ✓ | List of access control devices connected to this module. Each controller manages |
| `http_link` | Char | Http Link |  | - | Direct web interface link to the module. Only available when "Behind NAT" is dis |
| `module_username` | Selection | Module Username |  | ✓ | Username for accessing the module's web interface. Use "admin" for full access o |
| `module_password` | Char | Module Password |  | ✓ | Password for the module's web interface. Must match the password configured in t |
| `available` | Selection | Available? |  | ✓ | Connection status indicator: • Available (green): Module is online and respondin |
| `presence_misses` | Integer | Missed presence checks |  | ✓ | How many presence scans in a row found this module silent. Reset by the next con |
| `last_update` | Boolean | Contacted recently |  | ✓ | Whether the module is currently reachable. Set when it checks in and cleared by  |
| `commands_count` | Char | Commands count |  | - | Total number of commands sent to this module. Includes pending, successful, and  |
| `system_event_count` | Char | System Events count |  | - | Total number of system events logged by this module. Includes errors, warnings,  |
| `controllers_count` | Char | Controllers count |  | - | Number of controllers currently connected to this module. Each controller manage |

#### Notable methods

- **`_cron_check_presence(self)`** - decorators: `@api.model`
  - Turn the ABSENCE of device traffic into something the operator sees.
  - effects: `log_warn`
- **`_notify_inactive(self)`** - decorators: `@api.model`
  - Notify Inactive
  - effects: `with_context`
  - touches: `ir.model`, `mail.activity`, `res.users`
- **`_compute_time_format(self)`** - decorators: `@api.depends`
- **`_compute_counts(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.command`, `hr.rfid.event.system`
- **`return_action_to_open(self)`** - decorators: -
  - This opens the xml view specified in xml_id for the current app
  - touches: `ir.actions.act_window`
- **`toggle_ws_active(self)`** - decorators: -
- **`action_set_active(self)`** - decorators: -
- **`action_set_inactive(self)`** - decorators: -
- **`action_set_webstack_settings(self)`** - decorators: -
  - Set webstack settings for the module.
  - effects: `http_post`, `i18n`, `log_info`, `raise:ValidationError`, `sudo`
  - touches: `ir.config_parameter`
- **`action_check_if_ws_available(self)`** - decorators: -
  - effects: `http_get`, `i18n`, `raise:ValidationError`
- **`get_controllers(self)`** - decorators: -
  - Retrieve the list of controllers from the webstack.
  - effects: `http_get`, `i18n`, `log_error`, `raise:ValidationError`, `sudo`, `with_context`
  - touches: `hr.rfid.ctrl`
- **`reboot_cmd(self)`** - decorators: -
  - Reboots the module.
  - effects: `http_get`, `http_post`, `i18n`, `raise:ValidationError`
- **`_compute_tz_offset(self)`** - decorators: `@api.depends`
- **`_compute_http_link(self)`** - decorators: `@api.depends`
- **`_check_shared_card_number_collisions(self)`** - decorators: `@api.constrains`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.command`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
- **`sys_log(self, error_description, input_json=None)`** - decorators: -
  - :param error_description: (str) Description of the error that occurred. :param input_json: (str) JSON input for the logs. :return: None
  - effects: `sudo`
  - touches: `hr.rfid.event.system`
- **`sync_all_clocks(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.webstack`
- **`direct_execute(self, cmd, command_id=None)`** - decorators: -
  - :param cmd: A dictionary that contains the command to be executed. :param command_id: (optional) A model instance representing a stored command. :return: The response from the command execution.
  - effects: `log_error`
- *14 more not listed*

### `hr.rfid.webstack.discovery.row` <a id='model-hr-rfid-webstack-discovery-row'></a>
Python class `HrRfidWebstackDiscoveryRow` in `models/hr_rfid_webstack_discovery.py:8`.  TransientModel (wizard).  Description: *Webstack discovery rows*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | Module name as reported in the UDP discovery beacon. |
| `last_ip` | Char | Last Ip |  | ✓ | IP address from which the module's discovery beacon was received. |
| `version` | Char | Version |  | ✓ | Firmware/software version reported by the discovered module. |
| `hw_version` | Char | Hw Version |  | ✓ | Hardware version reported by the discovered module. |
| `serial` | Char | Serial |  | ✓ | Serial number reported by the discovered module — used as the unique key when ad |
| `behind_nat` | Boolean | Behind Nat |  | ✓ | Discovery flag indicating whether the module sits behind a NAT and must initiate |
| `discovery_id` | Many2one → \`hr.rfid.webstack.discovery\` | Discovery |  | ✓ | Discovery wizard run that found this module. |

### `hr.rfid.webstack.discovery` <a id='model-hr-rfid-webstack-discovery'></a>
Python class `HrRfidWebstackDiscovery` in `models/hr_rfid_webstack_discovery.py:41`.  TransientModel (wizard).  Description: *Webstack discovery*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `found_webstacks` | One2many → \`hr.rfid.webstack.discovery.row\` | Found modules |  | ✓ | Modules that were just found during the discovery process |
| `what_to_do` | Selection | What To Do | ✓ | ✓ | What happens when you click Setup — Add as Inactive: register the module but do  |

#### Notable methods

- **`setup_modules(self)`** - decorators: -
  - effects: `sudo`
  - touches: `hr.rfid.webstack`

### `hr.rfid.webstack.manual.create` <a id='model-hr-rfid-webstack-manual-create'></a>
Python class `HrRfidWebstackManualCreate` in `models/hr_rfid_webstack_discovery.py:142`.  TransientModel (wizard).  Description: *Webstack Manual Creation*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `webstack_name` | Char | Module Name |  | ✓ | Friendly name for the module (e.g. 'Warehouse Gate Module'). Auto-filled from th |
| `webstack_serial` | Char | Serial Number | ✓ | ✓ | Serial number printed on the module's label. Must be unique across the database; |
| `behind_nat` | Boolean | Behind Nat |  | ✓ | Check if the module sits behind a NAT and Odoo cannot reach its IP directly. In  |
| `local_ip_address` | Char | Local Ip Address |  | ✓ | Required when Behind NAT is off — the LAN IP at which Odoo can reach the module  |

#### Notable methods

- **`create_webstack(self)`** - decorators: -
  - effects: `sudo`
  - touches: `hr.rfid.webstack`

### `hr.rfid.webstack` <a id='model-hr-rfid-webstack'></a>
Python class `HrRfidWebstackHwEvents` in `models/hr_rfid_webstack_hw_events.py:26`.  Model.  Inherits: `hr.rfid.webstack`.

### `hr.rfid.webstack.replace.wiz` <a id='model-hr-rfid-webstack-replace-wiz'></a>
Python class `HrRfidWebstackReplaceWiz` in `models/hr_rfid_webstack_replace_wiz.py:11`.  TransientModel (wizard).  Description: *Wizard for replacing one webstack with another*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `source_webstack_id` | Many2one → \`hr.rfid.webstack\` | Source Webstack |  | ✓ | Old webstack being replaced. Inactive modules are included to allow swap-in of p |
| `destination_webstack_id` | Many2one → \`hr.rfid.webstack\` | Destination Webstack |  | ✓ | New webstack that will take over the controllers. Inactive modules are included  |
| `source_controller_ids` | Many2many → \`hr.rfid.ctrl\` | Source Controller |  | ✓ | Controllers attached to the source webstack — these will be moved to the destina |
| `destination_controller_ids` | One2many → \`hr.rfid.ctrl\` | *from destination_webstack_id.controllers* |  | - | Controllers currently attached to the destination webstack — shown for reference |
| `replace_existing` | Boolean | Replace Existing |  | ✓ | Replace existing controllers in destination module.  This will remove the existi |
| `destination_active_state` | Boolean | Destination Active State |  | ✓ | The Active state of the destination module. |

#### Notable methods

- **`confirm_transfer(self)`** - decorators: -
  - effects: `message_post`, `raise:ValidationError`, `sudo`
  - touches: `ir.config_parameter`

### `hr.rfid.webstack` <a id='model-hr-rfid-webstack'></a>
Python class `HrRfidWebstackWs` in `models/hr_rfid_webstack_ws.py:55`.  Model.  Inherits: `hr.rfid.webstack`, `polimex.ws.mixin`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `endpoint_id` | Many2one → \`polimex.ws.endpoint\` | Real-time endpoint | ✓ | ✓ |  |

#### Notable methods

- **`unlink(self)`** - decorators: -
  - super-split (super `unlink`): pre=`log_warn` · post=-
  - effects: `log_warn`

### `hr.rfid.workcode` <a id='model-hr-rfid-workcode'></a>
Python class `HrRfidWorkcode` in `models/hr_rfid_workcode.py:5`.  Model.  Inherits: `mail.thread`.  Description: *RFID Workcode for Time Tracking*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name | ✓ | ✓ | A descriptive name for this workcode that helps employees understand its purpose |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company this workcode belongs to. In multi-company setups, each company can  |
| `workcode` | Char | Workcode | ✓ | ✓ | A 4-digit numerical code that employees will enter on RFID terminals to record t |
| `user_action` | Selection | User action | ✓ | ✓ | Defines what type of time tracking action this workcode represents: • Start: Rec |

#### Notable methods

- **`_check_workcode_code(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`

### `hr.rfid.ws.dedup` <a id='model-hr-rfid-ws-dedup'></a>
Python class `HrRfidWsDedup` in `models/hr_rfid_ws_dedup.py:24`.  Model.  Description: *Real-time Event Deduplication*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Webstack | ✓ | ✓ |  |
| `ctrl_id_num` | Integer | Ctrl Id Num | ✓ | ✓ |  |
| `bos` | Integer | Bos | ✓ | ✓ |  |
| `ev_ts` | Char | Ev Ts | ✓ | ✓ | Controller date+time string of the event. |
| `create_date` | Datetime | Create Date |  | ✓ |  |

#### Notable methods

- **`_seen(self, webstack, ctrl_id_num, bos, ev_ts)`** - decorators: `@api.model`
  - True when this event key was already successfully processed.
  - effects: `sudo`
- **`_claim(self, webstack, ctrl_id_num, bos, ev_ts)`** - decorators: `@api.model`
  - Record a SUCCESSFULLY processed event key (claim only on success: an event answered with a non-200 status stays unclaimed so its re-send gets processed - mirrors the HTTP path where a non-200…
  - effects: `sudo`

### `hr.rfid.zone` <a id='model-hr-rfid-zone'></a>
Python class `HrRfidZone` in `models/hr_rfid_zone.py:12`.  Model.  Inherits: `mail.thread`.  Description: *Zone*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Zone Name | ✓ | ✓ | A descriptive name for this zone (e.g., 'Main Building', 'Production Area', 'War |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company this zone belongs to. Zones are company-specific for multi-company s |
| `anti_pass_back` | Boolean | Anti-Pass Back |  | ✓ | Security feature that prevents tailgating and ensures accurate tracking. When en |
| `log_out_on_exit` | Boolean | Logout on Exit |  | ✓ | Automatically log out employees from the system when they exit this zone. Useful |
| `door_ids` | Many2many → \`hr.rfid.door\` | Doors |  | ✓ | Select all doors that define the boundaries of this zone. These are the entry/ex |
| `permitted_department_ids` | Many2many → \`hr.department\` | Departments |  | ✓ | Restrict zone access to specific departments. Only employees from selected depar |
| `permitted_employee_category_ids` | Many2many → \`hr.employee.category\` | Tags |  | ✓ | Restrict zone access to employees with specific tags/categories. Only employees  |
| `employee_ids` | Many2many → \`hr.employee\` | Employees |  | ✓ | Real-time list of employees currently present in this zone. This field is automa |
| `contact_ids` | Many2many → \`res.partner\` | Contacts |  | ✓ | Real-time list of external contacts (visitors, contractors, vendors) currently i |
| `notification_ids` | One2many → \`hr.rfid.notification\` | Notifications |  | ✓ | Configure automatic notifications for zone events. You can set up alerts for: •  |
| `employee_count` | Char | Employee Count |  | - | Current number of employees in this zone. Automatically calculated based on entr |
| `contact_count` | Char | Contact Count |  | - | Current number of external contacts (visitors) in this zone. Automatically calcu |

#### Notable methods

- **`_compute_counts(self)`** - decorators: `@api.depends`
- **`person_went_through(self, event)`** - decorators: -
  - touches: `hr.employee`
- **`person_entered(self, person, event)`** - decorators: -
  - touches: `hr.employee`
- **`person_left(self, person, event=None)`** - decorators: -
  - touches: `hr.employee`
- **`clear_employees(self)`** - decorators: -
  - touches: `hr.rfid.event.user`
- **`clear_contacts(self)`** - decorators: -
  - touches: `hr.rfid.event.user`
- **`employee_in_current_zone(self)`** - decorators: -
  - effects: `i18n`
- **`contact_in_current_zone(self)`** - decorators: -
  - effects: `i18n`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.door`
- **`process_event(self, event)`** - decorators: -

### `hr.rfid.zone.doors.wiz` <a id='model-hr-rfid-zone-doors-wiz'></a>
Python class `HrRfidZoneDoorsWizard` in `models/hr_rfid_zone.py:323`.  TransientModel (wizard).  Description: *Add or remove doors to the zone*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `zone_id` | Many2one → \`hr.rfid.zone\` | Zone | ✓ | ✓ | The zone you are modifying. This field is read-only as you're working with the c |
| `door_ids` | Many2many → \`hr.rfid.door\` | Doors | ✓ | ✓ | Select doors to add or remove from this zone. These doors will serve as entry/ex |

#### Notable methods

- **`add_doors(self)`** - decorators: -
- **`remove_doors(self)`** - decorators: -

### `ir.websocket` <a id='model-ir-websocket'></a>
Python class `IrWebsocket` in `models/ir_websocket.py:18`.  AbstractModel.  Inherits: `ir.websocket`.

### `onboarding.onboarding` <a id='model-onboarding-onboarding'></a>
Python class `OnboardingOnboarding` in `models/onboarding_onboarding.py:13`.  Model.  Inherits: `onboarding.onboarding`.

#### Notable methods

- **`action_close_panel_rfid_setup(self)`** - decorators: `@api.model`
  - effects: `sudo`
- **`close_onboarding_panel(self, route_name)`** - decorators: `@api.model`
  - Close (hide) the onboarding panel identified by ``route_name``.
  - effects: `sudo`
- **`get_onboarding_panel_html(self, route_name)`** - decorators: `@api.model`
  - Render Odoo's standard onboarding panel for ``route_name``.
  - effects: `log_warn`, `sudo`
  - touches: `ir.qweb`

### `onboarding.onboarding.step` <a id='model-onboarding-onboarding-step'></a>
Python class `OnboardingOnboardingStep` in `models/onboarding_onboarding_step.py:4`.  Model.  Inherits: `onboarding.onboarding.step`.

#### Notable methods

- **`action_open_step_rfid_settings(self)`** - decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_add_webstack(self)`** - decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_scan_controllers(self)`** - decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_create_access_group(self)`** - decorators: `@api.model`
- **`action_open_step_register_card(self)`** - decorators: `@api.model`

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:4`.  Model.  Inherits: `res.company`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `event_lifetime` | Integer | Event life time |  | ✓ | Enter event lifetime. Older events will be deleted |
| `card_input_type` | Selection | Card Input Type |  | ✓ | Format readers in this company report card numbers in — Wiegand 34 (5d+5d): faci |

#### Notable methods

- **`create(self, values_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.time.schedule`

### `res.partner` <a id='model-res-partner'></a>
Python class `ResPartner` in `models/res_partner.py:8`.  Model.  Inherits: `res.partner`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ |  |
| `hr_rfid_pin_code` | Char | RFID PIN Code |  | ✓ | 4-digit PIN code for secure door access. Use this along with an RFID card for hi |
| `hr_rfid_access_group_ids` | One2many → \`hr.rfid.access.group.contact.rel\` | Access Groups |  | ✓ | Door access permissions for this contact. Each group defines which doors they ca |
| `hr_rfid_card_ids` | One2many → \`hr.rfid.card\` | RFID Cards |  | ✓ | All RFID cards assigned to this contact. A person can have multiple cards (e.g., |
| `hr_rfid_event_ids` | One2many → \`hr.rfid.event.user\` | Access History |  | ✓ | Complete history of door access attempts by this contact. Includes successful en |
| `is_employee` | Boolean | Is Employee |  | - |  |
| `partner_event_count` | Char | Total Events |  | - | Total number of access events recorded for this contact. |
| `partner_doors_count` | Char | Accessible Doors |  | - | Number of doors this contact can currently access based on their access groups. |

#### Notable methods

- **`button_partner_events(self)`** - decorators: -
  - effects: `i18n`
- **`button_doors_list(self)`** - decorators: -
  - effects: `i18n`
- **`add_acc_gr(self, access_groups, expiration=None)`** - decorators: -
  - touches: `hr.rfid.access.group.contact.rel`
- **`remove_acc_gr(self, access_groups)`** - decorators: -
  - touches: `hr.rfid.access.group.contact.rel`
- **`get_doors(self, excluding_acc_grs=None, including_acc_grs=None)`** - decorators: -
  - touches: `hr.rfid.access.group`
- **`check_for_ts_inconsistencies_when_adding(self, new_acc_grs)`** - decorators: -
  - touches: `hr.rfid.access.group.door.rel`
- **`check_for_ts_inconsistencies(self)`** - decorators: -
  - touches: `hr.rfid.access.group.door.rel`
- **`check_access_group(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
  - touches: `hr.rfid.door`
- **`_check_pin_code(self)`** - decorators: `@api.constrains`
  - effects: `raise:ValidationError`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
- **`log_person_out(self, sids=None)`** - decorators: -
- **`generate_random_barcode_card(self)`** - decorators: -
  - effects: `write`
  - touches: `hr.rfid.card`
- **`generate_partner(self, name, parent_id=None, card_number=None, unlink_card_if_exsist=True, access_group_id=None)`** - decorators: `@api.model`
  - Require: name Optional: parent_id: int - res.partner.id card_number: str unlink_card_if_exsist:bool access_group_id: hr.rfid.access.group.id Context: activate_on: datetime deactivate_on: datetime
  - effects: `with_context`
  - touches: `hr.rfid.card`, `res.partner`
- **`add_access_group(self, access_group_id, activate_on=None, expire_on=None, visits=0)`** - decorators: -
  - Adding access group
- **`add_card_number(self, card_number, activate_on=None, expire_on=None, card_input_type=None)`** - decorators: -
- **`action_send_badge_email(self, template_xml_id=None)`** - decorators: -
  - Open a window to compose an email, with the template - 'card_badge' message loaded by default
- **`decode_mrz(self, mrz_string)`** - decorators: `@api.model`
  - This function receives a string containing the Machine Readable Zone (MRZ) data of a personal document, decodes the MRZ data and returns it as a dictionary. The function also performs basic…

### `res.partner.mass.wiz` <a id='model-res-partner-mass-wiz'></a>
Python class `HrPartnerMassAccGrsWiz` in `models/res_partner.py:465`.  TransientModel (wizard).  Description: *Bulk Access Group Management for Contacts*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `partner_ids` | Many2many → \`res.partner\` | Selected Contacts | ✓ | ✓ | The contacts whose access permissions you want to modify. |
| `remove_existing` | Boolean | Remove Existing Groups First |  | ✓ | Check this to remove all current access groups before adding the new ones. Use w |
| `acc_gr_ids` | Many2many → \`hr.rfid.access.group\` | Access Groups to Add |  | ✓ | Select the access groups to grant to the selected contacts. Each group defines s |
| `expiration` | Datetime | Access Expiration |  | ✓ | Optional expiration date for these access rights. Perfect for temporary access,  |

#### Notable methods

- **`add_acc_grs(self)`** - decorators: -
  - touches: `hr.rfid.access.group.contact.rel`
- **`remove_acc_grs(self)`** - decorators: -


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `controllers/polimex.py`

- **`MAX_DIRECT_EXECUTE`** *(scalar)* = `10`  - line 3
- **`MAX_DIRECT_EXECUTE_TIME`** *(scalar)* = `5`  - line 4
- **`HW_TYPES`** *(collection)* = `[('1', 'iCON200'), ('2', 'iCON150'), ('3', 'iCON150'), ('4', 'iCON140'), ('5', 'iCON120'), ('6', 'iCON110'), ('7', 'iCON160'), ('8', 'iCON170'), ('9', 'Turnstile'), ('10', 'iCON180'), ('11', 'iCON115'), ('12', 'iCON50'), ('13', 'iCON115 hot  # ...truncated`  - line 7
- **`VENDING_HW_VERSIONS`** *(collection)* = `('16', '20', '21')`  - line 24
- **`DEFAULT_IO_TABLES`** *(collection)* = `[[6, 2, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,   # ...truncated`  - line 25
- **`READ_CARDS_BLOCK_SIZE`** *(scalar)* = `5`  - line 518

### `models/hr_rfid_command_ws.py`

- **`WS_CMD_REPUBLISH_TIMEOUT_S`** *(scalar)* = `CMD_ANSWER_TIMEOUT_S` (15)
- **`WS_CMD_MAX_RETRIES`** *(scalar)* = `CMD_MAX_RETRIES` (5)

### `controllers/polimex.py` - the command queue

- **`CMD_ANSWER_TIMEOUT_S`** *(scalar)* = `15` - how long a command handed to a module may stay unanswered before it counts as lost; shared by the classic delivery and the real-time channel
- **`CMD_MAX_RETRIES`** *(scalar)* = `5` - how many times a lost command is handed over again
- **`ROUTINE_COMMANDS`** *(collection)* = `('D7', 'B3')` - the clock and the status reading: `single_attempt`, one system event when the controller stops answering them
- **`ERROR_NO_ANSWER`** = `'30'`, **`ERROR_CONTROLLER_SILENT`** = `'20'` - the reasons a command is closed for

### The conversation with a module (`controllers/main.py`, `models/hr_rfid_webstack.py`)

- **The shape of the reply** is settled per request by `_decode_post` and kept on the request (`request.rfid_reply_shape`: `json_rpc`, `id`, `plain`), never on the controller object, which is shared by every request. `_make_response` reads it: JSON-RPC envelope, plain JSON for a 100.1 (serial starting with '4'), and for a 10.3 an empty body or `{"cmd": {...}}` and nothing else - no `status`, no `ws` block.
- **One command out at a time** (`check_for_unsent_cmd`): while ANY command in `Process` is still awaited nothing is handed over and none is re-sent; once all are overdue, those that may not be sent again are closed (`_close_unanswered`), the oldest of the rest is re-sent (`retries + 1`), and with none left the next waiting one goes out in the same reply.
- **What the module answers to a command** (`parse_response`): `e=20` (controller silent) in the reply to a report re-sends the command in place (`_retry_command`) or closes it with '20'; on a delivery of its own (`direct_cmd=True`: the real-time channel, a module Odoo reaches) it goes back to `Wait` with `retries + 1` or is closed, because no reply carries a command there. `e=24` (module full) puts the command back to `Wait`. Neither re-queues a `single_attempt` command: it is closed.
- **On reconnect** (`_ws_on_connect_sync`): a `Process` command that may not be sent again is closed if its time is up, and holds the slot if it is still awaited; otherwise the oldest `Process` command is published again, else the next waiting one.
- **A controller that has not described itself** (`_hw_description_is_on_its_way`): a card event for a controller with no `hw_version` is answered 400 while its F0 is `Wait`/`Process` (asked here if it never was), with a system event that keeps the report. After an F0 that ended without describing it, the event is noted ("Could not find a reader with that id") and accepted, so the module is not held back.
- **`_reply_with_command(command, status_code)`** - used by the reports that are answered with a command of their own (event 30 the clock, event 25/31 the status reading, an unknown controller its F0): the command goes out in the reply only when nothing else is out; otherwise it waits its turn.
- **`single_attempt`** commands are never re-sent: the answer to event 64 (DB, and DB2 for vending credit) and routine upkeep.
- **A report that fails here** is recorded as a system event with the traceback AND the raw report (`with_context(keep_report=True)` bypasses the "save communications" setting, up to `KEPT_REPORT_MAX_CHARS` = 20000): a 10.3 reads an empty reply as "accepted" and forgets the event, so this record is its only copy. The kept copy leaves out the module's key (`_report_without_key`). Only for a module that has proved its key; before that the report is kept only if the site keeps its communication. The work on the report runs inside a savepoint (`post_event`, and the vending override): a failure undoes what was half done, and the record can still be written after a database error. The real-time channel does the same per event (`_ws_on_event_batch`).
- **A report with no key** is refused like a wrong key (400, "Webstack key and key in json did not match"); it used to raise.
- **Events 27/28** (alarm zone delay) are logged and acknowledged; they used to raise.
- **A late passage** (`hr.rfid.zone._passage_is_overtaken`): a granted passage more than `LATE_PASSAGE_AFTER_MINUTES` (10) old on arrival, with a newer one of the same person through a door of the zone, does not change the zone's people or the anti-passback flags; it is still recorded and still counts for attendance by its own time. A "newer" passage stamped after the server's own time is not counted (a controller with its clock ahead), and a passage that is not late always moves the zone. Each skip is logged at INFO with both passages.
- **Vending without a server for it** (`_hw_vending_request_for_balance`): logged and accepted; the text says "not installed" only when `hr.rfid.vending.event` is not in the registry, otherwise that vending is served over the classic connection only.

### `models/hr_rfid_ctrl_time_schedule.py`

- **`DEFAULT_TS_LINE`** *(expression)* = `'01\n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00\n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00 \n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00\n         `  - line 5

### `models/hr_rfid_event_system.py`

- **`SYS_EV_DEDUP_WINDOW_SECONDS`** *(scalar)* = `300`  - line 20

### `models/hr_rfid_event_user.py`

- **`ANONYMOUS_EVENT_ACTIONS`** *(collection)* = `('47', '-1')`  - line 15

### `models/hr_rfid_webstack.py`

- **`MAX_DETECTED_CONTROLLERS`** *(scalar)* = `64`  - line 23
- **`PRESENCE_WINDOW_MINUTES`** *(scalar)* = `10`  - line 28
- **`PRESENCE_MISSES_BEFORE_DARK`** *(scalar)* = `3`  - line 36

### `models/hr_rfid_webstack_ws.py`

- **`WS_EV_BATCH_MAX`** *(scalar)* = `20`  - line 47
- **`WS_CTRL_ID_MIN`** *(scalar)* = `1`  - line 51
- **`WS_CTRL_ID_MAX`** *(scalar)* = `254`  - line 52

### `models/hr_rfid_ws_dedup.py`

- **`WS_DEDUP_RETENTION_DAYS`** *(scalar)* = `7`  - line 20
- **`GC_UNLINK_LIMIT`** *(scalar)* = `1000`  - line 21

### `tools/odoo_bus_device_sim.py`

- **`PROTO`** *(scalar)* = `1`  - line 37


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`WebRfidController.post_barcode(self, **post)`** (`@http.route`) - `controllers/main.py:54`
  - :param post: Dictionary of parameters sent in the POST request. :return: List of dictionaries with barcode data.
  - effects: `log_info`
- **`WebRfidController.post_event(self, **post)`** (`@http.route`) - `controllers/main.py:240`
  - This method handles the POST request to the '/hr/rfid/event' route. It processes the received data from the request and performs necessary actions based on the data.
  - effects: `log_error`, `log_info`, `sudo`
  - touches: `hr.rfid.event.system`, `hr.rfid.webstack`
- **`WebRfidController.vending_request_for_balance(self)`** - `controllers/main.py:394`
- **`get_default_io_table(hw_version, mode, as_string=True)`** - `controllers/polimex.py:521`
- **`bytes_to_num(data, start, digits)`** - `controllers/polimex.py:530`
- **`str_hex_to_array(str)`** - `controllers/polimex.py:540`
- **`str_dec_to_array(str)`** - `controllers/polimex.py:542`
- **`get_temperature(h, l, precision=0.5)`** - `controllers/polimex.py:545`
- **`get_reverse_temperature(temp)`** - `controllers/polimex.py:553`
- **`simulate_event()`** - `controllers/simulate_event.py:9`
  - effects: `http_post`
- **`BaseImporter.connect_to_old_odoo(self)`** - `manual_import.py:34`
  - effects: `log_error`, `log_info`
- **`BaseImporter.connect_to_new_odoo(self)`** - `manual_import.py:44`
  - effects: `log_error`, `log_info`
- **`BaseImporter.fetch_data_in_batches(self, model, fields, domain=[])`** - `manual_import.py:54`
  - effects: `log_info`
- **`BaseImporter.check_external_id_exists(self, model, external_id)`** - `manual_import.py:68`
- **`BaseImporter.create_external_id(self, model, res_id, external_id)`** - `manual_import.py:72`
- **`BaseImporter.get_matching_fields(self, source_model, target_model)`** - `manual_import.py:80`
- **`BaseImporter.get_avatar_mixin_fields(self)`** - `manual_import.py:94`
- **`BaseImporter.get_mail_thread_fields(self)`** - `manual_import.py:102`
- **`BaseImporter.get_computed_fields(self, model)`** - `manual_import.py:124`
- **`BaseImporter.get_related_fields(self, model)`** - `manual_import.py:134`
- **`BaseImporter.get_model_specific_exceptions(self, model_name)`** - `manual_import.py:144`
- **`BaseImporter.get_field_mapping(self, model_name)`** - `manual_import.py:169`
- **`BaseImporter.get_final_field_mapping(self, source_model, target_model, model_name)`** - `manual_import.py:184`
  - effects: `log_info`
- **`BaseImporter.map_fields(self, record, field_mapping, source_model)`** - `manual_import.py:200`
- **`BaseImporter.import_related_model(self, related_model, related_id, related_field_mapping)`** - `manual_import.py:223`
  - effects: `create`, `log_info`
- **`BaseImporter.import_log_notes(self, source_model, target_model, record_id, new_record_id)`** - `manual_import.py:240`
  - effects: `log_info`
- **`BaseImporter.import_data(self, model, data, external_id, source_model, record_id)`** - `manual_import.py:260`
  - effects: `create`, `log_info`
- **`BaseImporter.import_data_for_model(self, source_model, target_model=None, ignored_ids=None)`** - `manual_import.py:282`
  - effects: `log_info`
- **`PartnerImporter.import_partners(self, target_model=None, ignored_ids=None)`** - `manual_import.py:309`
- **`test_import_partners()`** - `manual_import.py:318`
- **`demo_records_to_noupdate(cr, module)`** - `migration_utils.py:68`
  - Set ``noupdate`` on the module's demo ir.model.data rows.
  - effects: `log_info`, `sql`
- **`migrate(cr, version)`** - `migrations/19.0.2.11.1/post-migrate.py:26`
  - effects: `log_exception`, `log_info`, `with_context`
- **`migrate(cr, version)`** - `migrations/19.0.2.20.0/pre-migrate.py:8`
- **`migrate(cr, version)`** - `migrations/19.0.2.24.1/pre-migrate.py:8`
- **`get_local_ip()`** - `models/hr_rfid_webstack.py:42`
  - Return the IP address of the machine running the code.
- **`log(msg)`** - `tools/odoo_bus_device_sim.py:40`
- **`WsClient.send_text(self, payload)`** - `tools/odoo_bus_device_sim.py:81`
- **`WsClient.recv_text(self, timeout=15.0)`** - `tools/odoo_bus_device_sim.py:104`
  - Return the next TEXT payload; transparently answers PINGs.
- **`Device.http_checkin(self, extra)`** - `tools/odoo_bus_device_sim.py:149`
- **`Device.provision(self)`** - `tools/odoo_bus_device_sim.py:160`
- **`Device.connect_ws(self)`** - `tools/odoo_bus_device_sim.py:171`
- **`Device.send(self, mtype, **payload)`** - `tools/odoo_bus_device_sim.py:191`
- **`Device.expect(self, mtype, timeout=15.0)`** - `tools/odoo_bus_device_sim.py:196`
  - Wait for one bus notification of the given type; track last id.
- **`NoRedirect.redirect_request(self, *args, **kwargs)`** - `tools/odoo_bus_device_sim.py:212`
- **`event_dict(ctrl=5, bos=1, event_n=4, card='0000000000')`** - `tools/odoo_bus_device_sim.py:216`
- **`scenario_single(dev)`** - `tools/odoo_bus_device_sim.py:226`
  - The SPEC §12 walk: provisioning, hello, new-controller event flow, F0 response, event retry, dedup, command over the bus.
- **`main()`** - `tools/odoo_bus_device_sim.py:291`

### Private helpers

- **`_ws_db_update_dict()`** - `controllers/main.py:21`
- **`_get_remote_ip_address()`** - `controllers/main.py:28`
- **`WebRfidController._parse_event(self, post_data, webstack)`** - `controllers/main.py:39`
  - Thin delegate - the parsing core lives on ``hr.rfid.webstack`` (``models/hr_rfid_webstack_hw_events.py``) so the websocket ingress can reuse it. Kept as a method so route overrides that call it keep working unchanged.
- **`WebRfidController._respond_to_ev_64(self, open_door, controller, reader, card, post_data)`** - `controllers/main.py:46`
  - Thin delegate - core on hr.rfid.webstack (see _hw_respond_to_ev_64).
- **`WebRfidController._decode_post(self, post)`** - `controllers/main.py:95`
- **`WebRfidController._make_response(self, result)`** - `controllers/main.py:107`
  - Wrap the result for the wire the module speaks. THREE shapes:
- **`WebRfidController._authenticate_webstack(self, post_data)`** - `controllers/main.py:151`
  - Find and authenticate the webstack behind a hardware POST.
  - effects: `log_info`, `message_post`, `sudo`, `with_context`
  - touches: `hr.rfid.webstack`, `ir.config_parameter`, `res.company`, `res.users`
- **`WebRfidController._parse_raw_data(self, post_data)`** - `controllers/main.py:369`
  - Answer a device that speaks a shape this endpoint does not handle.
  - effects: `log_info`
- **`BaseImporter.__init__(self, old_url, old_db, old_username, old_password, new_url, new_db, new_username, new_password, source_version, batch_size=100)`** - `manual_import.py:8`
- **`_demo_xml_ids(module)`** - `migration_utils.py:37`
  - Every xml id declared by the module's own demo files.
  - effects: `log_warn`
- **`_check_overlap(ranges)`** - `models/hr_rfid_access_group.py:562`
- **`_tz_get(self)`** - `models/hr_rfid_webstack.py:64`
- **`WsClient.__init__(self, ws_url, origin, cookie)`** - `tools/odoo_bus_device_sim.py:49`
- **`WsClient._read_exact(self, n)`** - `tools/odoo_bus_device_sim.py:95`
- **`Device.__init__(self, args)`** - `tools/odoo_bus_device_sim.py:135`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `digest_digest_view_form` | `digest.digest` | - | digest.digest_digest_view_form | `views/digest_views.xml` |
| `hr_department_add_acc_grs_wiz` | `hr.department.acc.grs` | - |  | `views/hr_department_views.xml` |
| `hr_department_def_acc_gr_wiz` | `hr.department.def.acc.gr` | - |  | `views/hr_department_views.xml` |
| `hr_department_mass_acc_grs_wiz` | `hr.department.mass.wiz` | - |  | `views/hr_department_views.xml` |
| `hr_view_department_form_inherit_hr_rfid` | `hr.department` | - | hr.view_department_form | `views/hr_department_views.xml` |
| `hr_department_view_kanban_inherit_hr_rfid` | `hr.department` | - | hr.hr_department_view_kanban | `views/hr_department_views.xml` |
| `hr_view_employee_form_inherit_hr_rfid` | `hr.employee` | - | hr.view_employee_form | `views/hr_employee_views.xml` |
| `hr_rfid_access_group_add_doors_wiz` | `hr.rfid.access.group.wizard` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_del_doors_wiz` | `hr.rfid.access.group.wizard` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_view_form` | `hr.rfid.access.group` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_view_list` | `hr.rfid.access.group` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_view_search` | `hr.rfid.access.group` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_access_group_door_rel_view_form` | `hr.rfid.access.group.door.rel` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_acc_gr_employee_rel_view_form` | `hr.rfid.access.group.employee.rel` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_acc_gr_employee_rel_view_list` | `hr.rfid.access.group.employee.rel` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_acc_gr_contact_rel_view_form` | `hr.rfid.access.group.contact.rel` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_acc_gr_contact_rel_view_list` | `hr.rfid.access.group.contact.rel` | - |  | `views/hr_rfid_access_group.xml` |
| `hr_rfid_card_view_form` | `hr.rfid.card` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_view_list` | `hr.rfid.card` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_view_search` | `hr.rfid.card` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_type_view_form` | `hr.rfid.card.type` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_type_view_list` | `hr.rfid.card.type` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_type_view_search` | `hr.rfid.card.type` | - |  | `views/hr_rfid_card.xml` |
| `hr_rfid_card_door_rel_view_form` | `hr.rfid.card.door.rel` | - |  | `views/hr_rfid_card_door_rel.xml` |
| `hr_rfid_card_door_rel_view_list` | `hr.rfid.card.door.rel` | - |  | `views/hr_rfid_card_door_rel.xml` |
| `hr_rfid_card_door_rel_view_search` | `hr.rfid.card.door.rel` | - |  | `views/hr_rfid_card_door_rel.xml` |
| `hr_rfid_command_view_form` | `hr.rfid.command` | - |  | `views/hr_rfid_command.xml` |
| `hr_rfid_command_view_list` | `hr.rfid.command` | - |  | `views/hr_rfid_command.xml` |
| `hr_rfid_command_view_search` | `hr.rfid.command` | - |  | `views/hr_rfid_command.xml` |
| `hr_rfid_command_view_calendar` | `hr.rfid.command` | - |  | `views/hr_rfid_command.xml` |
| `hr_rfid_command_view_pivot` | `hr.rfid.command` | - |  | `views/hr_rfid_command.xml` |
| `hr_rfid_controller_view_form` | `hr.rfid.ctrl` | - |  | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_kanban` | `hr.rfid.ctrl` | - |  | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_list` | `hr.rfid.ctrl` | - |  | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_controller_view_search` | `hr.rfid.ctrl` | - |  | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_ctrl_alarm_list_view` | `hr.rfid.ctrl.alarm` | - |  | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_form_view` | `hr.rfid.ctrl.alarm` | - |  | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_view_kanban` | `hr.rfid.ctrl.alarm` | - |  | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_search_view` | `hr.rfid.ctrl.alarm` | - |  | `views/hr_rfid_ctrl_alarm.xml` |
| `hr_rfid_ctrl_alarm_group_list_view` | `hr.rfid.ctrl.alarm.group` | - |  | `views/hr_rfid_ctrl_alarm_group.xml` |
| `hr_rfid_ctrl_alarm_group_form_view` | `hr.rfid.ctrl.alarm.group` | - |  | `views/hr_rfid_ctrl_alarm_group.xml` |
| `hr_rfid_ctrl_alarm_group_hierarchy_view` | `hr.rfid.ctrl.alarm.group` | - |  | `views/hr_rfid_ctrl_alarm_group.xml` |
| `hr_rfid_ctrl_alarm_group_view_kanban` | `hr.rfid.ctrl.alarm.group` | - |  | `views/hr_rfid_ctrl_alarm_group.xml` |
| `hr_rfid_ctrl_alarm_group_search_view` | `hr.rfid.ctrl.alarm.group` | - |  | `views/hr_rfid_ctrl_alarm_group.xml` |
| `emergency_group_form_view` | `hr.rfid.ctrl.emergency.group` | - |  | `views/hr_rfid_ctrl_emergency_group.xml` |
| `emergency_group_list_view` | `hr.rfid.ctrl.emergency.group` | - |  | `views/hr_rfid_ctrl_emergency_group.xml` |
| `emergency_group_view_kanban` | `hr.rfid.ctrl.emergency.group` | - |  | `views/hr_rfid_ctrl_emergency_group.xml` |
| `hr_rfid_controller_io_table_wiz` | `hr.rfid.ctrl.io.table.wiz` | - |  | `views/hr_rfid_ctrl_iotable.xml` |
| `hr_rfid_ctrl_th_form_view` | `hr.rfid.ctrl.th` | - |  | `views/hr_rfid_ctrl_th.xml` |
| `hr_rfid_ctrl_th_list_view` | `hr.rfid.ctrl.th` | - |  | `views/hr_rfid_ctrl_th.xml` |
| `hr_rfid_ctrl_th_search_view` | `hr.rfid.ctrl.th` | - |  | `views/hr_rfid_ctrl_th.xml` |
| `hr_rfid_ctrl_th_log_list_view` | `hr.rfid.ctrl.th.log` | - |  | `views/hr_rfid_ctrl_th_log.xml` |
| `hr_rfid_ctrl_th_log_graph_view` | `hr.rfid.ctrl.th.log` | - |  | `views/hr_rfid_ctrl_th_log.xml` |
| `hr_rfid_ctrl_th_log_pivot_view` | `hr.rfid.ctrl.th.log` | - |  | `views/hr_rfid_ctrl_th_log.xml` |
| `hr_rfid_ctrl_th_log_search_view` | `hr.rfid.ctrl.th.log` | - |  | `views/hr_rfid_ctrl_th_log.xml` |
| `hr_rfid_controller_ts_wiz` | `hr.rfid.ctrl.ts.week.wiz` | - |  | `views/hr_rfid_ctrl_time_schedule.xml` |
| `hr_rfid_time_schedule_view_form` | `hr.rfid.time.schedule` | - |  | `views/hr_rfid_ctrl_time_schedule.xml` |
| `hr_rfid_time_schedule_view_kanban` | `hr.rfid.time.schedule` | - |  | `views/hr_rfid_ctrl_time_schedule.xml` |
| `hr_rfid_time_schedule_view_list` | `hr.rfid.time.schedule` | - |  | `views/hr_rfid_ctrl_time_schedule.xml` |
| `hr_rfid_door_open_close_wiz_form` | `hr.rfid.door.open.close.wiz` | - |  | `views/hr_rfid_door.xml` |
| `hr_rfid_door_view_form` | `hr.rfid.door` | - |  | `views/hr_rfid_door.xml` |
| `hr_rfid_door_view_list` | `hr.rfid.door` | - |  | `views/hr_rfid_door.xml` |
| `hr_rfid_door_view_kanban` | `hr.rfid.door` | - |  | `views/hr_rfid_door.xml` |
| `hr_rfid_door_view_search` | `hr.rfid.door` | - |  | `views/hr_rfid_door.xml` |
| `hr_rfid_sys_ev_wiz_form` | `hr.rfid.event.sys.wiz` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_sys_ev_view_form` | `hr.rfid.event.system` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_sys_ev_view_list` | `hr.rfid.event.system` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_sys_ev_view_search` | `hr.rfid.event.system` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_sys_ev_view_calendar` | `hr.rfid.event.system` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_system_ev_view_pivot` | `hr.rfid.event.system` | - |  | `views/hr_rfid_event_system.xml` |
| `hr_rfid_user_ev_view_form` | `hr.rfid.event.user` | - |  | `views/hr_rfid_event_user.xml` |
| `hr_rfid_user_ev_view_list` | `hr.rfid.event.user` | - |  | `views/hr_rfid_event_user.xml` |
| `hr_rfid_user_ev_view_search` | `hr.rfid.event.user` | - |  | `views/hr_rfid_event_user.xml` |
| `hr_rfid_user_ev_view_calendar` | `hr.rfid.event.user` | - |  | `views/hr_rfid_event_user.xml` |
| `hr_rfid_user_ev_view_pivot` | `hr.rfid.event.user` | - |  | `views/hr_rfid_event_user.xml` |
| `hr_rfid_reader_view_form` | `hr.rfid.reader` | - |  | `views/hr_rfid_reader.xml` |
| `hr_rfid_reader_view_list` | `hr.rfid.reader` | - |  | `views/hr_rfid_reader.xml` |
| `hr_rfid_reader_view_search` | `hr.rfid.reader` | - |  | `views/hr_rfid_reader.xml` |
| `hr_rfid_webstack_view_form` | `hr.rfid.webstack` | - |  | `views/hr_rfid_webstack.xml` |
| `hr_rfid_webstack_view_list` | `hr.rfid.webstack` | - |  | `views/hr_rfid_webstack.xml` |
| `webstack_view_search` | `hr.rfid.webstack` | - |  | `views/hr_rfid_webstack.xml` |
| `hr_rfid_webstack_view_kanban` | `hr.rfid.webstack` | - |  | `views/hr_rfid_webstack.xml` |
| `hr_rfid_webstack_discovery_wiz` | `hr.rfid.webstack.discovery` | - |  | `views/hr_rfid_webstack_discovery.xml` |
| `hr_rfid_webstack_manual_create_wiz` | `hr.rfid.webstack.manual.create` | - |  | `views/hr_rfid_webstack_discovery.xml` |
| `hr_rfid_webstack_replace_wiz_view_form` | `hr.rfid.webstack.replace.wiz` | - |  | `views/hr_rfid_webstack_replace_wiz.xml` |
| `hr_rfid_workcode_view_form` | `hr.rfid.workcode` | - |  | `views/hr_rfid_workcode.xml` |
| `hr_rfid_workcode_view_list` | `hr.rfid.workcode` | - |  | `views/hr_rfid_workcode.xml` |
| `hr_rfid_zone_doors_wiz` | `hr.rfid.zone.doors.wiz` | - |  | `views/hr_rfid_zone.xml` |
| `hr_rfid_zone_view_form` | `hr.rfid.zone` | - |  | `views/hr_rfid_zone.xml` |
| `hr_rfid_zone_view_list` | `hr.rfid.zone` | - |  | `views/hr_rfid_zone.xml` |
| `rfid_form_inherit_res_company` | `res.company` | - | base.view_company_form | `views/res_company.xml` |
| `res_config_settings_view_form` | `res.config.settings` | - | base.res_config_settings_view_form | `views/res_config_setting_view.xml` |
| `hr_view_partner_form_inherit_hr_rfid` | `res.partner` | - | base.view_partner_form | `views/res_partner_views.xml` |
| `view_res_partner_filter_inherit` | `res.partner` | - | base.view_res_partner_filter | `views/res_partner_views.xml` |
| `res_partner_mass_acc_grs_wiz` | `res.partner.mass.wiz` | - |  | `views/res_partner_views.xml` |

#### Sample XPath operations

- In `digest_digest_view_form`:
  - `//group[@name='kpi_general'] [after]`

- In `hr_department_view_kanban_inherit_hr_rfid`:
  - `//div[@name='kanban_primary_right'] [inside]`

- In `hr_view_employee_form_inherit_hr_rfid`:
  - `//div[@name='button_box'] [inside]`

- In `rfid_form_inherit_res_company`:
  - `//notebook [inside]`

- In `res_config_settings_view_form`:
  - `//form [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `hr_rfid_group_viewer`, `hr_rfid_group_officer`, `hr_rfid_group_manager`, `hr_rfid_view_module_discovery`, `hr_rfid_view_rfid_data`, `hr_rfid_view_rfid_pin_code_data`, `hr_rfid_view_door_open_close`, `hr_rfid_view_door_arm_disarm`, `hr_rfid_view_emergency_on_off`, `hr_view_own_department`, `hr_rfid_view_own_department`


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_hr_manager_department_acc_grs` | `model_hr_department_acc_grs` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_manager_department_add_def_acc_grs` | `model_hr_department_add_def_acc_grs` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_manager_department_def_acc_gr` | `model_hr_department_def_acc_gr` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_manager_department_mass_wiz` | `model_hr_department_mass_wiz` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_rfid_data_access_group` | `model_hr_rfid_access_group` | `hr_rfid.hr_rfid_view_rfid_data` | ✓ |  |  |  |

| `access_hr_rfid_rfid_data_card` | `model_hr_rfid_card` | `hr_rfid.hr_rfid_view_rfid_data` | ✓ |  |  |  |

| `access_hr_rfid_officer_access_group` | `model_hr_rfid_access_group` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_access_group` | `model_hr_rfid_access_group` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_officer_access_group_c_rel` | `model_hr_rfid_access_group_contact_rel` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_access_group_door_rel` | `model_hr_rfid_access_group_door_rel` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_access_group_door_rel` | `model_hr_rfid_access_group_door_rel` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_officer_access_group_e_rel` | `model_hr_rfid_access_group_employee_rel` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_manager_access_group_wizard` | `model_hr_rfid_access_group_wizard` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_card` | `model_hr_rfid_card` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_card` | `model_hr_rfid_card` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_card_door_rel` | `model_hr_rfid_card_door_rel` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_card_door_rel` | `model_hr_rfid_card_door_rel` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_officer_card_type` | `model_hr_rfid_card_type` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_officer_command` | `model_hr_rfid_command` | `hr_rfid.hr_rfid_group_officer` | ✓ |  |  |  |

| `access_hr_rfid_manager_command` | `model_hr_rfid_command` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_ctrl` | `model_hr_rfid_ctrl` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_ctrl` | `model_hr_rfid_ctrl` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_ctrl` | `model_hr_rfid_ctrl` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_ctrl_output_ts` | `model_hr_rfid_ctrl_output_ts` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_ctrl_alarm` | `model_hr_rfid_ctrl_alarm` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_ctrl_alarm` | `model_hr_rfid_ctrl_alarm` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_viewer_ctrl_alarm_group` | `model_hr_rfid_ctrl_alarm_group` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_ctrl_alarm_group` | `model_hr_rfid_ctrl_alarm_group` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_ctrl_emergency_group` | `model_hr_rfid_ctrl_emergency_group` | `hr_rfid.hr_rfid_group_viewer` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_ctrl_emergency_group` | `model_hr_rfid_ctrl_emergency_group` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_manager_ctrl_io_table_row` | `model_hr_rfid_ctrl_io_table_row` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_ctrl_io_table_wiz` | `model_hr_rfid_ctrl_io_table_wiz` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ |  |

| `access_hr_rfid_viewer_ctrl_th` | `model_hr_rfid_ctrl_th` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_ctrl_th` | `model_hr_rfid_ctrl_th` | `hr_rfid.hr_rfid_group_viewer` | ✓ | ✓ |  |  |

| `access_hr_rfid_viewer_ctrl_th_log` | `model_hr_rfid_ctrl_th_log` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_ctrl_th_log` | `model_hr_rfid_ctrl_th_log` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_ctrl_ts_line` | `model_hr_rfid_ctrl_ts_line` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_ctrl_ts_line` | `model_hr_rfid_ctrl_ts_line` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_manager_ctrl_ts_week_wiz` | `model_hr_rfid_ctrl_ts_week_wiz` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_manager_ctrl_input_mask` | `hr_rfid.model_hr_rfid_ctrl_input_mask` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ |  |  |

| `access_hr_rfid_office_ctrl_input_mask` | `hr_rfid.model_hr_rfid_ctrl_input_mask` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_viewer_door` | `model_hr_rfid_door` | `hr_rfid.hr_rfid_group_viewer` | ✓ | ✓ |  |  |

| `access_hr_rfid_viewer_door_open_close_wiz` | `model_hr_rfid_door_open_close_wiz` | `hr_rfid.hr_rfid_group_viewer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_manager_event_sys_wiz` | `model_hr_rfid_event_sys_wiz` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_event_system` | `model_hr_rfid_event_system` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_event_system` | `model_hr_rfid_event_system` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ |  |

| `access_hr_rfid_erp_manager_event_system` | `model_hr_rfid_event_system` | `base.group_erp_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_rfid_data_event_user` | `model_hr_rfid_event_user` | `hr_rfid.hr_rfid_view_rfid_data` | ✓ |  |  |  |

| `access_hr_rfid_viewer_event_user` | `model_hr_rfid_event_user` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_manager_event_user` | `model_hr_rfid_event_user` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ |  |

| `access_hr_rfid_erp_manager_event_user` | `model_hr_rfid_event_user` | `base.group_erp_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_viewer_reader` | `model_hr_rfid_reader` | `hr_rfid.hr_rfid_group_viewer` | ✓ |  |  |  |

| `access_hr_rfid_officer_reader` | `model_hr_rfid_reader` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_officer_time_schedule` | `model_hr_rfid_time_schedule` | `hr_rfid.hr_rfid_group_officer` | ✓ |  |  |  |

| `access_hr_rfid_manager_time_schedule` | `model_hr_rfid_time_schedule` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ |  |  |

| `access_hr_rfid_officer_webstack` | `model_hr_rfid_webstack` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_webstack` | `model_hr_rfid_webstack` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_webstack_discovery` | `model_hr_rfid_webstack_discovery` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_webstack_discovery_row` | `model_hr_rfid_webstack_discovery_row` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_webstack_manual_create` | `model_hr_rfid_webstack_manual_create` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_webstack_replace_wiz` | `hr_rfid.model_hr_rfid_webstack_replace_wiz` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_officer_workcode` | `model_hr_rfid_workcode` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ |  |  |

| `access_hr_rfid_manager_workcode` | `model_hr_rfid_workcode` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_officer_zone` | `model_hr_rfid_zone` | `hr_rfid.hr_rfid_group_officer` | ✓ |  |  |  |

| `access_hr_rfid_manager_zone` | `model_hr_rfid_zone` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_zone_doors_wiz` | `model_hr_rfid_zone_doors_wiz` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_notification_officer` | `hr_rfid.model_hr_rfid_notification` | `hr_rfid.hr_rfid_group_officer` | ✓ |  |  |  |

| `access_hr_rfid_notification_manager` | `hr_rfid.model_hr_rfid_notification` | `hr_rfid.hr_rfid_group_manager` | ✓ | ✓ | ✓ | ✓ |

| `access_res_partner_mass_wiz_officer` | `hr_rfid.model_res_partner_mass_wiz` | `hr_rfid.hr_rfid_group_officer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_ws_dedup_manager` | `model_hr_rfid_ws_dedup` | `hr_rfid.hr_rfid_group_manager` | ✓ |  |  |  |


### Record rules (ir.rule)

- **`ir_rule_hr_rfid_card_multi_company`** on `model_hr_rfid_card` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_access_group_multi_company`** on `model_hr_rfid_access_group` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_zone_multi_company`** on `model_hr_rfid_zone` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_workcode_multi_company`** on `model_hr_rfid_workcode` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`
- **`ir_rule_hr_rfid_webstack_multi_company`** on `model_hr_rfid_webstack` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_controllers_multi_company`** on `model_hr_rfid_ctrl` - perms=`R`, groups=`global`, domain=`['|', ('webstack_id.company_id', 'in', company_ids), ('webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_controllers_multi_company_write`** on `model_hr_rfid_ctrl` - perms=`WCD`, groups=`global`, domain=`[('webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_time_schedule_multi_company`** on `model_hr_rfid_time_schedule` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_door_multi_company`** on `model_hr_rfid_door` - perms=`R`, groups=`global`, domain=`['|', ('company_id', 'in', company_ids + [False]), ('webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_door_multi_company_write`** on `model_hr_rfid_door` - perms=`WCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`
- **`ir_rule_hr_rfid_reader_multi_company`** on `model_hr_rfid_reader` - perms=`R`, groups=`global`, domain=`['|', '|', '|', ('controller_id', '=', False), ('webstack_id.company_id', '=', False), ('webstack_id.company_id', 'in', company_ids), ('webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_reader_multi_company_write`** on `model_hr_rfid_reader` - perms=`WCD`, groups=`global`, domain=`['|', '|', ('controller_id', '=', False), ('webstack_id.company_id', '=', False), ('webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_alarm_line_multi_company`** on `model_hr_rfid_ctrl_alarm` - perms=`R`, groups=`global`, domain=`['|', ('controller_id.webstack_id.company_id', 'in', company_ids), ('controller_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_alarm_line_multi_company_write`** on `model_hr_rfid_ctrl_alarm` - perms=`WCD`, groups=`global`, domain=`[('controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_th_multi_company`** on `model_hr_rfid_ctrl_th` - perms=`R`, groups=`global`, domain=`['|', ('controller_id.webstack_id.company_id', 'in', company_ids), ('controller_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_th_multi_company_write`** on `model_hr_rfid_ctrl_th` - perms=`WCD`, groups=`global`, domain=`[('controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_th_log_multi_company`** on `model_hr_rfid_ctrl_th_log` - perms=`R`, groups=`global`, domain=`['|', ('th_id.controller_id.webstack_id.company_id', 'in', company_ids), ('th_id.controller_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_th_log_multi_company_write`** on `model_hr_rfid_ctrl_th_log` - perms=`WCD`, groups=`global`, domain=`[('th_id.controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_event_user_multi_company`** on `model_hr_rfid_event_user` - perms=`R`, groups=`global`, domain=`[
                '|', '|',
                '|', ('employee_id.company_id', 'in', company_ids),
                ('employee_id.company_id', '=', False),
                '|', ('contact_id.company_id', 'in', company_ids),
                ('contact_id.company_id', '=', False),
                '&', ('employee_id', '=', False),
                '&', ('contact_id', '=', False),
                '|', '|', '|', '|',
                ('reader_id.controller_id.webstack_id.company_id', 'in', company_ids),
                ('reader_id.controller_id.webstack_id.shared_company_ids', 'in', company_ids),
                ('reader_id', '=', False),
                ('reader_id.controller_id', '=', False),
                ('reader_id.controller_id.webstack_id.company_id', '=', False)
            ]`
- **`ir_rule_hr_rfid_event_system_multi_company`** on `model_hr_rfid_event_system` - perms=`R`, groups=`global`, domain=`['|', '|', '|', ('controller_id', '=', False), ('controller_id.webstack_id.company_id', '=', False), ('controller_id.webstack_id.company_id', 'in', company_ids), ('controller_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_event_system_multi_company_write`** on `model_hr_rfid_event_system` - perms=`WCD`, groups=`global`, domain=`['|', '|', ('controller_id', '=', False), ('controller_id.webstack_id.company_id', '=', False), ('controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_command_multi_company`** on `model_hr_rfid_command` - perms=`RWCD`, groups=`global`, domain=`[('webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_alarm_groups_multi_company`** on `model_hr_rfid_ctrl_alarm_group` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_emergency_groups_multi_company`** on `model_hr_rfid_ctrl_emergency_group` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_card_door_rel_multi_company`** on `model_hr_rfid_card_door_rel` - perms=`R`, groups=`global`, domain=`['|', ('card_id.company_id', 'in', company_ids), '|', ('door_id.company_id', 'in', company_ids + [False]), ('door_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_card_door_rel_multi_company_write`** on `model_hr_rfid_card_door_rel` - perms=`WCD`, groups=`global`, domain=`['|', ('card_id.company_id', 'in', company_ids), ('door_id.company_id', 'in', company_ids + [False])]`
- **`ir_rule_hr_rfid_access_group_door_rel_multi_company`** on `model_hr_rfid_access_group_door_rel` - perms=`R`, groups=`global`, domain=`['|', ('access_group_id.company_id', 'in', company_ids), '|', ('door_id.company_id', 'in', company_ids + [False]), ('door_id.webstack_id.shared_company_ids', 'in', company_ids)]`
- **`ir_rule_hr_rfid_access_group_door_rel_multi_company_write`** on `model_hr_rfid_access_group_door_rel` - perms=`WCD`, groups=`global`, domain=`['|', ('access_group_id.company_id', 'in', company_ids), ('door_id.company_id', 'in', company_ids + [False])]`
- **`hr_rfid_group_officer_department_cards_rule`** on `hr_rfid.model_hr_rfid_card` - perms=`RWCD`, groups=`hr_rfid_view_own_department`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_view_own_department_employees_rule`** on `hr.model_hr_employee` - perms=`RWCD`, groups=`hr_view_own_department`, domain=`[('department_id.id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_view_own_department_department_rule`** on `hr.model_hr_department` - perms=`RWCD`, groups=`hr_view_own_department`, domain=`[('id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_group_view_own_department_events_rule`** on `hr_rfid.model_hr_rfid_event_user` - perms=`RWCD`, groups=`hr_rfid_view_own_department`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_rfid_set_card_active_inactive_status`** (HR RFID: Check card activation status) on `model_hr_rfid_card`, runs every 1 minutes, active=True
- **`hr_rfid_sync_ctrl_clock_cron`** (HR RFID: Synchronize controller clocks) on `model_hr_rfid_command`, runs every 3 hours, active=True
- **`hr_rfid_read_ctrl_status_cron`** (HR RFID: Read controller statuses) on `model_hr_rfid_command`, runs every 5 minutes, active=True
- **`hr_rfid_check_module_presence_cron`** (HR RFID: Check module presence) on `model_hr_rfid_webstack`, runs every 5 minutes, active=True
- **`hr_rfid_ws_republish_cron`** (HR RFID: Real-time command re-publish) on `model_hr_rfid_command`, runs every 1 minutes, active=True

### Data records summary

- `ir.actions.act_window`: 43 record(s)
- `hr.rfid.event.user`: 11 record(s)
- `hr.rfid.card.type`: 10 record(s)
- `ir.actions.server`: 10 record(s)
- `hr.rfid.card`: 7 record(s)
- `ir.cron`: 5 record(s)
- `onboarding.onboarding.step`: 5 record(s)
- `hr.rfid.access.group.employee.rel`: 5 record(s)
- `hr.rfid.door`: 4 record(s)
- `hr.rfid.reader`: 4 record(s)
- `ir.config_parameter`: 3 record(s)
- `hr.department`: 3 record(s)
- `hr.rfid.workcode`: 3 record(s)
- `ir.actions.report`: 3 record(s)
- `hr.rfid.ctrl`: 2 record(s)
- `hr.rfid.access.group`: 2 record(s)
- `mail.template`: 1 record(s)
- `onboarding.onboarding`: 1 record(s)
- `res.lang`: 1 record(s)
- `res.users`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**OWL components**: `OnboardingBanner`


**JS files** (2): `static/src/components/onboarding/onboarding.js`, `static/src/views/onboarding_anywhere/onboarding_anywhere.js`


**SCSS files** (4): `static/src/scss/_variables.scss`, `static/src/scss/card_foldable_badge_report.scss`, `static/src/scss/card_full_page_ticket_report.scss`, `static/src/scss/card_full_page_ticket_report_pdf.scss`


**QWeb templates** (2): `static/src/components/onboarding/onboarding.xml`, `static/src/views/onboarding_anywhere/onboarding_anywhere.xml`


**QWeb templates in XML data, rendered by the server** (5): `card_barcode_report_template_foldable_badge`, `hr_rfid_card_report_template_foldable_badge`, `res_partner_report_template_foldable_badge`, `hr_employee_report_template_foldable_badge`, `card_barcode_report_template_formatted_address`


**Asset bundles extended in the manifest**: `web.assets_backend`, `web.report_assets_common`, `web.report_assets_pdf`, `web.assets_unit_tests` (tests only), `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (7): `static/tests/onboarding_banner.test.js`, `static/tests/onboarding_in_any_view.test.js`, `static/tests/tours/access_group_add_door_tour.js`, `static/tests/tours/add_webstack_tour.js`, `static/tests/tours/card_assign_tour.js`, `static/tests/tours/onboarding_panel_tour.js`, `static/tests/tours/realtime_channel_tour.js`



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

<figure id='fig-static-src-img-how-to-fold-1-png'>

![How To Fold 1](static/src/img/how_to_fold_1.png)

<figcaption>How To Fold 1</figcaption>
</figure>

> Tags: `how`, `fold`

<figure id='fig-static-src-img-how-to-fold-2-png'>

![How To Fold 2](static/src/img/how_to_fold_2.png)

<figcaption>How To Fold 2</figcaption>
</figure>

> Tags: `how`, `fold`

<figure id='fig-static-src-img-how-to-fold-3-png'>

![How To Fold 3](static/src/img/how_to_fold_3.png)

<figcaption>How To Fold 3</figcaption>
</figure>

> Tags: `how`, `fold`

<figure id='fig-static-src-img-how-to-fold-4-png'>

![How To Fold 4](static/src/img/how_to_fold_4.png)

<figcaption>How To Fold 4</figcaption>
</figure>

> Tags: `how`, `fold`

<figure id='fig-static-src-img-report-foldable-badge-background-png'>

![Report Foldable Badge Background](static/src/img/report_foldable_badge_background.png)

<figcaption>Report Foldable Badge Background</figcaption>
</figure>

> Tags: `report`, `foldable`, `badge`, `background`

<figure id='fig-static-src-img-report-full-page-ticket-background-png'>

![Report Full Page Ticket Background](static/src/img/report_full_page_ticket_background.png)

<figcaption>Report Full Page Ticket Background</figcaption>
</figure>

> Tags: `report`, `full`, `page`, `ticket`, `background`


## FAQ & Troubleshooting <a id='faq'></a>
Entries derived from the module's own code comments and bug-fix commit history.

### From `code_comments` (15)

#### TODO: Need to review and delete this

**TODO** in `models/hr_rfid_access_group.py:444`

> Need to review and delete this

#### TODO: New field. Need to implemented in cron job tasks!!!

**TODO** in `models/hr_rfid_access_group.py:600`

> New field. Need to implemented in cron job tasks!!!

#### TODO: Why this is here?!

**TODO** in `models/hr_rfid_command.py:589`

> Why this is here?!

#### TODO: Check if result is usless and delete command as previos function

**TODO** in `models/hr_rfid_ctrl.py:1287`

> Check if result is usless and delete command as previos function

#### TODO: Rename to just 'type'

**TODO** in `models/hr_rfid_ctrl_reader.py:37`

> Rename to just 'type'

#### TODO: Store command in model as in execution

**TODO** in `models/hr_rfid_webstack.py:872`

> Store command in model as in execution

#### TODO: get list of stored webstack serials

**TODO** in `models/hr_rfid_webstack_discovery.py:46`

> get list of stored webstack serials

#### TODO: Debug and test relay controller with this event

**TODO** in `models/hr_rfid_webstack_hw_events.py:171`

> Debug and test relay controller with this event

#### TODO: Reader number in relay controller hold the door 1 or 2!!!!!

**TODO** in `models/hr_rfid_webstack_hw_events.py:293`

> Reader number in relay controller hold the door 1 or 2!!!!!

#### TODO: Check details

**TODO** in `tests/test_functional.py:72`

> Check details

#### TODO: Check details

**TODO** in `tests/test_functional_old.py:74`

> Check details

#### TODO: remove buttons and move actions

**TODO** in `views/hr_rfid_access_group.xml:348`

> remove buttons and move actions

#### TODO: move view to actions

**TODO** in `views/hr_rfid_card.xml:197`

> move view to actions

#### TODO: delete buttons and move the actions

**TODO** in `views/hr_rfid_door.xml:369`

> delete buttons and move the actions

#### TODO: remove buttons and move actions

**TODO** in `views/hr_rfid_zone.xml:162`

> remove buttons and move actions

### From `git_log` (63)

#### Fix: fix(hr_rfid): green the vending + tour tests broken by three prior ...

Commit `b5dfd0bc1f` (2026-07-22): fix(hr_rfid): green the vending + tour tests broken by three prior changes

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: fix(hr_rfid): HTTP auth idempotent for unprovisioned 0000 + G1 heal ...

Commit `03a923e8c4` (2026-07-19): fix(hr_rfid): HTTP auth idempotent for unprovisioned 0000 + G1 heal (precommit)

#### Fix: fix(hr_rfid): remove dead orphaned hr_rfid_notification.xml ...

Commit `e6f8f6b466` (2026-07-19): fix(hr_rfid): remove dead orphaned hr_rfid_notification.xml (precommit A12)

#### Fix: fix(hr_rfid): system-event grouping never matched door events + no ...

Commit `c2a718801b` (2026-07-17): fix(hr_rfid): system-event grouping never matched door events + no time bound

#### Fix: fix(hr_rfid): reword two WS log lines so a serial doesn't read as ...

Commit `7f232e99c3` (2026-07-14): fix(hr_rfid): reword two WS log lines so a serial doesn't read as "N failed"

#### Fix: [FIX] hr_rfid: silent-failure-hunter findings on the websocket layer

Commit `639141922a` (2026-07-11): [FIX] hr_rfid: silent-failure-hunter findings on the websocket layer

#### Fix: [FIX] hr_rfid: security-review hardening of the websocket ingress

Commit `a22ec8fd10` (2026-07-11): [FIX] hr_rfid: security-review hardening of the websocket ingress

#### Fix: [FIX] revert malformed manual bg.po appends (broke web translation ...

Commit `fdb5eabb0c` (2026-06-24): [FIX] revert malformed manual bg.po appends (broke web translation loading)

#### Fix: [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

Commit `93125c7183` (2026-06-11): [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

#### Fix: [FIX] hr_rfid family: multi-company rules - global records + broken ...

Commit `a58ac6f455` (2026-06-11): [FIX] hr_rfid family: multi-company rules - global records + broken M2O chains were hidden

#### Fix: [FIX] hr_rfid: honor 'delay 0 = disabled' for delay_between_events

Commit `d78c5a8466` (2026-06-10): [FIX] hr_rfid: honor 'delay 0 = disabled' for delay_between_events

#### Fix: [FIX] hr_rfid: QR code mismatches hardware hex for w34s cards

Commit `47456010aa` (2026-05-20): [FIX] hr_rfid: QR code mismatches hardware hex for w34s cards

#### Fix: [FIX] hr_rfid: preserve card access on overlapping access group rels

Commit `46650f3373` (2026-05-19): [FIX] hr_rfid: preserve card access on overlapping access group rels

#### Fix: [FIX] hr_rfid: handle firmware event 32 (SOT_DENIED) as card event

Commit `3213db515a` (2026-04-23): [FIX] hr_rfid: handle firmware event 32 (SOT_DENIED) as card event

#### Fix: [IMP] hr_rfid: Fix exception variable naming and lazy log formatting

Commit `c3a615d172` (2026-04-03): [IMP] hr_rfid: Fix exception variable naming and lazy log formatting

#### Fix: [FIX] hr_rfid: Continue command chain on controller error response

Commit `7367e5bccc` (2026-04-03): [FIX] hr_rfid: Continue command chain on controller error response

#### Fix: [FIX] hr_rfid: Skip FF command for vending controllers during init

Commit `ccfff62d89` (2026-04-03): [FIX] hr_rfid: Skip FF command for vending controllers during init

#### Fix: [FIX] hr_rfid: Handle concurrent onboarding step progress creation

Commit `e4438fc921` (2026-03-28): [FIX] hr_rfid: Handle concurrent onboarding step progress creation

#### Fix: [FIX] hr_rfid: Fix legacy module 10.3 JSON response format

Commit `58827cc6c4` (2026-03-26): [FIX] hr_rfid: Fix legacy module 10.3 JSON response format

#### Fix: [FIX] hr_rfid: Stop command flooding on controller error response

Commit `a751b6c771` (2026-03-26): [FIX] hr_rfid: Stop command flooding on controller error response

#### Fix: [FIX] hr_rfid: Fix command retry loop causing event flooding

Commit `1b62ae05df` (2026-03-26): [FIX] hr_rfid: Fix command retry loop causing event flooding

#### Fix: [FIX] hr_rfid: Handle concurrent onboarding progress creation

Commit `1a00ac4e5b` (2026-03-26): [FIX] hr_rfid: Handle concurrent onboarding progress creation

#### Fix: [REM] hr_rfid: Delete obsolete http.py monkey-patch

Commit `311ce5c7e3` (2026-03-19): [REM] hr_rfid: Delete obsolete http.py monkey-patch

#### Fix: [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher

Commit `57aba8363e` (2026-03-19): [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid`
- Source digest: `sha256:8fae63ae5f5fdba8a7d7220c4629c62c3c8431043cc7cba8a1f624338cfaa506`
- Generated at: `2026-11-09T07:58:39+00:00`
- Generator: `polimex_module_knowledge`
