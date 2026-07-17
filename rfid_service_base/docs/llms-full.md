---
id: rfid_service_base
title: RFID Service system Base
module: rfid_service_base
module_version: 19.0.0.9.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        Base module for visitor management and temporary RFID access control\n    "
last_updated: '2026-05-14'
source_digest: sha256:836d6ead9b8933e24830e8a54e25e71f4612c24c0dc237191d7a92ab0114708d
depends:
- hr_rfid
- onboarding
entities:
  primary: hr.rfid.access.group.contact.rel
  related:
  - onboarding.onboarding
  - onboarding.onboarding.step
  - res.company
  - res.partner
  - rfid.service
  - rfid.service.tags
  - rfid.service.sale
  - rfid.service.sale.wiz
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
- partner
- rel
- res
- rfid
- service
- step
- temporary
- visitor
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


# RFID Service system Base — `rfid_service_base` v19.0.0.9.0


        Base module for visitor management and temporary RFID access control
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_base`
- **Version**: `19.0.0.9.0`
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
| `rfid_service_sale_id` | One2many → \`rfid.service.sale\` |  |  | ✓ | Visitor service sales backed by this contact-to-access-group binding. Used to ca |

### `onboarding.onboarding` <a id='model-onboarding-onboarding'></a>
Python class `OnboardingOnboarding` in `models/onboarding_onboarding.py:4`.  Model.  Inherits: `onboarding.onboarding`.

#### Notable methods

- **`action_close_panel_service_setup(self)`** — decorators: `@api.model`
  - effects: `sudo`

### `onboarding.onboarding.step` <a id='model-onboarding-onboarding-step'></a>
Python class `OnboardingOnboardingStep` in `models/onboarding_onboarding_step.py:4`.  Model.  Inherits: `onboarding.onboarding.step`.

#### Notable methods

- **`action_open_step_service_define(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`
- **`action_open_step_service_first_sale(self)`** — decorators: `@api.model`
  - touches: `ir.actions.act_window`

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:4`.  Model.  Inherits: `res.company`.

#### Notable methods

- **`create(self, values_list)`** — decorators: `@api.model_create_multi`
  - calls `super() `create``

### `res.partner` <a id='model-res-partner'></a>
Python class `ResPartner` in `models/res_partner.py:7`.  Model.  Inherits: `res.partner`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `partner_rfid_sales_count` | Char |  |  | — | Number of visitor service sales registered against this contact across all servi |

#### Notable methods

- **`action_rfid_sales(self)`** — decorators: —
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

- **`action_new_sale(self)`** — decorators: —
  - effects: `sudo`
  - touches: `hr.rfid.card`
- **`action_view_sales(self)`** — decorators: —
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
| `company_id` | Many2one → \`res.company\` | Company |  | — | Company that owns this sale — inherited from the underlying service. Used for mu |
| `partner_id` | Many2one → \`res.partner\` | Customer |  | ✓ | Customer who purchased this service.          • Individual: Must be a person, no |
| `card_id` | Many2one → \`hr.rfid.card\` | RFID Card |  | ✓ | Physical or digital card assigned to the customer for access.          • Access  |
| `card_number` | Char | Card Number |  | — | Unique identifier/number of the card assigned to this service sale. |
| `access_group_contact_rel` | Many2one → \`hr.rfid.access.group.contact.rel\` | Access Permission |  | ✓ | Technical link between customer and access group that grants permissions.        |
| `visits` | Integer | Remaining Visits |  | — | Number of visits remaining for this service (for visit-based services).  • Purpo |

#### Notable methods

- **`_compute_state(self)`** — decorators: `@api.depends`
- **`unlink(self)`** — decorators: —
  - calls `super() `unlink``
- **`extend_service(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`partner_sales(self)`** — decorators: —
  - touches: `ir.actions.act_window`
- **`email_card(self)`** — decorators: —
  - effects: `raise:UserError`
- **`print_card(self)`** — decorators: —
- **`cancel_sale(self)`** — decorators: —
  - effects: `message_post`
- **`fix_partner(self)`** — decorators: —
  - touches: `rfid.service.sale`

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceBaseSaleWiz` in `models/rfid_service_sale_wiz.py:17`.  TransientModel (wizard).  Inherits: `balloon.mixin`.  Description: *Base RFID Service Sale Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `extend_sale_id` | Many2one → \`rfid.service.sale\` |  |  | ✓ | When set, the wizard runs in Extend mode — it adds time to the linked sale inste |
| `ext_start_date` | Datetime | Old start |  | — | Original start date of the sale being extended (shown for reference). |
| `ext_end_date` | Datetime | Old end |  | — | Original end date of the sale being extended (shown for reference). The new end  |
| `service_id` | Many2one → \`rfid.service\` |  |  | ✓ | Catalog entry from which the card inherits its access group, time window and car |
| `fixed_time` | Boolean |  |  | — | Mirrors the service's Fixed Time flag — when true, the end date snaps to a fixed |
| `generate_barcode_card` | Boolean |  |  | — | Mirrors the service flag — when true, the wizard auto-generates a printable barc |
| `parent_id` | Many2one → \`res.partner\` |  |  | — | Parent partner the new visitor contact will be filed under (inherited from the s |
| `partner_id` | Many2one → \`res.partner\` |  |  | ✓ | The value will be generated automatic if empty! |
| `email` | Char |  |  | ✓ | Visitor email address. Pre-filled from the selected partner; editing here also u |
| `mobile` | Char |  |  | ✓ | Visitor mobile/phone number. Pre-filled from the selected partner; editing here  |
| `start_date` | Datetime | Service start |  | ✓ | Moment the card becomes active. Defaults to a calculated start based on the serv |
| `end_date` | Datetime | Service end |  | ✓ | Moment the card stops working. Calculated from start + the service's time interv |
| `card_number` | Char | The card number | ✓ | ✓ | The RFID number or generated barcode the visitor will carry. For RFID services,  |
| `visits` | Integer |  |  | — | Mirrors the visits-per-card limit from the service template — informational only |

#### Notable methods

- **`_onchange_service_id(self)`** — decorators: `@api.onchange`, `@api.depends`
- **`_onchange_start_date(self)`** — decorators: `@api.onchange`, `@api.depends`
- **`email_card(self)`** — decorators: —
  - effects: `raise:UserError`
- **`print_card(self)`** — decorators: —
- **`write_card(self)`** — decorators: —
  - touches: `ir.actions.act_window`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`TestRfidServiceOnboarding.setUpClass(cls)`** (`@classmethod`) — `tests/test_onboarding.py:13`
  - calls `super()`
- **`TestRfidServiceOnboarding.test_panel_has_two_steps_in_order(self)`** — `tests/test_onboarding.py:21`
- **`TestRfidServiceOnboarding.test_step_actions_resolve_to_real_windows(self)`** — `tests/test_onboarding.py:27`
  - touches: `onboarding.onboarding.step`
- **`TestRfidServiceOnboarding.test_define_step_completes_when_service_exists(self)`** — `tests/test_onboarding.py:34`
  - touches: `hr.rfid.access.group`, `rfid.service`
- **`TestRfidServiceOnboarding.test_sale_step_completes_when_service_sale_exists(self)`** — `tests/test_onboarding.py:54`
  - touches: `hr.rfid.access.group`, `res.partner`, `rfid.service`, `rfid.service.sale`
- **`TestRfidServiceLifecycle.setUpClass(cls)`** (`@classmethod`) — `tests/test_service_lifecycle.py:20`
  - calls `super()`
  - touches: `hr.rfid.access.group`, `res.partner`, `rfid.service`
- **`TestRfidServiceLifecycle.test_state_progress_when_inside_window(self)`** — `tests/test_service_lifecycle.py:70`
- **`TestRfidServiceLifecycle.test_state_finished_when_window_expired(self)`** — `tests/test_service_lifecycle.py:80`
- **`TestRfidServiceLifecycle.test_state_canceled_when_ag_rel_window_collapsed(self)`** — `tests/test_service_lifecycle.py:92`
  - The 'canceled' state is detected by a 1-second AG window —
- **`TestRfidServiceLifecycle.test_cancel_sale_collapses_ag_window(self)`** — `tests/test_service_lifecycle.py:111`
- **`TestRfidServiceLifecycle.test_cancel_sale_idempotent_for_already_finished(self)`** — `tests/test_service_lifecycle.py:123`
- **`TestRfidServiceLifecycle.test_extend_service_returns_action_with_correct_context(self)`** — `tests/test_service_lifecycle.py:144`
- **`TestRfidServiceLifecycle.test_extend_service_requires_single_record(self)`** — `tests/test_service_lifecycle.py:158`
  - touches: `hr.rfid.access.group.contact.rel`, `res.partner`, `rfid.service.sale`
- **`TestRfidServiceLifecycle.test_email_card_raises_when_partner_has_no_email(self)`** — `tests/test_service_lifecycle.py:189`
- **`TestRfidServiceLifecycle.test_print_card_returns_action(self)`** — `tests/test_service_lifecycle.py:201`
  - print_card() delegates to the foldable_badge report. We just
- **`TestRfidServiceLifecycle.test_service_default_color_is_assigned(self)`** — `tests/test_service_lifecycle.py:220`
  - touches: `rfid.service`
- **`TestRfidServiceLifecycle.test_action_view_sales_is_filtered_by_service(self)`** — `tests/test_service_lifecycle.py:230`
- **`RFIDServices.test_rfid_services(self)`** — `tests/test_services.py:20`
  - effects: `with_context`
  - touches: `hr.rfid.card`, `rfid.service`, `rfid.service.sale`, `rfid.service.sale.wiz`

### Private helpers

- **`TestRfidServiceLifecycle._attach_partner_to_ag(self, *, activate_on=None, expiration=None)`** — `tests/test_service_lifecycle.py:46`
  - touches: `hr.rfid.access.group.contact.rel`
- **`TestRfidServiceLifecycle._make_sale(self, *, start, end, ag_rel)`** — `tests/test_service_lifecycle.py:56`
  - touches: `rfid.service.sale`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_view_partner_form_inherit_hr_rfid` | `res.partner` | — | base.view_partner_form | `views/res_partner_views.xml` |
| `hr_rfid_service_kanban` | `rfid.service` | — |  | `views/rfid_service.xml` |
| `services_form` | `rfid.service` | — |  | `views/rfid_service.xml` |
| `services_tree` | `rfid.service` | — |  | `views/rfid_service.xml` |
| `hr_rfid_service_search` | `rfid.service` | — |  | `views/rfid_service.xml` |
| `hr_rfid_service_sale_action_search` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_form` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_tree` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_pivot` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_graph` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `hr_rfid_service_sale_calendar` | `rfid.service.sale` | — |  | `views/rfid_service_sale.xml` |
| `sale_wiz_form` | `rfid.service.sale.wiz` | — |  | `views/rfid_service_sale_wiz.xml` |

#### Sample XPath operations

- In `hr_view_partner_form_inherit_hr_rfid`:
  - `//div[@name='button_box'] [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_card_user`, `group_card_manager`


### Access rights (ir.model.access)

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

- **`ir_rule_rfid_service_multi_company`** on `model_rfid_service` — perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_rfid_service_sale_multi_company`** on `model_rfid_service_sale` — perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`ir_rule_rfid_service_tag_multi_company`** on `model_rfid_service_tags` — perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `rfid.service`: 10 record(s)
- `rfid.service.tags`: 6 record(s)
- `ir.attachment`: 5 record(s)
- `hr.rfid.card`: 3 record(s)
- `rfid.service.sale`: 3 record(s)
- `onboarding.onboarding.step`: 2 record(s)
- `ir.sequence`: 1 record(s)
- `onboarding.onboarding`: 1 record(s)
- `res.users`: 1 record(s)
- `res.partner`: 1 record(s)


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

#### Gotcha: `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. З
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.90 -->

From **Модели и полета** in odoo19-gotchas.md:

> `@api.onchange` **НЕ** се вика при `create()` — само при UI промяна. За логика при create ползвай `@api.model_create_multi` или `_compute`

Matched tokens: `@api.onchange, api.onchange, _compute, @api.model_create_multi, api.model_create_multi`

#### Gotcha: **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.70 -->

From **Security & Constraints** in odoo19-gotchas.md:

> **`res.groups.category_id` премахнато** → `privilege_id` (M2O към `res.groups.privilege`, който има `category_id`). Pattern: създаваш `res.groups.privilege` с `category_id=ref('module_category_X')`, после групите имат `privilege_id=ref('res_groups_privilege_X')`.

Matched tokens: `res.groups.privilege, privilege_id, category_id`

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `validationerror, models.constraint`

#### Gotcha: **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`**
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **Kanban templates: `<t t-name="card">` НЕ `<t t-name="kanban-box">`** — v18→v19 преименуване. Стария път минава XML lint и install, но при отваряне в браузъра гърми с `OwlError: Missing 'card' template`. Структурата на content също е олекотена (без `oe_kanban_card` обвивка — директно полета + footer).

Matched tokens: `<t t-name="card">, oe_kanban_card`

#### Gotcha: **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` ат
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Views (XML / kanban / search)** in odoo19-gotchas.md:

> **`%(name)s` буквално в XML view** (вкл. в `<code>`, `<p>`, `help=` атрибут) се интерпретира от Odoo XML parser-а като `ir.model.data` external-ID lookup → `ValueError: External ID not found in the system: <module>.<name>`. Не може да бъде escape-нато с `%%`. Решение: преформулирай текста без `%(...)s` синтаксис (напр. `the placeholder <code>response_time</code>` вместо `<code>%(response_time)s</code>`).

Matched tokens: `help=, <p>`

#### Gotcha: **TransientModel + `target='current'` = dead link.** TransientModel за
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.60 -->

From **Wizards & TransientModel** in odoo19-gotchas.md:

> **TransientModel + `target='current'` = dead link.** TransientModel записи биват изтрити от autovacuum cron след минути до часове. Ако `action_window` връща `target='current'` с `res_id`, browser-ът bookmark-ва URL `/odoo/<model>/<id>` — следващ refresh/back-button → 404 "тотална грешка" / "запис не съществува". **Винаги** използвай `target='new'` (modal dialog) — modal-ите не променят URL-а, така че няма bookmarkable стара ID. Ако имаш Next/Back бутони (`type="object"`), pre-create record-а в `action_open_wizard()` за да съществува за compute_field-а, но дръж dialog-а modal. Производна на това: `_reopen()` helper-и за multistep wizard-и също трябва да са `target='new'`, не `'current'`.

Matched tokens: `res_id, type="object"`

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

#### Gotcha: `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpC
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Тестове** in odoo19-gotchas.md:

> `_registry_readonly_enabled = False` (НЕ `readonly_enabled`) за `HttpCase` тестове с DB writes

Matched tokens: `httpcase`

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

#### Gotcha: При `ev64` хардуерни събития: хардуерът изпраща follow-up Granted even
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Общи** in odoo19-gotchas.md:

> При `ev64` хардуерни събития: хардуерът изпраща follow-up Granted event след grant — симулирай с `event_code=3`

Matched tokens: `event_code=3`

### From `git_log` (14)

#### Fix: [FIX] noupdate on user-tunable data records (3 modules)
<!-- source: git_log ref: df70ee69435fdfe180aa7565634eb91a0e62da0a occ: 1 conf: 0.60 -->

Commit `df70ee6943` (2026-05-01): [FIX] noupdate on user-tunable data records (3 modules)

#### Fix: [FIX] rfid_service_base, rfid_service_portal: Update imports for Odoo 19
<!-- source: git_log ref: 8ebc6e2c318211ee2fb4067bf9c63e1014da13c4 occ: 1 conf: 0.60 -->

Commit `8ebc6e2c31` (2025-12-19): [FIX] rfid_service_base, rfid_service_portal: Update imports for Odoo 19

#### Fix: Fix SQL constraint error message formatting in rfid_service_sale.py
<!-- source: git_log ref: 3e1885ed8b786b13f08967a1ee838b53b9cb58b8 occ: 1 conf: 0.60 -->

Commit `3e1885ed8b` (2025-04-02): Fix SQL constraint error message formatting in rfid_service_sale.py

#### Fix: Fix translation for unique service constraint message
<!-- source: git_log ref: 8edeb568321b77e6ae138e228a08a6fbe644cbd4 occ: 1 conf: 0.60 -->

Commit `8edeb56832` (2025-03-31): Fix translation for unique service constraint message

#### Fix: fixes ported from 17.0
<!-- source: git_log ref: 09608db8432b463a8cd496ebd68466c4e2d85fdd occ: 1 conf: 0.60 -->

Commit `09608db843` (2024-10-15): fixes ported from 17.0

#### Fix: Fix mail composer params to 17.0
<!-- source: git_log ref: e581c4e6b22f83d84fa5b9940411f221344de81b occ: 1 conf: 0.60 -->

Commit `e581c4e6b2` (2024-09-25): Fix mail composer params to 17.0

#### Fix: fix security and bugs
<!-- source: git_log ref: 7e2b0572afbec926f266101e2fd2970826651c7b occ: 1 conf: 0.60 -->

Commit `7e2b0572af` (2024-09-18): fix security and bugs

#### Fix: fix security and bugs
<!-- source: git_log ref: 88d8f7cf6fc51259fe4ea5ec240d594f6ef38627 occ: 1 conf: 0.60 -->

Commit `88d8f7cf6f` (2024-09-13): fix security and bugs

#### Fix: fix re-issue old un-active cards
<!-- source: git_log ref: 9220189542611d05382fb5bd78e3997f7731883c occ: 1 conf: 0.60 -->

Commit `9220189542` (2024-07-07): fix re-issue old un-active cards

#### Fix: fix re-issue old un-active cards
<!-- source: git_log ref: 08425a7d0349555d4821c6551beccb1b10dcce67 occ: 1 conf: 0.60 -->

Commit `08425a7d03` (2024-07-07): fix re-issue old un-active cards

#### Fix: fix operator rights
<!-- source: git_log ref: a3f5bdc3f4ee3b2d0bb84f552da4faab3510d19c occ: 1 conf: 0.60 -->

Commit `a3f5bdc3f4` (2024-06-25): fix operator rights

#### Fix: fix demo data
<!-- source: git_log ref: 58a6b16e4f7ed7d16b8aeae4c43541ea51f5b263 occ: 1 conf: 0.60 -->

Commit `58a6b16e4f` (2023-09-26): fix demo data

#### Fix: fix demo data
<!-- source: git_log ref: 9fe5aa23d7d75f6ae0e3c1d3541884c7ec12536d occ: 1 conf: 0.60 -->

Commit `9fe5aa23d7` (2023-09-26): fix demo data

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M
<!-- source: git_log ref: 3c84986ac48326833d2f41e4de1d121e3c526130 occ: 1 conf: 0.60 -->

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/rfid_service_base`
- Source digest: `sha256:836d6ead9b8933e24830e8a54e25e71f4612c24c0dc237191d7a92ab0114708d`
- Generated at: `2026-05-14T11:16:43+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
