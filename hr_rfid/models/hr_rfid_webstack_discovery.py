# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _, SUPERUSER_ID
import socket
import http.client
import json


class HrRfidWebstackDiscoveryRow(models.TransientModel):
    _name = 'hr.rfid.webstack.discovery.row'
    _description = 'Webstack discovery rows'

    name = fields.Char()
    last_ip = fields.Char(
        readonly=True
    )
    version = fields.Char(
        readonly=True
    )
    hw_version = fields.Char(
        readonly=True
    )
    serial = fields.Char(
        readonly=True
    )
    behind_nat = fields.Boolean(
        readonly=True
    )
    discovery_id = fields.Many2one(
        comodel_name='hr.rfid.webstack.discovery',
        readonly=True,
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
                data = data.decode().split('\n')[:-1]
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
        required=True
    )

    def setup_modules(self):
        for ws in self.found_webstacks:
            ws_dict = {
                'name': ws.name,
                'version': ws.version,
                'hw_version': ws.hw_version,
                'serial': ws.serial,
                'behind_nat': False,
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
        # required=True,
    )

    webstack_serial = fields.Char(
        string='Serial Number',
        required=True,
    )
    behind_nat = fields.Boolean(
        default=True
    )
    local_ip_address = fields.Char(

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
                'behind_nat': self.behind_nat,
                'last_ip': self.local_ip_address
            })
            if not self.behind_nat and ws_id:
                ws_id.action_check_if_ws_available()
                ws_id.get_controllers()
                ws_id.action_set_webstack_settings()
        else:
            exceptions.ValidationError(_('Please provide module serial number!'))

        return self.env.ref('hr_rfid.hr_rfid_webstack_action').sudo().read()[0]
