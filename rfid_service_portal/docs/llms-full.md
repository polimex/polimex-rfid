---
id: rfid_service_portal
title: RFID Services Portal
module: rfid_service_portal
module_version: 19.0.0.2.4
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: "\n        RFID Service System Portal plugin\n    "
last_updated: '2026-11-16'
source_digest: sha256:b0b464fac255aea18ff26e2f09a708b160e7c4d980cf88b577e1ef96e42c6894
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


# RFID Services Portal - `rfid_service_portal` v19.0.0.2.4


        RFID Service System Portal plugin
    

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `rfid_service_portal`
- **Version**: `19.0.0.2.4`
- **Category**: Generic Modules/Property Management System
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: yes
- **Installable**: yes
- **Depends on**: `rfid_service_base`, `hr_rfid_portal`

### README (verbatim)

====================
RFID Services Portal
====================

Overview
========

The portal side of RFID Services. A customer who was sold a service at the
till and has a portal login sees their services under **RFID Services** in
the portal, and the cashier can send the customer the badge or a portal
invitation from the sale form.

It adds nothing to configure and is installed automatically when both RFID
Services (``rfid_service_base``) and the RFID portal (``hr_rfid_portal``)
are installed.

Configuration
=============

Nothing to configure. The customer needs a portal login to see the list of
their services; the cashier can send the invitation while selling (see
Usage).

Usage
=====

For the customer
----------------

* The portal home page shows the card **RFID Services** with the number of
  services sold to the customer.
* **RFID Services** lists them, the newest first: the reference of the sale,
  the service, from when and until when it is valid, the visits counted on it
  and its state (Registered, Active, Finished or Canceled). The hours are
  shown on the customer's own clock.
* A badge shared with the customer opens as a page with the barcode of the
  card and the period the card is valid for. The link carries its own access
  key, so it opens without a login.

For the cashier
---------------

On the sale form of a service:

* **Invite in Portal**, next to the e-mail: when ticked, the customer gets an
  invitation to the portal by e-mail as soon as the sale is confirmed. The
  box appears once an e-mail is filled in.
* **Share**: confirms the sale and opens the sharing dialog, with the
  customer already chosen, to send them the link to their badge. It is shown
  for services that issue a barcode card, once an e-mail or a phone number is
  filled in, and it needs the e-mail.

Technical
=========

* ``/my/rfid_services`` (login required) - the sales of the logged-in user's
  contact (``rfid.service.sale`` by ``partner_id``).
* ``/my/rfid_service<card id>`` - the badge page of a card
  (``hr_rfid_portal.portal_my_barcode``) for whoever holds the card's access
  token. The link **Share** sends is the RFID portal's own
  (``/my/webcard/<card id>``, with the same token).
* ``rfid.service.sale.wiz`` gains ``invite_in_portal`` and ``share_card``;
  the invitation is core's portal access wizard (``portal.wizard.user``,
  ``action_grant_access``).
* The demo data gives the demo login a badge and a service that has ended;
  the RFID Demo Data module (``hr_rfid_demo``) keeps a running one next to
  it.

Credits
=======

Authors
-------

* Polimex Dev Team

Maintainers
-----------

This module is maintained by Polimex Holding Ltd. - https://polimex.co


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i rfid_service_portal --stop-after-init
```

> **Auto-install**: Odoo installs it by itself only in an operation that installs one of `rfid_service_base`, `hr_rfid_portal` while the rest of them are installed or installed in the same operation. A database that already has all of them does not get it by itself - not on an upgrade (`-u`), not on Update Apps List: install it once from Apps or with the command above.


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `rfid.service.sale.wiz` <a id='model-rfid-service-sale-wiz'></a>
Python class `RfidServiceBaseSaleWiz` in `models/rfid_service_sale_wiz.py:14`.  TransientModel (wizard).  Inherits: `rfid.service.sale.wiz`.  Description: *Base RFID Service Sale Wizard*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `invite_in_portal` | Boolean | Invite in Portal |  | ✓ | When checked, the visitor receives a portal access invitation by email right aft |

#### Notable methods

- **`share_card(self)`** - decorators: -
  - effects: `raise:UserError`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`ProjectCustomerPortal.portal_my_services(self, access_token=None, p=1, **kw)`** (`@http.route`) - `controllers/portal.py:17`
  - effects: `sudo`
  - touches: `rfid.service.sale`
- **`ProjectCustomerPortal.portal_my_service(self, card_id, access_token=None, **kw)`** (`@http.route`) - `controllers/portal.py:28`

### Private helpers

- **`ProjectCustomerPortal._prepare_home_portal_values(self, counters)`** - `controllers/portal.py:9`
  - super-split (super): pre=- · post=`sudo`
  - effects: `sudo`
  - touches: `rfid.service.sale`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `sale_wiz_form_inherit` | `rfid.service.sale.wiz` | - | rfid_service_base.sale_wiz_form | `views/rfid_service_sale_wiz.xml` |

#### Sample XPath operations

- In `sale_wiz_form_inherit`:
  - `//button[@name='email_card'] [after]`
  - `//field[@name='email'] [replace]`



## Security <a id='security'></a>

This module does not declare any access rules, record rules or groups of its own. It relies entirely on permissions inherited from its dependencies.


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Data records summary

- `hr.rfid.card`: 1 record(s)
- `rfid.service.sale`: 1 record(s)


## UI & Frontend <a id='assets'></a>

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**QWeb templates in XML data, rendered by the server** (3): `portal_layout`, `portal_my_home`, `portal_rfid_service_sale_table`



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

### From `git_log` (5)

#### Fix: fix(demo): showcase demo files must be noupdate=1 - production -u ...

Commit `54843cfc81` (2026-07-22): fix(demo): showcase demo files must be noupdate=1 - production -u re-wrote them

#### Fix: [FIX] drop test-framework import from module __init__ (A1)

Commit `d392540045` (2026-06-01): [FIX] drop test-framework import from module __init__ (A1)

#### Fix: [TEST] rfid_service_portal: HttpCase regression for the auth=user fix

Commit `18e6d40de8` (2026-05-03): [TEST] rfid_service_portal: HttpCase regression for the auth=user fix

#### Fix: [FIX] rfid_service_portal: /my/rfid_services must require login ...

Commit `231d084502` (2026-05-03): [FIX] rfid_service_portal: /my/rfid_services must require login (auth=user)

#### Fix: fix portal views for 18.0

Commit `0456b88c40` (2024-10-07): fix portal views for 18.0


## Source provenance <a id='provenance'></a>

- Module: `rfid_service_portal`
- Source digest: `sha256:b0b464fac255aea18ff26e2f09a708b160e7c4d980cf88b577e1ef96e42c6894`
- Generated at: `2026-11-16T14:31:05+00:00`
- Generator: `polimex_module_knowledge`
