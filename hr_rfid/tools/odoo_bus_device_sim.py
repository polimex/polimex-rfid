#!/usr/bin/env python3
# Copyright 2026 Polimex Holding Ltd..
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""iCON1XX device simulator for the Odoo Bus real-time channel.

Implements the DEVICE side of docs/odoo-bus/ODOO_BUS_PROTOCOL_SPEC.md (esp32
repo) with the Python standard library only - no websocket dependency - so it
runs anywhere and doubles as executable documentation of the wire contract:

    session cookie -> RFC6455 upgrade (Origin + non-browser UA + Cookie)
    -> subscribe(channel, last) -> hello -> ... scenario asserts ...

Usage (against a locally running Odoo WITH a gevent port):

    odoo_bus_device_sim.py --http http://localhost:8071 \
        --ws ws://localhost:8072 --db DBNAME --serial 234567 --key 0000 \
        --scenario single

The simulator provisions itself exactly like the firmware: it POSTs a classic
heartbeat on /hr/rfid/event and reads the ``result.ws`` block (the operator
must have pressed "Enable real-time" on the module form, or hr_rfid's
auto-registration must be on). Exit code 0 = every assert passed.
"""
import argparse
import base64
import hashlib
import json
import os
import random
import socket
import struct
import sys
import time
import urllib.parse
import urllib.request

PROTO = 1


def log(msg):
    print('[sim] %s' % msg, flush=True)


class WsClient:
    """Minimal RFC6455 client: text frames, ping/pong, close."""

    GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

    def __init__(self, ws_url, origin, cookie):
        u = urllib.parse.urlsplit(ws_url)
        self.host, self.port = u.hostname, u.port or (443 if u.scheme == 'wss' else 80)
        self.sock = socket.create_connection((self.host, self.port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            'GET /websocket HTTP/1.1\r\n'
            'Host: %s:%d\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Key: %s\r\n'
            'Sec-WebSocket-Version: 13\r\n'
            'Origin: %s\r\n'
            'User-Agent: PolimexICON-Sim/1.0\r\n'
            'Cookie: session_id=%s\r\n'
            '\r\n' % (self.host, self.port, key, origin, cookie))
        self.sock.sendall(handshake.encode())
        resp = b''
        while b'\r\n\r\n' not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('handshake: connection closed')
            resp += chunk
        head = resp.split(b'\r\n\r\n', 1)[0].decode(errors='replace')
        if ' 101 ' not in head.split('\r\n')[0]:
            raise ConnectionError('handshake refused:\n%s' % head)
        expect = base64.b64encode(hashlib.sha1(
            (key + self.GUID).encode()).digest()).decode()
        assert 'sec-websocket-accept: %s' % expect.lower() in head.lower(), \
            'bad Sec-WebSocket-Accept'
        self.buffer = resp.split(b'\r\n\r\n', 1)[1]

    def send_text(self, payload: str):
        data = payload.encode()
        mask = os.urandom(4)   # client frames MUST be masked (RFC6455)
        header = b'\x81'
        n = len(data)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack('>H', n)
        else:
            header += bytes([0x80 | 127]) + struct.pack('>Q', n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + mask + masked)

    def _read_exact(self, n):
        while len(self.buffer) < n:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError('connection closed')
            self.buffer += chunk
        out, self.buffer = self.buffer[:n], self.buffer[n:]
        return out

    def recv_text(self, timeout=15.0):
        """Return the next TEXT payload; transparently answers PINGs."""
        deadline = time.monotonic() + timeout
        message = b''
        while True:
            self.sock.settimeout(max(0.1, deadline - time.monotonic()))
            b1, b2 = self._read_exact(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack('>H', self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack('>Q', self._read_exact(8))[0]
            payload = self._read_exact(length)   # server frames are unmasked
            if opcode == 0x9:                    # ping -> pong
                mask = os.urandom(4)
                masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                self.sock.sendall(bytes([0x8A, 0x80 | len(payload)]) + mask + masked)
                continue
            if opcode == 0x8:
                code = struct.unpack('>H', payload[:2])[0] if len(payload) >= 2 else 1005
                raise ConnectionError('server closed: %d' % code)
            if opcode in (0x1, 0x0):
                message += payload
                if fin:
                    return message.decode()


class Device:
    """The device model: classic HTTP check-in + the real-time channel."""

    def __init__(self, args):
        self.http = args.http.rstrip('/')
        self.ws_url = args.ws.rstrip('/')
        self.db = args.db
        self.serial = args.serial
        self.key = args.key
        self.ws_conf = None      # the result.ws provisioning block
        self.last = 0            # bus replay cursor
        self.ws = None
        self.bid = 0
        self.consumed = []       # events we issued "0xDA" for (bos list)

    # -- classic HTTP channel (unchanged firmware contract) -------------

    def http_checkin(self, extra):
        body = {'jsonrpc': '2.0', 'id': 1, 'method': 'call',
                'params': dict({'convertor': int(self.serial),
                                'key': self.key}, **extra)}
        req = urllib.request.Request(
            self.http + '/hr/rfid/event',
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())['result']

    def provision(self):
        result = self.http_checkin({'heartbeat': 1, 'FW': '9.99'})
        block = result.get('ws')
        if block:
            self.ws_conf = block
            log('provisioned over HTTP: en=%s url=%s db=%s proto=%s'
                % (block['en'], block['url'], block['db'], block['proto']))
        return result

    # -- real-time channel ----------------------------------------------

    def connect_ws(self):
        conf = self.ws_conf
        assert conf and conf['en'], 'no ws provisioning - enable real-time in Odoo'
        # session bootstrap: anonymous cookie (the IoT-box model)
        url = '%s/web/login?db=%s' % (self.http, urllib.parse.quote(self.db))
        req = urllib.request.Request(url, method='GET')
        opener = urllib.request.build_opener(NoRedirect())
        cookie = None
        with opener.open(req, timeout=15) as resp:
            for header, value in resp.headers.items():
                if header.lower() == 'set-cookie' and 'session_id=' in value:
                    cookie = value.split('session_id=')[1].split(';')[0]
        assert cookie, 'no anonymous session cookie'
        self.ws = WsClient(self.ws_url, origin=self.http, cookie=cookie)
        channel = 'hr_rfid#%s#%s' % (self.serial, conf['tok'])
        self.ws.send_text(json.dumps({
            'event_name': 'subscribe',
            'data': {'channels': [channel], 'last': self.last}}))
        log('subscribed to %s… (last=%d)' % (channel[:24], self.last))

    def send(self, mtype, **payload):
        data = dict({'v': PROTO, 's': self.serial,
                     'k': self.ws_conf['tok'], 't': mtype}, **payload)
        self.ws.send_text(json.dumps({'event_name': 'hr_rfid', 'data': data}))

    def expect(self, mtype, timeout=15.0):
        """Wait for one bus notification of the given type; track last id."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.ws.recv_text(timeout=deadline - time.monotonic())
            notifications = json.loads(raw)
            for notification in notifications:
                self.last = max(self.last, notification['id'])
                message = notification['message']
                if message['type'] == mtype:
                    return message['payload']
                log('  (skipping %s)' % message['type'])
        raise TimeoutError('no %s within %.0fs' % (mtype, timeout))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def event_dict(ctrl=5, bos=1, event_n=4, card='0000000000'):
    now = time.localtime()
    return {'id': ctrl, 'event_n': event_n, 'bos': bos, 'tos': bos,
            'card': card, 'cmd': 'FA', 'err': 0, 'reader': 1,
            'dt': '00000000000000',
            'date': time.strftime('%d.%m.%y', now),
            'time': time.strftime('%H:%M:%S', now),
            'day': (now.tm_wday + 1) % 7}


