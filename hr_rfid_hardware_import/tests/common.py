"""One invented site, scripted for the fake module, shared by every test.

Module A (100.1) on the LAN: an iCON180 (4 readers, alarm zones, 6 cards), an
iCON110 (2 readers, 4 cards), a vending machine, a relay controller and a
temperature controller. Module B (10.3) behind a router: a fire panel and an
iCON115 (2 cards, one shared with module A). Every number is fabricated.
"""
import base64
from datetime import datetime

from odoo.tests import TransactionCase

from odoo.addons.hr_rfid_hardware_import.helpers import allowlist
from odoo.addons.hr_rfid_hardware_import.helpers.fake_transport import FakeBackend
from odoo.addons.hr_rfid_hardware_import.models import hw_import_run

MODULE_A_IP = '192.0.2.10'
MODULE_B_IP = '192.0.2.20'
MODULE_A_SERIAL = '4TEST1'
MODULE_B_SERIAL = 'TEST02'

ADDR_180, ADDR_110, ADDR_VEND, ADDR_RELAY, ADDR_TEMP = 15, 5, 1, 34, 41
ADDR_FIRE, ADDR_115 = 40, 2


def _digits(value, width):
    return ''.join('%02d' % int(d) for d in ('%0*d' % (width, value)))


def make_f0(hw, serial, sw, inputs, outputs, readers, ts, io, alarm, mode, max_cards, max_events):
    return (_digits(hw, 2) + _digits(serial, 4) + _digits(sw, 3) + _digits(inputs, 3) + _digits(outputs, 3)
            + '%02d' % readers + _digits(ts, 2) + _digits(io, 2) + '%02d' % alarm + '%02X' % mode
            + _digits(max_cards, 5) + _digits(max_events, 5))


def card_record(number, pin, ts, rights, alarm=None):
    hexs = _digits(int(number), 10) + _digits(int(pin or 0), 4) + ''.join('%02X' % t for t in ts) + '%02X' % rights
    if alarm is not None:
        hexs += '%02X' % alarm
    return hexs


def ts_reply(slot, intervals_by_day):
    body = ''
    for day in range(8):
        for n in range(4):
            iv = intervals_by_day.get(day, [])
            if n < len(iv):
                b, e = iv[n]
                body += '%02d%02d%02d%02d' % (int(b[:2]), int(b[3:]), int(e[:2]), int(e[3:]))
            else:
                body += '00000000'
    return ('%02X' % slot) + body + '00'


def clock_reply(now=None):
    now = now or datetime.now()
    return ''.join('%02d' % v for v in (now.second, now.minute, now.hour, now.isoweekday(),
                                         now.day, now.month, now.year % 100))


TS_WORK = {d: [('08:00', '18:00')] for d in range(5)}
TS_WIDE_A = {d: [('07:00', '20:00')] for d in range(6)}
TS_WIDE_B = {d: [('06:00', '22:00')] for d in range(7)}
TS_SAT = {5: [('08:00', '12:00')]}

CARDS_180 = [
    ('0000100001', '', [1, 1, 0, 0], 0b0011, 0x03),
    ('0000100002', '1234', [0, 0, 0, 0], 0b1111, 0x0F),
    ('0000100003', '', [1, 1, 2, 2], 0b1111, 0x00),
    ('0000100004', '', [2, 2, 0, 0], 0b0011, 0x00),
    ('0000100005', '', [1, 1, 0, 0], 0b0011, 0x03),
    ('0000100006', '', [1, 2, 0, 0], 0b0011, 0x00),
]
CARDS_110 = [
    ('0000100001', '', [1, 1, 0, 0], 0b0011),
    ('0000100002', '5678', [0, 0, 0, 0], 0b0011),
    ('0000100005', '', [0, 0, 0, 0], 0b0011),
    ('0000100007', '', [0, 0, 0, 0], 0b0001),
    ('0000100008', '9999', [0, 0, 0, 0], 0b0011),
]
CARDS_115 = [
    ('0000100001', '', [3, 3, 0, 0], 0b0011, 0x01),
    ('0000100009', '', [0, 0, 0, 0], 0b0011, 0x00),
]

COMMON = {
    'F6': '010100' * 4, 'F8': '0000000000', 'FB': '00000000', 'FF': '00' * 8,
    'F9': '00' * 224, 'B3': '5a0000000719000000000000020202020000000000000000',
}


