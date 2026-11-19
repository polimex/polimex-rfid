# Polimex Holding Ltd. - https://polimex.co
"""Form 76 letters typed on a Latin keyboard become the Cyrillic ones.

A letter that only looks like the legend's ("O" for "О") printed alike and was
counted in no column of the sheet. Rewriting it through the model makes it
Cyrillic (hr.leave.type.write).
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.l10n_bg_hr_form_76.models.hr_leave_type import LATIN_TO_CYRILLIC


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    leave_types = (
        env["hr.leave.type"]
        .with_context(active_test=False)
        .search([("form76_code", "!=", False)])
    )
    for leave_type in leave_types:
        code = leave_type.form76_code
        if code.translate(LATIN_TO_CYRILLIC) != code:
            leave_type.form76_code = code
