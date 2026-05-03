# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Backend lifecycle tests for rfid_service_base.

Covers the visitor / temporary-access flow that test_services.py exercises
end-to-end with hardware events. These tests stay at the model layer to
keep the suite fast and to lock down the state-machine and cancel/extend
helpers without spinning up the iCon controller stack.
"""
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_service", "rfid_service_lifecycle")
class TestRfidServiceLifecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Visitor One"})
        cls.access_group = cls.env["hr.rfid.access.group"].create({
            "name": "Test Visitor AG",
            "company_id": cls.company.id,
        })
        # Service template used by every test.
        cls.service = cls.env["rfid.service"].create({
            "name": "Day Pass",
            "company_id": cls.company.id,
            "service_type": "time_count",
            "visits": "1",
            "card_type": cls.env.ref("hr_rfid.hr_rfid_card_type_barcode").id,
            "time_interval_number": 4,
            "time_interval_type": "hours",
            "time_interval_start": 8.0,
            "time_interval_end": 18.0,
            "access_group_id": cls.access_group.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_partner_to_ag(self, *, activate_on=None, expiration=None):
        activate_on = activate_on or fields.Datetime.now()
        expiration = expiration or (fields.Datetime.now() + timedelta(hours=1))
        return self.env["hr.rfid.access.group.contact.rel"].create({
            "access_group_id": self.access_group.id,
            "contact_id": self.partner.id,
            "activate_on": activate_on,
            "expiration": expiration,
        })

    def _make_sale(self, *, start, end, ag_rel):
        return self.env["rfid.service.sale"].create({
            "service_id": self.service.id,
            "company_id": self.company.id,
            "partner_id": self.partner.id,
            "start_date": start,
            "end_date": end,
            "access_group_contact_rel": ag_rel.id,
        })

    # ==================================================================
    # State transitions
    # ==================================================================

    def test_state_progress_when_inside_window(self):
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now() - timedelta(minutes=10),
            end=fields.Datetime.now() + timedelta(hours=1),
            ag_rel=ag_rel,
        )
        # Computed automatically by _compute_state.
        self.assertEqual(sale.state, "progress")

    def test_state_finished_when_window_expired(self):
        ag_rel = self._attach_partner_to_ag(
            activate_on=fields.Datetime.now() - timedelta(hours=2),
            expiration=fields.Datetime.now() - timedelta(hours=1),
        )
        sale = self._make_sale(
            start=fields.Datetime.now() - timedelta(hours=2),
            end=fields.Datetime.now() - timedelta(hours=1),
            ag_rel=ag_rel,
        )
        self.assertEqual(sale.state, "finished")

    def test_state_canceled_when_ag_rel_window_collapsed(self):
        """The 'canceled' state is detected by a 1-second AG window —
        cancel_sale() collapses the window to that signature."""
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=2),
            ag_rel=ag_rel,
        )
        sale.cancel_sale()
        # _compute_state runs on access_group_contact_rel changes; force
        # the recompute by reading the field.
        sale.invalidate_recordset()
        self.assertEqual(sale.state, "canceled")

    # ==================================================================
    # Cancel
    # ==================================================================

    def test_cancel_sale_collapses_ag_window(self):
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=4),
            ag_rel=ag_rel,
        )
        sale.cancel_sale()
        # The AG-relation window should shrink to a one-second interval.
        delta = sale.access_group_contact_rel.expiration - sale.access_group_contact_rel.activate_on
        self.assertEqual(delta, timedelta(seconds=1))

    def test_cancel_sale_idempotent_for_already_finished(self):
        ag_rel = self._attach_partner_to_ag(
            activate_on=fields.Datetime.now() - timedelta(hours=2),
            expiration=fields.Datetime.now() - timedelta(hours=1),
        )
        sale = self._make_sale(
            start=fields.Datetime.now() - timedelta(hours=2),
            end=fields.Datetime.now() - timedelta(hours=1),
            ag_rel=ag_rel,
        )
        original_expiration = ag_rel.expiration
        # cancel_sale filters out finished/canceled — no-op expected.
        sale.cancel_sale()
        ag_rel.invalidate_recordset()
        self.assertEqual(ag_rel.expiration, original_expiration,
                         "Already-finished sale must not have its AG window mutated")

    # ==================================================================
    # Extend
    # ==================================================================

    def test_extend_service_returns_action_with_correct_context(self):
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=2),
            ag_rel=ag_rel,
        )
        action = sale.extend_service()
        self.assertEqual(action["type"], "ir.actions.act_window")
        ctx = action["context"]
        self.assertEqual(ctx["default_extend_sale_id"], sale.id)
        self.assertEqual(ctx["default_service_id"], self.service.id)
        self.assertEqual(ctx["default_partner_id"], self.partner.id)

    def test_extend_service_requires_single_record(self):
        ag_rel = self._attach_partner_to_ag()
        sale1 = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=2),
            ag_rel=ag_rel,
        )
        # A second sale must use a non-overlapping AG window or a
        # different partner — the AG-rel constraint forbids overlap.
        partner2 = self.env["res.partner"].create({"name": "Visitor Two"})
        ag_rel2 = self.env["hr.rfid.access.group.contact.rel"].create({
            "access_group_id": self.access_group.id,
            "contact_id": partner2.id,
            "activate_on": fields.Datetime.now(),
            "expiration": fields.Datetime.now() + timedelta(hours=2),
        })
        sale2 = self.env["rfid.service.sale"].create({
            "service_id": self.service.id,
            "company_id": self.company.id,
            "partner_id": partner2.id,
            "start_date": fields.Datetime.now(),
            "end_date": fields.Datetime.now() + timedelta(hours=2),
            "access_group_contact_rel": ag_rel2.id,
        })
        with self.assertRaises(ValueError):
            (sale1 | sale2).extend_service()

    # ==================================================================
    # Email & print
    # ==================================================================

    def test_email_card_raises_when_partner_has_no_email(self):
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=2),
            ag_rel=ag_rel,
        )
        # Partner created without email → must raise UserError.
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            sale.email_card()

    def test_print_card_returns_action(self):
        """print_card() delegates to the foldable_badge report. We just
        assert it returns a non-empty action dict — the exact action type
        depends on whether the partner has a printable card on file."""
        ag_rel = self._attach_partner_to_ag()
        sale = self._make_sale(
            start=fields.Datetime.now(),
            end=fields.Datetime.now() + timedelta(hours=2),
            ag_rel=ag_rel,
        )
        action = sale.print_card()
        self.assertIsInstance(action, dict)
        self.assertIn(action.get("type"),
                      {"ir.actions.report", "ir.actions.act_window"})

    # ==================================================================
    # Service template helpers
    # ==================================================================

    def test_service_default_color_is_assigned(self):
        srv = self.env["rfid.service"].create({
            "name": "Color Test",
            "company_id": self.company.id,
            "service_type": "time_count",
            "card_type": self.env.ref("hr_rfid.hr_rfid_card_type_barcode").id,
            "access_group_id": self.access_group.id,
        })
        self.assertIsNotNone(srv.color)

    def test_action_view_sales_is_filtered_by_service(self):
        action = self.service.action_view_sales()
        self.assertEqual(action["res_model"], "rfid.service.sale")
        self.assertIn(("service_id", "=", self.service.id), action["domain"])
