from odoo import fields, models


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    # What a forgotten badge is worth for the people on THIS schedule. The
    # company's Forgotten Badge setting (res.company) still decides whether a
    # forgotten day is credited at all and what a penalty takes off; this
    # number only stands in for "the scheduled day" in it, and never pays more
    # than that day (hr.attendance._settled_check_out). The case it exists
    # for: a floating schedule of fourteen hours, whose day is the frame people
    # may work in, not what a day nobody badged out of should pay (a customer's
    # request, owner's decision 12.11.2026). Zero keeps the scheduled day.
    forgotten_badge_hours = fields.Float(
        string="Hours for a Forgotten Badge",
        help="How many hours a day is worth when somebody on this schedule "
        "forgets to badge out and the system closes the day for them - at most "
        "the working day of the schedule. Leave at 0 to credit the working day. "
        "The Forgotten Badge setting of the company still applies: a penalty "
        'is taken off these hours, and with "Count nothing for that day" '
        "nothing is credited.",
    )

    _forgotten_badge_hours_not_negative = models.Constraint(
        "CHECK(forgotten_badge_hours >= 0)",
        "The hours for a forgotten badge cannot be negative. Enter 0 to credit "
        "the working day of the schedule.",
    )
