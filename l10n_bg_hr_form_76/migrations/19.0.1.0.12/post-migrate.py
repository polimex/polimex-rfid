# Polimex Holding Ltd. - https://polimex.co
""" "NA" is given back to the time-off types whose upgrade to 19.0.1.0.11 made it
half Cyrillic.

That upgrade turned every Latin look-alike into its Cyrillic twin, also inside
a code that holds a Latin letter without one: "NA", the default of a type
without a Form 76 letter, became "N" and a Cyrillic "А". A code that holds
Latin letters and Cyrillic look-alikes together came only from there; its
look-alikes go back to Latin.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_bg_hr_form_76.models.hr_leave_type import (
    LATIN_LETTER,
    LATIN_TO_CYRILLIC,
)

CYRILLIC_TO_LATIN = {cyrillic: latin for latin, cyrillic in LATIN_TO_CYRILLIC.items()}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    leave_types = (
        env["hr.leave.type"]
        .with_context(active_test=False)
        .search([("form76_code", "!=", False)])
    )
    for leave_type in leave_types:
        code = leave_type.form76_code
        latin = code.translate(CYRILLIC_TO_LATIN)
        if latin != code and LATIN_LETTER.search(code) and latin.isascii():
            leave_type.form76_code = latin
