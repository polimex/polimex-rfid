"""The old server's address is accepted the way people type it.

Field case, 20.10.2026: the operator typed the old server's IP address and
port, as in a browser bar, and the transfer answered "Connection error:
unsupported XML-RPC protocol" - the connection needs http:// in front, the
browser adds it by itself. The address is completed the same way.
"""

import types
import xmlrpc.client

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models import import_wizard


@tagged("post_install", "-at_install", "rfid_odoo_import", "rfid_import_ui")
class TestSourceAddress(TransactionCase):
    def _wizard(self, address):
        return self.env["hr.rfid.odoo.import.wiz"].create(
            {
                "source_url": address,
                "source_db": "src",
                "source_login": "admin",
                "source_password": "secret",
            }
        )

    def _connect(self, wiz):
        """Press "Test connection" against a stand-in server; return the addresses called."""
        called = []

        class _Proxy:
            def __init__(self, url, allow_none=True):
                called.append(url)

            def authenticate(self, db, login, password, context):
                return 2

            def execute_kw(self, db, uid, password, model, method, args, kwargs=None):
                if model == "ir.module.module":
                    leaf = next(term for term in args[0] if term[0] == "name")
                    if leaf[1] == "in":
                        return [{"name": "hr_rfid"}]
                    return [{"latest_version": "17.0.1.0.0"}]
                if model == "res.company":
                    return [{"id": 1, "name": "Company (test)"}]
                return []

        self.patch(
            import_wizard,
            "xmlrpc",
            types.SimpleNamespace(
                client=types.SimpleNamespace(
                    Fault=xmlrpc.client.Fault, ServerProxy=_Proxy
                )
            ),
        )
        wiz.action_test_connection()
        return called

    def test_an_address_typed_as_in_the_browser_connects(self):
        """An IP address and port, with no http:// in front, reaches the server."""
        wiz = self._wizard("192.168.74.64:8069")
        self.assertEqual(
            wiz.source_url,
            "http://192.168.74.64:8069",
            "the field shows the address completed, as it is used",
        )
        called = self._connect(wiz)
        self.assertEqual(wiz.state, "configure", "the connection must go through")
        self.assertIn("http://192.168.74.64:8069/xmlrpc/2/common", called)

    def test_a_full_address_is_kept_as_typed(self):
        """https:// stays https://; only a trailing slash goes, also on a later edit."""
        wiz = self._wizard("https://erp.example.com/")
        self.assertEqual(wiz.source_url, "https://erp.example.com")
        wiz.write({"source_url": " erp.example.com:8069 "})
        self.assertEqual(wiz.source_url, "http://erp.example.com:8069")
