---
id: hr_rfid_vending
title: RFID Vending Control
module: hr_rfid_vending
module_version: 19.0.1.7.12
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage EXECUTIVE based vending machines
last_updated: '2026-08-26'
source_digest: sha256:39dcdcb8b6b3c5d2bbff3e65b2f375fbba9281adbab7db195040463d59d2ef3b
depends:
- hr_rfid
- product
- hr_attendance
entities:
  primary: hr.rfid.vending.auto.refill
  related:
  - hr.rfid.vending.balance.history
  - hr.rfid.ctrl.cash.log
  - hr.rfid.ctrl.cash.wiz
  - digest.digest
  - hr.employee
  - hr.employee.vending.balance.wiz
  - hr.rfid.ctrl
  - hr.rfid.ctrl.vending.settings
  - hr.rfid.ctrl.vending.row
  - hr.rfid.vending.event
  - product.template
  - res.company
  - res.config.settings
  - hr.rfid.vending.event.reverse
keywords:
- auto
- balance
- based
- cash
- ctrl
- digest
- executive
- history
- log
- machines
- manage
- refill
- rfid
- vending
- wiz
license: AGPL-3
author: Polimex Dev Team
category: Vending
installable: true
application: false
auto_install: false
counts:
  models: 15
  views: 24
  access_rules: 12
  record_rules: 6
  crons: 1
  images: 2
images:
- path: static/description/icon.png
  sha256: sha256:77987aebeca562b297ef58e931ded619e6a61e24d4646145f68c972498adea75
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
- path: static/description/icon.svg
  sha256: sha256:853872438928af50d00d7003bc5075302a6fde2fcf7400c4b9ea1a33e0ec9ef7
  alt: Icon
  caption_generated_by: noop
  caption_prompt_version: v1
chunking:
  target_tokens: 500
  overlap_tokens: 75
  contextual_prefix_template: This chunk belongs to section '{section_title}' in Odoo module '{module}'
    v{module_version} (Odoo {odoo_version}), documenting {entities_primary}.
---


# RFID Vending Control - `hr_rfid_vending` v19.0.1.7.12

Manage EXECUTIVE based vending machines

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_vending`
- **Version**: `19.0.1.7.12`
- **Category**: Vending
- **License**: AGPL-3
- **Author**: Polimex Dev Team
- **Application**: no
- **Auto-install**: no
- **Installable**: yes
- **Depends on**: `hr_rfid`, `product`, `hr_attendance`

### README (verbatim)

#### RFID Vending Machine Integration

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-18.0.1.6.0-green.svg)](https://apps.odoo.com)

Complete vending machine management system integrated with RFID access control and employee accounts.

##### 🎯 Overview

RFID Vending integrates EXECUTIVE-based vending machines with Odoo's RFID system, enabling cashless transactions using employee RFID cards. It provides balance management, transaction tracking, automatic refills, and comprehensive reporting.

##### ✨ Key Features

###### Vending Management
- **Machine Configuration**: Support multiple vending machines
- **Product Mapping**: Link Odoo products to vending slots
- **Price Management**: Centralized pricing control
- **Stock Tracking**: Monitor product levels per machine

###### Employee Features
- **Card Balance**: Prepaid balance on RFID cards
- **Transaction History**: Complete purchase history
- **Auto-refill**: Automatic balance top-ups
- **Spending Limits**: Daily/monthly limits

###### Financial Control
- **Balance Management**: Add/deduct employee balances
- **Payroll Integration**: Deduct from salary
- **Subsidy System**: Company-subsidized products
- **Cash Collection**: Track physical cash removal

###### Reporting & Analytics
- **Sales Reports**: By product, employee, machine
- **Balance Reports**: Current balances, movements
- **Consumption Analysis**: Patterns and trends
- **Machine Performance**: Uptime, sales volume

##### 📋 Requirements

- Odoo 18.0+
- hr_rfid module installed
- EXECUTIVE vending machines with RFID readers
- Network connectivity to vending machines

###### Dependencies
```python
'depends': ['hr_rfid', 'product', 'hr']
```

##### 🛠️ Installation

1. Install hr_rfid module first

2. Install the vending module:
```bash
./odoo-bin -d your_database -i hr_rfid_vending
```

3. Configure vending controllers in RFID system

##### 🔧 Configuration

###### Vending Controller Setup

1. **Add Controller**
   - RFID → Configuration → Controllers
   - Select type: "Vending Machine"
   - Configure network settings

2. **Configure Products**
   - RFID → Vending → Machine Configuration
   - Map slots to Odoo products
   - Set prices per slot

3. **Enable on Employees**
   - HR → Employees → RFID tab
   - Check "Enable Vending"
   - Set initial balance

###### System Parameters

Configure in Settings → Technical → System Parameters:

```
#### Default balance for new employees
hr_rfid_vending.default_balance: 50.00

#### Maximum negative balance allowed
hr_rfid_vending.max_negative_balance: -10.00

#### Auto-refill settings
hr_rfid_vending.auto_refill_enabled: True
hr_rfid_vending.auto_refill_amount: 100.00
hr_rfid_vending.auto_refill_threshold: 10.00
```

###### Product Configuration

1. **Create Products**
   - Inventory → Products
   - Set as "Can be Sold"
   - Define vending price

2. **Map to Slots**
   - Vending → Machines → Select machine
   - Configure each slot/row
   - Assign product and capacity

##### 📖 Usage

###### Employee Perspective

1. **Check Balance**
   - Employee portal → My Vending Balance
   - View transaction history
   - Request balance top-up

2. **Make Purchase**
   - Scan RFID card at vending machine
   - Select product
   - Balance automatically deducted

3. **Top-up Balance**
   - Request through portal
   - Automatic refill when low
   - Manager approval for manual adds

###### Manager Functions

1. **Balance Management**
   - HR → Employees → Vending Balance
   - Add/deduct amounts
   - View employee history

2. **Machine Monitoring**
   - Vending → Machines
   - Check online status
   - View sales in real-time

3. **Reports**
   - Vending → Reports
   - Sales analysis
   - Balance movements
   - Product popularity

###### Accounting Integration

1. **Journal Entries**
   - Automatic entries for sales
   - Balance movements tracking
   - Cash collection reconciliation

2. **Payroll Deduction**
   - Monthly balance settlement
   - Automatic salary deduction
   - Detailed payslip lines

##### 🔌 API Integration

###### Vending Events

```python
#### Process vending transaction
POST /hr/rfid/vending/event
{
    "controller_id": "VEND001",
    "card_number": "1234567890",
    "slot": 5,
    "price": 2.50,
    "product_code": "COLA330"
}
```

###### Balance Operations

```python
#### Check balance
GET /api/vending/balance/{card_number}

