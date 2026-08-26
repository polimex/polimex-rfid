# -*- coding: utf-8 -*-
# Part of Polimex Modules. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "rfid_th")
class TestEnvironmentReadings(TransactionCase):
    """What the environment history is supposed to say.

    The owner of a server room reads this history to answer "how warm did it
    get last night". That answer is only worth something if a reading the
    device took appears ONCE, at the hour the device took it - a second copy
    stamped with the moment our server happened to receive it turns the graph
    into noise and doubles the table for no information.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
        cls.webstack = cls.env["hr.rfid.webstack"].create({
            "name": "TH WS", "serial": "990001", "key": "1234",
            "hw_version": "100.1", "version": "1.44", "active": True,
            "tz": "Europe/Sofia", "company_id": company.id})
        cls.ctrl = cls.env["hr.rfid.ctrl"].create({
            "name": "TH CTRL", "ctrl_id": 9, "serial_number": "9901",
            "webstack_id": cls.webstack.id, "hw_version": "9",
            "sw_version": "740", "max_cards_count": 100,
            "max_events_count": 100, "readers": 2, "mode": 2, "inputs": 0,
            "outputs": 0, "input_states": 0, "output_states": 0,
            "alarm_lines": 0, "io_table_lines": 0, "io_table": ""})
        # sensor_number 0 is the controller's own first sensor - the ordinary
        # case on a customer site, and the only one this history is kept for.
        cls.sensor = cls.env["hr.rfid.ctrl.th"].create({
            "name": "Server Room", "sensor_number": 0,
            "internal_number": "1", "uid": "28FF000000000001",
            "controller_id": cls.ctrl.id})

    def test_a_reported_reading_is_written_down_once(self):
        """A reading the device reports lands in the history once, at ITS time."""
        measured_at = datetime(2026, 8, 20, 3, 0, 0)
        self.sensor.write_log(measured_at, {"t": 19.5, "h": 55.0})

        logs = self.env["hr.rfid.ctrl.th.log"].search(
            [("th_id", "=", self.sensor.id)])
        self.assertEqual(
            len(logs), 1,
            "One reading from the device must leave one row in the history, "
            "not a second copy stamped with the moment it reached us",
        )
        self.assertEqual(
            logs.event_time, measured_at,
            "The row must carry the time the device measured, not now()",
        )
        self.assertEqual(logs.temperature, 19.5)
        self.assertEqual(logs.humidity, 55.0)

    def test_a_polled_reading_is_still_written_down(self):
        """The other way readings arrive must keep being recorded.

        Besides the reported events, the controller is polled every few
        minutes and the values are written straight onto the sensor. Nothing
        else records those, so silencing that path would quietly empty the
        history of every installation that only polls.
        """
        self.sensor.write({"temperature": 24.5, "humidity": 38.0})

        logs = self.env["hr.rfid.ctrl.th.log"].search(
            [("th_id", "=", self.sensor.id)])
        self.assertEqual(
            len(logs), 1,
            "A polled reading must still reach the history",
        )
        self.assertEqual(logs.temperature, 24.5)

    def test_an_unchanged_reading_adds_no_row(self):
        """Repeating the same value is not new information.

        The history exists to show when the room changed. A sensor that
        reports the same 21.0 every two minutes must not fill the table with
        identical rows - that is what the 'Log All Readings' switch is for.
        """
        self.sensor.write_log(datetime(2026, 8, 20, 3, 0, 0), {"t": 21.0})
        self.sensor.write_log(datetime(2026, 8, 20, 3, 2, 0), {"t": 21.0})

        logs = self.env["hr.rfid.ctrl.th.log"].search(
            [("th_id", "=", self.sensor.id)])
        self.assertEqual(
            len(logs), 1,
            "The same temperature reported twice is one entry in the history",
        )
