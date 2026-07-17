---
id: rfid_service_portal
title: RFID Services Portal
module: rfid_service_portal
module_version: 19.0.0.1.0
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        RFID Service System Portal plugin\n    "
last_updated: '2026-04-29'
source_digest: sha256:ccf7f1beec84f9b0620fff7a43f552ca0e341ffe343f2d63206308dd7170416a
depends:
- rfid_service_base
- hr_rfid_portal
entities:
  primary: rfid.service.sale.wiz
  related: []
keywords:
- plugin
- portal
- rfid
- sale
- service
- system
- wiz
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: true
application: false
auto_install: true
counts:
  models: 1
  views: 1
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:46b13bab71b79fd0e1a751c93a8e73761b41ea986fa356d5c1d393905b7da5f2
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:8d0bb5cc7f5bd3b0c62cefd86cb83a479525bb0bce4e29dded4baeadfc0a161c
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Services Portal — `rfid_service_portal` v19.0.0.1.0


        RFID Service System Portal plugin
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_portal`
- **Version**: `19.0.0.1.0`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: yes
- **Installable**: yes
- **Depends on**: `rfid_service_base`, `hr_rfid_portal`

### README (verbatim)

#### RFID Services Portal

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.0.1.0-green.svg)](https://apps.odoo.com)

Portal extension for RFID service management and self-service visitor registration.

##### 🎯 Overview

RFID Services Portal extends the RFID service system with portal functionality, enabling self-service visitor registration, service purchases, and badge management through a web interface. Perfect for visitor management systems that require minimal staff intervention.

##### ✨ Key Features

###### Self-Service Portal
- **Service Selection**: Browse available services
- **Online Registration**: Visitor self-registration
- **Badge Generation**: Instant badge creation
- **Email Delivery**: Automatic badge sending

###### Service Catalog
- **Public Services**: Display available services
- **Pricing Display**: Transparent pricing
- **Service Details**: Duration, access levels
- **Terms & Conditions**: Accept before purchase

###### Visitor Features
- **Quick Registration**: Minimal required fields
- **Badge Preview**: See badge before completion
- **Multiple Services**: Purchase several services
- **Receipt Generation**: Instant confirmation

###### Integration
- **Portal Framework**: Extends Odoo portal
- **Payment Options**: Online payment ready
- **Multi-language**: Full translation support
- **Mobile Responsive**: Works on all devices

##### 📋 Requirements

- Odoo 18.0+
- rfid_service_base module
- portal module (Odoo standard)
- website module (Odoo standard)

###### Dependencies
```python
'depends': ['rfid_service_base', 'portal', 'website']
```

##### 🛠️ Installation

1. Install rfid_service_base first

2. Install the portal module:
```bash
./odoo-bin -d your_database -i rfid_service_portal
```

3. Configure public services

##### 🔧 Configuration

###### Portal Setup

1. **Enable Public Access**
   - Settings → Website → RFID Services
   - Enable "Public Service Portal"
   - Configure terms & conditions

2. **Service Configuration**
   - Mark services as "Available in Portal"
   - Set public pricing
   - Add service descriptions
   - Upload service images

3. **Registration Form**
   - Configure required fields
   - Add custom fields if needed
   - Set validation rules
   - Configure email templates

###### Security Settings

```python
#### Portal access configuration
portal_allow_anonymous = True  # Allow without login
portal_require_email_verification = True
portal_max_services_per_session = 5
portal_session_timeout = 30  # minutes
```

##### 📖 Usage

###### Visitor Experience

1. **Access Portal**
   - Navigate to /my/services
   - Or direct link from website
   - No login required (configurable)

2. **Select Service**
   - Browse service catalog
   - View service details
   - Check pricing and duration
   - Add to cart

3. **Registration**
   - Fill visitor information
   - Upload photo (optional)
   - Accept terms
   - Submit registration

4. **Receive Badge**
   - Preview on screen
   - Download PDF
   - Receive via email
   - Print if needed

###### Service Catalog Display

Services are displayed with:
- Service name and icon
- Duration (1 day, 1 week, etc.)
- Access areas included
- Price (if applicable)
- Available spots (if limited)

###### Registration Flow

```
Select Service → Enter Details → Preview Badge → Confirm → Receive Badge
     ↓               ↓               ↓             ↓           ↓
   Catalog      Registration    Validation    Payment    Email/Download
```

##### 🎨 Customization

###### Portal Templates

Customize the look and feel:

```xml
<!-- Inherit service catalog template -->
<template id="portal_services_custom" inherit_id="rfid_service_portal.portal_my_services">
    <xpath expr="//div[@class='service-card']" position="attributes">
        <attribute name="class">service-card custom-style</attribute>
    </xpath>
    <xpath expr="//div[@class='service-description']" position="after">
        <div class="custom-features">
            <!-- Add custom content -->
        </div>
    </xpath>
</template>
```

###### Custom Fields

Add fields to registration:

```python
class ServiceSaleWizard(models.TransientModel):
    _inherit = 'rfid.service.sale.wiz'
    
    # Add custom fields
    company_name = fields.Char('Company')
    purpose_of_visit = fields.Selection([
        ('meeting', 'Business Meeting'),
        ('interview', 'Job Interview'),
        ('delivery', 'Delivery'),
        ('contractor', 'Contractor Work'),
    ])
    host_employee = fields.Many2one('hr.employee', 'Host')
