"""Decoders for the replies a survey reads and the few encoders it needs.

Everything here is a pure function of a hex string. The layouts mirror what
``hr_rfid`` already reads and writes (its F0 parser, its D1 card builder, its
time-schedule ``ts_data`` format, its B3 status decoder); the tests compare
these functions with the core where the core has a counterpart.
"""
import hashlib
from datetime import datetime

from odoo.addons.hr_rfid.controllers.polimex import HW_TYPES, READ_CARDS_BLOCK_SIZE, bytes_to_num

HW_LABELS = dict(HW_TYPES)

#: Hardware families. The codes are the two BCD digits the controller reports
#: in its system information; where hr_rfid has a classifier of its own
#: (is_vending_ctrl = '16', is_relay_ctrl = 30-32, is_temperature_ctrl = 22-24)
#: the family follows it exactly - tests/test_codecs.py holds the parity test.
#: Codes hr_rfid lists but no firmware reports (33, 36-39) stay unknown.
FAMILY_BY_HW = {}
for _code in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '17'):
    FAMILY_BY_HW[_code] = 'access'
for _code in ('13', '14'):
    FAMILY_BY_HW[_code] = 'hotel'
FAMILY_BY_HW['16'] = 'vending'
for _code in ('30', '31', '32'):
    FAMILY_BY_HW[_code] = 'relay'
for _code in ('34', '35'):
    FAMILY_BY_HW[_code] = 'io'
for _code in ('15', '22', '23', '24'):
    FAMILY_BY_HW[_code] = 'temperature'
for _code in ('18', '19'):
    FAMILY_BY_HW[_code] = 'fire'
FAMILY_BY_HW['25'] = 'gas'
FAMILY_BY_HW['26'] = 'power'
for _code in ('20', '21', '27', '28', '29'):
    FAMILY_BY_HW[_code] = 'alarm'
for _code in (str(c) for c in range(40, 50)):
    FAMILY_BY_HW[_code] = 'reader'
FAMILY_BY_HW['50'] = 'motor'

#: Families whose card table holds access cards in the standard record layout.
CARD_FAMILIES = ('access', 'hotel')

CARD_RECORD_BASE_SIZE = 19
CARD_RECORD_ALARM_SIZE = 20
CARD_RECORD_RELAY_SIZE = 34
CARD_RECORD_TEMPERATURE_SIZE = 36

TS_REPLY_BYTES = 130
TS_DAYS = 8          # Monday .. Sunday + holiday row
TS_INTERVALS = 4
DAY_LABELS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Hol')

HOLIDAY_REPLY_BYTES = 65


class DecodeError(ValueError):
    """A reply that does not have the shape the controller documents."""


class PageShapeError(DecodeError):
    """A card page whose length is not a whole number of records."""


# ---------------------------------------------------------------- helpers

def hex_bytes(data):
    """bytes from a hex string, tolerant of case and surrounding spaces."""
    data = (data or '').strip()
    if len(data) % 2:
        raise DecodeError("odd-length hex reply")
    try:
        return bytes.fromhex(data)
    except ValueError as exc:
        raise DecodeError("reply is not hexadecimal: %s" % exc) from exc


def family_of(hw_code):
    return FAMILY_BY_HW.get(str(hw_code or ''), 'unknown')


def hw_label(hw_code):
    return HW_LABELS.get(str(hw_code or ''), 'Unknown')


def record_size_of(hw_code, alarm_lines):
    """Bytes per card record for this controller, None when it holds no cards."""
    family = family_of(hw_code)
    if family in CARD_FAMILIES:
        return CARD_RECORD_ALARM_SIZE if (alarm_lines or 0) > 0 else CARD_RECORD_BASE_SIZE
    if family == 'relay':
        return CARD_RECORD_RELAY_SIZE
    if family == 'temperature':
        return CARD_RECORD_TEMPERATURE_SIZE
    return None


def reads_cards(hw_code):
    """Only the access families are read for cards (owner decision 6)."""
    return family_of(hw_code) in CARD_FAMILIES


# ---------------------------------------------------------------- F0

def decode_mode_byte(value):
    """The mode byte as hr_rfid reads it (parse_f0_response / F5)."""
    return {
        'mode': value & 0x07,
        'dual_person': bool(value & 0x08),
        'interlocking': bool(value & 0x10),
        'external_db': bool(value & 0x20),
        'relay_time_factor': bool(value & 0x40),
    }