#### Add balance
POST /api/vending/balance/add
{
    "employee_id": 123,
    "amount": 50.00,
    "reference": "Manual top-up"
}
```

##### 🐛 Troubleshooting

###### Common Issues

1. **Card not recognized**
   - Verify card is active in RFID system
   - Check vending enabled for employee
   - Confirm machine is online

2. **Insufficient balance**
   - Check current balance
   - Verify price configuration
   - Review negative balance settings

3. **Product not dispensing**
   - Check machine mechanical status
   - Verify product mapping
   - Review transaction logs

###### Machine Diagnostics

1. **Connection Test**
   - Vending → Machines → Test Connection
   - Check network settings
   - Verify controller status

2. **Event Logs**
   - Review vending events
   - Check for error codes
   - Monitor response times

##### ⚙️ Advanced Features

###### Auto-refill Rules

Configure automatic balance top-ups:

```python
#### In employee vending settings
auto_refill_enabled = True
auto_refill_amount = 100.00
auto_refill_threshold = 10.00
auto_refill_day = 1  # 1st of month
```

###### Subsidy System

Company-subsidized products:

```python
#### Product subsidy configuration
subsidy_percentage = 50  # Company pays 50%
employee_price = original_price * (1 - subsidy_percentage / 100)
```

###### Multi-Currency

Support for different currencies:
- Machine currency setting
- Automatic conversion
- Exchange rate updates

##### 📊 Reports

###### Standard Reports
- Daily sales summary
- Employee consumption report
- Product popularity analysis
- Machine revenue report

###### Financial Reports
- Balance movement report
- Payroll deduction summary
- Cash collection report
- Subsidy cost analysis

###### Custom Analytics
- Peak usage times
- Product preferences by department
- Machine utilization rates
- Predictive restocking

##### 🤝 Contributing

We welcome contributions:
1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request

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

- [User Manual](https://polimex.co/docs/rfid-vending)
- [Technical Documentation](https://github.com/polimex/odoo-apps/wiki)
- [Odoo Apps Store](https://apps.odoo.com/apps/modules/18.0/hr_rfid_vending/)

---

For more information, visit [polimex.co](https://polimex.co)


## Installation & Configuration <a id='install'></a>

Installation requirements and configuration entry points. Use this section to answer 'why won't the module install' questions.

```bash
./venv/bin/python odoo/odoo-bin -d DATABASE -i hr_rfid_vending --stop-after-init
```


## Models <a id='models'></a>
Each model below is an atomic concept: one H3 per model. Inherited models (extending core) are marked explicitly.

### `hr.rfid.vending.auto.refill` <a id='model-hr-rfid-vending-auto-refill'></a>
Python class `VendingAutoRefillEvents` in `models/auto_refill.py:16`.  Model.  Description: *Auto Refill Events*.  Default order: `id desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Name |  | ✓ | Auto-generated reference for each cron run (e.g. AR/2026/000123). Used as the hu |
| `company_id` | Many2one → \`res.company\` | Company |  | ✓ | Company in whose scope this refill run executed. Auto-refill is scheduled per co |
| `create_date` | Datetime | Auto Refill Time |  | ✓ | Timestamp the cron run created the record. Use this to correlate refill totals w |
| `auto_refill_total` | Float | Total Cash Refilled | ✓ | ✓ | Sum of all balance top-ups credited during this run. A useful sanity check again |
| `balance_history_ids` | One2many → \`hr.rfid.vending.balance.history\` | Balance History Changes |  | ✓ | Individual employee balance-history entries created by this run. Use them to see |

#### Notable methods

- **`auto_refill_job(self)`** - decorators: `@api.model`
  - effects: `log_info`, `log_warn`, `with_company`
  - touches: `res.company`
- **`_auto_refill(self)`** - decorators: `@api.model`
  - effects: `create`, `log_info`, `sudo`
  - touches: `hr.employee`, `hr.rfid.vending.balance.history`

### `hr.rfid.vending.balance.history` <a id='model-hr-rfid-vending-balance-history'></a>
Python class `BalanceHistory` in `models/balance_history.py:4`.  Model.  Description: *Balance history for employees*.  Default order: `id desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `name` | Char | Person Responsible/Item |  | - | Human-readable label — the operator who made the change for manual adjustments,  |
| `person_responsible` | Many2one → \`res.users\` | Person responsible for the change |  | ✓ | User who triggered the balance change. For vending sales this is the system user |
| `balance_change` | Float | Balance change | ✓ | ✓ | How much was deposited/withdrawn from the employee's balance |
| `balance_result` | Float | Balance result | ✓ | ✓ | How much the balance was after the change |
| `employee_id` | Many2one → \`hr.employee\` | Employee | ✓ | ✓ | Employee whose vending balance changed. Cascades on delete — when the employee r |
| `department_id` | Many2one → \`hr.department\` |  |  | ✓ | Department of the employee at the time of the change. Stored so reports filter c |
| `vending_event_id` | Many2one → \`hr.rfid.vending.event\` | Event |  | ✓ | Vending controller event that triggered the balance change (a sale or a sale rev |
| `auto_refill_id` | Many2one → \`hr.rfid.vending.auto.refill\` | Auto Refill Event |  | ✓ | Auto-refill cron run that produced this credit. Empty for manual top-ups and for |
| `item_id` | Many2one → \`product.template\` | Item Sold |  | ✓ | Product matching the item sold by the vending controller for this entry — copied |

### `hr.rfid.ctrl.cash.log` <a id='model-hr-rfid-ctrl-cash-log'></a>
Python class `CashCollectLog` in `models/ctrl_cash_collect_wizard.py:5`.  Model.  Description: *Cash Collect log from Vending Machines*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Vending Machine | ✓ | ✓ | Vending machine from which cash was collected. Set automatically based on the co |
| `currency_id` | Many2one → \`res.currency\` | Currency |  | ✓ | Currency used to record the collected amount — taken from the company default an |
| `value` | Monetary | Amount Collected | ✓ | ✓ | Amount of physical cash collected from the vending machine.          • Physical  |

### `hr.rfid.ctrl.cash.wiz` <a id='model-hr-rfid-ctrl-cash-wiz'></a>
Python class `CashCollectWiz` in `models/ctrl_cash_collect_wizard.py:37`.  TransientModel (wizard).  Description: *Wizard for Collect cash from Vending Machine*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `controller_ids` | Many2many → \`hr.rfid.ctrl\` | Vending Machines | ✓ | ✓ | Vending machines from which cash will be collected.          • Multiple machines |
| `currency_id` | Many2one → \`res.currency\` | Currency |  | ✓ | Currency used to record the collected amount — taken from the company default an |
| `value` | Monetary | Collection Amount | ✓ | ✓ | Amount of cash to collect from each selected vending machine.          • Per mac |

#### Notable methods

- **`collect(self)`** - decorators: -
  - effects: `message_post`, `raise:ValidationError`
  - touches: `hr.rfid.ctrl.cash.log`

### `digest.digest` <a id='model-digest-digest'></a>
Python class `Digest` in `models/digest.py:9`.  Model.  Inherits: `digest.digest`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `kpi_hr_rfid_vending_refill` | Boolean | Auto refill amount |  | ✓ | Include the total amount auto-refilled to employee balances in the digest email. |
| `kpi_hr_rfid_vending_sale` | Boolean | Sales amount |  | ✓ | Include the total amount of vending purchases (positive sum of debits) in the di |
| `kpi_hr_rfid_vending_sale_count` | Boolean | Sales count |  | ✓ | Include the count of individual purchases made through the vending controllers i |
| `kpi_hr_rfid_vending_refill_value` | Monetary |  |  | - | Live total of auto-refill credits added to employee balances during the digest w |
| `kpi_hr_rfid_vending_sale_value` | Monetary |  |  | - | Live total spent by employees through the vending controllers during the digest  |
| `kpi_hr_rfid_vending_sale_count_value` | Integer |  |  | - | Live count of individual vending purchases during the digest window. |

### `hr.employee` <a id='model-hr-employee'></a>
Python class `HrEmployee` in `models/hr_employee.py:7`.  Model.  Inherits: `hr.employee`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `hr_rfid_vending_balance` | Float | Vending Balance |  | ✓ | Company-provided balance for vending machine purchases.          • Purpose: Budg |
| `hr_rfid_vending_recharge_balance` | Float | Self Recharge Balance |  | ✓ | Personal balance loaded by the employee using their own money.          • Source |
| `hr_rfid_vending_negative_balance` | Boolean | Allow Negative Balance |  | ✓ | Allow employee to spend more than their current balance (credit system).         |
| `hr_rfid_vending_limit` | Float | Credit Limit |  | ✓ | Maximum debt amount when negative balance is allowed.          • Purpose: Set ma |
| `hr_rfid_vending_in_attendance` | Boolean | Require Active Attendance |  | ✓ | Restrict vending purchases to work hours only.          • When enabled: Employee |
| `hr_rfid_vending_daily_limit` | Float | Daily Spending Limit |  | ✓ | Maximum amount employee can spend per day on vending purchases.          • Purpo |
| `daily_limit_type` | Selection | Daily Limit Type |  | ✓ | How to calculate the daily spending period.          • Last 24 hours: Rolling 24 |
| `hr_rfid_vending_spent_today` | Monetary | Spent Today |  | - | Amount already spent today based on the daily limit type setting. Used to calcul |
| `hr_rfid_vending_current_balance` | Monetary | Available Balance |  | - | Total amount currently available for vending purchases. Combines company balance |
| `currency_id` | Many2one | Company Currency |  | - |  |
| `hr_rfid_vending_auto_refill` | Boolean | Enable Auto Refill |  | ✓ | Automatically add money to employee's vending balance on a monthly schedule.     |
| `hr_rfid_vending_refill_amount` | Monetary | Refill Amount |  | ✓ | Amount to add during each auto-refill cycle.          • Fixed type: Exact amount |
| `hr_rfid_vending_refill_type` | Selection | Refill Type |  | ✓ | How the auto-refill amount is applied to the employee's balance.          • Fixe |
| `hr_rfid_vending_refill_max` | Monetary | Refill Maximum |  | ✓ | Maximum balance that auto-refill will maintain (only for 'Up To' refill type).   |
| `hr_rfid_vending_balance_history` | One2many → \`hr.rfid.vending.balance.history\` | Balance History |  | ✓ | Complete history of all balance changes including purchases, refills, manual adj |

#### Notable methods

- **`employee_vending_balance_history_action(self)`** - decorators: -
  - effects: `sudo`
- **`_compute_current_balance(self)`** - decorators: `@api.depends`
- **`_compute_spend_today(self)`** - decorators: `@api.depends`
  - touches: `hr.rfid.vending.balance.history`
- **`get_employee_balance(self, controller=None)`** - decorators: -
- **`hr_rfid_vending_add_to_balance(self, value, ev=0)`** - decorators: -
  - Add to the balance of an employee
  - touches: `hr.rfid.vending.balance.history`
- **`hr_rfid_vending_set_balance(self, value, max_add=0, min_add=0, ev=0)`** - decorators: -
  - Set an employee's balance to a specific number, with the option of max_add
  - touches: `hr.rfid.vending.balance.history`
- **`hr_rfid_vending_purchase(self, cost, ev=0)`** - decorators: -
  - Purchase a product. Subtracts the parameter "cost" from the employee's balance

### `hr.employee.vending.balance.wiz` <a id='model-hr-employee-vending-balance-wiz'></a>
Python class `VendingBalanceWiz` in `models/hr_employee_wizards.py:6`.  TransientModel (wizard).  Description: *Employee balance setter*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `employee_ids` | Many2many → \`hr.employee\` | Employees | ✓ | ✓ | Select employees whose vending balances will be modified.          • Multiple se |
| `value` | Float | Amount | ✓ | ✓ | Amount to add, subtract, or set for the selected employees' vending balances.    |

#### Notable methods

- **`add_value(self)`** - decorators: -
  - effects: `raise:ValidationError`
- **`subtract_value(self)`** - decorators: -
  - effects: `raise:ValidationError`
- **`set_value(self)`** - decorators: -
  - effects: `message_post`, `raise:ValidationError`

### `hr.rfid.ctrl` <a id='model-hr-rfid-ctrl'></a>
Python class `HrRfidControllerVending` in `models/hr_rfid_ctrl.py:4`.  Model.  Inherits: `hr.rfid.ctrl`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `show_price_timeout` | Integer | Price Display Timeout |  | - | Duration (in seconds) that product prices remain visible on the vending machine  |
| `scale_factor` | Integer | Price Scale Factor |  | - | Multiplier used to convert currency amounts to vending machine units.          • |
| `cash_contained` | Float | Cash in Machine |  | ✓ | Current amount of physical cash stored in the vending machine.          • Purpos |
| `pricelist_id` | Many2one → \`product.pricelist\` | Product Pricelist |  | ✓ | Pricelist used to determine product prices for this vending machine.          •  |

#### Notable methods

- **`_convert_balance_to_ctrl(self, balance)`** - decorators: `@api.model`
- **`create_vending_rows(self)`** - decorators: -
  - touches: `hr.rfid.ctrl.vending.row`
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - touches: `hr.rfid.ctrl.vending.row`

### `hr.rfid.ctrl.vending.settings` <a id='model-hr-rfid-ctrl-vending-settings'></a>
Python class `HrRfidVendingSettingsWiz` in `models/hr_rfid_ctrl_settings.py:5`.  TransientModel (wizard).  Description: *Vending Machine Settings*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `controller_id` | Many2one → \`hr.rfid.ctrl\` |  | ✓ | ✓ | Vending controller being configured. Set automatically from the active record wh |
| `vending_row_ids` | Many2many → \`hr.rfid.ctrl.vending.row\` | Item/Price | ✓ | ✓ | The 4-slot rows of the vending machine grid. Editing the products here writes a  |
| `show_price_timeout` | Integer | Show Price Timeout | ✓ | ✓ | Seconds the vending controller keeps the product price on its screen after the u |
| `scale_factor` | Integer | Scale Factor | ✓ | ✓ | Divisor used to encode product prices in the controller (price in stotinki ÷ sca |

#### Notable methods

- **`save_settings(self)`** - decorators: -
  - effects: `raise:ValidationError`

### `hr.rfid.ctrl.vending.row` <a id='model-hr-rfid-ctrl-vending-row'></a>
Python class `HrRfidVendingRow` in `models/hr_rfid_ctrl_vending_row.py:5`.  Model.  Description: *Vending Machine Row*.  Default order: `row_num`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `row_num` | Integer |  | ✓ | ✓ | Row index inside the vending machine grid (1-based). Each row holds 4 item slots |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` |  | ✓ | ✓ | Vending controller this row belongs to. Cascade on delete — rows do not survive  |
| `item_number1` | Char | Slot 1 Number |  | - | Number the buyer presses on the machine keypad for the first slot of this row, c |
| `item_number2` | Char | Slot 2 Number |  | - | Number the buyer presses on the machine keypad for the second slot of this row. |
| `item_number3` | Char | Slot 3 Number |  | - | Number the buyer presses on the machine keypad for the third slot of this row. |
| `item_number4` | Char | Slot 4 Number |  | - | Number the buyer presses on the machine keypad for the fourth slot of this row. |
| `item1` | Many2one → \`product.template\` | Item#1 |  | ✓ | Product mapped to the first slot of this row. Determines the name shown on the c |
| `item2` | Many2one → \`product.template\` | Item#2 |  | ✓ | Product mapped to the second slot of this row. |
| `item3` | Many2one → \`product.template\` | Item#3 |  | ✓ | Product mapped to the third slot of this row. |
| `item4` | Many2one → \`product.template\` | Item#4 |  | ✓ | Product mapped to the fourth slot of this row. |

### `hr.rfid.vending.event` <a id='model-hr-rfid-vending-event'></a>
Python class `VendingEvents` in `models/hr_rfid_vending_event.py:8`.  Model.  Inherits: `hr.rfid.event.user`.  Description: *RFID Vending Event*.  Default order: `id desc`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `event_action` | Selection | Event Type |  | ✓ | Type of vending machine event that occurred.          • Purchase Complete (47):  |
| `transaction_price` | Float | Transaction Amount |  | ✓ | Amount charged for this vending transaction.          • Currency: Uses machine's |
| `item_sold` | Integer | Item Slot Number |  | ✓ | Physical slot/position number in the vending machine where the item was located. |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Vending Machine |  | ✓ | RFID controller/vending machine where this event occurred.          • Location t |
| `command_id` | Many2one → \`hr.rfid.command\` | System Response |  | ✓ | System command sent to the vending machine in response to this event.  • Communi |
| `item_sold_id` | Many2one → \`product.template\` | Product Purchased |  | ✓ | Product that was purchased in this vending transaction.          • Product track |
| `input_js` | Char | Raw Event Data |  | ✓ | Original JSON data received from the vending machine hardware.          • Debugg |

#### Notable methods

- **`create(self, vals_list)`** - decorators: `@api.model_create_multi`
  - calls `super() `create``
- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
- **`search(self, *args, **kwargs)`** - decorators: `@api.model`
  - calls `super() `search``

### `product.template` <a id='model-product-template'></a>
Python class `ProductTemplate` in `models/product_template.py:4`.  Model.  Inherits: `product.template`.

#### Notable methods

- **`write(self, vals)`** - decorators: -
  - calls `super() `write``
  - effects: `with_context`
  - touches: `hr.rfid.ctrl.vending.row`, `hr.rfid.ctrl.vending.settings`

### `res.company` <a id='model-res-company'></a>
Python class `ResCompany` in `models/res_company.py:4`.  Model.  Inherits: `res.company`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `refill_interval_number` | Integer |  |  | ✓ | Repeat every x. |
| `refill_interval_type` | Selection | Interval Unit |  | ✓ | Time unit for the auto-refill repeat interval. Combined with Repeat every (above |
| `refill_nextcall` | Datetime | Next Execution Date |  | ✓ | Next planned execution date for this refill. |

### `res.config.settings` <a id='model-res-config-settings'></a>
Python class `ResConfigSettings` in `models/res_config_settings.py:4`.  TransientModel (wizard).  Inherits: `res.config.settings`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `refill_interval_number` | Integer |  |  | - | Repeat every x. |
| `refill_interval_type` | Selection | Interval Unit |  | - | Time unit for the auto-refill repeat interval. Combined with Repeat every (above |
| `refill_nextcall` | Datetime | Next Execution Date |  | - | Next planned execution date for this refill. |

#### Notable methods

- **`get_values(self)`** - decorators: `@api.model`
  - calls `super() `get_values``
- **`set_values(self)`** - decorators: -
  - calls `super() `set_values``

### `hr.rfid.vending.event.reverse` <a id='model-hr-rfid-vending-event-reverse'></a>
Python class `VendingEventReverse` in `wizards/vending_event_reverse.py:7`.  TransientModel (wizard).  Description: *Reverse Vending Purchase*.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `event_id` | Many2one → \`hr.rfid.vending.event\` |  | ✓ | ✓ | Vending event being reversed. Set automatically from the active record when the  |
| `reason` | Text | Reason | ✓ | ✓ | Audit note explaining why the purchase is reversed (machine jam, double-charge,  |

#### Notable methods

- **`action_reverse(self)`** - decorators: -
  - effects: `message_post`, `raise:UserError`


## Module Constants <a id='constants'></a>

No module-level UPPER_CASE constants are declared by this module.


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`HrRfidVending.post_event(self, **post)`** (`@http.route`) - `controllers/main.py:22`
  - super-split (super): pre=- · post=`log_error`, `log_info`, `with_company`, `with_context`
  - effects: `log_error`, `log_info`, `with_company`, `with_context`
  - touches: `hr.rfid.card`, `hr.rfid.command`, `hr.rfid.ctrl.vending.row`, `hr.rfid.event.system`, `hr.rfid.vending.event`
- **`fc(a, b)`** - `tests/test_auto_refill_cron.py:30`
- **`TestAutoRefillCron.setUpClass(cls)`** (`@classmethod`) - `tests/test_auto_refill_cron.py:39`
  - calls `super()`
  - touches: `hr.rfid.vending.auto.refill`, `hr.rfid.vending.balance.history`
- **`TestAutoRefillCron.test_cron_skips_when_nextcall_in_future(self)`** - `tests/test_auto_refill_cron.py:75`
  - Future nextcall: cron must not modify balances.
- **`TestAutoRefillCron.test_cron_runs_when_nextcall_in_past(self)`** - `tests/test_auto_refill_cron.py:89`
  - Past nextcall: cron must run and advance the timestamp.
- **`TestAutoRefillCron.test_cron_skips_when_nextcall_is_null(self)`** - `tests/test_auto_refill_cron.py:105`
  - Companies with no refill_nextcall set must be skipped, not crash.
- **`TestAutoRefillCron.test_cron_advances_nextcall_even_when_no_employees_match(self)`** - `tests/test_auto_refill_cron.py:117`
  - Empty cohort still advances nextcall — otherwise the cron loops.
- **`TestAutoRefillCron.test_cron_idempotent_within_interval(self)`** - `tests/test_auto_refill_cron.py:125`
  - Second pass within interval must NOT refill again.
- **`TestAutoRefillCron.test_fixed_sets_balance_up_to_amount(self)`** - `tests/test_auto_refill_cron.py:147`
  - fixed: balance < refill_amount → set to refill_amount.
- **`TestAutoRefillCron.test_fixed_sets_balance_down_to_amount(self)`** - `tests/test_auto_refill_cron.py:161`
  - fixed: balance > refill_amount → balance is RESET DOWN.
- **`TestAutoRefillCron.test_fixed_no_op_when_balance_equals_amount(self)`** - `tests/test_auto_refill_cron.py:179`
  - fixed: balance == refill_amount → no change, no audit row.
- **`TestAutoRefillCron.test_fixed_restores_from_negative_balance(self)`** - `tests/test_auto_refill_cron.py:200`
  - fixed with negative balance (employee within credit limit) → set
- **`TestAutoRefillCron.test_up_to_starts_from_zero_tops_to_max(self)`** - `tests/test_auto_refill_cron.py:224`
  - up_to from zero, amount >= max → top to max.
- **`TestAutoRefillCron.test_up_to_partial_when_amount_smaller_than_gap(self)`** - `tests/test_auto_refill_cron.py:238`
  - up_to: amount < (max - balance) → add only amount, not full max.
- **`TestAutoRefillCron.test_up_to_caps_when_amount_overshoots(self)`** - `tests/test_auto_refill_cron.py:254`
  - up_to: amount > gap → only fill the gap, never overshoot max.
- **`TestAutoRefillCron.test_up_to_no_op_when_balance_at_max(self)`** - `tests/test_auto_refill_cron.py:269`
  - up_to: balance == max → no change.
- **`TestAutoRefillCron.test_up_to_no_op_when_balance_above_max(self)`** - `tests/test_auto_refill_cron.py:284`
  - up_to: balance > max (e.g. left over from prior config) → no change.
- **`TestAutoRefillCron.test_filter_excludes_auto_refill_off(self)`** - `tests/test_auto_refill_cron.py:303`
  - auto_refill = False → never touched.
- **`TestAutoRefillCron.test_filter_excludes_zero_amount(self)`** - `tests/test_auto_refill_cron.py:317`
  - refill_amount = 0 → search filter excludes; no history written.
- **`TestAutoRefillCron.test_filter_excludes_archived_employees(self)`** - `tests/test_auto_refill_cron.py:335`
  - active=False employees must NOT be refilled — search defaults to active=True.
- **`TestAutoRefillCron.test_multicompany_each_company_advances_independently(self)`** - `tests/test_auto_refill_cron.py:354`
  - Each company's nextcall advances independently. Refill of one
  - touches: `res.company`
- **`TestAutoRefillCron.test_multicompany_refill_does_not_leak_across_companies(self)`** - `tests/test_auto_refill_cron.py:388`
  - Even when both companies are due, employee balances must not be
  - touches: `res.company`
- **`TestAutoRefillCron.test_audit_row_created_when_at_least_one_refill(self)`** - `tests/test_auto_refill_cron.py:422`
  - One non-empty pass → exactly one hr.rfid.vending.auto.refill row.
- **`TestAutoRefillCron.test_no_audit_row_when_nothing_changed(self)`** - `tests/test_auto_refill_cron.py:436`
  - If every employee was already at target, no audit row is created.
- **`TestAutoRefillCron.test_history_rows_link_back_to_audit(self)`** - `tests/test_auto_refill_cron.py:452`
  - Every balance_history row from the pass has auto_refill_id set
- **`TestAutoRefillCron.test_total_refill_aggregates_across_multiple_employees(self)`** - `tests/test_auto_refill_cron.py:468`
  - auto_refill_total is sum of all per-employee balance_change values.
- **`TestAutoRefillCron.test_mixed_cohort_processes_each_correctly(self)`** - `tests/test_auto_refill_cron.py:488`
  - Multiple employees with mixed types and edge states in one pass —
- **`TestAutoRefillCron.test_changing_amount_triggers_reset_on_next_cycle(self)`** - `tests/test_auto_refill_cron.py:558`
  - If admin changes refill_amount mid-month, the next cycle must
- **`TestAutoRefillCron.test_switching_type_fixed_to_up_to_keeps_balance(self)`** - `tests/test_auto_refill_cron.py:580`
  - Switching type from fixed → up_to mid-flight: existing balance
- **`TestVendingEventMultiCompanyRule.setUpClass(cls)`** (`@classmethod`) - `tests/test_multi_company_rules.py:29`
  - super-split (super): pre=- · post=`with_context`
  - effects: `with_context`
  - touches: `res.company`, `res.users`
- **`TestVendingEventMultiCompanyRule.test_own_company_event_visible(self)`** - `tests/test_multi_company_rules.py:99`
  - Sanity: an event on a company-A webstack stays visible to a
- **`TestVendingEventMultiCompanyRule.test_no_company_webstack_event_visible(self)`** - `tests/test_multi_company_rules.py:107`
  - Regression: an event whose controller->webstack chain ends in
- **`TestVendingEventMultiCompanyRule.test_other_company_event_stays_hidden(self)`** - `tests/test_multi_company_rules.py:116`
  - Loosening for False must NOT leak other companies' events.
- **`fc(a, b)`** - `tests/test_vending_e2e.py:15`
  - Shorthand float_compare with 2 decimal precision.
- **`TestVendingE2E.setUp(self)`** - `tests/test_vending_e2e.py:26`
  - calls `super()`
- **`TestVendingE2E.test_01_ev64_balance_request_grant(self)`** - `tests/test_vending_e2e.py:202`
  - Full flow: add balance → ev64 → DB2 response with correct balance.
- **`TestVendingE2E.test_02_ev64_deny_zero_balance(self)`** - `tests/test_vending_e2e.py:217`
  - Zero balance → deny (empty response), event still created.
- **`TestVendingE2E.test_03_ev47_purchase_deducts_balance(self)`** - `tests/test_vending_e2e.py:229`
  - Purchase: balance decreases, history record created, event logged.
- **`TestVendingE2E.test_04_ev47_cash_purchase_increases_cash_contained(self)`** - `tests/test_vending_e2e.py:251`
  - Cash purchase (no card) increases machine cash_contained.
- **`TestVendingE2E.test_05_ev50_self_recharge(self)`** - `tests/test_vending_e2e.py:267`
  - Self recharge: employee adds personal money via machine.
- **`TestVendingE2E.test_06_combined_balance_in_ev64(self)`** - `tests/test_vending_e2e.py:283`
  - ev64 returns sum of company + personal balance.
- **`TestVendingE2E.test_07_daily_limit_caps_balance(self)`** - `tests/test_vending_e2e.py:298`
  - Daily limit restricts available balance in ev64.
- **`TestVendingE2E.test_08_daily_limit_exhausted_after_purchase(self)`** - `tests/test_vending_e2e.py:313`
  - After spending daily limit, next ev64 returns deny.
- **`TestVendingE2E.test_09_negative_balance_with_credit_limit(self)`** - `tests/test_vending_e2e.py:330`
  - Negative balance allowed up to credit limit.
- **`TestVendingE2E.test_10_attendance_not_checked_in_deny(self)`** - `tests/test_vending_e2e.py:345`
  - Employee with attendance check but not checked in → deny.
- **`TestVendingE2E.test_11_purchase_overflows_to_personal_balance(self)`** - `tests/test_vending_e2e.py:358`
  - Purchase exceeding company balance uses credit, verified via ev64.
- **`TestVendingE2E.test_12_auto_refill_fixed(self)`** - `tests/test_vending_e2e.py:381`
  - Fixed auto refill sets balance to refill_amount.
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`TestVendingE2E.test_13_auto_refill_up_to(self)`** - `tests/test_vending_e2e.py:399`
  - Up-to refill tops up balance to refill_max, not beyond.
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`TestVendingE2E.test_14_auto_refill_up_to_no_refill_when_full(self)`** - `tests/test_vending_e2e.py:422`
  - Up-to refill does nothing when balance >= max.
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`TestVendingE2E.test_15_purchase_links_product(self)`** - `tests/test_vending_e2e.py:443`
  - Purchase event links correct product.template via slot mapping.
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`TestVendingE2E.test_16_balance_history_audit_trail(self)`** - `tests/test_vending_e2e.py:464`
  - Each balance change creates a history record with correct data.
- **`TestVendingE2E.test_17_cash_collect_wizard(self)`** - `tests/test_vending_e2e.py:486`
  - Cash collect wizard zeroes out machine cash_contained.
  - effects: `with_context`
  - touches: `hr.rfid.ctrl.cash.wiz`
- **`TestVendingE2E.test_18_full_purchase_lifecycle(self)`** - `tests/test_vending_e2e.py:509`
  - Complete lifecycle: add balance → purchase → refill → purchase.
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`TestVendingE2E.test_19_multiple_employees_isolated(self)`** - `tests/test_vending_e2e.py:555`
  - Purchases by one employee don't affect another's balance.
- **`TestVendingE2E.test_20_unknown_card_deny(self)`** - `tests/test_vending_e2e.py:588`
  - Unknown card gets deny, no events or balance changes.
- **`TestVendingE2E.test_21_reversal_restores_balance(self)`** - `tests/test_vending_e2e.py:611`
  - Reversal of purchase restores balance, verified via ev64.
- **`TestVendingE2E.test_22_reversal_creates_history(self)`** - `tests/test_vending_e2e.py:635`
  - Reversal creates positive balance_history linked to same event.
  - touches: `hr.rfid.vending.balance.history`
- **`TestVendingE2E.test_23_double_reversal_blocked(self)`** - `tests/test_vending_e2e.py:656`
  - Cannot reverse an already reversed event.
- **`TestVendingE2E.test_24_reversal_non_purchase_blocked(self)`** - `tests/test_vending_e2e.py:670`
  - Cannot reverse non-purchase events.
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`TestVendingE2E.test_25_reversal_restores_daily_limit(self)`** - `tests/test_vending_e2e.py:685`
  - Reversal within same day neutralizes daily spend.
- **`TestVendingEv64.setUp(self)`** - `tests/test_vending_ev64.py:13`
  - calls `super()`
- **`TestVendingEv64.test_ev64_card_not_found(self)`** - `tests/test_vending_ev64.py:62`
  - Card unknown to system -> deny (empty response), no vending event.
- **`TestVendingEv64.test_ev64_card_inactive(self)`** - `tests/test_vending_ev64.py:70`
  - Inactive card -> deny, no vending event.
- **`TestVendingEv64.test_ev64_employee_not_checked_in(self)`** - `tests/test_vending_ev64.py:79`
  - Employee with attendance check enabled but not checked in -> deny.
- **`TestVendingEv64.test_ev64_zero_balance(self)`** - `tests/test_vending_ev64.py:88`
  - Employee with zero balance -> deny, vending event created.
- **`TestVendingEv64.test_ev64_grant_with_balance(self)`** - `tests/test_vending_ev64.py:99`
  - Employee with balance -> grant (DB2 command with balance).
  - effects: `with_context`
- **`TestVendingEv64.test_ev49_vend_fail_creates_system_event(self)`** - `tests/test_vending_ev64.py:120`
  - VEND FAIL (ev49) -> creates system event.
  - touches: `hr.rfid.event.system`
- **`TestVendingEv64.test_vending_init_skips_ff(self)`** - `tests/test_vending_ev64.py:133`
  - Vending controller init sequence should NOT include FF command.
  - touches: `hr.rfid.command`
- **`VendingController.test_vending_functionality(self)`** - `tests/test_vending_functionality.py:13`
- **`TestVendingKeyAuth.setUp(self)`** - `tests/test_vending_key_auth.py:26`
  - calls `super()`
- **`TestVendingKeyAuth.test_wrong_key_rejected(self)`** - `tests/test_vending_key_auth.py:63`
  - A forged event with the wrong key is rejected: no vending event, no
- **`TestVendingKeyAuth.test_correct_key_reaches_vending(self)`** - `tests/test_vending_key_auth.py:77`
  - The same event WITH the correct key passes authentication and reaches
- **`TestVendingKeyAuth.test_no_convertor_delegates_without_crash(self)`** - `tests/test_vending_key_auth.py:89`
  - A POST with no 'convertor' (raw/barcode device) must not crash the

### Private helpers

- **`TestAutoRefillCron._make_employee(self, name, company=None, **vending_vals)`** - `tests/test_auto_refill_cron.py:54`
  - touches: `hr.employee`
- **`TestAutoRefillCron._set_company_due(self, company=None)`** - `tests/test_auto_refill_cron.py:61`
- **`TestAutoRefillCron._set_company_future(self, company=None)`** - `tests/test_auto_refill_cron.py:66`
- **`TestVendingEventMultiCompanyRule._make_event_chain(cls, label, company_id, serial)`** (`@classmethod`) - `tests/test_multi_company_rules.py:65`
  - Build webstack -> controller -> reader -> vending event.
  - touches: `hr.rfid.ctrl`, `hr.rfid.reader`, `hr.rfid.vending.event`, `hr.rfid.webstack`
- **`TestVendingEventMultiCompanyRule._visible_ids(self)`** - `tests/test_multi_company_rules.py:94`
  - touches: `hr.rfid.vending.event`
- **`TestVendingE2E._setup_products(self)`** - `tests/test_vending_e2e.py:31`
  - Create products and configure vending machine slots.
  - effects: `with_context`
  - touches: `hr.rfid.ctrl.vending.settings`, `product.template`
- **`TestVendingE2E._ev64(self, card_number=None, ctrl_id=None)`** - `tests/test_vending_e2e.py:76`
  - Send ev64 (balance request) from vending machine.
- **`TestVendingE2E._ev47(self, product_slot, price_units, change_units=0, card_number=None, ctrl_id=None)`** - `tests/test_vending_e2e.py:96`
  - Send ev47 (purchase complete) from vending machine.
- **`TestVendingE2E._ev50(self, price_units, change_units=0, card_number=None, ctrl_id=None)`** - `tests/test_vending_e2e.py:123`
  - Send ev50 (cash collect / self recharge) from vending machine.
- **`TestVendingE2E._assert_balance_response(self, response, expected_units)`** - `tests/test_vending_e2e.py:149`
  - Assert that ev64 response contains correct balance.
- **`TestVendingE2E._assert_deny(self, response)`** - `tests/test_vending_e2e.py:157`
  - Assert that ev64 response is a deny (empty).
- **`TestVendingE2E._vending_event_count(self)`** - `tests/test_vending_e2e.py:161`
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`TestVendingE2E._history_count(self, employee=None)`** - `tests/test_vending_e2e.py:166`
  - touches: `hr.rfid.vending.balance.history`
- **`TestVendingE2E._last_history(self, employee=None)`** - `tests/test_vending_e2e.py:172`
  - touches: `hr.rfid.vending.balance.history`
- **`TestVendingE2E._emp(self)`** - `tests/test_vending_e2e.py:178`
  - Shortcut to reload employee.
- **`TestVendingE2E._reset_employee(self, employee=None)`** - `tests/test_vending_e2e.py:183`
  - Reset employee vending state to zero for test isolation.
- **`TestVendingE2E._get_last_purchase_event(self)`** - `tests/test_vending_e2e.py:598`
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`TestVendingE2E._reverse_event(self, event, reason='Test reversal')`** - `tests/test_vending_e2e.py:604`
  - Run the reversal wizard on an event.
  - effects: `with_context`
  - touches: `hr.rfid.vending.event.reverse`
- **`TestVendingEv64._ev64(self, card_number, ctrl_id=None, bos=1, tos=1)`** - `tests/test_vending_ev64.py:17`
  - Send ev64 (Cloud Card Request) and return parsed response.
- **`TestVendingEv64._ev49(self, card_number, ctrl_id=None)`** - `tests/test_vending_ev64.py:36`
  - Send ev49 (VEND FAIL) event.
- **`TestVendingEv64._vending_event_count(self)`** - `tests/test_vending_ev64.py:55`
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`VendingController._add_products(self, ctrl_id=None)`** - `tests/test_vending_functionality.py:24`
  - effects: `with_context`
  - touches: `hr.rfid.ctrl.vending.settings`, `product.template`
- **`VendingController._check_history_records_count(self, count)`** - `tests/test_vending_functionality.py:65`
  - touches: `hr.rfid.vending.balance.history`
- **`VendingController._check_balance(self, expected, ctrl_id=None)`** - `tests/test_vending_functionality.py:73`
- **`VendingController._balance_test(self, ctrl_id=None)`** - `tests/test_vending_functionality.py:101`
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`VendingController._sale_event(self, product, price_in_units, change_in_units=0, card_number=None, ctrl_id=None)`** - `tests/test_vending_functionality.py:142`
- **`VendingController._sale_test(self, ctrl_id=None)`** - `tests/test_vending_functionality.py:167`
  - effects: `with_company`
  - touches: `hr.rfid.vending.auto.refill`
- **`TestVendingKeyAuth._ev64_with_key(self, card_number, key)`** - `tests/test_vending_key_auth.py:34`
  - Send an ev64 (Cloud Card Request) signed with an explicit key.
- **`TestVendingKeyAuth._vending_event_count(self)`** - `tests/test_vending_key_auth.py:52`
  - effects: `sudo`
  - touches: `hr.rfid.vending.event`
- **`TestVendingKeyAuth._key_mismatch_sys_events(self)`** - `tests/test_vending_key_auth.py:57`
  - effects: `sudo`
  - touches: `hr.rfid.event.system`


## Views & Inheritance <a id='views'></a>

List of `ir.ui.view` records created or extended by this module.

| XML id | Model | Type | Inherit | File |
|---|---|---|---|---|
| `ctrl_cash_collect_log_view_form` | `hr.rfid.ctrl.cash.log` | - |  | `views/ctrl_cash_collect_log.xml` |
| `ctrl_cash_collect_log_view_tree` | `hr.rfid.ctrl.cash.log` | - |  | `views/ctrl_cash_collect_log.xml` |
| `ctrl_cash_collect_wizard_view_form` | `hr.rfid.ctrl.cash.wiz` | - |  | `views/ctrl_cash_collect_wizard.xml` |
| `digest_digest_view_form` | `digest.digest` | - | digest.digest_digest_view_form | `views/digest_views.xml` |
| `hr_employee_vending_balance_change_form` | `hr.employee.vending.balance.wiz` | - |  | `views/hr_employee_views.xml` |
| `hr_employee_vending_balance_set_form` | `hr.employee.vending.balance.wiz` | - |  | `views/hr_employee_views.xml` |
| `hr_rfid_employee_form_inherit_hr_rfid_vending` | `hr.employee` | - | hr.view_employee_form | `views/hr_employee_views.xml` |
| `hr_rfid_employee_view_tree_inherit_hr_rfid_vending` | `hr.employee` | - | hr.view_employee_tree | `views/hr_employee_views.xml` |
| `hr_rfid_ctrl_vending_prices_wiz` | `hr.rfid.ctrl.vending.settings` | - |  | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_ctrl_view_form_inherit_hr_rfid_vending` | `hr.rfid.ctrl` | - | hr_rfid.hr_rfid_controller_view_form | `views/hr_rfid_ctrl.xml` |
| `hr_rfid_vending_auto_refill_form` | `hr.rfid.vending.auto.refill` | - |  | `views/hr_rfid_vending_auto_refill.xml` |
| `hr_rfid_vending_auto_refill_tree` | `hr.rfid.vending.auto.refill` | - |  | `views/hr_rfid_vending_auto_refill.xml` |
| `hr_rfid_vending_auto_refill_search` | `hr.rfid.vending.auto.refill` | - |  | `views/hr_rfid_vending_auto_refill.xml` |
| `hr_rfid_vending_balance_history_form` | `hr.rfid.vending.balance.history` | - |  | `views/hr_rfid_vending_balance_history.xml` |
| `hr_rfid_vending_balance_history_tree` | `hr.rfid.vending.balance.history` | - |  | `views/hr_rfid_vending_balance_history.xml` |
| `hr_rfid_vending_balance_history_search` | `hr.rfid.vending.balance.history` | - |  | `views/hr_rfid_vending_balance_history.xml` |
| `hr_rfid_vending_balance_history_graph` | `hr.rfid.vending.balance.history` | - |  | `views/hr_rfid_vending_balance_history.xml` |
| `hr_rfid_vending_balance_history_pivot` | `hr.rfid.vending.balance.history` | - |  | `views/hr_rfid_vending_balance_history.xml` |
| `view_company_form_inherit_vending` | `res.company` | - | base.view_company_form | `views/res_company.xml` |
| `hr_rfid_vending_event_form` | `hr.rfid.vending.event` | - |  | `views/vending_event.xml` |
| `hr_rfid_vending_event_tree` | `hr.rfid.vending.event` | - |  | `views/vending_event.xml` |
| `hr_rfid_vending_event_search` | `hr.rfid.vending.event` | - |  | `views/vending_event.xml` |
| `hr_rfid_vending_event_pivot` | `hr.rfid.vending.event` | - |  | `views/vending_event.xml` |
| `hr_rfid_vending_event_graph` | `hr.rfid.vending.event` | - |  | `views/vending_event.xml` |