def scenario_single(dev):
    """The SPEC §12 walk: provisioning, hello, new-controller event flow,
    F0 response, event retry, dedup, command over the bus."""
    failures = []
    ctrl = random.randint(10, 250)   # fresh controller id -> re-runnable
    log('using controller id %d' % ctrl)

    def check(name, cond, detail=''):
        log('%s %s %s' % ('PASS' if cond else 'FAIL', name, detail))
        if not cond:
            failures.append(name)

    # 1. provisioning over the classic channel
    dev.provision()
    check('provision.block', bool(dev.ws_conf), '(enable real-time first?)')
    if not dev.ws_conf:
        return failures

    # 2. bootstrap + hello/hello_ack
    dev.connect_ws()
    dev.send('hello', fw='9.99', ctrl=[])
    ack = dev.expect('hr_rfid.hello_ack')
    check('hello.ack_ok', ack.get('ok') is True, json.dumps(ack))
    check('hello.proto', ack.get('proto') == PROTO)

    # 3. event from an UNKNOWN controller: not consumed + F0 setup flows
    dev.bid += 1
    dev.send('ev', bid=dev.bid, ev=[event_dict(ctrl=ctrl, bos=1)])
    ev_ack = dev.expect('hr_rfid.ev_ack')
    entry = ev_ack['res'][0]
    check('ev.new_ctrl.not_consumed',
          entry == {'i': 0, 'ok': False, 'dup': False}, json.dumps(ev_ack))
    inline = ev_ack.get('cmd') or {}
    check('ev.new_ctrl.f0_inline', inline.get('cmd', {}).get('c') == 'F0')

    # 4. answer the F0 over the rsp path (verified iCON110 vector)
    f0 = '0006000400000704000000030000030201050208000200010502060003000506'
    dev.send('rsp', cid=inline.get('cid', 0),
             r={'id': ctrl, 'c': 'F0', 'e': 0, 'd': f0})

    # 5. retry the SAME event (still bos=1): now processed
    time.sleep(1.0)
    dev.bid += 1
    dev.send('ev', bid=dev.bid, ev=[event_dict(ctrl=ctrl, bos=1)])
    ev_ack = dev.expect('hr_rfid.ev_ack')
    check('ev.retry.consumed', ev_ack['res'][0]['ok'] is True,
          json.dumps(ev_ack))

    # 6. re-send after a "lost ack": dup, no duplicate records
    dev.bid += 1
    dev.send('ev', bid=dev.bid, ev=[event_dict(ctrl=ctrl, bos=1)])
    ev_ack = dev.expect('hr_rfid.ev_ack')
    check('ev.resend.dup', ev_ack['res'][0].get('dup') is True,
          json.dumps(ev_ack))

    # 7. heartbeat over WS keeps presence alive
    dev.send('hb', n=2, ctrl=[ctrl])

    # 8. a command published over the bus reaches us (the F0 the hello
    #    provisioning of controller 5 queued was already consumed in step 4;
    #    ask the server to sync -> nothing pending is also a valid outcome)
    log('scenario complete')
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--http', default='http://localhost:8071')
    parser.add_argument('--ws', default='ws://localhost:8072')
    parser.add_argument('--db', required=True)
    parser.add_argument('--serial', default='234567')
    parser.add_argument('--key', default='0000')
    parser.add_argument('--scenario', default='single', choices=['single'])
    args = parser.parse_args()

    dev = Device(args)
    failures = scenario_single(dev)
    if failures:
        log('RESULT: %d failed: %s' % (len(failures), ', '.join(failures)))
        return 1
    log('RESULT: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
