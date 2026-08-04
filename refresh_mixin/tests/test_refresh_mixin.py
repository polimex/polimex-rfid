import logging
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "refresh_mixin")
class TestRefreshMixin(common.TransactionCase):
    """Unit coverage for the refresh.mixin abstract model.

    The mixin's send_notice() helper is what every consumer model relies
    on. We exercise it directly with a stubbed recordset shape so the
    tests do not depend on which downstream module (e.g.
    hr_rfid_refresh_views) is installed alongside.
    """

    def _patch_bus(self):
        bus_cls = type(self.env["bus.bus"])
        return patch.object(bus_cls, "_sendone")

    def _make_stub(self, *, has_company=True, realtime_refresh=True,
                   ids=(1, 2), extra_payload=None, companies=None):
        """Stub a recordset shape for send_notice().

        The company is a REAL res.company recordset: send_notice works on
        recordsets (sudo/filtered/ids), so a duck-typed object would test a
        contract nobody implements. `companies` overrides get_company_ids to
        cover a consumer whose record concerns several companies (shared
        hardware); by default the stub exercises the mixin's own single-company
        delegation.
        """
        Mixin = self.env["refresh.mixin"]

        company = self.env.company
        company.realtime_refresh = realtime_refresh
        stub = SimpleNamespace(
            _name=Mixin._name,
            _fields=({"company_id": object()} if has_company else {}),
            ids=list(ids),
            company_id=company if has_company else False,
            env=self.env,
            get_company_id=lambda: (company if has_company else self.env["res.company"]),
            _get_refresh_payload_extra=lambda: (extra_payload or {}),
        )
        stub.get_company_ids = (
            (lambda: companies) if companies is not None
            else (lambda: Mixin.get_company_ids.__func__(stub))
        )
        self.company = company
        return stub, Mixin

    def test_send_notice_emits_record_changed_for_write(self):
        stub, Mixin = self._make_stub()
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        self.assertEqual(mock_send.call_count, 1)
        channel, notif_type, payload = mock_send.call_args.args[:3]
        self.assertEqual(channel, "polimex.refresh.mixin")
        self.assertEqual(notif_type, "polimex.refresh.mixin.record_changed")
        self.assertEqual(payload["operation"], "write")
        self.assertEqual(payload["record_ids"], [1, 2])
        self.assertEqual(payload["company_id"], self.company.id)
        self.assertEqual(payload["company_ids"], [self.company.id])

    def test_send_notice_emits_record_created_for_create(self):
        stub, Mixin = self._make_stub()
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "create")
        self.assertEqual(mock_send.call_count, 1)
        _, notif_type, payload = mock_send.call_args.args[:3]
        self.assertEqual(notif_type, "polimex.refresh.mixin.record_created")
        self.assertEqual(payload["operation"], "create")

    def test_send_notice_skipped_when_realtime_refresh_disabled(self):
        stub, Mixin = self._make_stub(realtime_refresh=False)
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        self.assertEqual(mock_send.call_count, 0)

    def test_send_notice_skipped_when_no_company_field(self):
        stub, Mixin = self._make_stub(has_company=False)
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        self.assertEqual(mock_send.call_count, 0)

    def test_unresolvable_company_does_not_warn(self):
        # A record whose company cannot be resolved is expected control flow
        # (global record, camera event with no populated relations, ...): the
        # refresh is skipped silently. It must NOT be logged at WARNING — that
        # floods the operator log on a normal create/write path.
        stub, Mixin = self._make_stub(has_company=False)
        logger = logging.getLogger(
            "odoo.addons.refresh_mixin.models.refresh_mixin")
        with self._patch_bus(), self.assertNoLogs(logger, level="WARNING"):
            Mixin.send_notice.__func__(stub, "write")

    def test_extra_payload_is_merged(self):
        stub, Mixin = self._make_stub(
            extra_payload={"is_alert": True, "priority": 5},
        )
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        _, _, payload = mock_send.call_args.args[:3]
        self.assertTrue(payload["is_alert"])
        self.assertEqual(payload["priority"], 5)

    def test_payload_lists_every_company_concerned(self):
        """A record shared between companies (e.g. one access-control module
        serving two tenants) must reach the screens of ALL of them: the payload
        carries the full list, and `company_id` stays for older clients."""
        second = self.env["res.company"].create({"name": "Refresh Mixin Co 2"})
        second.realtime_refresh = True
        stub, Mixin = self._make_stub()
        both = self.env.company | second
        stub.get_company_ids = lambda: both
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        _, _, payload = mock_send.call_args.args[:3]
        self.assertEqual(set(payload["company_ids"]), set(both.ids))
        self.assertIn(payload["company_id"], both.ids)

    def test_only_companies_with_realtime_refresh_are_notified(self):
        """A company that switched realtime off is dropped from the list even
        when it shares the record."""
        quiet = self.env["res.company"].create({"name": "Refresh Mixin Quiet"})
        quiet.realtime_refresh = False
        stub, Mixin = self._make_stub()
        stub.get_company_ids = lambda: self.env.company | quiet
        with self._patch_bus() as mock_send:
            Mixin.send_notice.__func__(stub, "write")
        _, _, payload = mock_send.call_args.args[:3]
        self.assertEqual(payload["company_ids"], [self.company.id])
