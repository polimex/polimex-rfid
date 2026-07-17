---
id: rfid_service_zpl_labels_cups
title: Services ZPL Labels - CUPS Integration
module: rfid_service_zpl_labels_cups
module_version: 19.0.0.1.4
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        Replace direct ZPL printing with CUPS queue management\n    "
last_updated: '2026-04-30'
source_digest: sha256:f63fc069458ef87af158f0d919366c3fe6a6fbfad2ab007d110857cf1fdc793f
depends:
- rfid_service_zpl_labels
- base_report_to_label_printer
entities:
  primary: ir.actions.report
  related:
  - rfid.service
  - rfid.service.sale
  - rfid.service.sale.wiz
keywords:
- actions
- cups
- direct
- labels
- management
- printing
- queue
- replace
- report
- rfid
- sale
- service
- with
- wiz
- zpl
license: AGPL-3
author: Polimex Dev Team
category: Generic Modules/Property Management System
installable: false
application: false
auto_install: true
counts:
  models: 4
  views: 1
  access_rules: 0
  record_rules: 0
  crons: 0
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:d35990b9f1342df022cf0f86965095028973bd672e8cf6dd0db40cd5fc0a6042
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:f1371f335f70cd2125435e4082947a0f58fb48889ca1e2d457028b181cee6432
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# Services ZPL Labels - CUPS Integration — `rfid_service_zpl_labels_cups` v19.0.0.1.4


        Replace direct ZPL printing with CUPS queue management
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview — module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_zpl_labels_cups`
- **Version**: `19.0.0.1.4`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: yes
- **Installable**: no
- **Depends on**: `rfid_service_zpl_labels`, `base_report_to_label_printer`

### README (verbatim)

#### RFID Services ZPL Labels - CUPS Integration

This module provides seamless integration between RFID Service ZPL labels and the OCA printing framework.

##### Overview

When both `rfid_service_zpl_labels` and `base_report_to_label_printer` are installed, this module automatically activates to provide CUPS-based printing instead of direct socket printing.

##### Features

1. **Automatic Installation** - Installs automatically when both dependencies are present
2. **CUPS Integration** - Uses proper print queues and spooling
3. **User-based Printer Selection** - Respects each user's default label printer settings
4. **Fallback Support** - Can fall back to direct socket printing if needed
5. **CUPS Test Button** - Test CUPS printer configuration from RFID Service form

##### How It Works

###### Without This Module
- `rfid_service_zpl_labels` prints directly to printer via TCP socket
- No print queue management
- No user-specific printer settings

###### With This Module
- Printing goes through CUPS print server
- Users can configure their own label printer
- Print jobs are queued and managed properly
- ZPL report is marked as "label" type for automatic printer selection

##### Configuration

1. **Install Dependencies**
   ```bash
   # Install base modules first
   ./odoo-bin -d your_db --init=base_report_to_printer,base_report_to_label_printer
   
   # Install RFID ZPL labels
   ./odoo-bin -d your_db --init=rfid_service_zpl_labels
   
   # This module will auto-install
   ```

2. **Configure CUPS Server**
   - Settings → Technical → Printing → Servers
   - Add your CUPS server details

3. **Configure Label Printer**
   - Settings → Technical → Printing → Printers
   - Update printers from server
   - Each user sets their default label printer in preferences

##### Technical Details

###### Method Override

The module overrides the `print_label()` method in the wizard to use report action instead of direct socket printing:

```python
def print_label(self):
    # Create sale record
    sale_id = self._write_card()[0]
    
    # Use report action (will use label printer)
    return self.env.ref('rfid_service_zpl_labels.action_report_rfid_wristband').report_action(sale_id)
