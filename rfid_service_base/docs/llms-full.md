---
id: rfid_service_base
title: RFID Service system Base
module: rfid_service_base
module_version: 19.0.0.12.3
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        Base module for visitor management and temporary RFID access control\n    "
last_updated: '2026-11-23'
source_digest: sha256:7f5165561e9c2a3797b5b3c4577d9f704c5ec023618138f3e2251ad08d762b31
depends:
- hr_rfid
- onboarding
entities:
  primary: rfid.service.sale.wiz
  related:
  - hr.rfid.access.group.contact.rel
  - onboarding.onboarding
  - onboarding.onboarding.step
  - res.company
  - res.partner
  - rfid.service
  - rfid.service.tags
  - rfid.service.sale
keywords:
- access
- base
- company
- contact
- control
- group
- management
- module
- onboarding
- rel
- res
- rfid
- sale
- service
- step
- temporary
- visitor
- wiz
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: true
application: true
auto_install: false
counts:
  models: 9
  views: 12
  access_rules: 9
  record_rules: 3
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:714df9502f542c9f3355f806c2f51bcb313e53656b044662cecba22ea8026c5d
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:766956bf01d21ba05a4bcccfde341bb9f2822c2cb8a914099a001b5563c6cbcb
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Service system Base - `rfid_service_base` v19.0.0.12.3


        Base module for visitor management and temporary RFID access control
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_base`
- **Version**: `19.0.0.12.3`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: yes
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `onboarding`

### README (verbatim)

#### RFID Service Base

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.2.0-green.svg)](https://apps.odoo.com)

Foundation module for visitor management and temporary access services integrated with RFID access control.

##### 🎯 Overview

RFID Service Base provides the infrastructure for managing temporary access services, visitor passes, and time-limited access cards. It's designed for facilities that need to issue temporary RFID access for visitors, contractors, events, or services.

##### ✨ Key Features

###### Service Management
- **Service Templates**: Define reusable access patterns
- **Time-based Access**: Daily, weekly, monthly periods
- **Visit-based Access**: Limited number of entries
- **Combined Limits**: Time AND visit restrictions

###### Access Configuration
- **Access Groups**: Link services to door groups
- **Zone Restrictions**: Limit access to specific areas
- **Time Schedules**: Business hours, weekends
- **Automatic Expiry**: Cards expire automatically

###### Card Generation
- **Barcode Cards**: Auto-generated for quick printing
- **RFID Assignment**: Link to physical RFID cards
- **Batch Creation**: Generate multiple cards at once
- **Template-based**: Consistent card formatting

###### Sales Integration
- **Service Sales**: Sell access as a service
- **Pricing Models**: Fixed price or time-based
- **Partner Integration**: Link to customers
- **Invoice Generation**: Automatic billing

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module installed
- Python 3.8+

###### Dependencies
```python
'depends': ['hr_rfid']
```

##### 🛠️ Installation

1. Install hr_rfid module first

2. Install the service base module:
```bash
./odoo-bin -d your_database -i rfid_service_base
```

3. Configure services and access groups

##### 🔧 Configuration

###### Service Setup

1. **Create Service**
   - RFID → Services → Create
   - Name: "Day Pass", "Monthly Parking", etc.
   - Select service type (time/count/both)

2. **Configure Access**
   - Select access group (doors)
   - Set time limits (hours, days, months)
   - Set visit count (if applicable)
   - Define valid hours (9 AM - 6 PM)

3. **Card Settings**
   - Enable barcode generation
   - Select card type
   - Configure email template
   - Set print template

###### Access Groups

1. **Visitor Groups**
   - Create dedicated visitor access groups
   - Assign appropriate doors
   - Set emergency behavior

2. **Zone Assignment**
   - Link services to zones
   - Configure zone restrictions
   - Set default zones

###### Email Configuration

```python
#### Email template for sending badges
mail_template_id = fields.Many2one(
    'mail.template',
    default=lambda self: self.env.ref('hr_rfid.card_barcode_mail_template_badge')
)
```

###### Print Configuration

```python
#### Print template for badges
print_template_id = fields.Many2one(
    'ir.actions.report',
    default=lambda self: self.env.ref('hr_rfid.action_report_res_partner_foldable_badge')
)
```

##### 📖 Usage

###### Creating a Service

1. **Define Service**
```
Name: "Visitor Day Pass"
Type: Time-based
Duration: 1 Day
Valid Hours: 08:00 - 18:00
Access Group: Visitor Doors
Generate Barcode: Yes
```

2. **Sell Service**
   - Click "New Sale" on service
   - Enter visitor details
   - Generate and email/print badge

###### Service Types

###### Time-based Services
```
Examples:
- Day Pass (1 day)
- Week Pass (7 days)
- Monthly Pass (1 month)
- Annual Pass (1 year)
```

###### Count-based Services
```
Examples:
- 5-Visit Pass
- 10-Entry Ticket
- Single Use Pass
```

###### Combined Services
```
Examples:
- 10 visits within 30 days
- Unlimited access for 1 week
- 5 entries per month for 6 months
```

###### Selling Services

1. **Quick Sale**
   - Service → New Sale
   - Fill visitor information
   - Generate card instantly

2. **Partner Sale**
   - Select existing partner
   - Choose service
   - Auto-fill information

3. **Bulk Sales**
   - Create multiple cards
   - Same service, different visitors
   - Batch print/email

##### 🔌 API Extension

###### Custom Services

```python
class CustomService(models.Model):
    _inherit = 'rfid.service'
    
    # Add custom fields
    requires_approval = fields.Boolean()
    approval_user_id = fields.Many2one('res.users')
    
    def action_new_sale(self):
        # Custom validation
        if self.requires_approval:
            self.check_approval()
        return super().action_new_sale()
