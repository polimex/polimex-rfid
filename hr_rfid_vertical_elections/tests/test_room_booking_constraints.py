# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.room.tests.common import RoomCommon
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

@tagged("post_install", "-at_install")
class TestRoomBookingConstraints(RoomCommon):

    def test_booking_no_overlap(self):
        room_booking = self.env["room.booking"]
        # Create a booking overlapping an existing booking
        with self.assertRaises(ValidationError, msg="Bookings may not overlap"):
            room_booking.create({
                "name": "Meeting",
                "room_id": self.rooms[0].id,
                "start_datetime": datetime(2023, 5, 15, 10, 30),
                "stop_datetime": datetime(2023, 5, 15, 11, 30),
            })

        # Create two bookings that overlap
        with self.assertRaises(ValidationError, msg="Bookings may not overlap"):
            room_booking.create([
                {
                    "name": "Meeting 1",
                    "room_id": self.rooms[0].id,
                    "start_datetime": datetime(2023, 5, 15, 13, 0),
                    "stop_datetime": datetime(2023, 5, 15, 14, 0),
                }, {
                    "name": "Meeting 2",
                    "room_id": self.rooms[0].id,
                    "start_datetime": datetime(2023, 5, 15, 13, 30),
                    "stop_datetime": datetime(2023, 5, 15, 14, 30),
                }
            ])