#### Sample XPath operations

- In `digest_digest_view_form`:
  - `//group[@name='kpi_general'] [after]`

- In `hr_rfid_employee_form_inherit_hr_rfid_vending`:
  - `//div[@name='button_box'] [inside]`

- In `hr_rfid_ctrl_view_form_inherit_hr_rfid_vending`:
  - `//header [inside]`
  - `//button[@id='hr_rfid_view_modify_io_table_btn'] [attributes]`
  - `//button[@id='hr_rfid_view_modify_io_table_btn'] [after]`
  - `//page[@name='debug'] [before]`

- In `view_company_form_inherit_vending`:
  - `//notebook [inside]`



## Security <a id='security'></a>

Who can do what. Answer access-related questions from this section.


**Groups defined**: `group_customer`, `group_operator`


### Access rights (ir.model.access)

| CSV id | Model | Group | R | W | C | D |
|---|---|---|---|---|---|---|

| `access_vending_balance_history_view_own_department_data` | `model_hr_rfid_vending_balance_history` | `hr_rfid.hr_rfid_view_own_department` | ✓ |  |  |  |

| `access_vending_balance_history_group_customer` | `model_hr_rfid_vending_balance_history` | `hr_rfid_vending.group_customer` | ✓ | ✓ | ✓ | ✓ |

