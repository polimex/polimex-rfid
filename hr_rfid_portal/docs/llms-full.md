---
id: hr_rfid_portal
title: RFID Portal Access
module: hr_rfid_portal
module_version: 19.0.0.1.3
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        RFID System Portal plugin\n    "
last_updated: '2026-11-23'
source_digest: sha256:22f2cc509e4a8529a40bb7a52a24f576cb2cd95a0fd23b91b0a970dc4c037274
depends:
- hr_rfid
- portal
entities:
  primary: hr.rfid.card
  related:
  - ir.actions.report
keywords:
- actions
- card
- plugin
- portal
- report
- rfid
- system
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: true
application: false
auto_install: true
counts:
  models: 2
  views: 1
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:c7be45c808d7f329bc7c39d285b65b00caa71e369e3b47fcde1fca2080bb967f
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:b5cd49d127387f9a2268ba91d6cd97d26cafa25aa477fc882f3d31134cdf3cc6
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Portal Access - `hr_rfid_portal` v19.0.0.1.3


        RFID System Portal plugin
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_portal`
- **Version**: `19.0.0.1.3`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: yes
- **Installable**: yes
- **Depends on**: `hr_rfid`, `portal`

### README (verbatim)

#### RFID Portal Access

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.1.0-green.svg)](https://apps.odoo.com)

Portal interface for RFID card management and self-service features.

##### 🎯 Overview

RFID Portal Access extends Odoo's portal functionality to provide self-service RFID card management for employees, contractors, and visitors. Users can view their cards, access history, and manage their RFID-related information through a user-friendly web interface.

##### ✨ Key Features

###### Card Management
- **View Cards**: See all assigned RFID cards
- **Card Details**: View card number, type, and validity
- **Barcode Display**: Show card barcode for mobile access
- **Access Groups**: See assigned access permissions

###### Self-Service Features
- **Access History**: View personal entry/exit logs
- **Event Timeline**: Visual timeline of access events
- **Download Reports**: Export access history
- **Mobile Friendly**: Responsive design for all devices

###### Portal Integration
- **My Account**: RFID section in portal account
- **Notifications**: Email alerts for card changes
- **Security**: View-only access to personal data
- **Multi-language**: Full translation support

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module
- portal module (Odoo standard)
- website module (Odoo standard)

###### Dependencies
```python
'depends': ['hr_rfid', 'portal', 'website']
```

##### 🛠️ Installation

1. Install hr_rfid module first

2. Install the portal module:
```bash
./odoo-bin -d your_database -i hr_rfid_portal
```

3. Portal features are automatically available

##### 🔧 Configuration

###### Portal Access Setup

1. **Enable Portal Access**
   - Go to employee/partner record
   - Action → Grant Portal Access
   - User receives invitation email

2. **Configure Permissions**
   - Settings → Users → Portal Users
   - Ensure "RFID Portal User" group
   - View-only permissions by default

###### Display Options

Configure in Settings → Website → RFID Portal:
```python
#### Portal display settings
show_card_barcode = True
show_access_history_days = 30
allow_report_download = True
show_card_image = False
```

##### 📖 Usage

###### Employee Portal View

1. **Access Portal**
   - Login to portal account
   - Navigate to My Account → RFID Cards

2. **View Information**
   - Active cards list
   - Card details and barcode
   - Access group memberships
   - Recent access events

3. **Download Reports**
   - Select date range
   - Choose format (PDF/Excel)
   - Download access history

###### Features Available

###### Card Information
- Card number and type
- Issue and expiry dates
- Active/inactive status
- Assigned doors/zones

###### Access History
- Date and time
- Door/reader name
- Event type (entry/exit)
- Status (granted/denied)

###### Barcode Display
- Large barcode for scanning
- Card number below
- Print option available

##### 🎨 Customization

###### Portal Templates

Override templates for custom design:
```xml
<!-- Inherit and modify card display -->
<template id="portal_my_rfid_cards_custom" inherit_id="hr_rfid_portal.portal_my_rfid_cards">
    <xpath expr="//div[@class='card-body']" position="after">
        <div class="custom-info">
            <!-- Add custom content -->
        </div>
    </xpath>
</template>
```

###### CSS Styling

Add custom styles:
```scss
// In static/src/scss/portal_rfid.scss
.rfid-card-portal {
    .card-barcode {
        text-align: center;
        padding: 20px;
        
        svg {
            max-width: 300px;
        }
    }
}
```

##### 🔌 API Extensions

###### Add Portal Features

```python
from odoo import http
from odoo.http import request

class RFIDPortalExtended(http.Controller):
    
    @http.route('/my/rfid/cards/<int:card_id>/events', 
                type='http', auth='user', website=True)
    def card_events(self, card_id, **kw):
        # Show detailed events for a card
        card = request.env['hr.rfid.card'].browse(card_id)
        # Check access rights
        if card.employee_id.user_id != request.env.user:
            return request.redirect('/my')
        
        events = card.event_ids.filtered(
            lambda e: e.event_time >= datetime.now() - timedelta(days=30)
        )
        
        return request.render('hr_rfid_portal.card_events', {
            'card': card,
            'events': events,
        })
