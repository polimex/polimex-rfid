"""Only read commands may ever leave the survey - proven at the sender.

Business statement (owner, 2026-09-03): "командите към контролерите са строго
само за четене". The survey must be usable on a customer's working system with
no risk of wiping a card table, changing a mode or opening a door.
"""
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_hardware_import.helpers import allowlist
from odoo.addons.hr_rfid_hardware_import.helpers.fake_transport import FakeBackend


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_allowlist')
class TestAllowlist(TransactionCase):

    def test_every_write_command_is_refused_before_any_io(self):
        """A card write, a card deletion, a system reset, a door opening and the
        alarm setup write are refused - and the fake module never sees them."""
        backend = FakeBackend({'modules': {'10.0.0.1': {'devices': {1: {'F0': '00' * 32}}}}})
        client = backend.client('10.0.0.1')
        for opcode, data in (('D1', '00' * 19), ('D2', '00' * 10), ('DC', '0303'), ('DC', '0404'),
                             ('DB', '0100'), ('D5', '02'), ('D7', '00' * 7), ('D9', '00' * 8),
                             ('DE', '01'), ('DA', ''), ('B0', '00010100'), ('B1', '00' * 7), ('BF', '')):
            with self.assertRaises(allowlist.ForbiddenOpcode, msg=opcode):
                client.cmd(1, opcode, data)
        self.assertEqual(backend.commands_sent(), [], "nothing reached the module")

    def test_read_commands_pass(self):
        for opcode, data in (('F0', ''), ('F2', '0000000000'), ('F3', '01'), ('F3', '0F'), ('F4', '08'),
                             ('B0', '01'), ('B3', ''), ('FC', '')):
            self.assertEqual(allowlist.check_allowed(opcode, data), opcode)

    def test_schedule_slot_zero_is_refused(self):
        """Slot 0 is not a schedule; asking for it returns the controller's
        configuration page, so the survey refuses to ask."""
        with self.assertRaises(allowlist.ForbiddenOpcode):
            allowlist.check_allowed('F3', '00')
        with self.assertRaises(allowlist.ForbiddenOpcode):
            allowlist.check_allowed('F3', '10')
        with self.assertRaises(allowlist.ForbiddenOpcode):
            allowlist.check_allowed('F4', '09')

    def test_event_pool_is_not_read(self):
        """Reading the event pool is harmless alone but is only ever paired with
        the confirmation that moves the controller's pointer; the survey
        stays out of it."""
        with self.assertRaises(allowlist.ForbiddenOpcode):
            allowlist.check_allowed('FA', '')

    def test_module_paths_outside_the_read_interface_are_refused(self):
        for method, path in (('GET', '/protect/config.htm'), ('POST', '/protect/config.htm'),
                             ('GET', '/sdk/cmd.json?scan=1&from=1&to=254'), ('GET', '/sdk/out.json?out=1&on=1'),
                             ('GET', '/sdk/setkey.json?k=x'), ('GET', '/protect/restart')):
            with self.assertRaises(allowlist.ForbiddenPath, msg=path):
                allowlist.check_http_path(method, path)
        self.assertEqual(allowlist.check_http_path('GET', '/sdk/status.json?dev=3'), '/sdk/status.json')
        self.assertEqual(allowlist.check_http_path('POST', '/sdk/cmd.json'), '/sdk/cmd.json')
