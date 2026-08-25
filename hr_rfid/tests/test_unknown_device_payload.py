# -*- coding: utf-8 -*-
"""A device speaking a shape we do not handle gets an answer, not a 500.

/hr/rfid/event is public and is what every module in the field talks to. A
payload without the 'convertor' key falls to _parse_raw_data, and one shape of
it - serial + security + events, what barcode devices send - used to be handed
to a helper that built an 'hr.rfid.raw.data' record. That model was never
loaded: its file has never been imported, here or in 15.0 or 18.0. So the call
could only ever raise KeyError, and the device got HTTP 500 - on the product's
main public endpoint, for as long as the code has existed.
"""
import json

from odoo.tests import tagged

from odoo.addons.hr_rfid.tests.common import RFIDHttpCase

_TIMEOUT = 30


@tagged('post_install', '-at_install', 'rfid', 'rfid_endpoint')
class TestAnUnknownDevicePayload(RFIDHttpCase):

    def _post(self, payload):
        return self.url_open(
            self.app_url, data=json.dumps(payload), timeout=_TIMEOUT,
            headers={'Content-Type': 'application/json'})

    def test_the_barcode_shape_is_answered_not_dropped_on_the_floor(self):
        """The exact payload that used to end in a server error."""
        response = self._post({
            'serial': '234567',
            'security': 'whatever',
            'events': [{'bar': '1234567890128'}],
        })

        self.assertEqual(response.status_code, 200,
                         "a public device endpoint must not answer a device "
                         "with a server error")
        self.assertEqual(response.json().get('status'), 200,
                         "and the device must be told it was heard, or it "
                         "will keep retrying forever")

    def test_any_other_unknown_shape_is_answered_too(self):
        """NEGATIVE: nothing about this is special to barcode devices."""
        response = self._post({'something': 'else'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 200)
