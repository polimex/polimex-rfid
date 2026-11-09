---
id: hr_rfid_vending
title: RFID Vending Control
module: hr_rfid_vending
module_version: 19.0.1.7.14
odoo_version: '19.0'
odoo_edition: custom
doc_type: technical_reference
audience:
- administrator
- developer
companion_doc: llms.txt
summary: Manage EXECUTIVE based vending machines
last_updated: '2026-11-09'
source_digest: sha256:ffbc98011d8ee0ab14c766b66ed154ad069b333eac53a14b28627109c1a2420c
depends:
- hr_rfid
- product
- hr_attendance
entities:
  primary: hr.rfid.ctrl.vending.row
  related:
  - hr.rfid.vending.auto.refill
  - hr.rfid.vending.balance.history
  - hr.rfid.ctrl.cash.log
  - hr.rfid.ctrl.cash.wiz
  - digest.digest
  - hr.employee
  - hr.employee.vending.balance.wiz
  - hr.rfid.ctrl
  - hr.rfid.ctrl.vending.settings
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
- executive
- history
- log
- machines
- manage
- refill
- rfid
- row
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


# RFID Vending Control - `hr_rfid_vending` v19.0.1.7.14

Manage EXECUTIVE based vending machines

> **Audience: system administrators and developers.** End users who only configure and use the module should read [`llms.txt`](llms.txt) instead.


## Overview <a id='overview'></a>

Technical overview - module identity, license, dependencies and entry points. The matching end-user guide lives in `llms.txt`; anything below this section is sysadmin / developer territory.

- **Technical name**: `hr_rfid_vending`
- **Version**: `19.0.1.7.14`
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

###### Vending firmwares

The iCON180 vending board runs one of three firmwares, shown as the
controller's Hardware Type:

- **Vending** - Executive with a coin mechanism. Sells at the prices set in
  Odoo.
- **Vending Executive** - Executive only, no coin mechanism. Sells at the
  prices set in Odoo, exactly like Vending.
- **Vending MDB** - MDB cashless. The machine keeps its own prices, so the
  controller has no Prices button. Card payments on it are refused for now,
  because Odoo cannot yet record a sale the machine reports without its
  price. Each refused card, and any sale the machine still reports, leaves a
  system event on the controller with the card and the machine's data, for
  the operator to check on the machine.

