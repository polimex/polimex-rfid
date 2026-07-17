---
id: rfid_service_zpl_labels
title: Services ZPL Labels
module: rfid_service_zpl_labels
module_version: 19.0.1.0.1
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        ZPL wristband printing for RFID services with direct network printing\n    "
last_updated: '2026-04-29'
source_digest: sha256:e769d22fde73359d4c5eb4bbb91a73ed3eef7e1d33a7599016d766557a1bb571
depends:
- rfid_service_base
- hr_rfid
entities:
  primary: res.company
  related:
  - res.config.settings
  - rfid.service
  - rfid.service.sale
  - rfid.service.sale.wiz
keywords:
- company
- config
- direct
- labels
- network
- printing
- res
- rfid
- sale
- service
- services
- settings
- with
- wiz
- wristband
- zpl
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: true
application: false
auto_install: false
counts:
  models: 5
  views: 4
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:046c4a532ca85345872eb4dbc6aa05241b2fd80462b8d0e8366f5e0c8f7bee83
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:fa949c5a1583d838d0bea740191ef8f42dd7a41bb669134726b44895edd7465a
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Services ZPL Labels — `rfid_service_zpl_labels` v19.0.1.0.1


        ZPL wristband printing for RFID services with direct network printing
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_zpl_labels`
- **Version**: `19.0.1.0.1`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `rfid_service_base`, `hr_rfid`

### README (verbatim)

#### RFID Services ZPL Labels

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-875A7B.svg)](https://www.odoo.com/)
[![Module Version](https://img.shields.io/badge/Module_Version-18.0.1.0.0-success.svg)](https://github.com/polimex)

Professional ZPL wristband printing for RFID access control and visitor management systems.

##### Overview

The RFID Services ZPL Labels module extends Odoo's RFID service capabilities with enterprise-grade wristband printing functionality. Generate and print professional-quality wristbands directly to Zebra printers using native ZPL (Zebra Programming Language), perfect for visitor management, event registration, healthcare identification, and temporary access control.

###### ⚠️ Multi-User Environment Notice

For deployments with **multiple concurrent users**, install the companion module `rfid_service_zpl_labels_cups` to ensure:
- Proper print queue management
- Prevention of print job conflicts
- User-specific printer assignments
- Centralized print job tracking

Single-user installations can utilize the base module's direct socket printing capabilities.

##### Key Features

###### 🏷️ Wristband Generation
- **Native ZPL II Format** - Direct Zebra Programming Language output
- **Automatic Barcode Generation** - CODE-128 barcodes with service information
- **Flexible Templates** - Customizable wristband layouts via QWeb
- **Multiple Size Support** - Standard 1×11 inch and custom dimensions

###### 🖨️ Printing Capabilities
- **Direct Network Printing** - TCP/IP socket communication to Zebra printers
- **Company Branding** - Automatic inclusion of company logos and information
- **Dynamic Content** - Service type, validity dates, and access permissions
- **Visitor Information** - Name, ID, and custom fields support

###### 🔗 System Integration
- **RFID Service Integration** - Seamless operation with rfid_service_base
- **Batch Processing** - Print multiple wristbands in a single operation
- **Multi-Company Support** - Company-specific settings and branding
- **Portal Compatibility** - Full integration with service portal features

##### Requirements

###### System Requirements
- **Odoo**: Version 18.0 or higher
- **Python**: 3.8+
- **Dependencies**: `rfid_service_base`, `hr_rfid`
- **Hardware**: Zebra ZPL-compatible printer

###### Printing Infrastructure Options
| Method | Description | Best For |
|--------|-------------|----------|
| **Direct Socket** | TCP/IP communication | Single workstation |
| **CUPS Integration** | Linux print server | Multi-user environments |
| **Odoo IoT Box** | Official hardware solution | Cloud deployments |
| **File Export** | Save ZPL for manual printing | Testing/debugging |
| **OCA Modules** | Community printing solutions | Advanced setups |

##### Installation

###### Standard Installation

1. **Prerequisites**
   ```bash
   # Ensure rfid_service_base is installed
   ./odoo-bin -d your_database --init=rfid_service_base
   ```

2. **Module Installation**
   ```bash
   # Install the ZPL labels module
   ./odoo-bin -d your_database --init=rfid_service_zpl_labels
   ```

3. **Multi-User Setup** (if applicable)
   ```bash
   # Install CUPS integration for multi-user environments
   ./odoo-bin -d your_database --init=rfid_service_zpl_labels_cups
   ```

##### Configuration

###### Printer Setup

###### 1. Zebra Printer Configuration
- Enable ZPL command processing on your printer
- Configure network settings for TCP/IP printers
- Set appropriate DPI (203 or 300)
- Test connectivity with sample ZPL commands

###### 2. System Parameters (Odoo)
Navigate to **Settings → Technical → Parameters → System Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rfid_service.label_width` | 100 | Label width in mm |
| `rfid_service.label_height` | 50 | Label height in mm |
| `rfid_service.printer_dpi` | 203 | Printer resolution |
| `rfid_service.printer_ip` | - | Printer IP address |
| `rfid_service.printer_port` | 9100 | Printer port |

