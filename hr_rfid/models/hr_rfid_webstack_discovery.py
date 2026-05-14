# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _, SUPERUSER_ID
import socket
import http.client
import json


class HrRfidWebstackDiscoveryRow(models.TransientModel):
    _name = 'hr.rfid.webstack.discovery.row'
    _description = 'Webstack discovery rows'

    name = fields.Char(
        help="Module name as reported in the UDP discovery beacon.",
    )
    last_ip = fields.Char(
        readonly=True,
        help="IP address from which the module's discovery beacon was received.",
    )
    version = fields.Char(
        readonly=True,
        help="Firmware/software version reported by the discovered module.",
    )
    hw_version = fields.Char(
        readonly=True,
        help="Hardware version reported by the discovered module.",
    )
    serial = fields.Char(
        readonly=True,
        help="Serial number reported by the discovered module — used as the unique key when adopting the module into the registered list.",
    )
    behind_nat = fields.Boolean(
        readonly=True,
        help="Discovery flag indicating whether the module sits behind a NAT and must initiate the connection itself.",
    )
    discovery_id = fields.Many2one(
        comodel_name='hr.rfid.webstack.discovery',
        readonly=True,
        help="Discovery wizard run that found this module.",
    )

class HrRfidWebstackDiscovery(models.TransientModel):
    _name = 'hr.rfid.webstack.discovery'
    _description = 'Webstack discovery'

    def _discover_ws(self):
        # TODO get list of stored webstack serials
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        udp_sock.bind(("", 30303))

        send_msg = b'Discovery:'
        res = udp_sock.sendto(send_msg, ('<broadcast>', 30303))
        if res is False:
            udp_sock.close()
            return

        added_sn = list()
        ws_env = self.env['hr.rfid.webstack'].sudo()
        ws_env_d = self.env['hr.rfid.webstack.discovery.row'].sudo()
        found_webstacks = []
        for rec in ws_env.search([('|'), ('active', '=', True), ('active', '=', False)]):
            added_sn.append(rec.serial)
        while True:
            udp_sock.settimeout(0.5)
            try:
                data, addr = udp_sock.recvfrom(1024)
                data = data.decode(errors='ignore').split('\n')[:-1]
                data = list(map(str.strip, data))
                if (len(data) == 0) or (len(data) > 100) or (data[4] in added_sn):
                    continue
                # print(data[4])
                # if data[4] in added_sn:
                #     continue
                # if len(ws_env.search([('serial', '=', data[4])])) > 0:
                #     continue
                module = {
                    'last_ip': addr[0],
                    'name': data[0],
                    'version': data[3],
                    'hw_version': data[2],
                    'serial': data[4],
                    'behind_nat': False,
                    'discovery_id': self.id,
                    # 'available': 'u',
                }
                env = ws_env_d.sudo()

                module = env.create(module)
                added_sn.append(data[4])
                found_webstacks += [module.id]
                # module.action_check_if_ws_available()

                # try:
                #     module.action_check_if_ws_available()
                # except exceptions.ValidationError as __:
                #     pass
            except socket.timeout:
                break

        udp_sock.close()
        # self.write({"found_webstacks": [(4, module.id)]})
        # self.write({"found_webstacks": [(6, 0, found_webstacks)]})
        # self.found_webstacks.action_check_if_ws_available()
        # return return_wiz_form_view(self._name, self.id)
        return found_webstacks

    found_webstacks = fields.One2many(
        comodel_name='hr.rfid.webstack.discovery.row',
        inverse_name='discovery_id',
        string='Found modules',
        default=_discover_ws,
        help='Modules that were just found during the discovery process',
    )

    what_to_do = fields.Selection(
        selection=[
            ('add', 'Add as Inactive only'),
            ('full', 'Add as Active and read all information')
        ],
        default='add',
        required=True,
        help="What happens when you click Setup — Add as Inactive: register the module but do not contact it yet (useful for cabling-pending sites). Add as Active: register + immediately call Test Connection + read controllers.",
    )

    def setup_modules(self):
        for ws in self.found_webstacks:
            ws_dict = {
                'name': ws.name,
                'version': ws.version,
                'hw_version': ws.hw_version,
                'serial': ws.serial,
                'behind_nat': True,
                'available': 'a',
                'active': True,
                'last_ip': ws.last_ip,
            }
            ws_id = self.env['hr.rfid.webstack'].sudo().create([ws_dict])
            ws_id.action_check_if_ws_available()
            ws_id.action_set_webstack_settings()
            ws_id.get_controllers()

        return self.env.ref('hr_rfid.hr_rfid_webstack_action').sudo().read()[0]


class HrRfidWebstackManualCreate(models.TransientModel):
    _name = 'hr.rfid.webstack.manual.create'
    _description = 'Webstack Manual Creation'

    webstack_name = fields.Char(
        string='Module Name',
        help="Friendly name for the module (e.g. 'Warehouse Gate Module'). Auto-filled from the serial if left empty.",
    )

    webstack_serial = fields.Char(
        string='Serial Number',
        required=True,
        help="Serial number printed on the module's label. Must be unique across the database; used as the key to talk to the device.",
    )
    behind_nat = fields.Boolean(
        default=True,
        help="Check if the module sits behind a NAT and Odoo cannot reach its IP directly. In that case the module initiates the connection; otherwise Odoo dials out via Last IP.",
    )
    local_ip_address = fields.Char(
        help="Required when Behind NAT is off — the LAN IP at which Odoo can reach the module to send commands.",
    )

    @api.onchange('webstack_serial')
    def _webstack_serial_onchange(self):
        if self.webstack_serial:
            self.webstack_name = f"Module {self.webstack_serial}"

    def create_webstack(self):
        if self.webstack_serial:
            if not self.env['hr.rfid.webstack'].with_user(SUPERUSER_ID).search([('serial', '=', self.webstack_serial)]):
                ws_id = self.env['hr.rfid.webstack'].create({
                    'name': self.webstack_name,
                    'serial': self.webstack_serial,
                    'key': False,
                    'active': True,
                    'behind_nat': self.behind_nat,
                    'last_ip': self.local_ip_address
                })
                if not self.behind_nat and ws_id:
                    ws_id.action_check_if_ws_available()
                    ws_id.get_controllers()
                    ws_id.action_set_webstack_settings()
            else:
                exceptions.ValidationError(_('This serial number already exist in the system!'))
        elif self.local_ip_address:  # not used at this moment
            ws_id = self.env['hr.rfid.webstack'].create({
                'name': self.webstack_name,
                'active': True,
                'behind_nat': True,
                # 'behind_nat': self.behind_nat,
                'last_ip': self.local_ip_address
            })
            if not self.behind_nat and ws_id:
                ws_id.action_check_if_ws_available()
                ws_id.get_controllers()
                ws_id.action_set_webstack_settings()
        else:
            exceptions.ValidationError(_('Please provide module serial number!'))

        return self.env.ref('hr_rfid.hr_rfid_webstack_action').sudo().read()[0]