```

###### Report Configuration

The ZPL report is automatically marked as a "label" report:
```xml
<field name="label">True</field>
```

This ensures the report uses the user's configured label printer instead of their default printer.

###### CUPS Test Functionality

The module adds a "Test CUPS Printer" button to the RFID Service form:
- Creates a temporary test sale record
- Prints it through CUPS
- Deletes the test record
- Shows success/failure notification

###### Fallback Method

If CUPS printing fails, you can call the fallback method:
```python
#### From wizard instance
self.print_label_direct_fallback()
```

##### Benefits

1. **Print Queue Management** - Jobs are queued and can be monitored
2. **Multi-User Support** - Each user can have their own label printer
3. **Network Resilience** - CUPS handles network interruptions
4. **Print Status** - Can check if print job succeeded
5. **Printer Sharing** - Multiple users can share one printer

##### Troubleshooting

###### Module Not Auto-Installing

Check that both dependencies are installed:
```python
self.env['ir.module.module'].search([
    ('name', 'in', ['rfid_service_zpl_labels', 'base_report_to_label_printer']),
    ('state', '=', 'installed')
])
```

###### Printing Still Goes Direct

1. Verify this module is installed and active
2. Check that the report is marked as label type
3. Ensure user has a default label printer configured

###### CUPS Connection Issues

See the base_report_to_printer documentation for CUPS troubleshooting.

##### License

AGPL-3

##### Author

Polimex Dev Team


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_service_zpl_labels_cups --stop-after-init
```

> **Auto-install**: installed automatically when all dependencies are present.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `ir.actions.report` <a id='model-ir-actions-report'></a>
Python class `IrActionsReport` in `models/ir_actions_report.py:4`.  Model.  Inherits: `ir.actions.report`.

### `rfid.service` <a id='model-rfid-service'></a>
Python class `RfidServiceCups` in `models/rfid_service.py:8`.  Model.  Inherits: `rfid.service`.

#### Notable methods

- **`test_label_printer_connection(self)`** — decorators: —
  - Override the direct socket test to use CUPS instead.
- **`test_label_printer_connection_socket(self)`** — decorators: —
  - Fallback method for direct socket testing.
  - calls `super() `test_label_printer_connection``
- **`test_label_printer_cups(self)`** — decorators: —
  - Test CUPS label printer by printing a test label with failsafe values.
  - effects: `log_exception`, `log_info`, `raise:UserError`

### `rfid.service.sale` <a id='model-rfid-service-sale'></a>
Python class `RfidServiceSaleCups` in `models/rfid_service_sale.py:8`.  Model.  Inherits: `rfid.service.sale`.

#### Notable methods

- **`print_label_direct(self)`** — decorators: —
  - Override direct socket printing to use CUPS print queue.
  - effects: `log_exception`, `log_info`, `raise:UserError`
- **`print_label_direct_socket(self)`** — decorators: —
  - Fallback method for direct socket printing.
  - calls `super() `print_label_direct``

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceSaleWizCups` in `models/rfid_service_sale_wiz.py:8`.  TransientModel (wizard).  Inherits: `rfid.service.sale.wiz`.

#### Notable methods

- **`print_label(self)`** — decorators: —
  - Override to force CUPS printing directly.
  - effects: `log_error`, `log_info`, `raise:UserError`
- **`print_label_direct_fallback(self)`** — decorators: —
  - Fallback method that uses the original direct socket printing.
  - calls `super() `print_label_direct``


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

No module-level helper functions or install hooks are declared.


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `hr_rfid_service_sale_form_inherit_cups` | `rfid.service.sale` | — | rfid_service_zpl_labels.hr_rfid_service_sale_form_inherit_zpl_labels | `views/rfid_service_sale.xml` |

#### Sample XPath operations

- In `hr_rfid_service_sale_form_inherit_cups`:
  - `//button[@name='print_label_direct'] [attributes]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `ir.actions.report`: 1 record(s)
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

### From `git_log` (2)

#### Fix: [FIX] manifest validator issues flagged by Odoo Apps
<!-- source: git_log ref: 9a3d488b201a3d36dd71ae01c4b394d2ee8b8caf occ: 1 conf: 0.60 -->

Commit `9a3d488b20` (2026-04-21): [FIX] manifest validator issues flagged by Odoo Apps

#### Fix: Fix label printer selection to respect user preferences
<!-- source: git_log ref: d04571ed69fcdfa467d915ae5c7bd8925a2aaad2 occ: 1 conf: 0.60 -->

Commit `d04571ed69` (2025-10-07): Fix label printer selection to respect user preferences


## Source provenance <a id='provenance'></a>

- Module path: `/home/lubo/PycharmProjects/odoo19/custom-addons/polimex/rfid_service_zpl_labels_cups`
- Source digest: `sha256:f63fc069458ef87af158f0d919366c3fe6a6fbfad2ab007d110857cf1fdc793f`
- Generated at: `2026-04-30T10:42:53+00:00`
- Generator: `polimex_module_knowledge` (see `~/.claude/lib/polimex_module_knowledge/`)