| `access_vending_event_view_own_department_data` | `model_hr_rfid_vending_event` | `hr_rfid.hr_rfid_view_own_department` | ✓ |  |  |  |

| `access_vending_event_group_customer` | `model_hr_rfid_vending_event` | `hr_rfid_vending.group_customer` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_vending_row` | `model_hr_rfid_ctrl_vending_row` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_vending_auto_refill` | `model_hr_rfid_vending_auto_refill` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_employee_vending_balance_wiz` | `model_hr_employee_vending_balance_wiz` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_ctrl_vending_settings` | `model_hr_rfid_ctrl_vending_settings` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_ctrl_cash_wiz` | `hr_rfid_vending.model_hr_rfid_ctrl_cash_wiz` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_hr_rfid_ctrl_cash_log` | `hr_rfid_vending.model_hr_rfid_ctrl_cash_log` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ |  |

| `access_vending_event_reverse_wiz` | `hr_rfid_vending.model_hr_rfid_vending_event_reverse` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |

| `access_product_template_vending_operator` | `model_product_template` | `hr_rfid_vending.group_operator` | ✓ | ✓ | ✓ | ✓ |


### Record rules (ir.rule)

- **`ir_rule_hr_rfid_vending_event_user_multi_company`** on `model_hr_rfid_vending_event` - perms=`R`, groups=`global`, domain=`['|', '|', ('controller_id', '=', False), ('controller_id.webstack_id.company_id', '=', False), ('controller_id.webstack_id.company_id', 'in', company_ids)]`
- **`ir_rule_hr_rfid_vending_balance_history_multi_company`** on `model_hr_rfid_vending_balance_history` - perms=`R`, groups=`global`, domain=`[
                '|',
                '|', ('employee_id.company_id', 'in', company_ids), ('employee_id.company_id', '=', False),
                '|', ('item_id.company_id', 'in', company_ids), ('item_id.company_id', '=', False)
            ]`
