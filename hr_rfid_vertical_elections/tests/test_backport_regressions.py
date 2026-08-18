# -*- coding: utf-8 -*-
"""Regression tests for improvements back-ported from 19.0 to hr_rfid_vertical_elections.

Run:  odoo-bin -u hr_rfid_vertical_elections --test-enable --test-tags elections_backport
"""
import inspect
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install', 'elections_backport')
class ElectionsBackportRegressions(TransactionCase):

    # ---- 887641a: public session_close must not accept a client state -------
    def test_session_close_ignores_client_state(self):
        """The public (token-only) session_close endpoint must absorb any
        client-supplied kwargs (**kwargs) and never write a caller-provided
        state - closing the mass-assignment / reopen vector."""
        from odoo.addons.hr_rfid_vertical_elections.controllers.voting import VoteController
        sig = inspect.signature(VoteController.session_close)
        self.assertTrue(
            any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()),
            'session_close must accept **kwargs so a malicious state= is absorbed, not applied')
        src = inspect.getsource(VoteController.session_close)
        self.assertIn('"state": "closed"', src,
                      'session_close must hard-code state=closed rather than trust the caller')

    # ---- b87c8f2: field help= back-ported on the voting session -------------
    def test_voting_session_field_help(self):
        field = self.env['voting.session']._fields.get('state')
        self.assertTrue(field is not None, 'voting.session.state must exist')
        # at least one field on the session carries a back-ported help tooltip
        helped = [f for f in self.env['voting.session']._fields.values() if getattr(f, 'help', None)]
        self.assertTrue(helped, 'b87c8f2 must have added help= tooltips to voting.session fields')
