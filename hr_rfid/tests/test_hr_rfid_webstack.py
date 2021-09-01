from odoo.tests import common
from odoo import exceptions, fields
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, \
    get_ws_doors, create_employees, create_departments
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from queue import Queue
from functools import partial

import json


class WebstackEmulationHandler(BaseHTTPRequestHandler):
    def __init__(self, queue: Queue, *args, **kwargs):
        self._q = queue
        super().__init__(*args, **kwargs)

    def do_GET(self):
        body = {
            'bridgeClient': {
                'add_info': 0,
                'auto_connect': 0,
                'last_error': 0,
                'port': 5000,
                'status': 0,
                'url': 'url.or.ip.com'
            },
            'convertor': 404040,
            'currentIPFiltering': {
                'IP1': '0.0.0.0',
                'checkbox_Enable_IP1_filter': ''
            },
            'inputOutputHardware': {
                'portInDigital': 5,
                'portOut': 4,
                'uarts': [
                    [
                        0,
                        [
                            0,
                            2,
                            5
                        ]
                    ],
                    [
                        2,
                        [
                            0,
                            1,
                            2,
                            5
                        ]
                    ]
                ]
            },
            'netConfig': {
                'Gateway': '192.168.74.254',
                'Host_Name': 'WIFI-16C4',
                'IP_Address': '192.168.74.61',
                'MAC_Address': '24:0a:c4:16:04:c3',
                'Primary_DNS': '192.168.74.254',
                'Secondary_DNS': '0.0.0.0',
                'Subnet_Mask': '255.255.255.0',
                'checkbox_DHCP': 'checked',
                'net_mode': 1,
                'sntp_server': 'bg.pool.ntp.org'
            },
            'sdk': {
                'ConnectionType': 3,
                'TCPStackVersion': 'v3.3-71-g46b12a5',
                'devFound': 1,
                'deviceTime': 1571388442,
                'freeRAM': 69716,
                'heartBeatCounter': 2375,
                'heartBeatTimeOut': 11,
                'isBridgeActive': 0,
                'isCmdExecute': 0,
                'isCmdWaiting': 0,
                'isDeviceScan': 0,
                'isEventPause': 0,
                'isEventScan': 1,
                'isServerToSendDown': 0,
                'maxDevInList': 64,
                'remoteIP': '0.0.0.0',
                'scanIDfrom': 0,
                'scanIDprogress': 0,
                'scanIDto': 254,
                'sdkHardware': '100.1',
                'sdkVersion': '1.46',
                'upTime': '1d 15:51:08'
            },
            'sdkSettings': {
                'Bridge_PORT': 5000,
                'HeartBeat_Time': 60,
                'Server_PORT': '8069',
                'Server_URL': 'ilian.com/hr/rfid/event',
                'checkbox_Enable_HTTP_IO_Event_Server_Push': '',
                'checkbox_Enable_HTTP_Pull_Technology': 'checked',
                'checkbox_Enable_HTTP_Server_Push': 'checked',
                'checkbox_Enable_HeartBeat': 'checked',
                'checkbox_Enable_TCP_Bridge': 'checked',
                'checkbox_Enable_custom_Bridge_port': '',
                'checkbox_SDK_Password_Require': '',
                'enable_odoo': 1,
                'enable_tls': 0,
                'modbus_id': 239,
                'modbus_port': 502,
                'modbus_uart_timeout': 1000,
                'rbridge_started': 0
            },
            'uartConfig': [
                {
                    'br': 9600,
                    'db': 3,
                    'fc': 0,
                    'ft': 122,
                    'port': 0,
                    'pr': 0,
                    'rt': False,
                    'sb': 1,
                    'usage': 0
                },
                {
                    'br': 9600,
                    'db': 3,
                    'fc': 0,
                    'ft': 122,
                    'port': 2,
                    'pr': 0,
                    'rt': False,
                    'sb': 1,
                    'usage': 1
                }
            ],
            'wifiConfig': {
                'apauth': 3,
                'apbeac': 100,
                'apchan': 11,
                'aphidd': 0,
                'apmac': '00:24:fe:3f:00:00',
                'apmaxc': 4,
                'apssid': 'WIFI-16C4',
                'chan': 0,
                'mode': 1,
                'phy': 5,
                'rssi': 0,
                'ssid': 'PH',
                'stamac': '24:0a:c4:16:04:c0',
                'status': 1073610744
            }
        }
        body = json.dumps(body)
        self.send_response(200)
        self.send_header('content-length', len(body))
        self.end_headers()
        self.wfile.write(body.encode())

    def do_POST(self):
        buff = self.rfile.read(int(self.headers['content-length'])).decode()
        self._q.put(buff)
        self.send_response(200)

        if self.path == '/sdk/cmd.json':
            js = json.loads(buff)
            response = {
                'convertor': 423152,
                'response': {
                    'id': js['cmd']['id'],
                    'c': js['cmd']['c'],
                    'e': 0,
                    'd': '',
                }
            }
            response = json.dumps(response).encode()
            self.send_header('content-length', len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.end_headers()


class HttpServerThread(Thread):
    def __init__(self, server: HTTPServer):
        super().__init__()
        self._server = server

    def run(self):
        self._server.serve_forever()


class WebstackTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(WebstackTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])

    def run_test_webstack_server(self):
        queue = Queue()
        self._q = queue
        custom_handler = partial(WebstackEmulationHandler, queue)
        self._ws_server = HTTPServer(('', 80), custom_handler)
        self._ws_server_thread = HttpServerThread(self._ws_server)
        self._ws_server_thread.start()

    def stop_test_webstack_server(self):
        self._ws_server.shutdown()
        self._ws_server_thread.join()
        self._ws_server = None
        self._ws_server_thread = None

    def test_action_set_webstack_settings(self):
        self._ws.last_ip = 'localhost'

        with self.assertRaises(exceptions.ValidationError):
            self._ws.action_set_webstack_settings()

        self.run_test_webstack_server()

        try:
            self._ws.action_set_webstack_settings()
        except exceptions.ValidationError:
            self.fail(msg="action_set_webstack_settings failed when it shouldn't have")
        finally:
            self.stop_test_webstack_server()

        self.assertEqual(self._q.qsize(), 2)

        msg = self._q.get()

        try:
            js_uart_conf = json.loads(msg)
        except json.decoder.JSONDecodeError as e:
            self.fail('Could not load js_uart_conf even though we should have been able to. Error: ' + e.msg)

        self.assertEqual(type(js_uart_conf), type([]))
        self.assertEqual(len(js_uart_conf), 2)

        js1 = js_uart_conf[0]
        js2 = js_uart_conf[1]

        self.assertIn('br', js1)
        self.assertIn('db', js1)
        self.assertIn('fc', js1)
        self.assertIn('ft', js1)
        self.assertIn('port', js1)
        self.assertIn('pr', js1)
        self.assertIn('rt', js1)
        self.assertIn('sb', js1)
        self.assertIn('usage', js1)
        self.assertEqual(js1['br'], 9600)
        self.assertEqual(js1['db'], 3)
        self.assertEqual(js1['fc'], 0)
        self.assertEqual(js1['ft'], 122)
        self.assertEqual(js1['port'], 0)
        self.assertEqual(js1['pr'], 0)
        self.assertEqual(js1['rt'], False)
        self.assertEqual(js1['sb'], 1)
        self.assertEqual(js1['usage'], 0)
        self.assertIn('br', js2)
        self.assertIn('db', js2)
        self.assertIn('fc', js2)
        self.assertIn('ft', js2)
        self.assertIn('port', js2)
        self.assertIn('pr', js2)
        self.assertIn('rt', js2)
        self.assertIn('sb', js2)
        self.assertIn('usage', js2)
        self.assertEqual(type(js1['br']), type(0))
        self.assertEqual(type(js1['db']), type(0))
        self.assertEqual(type(js1['fc']), type(0))
        self.assertEqual(type(js1['ft']), type(0))
        self.assertEqual(type(js1['port']), type(0))
        self.assertEqual(type(js1['pr']), type(0))
        self.assertEqual(type(js1['rt']), type(False))
        self.assertEqual(type(js1['sb']), type(0))
        self.assertEqual(type(js1['usage']), type(0))

        msg = self._q.get()
        odoo_url = str(self.env['ir.config_parameter'].get_param('web.base.url'))
        splits = odoo_url.split(':')
        odoo_url = splits[1][2:]
        if len(splits) == 3:
            odoo_port = int(splits[2], 10)
        else:
            odoo_port = 80
        odoo_url += '/hr/rfid/event'

        params = str(msg).split('&')
        self.assertEqual(len(params), 9)
        self.assertIn('sdk=1', params)
        self.assertIn('stsd=1', params)
        self.assertIn('sdts=1', params)
        self.assertIn('stsu=' + odoo_url, params)
        self.assertIn('prt=' + str(odoo_port), params)
        self.assertIn('hb=1', params)
        self.assertIn('thb=60', params)
        self.assertIn('odoo=1', params)

    def test_action_check_if_ws_available(self):
        # TODO Check if it will throw an error if we send it bad data
        self._ws.last_ip = 'localhost'

        with self.assertRaises(exceptions.ValidationError):
            self._ws.action_check_if_ws_available()

        self.run_test_webstack_server()

        try:
            self._ws.action_check_if_ws_available()
        except exceptions.ValidationError:
            self.fail(msg="action_check_if_ws_available failed when it shouldn't have")
        finally:
            self.stop_test_webstack_server()

        self.assertEqual(self._q.qsize(), 0)

    def test_action_set_active_inactive(self):
        self._ws.action_set_active()
        self.assertTrue(self._ws.active)
        self._ws.action_set_active()
        self.assertTrue(self._ws.active)
        self._ws.action_set_inactive()
        self.assertFalse(self._ws.active)
        self._ws.action_set_inactive()
        self.assertFalse(self._ws.active)
        self._ws.action_set_active()
        self.assertTrue(self._ws.active)


class ControllerTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(ControllerTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])
        cls._controllers = cls._ws.controllers
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 2)
        cls._contacts = create_contacts(cls.env, [ 'Josh', 'Uncool Josh', 'Reaver Spolarity' ])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[1])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[1])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)

    def test_button_reload_cards(self):
        rels_env = self.env['hr.rfid.card.door.rel']
        rels_env.search([]).unlink()

        self._controllers[0].button_reload_cards()
        rels = rels_env.search([])

        self.assertEqual(len(rels), 5)

        expected_rels = [
            (self._cards[0], self._doors[0], self._def_ts),
            (self._cards[1], self._doors[0], self._def_ts),
            (self._cards[1], self._doors[1], self._def_ts),
            (self._cards[2], self._doors[0], self._def_ts),
            (self._cards[2], self._doors[1], self._def_ts),
        ]
        rels = [ (a.card_id, a.door_id, a.time_schedule_id) for a in rels ]
        self.assertCountEqual(expected_rels, rels)

        rels_env.search([]).unlink()
        self.env['hr.rfid.access.group'].search([]).unlink()

        self._controllers[0].button_reload_cards()
        rels = rels_env.search([])
        self.assertFalse(rels.exists())

    def test_change_io_table(self):
        ctrl = self._controllers[0]
        cmds_env = self.env['hr.rfid.command']
        cmds_env.search([]).unlink()

        def_io_table = ctrl.get_default_io_table(ctrl.hw_version, ctrl.sw_version, ctrl.mode)
        ctrl.io_table = def_io_table
        new_io_table = def_io_table[0] + str(9 - int(def_io_table[0])) + def_io_table[2:]

        ctrl.change_io_table(new_io_table)

        cmd = cmds_env.search([])
        self.assertEqual(len(cmd), 1)
        self.assertEqual(cmd.webstack_id, ctrl.webstack_id)
        self.assertEqual(cmd.controller_id, ctrl)
        self.assertEqual(cmd.cmd, 'D9')
        self.assertEqual(cmd.cmd_data, '00' + new_io_table)

        cmds_env.search([]).unlink()

        ctrl.change_io_table(ctrl.io_table)
        cmd = cmds_env.search([])
        self.assertFalse(cmd.exists())

    def test_io_table_wizard(self):
        ctrl = self._controllers[0]
        ctrl.io_table = ctrl.get_default_io_table(ctrl.hw_version, ctrl.sw_version, ctrl.mode)
        wiz = self.env['hr.rfid.ctrl.io.table.wiz'].with_context(active_ids=ctrl.id).create({})

        wiz_io_table = ''
        for row in wiz.io_row_ids:
            outs = [ row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1 ]
            row_str = ''.join([ '%02X' % a for a in outs ])
            wiz_io_table += row_str

        self.assertEqual(ctrl.io_table, wiz_io_table)

        wiz.io_row_ids[0].out5 = 9 - wiz.io_row_ids[0].out5
        wiz.io_row_ids[1].out5 = 9 - wiz.io_row_ids[1].out5
        wiz.io_row_ids[2].out5 = 9 - wiz.io_row_ids[2].out5
        wiz.io_row_ids[3].out5 = 9 - wiz.io_row_ids[3].out5
        wiz.io_row_ids[4].out5 = 9 - wiz.io_row_ids[4].out5
        wiz.io_row_ids[5].out5 = 9 - wiz.io_row_ids[5].out5

        new_io_table = ''
        for row in wiz.io_row_ids:
            outs = [ row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1 ]
            row_str = ''.join([ '%02X' % a for a in outs ])
            new_io_table += row_str

        wiz.save_table()
        self.assertEqual(new_io_table, ctrl.io_table)


class DoorTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(DoorTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2, 1])
        cls._controllers = cls._ws.controllers
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 2)
        cls._contacts = create_contacts(cls.env, [ 'Josh', 'Uncool Josh', 'Reaver Spolarity' ])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[1])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[1])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)

    def run_test_webstack_server(self):
        queue = Queue()
        self._q = queue
        custom_handler = partial(WebstackEmulationHandler, queue)
        self._ws_server = HTTPServer(('', 80), custom_handler)
        self._ws_server_thread = HttpServerThread(self._ws_server)
        self._ws_server_thread.start()

    def stop_test_webstack_server(self):
        self._ws_server.shutdown()
        self._ws_server_thread.join()
        self._ws_server = None
        self._ws_server_thread = None

    def test_get_potential_cards(self):
        door = self._doors[0]

        cards = door.get_potential_cards()
        expected_cards = [
            (self._cards[0], self._def_ts),
            (self._cards[1], self._def_ts),
            (self._cards[2], self._def_ts),
        ]
        self.assertEqual(cards, expected_cards)

        self._contacts[0].remove_acc_gr(self._acc_grs[0])

        cards = door.get_potential_cards()
        expected_cards = [
            (self._cards[1], self._def_ts),
            (self._cards[2], self._def_ts),
        ]
        self.assertEqual(cards, expected_cards)

        self._contacts[1].remove_acc_gr(self._acc_grs[0])

        cards = door.get_potential_cards()
        self.assertEqual(len(cards), 0)

    def test_create_door_out_cmd(self):
        cmd_env = self.env['hr.rfid.command']
        door = self._doors[0]
        door.controller_id.webstack_id.behind_nat = True

        cmd_env.search([]).unlink()

        out = 1
        time = 5
        door.create_door_out_cmd(out, time)

        c = cmd_env.search([])
        self.assertEqual(len(c), 1)
        self.assertEqual(c.webstack_id, self._ws[0])
        self.assertEqual(c.controller_id, self._controllers[0])
        self.assertEqual(c.cmd, 'DB')
        self.assertEqual(c.cmd_data, '%02d%02d%02d' % (door.number, out, time))

        cmd_env.search([]).unlink()

        out = 0
        time = 15
        door.create_door_out_cmd(out, time)

        c = cmd_env.search([])
        self.assertEqual(len(c), 1)
        self.assertEqual(c.webstack_id, self._ws[0])
        self.assertEqual(c.controller_id, self._controllers[0])
        self.assertEqual(c.cmd, 'DB')
        self.assertEqual(c.cmd_data, '%02d%02d%02d' % (door.number, out, time))

    def test_change_door_out(self):
        door = self._doors[0]
        door.controller_id.webstack_id.behind_nat = False

        out = 1
        time = 5

        with self.assertRaises(exceptions.ValidationError):
            door.change_door_out(out, time)

        self.run_test_webstack_server()

        try:
            door.change_door_out(out, time)
        except exceptions.ValidationError:
            self.fail(msg="change_door_out failed when it shouldn't have")
        finally:
            self.stop_test_webstack_server()

        self.assertEqual(self._q.qsize(), 1)

        msg = self._q.get()

        try:
            js = json.loads(msg)
        except json.decoder.JSONDecodeError as e:
            self.fail('Could not load js even though we should have been able to. Error: ' + e.msg)

        self.assertEqual(type(js), type({}))
        self.assertEqual(len(js), 1)
        self.assertIn('cmd', js)

        cmd = js['cmd']

        self.assertEqual(type(cmd), type({}))
        self.assertEqual(len(cmd), 3)
        self.assertIn('id', cmd)
        self.assertIn('c', cmd)
        self.assertIn('d', cmd)

        self.assertEqual(cmd['id'], door.controller_id.ctrl_id)
        self.assertEqual(cmd['c'], 'DB')
        self.assertEqual(cmd['d'], '%02d%02d%02d' % (door.number, out, time))

    def test_write_card_type(self):
        rel_env = self.env['hr.rfid.card.door.rel']
        door = self._doors[0]
        card = self._cards[0]

        rel = rel_env.search([ ('door_id', '=', door.id), ('card_id', '=', card.id) ])
        self.assertEqual(len(rel), 1)

        door.write({ 'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_1').id })
        rel = rel_env.search([ ('door_id', '=', door.id), ('card_id', '=', card.id) ])
        self.assertEqual(len(rel), 0)

        door.write({ 'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_def').id })
        rel = rel_env.search([ ('door_id', '=', door.id), ('card_id', '=', card.id) ])
        self.assertEqual(len(rel), 1)

    def test_write_apb_mode(self):
        door = self._doors[0]
        cmd_env = self.env['hr.rfid.command']

        door.apb_mode = False
        cmd_env.search([]).unlink()

        with self.assertRaises(exceptions.ValidationError):
            door.write({ 'apb_mode': True })

        door = self._doors[2]

        door.apb_mode = False
        door.write({ 'apb_mode': True })
        self.assertTrue(door.apb_mode)
        cmd = cmd_env.search([])

        self.assertEqual(len(cmd), 1)
        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'DE')
        self.assertEqual(cmd.cmd_data, '%02d' % door.number)

        door.write({ 'apb_mode': False })

        self.assertTrue(cmd.exists())
        self.assertEqual(cmd, cmd_env.search([]))
        self.assertEqual(cmd.webstack_id, door.controller_id.webstack_id)
        self.assertEqual(cmd.controller_id, door.controller_id)
        self.assertEqual(cmd.cmd, 'DE')
        self.assertEqual(cmd.cmd_data, '00')


class ReaderTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(ReaderTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])
        cls._controllers = cls._ws.controllers
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 2)
        cls._contacts = create_contacts(cls.env, [ 'Josh', 'Uncool Josh', 'Reaver Spolarity' ])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[1])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[1])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)

    def test_write_mode(self):
        ctrl = self._controllers[0]
        door = ctrl.door_ids[0]
        reader = door.reader_ids[0]
        cmd_env = self.env['hr.rfid.command']

        cmd_env.search([]).unlink()

        reader.write({ 'mode': reader.mode })
        c = cmd_env.search([])
        self.assertFalse(c.exists())

        if reader.mode == '01':
            mode = '02'
        else:
            mode = '01'

        reader.write({ 'mode': mode })
        c = cmd_env.search([])

        expected_data = ''
        for reader in ctrl.reader_ids:
            expected_data += str(reader.mode) + '0100'

        self.assertEqual(len(c), 1)
        self.assertEqual(c.webstack_id, self._ws[0])
        self.assertEqual(c.controller_id, self._controllers[0])
        self.assertEqual(c.cmd, 'D6')
        self.assertEqual(c.cmd_data, expected_data)


class UserEventTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(UserEventTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, webstacks=1, controllers=[2, 2, 0x22, 1])
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 4)
        cls._departments = create_departments(cls.env, ['Upstairs Office', 'Downstairs Office'])

        cls._employees = create_employees(cls.env,
                                          ['Max', 'Cooler Max', 'Jacob', 'Andrej'],
                                          [cls._departments[0], cls._departments[1]])
        cls._contacts = create_contacts(cls.env, ['Greg', 'Cooler Greg', 'Richard'])

        cls._departments[0].hr_rfid_allowed_access_groups = cls._acc_grs[0] + cls._acc_grs[1]
        cls._departments[1].hr_rfid_allowed_access_groups = cls._acc_grs[1] + cls._acc_grs[2] + cls._acc_grs[3]

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._employees[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[0])

        cls._employees[0].add_acc_gr(cls._acc_grs[0])
        cls._employees[1].add_acc_gr(cls._acc_grs[1])
        cls._employees[3].add_acc_gr(cls._acc_grs[3])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[2])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')
        cls._other_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_1')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)
        cls._acc_grs[2].add_doors(cls._doors[2] + cls._doors[3], cls._def_ts)
        cls._acc_grs[3].add_doors(cls._doors[4], cls._other_ts)

    def test_create_one_reader_door(self):
        ev_env = self.env['hr.rfid.event.user']
        door = self._doors[0]
        employee = self._employees[0]
        contact = self._contacts[0]
        zone = self.env['hr.rfid.zone'].create({ 'name': 'asd' })
        zone.door_ids = door

        self.assertEqual(len(door.reader_ids), 1)

        ev_env.create({
            'ctrl_addr': 1,
            'employee_id': employee.id,
            'door_id': door.id,
            'reader_id': door.reader_ids[0].id,
            'card_id': employee.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertEqual(zone.employee_ids, employee)

        ev_env.create({
            'ctrl_addr': 1,
            'contact_id': contact.id,
            'door_id': door.id,
            'reader_id': door.reader_ids[0].id,
            'card_id': contact.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertEqual(zone.contact_ids, contact)

        ev_env.create({
            'ctrl_addr': 1,
            'employee_id': employee.id,
            'door_id': door.id,
            'reader_id': door.reader_ids[0].id,
            'card_id': employee.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertFalse(zone.employee_ids)

        ev_env.create({
            'ctrl_addr': 1,
            'contact_id': contact.id,
            'door_id': door.id,
            'reader_id': door.reader_ids[0].id,
            'card_id': contact.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertFalse(zone.contact_ids)

    def test_create_two_reader_door(self):
        ev_env = self.env['hr.rfid.event.user']
        door = self._ws[0].controllers[3].door_ids[0]
        employee = self._employees[0]
        zone = self.env['hr.rfid.zone'].create({ 'name': 'asd' })
        zone.door_ids = door

        self.assertEqual(len(door.reader_ids), 2)

        in_reader  = door.reader_ids[0] if door.reader_ids[0].reader_type == '0' else door.reader_ids[1]
        out_reader = door.reader_ids[0] if door.reader_ids[0].reader_type == '1' else door.reader_ids[1]

        ev_env.create({
            'ctrl_addr': 1,
            'employee_id': employee.id,
            'door_id': door.id,
            'reader_id': in_reader.id,
            'card_id': employee.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertEqual(zone.employee_ids, employee)

        ev_env.create({
            'ctrl_addr': 1,
            'employee_id': employee.id,
            'door_id': door.id,
            'reader_id': out_reader.id,
            'card_id': employee.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })
        self.assertFalse(zone.employee_ids)

    def test_create_workcode_door(self):
        ev_env = self.env['hr.rfid.event.user']
        door = self._doors[0]
        reader = door.reader_ids[0]
        employee = self._employees[0]
        zone = self.env['hr.rfid.zone'].create({ 'name': 'asd' })
        wc_env = self.env['hr.rfid.workcode']
        workcode_start = wc_env.create({ 'name': 'asd1', 'workcode': '0001', 'user_action': 'start' })
        workcode_break = wc_env.create({ 'name': 'asd2', 'workcode': '0002', 'user_action': 'break' })
        workcode_stop  = wc_env.create({ 'name': 'asd3', 'workcode': '0003', 'user_action': 'stop'  })

        zone.door_ids = door
        reader.mode = '03'
        self.assertEqual(len(door.reader_ids), 1)

        def create_ev(wc):
            create_ev.second += 1
            return ev_env.create({
                'ctrl_addr': 1,
                'employee_id': employee.id,
                'door_id': door.id,
                'reader_id': reader.id,
                'workcode_id': wc.id,
                'card_id': employee.hr_rfid_card_ids[0].id,
                'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:' + ('%02d' % create_ev.second)),
                'event_action': '1',
            })
        create_ev.second = 1

        create_ev(workcode_stop)
        self.assertFalse(zone.employee_ids)

        create_ev(workcode_start)
        self.assertEqual(zone.employee_ids, employee)

        create_ev(workcode_break)
        self.assertFalse(zone.employee_ids)

        create_ev(workcode_stop)
        self.assertEqual(zone.employee_ids, employee)

        create_ev(workcode_stop)
        self.assertFalse(zone.employee_ids)


class CommandTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(CommandTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, webstacks=1, controllers=[2, 2, 0x22])
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 4)
        cls._departments = create_departments(cls.env, ['Upstairs Office', 'Downstairs Office'])

        cls._employees = create_employees(cls.env,
                                          ['Max', 'Cooler Max', 'Jacob', 'Andrej'],
                                          [cls._departments[0], cls._departments[1]])
        cls._contacts = create_contacts(cls.env, ['Greg', 'Cooler Greg', 'Richard'])

        cls._departments[0].hr_rfid_allowed_access_groups = cls._acc_grs[0] + cls._acc_grs[1]
        cls._departments[1].hr_rfid_allowed_access_groups = cls._acc_grs[1] + cls._acc_grs[2] + cls._acc_grs[3]

        cls._employees[0].add_acc_gr(cls._acc_grs[0])
        cls._employees[1].add_acc_gr(cls._acc_grs[1])
        cls._employees[3].add_acc_gr(cls._acc_grs[3])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[2])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')
        cls._other_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_1')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)
        cls._acc_grs[2].add_doors(cls._doors[2] + cls._doors[3], cls._def_ts)
        cls._acc_grs[3].add_doors(cls._doors[4], cls._other_ts)

    def test_create_d1_cmd(self):
        pass  # TODO Implement

    def test_add_remove_card(self):
        pass  # TODO Implement

    def test_add_card(self):
        pass  # TODO Implement

    def test_remove_card(self):
        pass  # TODO Implement

    def test_change_apb_flag(self):
        pass  # TODO Implement

    def test_create(self):
        pass  # TODO Implement

    def test_write(self):
        pass  # TODO Implement