def decode_f0(data):
    """System information; same offsets as hr_rfid's F0 parser."""
    data = (data or '').strip()
    if len(data) < 64:
        raise DecodeError("system information reply is too short (%d chars)" % len(data))
    mode_byte = int(data[42:44], 16)
    result = {
        'hw_code': str(bytes_to_num(data, 0, 2)),
        'serial': str(bytes_to_num(data, 4, 4)),
        'sw_version': str(bytes_to_num(data, 12, 3)),
        'inputs': bytes_to_num(data, 18, 3),
        'outputs': bytes_to_num(data, 24, 3),
        'readers': int(data[30:32], 16),
        'time_schedules': bytes_to_num(data, 32, 2),
        'io_table_lines': bytes_to_num(data, 36, 2),
        'alarm_lines': bytes_to_num(data, 40, 1),
        'mode_byte': mode_byte,
        'max_cards': bytes_to_num(data, 44, 5),
        'max_events': bytes_to_num(data, 54, 5),
    }
    result.update(decode_mode_byte(mode_byte))
    return result


MODE_READER_RELATION = {1: (1, 2), 2: (2, 4), 3: (4,), 4: (4,)}


def f0_would_pass(dec):
    """Would hr_rfid accept this system information for an existing controller?

    Mirrors the checks in parse_f0_response: the mode must be 1..4, the reader
    count must fit the mode (except for the families the core exempts), a relay
    controller in mode 2 with more than 16 outputs needs two readers, and a
    relay controller only knows modes 1, 2 and 3.
    """
    hw = str(dec['hw_code'])
    mode = dec['mode']
    if mode < 1 or mode > 4:
        return False
    if hw not in ('22', '30', '31', '32') and dec['readers'] not in MODE_READER_RELATION[mode]:
        return False
    if family_of(hw) == 'relay' and hw in ('30', '31', '32'):
        if mode == 2 and dec['outputs'] > 16 and dec['readers'] < 2:
            return False
        if mode == 4:
            return False
    return True


# ---------------------------------------------------------------- reader / door / zone maps

def reader_door_map(hw_code, mode, readers):
    """{door_number: [reader numbers]} exactly as parse_f0_response builds them."""
    family = family_of(hw_code)
    if family not in CARD_FAMILIES:
        return {}
    doors = {}
    if mode in (1, 3):
        doors[1] = [1] + ([2] if readers > 1 else [])
        if mode == 3:
            doors[2] = [3]
            doors[3] = [4]
    elif mode == 2 and readers == 4:
        doors[1] = [1, 2]
        doors[2] = [3, 4]
    else:
        doors[1] = [1]
        doors[2] = [2]
        if mode == 4:
            doors[3] = [3]
            doors[4] = [4]
    return doors


def reader_types(hw_code, mode, readers):
    """{reader_number: '0' (in) | '1' (out)} as parse_f0_response assigns them."""
    types = {}
    if mode in (1, 3):
        types[1] = '0'
        if readers > 1:
            types[2] = '1'
        if mode == 3:
            types[3] = '0'
            types[4] = '0'
    elif mode == 2 and readers == 4:
        types.update({1: '0', 2: '1', 3: '0', 4: '1'})
    else:
        types[1] = '0'
        types[2] = '0'
        if mode == 4:
            types[3] = '0'
            types[4] = '0'
    return types


def zone_door_map(alarm_lines, mode):
    """{door_number: [alarm zone numbers]} as hr_rfid's _setup_alarm_lines binds them."""
    if not alarm_lines:
        return {}
    if alarm_lines == 1:
        return {1: [1]}
    if mode == 2:
        return {1: [1, 2], 2: [3, 4]}
    if mode == 3:
        return {1: [1, 2], 2: [3], 3: [4]}
    if mode == 4:
        return {1: [1], 2: [2], 3: [3], 4: [4]}
    return {1: list(range(1, alarm_lines + 1))}


# ---------------------------------------------------------------- cards

def encode_f2_count():
    """Request form 1: how many cards the controller holds."""
    return '0000000000'


