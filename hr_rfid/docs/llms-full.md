---
id: hr_rfid
title: RFID Access Control
module: hr_rfid
module_version: 19.0.2.32.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage employee access control
last_updated: '2026-08-26'
source_digest: sha256:bfab40bc1cfdb3403bf012bf5a0430bfb6d4596ac391cee94607bed4b739ad8c
depends:
- hr
- contacts
- digest
- onboarding
- polimex_ws
entities:
  primary: balloon.mixin
  related:
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
  - hr.rfid.card
keywords:
- acc
- access
- balloon
- control
- def
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


# RFID Access Control - `hr_rfid` v19.0.2.32.0

Manage employee access control

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid`
- **Version**: `19.0.2.32.0`
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
  - Return action for message in balloon.

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
| `kpi_hr_rfid_denied_value` | Integer |  |  | - | Live count of denied access events during the digest window. |
| `kpi_hr_rfid_granted_value` | Integer |  |  | - | Live count of granted access events during the digest window. |
| `kpi_hr_rfid_system_value` | Integer |  |  | - | Live count of system events during the digest window. |
| `kpi_hr_rfid_command_value` | Integer |  |  | - | Live count of commands executed against controllers during the digest window. |
| `kpi_hr_rfid_card_value` | Integer |  |  | - | Live count of new cards created during the digest window. |

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
| `delay_between_events` | Integer |  |  | ✓ | Anti-passback feature: Sets the minimum time (in seconds) that must pass between |
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
| `card_type` | Many2one → \`hr.rfid.card.type\` |  |  | - | The type of RFID card required for this door (automatically determined by the do |
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` | Time schedule | ✓ | ✓ | Defines when this door can be accessed by this group. For example: "Monday-Frida |
| `alarm_rights` | Boolean |  | ✓ | ✓ | Allow users in this group to arm/disarm the door's alarm system. This is typical |

#### Notable methods

