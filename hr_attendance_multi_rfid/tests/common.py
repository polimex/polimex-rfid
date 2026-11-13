"""Moments of a Sofia day, as the database keeps them.

Sofia is two or three hours ahead of UTC, which is exactly what makes a day
there and the same date in UTC different stretches of time - the shape every
test of "the person's own day" has to build. Shared by the attendance tests of
this module and of the modules built on it.
"""

from datetime import datetime, time

from pytz import timezone, utc

from odoo.addons.hr_rfid.tests.hardware import one_door  # noqa: F401  (the tests of this module take it from here)

SOFIA = timezone("Europe/Sofia")


def passage(employee, door, reader, moment):
    """Somebody walks through the door and is let in."""
    return employee.env["hr.rfid.event.user"].create(
        {
            "employee_id": employee.id,
            "door_id": door.id,
            "reader_id": reader.id,
            "event_time": moment,
            "event_action": "1",
        }
    )


def in_sofia(day, hour, minute=0):
    """The moment the clock on a Sofia wall says, as naive UTC."""
    moment = SOFIA.localize(datetime.combine(day, time(hour, minute)))
    return moment.astimezone(utc).replace(tzinfo=None)
