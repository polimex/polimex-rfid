"""A scripted stand-in for the module, used by tests, tours and demos.

It answers discovery, the module reads and controller commands from a plain
dict, records every call, enforces the same allowlist as the real client (a
scripted forbidden command is a test failure on both sides) and can inject a
skewed reply or a "no response" once, for the retry tests.

Script shape::

    {
        'discovery': [ {ip, hostname, mac, hw_version, fw_version, serial, bridge_port} ],
        'modules': {
            '192.0.2.10': {
                'config': {...},        # /config.json
                'details': {...},       # /sdk/details.json
                'status': {0: {...}},   # /sdk/status.json?dev=N
                'devices': {
                    15: {
                        'F0': '...hex...', 'F5': '..', ...,
                        'F3': {1: '...', 2: '...'},   # per slot
                        'F4': {1: '...'},
                        'cards': ['<record hex>', ...],  # served through F2
                        'gaps': ['B0'],                  # answered with e=14
                    },
                },
            },
        },
    }
"""
from . import allowlist
from . import codecs
from .transport import (CapabilityGap, DiscoveryFailed, ReadFailed, Reply, Unreachable, E_UNKNOWN_COMMAND,
                        E_NO_RESPONSE, E_WRONG_VALUE)


class FakeDiscovery:
    def __init__(self, script, calls):
        self.script = script
        self.calls = calls

    def broadcast(self, timeout=2.0):
        self.calls.append(('broadcast', timeout))
        if self.script.get('discovery_fault'):
            # The search itself could not run (port in use, no broadcast).
            raise DiscoveryFailed(self.script['discovery_fault'])
        return [dict(item) for item in self.script.get('discovery', [])]

    def unicast(self, ip, timeout=1.5):
        self.calls.append(('unicast', ip))
        for item in self.script.get('discovery', []):
            if item.get('ip') == ip:
                return dict(item)
        module = self.script.get('modules', {}).get(ip)
        if module and module.get('discovery'):
            return dict(module['discovery'], ip=ip)
        return None


class FakeClient:
    def __init__(self, script, ip, calls, on_log=None, faults=None):
        self.script = script
        self.ip = ip
        self.calls = calls
        self.on_log = on_log
        self.faults = faults if faults is not None else {}
        self.module = script.get('modules', {}).get(ip)

    def _need_module(self):
        if self.module is None:
            raise Unreachable("%s: no such module in the script" % self.ip)
        return self.module

    def get_config(self):
        self.calls.append(('GET', self.ip, '/config.json'))
        return dict(self._need_module().get('config', {}))

    def get_details(self):
        self.calls.append(('GET', self.ip, '/sdk/details.json'))
        return dict(self._need_module().get('details', {}))

    def get_status(self, dev):
        self.calls.append(('GET', self.ip, '/sdk/status.json?dev=%s' % dev))
        status = self._need_module().get('status', {})
        if dev not in status:
            raise Unreachable("%s: no device index %s" % (self.ip, dev))
        return dict(status[dev])

    def get_discovery(self):
        self.calls.append(('GET', self.ip, '/discovery.json'))
        return dict(self._need_module().get('discovery', {}))

    def _log(self, address, opcode, data, e_code, reply_data, skewed, attempt):
        if self.on_log:
            self.on_log({
                'address': int(address), 'opcode': opcode, 'data_sent': data,
                'e_code': e_code, 'duration_ms': 1, 'response_hex': reply_data,
                'skewed': skewed, 'attempt': attempt,
            })

    def cmd(self, address, opcode, data='', relay=False):
        opcode = allowlist.check_allowed(opcode, data)
        data = (data or '').upper()
        self.calls.append(('CMD', self.ip, int(address), opcode, data))
        devices = self._need_module().get('devices', {})
        device = devices.get(int(address))
        attempt = 1
        fault = self.faults.pop((int(address), opcode), None)
        if fault == 'skew':
            self._log(address, opcode, data, 0, '', True, attempt)
            attempt += 1
        elif fault == 'no_response':
            self._log(address, opcode, data, E_NO_RESPONSE, '', False, attempt)
            attempt += 1
        elif fault == 'wrong_value':
            # The controller refuses this request; a relay controller means
            # "not supported", every other one a plain refusal (no retry).
            self._log(address, opcode, data, E_WRONG_VALUE, '', False, attempt)
            if relay:
                raise CapabilityGap(opcode, E_WRONG_VALUE, address)
            raise ReadFailed(opcode, E_WRONG_VALUE, address)
        elif fault == 'empty':
            # Success with nothing in it.
            self._log(address, opcode, data, 0, '', False, attempt)
            return Reply(int(address), opcode, 0, '', 1, attempt, 0)
        if device is None:
            self._log(address, opcode, data, E_NO_RESPONSE, '', False, attempt)
            raise ReadFailed(opcode, E_NO_RESPONSE, address)
        if opcode in device.get('errors', {}):
            # A persistent error code for this command (a damaged bus, say).
            e_code = device['errors'][opcode]
            self._log(address, opcode, data, e_code, '', False, attempt)
            raise ReadFailed(opcode, e_code, address)
        if opcode in device.get('gaps', ()):
            self._log(address, opcode, data, E_UNKNOWN_COMMAND, '', False, attempt)
            raise CapabilityGap(opcode, E_UNKNOWN_COMMAND, address)
        reply_data = self._answer(device, opcode, data)
        self._log(address, opcode, data, 0, reply_data, False, attempt)
        return Reply(int(address), opcode, 0, reply_data, 1, attempt, 1 if fault == 'skew' else 0)

    def _answer(self, device, opcode, data):
        if opcode == 'F2':
            return self._answer_f2(device, data)
        if opcode in ('F3', 'F4'):
            slot = int(data[:2], 16)
            table = device.get(opcode, {})
            if slot in table:
                return table[slot]
            if opcode == 'F3':
                return ('%02X' % slot) + '00' * 128 + '00'
            return ('%02X' % slot) + '00' * 64
        if opcode == 'F9':
            table = device.get('F9', '')
            if data and data != '00':
                row = int(data, 16)
                return table[(row - 1) * 16:row * 16]
            return table
        if opcode == 'B0':
            return device.get('B0', '01000000')
        value = device.get(opcode)
        if value is None:
            raise CapabilityGap(opcode, E_UNKNOWN_COMMAND, None)
        return value

    def _answer_f2(self, device, data):
        cards = device.get('cards', [])
        if data == codecs.encode_f2_count():
            # 'card_count' lets a script announce more cards than it serves.
            return ''.join('0%s' % d for d in '%.5d' % device.get('card_count', len(cards)))
        position = codecs.bytes_to_num(data, 0, 5)
        count = int(data[10:12])
        page = cards[position - 1:position - 1 + count]
        return ''.join(page).upper()


class FakeBackend:
    """Drop-in for RealBackend; one instance per test, shared script."""

    def __init__(self, script, faults=None):
        self.script = script
        self.calls = []
        self.faults = dict(faults or {})

    def discovery(self):
        return FakeDiscovery(self.script, self.calls)

    def client(self, host, port=80, auth=None, on_log=None):
        return FakeClient(self.script, host, self.calls, on_log=on_log, faults=self.faults)

    def commands_sent(self):
        return [c for c in self.calls if c[0] == 'CMD']