```

##### 🔒 Security

###### Access Control
- Users see only their own cards
- No modification rights via portal
- Audit trail for all views
- Session timeout protection

###### Data Protection
- Personal data filtered
- Sensitive fields hidden
- Download limits enforced
- IP restrictions available

##### 🐛 Troubleshooting

###### Common Issues

1. **Can't see RFID section**
   - Check portal access is granted
   - Verify user has RFID cards
   - Clear browser cache

2. **Barcode not displaying**
   - Check barcode library installed
   - Verify card has barcode number
   - Enable in settings

3. **Access history missing**
   - Check date range settings
   - Verify events exist
   - Check user permissions

##### 📱 Mobile Optimization

###### Responsive Features
- Touch-friendly interface
- Swipe navigation
- Optimized barcode size
- Quick access buttons

###### Mobile App Integration
- QR code for app linking
- Push notifications ready
- Offline card display
- Biometric authentication

##### 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Create feature branch
3. Test on multiple devices
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-portal)
- [Demo Portal](https://demo.polimex.co/my)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_portal/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_portal --stop-after-init
```

> **Auto-install**: Odoo installs it by itself only in an operation that installs one of `hr_rfid`, `portal` while the rest of them are installed or installed in the same operation. A database that already has all of them does not get it by itself - not on an upgrade (`-u`), not on Update Apps List: install it once from Apps or with the command above.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.card` <a id='model-hr-rfid-card'></a>
Python class `HrRfidCard` in `models/hr_rfid_card.py:34`.  Model.  Inherits: `hr.rfid.card`, `portal.mixin`.  Description: *Card*.

#### Notable methods

- **`SELF_READABLE_FIELDS(self)`** - decorators: `@property`
- **`SELF_WRITABLE_FIELDS(self)`** - decorators: `@property`
- **`fields_get(self, allfields=None, attributes=None)`** - decorators: `@api.model`
  - calls `super() `fields_get``
- **`read(self, fields=None, load='_classic_read')`** - decorators: -
  - calls `super() `read``
- **`mapped(self, func)`** - decorators: -
  - calls `super() `mapped``
- **`_ensure_portal_user_can_write(self, fields)`** - decorators: `@api.model`
  - effects: `raise:AccessError`
- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - super-split (super `create`): pre=`with_context` · post=-
  - effects: `with_context`
- **`preview_card(self)`** - decorators: -

### `ir.actions.report` <a id='model-ir-actions-report'></a>
Python class `IrActionsReport` in `models/ir_actions_report.py:13`.  Model.  Inherits: `ir.actions.report`.

#### Notable methods

- **`get_available_barcode_masks(self)`** - decorators: `@api.model`
  - calls `super() `get_available_barcode_masks``
- **`apply_qr_code_polimex_logo_mask(self, width, height, barcode_drawing)`** - decorators: `@api.model`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_rfid_card.py`

- **`RFID_CARD_READABLE_FIELDS`** *(collection)* = `{'id', 'active', 'name', 'number', 'card_reference', 'card_type', 'employee_id', 'contact_id', 'activate_on', 'deactivate_on', 'cloud_card', 'create_date', 'write_date', 'company_id', 'display_name'}`  - line 12
- **`RFID_CARD_WRITABLE_FIELDS`** *(collection)* = `{'active'}`  - line 30

### `models/ir_actions_report.py`

- **`POLIMEX_QR_LOGO_SIZE_RATIO`** *(scalar)* = `0.1522`  - line 8
- **`POLIMEX_QR_LOGO_FILE`** *(expression)* = `Path('../static/img/polimex_qr_logo.png')`  - line 10


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`RFIDCustomerPortal.portal_my_webcards(self, **kw)`** (`@http.route`) - `controllers/portal.py:49`
  - effects: `sudo`
  - touches: `hr.rfid.card`
- **`RFIDCustomerPortal.portal_my_webcard(self, card_id, access_token=None, **kw)`** (`@http.route`) - `controllers/portal.py:66`
  - effects: `sudo`
  - touches: `ir.actions.report`
- **`RFIDCustomerPortal.portal_my_events(self, page=1, **kw)`** (`@http.route`) - `controllers/portal.py:89`
  - effects: `sudo`
  - touches: `hr.rfid.event.user`

### Private helpers

- **`RFIDCustomerPortal._prepare_home_portal_values(self, counters)`** - `controllers/portal.py:15`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `hr.rfid.card`, `hr.rfid.event.user`
- **`RFIDCustomerPortal._card_get_page_view_values(self, card, access_token, **kwargs)`** - `controllers/portal.py:33`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_card_form_inherit` | `hr.rfid.card` | - | hr_rfid.hr_rfid_card_view_form | `views/hr_rfid_card.xml` |

#### Sample XPath operations

- In `hr_rfid_card_form_inherit`:
  - `//div[@name='button_box'] [inside]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `hr.rfid.event.user`: 3 record(s)
- `hr.rfid.card`: 2 record(s)
- `hr.rfid.access.group.contact.rel`: 1 record(s)
- `ir.actions.act_window`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**QWeb templates in XML data, rendered by the server** (5): `portal_layout`, `portal_my_home_hr_rfid`, `portal_barcode_table`, `portal_my_barcode`, `portal_user_event_table`



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
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (3)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: fix portal views for 18.0

Commit `0456b88c40` (2024-10-07): fix portal views for 18.0


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_portal`
- Source digest: `sha256:22f2cc509e4a8529a40bb7a52a24f576cb2cd95a0fd23b91b0a970dc4c037274`
- Generated at: `2026-11-23T10:04:54+00:00`
- Generator: `polimex_module_knowledge`