###### Wristband Specifications

**Standard Template**:
- **Dimensions**: 1×11 inches (25×279mm)
- **Resolution**: 203 DPI (8 dots/mm)
- **Orientation**: Portrait
- **Layout**: 4-column design with company branding


##### Usage

###### Printing Wristbands

###### Single Wristband Printing
1. Navigate to **RFID Services → Service Sales**
2. Open the desired service sale record
3. Click **"Print Label"** button
4. The wristband is sent directly to the configured printer

###### Batch Printing
1. Go to **RFID Services → Service Sales**
2. Select multiple service sale records
3. Choose **Action → Print Wristbands**
4. All selected wristbands print sequentially

###### Printing Methods

###### Method 1: Direct Socket Printing (Built-in)
The module includes direct socket printing functionality:
```python
#### Automatic when clicking "Print Label"
#### Sends ZPL directly to printer_ip:printer_port
```

###### Method 2: File Export
```bash
#### Linux - Using lpr
lpr -P zebra_printer wristband.zpl

#### Windows - Copy to printer share
copy wristband.zpl \\computer\zebra_printer

#### macOS - Using lp
lp -d zebra_printer wristband.zpl
```

###### Method 3: Python Script
```python
import socket

def send_zpl_to_printer(zpl_content, printer_ip="192.168.1.100", printer_port=9100):
    """Send ZPL data to network printer"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((printer_ip, printer_port))
        sock.send(zpl_content.encode('utf-8'))
    finally:
        sock.close()
```

##### ZPL Format Details

###### Sample ZPL Output
```zpl
^XA^CI28
^PW203 ^LL2233 ^LH0,0

; COLUMN 1: Company + Service Information
^FO90,150
^A0R,24,24^FDYour Company Name^FS
^FO60,150
^A0R,22,22^FDService Type^FS

; COLUMN 2: Visitor Name
^FO85,750
^A0R,30,30^FDVisitor Name^FS

; COLUMN 3: Barcode with Service ID
^FO60,1250
^BY2,2,80
^BCR,80,N,N,N
^FDService-ID-Here^FS

; COLUMN 4: Validity Period
^FO85,1800
^A0R,18,18^FDFrom: Date Time^FS
^FO55,1800
^A0R,18,18^FDTo: Date Time^FS

^XZ
```

###### Customizing the Template

The wristband layout is defined in `reports/report_wristband.xml` using QWeb syntax:

1. **Position Adjustment**: Modify `^FO` (Field Origin) coordinates
2. **Font Changes**: Adjust `^A` (Font) parameters
3. **Barcode Settings**: Configure `^BC` (Code 128) parameters
4. **Add Custom Fields**: Extend the template with additional data