```

###### Service Validation

```python
class ServiceSaleWizard(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    @api.constrains('email')
    def _check_visitor_blacklist(self):
        # Custom validation logic
        if self.email in self.get_blacklist():
            raise ValidationError("Visitor is blacklisted")
```

##### The setup checklist

Until visitor services are set up, a checklist appears above the services
(**Services**): define a visitor service, then issue the first visitor card.
Each step opens the screen where it is done, and ticks itself off as soon as
the thing exists - there is nothing to mark by hand.

Close it with the **X** (you are asked to confirm) and it is gone for good for
everybody in the company. It has no effect on anything else.

##### 🐛 Troubleshooting

###### Common Issues

1. **Card not working**
   - Check service active dates
   - Verify visit count remaining
   - Confirm time restrictions
   - Check access group doors

2. **Email not sending**
   - Verify email configuration
   - Check template settings
   - Confirm partner email

3. **Print issues**
   - Check print template
   - Verify report configuration
   - Test with preview

###### Debug Checklist

- [ ] Service is active
- [ ] Access group has doors
- [ ] Card is not expired
- [ ] Time schedule matches
- [ ] Visit count available
- [ ] Partner has access rights

##### ⚙️ Advanced Features

###### Multi-Service Cards

Assign multiple services to one card:
```python
#### One card, multiple services
card.service_ids = [(4, service1.id), (4, service2.id)]
```

###### Service Inheritance

Create service variations:
```python
#### Base service as template
base_service = self.env.ref('rfid_service_base.visitor_day_pass')
new_service = base_service.copy({
    'name': 'VIP Day Pass',
    'access_group_id': vip_access_group.id
})
```

###### Automatic Renewals

Configure auto-renewal:
```python
#### In service configuration
auto_renew = fields.Boolean()
renew_before_days = fields.Integer(default=7)
```

##### 📊 Reports

###### Service Analytics
- Services sold by period
- Revenue by service type
- Popular services ranking
- Utilization rates

###### Visitor Reports
- Active visitors count
- Visitor frequency
- Access patterns
- Expired services

###### Usage Statistics
- Entry count by service
- Peak usage times
- Average visit duration
- Zone utilization

##### 🤝 Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-services)
- [Video Tutorials](https://polimex.co/tutorials)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_base/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_service_base --stop-after-init
```

> **Application**: this module will appear as a top-level app in the Apps menu.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.access.group.contact.rel` <a id='model-hr-rfid-access-group-contact-rel'></a>
Python class `HrRfidAccessGroupContactRel` in `models/hr_rfid_access_group_contact_rel.py:4`.  Model.  Inherits: `hr.rfid.access.group.contact.rel`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `rfid_service_sale_id` | One2many → \`rfid.service.sale\` | Rfid Service Sale |  | ✓ | Visitor service sales backed by this contact-to-access-group binding. Used to ca |

### `onboarding.onboarding` <a id='model-onboarding-onboarding'></a>
Python class `OnboardingOnboarding` in `models/onboarding_onboarding.py:4`.  Model.  Inherits: `onboarding.onboarding`.

#### Notable methods

- **`action_close_panel_service_setup(self)`** - decorators: `@api.model`
  - effects: `sudo`

### `onboarding.onboarding.step` <a id='model-onboarding-onboarding-step'></a>
Python class `OnboardingOnboardingStep` in `models/onboarding_onboarding_step.py:4`.  Model.  Inherits: `onboarding.onboarding.step`.

#### Notable methods

- **`action_open_step_service_define(self)`** - decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_service_first_sale(self)`** - decorators: `@api.model`
  - touches: `ir.actions.act_window`

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:4`.  Model.  Inherits: `res.company`.

#### Notable methods

- **`create(self, values_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``

### `res.partner` <a id='model-res-partner'></a>
Python class `ResPartner` in `models/res_partner.py:7`.  Model.  Inherits: `res.partner`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `partner_rfid_sales_count` | Char | Partner Rfid Sales Count |  | - | Number of visitor service sales registered against this contact across all servi |

#### Notable methods

- **`action_rfid_sales(self)`** - decorators: -
  - effects: `i18n`

### `rfid.service` <a id='model-rfid-service'></a>
Python class `BaseRFIDService` in `models/rfid_service.py:11`.  Model.  Inherits: `mail.activity.mixin`, `mail.thread`.  Description: *RFID Service*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Service Name | ✓ | ✓ | User-friendly name for this RFID service offering.          • Purpose: Identify  |
| `active` | Boolean | Active |  | ✓ | Whether this service is currently available for new sales.          • Active: Se |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns this service template. Services are isolated per company — use |
| `color` | Integer | Color |  | ✓ | Color coding for visual identification in kanban and other views.          • Vis |
| `displayed_image_id` | Many2one → \`ir.attachment\` | Cover Image |  | ✓ | Visual image displayed on service cards and promotional materials.          • Pu |
| `tag_ids` | Many2many → \`rfid.service.tags\` | Service Tags |  | ✓ | Categorization tags for organizing and filtering services.          • Organizati |
| `service_type` | Selection | Service Type |  | ✓ | How this service controls customer access duration and usage.      • Time based: |
| `visits` | Integer | Number of Visits |  | ✓ | Maximum number of times a customer can access with this service.          • Purp |
| `time_interval_number` | Integer | Duration Number |  | ✓ | Numeric part of the service duration (combined with Duration Unit).          • P |
| `time_interval_type` | Selection | Duration Unit |  | ✓ | Time unit for the service duration (combined with Duration Number).          • M |
| `time_interval_start` | Float | Access Start Time |  | ✓ | Daily start time when access is allowed (24-hour format).          • Format: Hou |
| `time_interval_end` | Float | Access End Time |  | ✓ | Daily end time when access is no longer allowed (24-hour format).          • For |
| `access_group_id` | Many2one → \`hr.rfid.access.group\` | Access Group | ✓ | ✓ | RFID access group that defines which doors customers can access.          • Purp |
| `generate_barcode_card` | Boolean | Generate Barcode Cards |  | ✓ | Automatically create barcode-based cards instead of RFID cards.          • When  |
| `zone_id` | Many2one → \`hr.rfid.zone\` | Tracking Zone |  | ✓ | Optional zone for tracking customer presence and behavior.          • Purpose: M |
| `parent_id` | Many2one → \`res.partner\` | Parent Customer |  | ✓ | Parent company or organization that all service customers will be linked to.     |
| `card_type` | Many2one → \`hr.rfid.card.type\` | Card Type |  | ✓ | Type of RFID card issued to customers for this service.          • Purpose: Defi |
| `fixed_time` | Boolean | Fixed Time Schedule |  | ✓ | Whether service times are fixed or can be customized per sale.          • Fixed  |
| `mail_template_id` | Many2one → \`mail.template\` | Email Template |  | ✓ | Email template used when sending badges/cards to customers.          • Purpose:  |
| `print_template_id` | Many2one → \`ir.actions.report\` | Print Template |  | ✓ | Report template used when printing physical badges/cards for customers.          |

#### Notable methods

- **`action_new_sale(self)`** - decorators: -
  - effects: `sudo`
  - touches: `hr.rfid.card`
- **`action_view_sales(self)`** - decorators: -
  - effects: `sudo`

### `rfid.service.tags` <a id='model-rfid-service-tags'></a>
Python class `ServiceTags` in `models/rfid_service.py:296`.  Model.  Description: *Service Tags*.

> Tags of service's

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Tag Name | ✓ | ✓ | Name of the service tag for categorization and filtering.          • Purpose: Cr |
| `color` | Integer | Color |  | ✓ | Color for visual identification of this tag in lists and kanban views.           |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company that owns this tag. Tags are isolated per company so each tenant can bui |

### `rfid.service.sale` <a id='model-rfid-service-sale'></a>
Python class `BaseRFIDService` in `models/rfid_service_sale.py:11`.  Model.  Inherits: `mail.thread`.  Description: *RFID Service Sales*.  Default order: `create_date desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Sale Reference |  | ✓ | Unique identifier for this service sale transaction.          • Purpose: Track a |
| `service_id` | Many2one → \`rfid.service\` | Service | ✓ | ✓ | RFID service that was sold to the customer.          • Purpose: Links this sale  |
| `start_date` | Datetime | Access Start Date | ✓ | ✓ | Date and time when customer access begins.          • Activation: Customer's car |
| `end_date` | Datetime | Access End Date | ✓ | ✓ | Date and time when customer access expires.          • Expiration: Customer's ca |
| `state` | Selection | Status |  | ✓ | Current status of this service sale.          • Registered: Sale created but ser |
| `company_id` | Many2one → \`res.company\` | Company |  | - | Company that owns this sale — inherited from the underlying service. Used for mu |
| `partner_id` | Many2one → \`res.partner\` | Customer |  | ✓ | Customer who purchased this service.          • Individual: Must be a person, no |
| `card_id` | Many2one → \`hr.rfid.card\` | RFID Card |  | ✓ | Physical or digital card assigned to the customer for access.          • Access  |
| `card_number` | Char | Card Number |  | - | Unique identifier/number of the card assigned to this service sale. |
| `access_group_contact_rel` | Many2one → \`hr.rfid.access.group.contact.rel\` | Access Permission |  | ✓ | Technical link between customer and access group that grants permissions.        |
| `visits` | Integer | Remaining Visits |  | - | How many more times the customer can come in on this service. Every entry throug |

#### Notable methods

- **`_compute_visits(self)`** - decorators: `@api.depends`
- **`_compute_state(self)`** - decorators: `@api.depends`
- **`unlink(self)`** - decorators: -
  - calls `super() `unlink``
- **`extend_service(self)`** - decorators: -
  - touches: `ir.actions.act_window`
- **`partner_sales(self)`** - decorators: -
  - touches: `ir.actions.act_window`
- **`email_card(self)`** - decorators: -
  - effects: `raise:UserError`
- **`print_card(self)`** - decorators: -
- **`cancel_sale(self)`** - decorators: -
  - effects: `message_post`
- **`fix_partner(self)`** - decorators: -
  - touches: `rfid.service.sale`

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceBaseSaleWiz` in `models/rfid_service_sale_wiz.py:17`.  TransientModel (wizard).  Inherits: `balloon.mixin`.  Description: *Base RFID Service Sale Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `extend_sale_id` | Many2one → \`rfid.service.sale\` | Extend Sale |  | ✓ | When set, the wizard runs in Extend mode — it adds time to the linked sale inste |
| `ext_start_date` | Datetime | Old start |  | - | Original start date of the sale being extended (shown for reference). |
| `ext_end_date` | Datetime | Old end |  | - | Original end date of the sale being extended (shown for reference). The new end  |
| `service_id` | Many2one → \`rfid.service\` | Service |  | ✓ | Catalog entry from which the card inherits its access group, time window and car |
| `fixed_time` | Boolean | *from service_id.fixed_time* |  | - | Mirrors the service's Fixed Time flag — when true, the end date snaps to a fixed |
| `generate_barcode_card` | Boolean | *from service_id.generate_barcode_card* |  | - | Mirrors the service flag — when true, the wizard auto-generates a printable barc |
| `parent_id` | Many2one → \`res.partner\` | *from service_id.parent_id* |  | - | Parent partner the new visitor contact will be filed under (inherited from the s |
| `partner_id` | Many2one → \`res.partner\` | Partner |  | ✓ | The value will be generated automatic if empty! |
| `email` | Char | Email |  | ✓ | Visitor email address. Pre-filled from the selected partner; editing here also u |
| `mobile` | Char | Mobile |  | ✓ | Visitor mobile/phone number. Pre-filled from the selected partner; editing here  |
| `start_date` | Datetime | Service start |  | ✓ | Moment the card becomes active. Defaults to a calculated start based on the serv |
| `end_date` | Datetime | Service end |  | ✓ | Moment the card stops working. Calculated from start + the service's time interv |
| `card_number` | Char | The card number | ✓ | ✓ | The RFID number or generated barcode the visitor will carry. For RFID services,  |
| `visits` | Integer | *from service_id.visits* |  | - | Mirrors the visits-per-card limit from the service template — informational only |

#### Notable methods

- **`_onchange_service_id(self)`** - decorators: `@api.onchange`, `@api.depends`
- **`_onchange_start_date(self)`** - decorators: `@api.onchange`, `@api.depends`
- **`email_card(self)`** - decorators: -
  - effects: `raise:UserError`
- **`print_card(self)`** - decorators: -
- **`write_card(self)`** - decorators: -
  - touches: `ir.actions.act_window`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_view_partner_form_inherit_hr_rfid` | `res.partner` | - | base.view_partner_form | `views/res_partner_views.xml` |
| `hr_rfid_service_kanban` | `rfid.service` | - |  | `views/rfid_service.xml` |
| `services_form` | `rfid.service` | - |  | `views/rfid_service.xml` |
| `services_tree` | `rfid.service` | - |  | `views/rfid_service.xml` |
| `hr_rfid_service_search` | `rfid.service` | - |  | `views/rfid_service.xml` |
| `hr_rfid_service_sale_action_search` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_form` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_tree` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_pivot` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_graph` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_calendar` | `rfid.service.sale` | - |  | `views/rfid_service_sale.xml` |
| `sale_wiz_form` | `rfid.service.sale.wiz` | - |  | `views/rfid_service_sale_wiz.xml` |

#### Sample XPath operations

- In `hr_view_partner_form_inherit_hr_rfid`:
  - `//div[@name='button_box'] [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_card_user`, `group_card_manager`


### Access rights (ir.model.access; v20: ir.access rows with a group)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `rfid_service_base.access_service.user` | `rfid_service_base.model_rfid_service` | `rfid_service_base.group_card_user` | ✓ |  |  |  |

| `rfid_service_base.access_service.manager` | `rfid_service_base.model_rfid_service` | `rfid_service_base.group_card_manager` | ✓ | ✓ | ✓ |  |

| `rfid_service_base.access_service.erp.manager` | `rfid_service_base.model_rfid_service` | `base.group_erp_manager` | ✓ | ✓ | ✓ | ✓ |

| `rfid_service_base.access_rfid_service_tags_user` | `rfid_service_base.model_rfid_service_tags` | `rfid_service_base.group_card_user` | ✓ |  |  |  |

| `rfid_service_base.access_rfid_service_tags_manager` | `rfid_service_base.model_rfid_service_tags` | `rfid_service_base.group_card_manager` | ✓ | ✓ | ✓ | ✓ |

| `rfid_service_base.access_service_sale.user` | `rfid_service_base.model_rfid_service_sale` | `rfid_service_base.group_card_user` | ✓ |  |  |  |

| `rfid_service_base.access_service_sale.manager` | `rfid_service_base.model_rfid_service_sale` | `rfid_service_base.group_card_manager` | ✓ | ✓ |  |  |

| `rfid_service_base.access_service_sale.erp.manager` | `rfid_service_base.model_rfid_service_sale` | `base.group_erp_manager` | ✓ | ✓ |  | ✓ |

| `rfid_service_base.access_service_sale_wiz.user` | `rfid_service_base.model_rfid_service_sale_wiz` | `rfid_service_base.group_card_user` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_rfid_service_multi_company`** on `model_rfid_service` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_rfid_service_sale_multi_company`** on `model_rfid_service_sale` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_rfid_service_tag_multi_company`** on `model_rfid_service_tags` - perms=`RWCD`, groups=`global`, domain=`[('company_id', 'in', company_ids + [False])]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `rfid.service`: 12 record(s)
- `rfid.service.tags`: 7 record(s)
- `hr.rfid.card`: 5 record(s)
- `rfid.service.sale`: 5 record(s)
- `ir.attachment`: 5 record(s)
- `ir.actions.act_window`: 3 record(s)
- `onboarding.onboarding.step`: 2 record(s)
- `hr.rfid.access.group.contact.rel`: 2 record(s)
- `ir.sequence`: 1 record(s)
- `onboarding.onboarding`: 1 record(s)
- `res.users`: 1 record(s)
- `res.partner`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (1): `static/tests/tours/issue_visitor_card_tour.js`



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

##### The setup checklist (onboarding banner)

The banner is NOT a view class of this module. It is attached by putting the
onboarding's `route_name` in the CONTEXT of the action:

```xml
<field name="context">{'onboarding_route_name': 'rfid_service_base_setup'}</field>
```

on ``hr_rfid_service_action` (Services, kanban/list/form)` (`views/rfid_service.xml`). That is the whole integration on this side.

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
`_prepare_rendering_values` auto-completes its two steps (a `rfid.service` exists; a `rfid.service.sale` exists) for the CURRENT company
before delegating to core, and `action_close_panel_service_setup` is the close action named on the
onboarding record. Nothing here has to know how the banner is drawn.
Entries derived from the module's own code comments and bug-fix commit history.

### From `git_log` (14)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: [TOUR] rfid_service_base: issue-visitor-card E2E + v19 view fixes

Commit `ec9fb6b37a` (2026-05-14): [TOUR] rfid_service_base: issue-visitor-card E2E + v19 view fixes

#### Fix: [FIX] noupdate on user-tunable data records (3 modules)

Commit `df70ee6943` (2026-05-01): [FIX] noupdate on user-tunable data records (3 modules)

#### Fix: Fix SQL constraint error message formatting in rfid_service_sale.py

Commit `3e1885ed8b` (2025-04-02): Fix SQL constraint error message formatting in rfid_service_sale.py

#### Fix: Fix translation for unique service constraint message

Commit `8edeb56832` (2025-03-31): Fix translation for unique service constraint message

#### Fix: fixes ported from 17.0

Commit `09608db843` (2024-10-15): fixes ported from 17.0

#### Fix: Fix mail composer params to 17.0

Commit `e581c4e6b2` (2024-09-25): Fix mail composer params to 17.0

#### Fix: fix security and bugs

Commit `7e2b0572af` (2024-09-18): fix security and bugs

#### Fix: fix security and bugs

Commit `88d8f7cf6f` (2024-09-13): fix security and bugs

#### Fix: fix re-issue old un-active cards

Commit `9220189542` (2024-07-07): fix re-issue old un-active cards

#### Fix: fix re-issue old un-active cards

Commit `08425a7d03` (2024-07-07): fix re-issue old un-active cards

#### Fix: fix operator rights

Commit `a3f5bdc3f4` (2024-06-25): fix operator rights

#### Fix: fix demo data

Commit `58a6b16e4f` (2023-09-26): fix demo data

#### Fix: fix demo data

Commit `9fe5aa23d7` (2023-09-26): fix demo data


## Source provenance <a id='provenance'></a>

- Module: `rfid_service_base`
- Source digest: `sha256:7f5165561e9c2a3797b5b3c4577d9f704c5ec023618138f3e2251ad08d762b31`
- Generated at: `2026-11-23T10:04:19+00:00`
- Generator: `polimex_module_knowledge`
