# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # What happens to a stay the system had to settle itself. WHEN that
    # happens is core's own question - Settings -> Attendances -> Automatic
    # Check Out, with its tolerance, measured against the person's own
    # schedule - and it is asked in exactly one place now. This is the second
    # half of the same setting: what the company then credits the person.
    forgotten_badge_policy = fields.Selection(
        selection=[
            ('credit_schedule', 'Credit the scheduled day'),
            ('penalty', 'Credit the scheduled day, minus a penalty'),
            ('ignore', 'Count nothing for that day'),
        ],
        string="Forgotten Badge",
        default='credit_schedule',
        required=True,
        help="What to record when somebody forgets to badge out and the "
             "system has to settle the stay for them:\n\n"
             "• Credit the scheduled day: they are credited the hours their "
             "working schedule says for that day.\n"
             "• Credit the scheduled day, minus a penalty: the same, less the "
             "hours set below - for companies that treat a forgotten badge as "
             "time off site.\n"
             "• Count nothing for that day: no working time at all. The stay "
             "is marked as a forgotten badge, and somebody has to enter the "
             "real hours by hand - which is the point: the person has to say "
             "why they forgot.",
    )
    forgotten_badge_penalty_hours = fields.Float(
        string="Penalty",
        default=2.0,
        help="Hours taken off the scheduled day when a badge is forgotten. "
             "Used only with the penalty option above. A day shorter than the "
             "penalty is credited nothing rather than a negative number.",
    )
