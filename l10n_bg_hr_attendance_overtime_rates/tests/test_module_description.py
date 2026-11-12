import os

import polib

from odoo.modules.module import Manifest
from odoo.tests import TransactionCase, tagged

MODULE = "l10n_bg_hr_attendance_overtime_rates"
# The Apps list and the public /website/info page show the module's name and
# summary; Odoo translates them from entries of the module's catalog that point
# at the module's record in ``base``, not at the module itself.
NAME_REF = (
    "model:ir.module.module,shortdesc:base.module_l10n_bg_hr_attendance_overtime_rates"
)
SUMMARY_REF = (
    "model:ir.module.module,summary:base.module_l10n_bg_hr_attendance_overtime_rates"
)


@tagged("post_install", "-at_install")
class TestNameAndSummaryInBulgarian(TransactionCase):
    """A Bulgarian user reads this module's name and summary in Bulgarian, in
    the list of apps and on the public page that lists what a site runs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manifest = Manifest.for_addon(MODULE)
        cls.catalog = polib.pofile(os.path.join(cls.manifest.path, "i18n", "bg.po"))

    def _entry(self, reference):
        found = [
            entry
            for entry in self.catalog
            if any(reference == occurrence[0] for occurrence in entry.occurrences)
        ]
        self.assertEqual(len(found), 1, "catalog entry for %s" % reference)
        return found[0]

    def test_the_name_and_summary_are_translated_into_bulgarian(self):
        """Both entries exist, carry the manifest's text and a real translation.

        They point at ``base``, so a catalog sync that dropped them, or a
        manifest edited without its translation, would show English again.
        """
        for reference, english in (
            (NAME_REF, self.manifest["name"]),
            (SUMMARY_REF, self.manifest["summary"]),
        ):
            entry = self._entry(reference)
            self.assertEqual(entry.msgid, english, reference)
            self.assertTrue(entry.msgstr.strip(), reference)
            self.assertNotEqual(entry.msgstr, english, reference)
            self.assertNotIn("fuzzy", entry.flags, reference)
