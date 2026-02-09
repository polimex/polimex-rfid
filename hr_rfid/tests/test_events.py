# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import unittest
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestUserEventsICON50(RFIDController, HttpCase):
    """Test user events on iCON50 (single reader controller)."""
    _registry_readonly_enabled = False

    def test_reader_events_3_to_6(self):
        """Test reader events 3 (granted), 4 (denied no access), 5 (denied ts), 6 (denied APB)."""
        self._add_iCon50()
        user_events_count = self._count_user_events()
        self._make_event(self.c_50, reader=1, event_code=3)
        self._make_event(self.c_50, reader=1, event_code=4)
        self._make_event(self.c_50, reader=1, event_code=5)
        self._make_event(self.c_50, reader=1, event_code=6)
        self.assertEqual(user_events_count + 4, self._count_user_events(),
                         'Should create 4 user events')

    def test_unknown_card_creates_system_event(self):
        """Test unknown card generates system event instead of user event."""
        self._add_iCon50()
        system_events_count = self._count_system_events()
        self._make_event(self.c_50, card='1122334455', reader=1, event_code=4)
        self.assertEqual(system_events_count + 1, self._count_system_events(),
                         'Unknown card should create system event')

    def test_duress_events(self):
        """Test duress events (1, 2) on all readers."""
        self._add_iCon50()
        self._test_Duress(self.c_50)

    def test_all_reader_events(self):
        """Test complete reader event sequence on iCON50."""
        self._add_iCon50()
        self._test_R_event(self.c_50, 1)


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestUserEventsICON110(RFIDController, HttpCase):
    """Test user events on iCON110 (2 reader controller)."""
    _registry_readonly_enabled = False

    def test_reader1_events(self):
        """Test events on reader 1."""
        self._add_iCon110()
        self._test_R_event(self.c_110, 1)

    def test_reader2_events(self):
        """Test events on reader 2."""
        self._add_iCon110()
        self._test_R_event(self.c_110, 2)

    def test_duress_both_readers(self):
        """Test duress events on both readers."""
        self._add_iCon110()
        self._test_Duress(self.c_110)


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestUserEventsICON130(RFIDController, HttpCase):
    """Test user events on iCON130 (4 reader controller)."""
    _registry_readonly_enabled = False

    def test_all_four_readers(self):
        """Test events on all 4 readers."""
        self._add_iCon130()
        self._test_R1R2R3R4(self.c_130)


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestSystemEvents(RFIDController, HttpCase):
    """Test system events: emergency, exit, overtime, force open, power on, external."""
    _registry_readonly_enabled = False

    def test_emergency_events(self):
        """Test emergency events (event 19) on reader 1, 1+64 (off), and 0 (hardware)."""
        self._add_iCon50()
        self._test_Emergency(self.c_50)

    def test_exit_button_events(self):
        """Test exit button events (event 21) on all doors."""
        self._add_iCon110()
        self._test_Exit_buttons(self.c_110)

    def test_door_overtime_events(self):
        """Test door overtime events (event 25) with command generation."""
        self._add_iCon110()
        self._test_Door_Overtime(self.c_110)

    def test_force_door_open_events(self):
        """Test force door open events (event 26)."""
        self._add_iCon110()
        self._test_Force_Door_Open(self.c_110)

    def test_power_on_event(self):
        """Test power on event (event 30) triggers time sync command."""
        self._add_iCon50()
        self._test_Power_On(self.c_50)

    def test_external_control_event(self):
        """Test external control event (event 29)."""
        self._add_iCon50()
        self._test_External_control(self.c_50)

    def test_all_system_events(self):
        """Test full system events sequence on iCON50."""
        self._add_iCon50()
        self._test_inputs(self.c_50)
        self._check_no_commands()


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestEvent64CloudCard(RFIDController, HttpCase):
    """Test event 64 - cloud card (external database) requests.
    Tests the full ev64 flow: denied (no doors) → granted (doors added) → denied (delay).
    The test simulates the hardware follow-up Granted event after the ev64 grant response,
    because _calc_last_user_event_in_ag searches for event_action='1' (Granted) to check delay.
    """
    _registry_readonly_enabled = False

    def test_ev64_icon50(self):
        """Test external DB card request on iCON50."""
        self._add_iCon50()
        self._ev64(self.c_50)
        self._check_no_commands()

    def test_ev64_icon110(self):
        """Test external DB card request on iCON110."""
        self._add_iCon110()
        self._ev64(self.c_110)
        self._check_no_commands()

    def test_ev64_icon115(self):
        """Test external DB card request on iCON115."""
        self._add_iCon115()
        self._ev64(self.c_115)
        self._check_no_commands()

    def test_ev64_icon130(self):
        """Test external DB card request on iCON130."""
        self._add_iCon130()
        self._ev64(self.c_130)
        self._check_no_commands()

    def test_ev64_icon180(self):
        """Test external DB card request on iCON180."""
        self._add_iCon180()
        self._ev64(self.c_180)
        self._check_no_commands()


@tagged('standard', 'at_install', 'rfid', 'rfid_events')
class TestTurnstileSpecialEvents(RFIDController, HttpCase):
    """Test turnstile-specific events including reader 65."""
    _registry_readonly_enabled = False

    def test_turnstile_reader_events(self):
        """Test events on turnstile readers 1 and 2."""
        self._add_Turnstile()
        self._test_R1R2(self.c_turnstile)

    def test_turnstile_reader_65(self):
        """Test special reader 65 events on turnstile."""
        self._add_Turnstile()
        response = self._make_event(self.c_turnstile, reader=65, event_code=3)
        self.assertEqual(response, {}, 'Reader 65 event should be processed')
        response = self._make_event(self.c_turnstile, reader=65, event_code=3)
        self.assertEqual(response, {}, 'Second reader 65 event should be processed')
        self._check_no_commands()
