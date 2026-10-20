"""Moments of a Sofia day, as the database keeps them.

Sofia is two or three hours ahead of UTC, which is exactly what makes a day
there and the same date in UTC different stretches of time - the shape every
test of "the person's own day" has to build. Shared by the attendance tests of
this module and of the modules built on it.
"""

from datetime import datetime, time

from pytz import timezone, utc

SOFIA = timezone("Europe/Sofia")


def in_sofia(day, hour, minute=0):
    """The moment the clock on a Sofia wall says, as naive UTC."""
    moment = SOFIA.localize(datetime.combine(day, time(hour, minute)))
    return moment.astimezone(utc).replace(tzinfo=None)
