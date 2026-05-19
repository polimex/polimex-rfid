# -*- coding: utf-8 -*-
"""
Migration 19.0.2.11.1 — Repair orphan cards left behind by _deactivate race.

The previous _deactivate (on access_group_contact_rel / employee_rel) unconditionally
removed every hr.rfid.card.door.rel for the card+door pair, without checking whether
another active access group still covered the same door. When _activate ran first
(via lazy _compute_state recompute) and saw the existing rel, it skipped the ADD
command — then _deactivate wiped the rel anyway, leaving the controller without
that card.

Symptom in production: card has active access_group_contact_rel (state=True,
internal_state=True) but zero hr.rfid.card.door.rel records. Card stops working.

This migration scans for those orphans and replays update_card_rels for each one,
which recreates the door rel and enqueues the missing ADD command toward the
controller.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Starting hr_rfid post-migration 19.0.2.11.1 (orphan card repair)")

    env = api.Environment(cr, SUPERUSER_ID, {})

    Card = env["hr.rfid.card"].with_context(active_test=False)
    rel_env = env["hr.rfid.card.door.rel"]

    # Contact-based orphans
    contact_orphans = Card.search([
        ("active", "=", True),
        ("contact_id", "!=", False),
        ("contact_id.hr_rfid_access_group_ids.state", "=", True),
        ("door_rel_ids", "=", False),
    ])

    # Employee-based orphans
    employee_orphans = Card.search([
        ("active", "=", True),
        ("employee_id", "!=", False),
        ("employee_id.hr_rfid_access_group_ids.state", "=", True),
        ("door_rel_ids", "=", False),
    ])

    orphans = contact_orphans | employee_orphans
    _logger.info(
        "Found %d orphan cards (contact=%d, employee=%d)",
        len(orphans), len(contact_orphans), len(employee_orphans),
    )

    repaired = 0
    skipped = 0
    for card in orphans:
        if not card.card_ready():
            skipped += 1
            _logger.info("Skipping card %s — not card_ready()", card.number)
            continue
        try:
            rel_env.update_card_rels(card)
            cr.commit()
            repaired += 1
            _logger.info(
                "Repaired card %s (id=%s, owner=%s) — %d door rel(s) restored",
                card.number, card.id, card.get_owner().display_name,
                len(card.door_rel_ids),
            )
        except Exception:
            cr.rollback()
            _logger.exception("Failed to repair card %s (id=%s)", card.number, card.id)

    _logger.info(
        "Post-migration 19.0.2.11.1 complete: repaired=%d, skipped=%d, total=%d",
        repaired, skipped, len(orphans),
    )
