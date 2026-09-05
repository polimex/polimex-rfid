"""The module's decoders against the protocol library's canonical vectors.

The vectors are private (they carry the wire formats) and are never part of
this repository: the test reads them from the path in the environment
variable POLIMEX_PROTOCOL_VECTORS and is skipped when it is not set. Verified
against polimex-protocol 0.1.1 (tag polimex-protocol-v0.1.1).

Business statement: what the survey reads from a controller is exactly what
the protocol's own reference implementation reads from the same bytes.
"""
import json
import os

from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_hardware_import.helpers import codecs

#: Vectors whose expectation is under discussion with the protocol owners;
#: reported, not silently accepted. Key = vector name, value = reason.
KNOWN_DISAGREEMENTS = {}
INPUT_MASK_FN = 'io.decode_get_input_mask_response'


def _short(fn):
    return fn.replace('polimex_protocol.commands.', '').replace('polimex_protocol.', '')


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_oracle')
class TestOracleVectors(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = os.environ.get('POLIMEX_PROTOCOL_VECTORS')
        cls.vectors = []
        if path and os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                cls.vectors = json.load(handle)['vectors']

    def _need_vectors(self):
        if not self.vectors:
            self.skipTest("POLIMEX_PROTOCOL_VECTORS is not set; the private canonical vectors are unavailable")

    def _each(self, fn):
        for vector in self.vectors:
            if _short(vector['fn']) == fn and vector['kind'] == 'decode':
                if vector['name'] in KNOWN_DISAGREEMENTS:
                    continue
                yield vector

    def test_card_records(self):
        self._need_vectors()
        checked = 0
        for vector in self._each('cards.decode_card_full'):
            size = 20 if vector.get('extra_args', {}).get('has_alarm_zones') else 19
            rec = codecs.decode_card_record(vector['payload_hex'], size)
            expected = vector['decoded']
            self.assertEqual(rec['number'], expected['card_number'], vector['name'])
            self.assertEqual(rec['pin'] or '0000', expected['pin_code'], vector['name'])
            self.assertEqual(rec['ts'], expected['reader_ts'], vector['name'])
            self.assertEqual([bool(b) for b in rec['reader_bits']], expected['reader_rights'], vector['name'])
            self.assertEqual((rec['apb1'], rec['apb2']), (expected['apb1'], expected['apb2']), vector['name'])
            self.assertEqual(rec['rights'], expected['rights_byte'], vector['name'])
            self.assertEqual(rec['alarm_bits'], expected['alarm_rights'], vector['name'])
            checked += 1
        for vector in self._each('cards.decode_cards_page_full'):
            size = 20 if vector.get('extra_args', {}).get('has_alarm_zones') else 19
            page = codecs.decode_cards_page(vector['payload_hex'], size)
            self.assertEqual([r['number'] for r in page], [e['card_number'] for e in vector['decoded']], vector['name'])
            self.assertEqual([r['rights'] for r in page], [e['rights_byte'] for e in vector['decoded']], vector['name'])
            checked += 1
        for vector in self._each('cards.decode_cards_count'):
            self.assertEqual(codecs.decode_f2_count(vector['payload_hex']), vector['decoded'], vector['name'])
            checked += 1
        self.assertGreater(checked, 0)

    def test_system_information(self):
        self._need_vectors()
        checked = 0
        for vector in self._each('responses.decode_version'):
            if vector['decoded'].get('truncated'):
                continue
            dec = codecs.decode_f0(vector['payload_hex'])
            expected = vector['decoded']
            self.assertEqual(int(dec['hw_code']), expected['hw_code'], vector['name'])
            self.assertEqual(int(dec['serial']), expected['serial_number'], vector['name'])
            self.assertEqual(int(dec['sw_version']), expected['sw_version'], vector['name'])
            self.assertEqual(dec['inputs'], expected['num_inputs'], vector['name'])
            self.assertEqual(dec['outputs'], expected['num_outputs'], vector['name'])
            self.assertEqual(dec['readers'], expected['num_readers'], vector['name'])
            self.assertEqual(dec['time_schedules'], expected['time_schedules'], vector['name'])
            self.assertEqual(dec['io_table_lines'], expected['io_table_lines'], vector['name'])
            self.assertEqual(dec['alarm_lines'], expected['alarm_lines'], vector['name'])
            self.assertEqual(dec['mode_byte'], expected['mode_byte'], vector['name'])
            self.assertEqual(dec['max_cards'], expected['max_cards'], vector['name'])
            self.assertEqual(dec['max_events'], expected['max_events'], vector['name'])
            checked += 1
        self.assertGreater(checked, 0)

    def test_modes_and_settings(self):
        self._need_vectors()
        checked = 0
        for vector in self._each('mode.decode_read_controller_mode_response'):
            dec = codecs.decode_f5(vector['payload_hex'])
            expected = vector['decoded']
            self.assertEqual(dec['mode'], expected['mode'], vector['name'])
            self.assertEqual(dec['dual_person'], expected['dual_person'], vector['name'])
            self.assertEqual(dec['interlocking'], expected['interlocking_master_card'], vector['name'])
            self.assertEqual(dec['external_db'], expected['external_db'], vector['name'])
            self.assertEqual(dec['relay_time_factor'], expected['relay_time_factor'], vector['name'])
            checked += 1
        for vector in self._each('mode.decode_get_reader_mode_response'):
            dec = codecs.decode_reader_modes(vector['payload_hex'])
            self.assertEqual([(int(r['mode']), r['mode_ts'], r['ts']) for r in dec],
                             [(e['mode_n'], e['mode_ts'], e['ts']) for e in vector['decoded']], vector['name'])
            checked += 1
        for vector in self._each('apb.decode_get_apb_response'):
            bitmap = codecs.decode_apb(vector['payload_hex'])
            for door in (1, 2, 3):
                self.assertEqual(codecs.door_apb(bitmap, door), vector['decoded']['door_%d' % door], vector['name'])
            checked += 1
        for vector in self._each('sot.decode_sot_response'):
            dec = codecs.decode_alarm_setup(vector['payload_hex'])
            expected = vector['decoded']
            self.assertEqual(dec['disable_readers'], expected['disable_readers'], vector['name'])
            self.assertEqual(dec['disable_door_contacts'], expected['disable_door_contacts'], vector['name'])
            self.assertEqual(dec['zones_enabled'], expected['zones_enabled'], vector['name'])
            self.assertEqual(dec['sensor_events'], expected['save_event_34'], vector['name'])
            checked += 1
        for vector in self._each(INPUT_MASK_FN):
            mask, relay_bytes = codecs.decode_input_masks(vector['payload_hex'])
            self.assertEqual(mask, vector['decoded']['input_mask'], vector['name'])
            checked += 1
        for vector in self._each('time_schedules.decode_read_out_ts_response'):
            self.assertEqual(codecs.decode_output_ts(vector['payload_hex'], 8), vector['decoded'], vector['name'])
            checked += 1
        self.assertGreater(checked, 0)

    def test_schedules_holidays_clock(self):
        self._need_vectors()
        checked = 0
        for vector in self._each('time_schedules.decode_read_ts_response'):
            dec = codecs.decode_ts(vector['payload_hex'])
            slot, days, holiday_ref = vector['decoded']
            self.assertEqual(dec['slot'], slot, vector['name'])
            self.assertEqual(dec['holiday_ref'], holiday_ref, vector['name'])
            for day_index, intervals in enumerate(days):
                ours = dec['grid'][day_index]
                for n, interval in enumerate(intervals):
                    expected = ('%02d:%02d' % (interval['begin_hour'], interval['begin_minute']),
                                '%02d:%02d' % (interval['end_hour'], interval['end_minute']))
                    if expected == ('00:00', '00:00'):
                        self.assertIsNone(ours[n], vector['name'])
                    else:
                        self.assertEqual(ours[n], expected, vector['name'])
            checked += 1
        for vector in self._each('time_schedules.decode_read_holiday_response'):
            dec = codecs.decode_holidays(vector['payload_hex'])
            slot, dates = vector['decoded']
            self.assertEqual(dec['slot'], slot, vector['name'])
            self.assertEqual([list(d) for d in dec['dates']], dates, vector['name'])
            checked += 1
        for vector in self._each('system.decode_get_time_response'):
            clock = codecs.decode_clock(vector['payload_hex'])
            if vector['decoded'] is None:
                self.assertIsNone(clock, vector['name'])
            else:
                self.assertEqual(clock.isoformat(), vector['decoded'], vector['name'])
            checked += 1
        self.assertGreater(checked, 0)

    def test_status(self):
        self._need_vectors()
        checked = 0
        for vector in self._each('status.decode_controller_status'):
            dec = codecs.decode_status(vector['payload_hex'])
            expected = vector['decoded']
            self.assertAlmostEqual(dec['system_voltage'], expected['system_voltage'], places=3, msg=vector['name'])
            self.assertAlmostEqual(dec['input_voltage'], expected['input_voltage'], places=3, msg=vector['name'])
            self.assertEqual(dec['zones'], expected['alarm_zones'], vector['name'])
            self.assertEqual(dec['time_of_service'], expected['tos'], vector['name'])
            if expected.get('temperature') is not None:
                self.assertAlmostEqual(dec['temperature'], expected['temperature'], places=1, msg=vector['name'])
            checked += 1
        self.assertGreater(checked, 0)