def encode_f2_page(position, count):
    """Request form 2: ``count`` records from 1-based ``position``.

    Same encoding as hr_rfid's read_cards_cmd: five per-digit BCD bytes for the
    position, one packed BCD byte for the count.
    """
    if position < 1 or position > 99999:
        raise ValueError("card position out of range: %s" % position)
    if count < 1 or count > READ_CARDS_BLOCK_SIZE:
        raise ValueError("card page size out of range: %s" % count)
    return ''.join('0%s' % d for d in '%.5d' % position) + '%.2d' % count


def decode_f2_count(data):
    """The card count reply: five per-digit BCD bytes."""
    data = (data or '').strip()
    if len(data) != 10:
        raise DecodeError("card count reply has %d chars, expected 10" % len(data))
    return bytes_to_num(data, 0, 5)


def _digits(bs):
    """Per-digit BCD bytes to a decimal string; None when a byte is not a digit."""
    if any(b > 9 for b in bs):
        return None
    return ''.join(str(b) for b in bs)


def decode_card_record(data, record_size):
    """One card record. Returns None for a terminator (all 00 / all FF)."""
    bs = hex_bytes(data)
    if len(bs) != record_size:
        raise DecodeError("card record has %d bytes, expected %d" % (len(bs), record_size))
    if all(b == 0 for b in bs) or all(b == 0xFF for b in bs):
        return None
    number = _digits(bs[0:10])
    pin = _digits(bs[10:14])
    rights = bs[18]
    record = {
        'raw_hex': data.upper(),
        'number': number or '',
        'pin': '' if pin in (None, '0000') else pin,
        'ts': [bs[14], bs[15], bs[16], bs[17]],
        'rights': rights,
        'reader_bits': [(rights >> i) & 1 for i in range(4)],
        'apb2': bool(rights & 0x20),
        'apb1': bool(rights & 0x40),
        'alarm_bits': bs[19] if record_size >= CARD_RECORD_ALARM_SIZE else 0,
        'anomaly': '' if number is not None else 'bad_bcd',
    }
    return record


def decode_cards_page(data, record_size):
    """All records of one page; terminators are dropped."""
    bs = hex_bytes(data)
    if not bs:
        return []
    if len(bs) % record_size:
        raise PageShapeError(
            "card page has %d bytes, not a multiple of the %d-byte record"
            % (len(bs), record_size))
    records = []
    for i in range(0, len(bs), record_size):
        rec = decode_card_record(bs[i:i + record_size].hex(), record_size)
        if rec is not None:
            # The offset within the page, terminators counted, so the caller
            # can name the record's true position in the controller's table.
            rec['index'] = i // record_size
            records.append(rec)
    return records


# ---------------------------------------------------------------- time schedules

def _interval_is_valid(chunk):
    """Four packed-BCD bytes hh mm hh mm; erased flash (FF) is not a time."""
    for b in chunk:
        if (b >> 4) > 9 or (b & 0x0F) > 9:
            return False
    return True


def week_fingerprint(ts_data):
    """Fingerprint of the weekly grid of a schedule in hr_rfid's ``ts_data``
    form: the 128 interval bytes, without the slot echo in front and the
    holiday reference at the end. Two schedules with the same fingerprint let
    people through at the same times."""
    return hashlib.sha1((ts_data or '')[2:258].upper().encode()).hexdigest()


def ts_is_empty(ts_data):
    """Empty exactly as hr_rfid's own schedule sees it: nothing set after the
    slot echo, the holiday reference included."""
    return (ts_data or '')[2:].replace('0', '') == ''


def decode_ts(data):
    """A time schedule slot reply, in the ``ts_data`` form hr_rfid stores.

    The reply has the same layout as hr_rfid's DEFAULT_TS_LINE: one echo byte
    (the slot), 8 rows x 4 intervals x 4 packed-BCD bytes, one holiday
    reference. Erased or non-BCD intervals are normalised to 00000000 so the
    core's schedule wizard, which parses the digits as decimal text, can open
    the imported schedule.
    """
    bs = hex_bytes(data)
    if len(bs) != TS_REPLY_BYTES:
        raise DecodeError("time schedule reply has %d bytes, expected %d" % (len(bs), TS_REPLY_BYTES))
    grid = []
    body = bytearray()
    for day in range(TS_DAYS):
        intervals = []
        for n in range(TS_INTERVALS):
            start = 1 + day * 16 + n * 4
            chunk = bs[start:start + 4]
            if not _interval_is_valid(chunk):
                chunk = b'\x00\x00\x00\x00'
            body += chunk
            begin = '%02x:%02x' % (chunk[0], chunk[1])
            end = '%02x:%02x' % (chunk[2], chunk[3])
            intervals.append((begin, end) if chunk != b'\x00\x00\x00\x00' else None)
        grid.append(intervals)
    holiday_ref = bs[129]
    body_hex = body.hex().upper()
    ts_data = '%02X%s%02X' % (bs[0], body_hex, holiday_ref)
    return {
        'slot': bs[0],
        'ts_data': ts_data,
        'week_fingerprint': week_fingerprint(ts_data),
        'is_empty': ts_is_empty(ts_data),
        'holiday_ref': holiday_ref,
        'grid': grid,
        'summary': ts_summary(grid),
    }


