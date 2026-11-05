"""A device whose request lost a race for a row is served, not told 500.

Two workers writing the same attendance or controller row is ordinary on a busy
installation, and Odoo answers it by replaying the whole request. It can only do
that when the error reaches it. Answered by the device endpoint instead, what
the request had done so far would be committed and the device's next attempt
dropped as a duplicate of the same passage.
"""

import json
from unittest.mock import patch

from odoo.exceptions import ConcurrencyError
from odoo.tests import tagged

from odoo.addons.hr_rfid.tests.common import RFIDHttpCase


@tagged("post_install", "-at_install", "rfid", "rfid_endpoint")
class TestALostRaceIsRetried(RFIDHttpCase):
    def test_the_request_is_replayed_and_the_device_is_answered(self):
        webstack_class = type(self.env["hr.rfid.webstack"])
        heartbeat = webstack_class.parse_heartbeat
        calls = []

        def lose_once(record, post_data):
            calls.append(1)
            if len(calls) == 1:
                raise ConcurrencyError("somebody else wrote this row first")
            return heartbeat(record, post_data=post_data)

        webstack = self.test_webstack_10_3_id
        system_events = self.env["hr.rfid.event.system"]
        before = system_events.search_count([("webstack_id", "=", webstack.id)])
        with (
            patch.object(webstack_class, "parse_heartbeat", lose_once),
            patch("odoo.service.model.time.sleep"),
        ):
            response = self.url_open(
                self.app_url,
                data=json.dumps(
                    {
                        "convertor": webstack.serial,
                        "FW": "1.3400",
                        "key": webstack.key,
                        "heartbeat": 1,
                    }
                ),
                timeout=30,
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(len(calls), 2, "Odoo replayed the request")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            system_events.search_count([("webstack_id", "=", webstack.id)]),
            before,
            "a lost race is no fault of the device's to report",
        )
