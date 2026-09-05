"""The survey reads the same bytes the access control module writes.

Business statement: what the survey shows for a controller must be what the
access control module itself would show for that controller - the same doors,
the same readers, the same schedule format. The oracle here is the core module
(its F0 parser, its schedule format, its door layout), not this module's code.
"""
from odoo.addons.hr_rfid.controllers.polimex import HW_TYPES
from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_rfid_hardware_import.helpers import codecs


def make_f0(hw, serial, sw, inputs, outputs, readers, ts, io, alarm, mode, max_cards, max_events):
    def digits(value, width):
        return ''.join('%02d' % int(d) for d in ('%0*d' % (width, value)))
    return (digits(hw, 2) + digits(serial, 4) + digits(sw, 3) + digits(inputs, 3) + digits(outputs, 3)
            + '%02d' % readers + digits(ts, 2) + digits(io, 2) + '%02d' % alarm + '%02X' % mode
            + digits(max_cards, 5) + digits(max_events, 5))


def card_record(number, pin, ts, rights, alarm=None):
    def digits(value, width):
        return ''.join('%02d' % int(d) for d in ('%0*d' % (width, value)))
    hexs = digits(int(number), 10) + digits(int(pin or 0), 4) + ''.join('%02X' % t for t in ts) + '%02X' % rights
    if alarm is not None:
        hexs += '%02X' % alarm
    return hexs


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_codecs')
class TestCodecs(TransactionCase):

    def test_system_information_decodes_like_the_core_parser(self):
        """The same reply gives the same hardware, serial, firmware and limits as
        the access control module's own parser."""
        f0 = make_f0(10, 1801, 748, 10, 8, 4, 15, 28, 4, 0x22, 7679, 4094)
        ours = codecs.decode_f0(f0)
        theirs = self.env['hr.rfid.command']._parse_f0_cmd(f0)
        from odoo.addons.hr_rfid.models.hr_rfid_command import F0Parse
        self.assertEqual(ours['hw_code'], theirs[F0Parse.hw_ver])
        self.assertEqual(ours['serial'], theirs[F0Parse.serial_num])
        self.assertEqual(ours['sw_version'], theirs[F0Parse.sw_ver])
        self.assertEqual(ours['inputs'], theirs[F0Parse.inputs])
        self.assertEqual(ours['outputs'], theirs[F0Parse.outputs])
        self.assertEqual(ours['time_schedules'], theirs[F0Parse.time_schedules])
        self.assertEqual(ours['io_table_lines'], theirs[F0Parse.io_table_lines])
        self.assertEqual(ours['alarm_lines'], theirs[F0Parse.alarm_lines])
        self.assertEqual(ours['max_cards'], theirs[F0Parse.max_cards_count])
        self.assertEqual(ours['max_events'], theirs[F0Parse.max_events_count])
        self.assertEqual(ours['readers'], 4)
        self.assertEqual(ours['mode'], 2)
        self.assertTrue(ours['external_db'])
        self.assertFalse(ours['relay_time_factor'])

    def test_reader_door_layout_matches_the_core_for_every_mode(self):
        """The doors and readers the survey assumes are the ones the access
        control module builds for the same controller."""
        cases = [
            ('6', 1, 2, {1: [1, 2]}, {1: '0', 2: '1'}),
            ('6', 2, 2, {1: [1], 2: [2]}, {1: '0', 2: '0'}),
            ('10', 2, 4, {1: [1, 2], 2: [3, 4]}, {1: '0', 2: '1', 3: '0', 4: '1'}),
            ('10', 3, 4, {1: [1, 2], 2: [3], 3: [4]}, {1: '0', 2: '1', 3: '0', 4: '0'}),
            ('10', 4, 4, {1: [1], 2: [2], 3: [3], 4: [4]}, {1: '0', 2: '0', 3: '0', 4: '0'}),
            ('12', 1, 1, {1: [1]}, {1: '0'}),
        ]
        for hw, mode, readers, doors, types in cases:
            self.assertEqual(codecs.reader_door_map(hw, mode, readers), doors, (hw, mode, readers))
            self.assertEqual(codecs.reader_types(hw, mode, readers), types, (hw, mode, readers))
        self.assertEqual(codecs.reader_door_map('16', 2, 2), {}, "a vending machine has no doors here")

    def test_zone_layout_matches_the_core_alarm_lines(self):
        self.assertEqual(codecs.zone_door_map(1, 1), {1: [1]})
        self.assertEqual(codecs.zone_door_map(4, 2), {1: [1, 2], 2: [3, 4]})
        self.assertEqual(codecs.zone_door_map(4, 3), {1: [1, 2], 2: [3], 3: [4]})
        self.assertEqual(codecs.zone_door_map(4, 4), {1: [1], 2: [2], 3: [3], 4: [4]})
        self.assertEqual(codecs.zone_door_map(0, 2), {})

    def test_card_record_layout(self):
        """Number, PIN, schedule per reader, reader bits and the alarm byte come
        out of a record exactly where the module writes them."""
        rec = codecs.decode_card_record(card_record('0012345678', '4321', [1, 1, 0, 2], 0b0100_1011, 0x05), 20)
        self.assertEqual(rec['number'], '0012345678')
        self.assertEqual(rec['pin'], '4321')
        self.assertEqual(rec['ts'], [1, 1, 0, 2])
        self.assertEqual(rec['reader_bits'], [1, 1, 0, 1])
        self.assertTrue(rec['apb1'])
        self.assertFalse(rec['apb2'])
        self.assertEqual(rec['alarm_bits'], 5)
        self.assertEqual(rec['anomaly'], '')
        no_pin = codecs.decode_card_record(card_record('0000000009', '0000', [0, 0, 0, 0], 1), 19)
        self.assertEqual(no_pin['pin'], '')
        self.assertIsNone(codecs.decode_card_record('00' * 19, 19), "an all-zero record is a terminator")
        self.assertIsNone(codecs.decode_card_record('FF' * 19, 19), "an erased record is a terminator")

    def test_card_page_must_be_whole_records(self):
        page = card_record('0000000001', '', [0] * 4, 1) + card_record('0000000002', '', [0] * 4, 3)
        self.assertEqual([r['number'] for r in codecs.decode_cards_page(page, 19)],
                         ['0000000001', '0000000002'])
        with self.assertRaises(codecs.PageShapeError):
            codecs.decode_cards_page(page + '00', 19)
        self.assertEqual(codecs.decode_cards_page('', 19), [])

    def test_record_size_follows_the_hardware_not_the_reply(self):
        self.assertEqual(codecs.record_size_of('6', 0), 19)
        self.assertEqual(codecs.record_size_of('10', 4), 20)
        self.assertEqual(codecs.record_size_of('11', 1), 20)
        self.assertEqual(codecs.record_size_of('31', 0), 34)
        self.assertEqual(codecs.record_size_of('22', 0), 36)
        self.assertIsNone(codecs.record_size_of('18', 0), "a fire panel holds no cards")
        self.assertTrue(codecs.reads_cards('10'))
        self.assertFalse(codecs.reads_cards('16'), "vending machines are never read for cards")
        self.assertFalse(codecs.reads_cards('31'))

    def test_page_request_encoding_matches_the_core(self):
        self.assertEqual(codecs.encode_f2_count(), '0000000000')
        self.assertEqual(codecs.encode_f2_page(1, 5), '000000000105')
        self.assertEqual(codecs.encode_f2_page(123, 2), '000001020302')
        self.assertEqual(codecs.decode_f2_count('0000000004'), 4)
        self.assertEqual(codecs.decode_f2_count('0009070002'), 9702)

    def test_schedule_reply_becomes_the_core_schedule_format(self):
        """The slot reply, normalised, is a valid ts_data the core wizard can open:
        the same length, the slot in the first byte, and every interval parsable
        as decimal digits."""
        body = ''
        for day in range(8):
            for n in range(4):
                body += '08001800' if (day < 5 and n == 0) else '00000000'
        reply = '03' + body + '00'
        dec = codecs.decode_ts(reply)
        self.assertEqual(len(dec['ts_data']), 260)
        self.assertEqual(dec['ts_data'][:2], '03')
        self.assertFalse(dec['is_empty'])
        self.assertEqual(dec['summary'], 'Mon-Fri 08:00-18:00')
        ts = self.env['hr.rfid.time.schedule'].search([('number', '=', 3)], limit=1)
        ts = ts.with_context(active_test=False)
        ts.sudo().write({'ts_data': dec['ts_data']})
        self.assertEqual(ts._get_interval_from_day_tuple(0, 0), (8.0, 18.0))
        self.assertEqual(ts._get_interval_from_day_tuple(5, 0), (0.0, 0.0))
        self.assertFalse(ts.is_empty)

    def test_erased_schedule_intervals_read_as_empty(self):
        reply = '01' + 'FF' * 128 + '00'
        dec = codecs.decode_ts(reply)
        self.assertTrue(dec['is_empty'])
        self.assertEqual(dec['ts_data'], '01' + '00' * 128 + '00')

    def test_status_decodes_like_the_core(self):
        data = '5a0000000719000000000000020202020000000000000000'
        status = codecs.decode_status(data)
        self.assertEqual(status['input_states'], 0x5a & 0x7f)
        self.assertEqual(status['zones'], [2, 2, 2, 2])
        self.assertAlmostEqual(status['system_voltage'], (719 * 8) / 500)

    def test_card_numbers_are_normalised_and_converted(self):
        self.assertEqual(codecs.normalise_card_number(' 12345 '), '0000012345')
        self.assertEqual(codecs.normalise_card_number('0000012345678'), '0000012345678'[3:].zfill(10))
        self.assertIsNone(codecs.normalise_card_number('abc'))
        self.assertIsNone(codecs.normalise_card_number('12345678901'))
        card = self.env['hr.rfid.card'].new({'number': '0012345678', 'card_input_type': 'w34s'})
        card._compute_internal_number()
        self.assertEqual(codecs.w34s_to_internal('0012345678'), card.internal_number)
        self.assertEqual(codecs.internal_to_w34s(card.internal_number), '0012345678')
        self.assertEqual(codecs.display_number('0018834062', 'w34'), '0018834062')

    def test_alarm_setup_polarity_matches_the_core(self):
        setup = codecs.decode_alarm_setup('01010203')
        self.assertEqual(setup['alarm_lines_setup'], '010203')
        self.assertEqual(setup['disable_readers'], 1)
        self.assertEqual(setup['disable_door_contacts'], 2)
        self.assertEqual(setup['zones_enabled'], 3)
        self.assertFalse(setup['sensor_events'])
        self.assertTrue(codecs.decode_alarm_setup('01000013')['sensor_events'])
        self.assertTrue(codecs.decode_alarm_setup('00')['short_form'])

    def test_f0_acceptance_mirrors_the_core_checks(self):
        ok = codecs.decode_f0(make_f0(10, 1, 748, 10, 8, 4, 15, 28, 4, 2, 7679, 4094))
        self.assertTrue(codecs.f0_would_pass(ok))
        wrong_readers = codecs.decode_f0(make_f0(18, 1, 720, 8, 4, 0, 0, 24, 0, 1, 0, 1000))
        self.assertFalse(codecs.f0_would_pass(wrong_readers), "a fire panel with no readers is not a door controller")
        relay_mode4 = codecs.decode_f0(make_f0(31, 1, 751, 5, 8, 2, 8, 28, 0, 4, 9727, 3056))
        self.assertFalse(codecs.f0_would_pass(relay_mode4))
        temp = codecs.decode_f0(make_f0(22, 1, 745, 4, 4, 0, 0, 24, 0, 1, 0, 4064))
        self.assertTrue(codecs.f0_would_pass(temp), "the core exempts temperature controllers from the reader check")


@tagged('post_install', '-at_install', 'rfid_hw_import', 'rfid_hw_import_codecs')
class TestFamiliesAgainstTheCore(TransactionCase):
    """The survey and the access control module must agree on what a hardware
    code is; one truth, held by the module that owns the hardware."""

    def test_the_families_agree_with_the_core_classifiers_for_every_code(self):
        Ctrl = self.env['hr.rfid.ctrl']
        for code, _label in HW_TYPES:
            family = codecs.family_of(code)
            self.assertEqual(family == 'relay', Ctrl.is_relay_ctrl(hw_version=code), code)
            self.assertEqual(family == 'vending', Ctrl.is_vending_ctrl(hw_version=code), code)
            if Ctrl.is_temperature_ctrl(hw_version=code):
                self.assertEqual(family, 'temperature', code)
            if Ctrl.is_turnstile_ctrl(hw_version=code):
                self.assertEqual(family, 'access', code)

    def test_a_clock_that_is_not_a_date_is_refused_not_zeroed(self):
        for reply in ('00' * 7, 'FF' * 7, '00000099000000'):
            with self.assertRaises(codecs.DecodeError, msg=reply):
                codecs.decode_clock(reply)