##### API Reference

###### Programmatic Label Generation

```python
from odoo import models

class RfidServiceSale(models.Model):
    _inherit = 'rfid.service.sale'
    
    def generate_wristband_zpl(self):
        """Generate ZPL data for wristband"""
        self.ensure_one()
        report = self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband')
        zpl_data, _ = report.render_qweb_text(self.ids)
        return zpl_data  # Returns ZPL string
```

###### Extending Wristband Data

```python
from odoo import fields, models

class RfidServiceSaleCustom(models.Model):
    _inherit = 'rfid.service.sale'
    
    # Add custom fields that will appear on wristband
    wristband_color = fields.Selection([
        ('red', 'Red - VIP'),
        ('blue', 'Blue - Standard'),
        ('green', 'Green - Staff'),
    ], string='Wristband Color')
    
    emergency_contact = fields.Char('Emergency Contact')
    medical_info = fields.Text('Medical Information')
```

###### Direct Printing Method

```python
def print_label_direct(self):
    """Send label directly to configured printer"""
    for rec in self:
        zpl_data = rec.generate_wristband_zpl()
        # Send to printer using the service's print method
        rec.service_id.print_label_direct()
        # Log the printing action
        rec.message_post(body="Wristband printed successfully")
```

##### Troubleshooting

###### Common Issues

1. **Printer not receiving data**
   - Check printer network settings
   - Verify ZPL mode is enabled
   - Test with simple ZPL command

2. **Barcode not scanning**
   - Verify 10-digit card number
   - Check barcode symbology settings
   - Ensure proper quiet zones

3. **Text cut off**
   - Adjust label width (^PW command)
   - Check printer margins
   - Verify DPI settings

###### Debug Mode

Test ZPL output:
1. Print to file instead of printer
2. Use Labelary.com ZPL viewer
3. Check raw ZPL syntax

##### Advanced Features

###### Multiple Wristband Sizes

Add new paper formats:
```xml
<record id="paperformat_wristband_pediatric" model="report.paperformat">
    <field name="name">Pediatric Wristband</field>
    <field name="page_width">19</field>  <!-- 3/4 inch -->
    <field name="page_height">178</field> <!-- 7 inch -->
</record>
```

###### Dynamic Content

Add conditions in template:
```xml
<t t-if="sale.service_id.name == 'VIP Pass'">
    ^FO20,150^A0N,24,24^FDVIP ACCESS^FS
</t>
```

###### Multi-language Support

Template supports translations:
```xml
<t t-if="lang == 'en_US'">
    ^FO20,95^A0N,28,28^FDValid:^FS
</t>
<t t-else="">
    ^FO20,95^A0N,28,28^FDВалидно:^FS
</t>
```

##### Reports

The module provides:
- Wristband print history
- Service usage by wristband
- Failed print attempts log

##### Contributing

Contributions welcome:
1. Fork repository
2. Create feature branch
3. Test with real Zebra printer
4. Submit pull request

##### License

This module is licensed under AGPL-3.0. See [LICENSE](../LICENSE) for details.

##### Credits

###### Authors
- Polimex Dev Team