- **`ir_rule_hr_rfid_vending_auto_refill_multi_company`** on `model_hr_rfid_vending_auto_refill` - perms=`R`, groups=`global`, domain=`[('company_id', 'in', company_ids)]`
- **`hr_rfid_vending_operator_department_vending_events_rule`** on `hr_rfid_vending.model_hr_rfid_vending_event` - perms=`RD`, groups=`global`, domain=`
        [('employee_id.department_id.id','=',user.employee_ids.department_id.id)]
      `
- **`hr_rfid_group_operator_vending_events_rule`** on `hr_rfid_vending.model_hr_rfid_vending_event` - perms=`RD`, groups=`global`, domain=`[(1,'=',1)] `
- **`hr_rfid_vending_department_vending_balance_history_rule`** on `hr_rfid_vending.model_hr_rfid_vending_balance_history` - perms=`RD`, groups=`global`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_rfid_vending_employees_auto_refill`** (HR RFID Vending: Employees Auto Refill) on `model_hr_rfid_vending_auto_refill`, runs every 10 minutes, active=True

### Data records summary

- `hr.rfid.vending.event`: 5 record(s)
- `product.template`: 4 record(s)
- `hr.rfid.vending.balance.history`: 4 record(s)
- `hr.employee`: 3 record(s)
- `ir.sequence`: 2 record(s)
- `hr.rfid.ctrl.vending.row`: 2 record(s)
- `ir.cron`: 1 record(s)
- `product.pricelist`: 1 record(s)
- `hr.rfid.ctrl`: 1 record(s)
- `hr.rfid.reader`: 1 record(s)
- `res.company`: 1 record(s)
- `hr.rfid.card`: 1 record(s)
- `hr.rfid.event.system`: 1 record(s)
- `hr.rfid.vending.auto.refill`: 1 record(s)
- `hr.rfid.ctrl.cash.log`: 1 record(s)


## UI & Frontend <a id='assets'></a>

This module ships no frontend assets (no JavaScript, SCSS, OWL components or QWeb templates).


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

### From `code_comments` (9)

#### TODO: Move into function "deal_with_ev_64"

**TODO** in `controllers/main.py:115`

> Move into function "deal_with_ev_64"

#### TODO: Move into function "deal_with_ev_47"

**TODO** in `controllers/main.py:158`

> Move into function "deal_with_ev_47"

#### TODO: Reduce item quantity

**TODO** in `controllers/main.py:225`

> Reduce item quantity

#### TODO: Move into function "deal_with_err_evs"

**TODO** in `controllers/main.py:237`

> Move into function "deal_with_err_evs"

#### TODO: What type of error?

**TODO** in `models/hr_rfid_vending_event.py:17`

> What type of error?

#### TODO: What type of error?

**TODO** in `models/hr_rfid_vending_event.py:18`

> What type of error?

#### TODO: What type of error?

**TODO** in `models/hr_rfid_vending_event.py:19`

> What type of error?

#### TODO: Replace this search() override with a proper ir.rule for group_custome

**TODO** in `models/hr_rfid_vending_event.py:298`

> Replace this search() override with a proper ir.rule for group_customer.

#### TODO: Add this event if happend

**TODO** in `tests/test_vending_functionality.py:10`

> Add this event if happend

### From `git_log` (73)

#### Fix: fix(hr_rfid): green the vending + tour tests broken by three prior chang

Commit `b5dfd0bc1f` (2026-07-22): fix(hr_rfid): green the vending + tour tests broken by three prior changes

#### Fix: [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

Commit `93125c7183` (2026-06-11): [FIX] hr_rfid/vending/ip_cam: authenticate hardware & camera webhooks

#### Fix: [FIX] hr_rfid family: multi-company rules — global records + broken M2O 

Commit `a58ac6f455` (2026-06-11): [FIX] hr_rfid family: multi-company rules — global records + broken M2O chains were hidden

#### Fix: [FIX] hr_rfid_vending: diagnostic logging + sudo() guard for auto_refill

Commit `cb95baba9e` (2026-05-01): [FIX] hr_rfid_vending: diagnostic logging + sudo() guard for auto_refill cron

#### Fix: [FIX] hr_rfid_vending: persist cron interval changes across upgrades

Commit `2c77712f8c` (2026-05-01): [FIX] hr_rfid_vending: persist cron interval changes across upgrades

#### Fix: [TEST] hr_rfid_vending: Add ev64 flow tests and fix init sequence

Commit `27d717a56e` (2026-04-03): [TEST] hr_rfid_vending: Add ev64 flow tests and fix init sequence

#### Fix: [IMP] hr_rfid_vending: Fix lazy log formatting and type comparison

Commit `ffabeb6b6e` (2026-04-03): [IMP] hr_rfid_vending: Fix lazy log formatting and type comparison

#### Fix: [FIX] hr_rfid_vending: Fix singleton error on search with auth=none

Commit `aae51e92e6` (2026-04-03): [FIX] hr_rfid_vending: Fix singleton error on search with auth=none

#### Fix: [FIX] hr_rfid_vending: Restore TODO comment removed by mistake

Commit `8ff6c6f7a2` (2026-04-03): [FIX] hr_rfid_vending: Restore TODO comment removed by mistake

#### Fix: [IMP] hr_rfid_vending: Upgrade logging from debug to info level

Commit `84db2e0a9a` (2026-04-03): [IMP] hr_rfid_vending: Upgrade logging from debug to info level

#### Fix: [FIX] hr_rfid,hr_rfid_vending: Add readonly=False to hardware routes and

Commit `1309fee0a8` (2026-04-03): [FIX] hr_rfid,hr_rfid_vending: Add readonly=False to hardware routes and fix onboarding access

#### Fix: [FIX] hr_rfid_vending: Replace deprecated read_group with _read_group

Commit `544cae5015` (2026-03-31): [FIX] hr_rfid_vending: Replace deprecated read_group with _read_group

#### Fix: [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher

Commit `57aba8363e` (2026-03-19): [MIG] all: Migrate hardware routes to Odoo 19 Json2Dispatcher

#### Fix: [FIX] all: Replace deprecated self._cr with self.env.cr

Commit `f0f152c3e0` (2026-03-18): [FIX] all: Replace deprecated self._cr with self.env.cr

#### Fix: [FIX] all: Replace deprecated self._context with self.env.context

Commit `c2b001ba20` (2026-02-16): [FIX] all: Replace deprecated self._context with self.env.context

#### Fix: fix license

Commit `6e49a3ef0c` (2024-09-09): fix license

#### Fix: FIX: Stop balance for archived employees and fix balance with self-charg

Commit `ece161eb61` (2023-12-05): FIX: Stop balance for archived employees and fix balance with self-charge

#### Fix: Fix for shifted sales data

Commit `7e85e39f18` (2023-10-16): Fix for shifted sales data

#### Fix: fix product rights for vending operators

Commit `9971e59c33` (2023-09-19): fix product rights for vending operators

#### Fix: fix vending event 48,49

Commit `b4e2645783` (2023-09-13): fix vending event 48,49

#### Fix: fix vending event 48,49

Commit `eb59550e45` (2023-09-13): fix vending event 48,49

#### Fix: vending fix spend today

Commit `cf2e3f2cb9` (2023-08-08): vending fix spend today

#### Fix: vending fix cron

Commit `065fada151` (2023-08-07): vending fix cron

#### Fix: vending fix daly balance

Commit `5c9f902bc0` (2023-08-07): vending fix daly balance

#### Fix: v2.1 Added portal functionality, barcode generation and RFID services. M

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_vending`
- Source digest: `sha256:39dcdcb8b6b3c5d2bbff3e65b2f375fbba9281adbab7db195040463d59d2ef3b`
- Generated at: `2026-08-26T11:07:13+00:00`
- Generator: `polimex_module_knowledge`
