# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_service", "rfid_service_onboarding")
class TestRfidServiceOnboarding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.onboarding = cls.env.ref('rfid_service_base.onboarding_service_setup')
        cls.step_define = cls.env.ref('rfid_service_base.onboarding_step_service_define')
        cls.step_sale = cls.env.ref('rfid_service_base.onboarding_step_service_first_sale')
        cls.onboarding._search_or_create_progress()

    def test_panel_has_two_steps_in_order(self):
        steps = self.onboarding.step_ids.sorted('sequence')
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0], self.step_define)
        self.assertEqual(steps[1], self.step_sale)

    def test_step_actions_resolve_to_real_windows(self):
        step_model = self.env['onboarding.onboarding.step']
        define_action = step_model.action_open_step_service_define()
        sale_action = step_model.action_open_step_service_first_sale()
        self.assertEqual(define_action['res_model'], 'rfid.service')
        self.assertEqual(sale_action['res_model'], 'rfid.service.sale')

    def test_define_step_completes_when_service_exists(self):
        ag = self.env["hr.rfid.access.group"].create({
            "name": "OnbVisitorAG", "company_id": self.company.id,
        })
        self.env["rfid.service"].create({
            "name": "OnbDayPass",
            "company_id": self.company.id,
            "service_type": "time_count",
            "visits": "1",
            "card_type": self.env.ref("hr_rfid.hr_rfid_card_type_barcode").id,
            "time_interval_number": 4,
            "time_interval_type": "hours",
            "time_interval_start": 8.0,
            "time_interval_end": 18.0,
            "access_group_id": ag.id,
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_define.current_step_state, 'done')
        self.assertEqual(self.step_sale.current_step_state, 'not_done')

    def test_sale_step_completes_when_service_sale_exists(self):
        ag = self.env["hr.rfid.access.group"].create({
            "name": "OnbVisitorAG2", "company_id": self.company.id,
        })
        service = self.env["rfid.service"].create({
            "name": "OnbDayPass2",
            "company_id": self.company.id,
            "service_type": "time_count",
            "visits": "1",
            "card_type": self.env.ref("hr_rfid.hr_rfid_card_type_barcode").id,
            "time_interval_number": 4,
            "time_interval_type": "hours",
            "time_interval_start": 8.0,
            "time_interval_end": 18.0,
            "access_group_id": ag.id,
        })
        partner = self.env["res.partner"].create({"name": "OnbVisitor"})
        now = fields.Datetime.now()
        self.env["rfid.service.sale"].create({
            "service_id": service.id,
            "partner_id": partner.id,
            "company_id": self.company.id,
            "start_date": now,
            "end_date": now + timedelta(days=1),
        })
        self.onboarding._prepare_rendering_values()
        self.assertEqual(self.step_sale.current_step_state, 'done')
