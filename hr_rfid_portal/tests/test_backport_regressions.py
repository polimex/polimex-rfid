# -*- coding: utf-8 -*-
"""Regression tests for the portal barcode-mechanism improvement (c4cf957).

Run:  odoo-bin -u hr_rfid_portal --test-enable --test-tags portal_backport
"""
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'portal_backport')
class PortalBackportRegressions(TransactionCase):

    # ---- c4cf957: Polimex QR-logo barcode mask registered ------------------
    def test_polimex_logo_mask_registered(self):
        report = self.env['ir.actions.report']
        masks = report.get_available_barcode_masks()
        self.assertIn('polimex_logo', masks,
                      'the polimex_logo QR-code mask must be registered so the portal '
                      'barcode/QR card renders with the Polimex logo overlay')
        self.assertTrue(hasattr(report, 'apply_qr_code_polimex_logo_mask'))
