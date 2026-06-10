# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import etree

from odoo.tests.common import HttpCase, tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController


@tagged('standard', 'at_install', 'rfid', 'rfid_interlocking')
class TestInterlockingMode(RFIDController, HttpCase):
    """E2E for contr_mode bit 4 (interlocking / legacy master card).

    The controller-mode byte (D5 command, F0 response[42:44]) packs:
      bit6 relay factor, bit5 external DB, bit4 interlocking, bit3 dual
      person, bits0-2 mode. Bit 4 used to be neither read nor written, so
      every mode write silently zeroed interlocking on the hardware. These
      tests walk the full hardware<->Odoo round trip on an iCON115.
    """

    readonly_enabled = False

    def _drain_io_table(self, response):
        """Consume the follow-up D9 io-table commands an F0 read queues."""
        while response != {} and response['cmd']['c'] == 'D9':
            response = self._send_cmd_response(response)
        return response

    def test_decode_reads_interlocking_bit(self):
        """Hardware reports bit 4 set in contr_mode -> Odoo stores it."""
        self._add_iCon115()
        ctrl = self.c_115
        self.assertFalse(ctrl.interlocking_mode, "starts off")

        f0 = self.default_F0[int(ctrl.hw_version)]
        patched = '%02X' % (int(f0[42:44], 16) | 0x10)
        f0_interlocked = f0[:42] + patched + f0[44:]

        ctrl.read_controller_information_cmd()
        response = self._hearbeat(ctrl.webstack_id)
        self.assertEqual(response['cmd']['c'], 'F0', '(%s)' % ctrl.name)
        response = self._send_cmd_response(response, f0_interlocked)
        self._drain_io_table(response)

        self.assertTrue(
            ctrl.interlocking_mode,
            "Bit 4 of contr_mode must be decoded into interlocking_mode",
        )
        # The mode (bits 0-2) must still be read correctly alongside it.
        self.assertTrue(1 <= ctrl.mode <= 4)

    def test_encode_includes_interlocking_bit(self):
        """Enabling interlocking -> the D5 mode byte carries bit 0x10."""
        self._add_iCon115()
        cmd = self.c_115.write_controller_mode(new_mode=2, new_interlocking_mode=True)
        byte = int(cmd.cmd_data, 16)
        self.assertTrue(byte & 0x10, "interlocking bit set in the D5 byte")
        self.assertEqual(byte & 0x07, 2, "mode bits intact")

    def test_default_has_no_interlocking_bit(self):
        """A plain mode write leaves bit 4 clear."""
        self._add_iCon115()
        cmd = self.c_115.write_controller_mode(new_mode=2)
        self.assertFalse(int(cmd.cmd_data, 16) & 0x10)

    def test_mode_write_preserves_interlocking(self):
        """THE BUGFIX: changing another mode flag must NOT zero bit 4.

        Before the fix, write_controller_mode rebuilt the byte without the
        interlocking bit, so toggling dual-person mode wiped interlocking on
        the controller.
        """
        self._add_iCon115()
        ctrl = self.c_115
        ctrl.interlocking_mode = True            # stored + first D5 queued
        ctrl.dual_person_mode = True             # an unrelated mode write

        d5 = self.env['hr.rfid.command'].search(
            [('controller_id', '=', ctrl.id), ('cmd', '=', 'D5'),
             ('status', '=', 'Wait')],
            order='id desc', limit=1,
        )
        self.assertTrue(d5, "a D5 mode command must be queued")
        byte = int(d5.cmd_data, 16)
        self.assertTrue(byte & 0x10, "interlocking survives the dual-person write")
        self.assertTrue(byte & 0x08, "dual person bit also set")

    def test_write_triggers_hardware_command(self):
        """Setting interlocking_mode from Odoo pushes a D5 to the controller."""
        self._add_iCon115()
        ctrl = self.c_115
        ctrl.interlocking_mode = True
        response = self._hearbeat(ctrl.webstack_id)
        self.assertEqual(response['cmd']['c'], 'D5', '(%s)' % ctrl.name)
        self.assertTrue(int(response['cmd']['d'], 16) & 0x10)

    def test_field_gated_to_supporting_controllers(self):
        """UI: interlocking_mode is hidden unless hw is iCON115/iCON130."""
        view = self.env.ref('hr_rfid.hr_rfid_controller_view_form')
        arch = self.env['hr.rfid.ctrl'].get_view(view.id, 'form')['arch']
        node = etree.fromstring(arch).xpath("//field[@name='interlocking_mode']")
        self.assertTrue(node, "interlocking_mode must be on the controller form")
        invisible = node[0].get('invisible', '')
        self.assertIn('hw_version', invisible)
        self.assertIn('11', invisible)
        self.assertIn('17', invisible)
