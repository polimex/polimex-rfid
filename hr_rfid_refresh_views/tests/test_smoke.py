from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_refresh_views")
class TestRfidRefreshViewsSmoke(TransactionCase):
    """Smoke coverage — verify each consumer model now has the
    refresh.mixin in its MRO and writes trigger a polimex.<model> bus
    event when realtime_refresh is enabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.realtime_refresh = True

    def _patch_bus(self):
        bus_cls = type(self.env["bus.bus"])
        return patch.object(bus_cls, "_sendone")

    def test_consumer_models_have_refresh_mixin(self):
        # The refresh.mixin defines send_notice() — checking the method
        # is reachable on each consumer is a robust proxy for inheritance.
        for model_name in (
            "hr.rfid.ctrl",
            "hr.rfid.command",
            "hr.rfid.door",
            "hr.rfid.event",
            "hr.rfid.webstack",
            "hr.rfid.ctrl.alarm",
            "hr.rfid.ctrl.alarm.group",
        ):
            model = self.env[model_name]
            self.assertTrue(hasattr(model, "send_notice"),
                            f"{model_name} must inherit refresh.mixin")

    def test_webstack_write_emits_bus_notification(self):
        """A webstack lives at the head of the dependency chain — write
        should emit a polimex.hr.rfid.webstack.record_changed event when
        realtime_refresh is enabled on the company."""
        webstack = self.env["hr.rfid.webstack"].create({
            "name": "Refresh Test Stack",
            "serial": "REF001",
            "company_id": self.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        with self._patch_bus() as mock_send:
            webstack.write({"name": "Refresh Test Stack (renamed)"})
        polimex_calls = [
            c for c in mock_send.call_args_list
            if c.args and isinstance(c.args[0], str) and c.args[0].startswith("polimex.")
        ]
        self.assertTrue(polimex_calls,
                        "Writing to a refreshed model must emit a polimex bus event")
