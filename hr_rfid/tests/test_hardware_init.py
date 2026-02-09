# Copyright 2024 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_rfid.tests.controller import RFIDController
from odoo.tests.common import HttpCase, tagged

import logging

_logger = logging.getLogger(__name__)


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestiCON50Init(RFIDController, HttpCase):
    """Test iCON50 controller initialization sequence."""
    _registry_readonly_enabled = False

    def test_icon50_init_sequence(self):
        """Test full iCON50 initialization: F0 → D7 → DC → DC → F6 → F9 → FB → FF → B3."""
        self._add_iCon50()
        self._check_added_controller(self.c_50)
        self._check_no_commands()

    def test_icon50_hw_version(self):
        """Test iCON50 hardware version is correctly parsed from F0 response."""
        self._add_iCon50()
        self.c_50.read()
        self.assertEqual(self.c_50.hw_version, '12', 'iCON50 hw_version should be 12')

    def test_icon50_single_reader(self):
        """Test iCON50 has exactly 1 reader and 1 door."""
        self._add_iCon50()
        self.c_50.read()
        self.assertEqual(self.c_50.readers, 1, 'iCON50 should have 1 reader')
        self.assertEqual(len(self.c_50.door_ids), 1, 'iCON50 should create 1 door')

    def test_icon50_io_table(self):
        """Test iCON50 IO table is properly initialized."""
        self._add_iCon50()
        self.c_50.read()
        self.assertEqual(self.c_50.io_table, self.c_50.default_io_table,
                         'IO table should match default after init')
        self.assertTrue(len(self.c_50.io_table) > 0, 'IO table should not be empty')

    def test_icon50_serial_number(self):
        """Test iCON50 serial number is parsed from F0."""
        self._add_iCon50()
        self.c_50.read()
        self.assertTrue(self.c_50.serial_number != '', 'Serial number should be set')

    def test_icon50_mode(self):
        """Test iCON50 mode is set after initialization."""
        self._add_iCon50()
        self.c_50.read()
        self.assertTrue(self.c_50.mode > 0, 'Mode should be > 0 after init')

    def test_icon50_max_cards(self):
        """Test iCON50 max cards count is parsed."""
        self._add_iCon50()
        self.c_50.read()
        self.assertTrue(self.c_50.max_cards_count > 0, 'Max cards count should be > 0')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestiCON110Init(RFIDController, HttpCase):
    """Test iCON110 controller initialization sequence."""
    _registry_readonly_enabled = False

    def test_icon110_init_sequence(self):
        """Test full iCON110 initialization."""
        self._add_iCon110()
        self._check_added_controller(self.c_110)
        self._check_no_commands()

    def test_icon110_hw_version(self):
        """Test iCON110 hardware version is correctly parsed."""
        self._add_iCon110()
        self.c_110.read()
        self.assertEqual(self.c_110.hw_version, '6', 'iCON110 hw_version should be 6')

    def test_icon110_two_readers(self):
        """Test iCON110 has 2 readers and 2 doors in default mode."""
        self._add_iCon110()
        self.c_110.read()
        self.assertEqual(self.c_110.readers, 2, 'iCON110 should have 2 readers')
        self.assertEqual(len(self.c_110.door_ids), 2, 'iCON110 should create 2 doors in mode 2')

    def test_icon110_io_table(self):
        """Test iCON110 IO table matches default."""
        self._add_iCon110()
        self.c_110.read()
        self.assertEqual(self.c_110.io_table, self.c_110.default_io_table)


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestiCON115Init(RFIDController, HttpCase):
    """Test iCON115 controller initialization - has B0 alarm line read."""
    _registry_readonly_enabled = False

    def test_icon115_init_sequence(self):
        """Test full iCON115 initialization including B0 alarm line protocol."""
        self._add_iCon115()
        self._check_added_controller(self.c_115)
        self._check_no_commands()

    def test_icon115_hw_version(self):
        """Test iCON115 hardware version."""
        self._add_iCon115()
        self.c_115.read()
        self.assertEqual(self.c_115.hw_version, '11', 'iCON115 hw_version should be 11')

    def test_icon115_two_readers(self):
        """Test iCON115 has 2 readers."""
        self._add_iCon115()
        self.c_115.read()
        self.assertEqual(self.c_115.readers, 2, 'iCON115 should have 2 readers')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestiCON130Init(RFIDController, HttpCase):
    """Test iCON130 controller initialization - 4 readers."""
    _registry_readonly_enabled = False

    def test_icon130_init_sequence(self):
        """Test full iCON130 initialization."""
        self._add_iCon130()
        self._check_added_controller(self.c_130)
        self._check_no_commands()

    def test_icon130_hw_version(self):
        """Test iCON130 hardware version."""
        self._add_iCon130()
        self.c_130.read()
        self.assertEqual(self.c_130.hw_version, '17', 'iCON130 hw_version should be 17')

    def test_icon130_four_readers(self):
        """Test iCON130 has 4 readers and appropriate doors."""
        self._add_iCon130()
        self.c_130.read()
        self.assertEqual(self.c_130.readers, 4, 'iCON130 should have 4 readers')
        self.assertTrue(len(self.c_130.door_ids) >= 2, 'iCON130 should create at least 2 doors')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestiCON180Init(RFIDController, HttpCase):
    """Test iCON180 controller initialization - 4 readers."""
    _registry_readonly_enabled = False

    def test_icon180_init_sequence(self):
        """Test full iCON180 initialization."""
        self._add_iCon180()
        self._check_added_controller(self.c_180)
        self._check_no_commands()

    def test_icon180_four_readers(self):
        """Test iCON180 has 4 readers."""
        self._add_iCon180()
        self.c_180.read()
        self.assertEqual(self.c_180.readers, 4, 'iCON180 should have 4 readers')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestRelayControllerInit(RFIDController, HttpCase):
    """Test Relay controller initialization."""
    _registry_readonly_enabled = False

    def test_relay_init_sequence(self):
        """Test full Relay controller initialization."""
        self._add_RelayController()
        self._check_added_controller(self.c_Relay)
        self._check_no_commands()

    def test_relay_hw_version(self):
        """Test Relay controller hardware version."""
        self._add_RelayController()
        self.c_Relay.read()
        self.assertEqual(self.c_Relay.hw_version, '30', 'Relay hw_version should be 30')

    def test_relay_is_relay(self):
        """Test is_relay_ctrl() returns True for relay controller."""
        self._add_RelayController()
        self.assertTrue(self.c_Relay.is_relay_ctrl(), 'Relay controller should be identified as relay')

    def test_relay_readers(self):
        """Test Relay controller has 2 readers."""
        self._add_RelayController()
        self.c_Relay.read()
        self.assertEqual(self.c_Relay.readers, 2, 'Relay should have 2 readers')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestTurnstileInit(RFIDController, HttpCase):
    """Test Turnstile controller initialization - includes FC (APB read)."""
    _registry_readonly_enabled = False

    def test_turnstile_init_sequence(self):
        """Test full Turnstile initialization including FC anti-passback read."""
        self._add_Turnstile()
        self._check_no_commands()

    def test_turnstile_hw_version(self):
        """Test Turnstile hardware version."""
        self._add_Turnstile()
        self.c_turnstile.read()
        self.assertEqual(self.c_turnstile.hw_version, '9', 'Turnstile hw_version should be 9')

    def test_turnstile_readers(self):
        """Test Turnstile has 2 readers."""
        self._add_Turnstile()
        self.c_turnstile.read()
        self.assertEqual(self.c_turnstile.readers, 2, 'Turnstile should have 2 readers')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestTemperatureInit(RFIDController, HttpCase):
    """Test Temperature controller initialization - includes F2/B1 sensor protocol."""
    _registry_readonly_enabled = False

    def test_temperature_init_sequence(self):
        """Test full Temperature controller init including sensor reading (F2/B1)."""
        self._add_Temperature()
        self._check_no_commands()

    def test_temperature_sensors_created(self):
        """Test that temperature sensors are created during init."""
        self._add_Temperature()
        self.c_temperature.read()
        self.assertTrue(len(self.c_temperature.sensor_ids) >= 3,
                        'Temperature controller should have at least 3 sensors (got %d)' %
                        len(self.c_temperature.sensor_ids))

    def test_temperature_cards_count(self):
        """Test cards count (sensors) is parsed from F2 response."""
        self._add_Temperature()
        self.assertEqual(self.c_temperature.cards_count, 4,
                         'Temperature controller cards_count should be 4')

    def test_temperature_hw_version(self):
        """Test Temperature controller hardware version."""
        self._add_Temperature()
        self.c_temperature.read()
        self.assertEqual(self.c_temperature.hw_version, '22', 'Temperature hw_version should be 22')


@tagged('standard', 'at_install', 'rfid', 'rfid_hardware')
class TestVendingInit(RFIDController, HttpCase):
    """Test Vending controller initialization."""
    _registry_readonly_enabled = False

    def test_vending_init_sequence(self):
        """Test full Vending controller initialization."""
        self._add_Vending()
        self._check_no_commands()

    def test_vending_hw_version(self):
        """Test Vending controller hardware version."""
        self._add_Vending()
        self.c_vending.read()
        self.assertEqual(self.c_vending.hw_version, '16', 'Vending hw_version should be 16')