def site_script():
    f7 = clock_reply()
    return {
        'discovery': [{
            'ip': MODULE_A_IP, 'hostname': 'polimex-test-a', 'mac': '02-00-00-00-00-0A', 'hw_version': '100.1',
            'fw_version': '1.69', 'serial': MODULE_A_SERIAL, 'bridge_port': 5000,
        }],
        'modules': {
            MODULE_A_IP: {
                'config': {'convertor': MODULE_A_SERIAL,
                           'sdk': {'sdkVersion': '1.69', 'sdkHardware': '100.1', 'devFound': 5},
                           'sdkSettings': {'Server_URL': 'http://old-server.example/hr/rfid/event',
                                           'server_push_key': 'secret'},
                           'flashConfig': {'user_1_pass': 'secret'}},
                'details': {'devFound': 5, 'maxDevInList': 64},
                'status': {
                    0: {'dev': {'devID': ADDR_180, 'devHardware': 10, 'devSoftware': 748, 'devSerial': 1801}},
                    1: {'dev': {'devID': ADDR_110, 'devHardware': 6, 'devSoftware': 741, 'devSerial': 1101}},
                    2: {'dev': {'devID': ADDR_VEND, 'devHardware': 16, 'devSoftware': 742, 'devSerial': 1601}},
                    3: {'dev': {'devID': ADDR_RELAY, 'devHardware': 31, 'devSoftware': 751, 'devSerial': 3101}},
                    4: {'dev': {'devID': ADDR_TEMP, 'devHardware': 22, 'devSoftware': 745, 'devSerial': 2201}},
                },
                'devices': {
                    ADDR_180: dict(COMMON, F0=make_f0(10, 1801, 748, 10, 8, 4, 15, 28, 4, 0x02, 7679, 4094),
                                   F5='02', FC='01', B0='01000003', F7=f7,
                                   F3={1: ts_reply(1, TS_WORK), 2: ts_reply(2, TS_WIDE_A)},
                                   cards=[card_record(*c) for c in CARDS_180]),
                    ADDR_110: dict(COMMON, F0=make_f0(6, 1101, 741, 3, 3, 2, 15, 28, 0, 0x01, 1526, 3056),
                                   F5='01', FC='00', F7=f7,
                                   F3={1: ts_reply(1, TS_WORK), 2: ts_reply(2, TS_WIDE_B)},
                                   cards=[card_record(*c) for c in CARDS_110]),
                    ADDR_VEND: dict(COMMON, F0=make_f0(16, 1601, 742, 8, 8, 2, 15, 28, 0, 0x02, 9727, 3056),
                                    cards=[card_record('0000100099', '', [0] * 4, 3)]),
                    ADDR_RELAY: dict(COMMON, F0=make_f0(31, 3101, 751, 5, 8, 2, 8, 28, 0, 0x01, 9727, 3056),
                                     F5='01', F7=f7, gaps=['F3', 'F8', 'FC']),
                    ADDR_TEMP: dict(COMMON, F0=make_f0(22, 2201, 745, 4, 4, 0, 0, 24, 0, 0x01, 0, 4064),
                                    F5='01', F7=f7, gaps=['F6', 'FF']),
                },
            },
            MODULE_B_IP: {
                'discovery': {'hostname': 'polimex-test-b', 'mac': '02-00-00-00-00-0B', 'hw_version': '10.3',
                              'fw_version': '1.30', 'serial': MODULE_B_SERIAL, 'bridge_port': 5000},
                'config': {'convertor': MODULE_B_SERIAL,
                           'sdk': {'sdkVersion': '1.30', 'sdkHardware': '10.3', 'devFound': 2},
                           'sdkSettings': {'Server_URL': ''}},
                'status': {
                    0: {'dev': {'devID': ADDR_FIRE, 'devHardware': 18, 'devSoftware': 720, 'devSerial': 1802}},
                    1: {'dev': {'devID': ADDR_115, 'devHardware': 11, 'devSoftware': 744, 'devSerial': 1151}},
                },
                'devices': {
                    ADDR_FIRE: dict(COMMON, F0=make_f0(18, 1802, 720, 8, 4, 0, 0, 24, 0, 0x01, 0, 1000),
                                    F5='01', F7=f7, gaps=['F6', 'FC', 'FF', 'F3', 'F4']),
                    ADDR_115: dict(COMMON, F0=make_f0(11, 1151, 744, 5, 4, 2, 15, 28, 1, 0x01, 9727, 3056),
                                   F5='01', FC='00', B0='01000001', F7=f7,
                                   F3={1: ts_reply(1, TS_WORK), 3: ts_reply(3, TS_SAT)},
                                   cards=[card_record(*c) for c in CARDS_115]),
                },
            },
        },
    }