```

###### Styling

Add custom CSS:

```css
/* In static/src/scss/portal_services.scss */
.service-portal {
    .service-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }
    
    .service-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 20px;
        transition: all 0.3s ease;
        
        &:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
    }
}
```

##### 🔒 Security Features

###### Validation
- Email verification
- Phone number validation
- Duplicate detection
- Blacklist checking

###### Rate Limiting
- Registration limits
- IP-based throttling
- Session management
- CAPTCHA integration

###### Data Protection
- Minimal data collection
- Automatic data expiry
- GDPR compliance
- Secure badge generation

##### 🔌 API Integration

###### External Registration

```python
@http.route('/api/service/register', type='json', auth='public', methods=['POST'])
def api_register_visitor(self, **kwargs):
    # Validate input
    required_fields = ['name', 'email', 'service_id']
    for field in required_fields:
        if field not in kwargs:
            return {'error': f'Missing required field: {field}'}
    
    # Create registration
    wizard = request.env['rfid.service.sale.wiz'].sudo().create({
        'partner_name': kwargs['name'],
        'email': kwargs['email'],
        'service_id': kwargs['service_id'],
    })
    
    # Process and return badge
    wizard.action_confirm()
    return {
        'success': True,
        'badge_url': wizard.get_badge_url(),
        'card_number': wizard.card_number,
    }
```

###### Webhook Notifications

```python
#### Notify external system on registration
def send_registration_webhook(self):
    webhook_url = self.env['ir.config_parameter'].get_param('rfid.portal.webhook')
    if webhook_url:
        requests.post(webhook_url, json={
            'visitor': self.partner_name,
            'service': self.service_id.name,
            'valid_from': self.start_date.isoformat(),
            'valid_to': self.end_date.isoformat(),
        })
```

##### 📱 Mobile Optimization

###### Responsive Design
- Touch-friendly interface
- Mobile-first approach
- Optimized forms
- QR code support

###### Progressive Web App
- Offline capability
- Install to homescreen
- Push notifications
- Camera integration

##### 🐛 Troubleshooting

###### Common Issues

1. **Services not showing**
   - Check "Available in Portal" flag
   - Verify service is active
   - Check access rights
   - Clear website cache

2. **Registration fails**
   - Check required fields
   - Verify email configuration
   - Review validation rules
   - Check server logs

3. **Badge not received**
   - Verify email settings
   - Check spam folder
   - Test email template
   - Review mail queue

###### Debug Mode

Enable portal debugging:
```python
#### In settings
portal_debug = True
portal_log_registrations = True
```

##### 📊 Analytics

Track portal usage:
- Service popularity
- Registration trends
- Conversion rates
- Error tracking
- User journey analysis

##### 🤝 Contributing

We welcome contributions:
1. Fork repository
2. Add portal features
3. Test responsive design
4. Submit pull request

##### 📄 License

Licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### 👥 Credits

###### Authors
- Polimex Dev Team

###### Maintainer
- [Polimex](https://polimex.co)

##### 🌐 Links

- [Documentation](https://polimex.co/docs/rfid-service-portal)
- [Live Demo](https://demo.polimex.co/my/services)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_portal/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_service_portal --stop-after-init
```

> **Auto-install**: installed automatically when all dependencies are present.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceBaseSaleWiz` in `models/rfid_service_sale_wiz.py:14`.  TransientModel (wizard).  Inherits: `rfid.service.sale.wiz`.  Description: *Base RFID Service Sale Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `invite_in_portal` | Boolean | Invite in Portal |  | ✓ |  |

#### Notable methods

- **`share_card(self)`** — decorators: —
  - effects: `raise:UserError`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`ProjectCustomerPortal.portal_my_services(self, access_token=None, p=1, **kw)`** (`@http.route`) — `controllers/portal.py:17`
  - effects: `sudo`
  - touches: `rfid.service.sale`
- **`ProjectCustomerPortal.portal_my_service(self, card_id, access_token=None, **kw)`** (`@http.route`) — `controllers/portal.py:30`

### Private helpers

- **`ProjectCustomerPortal._prepare_home_portal_values(self, counters)`** — `controllers/portal.py:9`
  - super-split (super): pre=— · post=`sudo`
  - effects: `sudo`
  - touches: `rfid.service.sale`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `sale_wiz_form_inherit` | `rfid.service.sale.wiz` | — | rfid_service_base.sale_wiz_form | `views/rfid_service_sale_wiz.xml` |

#### Sample XPath operations

- In `sale_wiz_form_inherit`:
  - `//button[@name='email_card'] [after]`
  - `//field[@name='email'] [replace]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

No XML data records or cron jobs are declared by this module.


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

### From `gotchas` (1)

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `validationerror`

### From `git_log` (3)

#### Fix: [FIX] rfid_service_base, rfid_service_portal: Update imports for Odoo 19
<!-- source: git_log ref: 8ebc6e2c318211ee2fb4067bf9c63e1014da13c4 occ: 1 conf: 0.60 -->

Commit `8ebc6e2c31` (2025-12-19): [FIX] rfid_service_base, rfid_service_portal: Update imports for Odoo 19

#### Fix: fix portal views for 18.0
<!-- source: git_log ref: 0456b88c4090ad8bee6edc0f540498c337080021 occ: 1 conf: 0.60 -->

Commit `0456b88c40` (2024-10-07): fix portal views for 18.0

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M
<!-- source: git_log ref: 3c84986ac48326833d2f41e4de1d121e3c526130 occ: 1 conf: 0.60 -->

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/rfid_service_portal`
- Source digest: `sha256:ccf7f1beec84f9b0620fff7a43f552ca0e341ffe343f2d63206308dd7170416a`
- Generated at: `2026-04-29T07:30:42+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
