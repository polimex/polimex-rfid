# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install', 'rfid_import_tour')
class TestTransferTours(HttpCase):
    """The operator can drive the wizard on screen.

    Бизнес твърдение: човекът, който прехвърля системата, попълва адреса и
    достъпа и избира какво да включи. Помощник, който се рендира, но не приема
    писане, е точно провалът, който собственикът откри сам - затова тук се
    ПИШЕ и се КЛИКА, а не само се проверява, че елементите ги има.
    """

    # This test writes to the database from the browser session.
    _registry_readonly_enabled = False

    def test_the_operator_can_fill_the_wizard_in(self):
        self.start_tour('/odoo', 'rfid_transfer_gate_tour', login='admin')