A refused card on any vending machine (unknown, archived, without an
employee, or an employee who must be checked in first) leaves a system event
on the controller with the card number and the reason.

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
   - Set prices per slot (Vending and Vending Executive; a Vending MDB machine
     keeps its own prices)

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
| `department_id` | Many2one → \`hr.department\` | *from employee_id.department_id* |  | ✓ | Department of the employee at the time of the change. Stored so reports filter c |
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
| `kpi_hr_rfid_vending_refill_value` | Monetary | Kpi Hr Rfid Vending Refill Value |  | - | Live total of auto-refill credits added to employee balances during the digest w |
| `kpi_hr_rfid_vending_sale_value` | Monetary | Kpi Hr Rfid Vending Sale Value |  | - | Live total spent by employees through the vending controllers during the digest  |
| `kpi_hr_rfid_vending_sale_count_value` | Integer | Kpi Hr Rfid Vending Sale Count Value |  | - | Live count of individual vending purchases during the digest window. |

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
  - Add to the balance of an employee :param value: How much to add/subtract to/from the balance. Can be a positive or negative number. :param ev: Event id, ignored if 0 :return: Balance history if…
  - touches: `hr.rfid.vending.balance.history`
- **`hr_rfid_vending_set_balance(self, value, max_add=0, min_add=0, ev=0)`** - decorators: -
  - Set an employee's balance to a specific number, with the option of max_add :param value: :param max_add: :param min_add: :param ev: Event id, ignored if 0 :return: Balance history on success
  - touches: `hr.rfid.vending.balance.history`
- **`hr_rfid_vending_purchase(self, cost, ev=0)`** - decorators: -
  - Purchase a product. Subtracts the parameter "cost" from the employee's balance :param cost: How much to subtract :param ev: Event id, ignored if 0 :return: Balance history on success

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
Python class `HrRfidControllerVending` in `models/hr_rfid_ctrl.py:10`.  Model.  Inherits: `hr.rfid.ctrl`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `show_price_timeout` | Integer | Price Display Timeout |  | - | Duration (in seconds) that product prices remain visible on the vending machine  |
| `scale_factor` | Integer | Price Scale Factor |  | - | Multiplier used to convert currency amounts to vending machine units.          • |
| `cash_contained` | Float | Cash in Machine |  | ✓ | Current amount of physical cash stored in the vending machine.          • Purpos |
| `pricelist_id` | Many2one → \`product.pricelist\` | Product Pricelist |  | ✓ | Pricelist used to determine product prices for this vending machine.          •  |
| `is_vending` | Boolean | Is a Vending Machine |  | - | Set when the controller runs a vending firmware: it works with card balances and |
| `has_vending_price_table` | Boolean | Prices Set in Odoo |  | - | Set when the machine sells at the prices entered in Odoo. Machines that keep the |

#### Notable methods

- **`_compute_vending_flags(self)`** - decorators: `@api.depends`
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
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | Vending controller being configured. Set automatically from the active record wh |
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
| `row_num` | Integer | Row Num | ✓ | ✓ | Row index inside the vending machine grid (1-based). Each row holds 4 item slots |
| `controller_id` | Many2one → \`hr.rfid.ctrl\` | Controller | ✓ | ✓ | Vending controller this row belongs to. Cascade on delete — rows do not survive  |
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
| `refill_interval_number` | Integer | Refill Interval Number |  | ✓ | Repeat every x. |
| `refill_interval_type` | Selection | Interval Unit |  | ✓ | Time unit for the auto-refill repeat interval. Combined with Repeat every (above |
| `refill_nextcall` | Datetime | Next Execution Date |  | ✓ | Next planned execution date for this refill. |

### `res.config.settings` <a id='model-res-config-settings'></a>
Python class `ResConfigSettings` in `models/res_config_settings.py:4`.  TransientModel (wizard).  Inherits: `res.config.settings`.

#### Fields

| Name | Type | Label | Required | Store | Help |
|---|---|---|---|---|---|
| `refill_interval_number` | Integer | *from company_id.refill_interval_number* |  | - | Repeat every x. |
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
| `event_id` | Many2one → \`hr.rfid.vending.event\` | Event | ✓ | ✓ | Vending event being reversed. Set automatically from the active record when the  |
| `reason` | Text | Reason | ✓ | ✓ | Audit note explaining why the purchase is reversed (machine jam, double-charge,  |

#### Notable methods

- **`action_reverse(self)`** - decorators: -
  - effects: `message_post`, `raise:UserError`


## Module Constants <a id='constants'></a>

UPPER_CASE module-level assignments - rates, mappings, priority tables, status maps. Answer 'what values does the module hard-code?' here.


### `models/hr_rfid_ctrl.py`

- **`PRICE_TABLE_HW_VERSIONS`** *(collection)* = `('16', '20')`  - line 7


## Module Helpers & Hooks <a id='helpers'></a>

Top-level functions that sit outside any Odoo model class. Use this section to answer 'how do I call this programmatically' and 'what happens at install/uninstall'.


### Public helpers

- **`HrRfidVending.post_event(self, **post)`** (`@http.route`) - `controllers/main.py:22`
  - super-split (super): pre=- · post=`log_error`, `log_info`, `log_warn`, `with_company`, `with_context`
  - effects: `log_error`, `log_info`, `log_warn`, `with_company`, `with_context`
  - touches: `hr.rfid.card`, `hr.rfid.command`, `hr.rfid.ctrl.vending.row`, `hr.rfid.event.system`, `hr.rfid.vending.event`


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


### Access rights (ir.model.access; v20: ir.access rows with a group)

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
- **`hr_rfid_vending_operator_department_vending_events_rule`** on `hr_rfid_vending.model_hr_rfid_vending_event` - perms=`RD`, groups=`hr_rfid.hr_rfid_view_own_department`, domain=`
        [('employee_id.department_id.id','=',user.employee_ids.department_id.id)]
      `
- **`hr_rfid_group_operator_vending_events_rule`** on `hr_rfid_vending.model_hr_rfid_vending_event` - perms=`RD`, groups=`hr_rfid_vending.group_operator`, domain=`[(1,'=',1)] `
- **`hr_rfid_vending_department_vending_balance_history_rule`** on `hr_rfid_vending.model_hr_rfid_vending_balance_history` - perms=`RD`, groups=`hr_rfid.hr_rfid_view_own_department`, domain=`[('employee_id.department_id.id','=',user.employee_ids.department_id.id)]`


## Data & Automation <a id='data'></a>

XML records seeded at install and scheduled actions.


### Cron jobs

- **`hr_rfid_vending_employees_auto_refill`** (HR RFID Vending: Employees Auto Refill) on `model_hr_rfid_vending_auto_refill`, runs every 10 minutes, active=True

### Data records summary

- `ir.actions.act_window`: 10 record(s)
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

JavaScript, SCSS, OWL components and QWeb templates shipped by this module.


**Asset bundles extended in the manifest**: `web.assets_tests` (tests only)


**Other static JS/SCSS loaded by these bundles** (1): `static/tests/tours/vending_firmware_form_tour.js`



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

**TODO** in `controllers/main.py:144`

> Move into function "deal_with_ev_64"

#### TODO: Move into function "deal_with_ev_47"

**TODO** in `controllers/main.py:198`

> Move into function "deal_with_ev_47"

#### TODO: Reduce item quantity

**TODO** in `controllers/main.py:265`

> Reduce item quantity

#### TODO: Move into function "deal_with_err_evs"

**TODO** in `controllers/main.py:280`

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

#### TODO: Replace this search() override with a proper ir.rule for ...

**TODO** in `models/hr_rfid_vending_event.py:298`

> Replace this search() override with a proper ir.rule for group_customer.

#### TODO: Add this event if happend

**TODO** in `tests/test_vending_functionality.py:12`

> Add this event if happend

### From `git_log` (69)

#### Fix: [FIX] hr_rfid_vending: diagnostic logging + sudo() guard for ...

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

#### Fix: FIX: Stop balance for archived employees and fix balance with ...

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

#### Fix: v2.1 Added portal functionality, barcode generation and RFID ...

Commit `3c84986ac4` (2023-07-24): v2.1 Added portal functionality, barcode generation and RFID services. Many bugfixes

#### Fix: fix kpi field type sales count

Commit `eb7897abe3` (2023-05-26): fix kpi field type sales count

#### Fix: auto refill next call fix

Commit `349ff481e8` (2023-01-24): auto refill next call fix

#### Fix: Add Refill balance additional action to fix problem

Commit `6e3b378483` (2022-11-24): Add Refill balance additional action to fix problem

#### Fix: Fixes for Toni

Commit `f96d2b4fc1` (2022-11-15): Fixes for Toni


## Source provenance <a id='provenance'></a>

- Module: `hr_rfid_vending`
- Source digest: `sha256:ffbc98011d8ee0ab14c766b66ed154ad069b333eac53a14b28627109c1a2420c`
- Generated at: `2026-11-09T07:58:39+00:00`
- Generator: `polimex_module_knowledge`