def ts_summary(grid):
    """"Mon-Fri 08:00-18:00; Sat 08:00-12:00" from the decoded grid."""
    runs = []
    for idx, intervals in enumerate(grid):
        key = tuple(i for i in intervals if i)
        if not key:
            continue
        if runs and runs[-1][2] == key and runs[-1][1] == idx - 1 and idx < 7:
            runs[-1][1] = idx
        else:
            runs.append([idx, idx, key])
    parts = []
    for first, last, key in runs:
        days = DAY_LABELS[first] if first == last else '%s-%s' % (DAY_LABELS[first], DAY_LABELS[last])
        parts.append('%s %s' % (days, ', '.join('%s-%s' % iv for iv in key)))
    return '; '.join(parts)


def decode_holidays(data):
    """One holiday slot: echo + 32 x (day, month); empty pairs are dropped."""
    bs = hex_bytes(data)
    if len(bs) != HOLIDAY_REPLY_BYTES:
        raise DecodeError("holiday reply has %d bytes, expected %d" % (len(bs), HOLIDAY_REPLY_BYTES))
    dates = []
    for i in range(32):
        day, month = bs[1 + i * 2], bs[2 + i * 2]
        if 1 <= day <= 31 and 1 <= month <= 12:
            dates.append((day, month))
    return {'slot': bs[0], 'dates': dates}


# ---------------------------------------------------------------- other configuration

def decode_f5(data):
    bs = hex_bytes(data)
    if len(bs) < 1:
        raise DecodeError("controller mode reply is empty")
    return decode_mode_byte(bs[0])


def decode_reader_modes(data):
    """Four readers x (mode, mode_ts, ts); hr_rfid keeps the mode as a 2-char code."""
    bs = hex_bytes(data)
    if len(bs) < 12:
        raise DecodeError("reader modes reply has %d bytes, expected 12" % len(bs))
    return [{
        'reader': i + 1,
        'mode': '%02d' % bs[i * 3],
        'mode_ts': bs[i * 3 + 1],
        'ts': bs[i * 3 + 2],
    } for i in range(4)]


def decode_input_masks(data):
    """(input mask as hr_rfid stores it, the two trailing bytes for the relay flag)."""
    bs = hex_bytes(data)
    if len(bs) < 4:
        raise DecodeError("input masks reply has %d bytes, expected 4" % len(bs))
    mask = (bs[0] & 0x7F) | ((bs[1] & 0x7F) << 7)
    return mask, bytes(bs[2:4])


def decode_apb(data):
    bs = hex_bytes(data)
    if len(bs) < 1:
        raise DecodeError("anti-passback reply is empty")
    return bs[0]


def door_apb(bitmap, door_number):
    return bool(bitmap & (1 << (door_number - 1)))


def decode_output_ts(data, outputs=8):
    """Time schedule slot per output (low nibble), outputs 1..min(outputs, 8)."""
    bs = hex_bytes(data)
    count = min(outputs or 8, 8, len(bs))
    return [bs[i] & 0x0F for i in range(count)]


def decode_alarm_setup(data):
    """The alarm-zone setup read reply, in the form hr_rfid stores it.

    ``alarm_lines_setup`` is the three bytes after the echo as six hex chars
    (hr_rfid's own B0 parser writes them that way); the flag bytes are DISABLE
    masks and the third byte enables zones, bit 4 of it saves the sensor
    events. A one-byte reply (some builds) means "everything at defaults".
    """
    bs = hex_bytes(data)
    if len(bs) < 4:
        return {'alarm_lines_setup': '000000', 'sensor_events': False,
                'disable_readers': 0, 'disable_door_contacts': 0, 'zones_enabled': 0,
                'short_form': True}
    return {
        'alarm_lines_setup': '%02x%02x%02x' % (bs[1], bs[2], bs[3]),
        'sensor_events': bool(bs[3] & 0x10),
        'disable_readers': bs[1] & 0x0F,
        'disable_door_contacts': bs[2] & 0x0F,
        'zones_enabled': bs[3] & 0x0F,
        'short_form': False,
    }


