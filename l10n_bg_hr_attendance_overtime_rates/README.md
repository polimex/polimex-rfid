# Bulgaria - Attendance Overtime Rates & Public Holidays

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Bulgarian localisation seed for the attendance cost layer: statutory overtime coefficients, the night-shift supplement, and official public holidays.

## 🎯 Overview

`hr_attendance_late` provides a generic, dated legal-rate table (`hr.legal.rate`) used when costing attendance. This module fills it with the Bulgarian Labour Code values and adds the country's public holidays as global calendar leaves, so the cost bridge in `hr_attendace_rfid_hr_hourly_cost` can tell a rest-day from a public holiday.

## ✨ Key Features

- **КТ overtime coefficients (dated)** - work-day overtime ×1.5, rest-day ×1.75, public-holiday ×2.0 (КТ чл. 262 minimums), seeded with a historical effective date so future law changes are added as new dated rows.
- **Night-shift supplement** - an additive per-hour amount (НСОРЗ чл. 8), seeded at 0.51 EUR effective 2026-01-01 (eurozone). Additive, not a multiplier.
- **Public-holiday generation** - computes the year's official Bulgarian holidays, including the movable Orthodox Easter dates (`dateutil.easter` with `EASTER_ORTHODOX`), as public holidays with no working schedule, so they hold for everybody in the company whatever schedule a person is on (shifts, part time, nights). A day the company already holds is left as it is.
- **Wizard + annual cron** - generate holidays for a chosen year on demand, or let the yearly cron roll the next year forward for every company in Bulgaria that keeps public holidays.

## 📋 Requirements

- Odoo 19.0+
- `hr_attendance`
- `hr_holidays`
- `hr_attendance_late` (provides the `hr.legal.rate` table the seed targets)

## ⚙️ Configuration

- The legal rates are seeded on install (`noupdate`, so local overrides survive upgrades). Review or override them under **Attendances ▸ Configuration ▸ Legal Rates**.
- Generate public holidays via **Attendances** → the *Generate Bulgarian Public Holidays* wizard, or rely on the annual cron.

## 🚀 Usage

1. Install - КТ coefficients and the night supplement appear in **Legal Rates**.
2. Run the holiday wizard for the current/next year (or wait for the cron).
3. The attendance cost bridge reads these rates and the public-holiday calendar automatically; no further setup is needed.

> When the law changes a coefficient, add a **new** Legal Rate row with the new *Valid From* date - past worked days keep their historical value.

## The holidays it creates

Each generated public holiday is a day off for everybody in the company,
whatever working schedule a person is on: shifts, part time or nights. It is
the whole day, midnight to midnight, in the timezone of the company's working
schedule - whoever generates the year: an HR officer, or the yearly scheduled
action, which has no timezone of its own. This is the shape
**Time Off -> Configuration -> Public Holidays** creates when *Working Hours*
is left empty, so the days it makes and the days typed in by hand read alike.
A day the company already holds as a public holiday is left as it is.

## 🛠️ Technical

- **`data/legal_rates.xml`** - seeds `hr.legal.rate` rows (`overtime_workday`, `overtime_weekend`, `overtime_holiday`, `night_supplement`).
- **`res.company._generate_bg_public_holidays(year)`** - idempotent batched creation of `resource.calendar.leaves` with no schedule and no resource (core applies them to every schedule of the company); fixed dates + Orthodox-Easter-derived Good Friday / Holy Saturday / Easter Monday.
- **`_cron_generate_bg_public_holidays`** - annual roll-forward, only for companies whose country is Bulgaria.
- **Upgrade to 19.0.1.0.6** - for companies in Bulgaria, official days from today on that earlier versions tied to one schedule are released to every schedule (`_hand_bg_public_holidays_to_everyone`); days already over, closures of several days and closing days on ordinary dates keep their schedule, and a day core refuses to release is logged and left.
- **`generate.bg.holidays.wizard`** - on-demand generation for a chosen year.

## 👥 Credits

**Polimex Holding Ltd.** - https://polimex.co