- **`_check_shared_module_grant(self)`** - decorators: `@api.constrains`
  - A company the module is shared with may include its doors in its
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
| `internal_state` | Boolean |  |  | ✓ | Internal field used to track state changes and trigger card updates. This is man |
| `access_group_id` | Many2one → \`hr.rfid.access.group\` | Access Group | ✓ | ✓ | The access group that provides door permissions to the employee or contact. Mult |
| `activate_on` | Datetime | Activation Date |  | ✓ | The date and time when this access group becomes active for the user. Access wil |
| `expiration` | Datetime | Expiration Date |  | ✓ | The date and time when this access group expires and access is revoked. Leave em |
| `visits_counting` | Boolean | Enable Visit Counting |  | ✓ | Enable visit counting to limit the number of times this access can be used. Usef |
| `permitted_visits` | Integer | Permitted Visits |  | ✓ | Maximum number of visits allowed with this access group. After reaching this lim |
| `visits_counter` | Integer | Visit Counter |  | ✓ | Current number of visits used. When this reaches the permitted visits limit, acc |

#### Notable methods

- **`active_for_visits(self)`** - decorators: -
  - Whether every relation in ``self`` still grants access from the
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
| `name` | Char |  |  | - | Display name of the card - shows either the card reference or card number |
| `internal_number` | Char |  |  | ✓ | Internal representation of the card number used by the system. This is automatic |
| `number` | Char | Card Number | ✓ | ✓ | The unique 10-digit number printed on or associated with the RFID card. This is  |
| `card_input_type` | Selection |  |  | ✓ | Technical format of how the card number is encoded. Wiegand 34 bit (5d+5d) split |
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
| `pin_code` | Char |  |  | - | The PIN code associated with this card's owner. Used for doors that require both |
| `barcode_number` | Char |  |  | - | Hexadecimal representation of the card number, used for barcode printing and sca |
| `is_barcode` | Boolean |  |  | - | Indicates if this card is configured as a barcode card type. |

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
| `name` | Char |  |  | - | User-friendly name combining command code and description |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module | ✓ | ✓ | The communication module (webstack) that connects to the physical controller. Th |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | The physical RFID controller device that manages card readers and access control |
| `cmd` | Selection | Command | ✓ | ✓ | The type of operation to perform on the controller. Commands starting with "F" r |
| `cmd_data` | Char | Command data |  | ✓ | Additional parameters or values sent with the command. This might include card n |
| `status` | Selection | Status |  | ✓ | Current execution state of the command: • Wait: Command is queued and waiting to |
| `error` | Selection | Error |  | ✓ | Detailed error information when a command fails. Common errors include: • Commun |
| `create_date` | Datetime |  |  | ✓ |  |
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
- **`_update_commands(self)`** - decorators: `@api.model`
- **`_sync_clocks(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.webstack`

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
| `time_schedule_id` | Many2one → \`hr.rfid.time.schedule\` |  | ✓ | ✓ | Time schedule that controls when this output will be active. The output will aut |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` |  | ✓ | ✓ | Controller that owns this output-to-time-schedule binding. Cascade on delete — t |
| `output_count` | Integer |  |  | - | Number of physical outputs reported by the controller. Used to validate that out |
| `max_ts` | Integer |  |  | - | Highest time-schedule slot the controller supports. Used to validate that the as |
| `time_schedule_number` | Integer |  |  | - | Numeric slot of the linked time schedule, shown for quick reference in lists. |

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
| `controller_id` | Many2one → \`hr.rfid.ctrl\` |  | ✓ | ✓ | Controller that owns this input-mask row. Cascade on delete — the row disappears |
| `input_count` | Integer |  |  | - | Total number of physical inputs on the controller — used to display only the mas |

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
| `inputs_mask` | Integer |  |  | ✓ | Binary mask that defines the type of each input (NC/NO). Each bit represents one |
| `input_mask_ids` | One2many → \`hr.rfid.ctrl.input.mask\` | Input Masks |  | ✓ | Per-input NC/NO configuration. One row per physical input. Toggling a row sends  |
| `input_states` | Integer |  |  | ✓ | Current state of all inputs as a binary value. Each bit represents one input: 1  |
| `outputs` | Integer | Outputs |  | ✓ | Number of physical output connections (relays) available on this controller. Out |
| `output_states` | Integer |  |  | ✓ | Current state of all outputs as a binary value. Each bit represents one output:  |
| `output_ts_ids` | One2many → \`hr.rfid.ctrl.output.ts\` | Output's Time schedules |  | ✓ | Control the Output's Time schedules of the controller. You can add PLC-like logi |
| `relay_output_mask` | Boolean |  |  | ✓ | Relay output configuration for relay controllers. When enabled, relay outputs op |
| `readers` | Integer | Readers |  | ✓ | Number of RFID card readers that can be connected to this controller. Each reade |
| `time_schedules` | Integer | Time Schedules |  | ✓ | Maximum number of time schedules this controller can store. Time schedules defin |
| `io_table_lines` | Integer | IO Table Lines |  | ✓ | Number of programmable logic lines in the I/O table. Each line can contain rules |
| `alarm_lines` | Integer | Alarm Lines |  | ✓ | Number of dedicated alarm zone inputs on this controller. Each zone can monitor  |
| `alarm_line_states` | Char | Alarm Line States |  | ✓ | Real-time status of each alarm zone as hexadecimal values. Shows if zones are ar |
| `alarm_lines_setup` | Char |  |  | ✓ | Configuration data for alarm zones in hexadecimal format. Defines which zones ar |
| `alarm_sensor_events` | Boolean | Alarm Sensor Events |  | ✓ | When enabled, the controller reports all sensor state changes as events, even wh |
| `siren_state` | Boolean |  |  | - | Current state of the alarm siren. True = Siren is active/sounding, False = Siren |
| `emergency_group_id` | Many2one → \`hr.rfid.ctrl.emergency.group\` |  |  | ✓ | Emergency group this controller belongs to. When any controller in the group ent |
| `emergency_state` | Selection |  |  | - | Emergency mode status: - No Emergency: Normal operation - Group Emergency: Activ |
| `mode` | Integer | Controller Mode |  | ✓ | Operating mode that defines how many doors/devices this controller manages and h |
| `mode_selection` | Selection | Controller mode | ✓ | - | Door control mode for standard access controllers. One door mode uses all resour |
| `mode_selection_4` | Selection | Doors mode | ✓ | - | Door control mode for advanced access controllers that support up to 4 doors. Ea |
| `mode_selection_31` | Selection | Relays mode | ✓ | - | Relay configuration mode: - 1 x 32: Single bank of 32 relays - 2 x 16: Two indep |
| `external_db` | Boolean | External DB |  | ✓ | External database mode. When on, the controller does not keep the card list in i |
| `relay_time_factor` | Selection | Relay Time Factor |  | ✓ | Time unit for relay activation duration. When set to "1 second", relay timers co |
| `dual_person_mode` | Boolean | Dual Person Mode |  | ✓ | Security feature requiring two authorized persons to badge within a time window  |
| `interlocking_mode` | Boolean | Interlocking Mode |  | ✓ | Interlocking (mantrap): only one of the controller's doors may be open at a time |
| `max_cards_count` | Integer | Maximum Cards |  | ✓ | Maximum number of access cards this controller can store in its internal memory. |
| `cards_count` | Integer |  |  | ✓ | Current number of access cards stored in the controller's memory. When this appr |
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
| `event_interval` | Integer |  |  | - | Interval in minutes for automatic temperature/humidity event reporting. Set to 0 |
| `high_temperature` | Float |  |  | ✓ | Upper temperature threshold in Celsius. When exceeded, the controller triggers a |
| `low_temperature` | Float |  |  | ✓ | Lower temperature threshold in Celsius. When temperature drops below this value, |
| `hysteresis` | Float |  |  | ✓ | Temperature hysteresis (dead band) in Celsius to prevent alarm flickering. The t |
| `system_voltage` | Float | System Voltage |  | ✓ | Current voltage level of the controller's internal power supply in VDC. Normal r |
| `input_voltage` | Float | Input Voltage |  | ✓ | Voltage level supplied to the controller from the external power source in VDC.  |
| `last_f0_read` | Datetime | Last System Information Update |  | ✓ | Date and time when the controller's system information (hardware details, capabi |
| `commands_count` | Char | Commands count |  | - | Total number of commands (pending and executed) for this controller. High number |
| `system_event_count` | Char | System Events count |  | - | Number of system events (errors, status changes, communication issues) logged by |
| `user_event_count` | Char | User events count |  | - | Number of user access events (card swipes, access granted/denied, door forced) r |
| `readers_count` | Char | Readers count |  | - | Number of card readers configured for this controller. Typically matches the num |
| `doors_count` | Char | Doors count |  | - | Number of doors managed by this controller. Depends on the controller mode: sing |
| `alarm_line_count` | Char | Alarm line count |  | - | Number of alarm zones configured for this controller. Each zone can monitor diff |
| `default_io_table` | Char |  |  | - | Factory default I/O table configuration for this controller model and mode. Used |

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

### `hr.rfid.ctrl.alarm` <a id='model-hr-rfid-ctrl-alarm'></a>
Python class `HrRfidCtrlAlarm` in `models/hr_rfid_ctrl_alarm.py:6`.  Model.  Inherits: `mail.thread`, `balloon.mixin`.  Description: *Controller Alarm Lines*.  Default order: `controller_id, line_number`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  | ✓ | ✓ | Enter a descriptive name for this alarm sensor (e.g., 'Main Entrance Motion Dete |
| `line_number` | Integer |  |  | ✓ | The physical input number on the controller where this sensor is connected (1-16 |
| `state` | Selection |  |  | - | Current status of the alarm sensor: • Unknown - Communication lost with sensor • |
| `armed` | Selection |  |  | ✓ | Security status of this alarm line: • No Alarm functionality - This line is not  |
| `enableAC` | Boolean | Integrate with Access control |  | ✓ | When enabled, this alarm line will work together with door access control: • Aut |
| `enableDC` | Boolean | Include Door contact |  | ✓ | Monitor the door's open/closed status as part of this alarm: • When armed, an op |
| `enabled` | Boolean |  |  | ✓ | Master switch for this alarm line: • ON - The sensor is active and can trigger a |
| `siren_state` | Boolean |  |  | - | Shows whether the alarm siren is currently sounding: • ON - Siren is active (lou |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | The RFID controller device that monitors this alarm sensor. Each controller can  |
| `control_output` | Integer |  |  | ✓ | Technical field: The output number used to arm/disarm this line remotely |
| `door_id` | Many2one → \`hr.rfid.door\` |  |  | ✓ | Link this alarm to a specific door for integrated security: • The alarm can auto |
| `user_event_count` | Integer |  |  | - | Number of alarm events triggered by user actions (e.g., motion detected, door op |
| `system_event_count` | Integer |  |  | - | Number of technical events for this alarm line (e.g., sensor faults, communicati |
| `alarm_group_id` | Many2one → \`hr.rfid.ctrl.alarm.group\` |  |  | ✓ | Assign this alarm to a group for easier management: • Arm/disarm multiple alarms |

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
| `name` | Char |  | ✓ | ✓ | Enter a descriptive name for this alarm group (e.g., 'First Floor Alarms', 'Ware |
| `color` | Integer | Color Index |  | ✓ | Choose a color to visually distinguish this group in the hierarchy view. This he |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | The company that owns this alarm group. Used in multi-company setups to separate |
| `state` | Selection |  |  | ✓ | Overall security status of all alarms in this group: • No Alarm functionality -  |
| `parent_id` | Many2one → \`hr.rfid.ctrl.alarm.group\` |  |  | ✓ | Parent group for creating hierarchical alarm structures. For example: • Building |
| `child_ids` | One2many → \`hr.rfid.ctrl.alarm.group\` |  |  | ✓ | Sub-groups under this group. When you arm/disarm this group, all child groups wi |
| `alarm_line_ids` | One2many → \`hr.rfid.ctrl.alarm\` |  | ✓ | ✓ | Individual alarm sensors that belong to this group. You can: • Add multiple sens |

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
| `name` | Char |  |  | ✓ | Name of the emergency group (e.g., 'Emergency Floor 1', 'Building A Emergency'). |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns this emergency group. Used to separate emergency groups betwee |
| `controller_ids` | One2many → \`hr.rfid.ctrl\` |  |  | ✓ | List of controllers that belong to this emergency group. When emergency mode is  |
| `state` | Selection |  |  | - | Current state of the emergency group: • Normal: All controllers operating normal |

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
| `controller_id` | Many2one → \`hr.rfid.ctrl\` |  | ✓ | ✓ | Controller being edited. Set automatically from the active record when the wizar |
| `io_row_ids` | Many2many → \`hr.rfid.ctrl.io.table.row\` | IO Table |  | ✓ | One row per event code (Duress, Card OK, etc.) with the values written to each o |
| `outs` | Integer |  |  | ✓ | Number of output columns shown in the table (4 for relay controllers, otherwise  |

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
| `active` | Boolean |  |  | ✓ | When unchecked, this sensor will be hidden and stop recording data. You can reac |
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
- **`_demo_generate_th_readings(self)`** - decorators: `@api.model`
  - Fill the shipped demo sensor with two weeks of readings.
  - effects: `log_info`
  - touches: `ir.config_parameter`

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
| `is_empty` | Boolean |  |  | - | Indicates whether this time schedule has any active time periods defined. Empty  |
| `ts_data` | Char |  |  | ✓ | Internal representation of the time schedule data in hexadecimal format. Contain |
| `access_group_door_ids` | One2many → \`hr.rfid.access.group.door.rel\` | Access Group/Door Combinations |  | ✓ | Shows all doors and access groups that use this time schedule. This helps you un |
| `controller_ids` | Many2many → \`hr.rfid.ctrl\` |  |  | ✓ | RFID controllers that have this time schedule programmed. The schedule is automa |

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
| `display_name` | Char |  |  | - | Display name showing the day and interval number for easy identification. |
| `begin` | Float |  |  | ✓ | Start time for this access period. Enter in 24-hour format (e.g., 8.5 for 8:30 A |
| `end` | Float |  |  | ✓ | End time for this access period. Enter in 24-hour format (e.g., 17.5 for 5:30 PM |
| `number` | Integer |  |  | ✓ | Interval number (1-4). Each day can have up to 4 separate access periods. For ex |
| `day_number` | Integer |  |  | ✓ | Internal day number (0-7) used for data processing. |
| `day` | Selection | Day |  | ✓ | Day of the week or Holiday. The Holiday setting applies to all dates marked as h |
| `week_id` | Many2one → \`hr.rfid.ctrl.ts.week.wiz\` |  |  | ✓ | Reference to the parent time schedule week wizard. |

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
| `interval_ids` | One2many → \`hr.rfid.ctrl.ts.line\` |  |  | ✓ | Define up to 4 time periods per day when access is allowed. The schedule works a |

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
| `hotel_readers` | Integer |  |  | - | Number of hotel-mode readers connected to the controller. Used for hotel room ma |
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
  - :param action: 1 for door open, 0 for door close
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
- **`update_card_rels(self, card_id, access_group=None)`** - decorators: `@api.model`
  - Checks all card-door relations and updates them
- **`update_door_rels(self, door_id, access_group=None)`** - decorators: `@api.model`
  - Checks all card-door relations and updates them
- **`reload_door_rels(self, door_id)`** - decorators: `@api.model`
- **`check_relevance_slow(self, card_id, door_id, ts_id=None)`** - decorators: `@api.model`
  - Check if card has access to door. If it does, create relation or do nothing if it exists,
  - effects: `create`, `raise:ValidationError`
- **`check_relevance_fast(self, card_id, door_id, ts_id=None, alarm_right=False)`** - decorators: `@api.model`
  - Check if card is compatible with the door. If it is, create relation or do nothing if it exists,
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
  - On a module shared between companies the controller stores bare
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
| `name` | Char |  |  | - | Auto-generated system event description combining event type and location |
| `webstack_id` | Many2one → \`hr.rfid.webstack\` | Module |  | ✓ | The RFID webstack module (network interface) where this system event occurred. W |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller |  | ✓ | The RFID controller device that generated this system event. Controllers manage  |
| `door_id` | Many2one → \`hr.rfid.door\` | Door |  | ✓ | The specific door involved in this system event (e.g., forced open, overtime). M |
| `alarm_line_id` | Many2one → \`hr.rfid.ctrl.alarm\` | Alarm line |  | ✓ | The alarm input/output line that triggered this event. Used for security sensors |
| `siren` | Boolean |  |  | ✓ | Indicates whether the siren/alarm is currently active. True = Siren ON (alarm co |
| `timestamp` | Datetime | Timestamp | ✓ | ✓ | Exact date and time when this system event was detected. Critical for security a |
| `occurrences` | Integer | Occurrences |  | ✓ | Count of how many times this identical event has occurred. System groups repeate |
| `last_occurrence` | Datetime | Last occurrence |  | ✓ | Date and time of the most recent occurrence when the same event happened multipl |
| `event_action` | Selection | Event Type |  | ✓ | Type of system event: • Power On: Controller started • Door Overtime: Door held  |
| `error_description` | Char | Description |  | ✓ | Detailed explanation of the error or event condition. Provides context for troub |
| `card_number` | Char | Card number from this event |  | ✓ | RFID card number that triggered this system event. Only populated for card-relat |
| `input_js` | Char | Input JSON |  | ✓ | Raw JSON data received from the controller. Contains technical details for debug |
| `is_card_event` | Boolean |  |  | - | Indicates if this system event is related to an unknown/denied card, allowing ca |

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
- **`_demo_generate_system_events(self)`** - decorators: `@api.model`
  - Generate ~30 days of security/device system events for the demo.
  - effects: `create`, `log_info`
  - touches: `ir.config_parameter`

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
| `name` | Char |  |  | - | Auto-generated event description combining person name, action, and location |
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
| `action_string` | Char |  |  | - | Human-readable description of the event action for display purposes. |
| `more_json` | Char | More info about event in JSON |  | ✓ | Additional technical details about the event in JSON format. Used for debugging  |

#### Notable methods

- **`_compute_user_ev_name(self)`** - decorators: `@api.depends`
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
- **`_demo_generate_events(self)`** - decorators: `@api.model`
  - Generate ~30 days of realistic demo access events for the dashboards.
  - effects: `create`, `log_info`
  - touches: `hr.employee`, `ir.config_parameter`, `res.partner`

### `hr.rfid.notification` <a id='model-hr-rfid-notification'></a>
Python class `RFIDNotification` in `models/hr_rfid_notification.py:11`.  Model.  Description: *RFID Notification*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  |  | - | Computed display label combining the event type and notification channel (e.g. ' |
| `zone_id` | Many2one → \`hr.rfid.zone\` | Zone | ✓ | ✓ | The zone or area where this notification rule applies. When events occur in this |
| `company_id` | Many2one → \`res.company\` | Company | ✓ | - | Company that owns this notification. Automatically set based on the selected zon |
| `notification_type` | Selection |  |  | ✓ | How to send the notification: • System Chat: Send instant message through Odoo's |
| `user_event` | Selection | User Event |  | ✓ | Select a user-related event that will trigger this notification. Examples: Acces |
| `system_event` | Selection | System Event |  | ✓ | Select a system-related event that will trigger this notification. Examples: Con |
| `notify_followers` | Boolean | Notify Followers |  | ✓ | Send notifications to all users who follow this zone. This is useful for securit |
| `notify_partner_ids` | Many2many → \`res.partner\` |  |  | ✓ | Specific people to notify when this event occurs. You can add multiple recipient |

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
| `time_format` | Char |  |  | - | Time format used by this module based on its hardware version. Automatically det |
| `serial` | Char | Serial number |  | ✓ | Unique 6-digit serial number printed on the module hardware. This is automatical |
| `active` | Boolean | Active |  | ✓ | Enable this to allow the module to communicate with Odoo. When disabled, the mod |
| `version` | Char | Version |  | ✓ | Firmware version running on the module. This is automatically detected. Contact  |
| `hw_version` | Char | Hardware Version |  | ✓ | Hardware model/version of the module (e.g., 10.3, 50.1, 100.1). This determines  |
| `behind_nat` | Boolean | Behind NAT | ✓ | ✓ | Enable if the module is behind a firewall/router (most common). When enabled, th |
| `last_ip` | Char | Last IP |  | ✓ | The IP address the module last connected from. For modules behind NAT, this is t |
| `updated_at` | Datetime | Last Update |  | ✓ | Last time this module communicated with Odoo. If this is more than 10 minutes ag |
| `controllers` | One2many → \`hr.rfid.ctrl\` | Controllers |  | ✓ | List of access control devices connected to this module. Each controller manages |
| `http_link` | Char |  |  | - | Direct web interface link to the module. Only available when "Behind NAT" is dis |
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
  - :param error_description: (str) Description of the error that occurred.
  - effects: `sudo`
  - touches: `hr.rfid.event.system`
- **`sync_all_clocks(self)`** - decorators: `@api.model`
  - touches: `hr.rfid.webstack`
- **`direct_execute(self, cmd, command_id=None)`** - decorators: -
  - :param cmd: A dictionary that contains the command to be executed.
  - effects: `log_error`

### `hr.rfid.webstack.discovery.row` <a id='model-hr-rfid-webstack-discovery-row'></a>
Python class `HrRfidWebstackDiscoveryRow` in `models/hr_rfid_webstack_discovery.py:8`.  TransientModel (wizard).  Description: *Webstack discovery rows*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char |  |  | ✓ | Module name as reported in the UDP discovery beacon. |
| `last_ip` | Char |  |  | ✓ | IP address from which the module's discovery beacon was received. |
| `version` | Char |  |  | ✓ | Firmware/software version reported by the discovered module. |
| `hw_version` | Char |  |  | ✓ | Hardware version reported by the discovered module. |
| `serial` | Char |  |  | ✓ | Serial number reported by the discovered module — used as the unique key when ad |
| `behind_nat` | Boolean |  |  | ✓ | Discovery flag indicating whether the module sits behind a NAT and must initiate |
| `discovery_id` | Many2one → \`hr.rfid.webstack.discovery\` |  |  | ✓ | Discovery wizard run that found this module. |

### `hr.rfid.webstack.discovery` <a id='model-hr-rfid-webstack-discovery'></a>
Python class `HrRfidWebstackDiscovery` in `models/hr_rfid_webstack_discovery.py:41`.  TransientModel (wizard).  Description: *Webstack discovery*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `found_webstacks` | One2many → \`hr.rfid.webstack.discovery.row\` | Found modules |  | ✓ | Modules that were just found during the discovery process |
| `what_to_do` | Selection |  | ✓ | ✓ | What happens when you click Setup — Add as Inactive: register the module but do  |

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
| `behind_nat` | Boolean |  |  | ✓ | Check if the module sits behind a NAT and Odoo cannot reach its IP directly. In  |
| `local_ip_address` | Char |  |  | ✓ | Required when Behind NAT is off — the LAN IP at which Odoo can reach the module  |

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
| `source_webstack_id` | Many2one → \`hr.rfid.webstack\` |  |  | ✓ | Old webstack being replaced. Inactive modules are included to allow swap-in of p |
| `destination_webstack_id` | Many2one → \`hr.rfid.webstack\` |  |  | ✓ | New webstack that will take over the controllers. Inactive modules are included  |
| `source_controller_ids` | Many2many → \`hr.rfid.ctrl\` |  |  | ✓ | Controllers attached to the source webstack — these will be moved to the destina |
| `destination_controller_ids` | One2many → \`hr.rfid.ctrl\` |  |  | - | Controllers currently attached to the destination webstack — shown for reference |
| `replace_existing` | Boolean |  |  | ✓ | Replace existing controllers in destination module.  This will remove the existi |
| `destination_active_state` | Boolean |  |  | ✓ | The Active state of the destination module. |

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
| `webstack_id` | Many2one → \`hr.rfid.webstack\` |  | ✓ | ✓ |  |
| `ctrl_id_num` | Integer |  | ✓ | ✓ |  |
| `bos` | Integer |  | ✓ | ✓ |  |
| `ev_ts` | Char |  | ✓ | ✓ | Controller date+time string of the event. |
| `create_date` | Datetime |  |  | ✓ |  |

#### Notable methods

- **`_seen(self, webstack, ctrl_id_num, bos, ev_ts)`** - decorators: `@api.model`
  - True when this event key was already successfully processed.
  - effects: `sudo`
- **`_claim(self, webstack, ctrl_id_num, bos, ev_ts)`** - decorators: `@api.model`
  - Record a SUCCESSFULLY processed event key (claim only on success:
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
| `employee_count` | Char |  |  | - | Current number of employees in this zone. Automatically calculated based on entr |
| `contact_count` | Char |  |  | - | Current number of external contacts (visitors) in this zone. Automatically calcu |

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
| `card_input_type` | Selection |  |  | ✓ | Format readers in this company report card numbers in — Wiegand 34 (5d+5d): faci |

#### Notable methods

- **`create(self, values_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
  - touches: `hr.rfid.time.schedule`

### `res.partner` <a id='model-res-partner'></a>
Python class `ResPartner` in `models/res_partner.py:8`.  Model.  Inherits: `res.partner`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `company_id` | Many2one → \`res.company\` |  |  | ✓ |  |
| `hr_rfid_pin_code` | Char | RFID PIN Code |  | ✓ | 4-digit PIN code for secure door access. Use this along with an RFID card for hi |
| `hr_rfid_access_group_ids` | One2many → \`hr.rfid.access.group.contact.rel\` | Access Groups |  | ✓ | Door access permissions for this contact. Each group defines which doors they ca |
| `hr_rfid_card_ids` | One2many → \`hr.rfid.card\` | RFID Cards |  | ✓ | All RFID cards assigned to this contact. A person can have multiple cards (e.g., |
| `hr_rfid_event_ids` | One2many → \`hr.rfid.event.user\` | Access History |  | ✓ | Complete history of door access attempts by this contact. Includes successful en |
| `is_employee` | Boolean |  |  | - |  |
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
  - Require:
  - effects: `with_context`
  - touches: `hr.rfid.card`, `res.partner`
- **`add_access_group(self, access_group_id, activate_on=None, expire_on=None, visits=0)`** - decorators: -
  - Adding access group
- **`add_card_number(self, card_number, activate_on=None, expire_on=None, card_input_type=None)`** - decorators: -
- **`action_send_badge_email(self, template_xml_id=None)`** - decorators: -
  - Open a window to compose an email, with the template - 'card_badge'
- **`decode_mrz(self, mrz_string)`** - decorators: `@api.model`
  - This function receives a string containing the Machine Readable Zone (MRZ) data of a personal document,

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
- **`HW_TYPES`** *(collection)* = `[('1', 'iCON200'), ('2', 'iCON150'), ('3', 'iCON150'), ('4', 'iCON140'), ('5', 'iCON120'), ('6', 'iCON110'), ('7', 'iCON160'), ('8', 'iCON170'), ('9', 'Turnstile'), ('10', 'iCON180'), ('11', 'iCON115'), ('12', 'iCON50'), ('13', 'FireControl  # ...truncated`  - line 7
- **`DEFAULT_IO_TABLES`** *(collection)* = `[[6, 2, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,   # ...truncated`  - line 21
- **`READ_CARDS_BLOCK_SIZE`** *(scalar)* = `5`  - line 514

### `models/hr_rfid_command_ws.py`

- **`WS_CMD_REPUBLISH_TIMEOUT_S`** *(scalar)* = `15`  - line 25
- **`WS_CMD_MAX_RETRIES`** *(scalar)* = `5`  - line 26

### `models/hr_rfid_ctrl_th.py`

- **`DEMO_TH_SEED`** *(scalar)* = `20260826`  - line 9
- **`DEMO_TH_READINGS_FLAG`** *(scalar)* = `'hr_rfid.demo_th_readings_generated'`  - line 10

### `models/hr_rfid_ctrl_time_schedule.py`

- **`DEFAULT_TS_LINE`** *(expression)* = `'01\n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00\n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00 \n                   00 00  00 00  00 00  00 00  00 00  00 00  00 00  00 00\n         `  - line 5

### `models/hr_rfid_event_system.py`

- **`DEMO_SYSTEM_EVENT_SEED`** *(scalar)* = `20260717`  - line 13
- **`DEMO_SYSTEM_EVENTS_FLAG`** *(scalar)* = `'hr_rfid.demo_system_events_generated'`  - line 14
- **`SYS_EV_DEDUP_WINDOW_SECONDS`** *(scalar)* = `300`  - line 20

### `models/hr_rfid_event_user.py`

- **`DEMO_EVENT_SEED`** *(scalar)* = `20260716`  - line 9
- **`DEMO_EVENTS_FLAG`** *(scalar)* = `'hr_rfid.demo_events_generated'`  - line 10
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

### `tests/common.py`

- **`_TIMEOUT`** *(scalar)* = `500`  - line 15

### `tests/test_onboarding_panel_errors.py`

- **`BANNER_LOG`** *(scalar)* = `'odoo.addons.hr_rfid.models.onboarding_onboarding'`  - line 22

### `tests/test_one_door_two_schedules.py`

- **`DUPLICATE_DOOR_LOGGER`** *(scalar)* = `'odoo.addons.hr_rfid.models.hr_rfid_access_group'`  - line 29

### `tests/test_recalc_hook.py`

- **`COMMON_ANCESTOR`** *(scalar)* = `'odoo.addons.hr_rfid.models.hr_employee'`  - line 23

### `tests/test_sot_denied.py`

- **`_TIMEOUT`** *(scalar)* = `30`  - line 27

### `tests/test_unknown_device_payload.py`

- **`_TIMEOUT`** *(scalar)* = `30`  - line 18

### `tests/test_ws_dispatch.py`

- **`F0_ICON110`** *(scalar)* = `'0006000400000704000000030000030201050208000200010502060003000506'`  - line 25

### `tools/odoo_bus_device_sim.py`

- **`PROTO`** *(scalar)* = `1`  - line 37


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`WebRfidController.post_barcode(self, **post)`** (`@http.route`) - `controllers/main.py:53`
  - :param post: Dictionary of parameters sent in the POST request.
  - effects: `log_info`
- **`WebRfidController.post_event(self, **post)`** (`@http.route`) - `controllers/main.py:239`
  - This method handles the POST request to the '/hr/rfid/event' route. It processes the received data from the request and performs necessary actions based on the data.
  - effects: `log_error`, `log_info`, `sudo`
  - touches: `hr.rfid.event.system`, `hr.rfid.webstack`
- **`WebRfidController.vending_request_for_balance(self)`** - `controllers/main.py:366`
- **`get_default_io_table(hw_version, mode, as_string=True)`** - `controllers/polimex.py:517`
- **`bytes_to_num(data, start, digits)`** - `controllers/polimex.py:526`
- **`str_hex_to_array(str)`** - `controllers/polimex.py:536`
- **`str_dec_to_array(str)`** - `controllers/polimex.py:538`
- **`get_temperature(h, l, precision=0.5)`** - `controllers/polimex.py:541`
- **`get_reverse_temperature(temp)`** - `controllers/polimex.py:549`
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
- **`RFIDAppCase.setUpClass(cls)`** (`@classmethod`) - `tests/common.py:21`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `hr.department`, `hr.employee`, `hr.employee.category`, `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`, `hr.rfid.card`, `hr.rfid.webstack`, `res.company`, … (+1)
- **`RFIDAppCase.setUp(self)`** - `tests/common.py:135`
  - calls `super()`
- **`RFIDHttpCase.setUpClass(cls)`** (`@classmethod`) - `tests/common.py:612`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `hr.department`, `hr.employee`, `hr.employee.category`, `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`, `hr.rfid.card`, `hr.rfid.webstack`, `res.company`, … (+1)
- **`RFIDController.setUpClass(cls)`** (`@classmethod`) - `tests/controller.py:15`
  - calls `super()`
- **`RFIDController.setUp(self)`** - `tests/controller.py:42`
  - calls `super()`
- **`TestAddDoorsTimeSchedule.setUpClass(cls)`** (`@classmethod`) - `tests/test_access_group_add_doors.py:22`
  - calls `super()`
  - touches: `hr.rfid.time.schedule`, `res.company`
- **`TestAddDoorsTimeSchedule.test_schedule_never_belongs_to_another_company(self)`** - `tests/test_access_group_add_doors.py:40`
  - Избраното работно време е на фирмата на групата, или е общо.
  - touches: `res.company`
- **`TestAddDoorsTimeSchedule.test_missing_schedule_says_what_is_missing(self)`** - `tests/test_access_group_add_doors.py:65`
  - Липсващо работно време казва какво липсва.
- **`TestAddDoorsTimeSchedule.test_global_schedule_is_acceptable(self)`** - `tests/test_access_group_add_doors.py:84`
  - График без фирма важи за всички - не бива да се отхвърля.
  - touches: `res.company`
- **`TestAccessGroupBasic.test_create_access_group(self)`** - `tests/test_access_groups.py:20`
  - Test creating a basic access group.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupBasic.test_access_group_company_isolation(self)`** - `tests/test_access_groups.py:29`
  - Test access groups belong to specific company.
- **`TestAccessGroupBasic.test_access_group_delay_default(self)`** - `tests/test_access_groups.py:35`
  - Test delay_between_events defaults to 0.
- **`TestAccessGroupBasic.test_access_group_set_delay(self)`** - `tests/test_access_groups.py:40`
  - Test setting delay_between_events.
- **`TestAccessGroupBasic.test_access_group_unlink(self)`** - `tests/test_access_groups.py:46`
  - Test deleting an access group.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupBasic.test_delay_zero_means_disabled(self)`** - `tests/test_access_groups.py:58`
  - delay_between_events=0 must disable the anti-passback window.
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.event.user`, `hr.rfid.reader`
- **`TestAccessGroupInheritance.test_simple_inheritance(self)`** - `tests/test_access_groups.py:110`
  - Test basic parent→child inheritance.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupInheritance.test_circular_reference_raises(self)`** - `tests/test_access_groups.py:124`
  - Test circular inheritance raises ValidationError.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupInheritance.test_deep_circular_reference_raises(self)`** - `tests/test_access_groups.py:138`
  - Test deep circular inheritance (A→B→C→A) raises ValidationError.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupEmployeeRel.test_create_employee_rel(self)`** - `tests/test_access_groups.py:162`
  - Test creating employee ↔ AG relationship.
  - touches: `hr.rfid.access.group.employee.rel`
- **`TestAccessGroupEmployeeRel.test_employee_rel_future_activation(self)`** - `tests/test_access_groups.py:170`
  - Test employee rel with future activation date.
  - touches: `hr.rfid.access.group.employee.rel`
- **`TestAccessGroupEmployeeRel.test_employee_rel_expired(self)`** - `tests/test_access_groups.py:180`
  - Test employee rel with past expiration.
  - touches: `hr.rfid.access.group.employee.rel`
- **`TestAccessGroupEmployeeRel.test_employee_rel_visits_counting(self)`** - `tests/test_access_groups.py:191`
  - Test visits counting on employee AG relationship.
  - touches: `hr.rfid.access.group.employee.rel`
- **`TestAccessGroupEmployeeRel.test_employee_ag_must_be_in_department_allowed(self)`** - `tests/test_access_groups.py:203`
  - Test AG must be in department's allowed access groups.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`TestAccessGroupContactRel.test_create_contact_rel(self)`** - `tests/test_access_groups.py:221`
  - Test creating contact ↔ AG relationship.
- **`TestAccessGroupContactRel.test_contact_rel_with_different_ag(self)`** - `tests/test_access_groups.py:229`
  - Test creating contact rel with a different access group.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`TestAccessGroupContactRel.test_contact_rel_visits_counting(self)`** - `tests/test_access_groups.py:241`
  - Test visits counting on contact AG relationship.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`TestAlarmLineStateParse.test_non_hex_state_returns_unknown_without_raising(self)`** - `tests/test_alarm_line_state.py:29`
- **`TestAlarmLineStateParse.test_too_short_state_returns_unknown_without_raising(self)`** - `tests/test_alarm_line_state.py:33`
- **`TestAlarmLineStateParse.test_empty_state_returns_unknown(self)`** - `tests/test_alarm_line_state.py:37`
- **`TestAlarmLineStateParse.test_valid_state_still_parses(self)`** - `tests/test_alarm_line_state.py:42`
- **`TestZoneCreation.test_create_zone(self)`** - `tests/test_apb_zones.py:17`
  - Test creating a basic zone.
  - touches: `hr.rfid.zone`
- **`TestZoneCreation.test_create_apb_zone(self)`** - `tests/test_apb_zones.py:26`
  - Test creating anti-passback zone.
  - touches: `hr.rfid.zone`
- **`TestZoneCreation.test_zone_add_doors(self)`** - `tests/test_apb_zones.py:35`
  - Test adding doors to a zone.
  - touches: `hr.rfid.zone`
- **`TestZoneCreation.test_zone_department_filter(self)`** - `tests/test_apb_zones.py:46`
  - Test zone with department filter.
  - touches: `hr.rfid.zone`
- **`TestZoneCreation.test_zone_tag_filter(self)`** - `tests/test_apb_zones.py:55`
  - Test zone with employee tag filter.
  - touches: `hr.rfid.zone`
- **`TestAntiPassback.test_apb_zone_creation_generates_commands(self)`** - `tests/test_apb_zones.py:125`
  - Test that creating APB zone generates APB flag commands.
  - touches: `hr.rfid.zone`
- **`TestAntiPassback.test_apb_entry_event_updates_flags(self)`** - `tests/test_apb_zones.py:157`
  - Test APB entry event generates flag update commands.
  - touches: `hr.rfid.zone`
- **`TestAntiPassback.test_apb_zone_tracks_employees(self)`** - `tests/test_apb_zones.py:197`
  - Test APB zone tracks employees inside.
  - touches: `hr.rfid.zone`
- **`TestBarcodeNumber.test_w34_card_barcode_matches_hardware_hex(self)`** - `tests/test_barcode_qr.py:40`
  - Card in 5+5 dec format: barcode_number == hex of the same hex pair.
  - touches: `hr.rfid.card`
- **`TestBarcodeNumber.test_w34s_card_barcode_matches_hardware_hex(self)`** - `tests/test_barcode_qr.py:53`
  - Regression: w34s (10d single decimal) card encodes correctly.
  - touches: `hr.rfid.card`
- **`TestBarcodeNumber.test_barcode_number_recomputes_when_input_type_changes(self)`** - `tests/test_barcode_qr.py:77`
  - Customer-reported flow: changing card_input_type must invalidate QR.
- **`TestBarcodeNumber.test_helpers_are_inverse_on_internal_number(self)`** - `tests/test_barcode_qr.py:103`
  - w34_to_hex and hex_to_w34 are inverses on the canonical 5+5 form.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_create_card_w34_format(self)`** - `tests/test_card_lifecycle.py:21`
  - Test creating a card with Wiegand 34 bit format.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_create_card_w34s_format(self)`** - `tests/test_card_lifecycle.py:33`
  - Test creating a card with Wiegand 34 swapped format.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_card_name_from_reference(self)`** - `tests/test_card_lifecycle.py:44`
  - Test card name defaults to card_reference when set.
- **`TestCardCreation.test_card_name_from_number(self)`** - `tests/test_card_lifecycle.py:49`
  - Test card name falls back to number when no reference.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_duplicate_card_number_same_company_raises(self)`** - `tests/test_card_lifecycle.py:60`
  - Test that duplicate card number in same company raises error.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_card_number_padding(self)`** - `tests/test_card_lifecycle.py:70`
  - Test that short card numbers are padded with leading zeros.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_card_number_digits_only(self)`** - `tests/test_card_lifecycle.py:83`
  - Test that non-numeric card number raises ValidationError.
  - touches: `hr.rfid.card`
- **`TestCardCreation.test_card_both_employee_and_contact_raises(self)`** - `tests/test_card_lifecycle.py:93`
  - Test that setting both employee and contact raises error.
  - touches: `hr.rfid.card`
- **`TestCardActivation.test_card_ready_no_dates(self)`** - `tests/test_card_lifecycle.py:109`
  - Test card_ready() returns True when no activation dates set.
- **`TestCardActivation.test_card_ready_active_window(self)`** - `tests/test_card_lifecycle.py:114`
  - Test card_ready() within valid activation window.
- **`TestCardActivation.test_card_not_ready_future_activation(self)`** - `tests/test_card_lifecycle.py:123`
  - Test card_ready() returns False before activation date.
- **`TestCardActivation.test_card_not_ready_past_deactivation(self)`** - `tests/test_card_lifecycle.py:131`
  - Test card_ready() returns False after deactivation date.
- **`TestCardActivation.test_card_door_compatible(self)`** - `tests/test_card_lifecycle.py:140`
  - Test card door compatibility check based on card type.
- **`TestCardOwnerChange.test_card_employee_assignment(self)`** - `tests/test_card_lifecycle.py:151`
  - Test card is properly assigned to employee.
- **`TestCardOwnerChange.test_card_contact_assignment(self)`** - `tests/test_card_lifecycle.py:157`
  - Test card is properly assigned to contact.
- **`TestCardOwnerChange.test_card_pin_code_from_owner(self)`** - `tests/test_card_lifecycle.py:163`
  - Test card PIN code is computed from owner.
- **`TestCardOwnerChange.test_card_internal_number_w34(self)`** - `tests/test_card_lifecycle.py:170`
  - Test internal number calculation for w34 format.
- **`TestPlateNumberEntry.test_convertible_input_is_fixed_without_a_word(self)`** - `tests/test_card_lifecycle.py:194`
  - Кирилски двойници, малки букви и разделители се поправят тихо -
- **`TestPlateNumberEntry.test_junk_is_refused_out_loud_naming_the_character(self)`** - `tests/test_card_lifecycle.py:201`
  - Символ без съответствие на табела не се изтрива тихо - до днес
- **`TestPlateNumberEntry.test_the_round_trip_is_the_point(self)`** - `tests/test_card_lifecycle.py:211`
  - Въведеното с двойници се намира от събитието на камерата -
  - effects: `with_context`
  - touches: `hr.rfid.card`
- **`TestPlateNumberEntry.test_ordinary_cards_keep_their_own_rules(self)`** - `tests/test_card_lifecycle.py:223`
  - touches: `hr.rfid.card`
- **`TestCommandQueue.test_command_created_on_controller_init(self)`** - `tests/test_commands.py:17`
  - Test that F0 command is created when controller requests info.
  - touches: `hr.rfid.command`, `hr.rfid.ctrl`
- **`TestCommandQueue.test_command_status_lifecycle(self)`** - `tests/test_commands.py:31`
  - Test command goes from Wait → Process → Success.
  - touches: `hr.rfid.command`
- **`TestCommandQueue.test_card_add_generates_d1_command(self)`** - `tests/test_commands.py:43`
  - Test adding card to AG generates D1 command.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`TestCommandQueue.test_command_order(self)`** - `tests/test_commands.py:66`
  - Test commands are ordered by create_date desc.
  - touches: `hr.rfid.command`
- **`TestCommandQueue.test_no_commands_clean_state(self)`** - `tests/test_commands.py:76`
  - Test no pending commands after full controller init.
- **`TestCommandQueue.test_heartbeat_returns_pending_command(self)`** - `tests/test_commands.py:81`
  - Test heartbeat returns pending command when one exists.
  - touches: `hr.rfid.ctrl`
- **`TestCardConstraints.test_card_number_unique_per_type(self)`** - `tests/test_constraints.py:17`
  - Test card number must be unique per card type and company.
  - touches: `hr.rfid.card`
- **`TestCardConstraints.test_card_number_padding(self)`** - `tests/test_constraints.py:28`
  - Test that short card numbers are padded to 10 digits.
  - touches: `hr.rfid.card`
- **`TestCardConstraints.test_card_number_digits_only(self)`** - `tests/test_constraints.py:41`
  - Test card number must contain only digits.
  - touches: `hr.rfid.card`
- **`TestCardConstraints.test_card_owner_xor(self)`** - `tests/test_constraints.py:51`
  - Test card must have employee XOR contact, not both.
  - touches: `hr.rfid.card`
- **`TestCardConstraints.test_card_number_10_digits_valid(self)`** - `tests/test_constraints.py:62`
  - Test valid 10-digit card number.
  - touches: `hr.rfid.card`
- **`TestWorkcodeConstraints.test_workcode_exactly_4_chars(self)`** - `tests/test_constraints.py:78`
  - Test workcode must be exactly 4 characters.
  - touches: `hr.rfid.workcode`
- **`TestWorkcodeConstraints.test_workcode_digits_only(self)`** - `tests/test_constraints.py:87`
  - Test workcode must contain only digits.
  - touches: `hr.rfid.workcode`
- **`TestWorkcodeConstraints.test_workcode_valid(self)`** - `tests/test_constraints.py:96`
  - Test valid workcode creation.
  - touches: `hr.rfid.workcode`
- **`TestWorkcodeConstraints.test_workcode_unique(self)`** - `tests/test_constraints.py:105`
  - Test workcode uniqueness SQL constraint.
  - touches: `hr.rfid.workcode`
- **`TestEmployeeConstraints.test_employee_pin_exactly_4_digits(self)`** - `tests/test_constraints.py:124`
  - Test employee PIN code must be exactly 4 digits.
- **`TestEmployeeConstraints.test_employee_pin_digits_only(self)`** - `tests/test_constraints.py:129`
  - Test employee PIN code must contain only digits.
- **`TestEmployeeConstraints.test_employee_pin_valid(self)`** - `tests/test_constraints.py:134`
  - Test valid employee PIN code.
- **`TestEmployeeConstraints.test_employee_ag_must_be_in_department(self)`** - `tests/test_constraints.py:139`
  - Test employee AG must be in department's allowed list.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`TestPartnerConstraints.test_partner_pin_exactly_4_digits(self)`** - `tests/test_constraints.py:156`
  - Test partner PIN code must be exactly 4 digits.
- **`TestPartnerConstraints.test_partner_pin_digits_only(self)`** - `tests/test_constraints.py:161`
  - Test partner PIN code must contain only digits.
- **`TestPartnerConstraints.test_partner_pin_valid(self)`** - `tests/test_constraints.py:166`
  - Test valid partner PIN code.
- **`TestDepartmentConstraints.test_default_ag_must_be_in_allowed(self)`** - `tests/test_constraints.py:176`
  - Test default access group must be in allowed access groups list.
  - touches: `hr.rfid.access.group`
- **`TestDepartmentConstraints.test_default_ag_valid(self)`** - `tests/test_constraints.py:185`
  - Test valid default access group setting.
- **`TestDepartmentConstraints.test_add_allowed_ag(self)`** - `tests/test_constraints.py:192`
  - Test adding an access group to allowed list.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupConstraints.test_circular_inheritance_direct(self)`** - `tests/test_constraints.py:208`
  - Test direct circular inheritance raises error.
  - touches: `hr.rfid.access.group`
- **`TestAccessGroupConstraints.test_self_inheritance_raises(self)`** - `tests/test_constraints.py:222`
  - Test self-inheritance raises error.
  - touches: `hr.rfid.access.group`
- **`TestEnvironmentReadings.setUpClass(cls)`** (`@classmethod`) - `tests/test_environment_readings.py:20`
  - calls `super()`
  - touches: `hr.rfid.ctrl`, `hr.rfid.ctrl.th`, `hr.rfid.webstack`
- **`TestEnvironmentReadings.test_a_reported_reading_is_written_down_once(self)`** - `tests/test_environment_readings.py:41`
  - A reading the device reports lands in the history once, at ITS time.
  - touches: `hr.rfid.ctrl.th.log`
- **`TestEnvironmentReadings.test_a_polled_reading_is_still_written_down(self)`** - `tests/test_environment_readings.py:60`
  - The other way readings arrive must keep being recorded.
  - touches: `hr.rfid.ctrl.th.log`
- **`TestEnvironmentReadings.test_an_unchanged_reading_adds_no_row(self)`** - `tests/test_environment_readings.py:78`
  - Repeating the same value is not new information.
  - touches: `hr.rfid.ctrl.th.log`
- **`TestUserEventsICON50.test_reader_events_3_to_6(self)`** - `tests/test_events.py:21`
  - Test reader events 3 (granted), 4 (denied no access), 5 (denied ts), 6 (denied APB).
- **`TestUserEventsICON50.test_unknown_card_creates_system_event(self)`** - `tests/test_events.py:32`
  - Test unknown card generates system event instead of user event.
- **`TestUserEventsICON50.test_duress_events(self)`** - `tests/test_events.py:40`
  - Test duress events (1, 2) on all readers.
- **`TestUserEventsICON50.test_all_reader_events(self)`** - `tests/test_events.py:45`
  - Test complete reader event sequence on iCON50.
- **`TestUserEventsICON110.test_reader1_events(self)`** - `tests/test_events.py:56`
  - Test events on reader 1.
- **`TestUserEventsICON110.test_reader2_events(self)`** - `tests/test_events.py:61`
  - Test events on reader 2.
- **`TestUserEventsICON110.test_duress_both_readers(self)`** - `tests/test_events.py:66`
  - Test duress events on both readers.
- **`TestUserEventsICON130.test_all_four_readers(self)`** - `tests/test_events.py:77`
  - Test events on all 4 readers.
- **`TestSystemEvents.test_emergency_events(self)`** - `tests/test_events.py:88`
  - Test emergency events (event 19) on reader 1, 1+64 (off), and 0 (hardware).
- **`TestSystemEvents.test_exit_button_events(self)`** - `tests/test_events.py:93`
  - Test exit button events (event 21) on all doors.
- **`TestSystemEvents.test_door_overtime_events(self)`** - `tests/test_events.py:98`
  - Test door overtime events (event 25) with command generation.
- **`TestSystemEvents.test_force_door_open_events(self)`** - `tests/test_events.py:103`
  - Test force door open events (event 26).
- **`TestSystemEvents.test_power_on_event(self)`** - `tests/test_events.py:108`
  - Test power on event (event 30) triggers time sync command.
- **`TestSystemEvents.test_external_control_event(self)`** - `tests/test_events.py:113`
  - Test external control event (event 29).
- **`TestSystemEvents.test_all_system_events(self)`** - `tests/test_events.py:118`
  - Test full system events sequence on iCON50.
- **`TestEvent64CloudCard.test_ev64_icon50(self)`** - `tests/test_events.py:134`
  - Test external DB card request on iCON50.
- **`TestEvent64CloudCard.test_ev64_icon110(self)`** - `tests/test_events.py:140`
  - Test external DB card request on iCON110.
- **`TestEvent64CloudCard.test_ev64_icon115(self)`** - `tests/test_events.py:146`
  - Test external DB card request on iCON115.
- **`TestEvent64CloudCard.test_ev64_icon130(self)`** - `tests/test_events.py:152`
  - Test external DB card request on iCON130.
- **`TestEvent64CloudCard.test_ev64_icon180(self)`** - `tests/test_events.py:158`
  - Test external DB card request on iCON180.
- **`TestTurnstileSpecialEvents.test_turnstile_reader_events(self)`** - `tests/test_events.py:170`
  - Test events on turnstile readers 1 and 2.
- **`TestTurnstileSpecialEvents.test_turnstile_reader_65(self)`** - `tests/test_events.py:175`
  - Test special reader 65 events on turnstile.
- **`RFIDTests.setUp(self)`** - `tests/test_functional.py:18`
  - calls `super()`
- **`RFIDTests.test_functionality(self)`** - `tests/test_functional.py:21`
  - effects: `log_info`
- **`RFIDTests.setUp(self)`** - `tests/test_functional_old.py:20`
  - calls `super()`
- **`RFIDTests.test_functionality(self)`** - `tests/test_functional_old.py:23`
  - effects: `log_info`
- **`TestiCON50Init.test_icon50_init_sequence(self)`** - `tests/test_hardware_init.py:16`
  - Test full iCON50 initialization: F0 → D7 → DC → DC → F6 → F9 → FB → FF → B3.
- **`TestiCON50Init.test_icon50_hw_version(self)`** - `tests/test_hardware_init.py:22`
  - Test iCON50 hardware version is correctly parsed from F0 response.
- **`TestiCON50Init.test_icon50_single_reader(self)`** - `tests/test_hardware_init.py:28`
  - Test iCON50 has exactly 1 reader and 1 door.
- **`TestiCON50Init.test_icon50_io_table(self)`** - `tests/test_hardware_init.py:35`
  - Test iCON50 IO table is properly initialized.
- **`TestiCON50Init.test_icon50_serial_number(self)`** - `tests/test_hardware_init.py:43`
  - Test iCON50 serial number is parsed from F0.
- **`TestiCON50Init.test_icon50_mode(self)`** - `tests/test_hardware_init.py:49`
  - Test iCON50 mode is set after initialization.
- **`TestiCON50Init.test_icon50_max_cards(self)`** - `tests/test_hardware_init.py:55`
  - Test iCON50 max cards count is parsed.
- **`TestiCON110Init.test_icon110_init_sequence(self)`** - `tests/test_hardware_init.py:67`
  - Test full iCON110 initialization.
- **`TestiCON110Init.test_icon110_hw_version(self)`** - `tests/test_hardware_init.py:73`
  - Test iCON110 hardware version is correctly parsed.
- **`TestiCON110Init.test_icon110_two_readers(self)`** - `tests/test_hardware_init.py:79`
  - Test iCON110 has 2 readers and 2 doors in default mode.
- **`TestiCON110Init.test_icon110_io_table(self)`** - `tests/test_hardware_init.py:86`
  - Test iCON110 IO table matches default.
- **`TestiCON115Init.test_icon115_init_sequence(self)`** - `tests/test_hardware_init.py:98`
  - Test full iCON115 initialization including B0 alarm line protocol.
- **`TestiCON115Init.test_icon115_hw_version(self)`** - `tests/test_hardware_init.py:104`
  - Test iCON115 hardware version.
- **`TestiCON115Init.test_icon115_two_readers(self)`** - `tests/test_hardware_init.py:110`
  - Test iCON115 has 2 readers.
- **`TestiCON130Init.test_icon130_init_sequence(self)`** - `tests/test_hardware_init.py:122`
  - Test full iCON130 initialization.
- **`TestiCON130Init.test_icon130_hw_version(self)`** - `tests/test_hardware_init.py:128`
  - Test iCON130 hardware version.
- **`TestiCON130Init.test_icon130_four_readers(self)`** - `tests/test_hardware_init.py:134`
  - Test iCON130 has 4 readers and appropriate doors.
- **`TestiCON180Init.test_icon180_init_sequence(self)`** - `tests/test_hardware_init.py:147`
  - Test full iCON180 initialization.
- **`TestiCON180Init.test_icon180_four_readers(self)`** - `tests/test_hardware_init.py:153`
  - Test iCON180 has 4 readers.
- **`TestRelayControllerInit.test_relay_init_sequence(self)`** - `tests/test_hardware_init.py:165`
  - Test full Relay controller initialization.
- **`TestRelayControllerInit.test_relay_hw_version(self)`** - `tests/test_hardware_init.py:171`
  - Test Relay controller hardware version.
- **`TestRelayControllerInit.test_relay_is_relay(self)`** - `tests/test_hardware_init.py:177`
  - Test is_relay_ctrl() returns True for relay controller.
- **`TestRelayControllerInit.test_relay_readers(self)`** - `tests/test_hardware_init.py:182`
  - Test Relay controller has 2 readers.
- **`TestTurnstileInit.test_turnstile_init_sequence(self)`** - `tests/test_hardware_init.py:194`
  - Test full Turnstile initialization including FC anti-passback read.
- **`TestTurnstileInit.test_turnstile_hw_version(self)`** - `tests/test_hardware_init.py:199`
  - Test Turnstile hardware version.
- **`TestTurnstileInit.test_turnstile_readers(self)`** - `tests/test_hardware_init.py:205`
  - Test Turnstile has 2 readers.
- **`TestTemperatureInit.test_temperature_init_sequence(self)`** - `tests/test_hardware_init.py:217`
  - Test full Temperature controller init including sensor reading (F2/B1).
- **`TestTemperatureInit.test_temperature_sensors_created(self)`** - `tests/test_hardware_init.py:222`
  - Test that temperature sensors are created during init.
- **`TestTemperatureInit.test_temperature_cards_count(self)`** - `tests/test_hardware_init.py:230`
  - Test cards count (sensors) is parsed from F2 response.
- **`TestTemperatureInit.test_temperature_hw_version(self)`** - `tests/test_hardware_init.py:236`
  - Test Temperature controller hardware version.
- **`TestVendingInit.test_vending_init_sequence(self)`** - `tests/test_hardware_init.py:248`
  - Test full Vending controller initialization.
- **`TestVendingInit.test_vending_hw_version(self)`** - `tests/test_hardware_init.py:253`
  - Test Vending controller hardware version.
- **`TestInterlockingMode.test_decode_reads_interlocking_bit(self)`** - `tests/test_interlocking_mode.py:30`
  - Hardware reports bit 4 set in contr_mode -> Odoo stores it.
- **`TestInterlockingMode.test_encode_includes_interlocking_bit(self)`** - `tests/test_interlocking_mode.py:53`
  - Enabling interlocking -> the D5 mode byte carries bit 0x10.
- **`TestInterlockingMode.test_default_has_no_interlocking_bit(self)`** - `tests/test_interlocking_mode.py:61`
  - A plain mode write leaves bit 4 clear.
- **`TestInterlockingMode.test_mode_write_preserves_interlocking(self)`** - `tests/test_interlocking_mode.py:67`
  - THE BUGFIX: changing another mode flag must NOT zero bit 4.
  - touches: `hr.rfid.command`
- **`TestInterlockingMode.test_write_triggers_hardware_command(self)`** - `tests/test_interlocking_mode.py:89`
  - Setting interlocking_mode from Odoo pushes a D5 to the controller.
- **`TestInterlockingMode.test_field_gated_to_supporting_controllers(self)`** - `tests/test_interlocking_mode.py:98`
  - UI: interlocking_mode is hidden unless hw is iCON115/iCON130.
  - touches: `hr.rfid.ctrl`
- **`TestMultiCompanySharedRecords.setUpClass(cls)`** (`@classmethod`) - `tests/test_multi_company_rules.py:50`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `hr.rfid.ctrl`, `hr.rfid.webstack`, `res.company`
- **`TestMultiCompanySharedRecords.test_workcode_global_visible(self)`** - `tests/test_multi_company_rules.py:108`
  - A workcode with company_id=False is shared — must be visible.
  - touches: `hr.rfid.workcode`
- **`TestMultiCompanySharedRecords.test_workcode_other_company_hidden(self)`** - `tests/test_multi_company_rules.py:122`
  - Tolerating False must NOT leak other companies' workcodes.
  - touches: `hr.rfid.workcode`
- **`TestMultiCompanySharedRecords.test_door_without_webstack_visible(self)`** - `tests/test_multi_company_rules.py:138`
  - A door with no controller/webstack computes company_id=False —
  - touches: `hr.rfid.door`
- **`TestMultiCompanySharedRecords.test_door_other_company_hidden(self)`** - `tests/test_multi_company_rules.py:154`
  - A door wired to a company-B controller must stay hidden.
  - touches: `hr.rfid.door`
- **`TestMultiCompanySharedRecords.test_reader_without_controller_visible(self)`** - `tests/test_multi_company_rules.py:172`
  - A reader with controller_id=False has webstack_id=False (related
  - touches: `hr.rfid.reader`
- **`TestMultiCompanySharedRecords.test_reader_other_company_hidden(self)`** - `tests/test_multi_company_rules.py:192`
  - A reader on a company-B controller must stay hidden.
  - touches: `hr.rfid.reader`
- **`TestMultiCompanySharedRecords.test_event_system_controller_less_visible(self)`** - `tests/test_multi_company_rules.py:210`
  - PRODUCTION BUG CASE: a system event created without controller_id
  - touches: `hr.rfid.event.system`
- **`TestMultiCompanySharedRecords.test_event_system_other_company_hidden(self)`** - `tests/test_multi_company_rules.py:255`
  - A system event of a company-B controller must stay hidden.
  - touches: `hr.rfid.event.system`
- **`TestOrphanUserEventVisibility.setUpClass(cls)`** (`@classmethod`) - `tests/test_multi_company_rules.py:281`
  - super-split (super): pre=- · post=`sql`
  - effects: `sql`
  - touches: `hr.employee`, `hr.rfid.ctrl`, `hr.rfid.event.user`, `hr.rfid.reader`, `hr.rfid.webstack`, `res.company`
- **`TestOrphanUserEventVisibility.test_orphan_visible_to_door_owner(self)`** - `tests/test_multi_company_rules.py:431`
  - The security officer of the company operating a door must see
- **`TestOrphanUserEventVisibility.test_orphan_hidden_from_other_company(self)`** - `tests/test_multi_company_rules.py:445`
  - NEGATIVE: another company's officer must NOT see an unknown
- **`TestOrphanUserEventVisibility.test_orphan_on_shared_module_visible_to_sharing_company(self)`** - `tests/test_multi_company_rules.py:463`
  - Two companies sharing one entrance both guard it: the sharing
- **`TestOrphanUserEventVisibility.test_orphan_without_reader_stays_visible(self)`** - `tests/test_multi_company_rules.py:481`
  - A legacy imported event with NO reader resolves to no company;
- **`TestOrphanUserEventVisibility.test_orphan_broken_chain_stays_visible(self)`** - `tests/test_multi_company_rules.py:496`
  - A chain that stops before naming a company (reader with no
- **`TestOrphanUserEventVisibility.test_identified_event_ignores_hardware_chain(self)`** - `tests/test_multi_company_rules.py:520`
  - An event that DOES name a person is governed by that person's
- **`TestOrphanUserEventVisibility.test_foreign_identified_event_stays_hidden(self)`** - `tests/test_multi_company_rules.py:541`
  - Company A must not see another company's employee events at
- **`TestOnboardingPanel.setUp(self)`** - `tests/test_onboarding.py:15`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `onboarding.onboarding`, `onboarding.progress`, `onboarding.progress.step`
- **`TestOnboardingPanel.test_panel_html_renders_core_markup(self)`** - `tests/test_onboarding.py:35`
  - touches: `onboarding.onboarding`
- **`TestOnboardingPanel.test_panel_html_unknown_route_is_false(self)`** - `tests/test_onboarding.py:48`
  - touches: `onboarding.onboarding`
- **`TestOnboardingPanel.test_panel_html_hidden_after_close(self)`** - `tests/test_onboarding.py:54`
  - touches: `onboarding.onboarding`
- **`TestOnboardingPanelFirstLoadRace.setUp(self)`** - `tests/test_onboarding.py:84`
  - calls `super()`
  - touches: `onboarding.onboarding`
- **`TestOnboardingPanelFirstLoadRace.test_panel_still_shown_when_another_request_wins_the_first_load(self)`** - `tests/test_onboarding.py:104`
  - Losing the first-load race must not cost the user the banner.
  - touches: `onboarding.progress`, `onboarding.progress.step`
- **`TestOnboardingPanelFirstLoadRace.test_first_load_starts_tracking_exactly_once(self)`** - `tests/test_onboarding.py:132`
  - The winning request tracks progress, and a reload does not duplicate it.
- **`TestOnboardingPanelFailures.setUp(self)`** - `tests/test_onboarding_panel_errors.py:28`
  - calls `super()`
  - touches: `onboarding.onboarding`
- **`TestOnboardingPanelFailures.test_two_visitors_changing_the_same_thing_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:55`
- **`TestOnboardingPanelFailures.test_a_row_that_could_not_be_locked_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:58`
- **`TestOnboardingPanelFailures.test_a_deadlock_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:61`
- **`TestOnboardingPanelFailures.test_odoos_own_signal_to_run_the_request_again_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:64`
- **`TestOnboardingPanelFailures.test_a_column_the_database_does_not_know_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:69`
- **`TestOnboardingPanelFailures.test_a_value_the_database_will_not_accept_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:74`
- **`TestOnboardingPanelFailures.test_work_attempted_after_the_transaction_died_is_passed_on(self)`** - `tests/test_onboarding_panel_errors.py:79`
- **`TestOnboardingPanelFailures.test_anything_else_only_costs_the_banner(self)`** - `tests/test_onboarding_panel_errors.py:86`
- **`TestOnboardingPanelFailures.test_a_missing_template_only_costs_the_banner(self)`** - `tests/test_onboarding_panel_errors.py:95`
- **`TestOnboardingPanelFailures.test_the_hidden_banner_is_named_in_the_log(self)`** - `tests/test_onboarding_panel_errors.py:104`
  - Whoever reads the log can tell which help panel went missing.
- **`TestOneDoorTwoSchedules.setUp(self)`** - `tests/test_one_door_two_schedules.py:35`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`, `hr.rfid.time.schedule`, `ir.config_parameter`
- **`TestOneDoorTwoSchedules.test_a_contact_cannot_hold_one_door_on_two_schedules(self)`** - `tests/test_one_door_two_schedules.py:102`
- **`TestOneDoorTwoSchedules.test_a_contact_may_hold_one_door_twice_on_the_same_schedule(self)`** - `tests/test_one_door_two_schedules.py:122`
  - Съвпадащите графици остават разрешени - иначе това е забрана, не защита.
- **`TestOneDoorTwoSchedules.test_an_employee_cannot_hold_one_door_on_two_schedules(self)`** - `tests/test_one_door_two_schedules.py:141`
- **`TestOneDoorTwoSchedules.test_an_employee_may_hold_one_door_twice_on_the_same_schedule(self)`** - `tests/test_one_door_two_schedules.py:160`
- **`TestOverlappingAccessGroups.setUp(self)`** - `tests/test_overlapping_access_groups.py:27`
  - calls `super()`
  - touches: `hr.rfid.access.group.contact.rel`, `hr.rfid.access.group.door.rel`, `hr.rfid.card.door.rel`, `hr.rfid.command`, `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`, `hr.rfid.time.schedule`
- **`TestOverlappingAccessGroups.test_r1_new_rel_activate_creates_door_rel_and_add(self)`** - `tests/test_overlapping_access_groups.py:112`
  - R1: New rel that activates → 1 door rel + 1 ADD command, no REMOVE.
- **`TestOverlappingAccessGroups.test_r2_lone_rel_expires_removes_door_rel_and_emits_remove(self)`** - `tests/test_overlapping_access_groups.py:126`
  - R2: Single rel expires → -1 door rel + 1 REMOVE command.
- **`TestOverlappingAccessGroups.test_r3_card_not_ready_no_rel(self)`** - `tests/test_overlapping_access_groups.py:144`
  - R3: card.active=False → _activate creates no rel and no commands.
- **`TestOverlappingAccessGroups.test_r5_rel_unlink_removes_door_rel(self)`** - `tests/test_overlapping_access_groups.py:157`
  - R5: rel.unlink() → -1 door rel + 1 REMOVE command.
- **`TestOverlappingAccessGroups.test_r6_card_write_noop_idempotent(self)`** - `tests/test_overlapping_access_groups.py:170`
  - R6: card.write({deactivate_on: same}) → triggers update_card_rels but no duplicate work.
- **`TestOverlappingAccessGroups.test_e1_activate_before_deactivate_preserves_access(self)`** - `tests/test_overlapping_access_groups.py:190`
  - E1 (THE BUG): _activate called BEFORE _deactivate (lazy recompute order).
  - effects: `sql`
  - touches: `hr.rfid.access.group.contact.rel`
- **`TestOverlappingAccessGroups.test_e2_deactivate_before_activate_preserves_access(self)`** - `tests/test_overlapping_access_groups.py:244`
  - E2: _deactivate called BEFORE _activate (normal cron order).
  - effects: `sql`
  - touches: `hr.rfid.access.group.contact.rel`
- **`TestRecalcRefusalIsHeard.setUpClass(cls)`** (`@classmethod`) - `tests/test_recalc_hook.py:30`
  - super-split (super): pre=- · post=`with_context`
  - effects: `with_context`
  - touches: `hr.employee`
- **`TestRecalcRefusalIsHeard.test_nobody_objects_so_the_rebuild_goes_ahead(self)`** - `tests/test_recalc_hook.py:44`
  - With no add-on protecting anything, asking must simply be allowed.
- **`TestRecalcRefusalIsHeard.test_asking_about_nobody_is_allowed(self)`** - `tests/test_recalc_hook.py:52`
  - Selecting no one is not an error - there is nothing to protect.
  - touches: `hr.employee`
- **`TestRecalcRefusalIsHeard.test_an_objection_reaches_the_operator(self)`** - `tests/test_recalc_hook.py:58`
  - An add-on that refuses stops the rebuild, whoever loaded last.
  - effects: `raise:UserError`
- **`TestRecalcRefusalIsHeard.test_an_add_on_that_allows_does_not_silence_the_one_underneath(self)`** - `tests/test_recalc_hook.py:88`
  - Two add-ons, and only one of them objects: the refusal still wins.
  - effects: `raise:UserError`
- **`TestRecalcRefusalIsHeard.test_the_refusal_point_belongs_to_the_shared_module(self)`** - `tests/test_recalc_hook.py:117`
  - No add-on can take the place of the refusal point and drop it.
- **`TestMultiCompanyIsolation.test_webstack_company_isolation(self)`** - `tests/test_security.py:27`
  - Test webstacks are isolated by company.
- **`TestMultiCompanyIsolation.test_card_company_isolation(self)`** - `tests/test_security.py:34`
  - Test cards are isolated by company.
- **`TestMultiCompanyIsolation.test_access_group_company_isolation(self)`** - `tests/test_security.py:41`
  - Test access groups are isolated by company.
- **`TestMultiCompanyIsolation.test_create_webstack_company2(self)`** - `tests/test_security.py:48`
  - Test creating webstack in different company.
  - touches: `hr.rfid.webstack`
- **`TestGroupPermissions.setUpClass(cls)`** (`@classmethod`) - `tests/test_security.py:69`
  - calls `super()`
- **`TestGroupPermissions.test_viewer_can_read_cards(self)`** - `tests/test_security.py:96`
  - Test RFID viewer can read card records.
  - touches: `hr.rfid.card`
- **`TestGroupPermissions.test_viewer_can_read_events(self)`** - `tests/test_security.py:103`
  - Test RFID viewer can read user events.
  - touches: `hr.rfid.event.user`
- **`TestGroupPermissions.test_officer_can_create_card(self)`** - `tests/test_security.py:108`
  - Test RFID officer can create cards.
  - touches: `hr.rfid.card`
- **`TestGroupPermissions.test_manager_can_create_webstack(self)`** - `tests/test_security.py:118`
  - Test RFID manager can create webstacks.
  - touches: `hr.rfid.webstack`
- **`TestGroupPermissions.test_manager_can_create_access_group(self)`** - `tests/test_security.py:129`
  - Test RFID manager can create access groups.
  - touches: `hr.rfid.access.group`
- **`TestGroupPermissions.test_non_rfid_user_denied_webstack(self)`** - `tests/test_security.py:137`
  - Test user without RFID groups cannot access webstacks.
  - touches: `hr.rfid.webstack`
- **`TestGroupPermissions.test_non_rfid_user_denied_cards(self)`** - `tests/test_security.py:150`
  - Test user without RFID groups cannot access cards.
  - touches: `hr.rfid.card`
- **`TestSotDenied.setUpClass(cls)`** (`@classmethod`) - `tests/test_sot_denied.py:38`
  - calls `super()`
  - touches: `hr.rfid.card`, `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`, `res.partner`
- **`TestSotDenied.test_01_known_card_creates_user_event(self)`** - `tests/test_sot_denied.py:163`
  - Cardholder triggers SOT_DENIED → user event with action 5 or 15.
  - touches: `hr.rfid.event.user`
- **`TestSotDenied.test_02_unknown_card_falls_back_to_system_event(self)`** - `tests/test_sot_denied.py:187`
  - Unrecognised card number → system event (not a user event).
  - touches: `hr.rfid.event.user`
- **`TestSotDenied.test_03_no_card_falls_back_to_system_event(self)`** - `tests/test_sot_denied.py:202`
  - Hardware-only trigger (card=0000000000) → system event fallback.
- **`TestSystemEventDedup.setUpClass(cls)`** (`@classmethod`) - `tests/test_system_event_dedup.py:27`
  - calls `super()`
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.webstack`
- **`TestSystemEventDedup.test_same_door_repeat_groups(self)`** - `tests/test_system_event_dedup.py:65`
  - The regression itself: a repeating door event must GROUP (it never
- **`TestSystemEventDedup.test_different_door_new_row(self)`** - `tests/test_system_event_dedup.py:74`
- **`TestSystemEventDedup.test_after_quiet_gap_new_row(self)`** - `tests/test_system_event_dedup.py:79`
  - A repeat AFTER the window is a new incident - it must never vanish
- **`TestSystemEventDedup.test_sliding_window_keeps_grouping(self)`** - `tests/test_system_event_dedup.py:88`
  - Repeats each within the window of the PREVIOUS one keep grouping,
- **`TestSystemEventDedup.test_webstack_only_event_groups(self)`** - `tests/test_system_event_dedup.py:99`
  - Module-level events (no controller/door) keep grouping as before.
  - touches: `hr.rfid.event.system`
- **`TestSystemEventDedup.test_door_event_not_merged_into_doorless(self)`** - `tests/test_system_event_dedup.py:110`
  - An event WITH a door must not fold into a doorless row (and vice
  - touches: `hr.rfid.event.system`
- **`TestModulePresence.test_a_module_gone_dark_is_flagged(self)`** - `tests/test_telemetry_bus.py:54`
- **`TestModulePresence.test_one_missed_check_in_does_not_condemn_a_module(self)`** - `tests/test_telemetry_bus.py:62`
  - Only Odoo-provisioned modules are guaranteed to beat every minute;
- **`TestModulePresence.test_contact_restores_the_full_tolerance(self)`** - `tests/test_telemetry_bus.py:74`
  - A module that misses, reports, then misses again must get the whole
- **`TestModulePresence.test_a_module_already_dark_costs_nothing_more(self)`** - `tests/test_telemetry_bus.py:88`
  - A site switched off for a week must not cost a write every five
- **`TestModulePresence.test_a_module_still_reporting_keeps_its_green_light(self)`** - `tests/test_telemetry_bus.py:101`
  - The negative half: the scan must not call a healthy module dark.
  - touches: `hr.rfid.webstack`
- **`TestModulePresence.test_a_module_that_never_connected_is_not_nagged_about(self)`** - `tests/test_telemetry_bus.py:108`
  - An unfinished installation is not a communication failure - and the
  - touches: `hr.rfid.webstack`
- **`TestModulePresence.test_a_check_in_marks_a_dark_module_alive_again(self)`** - `tests/test_telemetry_bus.py:116`
  - Recovery is owned by the check-in itself, not by the scan: the scan
- **`TestModulePresence.test_the_scan_also_catches_a_module_that_recovered_unnoticed(self)`** - `tests/test_telemetry_bus.py:127`
  - Belt and braces: whatever route brought the timestamp forward, the
- **`TestModulePresence.test_a_real_time_module_is_not_called_dark(self)`** - `tests/test_telemetry_bus.py:137`
  - A module on the websocket never writes updated_at - judging it by
- **`TestModulePresence.test_the_daily_todo_ignores_a_healthy_real_time_module(self)`** - `tests/test_telemetry_bus.py:148`
  - Same trap, one day later: the 24-hour Todo must not land on a module
  - touches: `hr.rfid.webstack`
- **`TestModulePresence.test_the_daily_todo_still_fires_for_a_genuinely_silent_module(self)`** - `tests/test_telemetry_bus.py:158`
  - The transport-aware predicate must not swallow the real case.
  - touches: `hr.rfid.webstack`
- **`TestHeartbeatWritesOnlyWhatChanged.test_repeating_the_same_firmware_does_not_touch_the_record(self)`** - `tests/test_telemetry_bus.py:178`
- **`TestHeartbeatWritesOnlyWhatChanged.test_a_long_firmware_string_does_not_defeat_the_guard(self)`** - `tests/test_telemetry_bus.py:188`
  - The field truncates at its size; comparing the stored value against
- **`TestHeartbeatWritesOnlyWhatChanged.test_a_firmware_upgrade_is_recorded(self)`** - `tests/test_telemetry_bus.py:201`
- **`TestThePresenceScanIsInstalled.test_the_scan_runs_by_itself(self)`** - `tests/test_telemetry_bus.py:214`
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`TestTimeScheduleIntervals.test_time_schedule_exists(self)`** - `tests/test_time_schedules.py:17`
  - Test that default time schedules exist after module install.
  - touches: `hr.rfid.time.schedule`
- **`TestTimeScheduleIntervals.test_interval_begin_before_end(self)`** - `tests/test_time_schedules.py:22`
  - Test begin time must be before end time.
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestTimeScheduleIntervals.test_valid_interval_creation(self)`** - `tests/test_time_schedules.py:34`
  - Test creating a valid time schedule interval.
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestTimeScheduleIntervals.test_interval_float_to_str(self)`** - `tests/test_time_schedules.py:47`
  - Test float to string conversion for time values.
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestTimeScheduleIntervals.test_zero_end_allowed(self)`** - `tests/test_time_schedules.py:55`
  - Test that end=0 is allowed (means midnight/24h).
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestTimeScheduleIntervals.test_equal_begin_end_raises(self)`** - `tests/test_time_schedules.py:66`
  - Test that begin == end raises ValidationError (except when end=0).
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestTimeScheduleIntervals.test_display_name(self)`** - `tests/test_time_schedules.py:78`
  - Test display name computation for time schedule line.
  - touches: `hr.rfid.ctrl.ts.line`
- **`TestHrRfidTours.setUpClass(cls)`** (`@classmethod`) - `tests/test_tours.py:12`
  - calls `super()`
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.webstack`, `res.partner`, `res.users`
- **`TestHrRfidTours.test_add_webstack_tour(self)`** - `tests/test_tours.py:46`
  - Process 1: admin registers a brand-new RFID module.
  - touches: `hr.rfid.webstack`
- **`TestHrRfidTours.test_realtime_channel_tour(self)`** - `tests/test_tours.py:70`
  - Process: an operator enables the real-time channel on a module
- **`TestHrRfidTours.test_access_group_add_door_tour(self)`** - `tests/test_tours.py:91`
  - Process 2: admin creates an Access Group and attaches a door.
  - touches: `hr.rfid.access.group`
- **`TestHrRfidTours.test_onboarding_panel_tour(self)`** - `tests/test_tours.py:115`
  - Process 0: a new admin lands on User Events and is guided by the
  - effects: `sudo`
  - touches: `onboarding.onboarding`, `onboarding.progress`, `onboarding.progress.step`, `res.company`
- **`TestHrRfidTours.test_card_assign_tour(self)`** - `tests/test_tours.py:152`
  - Process 3: admin issues a card to a contact.
  - touches: `hr.rfid.card`
- **`TestAnUnknownDevicePayload.test_the_barcode_shape_is_answered_not_dropped_on_the_floor(self)`** - `tests/test_unknown_device_payload.py:29`
  - The exact payload that used to end in a server error.
- **`TestAnUnknownDevicePayload.test_any_other_unknown_shape_is_answered_too(self)`** - `tests/test_unknown_device_payload.py:44`
  - NEGATIVE: nothing about this is special to barcode devices.
- **`TestWebstackCRUD.test_webstack_create(self)`** - `tests/test_webstack.py:16`
  - Test creating a webstack.
- **`TestWebstackCRUD.test_webstack_serial(self)`** - `tests/test_webstack.py:21`
  - Test webstack serial number.
- **`TestWebstackCRUD.test_webstack_available(self)`** - `tests/test_webstack.py:26`
  - Test webstack availability status.
- **`TestWebstackCRUD.test_webstack_timezone(self)`** - `tests/test_webstack.py:31`
  - Test webstack timezone setting.
- **`TestWebstackCRUD.test_webstack_company(self)`** - `tests/test_webstack.py:36`
  - Test webstack company assignment.
- **`TestWebstackCRUD.test_webstack_key_generated(self)`** - `tests/test_webstack.py:42`
  - Test webstack key is generated on creation.
- **`TestWebstackCRUD.test_create_second_webstack(self)`** - `tests/test_webstack.py:47`
  - Test creating a second webstack with different serial.
  - touches: `hr.rfid.webstack`
- **`TestWebstackHeartbeat.test_heartbeat_empty_response(self)`** - `tests/test_webstack.py:66`
  - Test heartbeat with no pending commands returns empty.
- **`TestWebstackHeartbeat.test_heartbeat_increments(self)`** - `tests/test_webstack.py:72`
  - Test heartbeat counter increments properly.
- **`TestWebstackHeartbeat.test_heartbeat_provisions_detected_controller(self)`** - `tests/test_webstack.py:87`
  - A heartbeat reporting an unknown controller creates it and queues F0
  - touches: `hr.rfid.command`
- **`TestWebstackHeartbeat.test_heartbeat_provision_is_idempotent(self)`** - `tests/test_webstack.py:102`
  - Re-reporting the same controller creates no duplicate record or F0.
  - touches: `hr.rfid.command`
- **`TestWebstackHeartbeat.test_heartbeat_provision_mixed_only_creates_new(self)`** - `tests/test_webstack.py:116`
  - An array mixing a known and an unknown id creates only the unknown one.
  - touches: `hr.rfid.ctrl`
- **`TestWebstackHeartbeat.test_heartbeat_without_controllers_key_is_backward_compatible(self)`** - `tests/test_webstack.py:128`
  - Legacy firmware (no 'controllers' key) provisions nothing; FW still set.
  - touches: `hr.rfid.ctrl`
- **`TestWebstackHeartbeat.test_heartbeat_provision_skips_zero_id(self)`** - `tests/test_webstack.py:140`
  - Id 0 (broadcast/no-controller) is skipped; a real id alongside is created.
- **`TestWebstackHeartbeat.test_heartbeat_malformed_controllers_is_safe(self)`** - `tests/test_webstack.py:147`
  - A malformed 'controllers' value must never break the heartbeat (no 500).
  - touches: `hr.rfid.ctrl`
- **`TestWebstackHeartbeat.test_heartbeat_provision_caps_oversized_list(self)`** - `tests/test_webstack.py:158`
  - An oversized 'controllers' array (beyond the hardware bus max) is
  - touches: `hr.rfid.ctrl`
- **`TestWebstackHeartbeat.test_heartbeat_provision_failure_keeps_command_delivery(self)`** - `tests/test_webstack.py:169`
  - A pre-provision failure is best-effort: the heartbeat still delivers
  - touches: `hr.rfid.ctrl`
- **`SharedModuleCase.setUpClass(cls)`** (`@classmethod`) - `tests/test_webstack_sharing.py:31`
  - calls `super()`
  - touches: `hr.department`, `hr.employee`, `hr.rfid.access.group`, `hr.rfid.card`, `res.company`
- **`TestSharedModuleVisibility.test_sharing_company_sees_hardware_control_company_does_not(self)`** - `tests/test_webstack_sharing.py:143`
  - B (shared with) can see the controllers, doors and readers of the
- **`TestSharedModuleVisibility.test_module_record_itself_is_never_shared(self)`** - `tests/test_webstack_sharing.py:160`
  - The module record carries the device credentials that authenticate
  - effects: `sudo`
  - touches: `hr.rfid.command`
- **`TestSharedModuleVisibility.test_per_company_data_stays_isolated_while_sharing(self)`** - `tests/test_webstack_sharing.py:179`
  - Sharing the hardware shares NOTHING else: A's cards, access groups,
  - effects: `sudo`
  - touches: `hr.rfid.time.schedule`
- **`TestSharedModuleVisibility.test_grant_relations_scoped_not_enumerable(self)`** - `tests/test_webstack_sharing.py:196`
  - The card-door / group-door relations follow the same boundaries:
- **`TestSharedModuleVisibility.test_grant_by_sharing_company_reaches_the_hardware(self)`** - `tests/test_webstack_sharing.py:217`
  - B's grant must still be delivered to the owner's controller - the
  - effects: `sudo`
  - touches: `hr.rfid.command`
- **`TestSharedModuleGuards.test_duplicate_card_number_blocked_on_shared_module(self)`** - `tests/test_webstack_sharing.py:235`
  - Two people from the two companies cannot carry the same card
  - touches: `hr.rfid.card`
- **`TestSharedModuleGuards.test_duplicate_by_number_change_blocked(self)`** - `tests/test_webstack_sharing.py:252`
  - Renumbering an already-granted card into a colliding number is
  - effects: `sudo`
- **`TestSharedModuleGuards.test_duplicate_allowed_when_not_sharing(self)`** - `tests/test_webstack_sharing.py:262`
  - Regression: without sharing, the same number may exist and be
  - effects: `sudo`
  - touches: `hr.rfid.access.group.door.rel`, `hr.rfid.card`, `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`, `hr.rfid.webstack`
- **`TestSharedModuleGuards.test_foreign_grant_only_with_unrestricted_schedule(self)`** - `tests/test_webstack_sharing.py:292`
  - B may only grant 24/7 (schedule 0) on the shared module - the
  - effects: `sudo`
  - touches: `hr.rfid.access.group.door.rel`, `hr.rfid.time.schedule`
- **`TestSharedModuleGuards.test_unshared_door_not_grantable_by_other_company(self)`** - `tests/test_webstack_sharing.py:310`
  - A door whose module is NOT shared with B cannot enter B's access
  - effects: `sudo`
  - touches: `hr.rfid.access.group.door.rel`
- **`TestSharedModuleGuards.test_ownership_stays_with_owner(self)`** - `tests/test_webstack_sharing.py:323`
  - B operates the shared module but cannot take it over: changing the
- **`TestSharedModuleGuards.test_sharing_company_cannot_take_over_or_break_the_hardware(self)`** - `tests/test_webstack_sharing.py:341`
  - The sharing company may READ the owner's hardware, never change it.
  - touches: `hr.rfid.command`, `hr.rfid.webstack`
- **`TestSharedModuleGuards.test_sharing_company_cannot_remove_the_owners_grants(self)`** - `tests/test_webstack_sharing.py:367`
  - B manages the grants of its OWN people; the owner's grants on the
  - effects: `sudo`
  - touches: `hr.rfid.access.group.door.rel`
- **`TestSharedModuleGuards.test_unshare_revokes_access(self)`** - `tests/test_webstack_sharing.py:383`
  - Removing B from the sharing list drops B's grants, queues the
  - effects: `sudo`
  - touches: `hr.rfid.access.group.door.rel`, `hr.rfid.card.door.rel`, `hr.rfid.command`, `hr.rfid.ctrl`
- **`TestSharedModuleGuards.test_replace_wizard_carries_sharing(self)`** - `tests/test_webstack_sharing.py:408`
  - Swapping a broken module for a new one keeps serving both
  - touches: `hr.rfid.webstack`, `hr.rfid.webstack.replace.wiz`
- **`TestSharedModuleWorkcodes.test_workcode_of_badging_persons_company_is_recognised(self)`** - `tests/test_webstack_sharing.py:433`
  - touches: `hr.rfid.workcode`
- **`TestSharedModuleE2E.test_shared_module_full_lifecycle(self)`** - `tests/test_webstack_sharing.py:470`
  - effects: `sudo`
  - touches: `hr.employee`, `hr.rfid.card`, `hr.rfid.card.door.rel`, `hr.rfid.ctrl`, `hr.rfid.event.system`, `hr.rfid.event.user`
- **`TestAccessGroupWizard.test_wizard_add_doors(self)`** - `tests/test_wizards.py:19`
  - Test adding doors to AG via wizard.
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`
- **`TestAccessGroupWizard.test_wizard_del_doors(self)`** - `tests/test_wizards.py:31`
  - Test removing doors from AG via wizard.
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`
- **`TestZoneDoorsWizard.test_zone_wizard_add_doors(self)`** - `tests/test_wizards.py:55`
  - Test adding doors to zone via wizard.
  - effects: `with_context`
  - touches: `hr.rfid.zone`, `hr.rfid.zone.doors.wiz`
- **`TestZoneDoorsWizard.test_zone_wizard_remove_doors(self)`** - `tests/test_wizards.py:71`
  - Test removing doors from zone via wizard.
  - effects: `with_context`
  - touches: `hr.rfid.zone`, `hr.rfid.zone.doors.wiz`
- **`TestDepartmentAccessGroupWizard.test_dept_acc_gr_wizard(self)`** - `tests/test_wizards.py:97`
  - Test setting allowed access groups on department via wizard.
  - effects: `with_context`
  - touches: `hr.department.acc.grs`, `hr.rfid.access.group`
- **`TestDepartmentAccessGroupWizard.test_dept_def_acc_gr_wizard(self)`** - `tests/test_wizards.py:112`
  - Test setting default access group via wizard.
  - effects: `with_context`
  - touches: `hr.department.def.acc.gr`
- **`TestDepartmentAccessGroupWizard.test_dept_change_and_apply_def_acc_gr(self)`** - `tests/test_wizards.py:125`
  - Test changing default AG and applying to all employees.
  - effects: `with_context`
  - touches: `hr.department.def.acc.gr`
- **`TestDepartmentAccessGroupWizard.test_dept_mass_add_acc_grs(self)`** - `tests/test_wizards.py:137`
  - Test mass adding access groups to department employees.
  - effects: `with_context`
  - touches: `hr.department.mass.wiz`
- **`TestDepartmentAccessGroupWizard.test_dept_mass_remove_acc_grs(self)`** - `tests/test_wizards.py:146`
  - Test mass removing access groups from department employees.
  - effects: `with_context`
  - touches: `hr.department.mass.wiz`
- **`TestCardAddRemoveEmployee.test_add_remove_card_employee(self)`** - `tests/test_wizards.py:170`
  - Test full employee card add/remove cycle.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`TestCardAddRemovePartner.test_add_remove_card_partner(self)`** - `tests/test_wizards.py:218`
  - Test full partner card add/remove cycle with card validity interaction.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`TestWsCommands.setUp(self)`** - `tests/test_ws_commands.py:26`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`TestWsCommands.test_event_batch_does_not_burn_command_retries(self)`** - `tests/test_ws_commands.py:72`
  - F1: a multi-event batch must run the queued-command piggyback for
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsCommands.test_rsp_wrong_cid_falls_back_to_code_match(self)`** - `tests/test_ws_commands.py:92`
  - F2: a cid that points at a command whose code does not match the
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsCommands.test_poison_command_does_not_abort_sync_on_connect(self)`** - `tests/test_ws_commands.py:116`
  - F4/F12: the OLDEST queued command raising in send_command must not
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsCommands.test_republish_cron_climbs_to_giveup_on_poison(self)`** - `tests/test_ws_commands.py:145`
  - F5: a command that keeps failing to publish still climbs its retry
  - effects: `sql`
  - touches: `hr.rfid.command`
- **`TestWsCommands.test_create_publish_failure_does_not_break_creation(self)`** - `tests/test_ws_commands.py:172`
  - F6: a publish failure at create-time must never break the business
- **`TestWsCommands.test_create_publishes_when_online(self)`** - `tests/test_ws_commands.py:187`
  - touches: `bus.bus`
- **`TestWsCommands.test_create_offline_stays_wait_for_http(self)`** - `tests/test_ws_commands.py:203`
  - touches: `bus.bus`
- **`TestWsCommands.test_connect_sync_republishes_pending(self)`** - `tests/test_ws_commands.py:218`
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsCommands.test_republish_cron_retries_then_fails(self)`** - `tests/test_ws_commands.py:234`
  - effects: `sql`
  - touches: `bus.bus`, `hr.rfid.command`
- **`TestWsCommands.test_rsp_cid_targets_exact_command(self)`** - `tests/test_ws_commands.py:268`
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsDispatch.setUp(self)`** - `tests/test_ws_dispatch.py:34`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `ir.config_parameter`
- **`TestWsDispatch.test_bad_key_is_refused_with_nack(self)`** - `tests/test_ws_dispatch.py:75`
  - touches: `bus.bus`
- **`TestWsDispatch.test_keyless_device_presenting_0000_is_refused(self)`** - `tests/test_ws_dispatch.py:89`
  - A keyless (never-provisioned / re-keyed) module presenting the insecure
  - touches: `bus.bus`
- **`TestWsDispatch.test_heal_0000_to_real_key_adopts_onto_same_endpoint(self)`** - `tests/test_ws_dispatch.py:100`
  - G1 heal: a module stored with the insecure '0000' presents a new
  - effects: `sudo`
  - touches: `bus.bus`, `ir.config_parameter`
- **`TestWsDispatch.test_real_key_is_never_overridden_by_a_different_key(self)`** - `tests/test_ws_dispatch.py:130`
  - A device with a REAL (non-0000) key is NOT healable: a different key,
  - effects: `sudo`
  - touches: `bus.bus`, `ir.config_parameter`
- **`TestWsDispatch.test_auth_flood_raises_one_system_event(self)`** - `tests/test_ws_dispatch.py:153`
  - touches: `hr.rfid.event.system`
- **`TestWsDispatch.test_disabled_module_is_refused_with_nack(self)`** - `tests/test_ws_dispatch.py:163`
  - touches: `bus.bus`
- **`TestWsDispatch.test_unknown_serial_is_safe(self)`** - `tests/test_ws_dispatch.py:175`
  - touches: `hr.rfid.webstack`
- **`TestWsDispatch.test_hello_acks_and_updates(self)`** - `tests/test_ws_dispatch.py:185`
  - touches: `bus.bus`
- **`TestWsDispatch.test_hello_proto_mismatch(self)`** - `tests/test_ws_dispatch.py:204`
  - touches: `bus.bus`
- **`TestWsDispatch.test_hb_provisions_controllers(self)`** - `tests/test_ws_dispatch.py:214`
- **`TestWsDispatch.test_ev_from_new_controller_not_consumed(self)`** - `tests/test_ws_dispatch.py:224`
  - An event from an unknown controller mirrors the HTTP 400 path:
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_ev_batch_processes_and_acks(self)`** - `tests/test_ws_dispatch.py:247`
  - On a known controller the same core as HTTP processes the event
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_ev_resend_is_deduplicated(self)`** - `tests/test_ws_dispatch.py:264`
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_ev_malformed_entry_is_consumed_not_looped(self)`** - `tests/test_ws_dispatch.py:281`
  - A non-dict / unparseable entry is FINAL - consume it (ok:true +
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_ev_out_of_range_controller_id_dropped(self)`** - `tests/test_ws_dispatch.py:299`
  - An event whose controller id is outside the RS-485 range (1..254)
  - touches: `bus.bus`
- **`TestWsDispatch.test_ev_bad_time_is_consumed(self)`** - `tests/test_ws_dispatch.py:317`
  - A bad controller clock is consumed (ok:true) like the HTTP path's
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_malformed_rsp_does_not_escape_to_transport(self)`** - `tests/test_ws_dispatch.py:335`
  - A malformed rsp (missing 'c') must be caught in-dispatch: the HTTP
  - touches: `bus.bus`, `hr.rfid.event.system`
- **`TestWsDispatch.test_auth_fail_writes_are_bounded(self)`** - `tests/test_ws_dispatch.py:356`
  - Bad-token frames increment the counter only up to the threshold
- **`TestWsDispatch.test_poisoned_fw_does_not_break_parsing(self)`** - `tests/test_ws_dispatch.py:366`
  - A non-numeric fw from the device (hello) must not poison the
  - touches: `bus.bus`
- **`TestWsDispatch.test_f0_rsp_and_inline_command_on_event(self)`** - `tests/test_ws_dispatch.py:390`
  - Full round-trip: hello -> F0 read queued -> F0 response over the WS
  - effects: `sudo`, `with_context`
  - touches: `bus.bus`, `hr.rfid.command`
- **`TestWsDispatch.test_dedup_gc(self)`** - `tests/test_ws_dispatch.py:448`
  - effects: `sudo`
  - touches: `hr.rfid.ws.dedup`
- **`TestWsLayer.test_enable_does_not_mint_a_secret(self)`** - `tests/test_ws_layer.py:37`
- **`TestWsLayer.test_disable_keeps_key(self)`** - `tests/test_ws_layer.py:49`
- **`TestWsLayer.test_rekey_clears_key_for_tofu(self)`** - `tests/test_ws_layer.py:57`
  - action_ws_rekey arms TOFU: it clears the stored key so the next
- **`TestWsLayer.test_channel_format(self)`** - `tests/test_ws_layer.py:71`
- **`TestWsLayer.test_send_requires_enabled_and_key(self)`** - `tests/test_ws_layer.py:77`
  - touches: `bus.bus`
- **`TestWsLayer.test_send_publishes_on_device_channel(self)`** - `tests/test_ws_layer.py:83`
  - touches: `bus.bus`
- **`TestWsLayer.test_send_requires_a_key(self)`** - `tests/test_ws_layer.py:91`
  - With the key cleared (TOFU armed) there is no channel to publish
  - touches: `bus.bus`
- **`TestWsLayer.test_ws_online_compute_and_search(self)`** - `tests/test_ws_layer.py:105`
  - touches: `hr.rfid.webstack`
- **`TestWsLayer.test_provision_payload_only_when_pending(self)`** - `tests/test_ws_layer.py:126`
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
  - The SPEC §12 walk: provisioning, hello, new-controller event flow,
- **`main()`** - `tools/odoo_bus_device_sim.py:291`

### Private helpers

- **`_ws_db_update_dict()`** - `controllers/main.py:20`
- **`_get_remote_ip_address()`** - `controllers/main.py:27`
- **`WebRfidController._parse_event(self, post_data, webstack)`** - `controllers/main.py:38`
  - Thin delegate - the parsing core lives on ``hr.rfid.webstack``
- **`WebRfidController._respond_to_ev_64(self, open_door, controller, reader, card, post_data)`** - `controllers/main.py:45`
  - Thin delegate - core on hr.rfid.webstack (see _hw_respond_to_ev_64).
- **`WebRfidController._decode_post(self, post)`** - `controllers/main.py:94`
- **`WebRfidController._make_response(self, result)`** - `controllers/main.py:106`
  - Wrap the result for the wire the module speaks. THREE shapes:
- **`WebRfidController._authenticate_webstack(self, post_data)`** - `controllers/main.py:150`
  - Find and authenticate the webstack behind a hardware POST.
  - effects: `log_info`, `message_post`, `sudo`, `with_context`
  - touches: `hr.rfid.webstack`, `ir.config_parameter`, `res.company`, `res.users`
- **`WebRfidController._parse_raw_data(self, post_data)`** - `controllers/main.py:341`
  - Answer a device that speaks a shape this endpoint does not handle.
  - effects: `log_info`
- **`BaseImporter.__init__(self, old_url, old_db, old_username, old_password, new_url, new_db, new_username, new_password, source_version, batch_size=100)`** - `manual_import.py:8`
- **`_demo_xml_ids(module)`** - `migration_utils.py:37`
  - Every xml id declared by the module's own demo files.
  - effects: `log_warn`
- **`_check_overlap(ranges)`** - `models/hr_rfid_access_group.py:562`
- **`_tz_get(self)`** - `models/hr_rfid_webstack.py:64`
- **`RFIDAppCase._get_id_num(self)`** - `tests/common.py:156`
- **`RFIDAppCase._get_heartbeat(self)`** - `tests/common.py:160`
- **`RFIDAppCase._check_no_commands(self, module_id=None)`** - `tests/common.py:164`
- **`RFIDAppCase._make_F0(self, hw_version=None, serial_number=None, sw_version=None, mode=None, inputs=None, outputs=None, readers=None, time_schedules=None, io_table_lines=None, alarm_lines=None, max_cards_count=None, max_events_count=None, ctrl=None)`** - `tests/common.py:171`
- **`RFIDAppCase._get_F0_response(self, ctrl)`** - `tests/common.py:203`
- **`RFIDAppCase._time_10_3(self, delta_in_seconds)`** - `tests/common.py:223`
- **`RFIDAppCase._assertResponse(self, response)`** - `tests/common.py:231`
- **`RFIDAppCase._hearbeat(self, webstack_id, controllers=None)`** - `tests/common.py:239`
- **`RFIDAppCase._count_system_events(self, company_id=None)`** - `tests/common.py:253`
  - effects: `with_company`
  - touches: `hr.rfid.event.system`
- **`RFIDAppCase._count_user_events(self, company_id=None)`** - `tests/common.py:258`
  - touches: `hr.rfid.event.user`
- **`RFIDAppCase._user_events(self, company_id, count=True, last=False)`** - `tests/common.py:263`
  - effects: `with_company`
  - touches: `hr.rfid.event.user`
- **`RFIDAppCase._send_cmd(self, cmd, system_event=False, company_id=None)`** - `tests/common.py:273`
- **`RFIDAppCase._send_cmd_response(self, request_cmd, data='', module=234567, key='0000')`** - `tests/common.py:291`
- **`RFIDAppCase._count_ctrl_waiting_cmd(self, ctrl)`** - `tests/common.py:310`
  - touches: `hr.rfid.command`
- **`RFIDAppCase._check_no_cmd(self, ctrl)`** - `tests/common.py:313`
  - touches: `hr.rfid.command`
- **`RFIDAppCase._check_cmd_add_card(self, ctrl, count=None, rights=None, mask=None)`** - `tests/common.py:318`
  - touches: `hr.rfid.command`
- **`RFIDAppCase._check_cmd_delete_card(self, ctrl)`** - `tests/common.py:334`
  - touches: `hr.rfid.command`
- **`RFIDAppCase._check_cmd_add_card_and_remove(self, ctrl, count=None, rights=None, mask=None)`** - `tests/common.py:345`
- **`RFIDAppCase._check_cmd_delete_card_and_remove(self, ctrl)`** - `tests/common.py:348`
- **`RFIDAppCase._clear_ctrl_cmd(self, ctrl)`** - `tests/common.py:351`
  - touches: `hr.rfid.command`
- **`RFIDAppCase._process_io_table(self, response, ctrl, module=234567, key='0000')`** - `tests/common.py:356`
- **`RFIDAppCase._check_added_controller(self, ctrl)`** - `tests/common.py:381`
- **`RFIDAppCase._make_event_on_all_readers(self, ctrl, card=None, pin=None, date=None, day=None, time=None, event_code=None, system_event=False, relay_num=1)`** - `tests/common.py:393`
- **`RFIDAppCase._make_event(self, ctrl, card=None, pin=None, reader=None, date=None, day=None, time=None, event_code=None, system_event=False, relay_num=1)`** - `tests/common.py:405`
- **`RFIDAppCase._test_R_event(self, ctrl, reader=1)`** - `tests/common.py:453`
- **`RFIDAppCase._test_R1R2(self, ctrl)`** - `tests/common.py:473`
- **`RFIDAppCase._test_R1R2R3R4(self, ctrl)`** - `tests/common.py:477`
- **`RFIDAppCase._test_Duress(self, ctrl)`** - `tests/common.py:483`
- **`RFIDAppCase._test_inputs(self, ctrl)`** - `tests/common.py:488`
- **`RFIDAppCase._test_Emergency(self, ctrl)`** - `tests/common.py:496`
- **`RFIDAppCase._test_Exit_buttons(self, ctrl)`** - `tests/common.py:502`
- **`RFIDAppCase._test_External_control(self, ctrl)`** - `tests/common.py:504`
- **`RFIDAppCase._test_Door_Overtime(self, ctrl)`** - `tests/common.py:507`
- **`RFIDAppCase._test_Force_Door_Open(self, ctrl)`** - `tests/common.py:512`
- **`RFIDAppCase._test_Power_On(self, ctrl)`** - `tests/common.py:515`
- **`RFIDAppCase._change_mode(self, ctrl, mode)`** - `tests/common.py:520`
- **`RFIDAppCase._ev64(self, ctrl)`** - `tests/common.py:536`
  - effects: `log_info`
- **`RFIDController._add_Vending(self, module=234567, key='0000', id=None)`** - `tests/controller.py:57`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_Turnstile(self, module=234567, key='0000', id=None)`** - `tests/controller.py:86`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_iCon180(self, module=234567, key='0000', id=5)`** - `tests/controller.py:118`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_iCon130(self, module=234567, key='0000', id=None)`** - `tests/controller.py:147`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_RelayController(self, module=234567, key='0000', id=None)`** - `tests/controller.py:177`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_iCon115(self, module=234567, key='0000', id=None)`** - `tests/controller.py:207`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_iCon110(self, module=234567, key='0000', id=None)`** - `tests/controller.py:239`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_iCon50(self, module=234567, key='0000', id=None)`** - `tests/controller.py:269`
  - touches: `hr.rfid.ctrl`
- **`RFIDController._add_Temperature(self, module=234567, key='0000', id=None)`** - `tests/controller.py:298`
  - touches: `hr.rfid.ctrl`
- **`TestAddDoorsTimeSchedule._door(self, name='Врата')`** - `tests/test_access_group_add_doors.py:27`
  - touches: `hr.rfid.door`
- **`TestAddDoorsTimeSchedule._group(self, company)`** - `tests/test_access_group_add_doors.py:30`
  - touches: `hr.rfid.access.group`
- **`TestAddDoorsTimeSchedule._rel_schedule(self, group, door)`** - `tests/test_access_group_add_doors.py:35`
  - touches: `hr.rfid.access.group.door.rel`
- **`TestAlarmLineStateParse._ctrl(self, alarm_line_states)`** - `tests/test_alarm_line_state.py:19`
  - effects: `with_context`
  - touches: `hr.rfid.ctrl`
- **`TestAntiPassback._setup_apb_environment(self)`** - `tests/test_apb_zones.py:71`
  - Set up controllers and access groups for APB testing.
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`
- **`TestBarcodeNumber._make_card(self, number, card_input_type)`** - `tests/test_barcode_qr.py:31`
  - touches: `hr.rfid.card`
- **`TestPlateNumberEntry._plate(self, number)`** - `tests/test_card_lifecycle.py:186`
  - touches: `hr.rfid.card`
- **`RFIDTests._test_add_remove_card_employee(self, ctrl)`** - `tests/test_functional.py:98`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`RFIDTests._test_add_remove_card_partner(self, ctrl)`** - `tests/test_functional.py:160`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`RFIDTests._test_global_APB(self)`** - `tests/test_functional.py:232`
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`, `hr.rfid.zone`
- **`RFIDTests._test_add_remove_card_employee(self, ctrl)`** - `tests/test_functional_old.py:100`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.employee.rel`
- **`RFIDTests._test_add_remove_card_partner(self, ctrl)`** - `tests/test_functional_old.py:162`
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.contact.rel`
- **`RFIDTests._test_global_APB(self)`** - `tests/test_functional_old.py:234`
  - effects: `with_context`
  - touches: `hr.rfid.access.group.wizard`, `hr.rfid.zone`
- **`TestInterlockingMode._drain_io_table(self, response)`** - `tests/test_interlocking_mode.py:24`
  - Consume the follow-up D9 io-table commands an F0 read queues.
- **`TestMultiCompanySharedRecords._visible(self, model, record)`** - `tests/test_multi_company_rules.py:85`
  - Search the record as the company-A-bound non-superuser.
- **`TestMultiCompanySharedRecords._free_workcodes(cls, count)`** (`@classmethod`) - `tests/test_multi_company_rules.py:91`
  - Workcode has a global UNIQUE(workcode) constraint — pick codes
  - effects: `sudo`
  - touches: `hr.rfid.workcode`
- **`TestOrphanUserEventVisibility._sees(self, user, event)`** - `tests/test_multi_company_rules.py:424`
  - touches: `hr.rfid.event.user`
- **`TestOnboardingPanelFirstLoadRace._assert_full_panel(self, html)`** - `tests/test_onboarding.py:92`
- **`TestOnboardingPanelFailures._render_with(self, failure)`** - `tests/test_onboarding_panel_errors.py:32`
  - Render the banner while the work behind it fails with ``failure``.
- **`TestOnboardingPanelFailures._assert_passed_on(self, failure)`** - `tests/test_onboarding_panel_errors.py:43`
  - The failure travels on - and is never dressed up as a hidden banner.
- **`TestOneDoorTwoSchedules._group_on_the_door(self, name, schedule)`** - `tests/test_one_door_two_schedules.py:75`
  - Група за достъп, която отваря общата врата по подадения график.
  - touches: `hr.rfid.access.group`, `hr.rfid.access.group.door.rel`
- **`TestOneDoorTwoSchedules._both_groups_named(self, message, first, second)`** - `tests/test_one_door_two_schedules.py:92`
  - Съобщението на проверката за графици назовава ДВЕТЕ групи.
- **`TestOverlappingAccessGroups._card_state(self)`** - `tests/test_overlapping_access_groups.py:80`
  - touches: `hr.rfid.command`
- **`TestOverlappingAccessGroups._make_rel(self, activate_on, expiration)`** - `tests/test_overlapping_access_groups.py:100`
  - touches: `hr.rfid.access.group.contact.rel`
- **`TestOverlappingAccessGroups._raw_insert_rel(self, activate_on, expiration, state)`** - `tests/test_overlapping_access_groups.py:283`
  - Insert a contact rel bypassing the overlap @api.constrains check (we want overlap).
  - effects: `sql`
- **`TestRecalcRefusalIsHeard._ask(self, employee=None)`** - `tests/test_recalc_hook.py:38`
- **`TestSotDenied._build_minimal_hardware(cls)`** (`@classmethod`) - `tests/test_sot_denied.py:90`
  - Create a webstack + iCON115 controller + door + reader when the
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`, `hr.rfid.webstack`
- **`TestSotDenied._post_event_32(self, card_number, reader=1)`** - `tests/test_sot_denied.py:129`
- **`TestSotDenied._count_user_events(self, card)`** - `tests/test_sot_denied.py:155`
  - touches: `hr.rfid.event.user`
- **`TestSotDenied._count_sys_events(self)`** - `tests/test_sot_denied.py:159`
  - touches: `hr.rfid.event.system`
- **`TestSystemEventDedup._make(self, ts, door=None, action='25')`** - `tests/test_system_event_dedup.py:50`
  - touches: `hr.rfid.event.system`
- **`TestSystemEventDedup._count(self, action='25')`** - `tests/test_system_event_dedup.py:59`
  - touches: `hr.rfid.event.system`
- **`TestModulePresence._go_silent_since(self, minutes_ago)`** - `tests/test_telemetry_bus.py:29`
  - Put the module in the state a dark one is really in.
- **`TestModulePresence._pretend_realtime_connected(self)`** - `tests/test_telemetry_bus.py:43`
  - A module living on the websocket - it never writes updated_at.
- **`TestModulePresence._scan(self, times=1)`** - `tests/test_telemetry_bus.py:50`
  - touches: `hr.rfid.webstack`
- **`TestHeartbeatWritesOnlyWhatChanged._heartbeat_payload(self, firmware)`** - `tests/test_telemetry_bus.py:174`
- **`TestAnUnknownDevicePayload._post(self, payload)`** - `tests/test_unknown_device_payload.py:24`
- **`TestWebstackHeartbeat._ctrl(self, ctrl_id)`** - `tests/test_webstack.py:81`
  - touches: `hr.rfid.ctrl`
- **`SharedModuleCase._ts_b(self, number=0)`** - `tests/test_webstack_sharing.py:84`
  - effects: `sudo`
  - touches: `hr.rfid.time.schedule`
- **`SharedModuleCase._make_light_hardware(self)`** - `tests/test_webstack_sharing.py:90`
  - Owner-side controller/door/reader built directly through the ORM -
  - touches: `hr.rfid.ctrl`, `hr.rfid.door`, `hr.rfid.reader`
- **`SharedModuleCase._share_with_b(self)`** - `tests/test_webstack_sharing.py:111`
- **`SharedModuleCase._grant_b(self, door, ts_number=0, ag=None)`** - `tests/test_webstack_sharing.py:116`
  - B includes the shared door in ITS OWN access group, as B's manager.
  - touches: `hr.rfid.access.group.door.rel`
- **`TestSharedModuleVisibility._search_as(self, user, model, domain)`** - `tests/test_webstack_sharing.py:140`
- **`TestWsCommands._ws(self)`** - `tests/test_ws_commands.py:36`
- **`TestWsCommands._go_online(self, ws)`** - `tests/test_ws_commands.py:39`
  - effects: `sudo`
  - touches: `bus.bus`, `hr.rfid.command`, `ir.websocket`
- **`TestWsCommands._mk_cmd(self, ctrl, **vals)`** - `tests/test_ws_commands.py:53`
  - effects: `sudo`
  - touches: `hr.rfid.command`
- **`TestWsCommands._event(self, ctrl, bos, event_n=4)`** - `tests/test_ws_commands.py:59`
- **`TestWsCommands._dispatch_ev(self, ws, bid, events)`** - `tests/test_ws_commands.py:66`
  - touches: `bus.bus`, `ir.websocket`
- **`TestWsDispatch._ws(self)`** - `tests/test_ws_dispatch.py:31`
- **`TestWsDispatch._enable(self)`** - `tests/test_ws_dispatch.py:43`
- **`TestWsDispatch._msg(self, mtype, ws=None, k=None, v=WS_PROTO_VERSION, **payload)`** - `tests/test_ws_dispatch.py:48`
- **`TestWsDispatch._dispatch(self, data)`** - `tests/test_ws_dispatch.py:57`
  - touches: `ir.websocket`
- **`TestWsDispatch._event_dict(self, ctrl_id=5, bos=1, card=None, event_n=4, reader=1)`** - `tests/test_ws_dispatch.py:61`
- **`TestWsLayer._ws(self)`** - `tests/test_ws_layer.py:30`
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


### Access rights (ir.model.access)

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
- **`hr_rfid_group_officer_department_cards_rule`** on `hr_rfid.model_hr_rfid_card` - perms=`RWCD`, groups=`global`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_view_own_department_employees_rule`** on `hr.model_hr_employee` - perms=`RWCD`, groups=`global`, domain=`[('department_id.id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_view_own_department_department_rule`** on `hr.model_hr_department` - perms=`RWCD`, groups=`global`, domain=`[('id','=',user.employee_ids.department_id.id)]`
- **`hr_rfid_group_view_own_department_events_rule`** on `hr_rfid.model_hr_rfid_event_user` - perms=`RWCD`, groups=`global`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_rfid_set_card_active_inactive_status`** (HR RFID: Check card activation status) on `model_hr_rfid_card`, runs every 1 minutes, active=True
- **`hr_rfid_sync_ctrl_clock_cron`** (HR RFID: Synchronize controller clocks) on `model_hr_rfid_command`, runs every 3 hours, active=True
- **`hr_rfid_read_ctrl_status_cron`** (HR RFID: Read controller statuses) on `model_hr_rfid_command`, runs every 5 minutes, active=True
- **`hr_rfid_check_module_presence_cron`** (HR RFID: Check module presence) on `model_hr_rfid_webstack`, runs every 5 minutes, active=True
- **`hr_rfid_ws_republish_cron`** (HR RFID: Real-time command re-publish) on `model_hr_rfid_command`, runs every 1 minutes, active=True

### Data records summary

- `hr.rfid.event.user`: 11 record(s)
- `hr.rfid.card.type`: 10 record(s)
- `hr.rfid.card`: 7 record(s)
- `ir.cron`: 5 record(s)
- `onboarding.onboarding.step`: 5 record(s)
- `hr.rfid.access.group.employee.rel`: 5 record(s)
- `hr.rfid.door`: 4 record(s)
- `hr.rfid.reader`: 4 record(s)
- `ir.config_parameter`: 3 record(s)
- `hr.department`: 3 record(s)
- `hr.rfid.workcode`: 3 record(s)
- `hr.rfid.ctrl`: 2 record(s)
- `hr.rfid.access.group`: 2 record(s)
- `mail.template`: 1 record(s)
- `onboarding.onboarding`: 1 record(s)
- `res.lang`: 1 record(s)
- `res.users`: 1 record(s)
- `hr.rfid.webstack`: 1 record(s)
- `hr.rfid.ctrl.alarm`: 1 record(s)
- `hr.rfid.ctrl.emergency.group`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**OWL components**: `OnboardingBanner`


**JS files** (2): `static/src/components/onboarding/onboarding.js`, `static/src/views/onboarding_anywhere/onboarding_anywhere.js`


**SCSS files** (4): `static/src/scss/_variables.scss`, `static/src/scss/card_foldable_badge_report.scss`, `static/src/scss/card_full_page_ticket_report.scss`, `static/src/scss/card_full_page_ticket_report_pdf.scss`


**QWeb templates** (2): `static/src/components/onboarding/onboarding.xml`, `static/src/views/onboarding_anywhere/onboarding_anywhere.xml`



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

### From `git_log` (70)

#### Fix: fix(hr_rfid): green the vending + tour tests broken by three prior chang

Commit `b5dfd0bc1f` (2026-07-22): fix(hr_rfid): green the vending + tour tests broken by three prior changes

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u re-wro

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: fix(hr_rfid): HTTP auth idempotent for unprovisioned 0000 + G1 heal (pre

Commit `03a923e8c4` (2026-07-19): fix(hr_rfid): HTTP auth idempotent for unprovisioned 0000 + G1 heal (precommit)

#### Fix: fix(hr_rfid): remove dead orphaned hr_rfid_notification.xml (precommit A

Commit `e6f8f6b466` (2026-07-19): fix(hr_rfid): remove dead orphaned hr_rfid_notification.xml (precommit A12)

#### Fix: fix(hr_rfid): system-event grouping never matched door events + no time 

Commit `c2a718801b` (2026-07-17): fix(hr_rfid): system-event grouping never matched door events + no time bound

#### Fix: fix(hr_rfid): reword two WS log lines so a serial doesn't read as "N fai

Commit `7f232e99c3` (2026-07-14): fix(hr_rfid): reword two WS log lines so a serial doesn't read as "N failed"

#### Fix: [FIX] hr_rfid: silent-failure-hunter findings on the websocket layer

Commit `639141922a` (2026-07-11): [FIX] hr_rfid: silent-failure-hunter findings on the websocket layer

#### Fix: [FIX] hr_rfid: security-review hardening of the websocket ingress

Commit `a22ec8fd10` (2026-07-11): [FIX] hr_rfid: security-review hardening of the websocket ingress

#### Fix: [FIX] revert malformed manual bg.po appends (broke web translation loadi

Commit `fdb5eabb0c` (2026-06-24): [FIX] revert malformed manual bg.po appends (broke web translation loading)

#### Fix: [FIX] hr_rfid + hr_attendance_multi_rfid + rfid_service_base: two real b

Commit `27870ac47b` (2026-06-11): [FIX] hr_rfid + hr_attendance_multi_rfid + rfid_service_base: two real bugs found by un-flaking the test suites

#### Fix: [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

Commit `93125c7183` (2026-06-11): [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

#### Fix: [FIX] hr_rfid family: multi-company rules — global records + broken M2O 

Commit `a58ac6f455` (2026-06-11): [FIX] hr_rfid family: multi-company rules — global records + broken M2O chains were hidden

#### Fix: [FIX] hr_rfid: honor 'delay 0 = disabled' for delay_between_events

Commit `d78c5a8466` (2026-06-10): [FIX] hr_rfid: honor 'delay 0 = disabled' for delay_between_events

#### Fix: [FIX] hr_rfid: QR code mismatches hardware hex for w34s cards

Commit `47456010aa` (2026-05-20): [FIX] hr_rfid: QR code mismatches hardware hex for w34s cards

#### Fix: [FIX] hr_rfid: preserve card access on overlapping access group rels

Commit `46650f3373` (2026-05-19): [FIX] hr_rfid: preserve card access on overlapping access group rels

#### Fix: [FIX] hr_rfid: handle firmware event 32 (SOT_DENIED) as card event

Commit `3213db515a` (2026-04-23): [FIX] hr_rfid: handle firmware event 32 (SOT_DENIED) as card event

#### Fix: [TEST] hr_rfid_vending: Add ev64 flow tests and fix init sequence

Commit `27d717a56e` (2026-04-03): [TEST] hr_rfid_vending: Add ev64 flow tests and fix init sequence

#### Fix: [IMP] hr_rfid: Fix exception variable naming and lazy log formatting

Commit `c3a615d172` (2026-04-03): [IMP] hr_rfid: Fix exception variable naming and lazy log formatting

#### Fix: [FIX] hr_rfid: Continue command chain on controller error response

Commit `7367e5bccc` (2026-04-03): [FIX] hr_rfid: Continue command chain on controller error response

#### Fix: [FIX] hr_rfid: Skip FF command for vending controllers during init

Commit `ccfff62d89` (2026-04-03): [FIX] hr_rfid: Skip FF command for vending controllers during init

#### Fix: [FIX] hr_rfid,hr_rfid_vending: Add readonly=False to hardware routes and

Commit `1309fee0a8` (2026-04-03): [FIX] hr_rfid,hr_rfid_vending: Add readonly=False to hardware routes and fix onboarding access

#### Fix: [FIX] hr_rfid,rfid_service_zpl_labels: Add forcecreate=False to ir.confi

Commit `3a9ba0c116` (2026-03-31): [FIX] hr_rfid,rfid_service_zpl_labels: Add forcecreate=False to ir.config_parameter records

#### Fix: [FIX] hr_rfid: Handle concurrent onboarding step progress creation

Commit `e4438fc921` (2026-03-28): [FIX] hr_rfid: Handle concurrent onboarding step progress creation

#### Fix: [FIX] hr_rfid: Fix legacy module 10.3 JSON response format

Commit `58827cc6c4` (2026-03-26): [FIX] hr_rfid: Fix legacy module 10.3 JSON response format

#### Fix: [FIX] hr_rfid: Stop command flooding on controller error response

Commit `a751b6c771` (2026-03-26): [FIX] hr_rfid: Stop command flooding on controller error response


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid`
- Source digest: `sha256:bfab40bc1cfdb3403bf012bf5a0430bfb6d4596ac391cee94607bed4b739ad8c`
- Generated at: `2026-08-26T11:07:13+00:00`
- Generator: `polimex_module_knowledge`
