# Copyright 2026 Polimex Holding Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from odoo.addons.hr_rfid.tests.controller import RFIDController


@tagged('standard', 'at_install', 'rfid', 'rfid_alarm')
class TestAlarmLineStateParse(RFIDController):
    """Regression guard for the _get_alarm_line_state error path.

    A malformed alarm_line_states byte string used to swallow the parse
    error with a print() and then read an unbound `state` (latent
    NameError, reachable from the controller form's computed alarm fields).
    The fix logs a warning and returns the safe ('no_alarm', 'unknown')
    fallback. These tests lock that behaviour in.
    """

    def _ctrl(self, alarm_line_states):
        ctrl = self.env['hr.rfid.ctrl'].with_context(
            no_hardware_commands=True).create({
                'name': 'Alarm Probe',
                'ctrl_id': 99,
                'webstack_id': self.test_webstack_10_3_id.id,
            })
        ctrl.alarm_line_states = alarm_line_states
        return ctrl

    def test_non_hex_state_returns_unknown_without_raising(self):
        ctrl = self._ctrl('ZZ')  # int('ZZ', 16) -> ValueError
        self.assertEqual(ctrl._get_alarm_line_state(1), ('no_alarm', 'unknown'))

    def test_too_short_state_returns_unknown_without_raising(self):
        ctrl = self._ctrl('1')   # slice for zone 5 is '' -> ValueError
        self.assertEqual(ctrl._get_alarm_line_state(5), ('no_alarm', 'unknown'))

    def test_empty_state_returns_unknown(self):
        # The pre-existing early return for the empty/'0' sentinel.
        ctrl = self._ctrl('0')
        self.assertEqual(ctrl._get_alarm_line_state(1), ('no_alarm', 'unknown'))

    def test_valid_state_still_parses(self):
        # 0x41 -> bit6 (arm) + bit0 (short); zone 1 reads chars [0:2].
        ctrl = self._ctrl('41')
        self.assertEqual(ctrl._get_alarm_line_state(1), ('arm', 'short'))
