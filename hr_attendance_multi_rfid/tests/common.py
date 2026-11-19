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


def set_public_holidays_aside(env):
    """Hold the public holidays already in the database off every schedule.

    A public holiday with no schedule holds for every schedule of its company
    (resource/models/resource_calendar.py:515) - the demo's, a localisation's,
    a customer's - so a test that speaks of an ordinary day finds a holiday on
    it on such a database. They are moved to a schedule nobody in the test
    works on, in SQL: through the ORM core would plan everybody's time off
    again (hr_holidays/models/resource.py, write). Each test then makes the
    holidays it talks about (skill odoo19-gotchas, tests.md).
    """
    aside = env["resource.calendar"].create(
        {"name": "Public holidays set aside (test)"}
    )
    env.flush_all()
    env.cr.execute(
        "UPDATE resource_calendar_leaves SET calendar_id = %s WHERE resource_id IS NULL",
        [aside.id],
    )
    env.invalidate_all()
    return aside
