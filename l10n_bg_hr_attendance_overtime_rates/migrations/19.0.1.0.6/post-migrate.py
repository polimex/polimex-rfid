# Polimex Holding Ltd. - https://polimex.co
"""The official holidays made by earlier versions hold for everybody.

Earlier versions tied every official day to the company's own working
schedule, so a person on any other schedule worked through the holiday in
every daily figure and in pay. The upgrade releases those days from the
schedule (res.company._hand_bg_public_holidays_to_everyone). Core then
re-counts the time off that falls on them, as it does for any change of a
public holiday: a person on another schedule with leave on such a day gets the
day back.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._hand_bg_public_holidays_to_everyone()
