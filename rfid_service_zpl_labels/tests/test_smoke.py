from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_zpl_labels")
class TestRfidZplLabelsSmoke(TransactionCase):
    """Smoke coverage — config parameters and report registration."""

    def test_printer_ip_config_parameter_exists(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "rfid.label.printer.ip"
        )
        self.assertEqual(param, "192.168.1.100")

    def test_printer_port_config_parameter_exists(self):
        param = self.env["ir.config_parameter"].sudo().get_param(
            "rfid.label.printer.port"
        )
        self.assertEqual(param, "9100")

    def test_wristband_report_is_registered(self):
        report = self.env.ref(
            "rfid_service_zpl_labels.action_report_rfid_wristband",
            raise_if_not_found=False,
        )
        self.assertTrue(report, "wristband report action must be registered")
