# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.room.tests.common import RoomCommon
from odoo.tests.common import tagged, users

@tagged("room_acl")
class TestRoomSecurity(RoomCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.room_manager = mail_new_test_user(
            cls.env,
            groups='room.group_room_manager',
            login='room_manager',
            name='Room Manager',
        )

        cls.public_user = mail_new_test_user(
            cls.env,
            groups='base.group_public',
            login='public_user',
            name='Public user',
        )

    @users('public_user')
    def test_models_as_public(self):
        # Booking
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Booking access to public"):
            self.env["room.booking"].search([])

        # Office
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Office access to public"):
            self.env["room.office"].search([])

        # Room
        with self.assertRaises(exceptions.AccessError, msg="ACLs: No Room access to public"):
            self.env["room.room"].search([])

    @users('employee')
    def test_models_as_employee(self):
        # Office
        with self.assertRaises(exceptions.AccessError, msg="ACLs: Readonly access on office"):
            self.office.with_env(self.env).write({"name": "Office 2"})

        # Room
        with self.assertRaises(exceptions.AccessError, msg="ACLs: Readonly access on room"):
            self.rooms[0].with_env(self.env).write({"name": "Room 2"})
