from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_portal")
class TestRfidPortalSmoke(TransactionCase):
    """Smoke coverage — module installs cleanly and the inherited
    hr.rfid.card model accepts records with the same shape as the
    base module expects."""

    def test_card_create_works_with_portal_extension(self):
        partner = self.env["res.partner"].create({"name": "Portal User"})
        card = self.env["hr.rfid.card"].create({
            "number": "9988776655",
            "card_type": self.env.ref("hr_rfid.hr_rfid_card_type_def").id,
            "contact_id": partner.id,
            "company_id": self.env.company.id,
        })
        self.assertTrue(card.id)

    def test_ir_actions_report_extension_loaded(self):
        # Module extends ir.actions.report; assert any existing report
        # record can still be read.
        report = self.env["ir.actions.report"].search([], limit=1)
        self.assertTrue(report, "ir.actions.report must remain queryable")
