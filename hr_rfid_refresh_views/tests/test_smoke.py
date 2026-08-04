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

    def test_shared_module_notifies_every_sharing_company(self):
        """A module shared between companies concerns all of them: the
        realtime refresh payload must carry the whole company list so each
        sharing company's screens update."""
        company_b = self.env["res.company"].create({"name": "Refresh Share Co B"})
        company_b.realtime_refresh = True
        webstack = self.env["hr.rfid.webstack"].create({
            "name": "Shared Refresh Stack",
            "serial": "REF002",
            "company_id": self.company.id,
            "shared_company_ids": [(6, 0, [company_b.id])],
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        ctrl = self.env["hr.rfid.ctrl"].create({
            "name": "Shared Refresh Ctrl",
            "ctrl_id": 95,
            "webstack_id": webstack.id,
        })
        door = self.env["hr.rfid.door"].create({
            "name": "Shared Refresh Door",
            "number": 9501,
            "controller_id": ctrl.id,
        })
        expected = self.company | company_b
        for record in (webstack, ctrl, door):
            self.assertEqual(record.get_company_ids(), expected,
                             "%s must notify owner + sharing companies" % record._name)
        with self._patch_bus() as mock_send:
            webstack.write({"name": "Shared Refresh Stack (renamed)"})
        payloads = [
            c.args[2] for c in mock_send.call_args_list
            if c.args and isinstance(c.args[0], str)
            and c.args[0] == "polimex.hr.rfid.webstack"
        ]
        self.assertTrue(payloads, "The webstack write must emit a refresh event")
        self.assertEqual(set(payloads[-1]["company_ids"]), set(expected.ids),
                         "The payload must list every company the module concerns")

    def test_unshared_module_payload_stays_single_company(self):
        """Regression: without sharing, the payload lists exactly the owner
        company - existing single-company behaviour is unchanged."""
        webstack = self.env["hr.rfid.webstack"].create({
            "name": "Solo Refresh Stack",
            "serial": "REF003",
            "company_id": self.company.id,
            "available": "a",
            "tz": "Europe/Sofia",
            "active": True,
        })
        with self._patch_bus() as mock_send:
            webstack.write({"name": "Solo Refresh Stack (renamed)"})
        payloads = [
            c.args[2] for c in mock_send.call_args_list
            if c.args and isinstance(c.args[0], str)
            and c.args[0] == "polimex.hr.rfid.webstack"
        ]
        self.assertTrue(payloads)
        self.assertEqual(payloads[-1]["company_ids"], [self.company.id])
        self.assertEqual(payloads[-1]["company_id"], self.company.id)
