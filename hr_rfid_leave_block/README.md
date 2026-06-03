# RFID Access Block on Leave

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-green.svg)](https://apps.odoo.com)

Suspend an employee's RFID cards automatically while they are on approved time off, and restore them when the leave ends.

## 🎯 Overview

When a time-off request is approved, this module deactivates the employee's currently-active RFID cards so they cannot enter while away. It remembers the exact set of cards it suspended and re-activates only those when access is restored — the day after the leave ends, or immediately if the leave is refused or cancelled. A card the employee had already disabled before the leave, or added during it, is intentionally left untouched.

## ✨ Key Features

- **Per-card snapshot** — records exactly which cards were active and got suspended (`hr.rfid.leave.block`), so restore never silently re-enables a card the user meant to keep off.
- **Automatic on approval** — a `hr.leave` state transition to *Approved* triggers the suspension; *Refused* / *Cancelled* / back-to-draft triggers the restore.
- **Idempotent** — re-approving a leave that already has an active block does not double-suspend or re-snapshot.
- **Scheduled restore** — a daily cron restores access for leaves whose end date has passed.
- **Self-cleaning audit** — restored audit rows are reclaimed by `@api.autovacuum` after one year, in batches.
- **Multi-company isolated** — blocks are scoped to the leave's company.

## 📋 Requirements

- Odoo 19.0+
- `hr_rfid`
- `hr_holidays`

## ⚙️ Configuration

No configuration is required. The behaviour is wired to the standard time-off approval flow. Two scheduled actions are created on install:

- **Restore RFID access for ended leaves** — daily.
- Restored audit rows are garbage-collected by the core *Auto-vacuum* cron (no separate schedule).

## 🚀 Usage

1. Approve a time-off request for an employee who holds RFID cards.
2. The employee's active cards are suspended and listed under **RFID ▸ Leave Access Blocks**.
3. When the leave ends (or is refused/cancelled), the snapshotted cards are re-activated automatically.

## 🛠️ Technical

- **Model `hr.rfid.leave.block`** — `leave_id`, related `employee_id`/`company_id`, `blocked_card_ids` (M2M snapshot read with `active_test=False` so archived cards stay visible), `state` (`active`/`restored`), `blocked_at`/`restored_at`.
- **`hr.leave.write` hook** — reacts to the `state` transition after the core write succeeds; `validate` → `_rfid_block_access`, `draft`/`confirm`/`refuse`/`cancel` → `_rfid_restore_access`.
- **`_cron_restore_expired_blocks`** — restores blocks whose `leave_id.date_to` has passed.
- **`_gc_restored_blocks`** — batched `@api.autovacuum` returning `(done, has_more)`.

## 👥 Credits

**Polimex Holding Ltd.** — https://polimex.co