def decode_status(data):
    """Live status, decoded the way hr_rfid decodes its own B3 replies."""
    data = (data or '').strip()
    if len(data) < 42:
        raise DecodeError("status reply has %d chars, expected at least 42" % len(data))
    input_states = (int(data[0:2], 16) & 0x7F) + ((int(data[2:4], 16) & 0x7F) << 7)
    output_states = (int(data[4:6], 16) & 0x7F) + ((int(data[6:8], 16) & 0x7F) << 7)
    usys = [int(data[8:10], 16), int(data[10:12], 16)]
    uin = [int(data[12:14], 16), int(data[14:16], 16)]
    temperature = int(data[16:20], 10) if data[16:20].isdigit() else 0
    humidity = int(data[20:24], 10) if data[20:24].isdigit() else 0
    zones = [int(data[24 + i * 2:26 + i * 2], 16) for i in range(4)]
    tos = sum(int(data[32 + i * 2:34 + i * 2], 16) * 10 ** (4 - i) for i in range(5))
    if temperature >= 1000:
        temperature = -(temperature - 1000)
    temperature /= 10
    humidity /= 10

    def _voltage(pair):
        value = ((pair[0] & 0xF0) >> 4) * 1000 + (pair[0] & 0x0F) * 100
        value += ((pair[1] & 0xF0) >> 4) * 10 + (pair[1] & 0x0F)
        return (value * 8) / 500

    return {
        'input_states': input_states,
        'output_states': output_states,
        'system_voltage': _voltage(usys),
        'input_voltage': _voltage(uin),
        'temperature': temperature,
        'humidity': humidity,
        'zones': zones,
        'time_of_service': tos,
    }


def decode_clock(data):
    """ss mm hh dow dd mm yy, packed BCD; None when the value is not a date."""
    bs = hex_bytes(data)
    if len(bs) < 7:
        raise DecodeError("clock reply has %d bytes, expected 7" % len(bs))
    try:
        parts = [int('%02x' % b) for b in bs[:7]]
        return datetime(2000 + parts[6], parts[5], parts[4], parts[2], parts[1], parts[0])
    except ValueError as exc:
        # A flat clock battery gives all-zero or all-FF digits: not a date,
        # and exactly the controller whose schedules are not working.
        raise DecodeError("clock reply is not a date: %s" % data) from exc


def io_table_is_complete(data, io_table_lines):
    return len((data or '').strip()) == (io_table_lines or 0) * 16


# ---------------------------------------------------------------- card numbers

def normalise_card_number(raw):
    """Digits only, left-padded to ten; None when it cannot be a card number."""
    digits = ''.join(ch for ch in str(raw or '') if ch.isdigit())
    if not digits:
        return None
    if len(digits) > 10:
        digits = digits.lstrip('0')
        if len(digits) > 10:
            return None
    return digits.zfill(10)


def w34s_to_internal(number):
    """A 10-digit decimal number in the 5d+5d form the readers report.

    Same arithmetic as hr_rfid's internal-number compute for the 'w34s' input
    type: the value as eight hex digits, split in two, each half as five
    decimal digits.
    """
    value = int(number)
    if value > 0xFFFFFFFF:
        return None
    h4 = '{:08X}'.format(value)
    return '{:05}'.format(int(h4[:4], 16)) + '{:05}'.format(int(h4[4:], 16))


def internal_to_w34s(internal):
    """The reverse of w34s_to_internal: 5d+5d back to one decimal number."""
    p1, p2 = int(internal[:5]), int(internal[5:])
    if p1 > 0xFFFF or p2 > 0xFFFF:
        return None
    return '{:010d}'.format((p1 << 16) | p2)


def display_number(internal, card_input_type):
    """How the company writes this card: 'w34' keeps 5d+5d, 'w34s' one number."""
    if card_input_type == 'w34s':
        return internal_to_w34s(internal) or internal
    return internal


def normalise_name(name):
    return ' '.join(str(name or '').split()).casefold()