###### Contributors
- See [contributors](https://github.com/polimex/odoo-apps/contributors)

###### Maintainer
- [Polimex](https://polimex.co)

##### Links

- [ZPL Programming Guide](https://www.zebra.com/content/dam/zebra/manuals/printers/common/programming/zpl-zbi2-pm-en.pdf)
- [Labelary Online ZPL Viewer](http://labelary.com/viewer.html)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/rfid_service_zpl_labels/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_service_zpl_labels --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `res.company` <a id='model-res-company'></a>
Python class `Company` in `models/res_company.py:8`.  Model.  Inherits: `res.company`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `rfid_label_printer_ip` | Char | Label Printer IP |  | ✓ | IP address of the Zebra label printer for this company |
| `rfid_label_printer_port` | Integer | Label Printer Port |  | ✓ | TCP port for the Zebra label printer connection |

#### Notable methods

- **`_logo_as_grf(self, grf_name='COMPLOGO.GRF')`** — decorators: `@api.model`
  - Return (^XA~DG…^XZ) string ready to prepend to a ZPL job.

### `res.config.settings` <a id='model-res-config-settings'></a>
Python class `ResConfigSettings` in `models/res_config_settings.py:4`.  TransientModel (wizard).  Inherits: `res.config.settings`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `rfid_label_printer_ip` | Char | Label Printer IP |  | — | IP address of the Zebra label printer for wristband printing |
| `rfid_label_printer_port` | Integer | Label Printer Port |  | — | TCP port for the Zebra label printer connection (default: 9100) |

### `rfid.service` <a id='model-rfid-service'></a>
Python class `BaseRFIDService` in `models/rfid_service.py:12`.  Model.  Inherits: `rfid.service`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `label_template_id` | Many2one → \`ir.actions.report\` | Label Template |  | ✓ | Select the label template to use for printing labels/wristbands. |

#### Notable methods

- **`test_label_printer_connection(self)`** — decorators: —
  - Test the connection to the configured label printer.
  - effects: `log_exception`, `log_info`
- **`preview_label(self)`** — decorators: —
  - Preview the label template configured for this service.

### `rfid.service.sale` <a id='model-rfid-service-sale'></a>
Python class `RfidServiceSale` in `models/rfid_service_sale.py:12`.  Model.  Inherits: `rfid.service.sale`.

#### Notable methods

- **`preview_label(self)`** — decorators: —
  - Generate and preview the ZPL label for this service sale.
- **`print_label_direct(self)`** — decorators: —
  - Print the label directly to the configured ZPL printer.
  - effects: `log_exception`, `raise:UserError`

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceBaseSaleWiz` in `models/rfid_service_sale_wiz.py:11`.  TransientModel (wizard).  Inherits: `rfid.service.sale.wiz`.

#### Notable methods

- **`print_label(self)`** — decorators: —
  - Print label using the configured method (socket or CUPS if overridden)
- **`print_label_direct(self)`** — decorators: —
  - Print ZPL wristband label directly to printer.
  - effects: `log_exception`, `log_info`, `raise:UserError`
- **`test_printer_connection(self)`** — decorators: —
  - Test the connection to the configured label printer.


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`RfidLabelPreviewController.preview_label(self, sale_id, **kw)`** (`@http.route`) — `controllers/main.py:9`
  - Render the label preview page with Labelary integration.
  - touches: `rfid.service.sale`
- **`RfidLabelPreviewController.preview_service_label(self, service_id, **kw)`** (`@http.route`) — `controllers/main.py:46`
  - Render the label preview page for a service without sale data.
  - touches: `rfid.service`
- **`test_and_save_label(zpl_content, filename_prefix)`** — `tmp/analyze_label_issues.py:61`
  - Test ZPL with Labelary and save the result
  - effects: `http_get`
- **`test_labelary_api()`** — `tmp/test_labelary.py:34`
  - Test the ZPL template with Labelary API
  - effects: `http_get`
- **`test_label_format(zpl_content, label_size, dpmm, description)`** — `tmp/test_labelary_formats.py:9`
  - Test a specific label format
  - effects: `http_get`
- **`create_preview_html(zpl_content)`** — `tmp/test_odoo_preview.py:46`
  - Create an HTML preview page similar to Odoo's template
- **`test_odoo_preview()`** — `tmp/test_odoo_preview.py:184`
  - Test the preview as it would appear in Odoo
  - effects: `http_get`
- **`WristbandDesigner.create_template(self, filename='wristband_template.png')`** — `tmp/wristband_designer.py:32`
  - Create a design template with zones
- **`WristbandDesigner.generate_optimized_zpl(self)`** — `tmp/wristband_designer.py:93`
  - Generate an optimized ZPL design
- **`WristbandDesigner.test_design(self, zpl_content, design_name='test')`** — `tmp/wristband_designer.py:150`
  - Test a ZPL design and return the image
  - effects: `http_get`
- **`WristbandDesigner.create_comparison(self, designs)`** — `tmp/wristband_designer.py:174`
  - Create a visual comparison of designs
- **`ZPLDesigner.test_zpl(self, zpl_content, filename_prefix='test')`** — `tmp/zpl_design_tool.py:19`
  - Test ZPL and save the result
  - effects: `http_get`
- **`ZPLDesigner.create_design_grid(self, filename='design_grid.png')`** — `tmp/zpl_design_tool.py:57`
  - Create a design grid to help with positioning

### Private helpers

- **`WristbandDesigner.__init__(self)`** — `tmp/wristband_designer.py:12`
- **`ZPLDesigner.__init__(self)`** — `tmp/zpl_design_tool.py:12`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `res_config_settings_view_form_inherit_rfid_labels` | `res.config.settings` | — | base.res_config_settings_view_form | `views/res_config_settings_views.xml` |
| `view_rfid_service_form_inherit_new_group` | `rfid.service` | — | rfid_service_base.services_form | `views/rfid_service.xml` |
| `hr_rfid_service_sale_form_inherit_zpl_labels` | `rfid.service.sale` | — | rfid_service_base.hr_rfid_service_sale_form | `views/rfid_service_sale.xml` |
| `sale_wiz_form_inherit_label_button` | `rfid.service.sale.wiz` | — | rfid_service_base.sale_wiz_form | `views/rfid_service_sale_wiz.xml` |

#### Sample XPath operations

- In `res_config_settings_view_form_inherit_rfid_labels`:
  - `//form [inside]`

- In `view_rfid_service_form_inherit_new_group`:
  - `//group[@id='rfid_service_form_printing_templates'] [inside]`
  - `//header [inside]`

- In `hr_rfid_service_sale_form_inherit_zpl_labels`:
  - `//header/button[@name='print_card'] [after]`

- In `sale_wiz_form_inherit_label_button`:
  - `//button[@special='cancel'] [before]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `ir.config_parameter`: 2 record(s)
- `ir.actions.server`: 1 record(s)


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

### From `gotchas` (3)

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

#### Gotcha: SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, н
<!-- source: gotchas ref: /home/lubo/.claude/rules/odoo19-gotchas.md occ: 1 conf: 0.50 -->

From **Модели и полета** in odoo19-gotchas.md:

> SQL constraints (`models.Constraint`) предизвикват `IntegrityError`, не `ValidationError`

Matched tokens: `validationerror`

### From `git_log` (3)

#### Fix: [FIX] rfid_service_zpl_labels: invalid target='inline' in v19
<!-- source: git_log ref: ff2de74a0bb11daf6e28908e230b000f019b296e occ: 1 conf: 0.60 -->

Commit `ff2de74a0b` (2026-04-20): [FIX] rfid_service_zpl_labels: invalid target='inline' in v19

#### Fix: [FIX] hr_rfid,rfid_service_zpl_labels: Add forcecreate=False to ir.confi
<!-- source: git_log ref: 3a9ba0c116dcc504cb54b63bb913f9f88aec8553 occ: 1 conf: 0.60 -->

Commit `3a9ba0c116` (2026-03-31): [FIX] hr_rfid,rfid_service_zpl_labels: Add forcecreate=False to ir.config_parameter records

#### Fix: Fix variable name in ZPL content rendering
<!-- source: git_log ref: 74349691f386dfb78b026fc01701b36cad7f08ec occ: 1 conf: 0.60 -->

Commit `74349691f3` (2025-06-13): Fix variable name in ZPL content rendering


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/rfid_service_zpl_labels`
- Source digest: `sha256:e769d22fde73359d4c5eb4bbb91a73ed3eef7e1d33a7599016d766557a1bb571`
- Generated at: `2026-04-29T07:30:42+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