NAMES_CSV = (
    "Name,Card\n"
    "Demo Holder One,0000100001\n"
    "Demo Holder One,0000100005\n"
    "Demo Holder Two,100002\n"
    "Ghost Holder,0000999999\n"
    "Demo Holder Three,0000100003\n"
    "Demo Holder Three Again,0000100003\n"
    ",0000100004\n"
)


class HwImportCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend = FakeBackend(site_script())
        hw_import_run.override_backend(cls.backend)
        cls.addClassCleanup(hw_import_run.override_backend, None)
        cls.env['hr.rfid.time.schedule'].sudo().set_company_ts()
        cls.company = cls.env.company
        cls.department = cls.env['hr.department'].create({'name': 'Survey test department'})

    def setUp(self):
        super().setUp()
        self.backend.calls.clear()
        self.backend.faults.clear()
        # The worker keeps each finished piece of work with a commit, and
        # undoes a failed pass with a rollback; inside a test both must be
        # no-ops (the test cursor forbids either for real).
        self.patch(self.env.cr, 'commit', lambda: None)
        self.patch(self.env.cr, 'rollback', lambda: None)
        # Commands that existed before the test (demo data of the access control
        # module) are not the survey's doing.
        self._commands_before = set(self.env['hr.rfid.command'].sudo().search([]).ids)

    # ------------------------------------------------------------ drivers

    def _new_run(self, **values):
        values.setdefault('company_id', self.company.id)
        return self.env['hr.rfid.hw.import.run'].create(values)

    def _work(self, run, max_passes=200):
        Run = self.env['hr.rfid.hw.import.run']
        passes = 0
        while run.state in hw_import_run.WORKER_STATES:
            Run._cron_process()
            run.invalidate_recordset()
            passes += 1
            self.assertLess(passes, max_passes, "the worker did not finish: state %s" % run.state)
        return passes

    def _add_module_b(self, run):
        wiz = self.env['hr.rfid.hw.import.add.ip.wiz'].create({'run_id': run.id, 'ip': MODULE_B_IP})
        wiz.action_add()
        return run.module_ids.filtered(lambda m: m.ip == MODULE_B_IP)

    def _survey(self, with_b=True, include_known=False):
        run = self._new_run()
        run.action_discover()
        self._work(run)
        if with_b:
            self._add_module_b(run)
        if include_known:
            run.module_ids.write({'include': True})
        run.action_read()
        self._work(run)
        return run

    def _upload_names(self, run, text=NAMES_CSV, file_name='names.csv'):
        wiz = self.env['hr.rfid.hw.import.names.wiz'].create({
            'run_id': run.id, 'file': base64.b64encode(text.encode('utf-8')), 'file_name': file_name})
        wiz.action_load()
        run.invalidate_recordset()
        return run

    def _import(self, run, **options):
        wiz = self.env['hr.rfid.hw.import.options.wiz'].with_context(default_run_id=run.id).create(
            dict({'run_id': run.id, 'default_department_id': self.department.id}, **options))
        wiz.action_start()
        self._work(run)
        return run

    # ------------------------------------------------------------ assertions

    def _write_commands(self):
        """Every command queued since the test began that is not a plain read.

        Written as an allowlist, like the sender's: a read is one of the read
        opcodes, or the read form of the alarm-setup and sensor commands. Any
        other opcode - present or future - counts as a write.
        """
        commands = self.env['hr.rfid.command'].sudo().search([('id', 'not in', list(self._commands_before))])
        return commands.filtered(lambda c: not (
            c.cmd in allowlist.READ_OPCODES
            or (c.cmd in ('B0', 'B1') and (c.cmd_data or '').startswith('01'))))

    def _with_script(self, script, faults=None):
        """Run the rest of this test against another scripted site."""
        backend = FakeBackend(script, faults=faults)
        hw_import_run.override_backend(backend)
        self.addCleanup(hw_import_run.override_backend, self.backend)
        return backend

    def _card(self, run, number):
        return run.card_ids.filtered(lambda c: c.number == number)

    def _person(self, run, name):
        return run.person_ids.filtered(lambda p: p.name == name)
