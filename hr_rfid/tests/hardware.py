"""The smallest hardware a test needs, made in the database and not by a handshake.

A module, one controller on it, one door, a reader in and a reader out. The
tests that are about what the hardware SAYS (the handshake, the set-up
sequence) build theirs through the endpoint (tests/controller.py); every other
test only needs it to exist. Shared with the modules built on this one.
"""

from odoo import Command


def one_door(
    env,
    label,
    number,
    ctrl_id,
    tz="Europe/Sofia",
    *,
    serial=None,
    hw_version="100.1",
    version="1.44",
    key="1234",
):
    """One door with an entry and an exit reader, on a controller of its own.

    :param number: four digits, the controller's serial
    :param serial: the module's serial; by default made from ``number``. A
                   serial starting with '4' is an iCON1XX 100.1, anything else
                   an older module (hr.rfid.webstack._serial_is_100_1) - which
                   decides the shape of every reply the module gets.
    :return: (door, reader_in, reader_out)
    """
    company = env.company
    webstack = env["hr.rfid.webstack"].create(
        {
            "name": f"{label} WS",
            "serial": serial or f"{number}01",
            "key": key,
            "hw_version": hw_version,
            "version": version,
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
            "hw_version": "11",
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
