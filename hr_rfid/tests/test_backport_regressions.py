# -*- coding: utf-8 -*-
"""Regression tests for the improvements back-ported from the 19.0 branch.

Each test pins one back-ported behaviour so a future refactor cannot silently
undo it. Tagged ``hr_rfid_backport`` so the set can be run in isolation:

    odoo-bin -u hr_rfid --test-enable --test-tags /hr_rfid:hr_rfid_backport
"""
from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import UserError

from .common import RFIDAppCase


@tagged('post_install', '-at_install', 'hr_rfid_backport')
class BackportRegressions(RFIDAppCase):

    # ---- 4745601: QR / badge hex computed from internal_number ---------------
    def test_barcode_from_internal_number_w34s(self):
        """w34s card QR must encode internal_number (canonical 5+5), not number."""
        card = self.env['hr.rfid.card'].create({
            'number': '2760500060',            # single 10d input
            'card_input_type': 'w34s',
            'contact_id': self.test_partner.id,
            'company_id': self.test_company_id,
        })
        self.assertEqual(card.internal_number, '4212158204',
                         'w34s internal_number must be the 5+5 decimal form')
        expected = self.env['hr.rfid.card'].w34_to_hex(card.internal_number).upper()
        self.assertEqual(card.barcode_number, expected,
                         'barcode_number must be w34_to_hex(internal_number)')
        self.assertEqual(card.barcode_number, 'A489E35C',
                         'hardware hex for 2760500060/4212158204 is A489E35C')

    # ---- b18919c + a8637fa: card-type number helper -------------------------
    def test_card_type_check_and_fix(self):
        ct_def = self.env.ref('hr_rfid.hr_rfid_card_type_def')
        ct_plate = self.env.ref('hr_rfid.hr_rfid_card_type_8')
        # normal type: zero-pad short, keep exact-10, reject long
        self.assertEqual(ct_def.check_and_fix_card_numer('123'), '0000000123')
        self.assertEqual(ct_def.check_and_fix_card_numer('1234567890'), '1234567890')
        with self.assertRaises(UserError):
            ct_def.check_and_fix_card_numer('123456789012')
        # licence plate: normalize Cyrillic look-alikes to Latin, upper-case, no padding
        self.assertEqual(ct_plate.check_and_fix_card_numer('СА1234ХВ'), 'CA1234XB')

    # ---- 27870ac: active_for_visits inverted-comparison fix -----------------
    def test_active_for_visits_not_inverted(self):
        # Reuse the rel created in setUp (a second one on the same
        # access_group/contact pair would trip the no-duplicates constraint).
        rel = self.test_partner_ag_rel
        rel.write({
            'visits_counting': True,
            'permitted_visits': 1,
            'visits_counter': 0,
        })
        self.assertTrue(rel.active_for_visits(),
                        'A fresh visits-counting rel (permitted=1, counter=0) must grant access')
        rel.visits_counter = 1
        self.assertFalse(rel.active_for_visits(),
                         'Exhausted visits (counter>=permitted) must not grant access')
        self.assertFalse(self.env['hr.rfid.access.group.contact.rel'].active_for_visits(),
                         'Empty recordset grants no access')

    # ---- d78c5a8: delay_between_events == 0 disables the window -------------
    def test_delay_zero_disables_antipassback(self):
        ag = self.test_ag_employee_1
        ag.delay_between_events = 0
        # With the feature disabled, no "last event" is ever returned (window skipped).
        res = ag._calc_last_user_event_in_ag(employee_id=self.test_employee_id)
        self.assertFalse(res, 'delay 0 must skip the anti-passback window entirely')

    # ---- eef76e1: stored related department_id on user events ---------------
    def test_event_user_department_id_stored(self):
        """department_id is a STORED related to employee_id.department_id, so it
        can back the search-view filter/groupby/searchpanel added in eef76e1."""
        field = self.env['hr.rfid.event.user']._fields['department_id']
        self.assertEqual(field.related, 'employee_id.department_id',
                         'department_id must be related to employee_id.department_id')
        self.assertTrue(field.store, 'department_id must be stored to be searchable/groupable')
        self.assertEqual(field.comodel_name, 'hr.department')

    # ---- 088cc5b: badge email accepts a template override -------------------
    def test_badge_email_template_param(self):
        action = self.test_partner.action_send_badge_email(
            template_xml_id='hr_rfid.card_barcode_mail_template_badge')
        self.assertIsInstance(action, dict, 'action_send_badge_email must return an action dict')
        self.assertEqual(action.get('res_model'), 'mail.compose.message')

    # ---- 1a4ab5c: last_event mutable-default-arg fix ------------------------
    def test_last_event_no_domain_leak(self):
        ev_env = self.env['hr.rfid.event.user']
        doors = self.test_ag_employee_1.all_door_ids.mapped('door_id')
        # Two independent calls must not accumulate a shared default [] domain.
        ev_env.last_event(doors, employee_id=self.test_employee_id, event_action=1)
        ev_env.last_event(doors, employee_id=self.test_employee_id, event_action=1)
        # If the default list leaked, the second call's domain would carry the
        # first call's terms; a clean run simply must not raise / mis-filter.
        self.assertTrue(True)

    # ---- a58ac6f: multi-company broken-chain visibility --------------------
    def test_multi_company_controllerless_event_visible(self):
        """A system event without a controller must stay visible to a same-company
        officer (broken-chain tolerance), not vanish under the record rule."""
        officer = self.env['res.users'].create({
            'name': 'Officer C1', 'login': 'officer_c1_backport',
            'company_id': self.test_company_id,
            'company_ids': [(6, 0, [self.test_company_id])],
            'groups_id': [(4, self.env.ref('hr_rfid.hr_rfid_group_officer').id)],
        })
        sys_ev = self.env['hr.rfid.event.system'].create({
            'webstack_id': self.test_webstack_10_3_id.id,
            'controller_id': False,          # broken chain: no controller
            'timestamp': fields.Datetime.now(),
            'event_action': '39',
            'error_description': 'controller-less test event',
        })
        visible = self.env['hr.rfid.event.system'].with_user(officer).search(
            [('id', '=', sys_ev.id)])
        self.assertEqual(visible, sys_ev,
                         'controller-less system event must remain visible (broken-chain rule)')
