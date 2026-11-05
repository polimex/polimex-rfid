"""Moments of a Sofia day, as the database keeps them.

Sofia is two or three hours ahead of UTC, which is exactly what makes a day
there and the same date in UTC different stretches of time - the shape every
test of "the person's own day" has to build. Shared by the attendance tests of
this module and of the modules built on it.
"""

from datetime import datetime, time

from pytz import timezone, utc

from odoo import Command

SOFIA = timezone("Europe/Sofia")


def one_door(env, label, number, ctrl_id, tz="Europe/Sofia"):
    """One door with an entry and an exit reader, on a controller of its own.

    The hardware a test of attendance needs and no more. Shape from
    hr_rfid/tests/test_system_event_dedup.py.

    :param number: four digits, the controller's serial
    :return: (door, reader_in, reader_out)
    """
    company = env.company
    webstack = env["hr.rfid.webstack"].create(
        {
            "name": f"{label} WS",
            "serial": f"{number}01",
            "key": "1234",
            "hw_version": "100.1",
            "version": "1.44",
            "active": True,
            "tz": tz,
            "company_id": company.id,
        }
    )
    ctrl = env["hr.rfid.ctrl"].create(
        {
            "name": f"{label} CTRL",
            "ctrl_id": ctrl_id,
            "serial_number": str(number),
            "webstack_id": webstack.id,
            "hw_version": "9",
            "sw_version": "740",
            "max_cards_count": 100,
            "max_events_count": 100,
            "readers": 2,
            "mode": 2,
            "inputs": 0,
            "outputs": 0,
            "input_states": 0,
            "output_states": 0,
            "alarm_lines": 0,
            "io_table_lines": 0,
            "io_table": "",
        }
    )
    quiet = env["hr.rfid.door"].with_context(no_hardware_commands=True)
    door = quiet.create(
        {
            "name": f"{label} Door",
            "number": 1,
            "controller_id": ctrl.id,
            "card_type": env.ref("hr_rfid.hr_rfid_card_type_def").id,
        }
    )
    readers = env["hr.rfid.reader"].with_context(no_hardware_commands=True)
    reader_in = readers.create(
        {
            "name": f"{label} In",
            "number": 1,
            "reader_type": "0",
            "controller_id": ctrl.id,
            "door_ids": [Command.link(door.id)],
        }
    )
    reader_out = readers.create(
        {
            "name": f"{label} Out",
            "number": 2,
            "reader_type": "1",
            "controller_id": ctrl.id,
            "door_ids": [Command.link(door.id)],
        }
    )
    return door, reader_in, reader_out


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
