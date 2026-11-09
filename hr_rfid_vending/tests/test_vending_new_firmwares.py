# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""One iCON180 vending board, three firmwares (Polimex, 06.11.2026):
16 is Executive with a coin mechanism, 20 is Executive only, 21 is MDB
cashless.

20 keeps the price table Odoo writes and sends the same events as 16, so an
employee buys at a 20 machine exactly as at a 16 machine. 21 keeps its own
prices and reports a sale with the credit left instead of its price: until
Odoo can book such a sale, the machine gets no credit, and what it reports
is left for the operator to check, never booked as a sale of a wrong amount.
"""

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

from . import test_vending_e2e
from .vending_common import VendingFlowMixin, fc, take_everyone_off_auto_refill


def report_scale_factor(ctrl, scale_factor):
    """The controller reports its IO table with this scale factor (row 0x14,
    the bytes every vending firmware reads it from)."""
    io_table = ctrl.io_table
    start = 16 * (0x14 - 1) + 12
    ctrl.with_context(from_controller=True).io_table = (
        io_table[:start] + "00%02X" % scale_factor + io_table[start + 4 :]
    )


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestExecutiveOnlyMachineSellsLikeTheCoinMachine(test_vending_e2e.TestVendingE2E):
    """Every flow of the coin machine - credit, sale, refill, limits,
    reversal - run against a machine with the Executive-only firmware (20).
    The cash flows are kept too: the firmware never starts them, and Odoo
    answers them the same way if they come."""

    # Odoo runs only the test methods a class defines itself unless told so
    # (odoo/tests/loader.py, get_module_test_cases).
    allow_inherited_tests_method = True
    vending_hw = 20


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestMdbMachineGetsNoCreditUntilItsSalesCanBeBooked(
    VendingFlowMixin, RFIDController, HttpCase
):
    """An MDB machine (21) must not hand out goods that Odoo books wrongly,
    and whatever it reports must reach the operator."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        take_everyone_off_auto_refill(self.env)
        self._add_Vending(hw=21)
        # A real machine reports a scale factor: the refusal below is not an
        # accident of a zero that turns every balance into no credit.
        report_scale_factor(self.c_vending, 5)
        self.assertEqual(self.c_vending.scale_factor, 5)
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

    def test_a_card_with_credit_is_refused_and_the_operator_sees_why(self):
        """The employee has credit, yet the machine gets none; one system
        event says which card asked."""
        response = self._ev64()

        self._assert_deny(response)
        refusal = self._system_events(event_action="64")
        self.assertEqual(len(refusal), 1)
        self.assertEqual(refusal.card_number, self.test_card_employee.number)
        self.assertEqual(self._vending_event_count(), 0, "no balance was handed out")

    def test_a_reported_sale_charges_nobody_and_reaches_the_operator(self):
        """The machine reports item 1 with 7 units of credit left. Booked as a
        sale it would charge the employee 0.35; instead the balance stays and
        the operator gets the sale to check, with its card and data."""
        history_before = self._history_count()

        response = self._ev47(product_slot=1, price_units=7)

        self.assertEqual(response, {})
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))
        self.assertEqual(self._history_count(), history_before)
        self.assertEqual(self._vending_event_count(), 0)
        self.assertEqual(self.c_vending.cash_contained, 0)
        reported = self._system_events(event_action="47")
        self.assertEqual(len(reported), 1)
        self.assertEqual(reported.card_number, self.test_card_employee.number)
        self.assertIn(
            "0000010007",
            reported.error_description,
            "the machine's data is kept for the check",
        )

    def test_a_refused_credit_and_a_reported_sale_are_two_entries(self):
        """The operator tells a refused card from a sale the machine made."""
        self._ev64()
        self._ev47(product_slot=1, price_units=7)

        self.assertEqual(len(self._system_events(event_action="64")), 1)
        self.assertEqual(len(self._system_events(event_action="47")), 1)

    def test_a_reported_recharge_credits_nothing(self):
        """The MDB firmware does not take coins; a recharge it reported would
        not be money in the machine, so it credits no one."""
        self._ev50(price_units=0, change_units=4)

        self.assertTrue(fc(self._emp().hr_rfid_vending_recharge_balance, 0))
        self.assertEqual(len(self._system_events(event_action="50")), 1)

    def test_the_machine_has_no_price_table_to_edit(self):
        """The machine keeps its prices, so Odoo offers no price rows for it,
        while it stays a vending machine with its counters."""
        ctrl = self.c_vending
        ctrl.invalidate_recordset()
        self.assertTrue(ctrl.is_vending)
        self.assertFalse(ctrl.has_vending_price_table)
        self.assertFalse(
            self.env["hr.rfid.ctrl.vending.row"].search_count(
                [("controller_id", "=", ctrl.id)]
            )
        )


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestMachinesOnOneModuleKeepTheirOwnRules(
    VendingFlowMixin, RFIDController, HttpCase
):
    """An MDB machine and an Executive-only machine behind the same module:
    each is answered by its own firmware's rules."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        take_everyone_off_auto_refill(self.env)
        self._add_Vending(hw=21)
        self.mdb = self.c_vending
        report_scale_factor(self.mdb, 5)
        self._add_Vending(hw=20)
        self.executive = self.c_vending
        self._setup_products()
        self._reset_employee()
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

    def test_credit_goes_to_the_executive_machine_only(self):
        self._assert_deny(self._ev64(ctrl_id=self.mdb))
        # 0.50 at scale factor 5 is 10 units.
        self._assert_balance_response(self._ev64(ctrl_id=self.executive), 10)

    def test_a_sale_is_charged_on_the_executive_machine_only(self):
        self._ev47(product_slot=1, price_units=7, ctrl_id=self.mdb)
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))

        # Slot 1 of the Executive machine sells product #1 at 0.05.
        self._ev47(product_slot=1, price_units=1, ctrl_id=self.executive)
        self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.45))


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestCreditSentToTheMachine(VendingFlowMixin, RFIDController, HttpCase):
    """The machine is offered all the credit the balance pays for."""

    _registry_readonly_enabled = False

    def setUp(self):
        super().setUp()
        take_everyone_off_auto_refill(self.env)
        self._add_Vending()
        self._setup_products()
        self._reset_employee()

    def test_a_balance_of_1_15_at_scale_5_is_23_units(self):
        """1.15 is 115 cents, 23 units of 5 cents - not the 22 that a
        floating point 22.999... cut to a whole number would give."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(1.15)
        self._assert_balance_response(self._ev64(), 23)

    def test_a_balance_between_two_units_is_offered_the_lower_one(self):
        """Negative: 0.29 pays for 5 units of 0.05, never for a sixth."""
        self.test_employee_id.hr_rfid_vending_add_to_balance(0.29)
        self._assert_balance_response(self._ev64(), 5)


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestVendErrorsOnTheNewFirmwares(VendingFlowMixin, RFIDController, HttpCase):
    """A vend failure from a 20 or 21 machine reaches the operator and moves
    no money."""

    _registry_readonly_enabled = False

    def test_a_vend_failure_is_a_system_event_and_charges_nobody(self):
        take_everyone_off_auto_refill(self.env)
        for hw in (20, 21):
            with self.subTest(hw=hw):
                self._add_Vending(hw=hw)
                self._reset_employee()
                self.test_employee_id.hr_rfid_vending_add_to_balance(0.50)

                self._ev49()

                self.assertEqual(len(self._system_events(event_action="49")), 1)
                self.assertEqual(self._vending_event_count(), 0)
                self.assertTrue(fc(self._emp().hr_rfid_vending_balance, 0.50))


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestPriceTableBelongsToMachinesThatUseIt(RFIDController, HttpCase):
    """The Prices button is offered only where the machine sells at the
    prices entered in Odoo."""

    _registry_readonly_enabled = False

    def test_coin_and_executive_only_machines_take_prices_from_odoo(self):
        for hw in (16, 20):
            with self.subTest(hw=hw):
                self._add_Vending(hw=hw)
                ctrl = self.c_vending
                ctrl.invalidate_recordset()
                self.assertTrue(ctrl.is_vending)
                self.assertTrue(ctrl.has_vending_price_table)
                # Reading the controller's IO table gives it its price rows.
                self.assertEqual(
                    self.env["hr.rfid.ctrl.vending.row"].search_count(
                        [("controller_id", "=", ctrl.id)]
                    ),
                    18,
                )
                ctrl.unlink()

    def test_a_door_controller_has_neither_flag(self):
        """Negative: a door controller shows no vending page and no Prices."""
        self._add_iCon130()
        self.c_130.invalidate_recordset()
        self.assertFalse(self.c_130.is_vending)
        self.assertFalse(self.c_130.has_vending_price_table)


@tagged("rfid_vending", "rfid_vending_firmwares", "post_install", "-at_install")
class TestControllerFormShowsWhatTheFirmwareUses(RFIDController, HttpCase):
    """A technician opens the controller a machine reported and sees the
    vending page, and the Prices button only where Odoo's prices are used."""

    _registry_readonly_enabled = False

    def _open_form(self, ctrl, tour):
        self.start_tour(
            "/odoo/action-hr_rfid.hr_rfid_ctrl_action/%d" % ctrl.id, tour, login="admin"
        )

    def test_an_executive_only_machine_offers_prices_and_the_vending_page(self):
        self._add_Vending(hw=20)
        self._open_form(self.c_vending, "hr_rfid_vending_price_table_form_tour")

    def test_an_mdb_machine_offers_the_vending_page_without_prices(self):
        self._add_Vending(hw=21)
        self._open_form(self.c_vending, "hr_rfid_vending_own_prices_form_tour")

    def test_a_door_controller_keeps_its_io_table_and_no_vending_controls(self):
        """Negative, and the proof that the tour sees the buttons at all."""
        self._add_iCon130()
        self._open_form(self.c_130, "hr_rfid_vending_door_controller_form_tour")
