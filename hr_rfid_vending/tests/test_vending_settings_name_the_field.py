# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
"""A setting out of range is refused by the name the person sees on the form.

The message used to carry an English fragment of its own ("the scale number")
inside a translated sentence, and asked for its translation where no language
could be found.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

TRANSLATION_LOG = "odoo.tools.translate"


@tagged("rfid_vending")
class TestVendingSettingsNameTheField(RFIDController, HttpCase):
    _registry_readonly_enabled = False

    def _settings(self, **values):
        self._add_Vending()
        settings = (
            self.env["hr.rfid.ctrl.vending.settings"]
            .with_context(ids=[self.c_vending.id])
            .create({"controller_id": self.c_vending.id})
        )
        settings.write(values)
        return settings

    def _refusal(self, settings):
        with (
            self.assertNoLogs(TRANSLATION_LOG, level="WARNING"),
            self.assertRaises(ValidationError) as refused,
        ):
            settings.save_settings()
        return str(refused.exception)

    def test_a_scale_factor_out_of_range_is_named_as_on_the_form(self):
        message = self._refusal(self._settings(scale_factor=300))

        self.assertIn("Scale Factor", message)
        self.assertIn("between 0 and 255", message)

    def test_a_price_timeout_out_of_range_is_named_as_on_the_form(self):
        message = self._refusal(self._settings(show_price_timeout=300))

        self.assertIn("Show Price Timeout", message)
