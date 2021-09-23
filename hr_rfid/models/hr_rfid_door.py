import base64
import socket

import requests

from odoo import fields, models, api, _, exceptions, SUPERUSER_ID
import http.client
import json

from odoo.addons.hr_rfid.models.hr_rfid_card import HrRfidCard
from odoo.addons.hr_rfid.models.hr_rfid_event_system import HrRfidSystemEvent
from odoo.addons.hr_rfid.models.hr_rfid_event_user import HrRfidUserEvent
from ..wizards.helpers import create_and_ret_d_box, return_wiz_form_view


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Name',
        help='A label to easily differentiate doors',
        required=True,
        index=True,
        tracking=True,
    )

    number = fields.Integer(
        string='Number',
        help='Number of the door in the controller',
        required=True,
        index=True,
    )

    card_type = fields.Many2one(
        'hr.rfid.card.type',
        string='Card type',
        help='Only cards of this type this door will open to',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_card_type_def').id,
        ondelete='set null',
        tracking=True,
    )

    apb_mode = fields.Boolean(
        string='APB Mode',
        default=False,
        tracking=True,
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the door',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    access_group_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'door_id',
        string='Door Access Groups',
        help='The access groups this door is a part of',
    )

    user_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'door_id',
        string='Events',
        help='Events concerning this door',
    )

    reader_ids = fields.Many2many(
        'hr.rfid.reader',
        'hr_rfid_reader_door_rel',
        'door_id',
        'reader_id',
        string='Readers',
        help='Readers that open this door',
    )

    card_rel_ids = fields.One2many(
        'hr.rfid.card.door.rel',
        'door_id',
        string='Cards',
        help='Cards that have access to this door',
    )

    zone_ids = fields.Many2many(
        'hr.rfid.zone',
        'hr_rfid_zone_door_rel',
        'door_id',
        'zone_id',
        string='Zones',
        help='Zones containing this door',
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        related='controller_id.webstack_id',
    )

    hb_dnd = fields.Boolean(
        string='DND button pressed',
        compute='_compute_hotel_buttons',
        inverse='_set_hb_dnd'
    )
    hb_clean = fields.Boolean(
        string='Clean button pressed',
        compute='_compute_hotel_buttons',
        inverse='_set_hb_clean'
    )
    hb_card_present = fields.Boolean(
        string='Present card in reader',
        compute='_compute_hotel_buttons'
    )

    access_group_count = fields.Char(compute='_compute_counts')
    user_event_count = fields.Char(compute='_compute_counts')
    reader_count = fields.Char(compute='_compute_counts')
    card_count = fields.Char(compute='_compute_counts')
    zone_count = fields.Char(compute='_compute_counts')

    @api.depends('controller_id.hotel_readers_buttons_pressed', 'controller_id.hotel_readers_card_presence')
    def _compute_hotel_buttons(self):
        for d in self:
            d.hb_dnd = (d.controller_id.hotel_readers_buttons_pressed & 0b001) == 1
            d.hb_clean = (d.controller_id.hotel_readers_buttons_pressed & 0b010) == 2
            readers_bits = [int(pow(2, i.number - 1)) for i in d.reader_ids]
            d.hb_card_present = any(
                [(d.controller_id.hotel_readers_card_presence & bits) == bits for bits in readers_bits])

    def _set_hb_dnd(self):
        for d in self:
            d.open_close_door(int(d.hb_dnd), 99, 20)
            if d.hb_dnd:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed | 1
            else:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed - 1

    def _set_hb_clean(self):
        for d in self:
            d.open_close_door(int(d.hb_clean), 99, 21)
            if d.hb_clean:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed | 2
            else:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed - 2

    def proccess_event(self, event):
        self.ensure_one()
        if isinstance(event, HrRfidUserEvent):
            if event.more_json:
                j = json.loads(event.more_json)
                if 'state' in j.keys():
                    if j["state"]:
                        self.controller_id.hotel_readers_buttons_pressed = self.controller_id.hotel_readers_buttons_pressed | event.reader_id.number
                    else:
                        self.controller_id.hotel_readers_buttons_pressed = self.controller_id.hotel_readers_buttons_pressed ^ event.reader_id.number
            elif event.event_action == '7':
                self.controller_id.hotel_readers_card_presence = self.controller_id.hotel_readers_card_presence | event.reader_id.number
            elif event.event_action == '9':
                self.controller_id.hotel_readers_card_presence = self.controller_id.hotel_readers_card_presence ^ event.reader_id.number

        elif isinstance(event, HrRfidSystemEvent):
            pass

    def _compute_counts(self):
        for r in self:
            r.access_group_count = len(r.access_group_ids)
            r.user_event_count = len(r.user_event_ids)
            r.reader_count = len(r.reader_ids)
            r.card_count = len(r.card_rel_ids)
            r.zone_count = len(r.zone_ids)

    def get_potential_cards(self, access_groups=None):
        """
        Returns a list of tuples (card, time_schedule) for which the card potentially has access to this door
        """
        if access_groups is None:
            acc_gr_rels = self.access_group_ids
        else:
            acc_gr_rels = self.env['hr.rfid.access.group.door.rel'].search([
                ('id', 'in', self.access_group_ids.ids),
                ('access_group_id', 'in', access_groups.ids),
            ])
        ret = []
        for rel in acc_gr_rels:
            ts_id = rel.time_schedule_id
            acc_gr = rel.access_group_id
            employees = acc_gr.mapped('all_employee_ids').mapped('employee_id')
            contacts = acc_gr.mapped('all_contact_ids').mapped('contact_id')
            cards = employees.mapped('hr_rfid_card_ids') + contacts.mapped('hr_rfid_card_ids')
            for card in cards:
                ret.append((card, ts_id))
        return ret

    def open_door(self):
        self.ensure_one()
        return self.open_close_door(1, 3)

    def close_door(self):
        self.ensure_one()
        return self.open_close_door(0, 3)

    def open_close_door(self, out: int, time: int, custom_out = None):
        self.ensure_one()

        if self.controller_id.webstack_id.behind_nat is True:
            return self.create_door_out_cmd(out, time)
        else:
            return self.change_door_out(out, time, custom_out)

    def create_door_out_cmd(self, out: int, time: int):
        self.ensure_one()
        cmd_env = self.env['hr.rfid.command']
        ctrl = self.controller_id
        cmd_dict = {
            'webstack_id': ctrl.webstack_id.id,
            'controller_id': ctrl.id,
            'cmd': 'DB',
        }
        if not ctrl.is_relay_ctrl():
            cmd_dict['cmd_data'] = '%02d%02d%02d' % (self.number, out, time)
        else:
            if out == 0:
                return create_and_ret_d_box(self.env, _('Cannot close a relay door.'),
                                            _('Relay doors cannot be closed.'))
            cmd_dict['cmd_data'] = ('1F%02X' % self.reader_ids[0].number) + self.create_rights_data()

        cmd_env.create([cmd_dict])
        self.log_door_change(out, time, cmd=True)
        return create_and_ret_d_box(
            self.env,
            _('Command creation successful'),
            _(
                'Because the webstack is behind NAT, we have to wait for the webstack to call us, so we created a command. The door will open/close as soon as possible.')
        )

    def create_rights_data(self):
        self.ensure_one()
        ctrl = self.controller_id
        if not ctrl.is_relay_ctrl():
            data = 1 << (self.reader_ids.number - 1)
        else:
            if ctrl.mode == 1:
                data = 1 << (self.number - 1)
            elif ctrl.mode == 2:
                data = 1 << (self.number - 1)
                if self.reader_ids.number == 2:
                    data *= 0x10000
            elif ctrl.mode == 3:
                data = self.number
            else:
                raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                                 % (ctrl.name, ctrl.mode))

        return self.create_rights_int_to_str(data)

    def create_rights_int_to_str(self, data):
        ctrl = self.controller_id
        if not ctrl.is_relay_ctrl():
            cmd_data = '{:02X}'.format(data)
        else:
            cmd_data = '%03d%03d%03d%03d' % (
                (data >> (3 * 8)) & 0xFF,
                (data >> (2 * 8)) & 0xFF,
                (data >> (1 * 8)) & 0xFF,
                (data >> (0 * 8)) & 0xFF,
            )
            cmd_data = ''.join(list('0' + ch for ch in cmd_data))
        return cmd_data

    def change_door_out(self, out: int, time: int, custom_out: bool):
        """
        :param out: 0 to open door, 1 to close door
        :param time: Range: [0, 99]
        """
        self.ensure_one()
        self.log_door_change(out, time)

        ws = self.controller_id.webstack_id
        if ws.module_username is False:
            username = ''
        else:
            username = str(ws.module_username)

        if ws.module_password is False:
            password = ''
        else:
            password = str(ws.module_password)

        auth = base64.b64encode((username + ':' + password).encode())
        auth = auth.decode()
        headers = {'content-type': 'application/json', 'Authorization': 'Basic ' + str(auth)}
        cmd = {
            'cmd': {
                'id': self.controller_id.ctrl_id,
                'c': 'DB',
            }
        }

        if self.controller_id.is_relay_ctrl():
            if out == 0:
                return create_and_ret_d_box(self.env, _('Cannot close a relay door.'),
                                            _('Relay doors cannot be closed.'))
            cmd['cmd']['d'] = ('1F%02X' % self.reader_ids[0].number) + self.create_rights_data()
        else:
            cmd['cmd']['d'] = '%02x%02d%02d' % (custom_out or self.number, out, time)

        # cmd = json.dumps(cmd)

        host = str(ws.last_ip)
        try:
            # conn = http.client.HTTPConnection(str(host), 80, timeout=2)
            # conn.request('POST', '/sdk/cmd.json', cmd, headers)
            response = requests.post('http://' + ws.last_ip + '/sdk/cmd.json', auth=(username, password), json=cmd,
                                     timeout=2)
            # response = conn.getresponse()
            code = response.status_code
            body_js = response.json()
            # conn.close()
            if code != 200:
                raise exceptions.ValidationError('While trying to send the command to the module, '
                                                 'it returned code ' + str(code) + ' with body:\n'
                                                 + response.content.decode())

            # body_js = json.loads(body.decode())
            if body_js['response']['e'] != 0:
                raise exceptions.ValidationError('Error. Controller returned body:\n' + str(response.content.decode()))
        except socket.timeout:
            raise exceptions.ValidationError('Could not connect to the module. '
                                             "Check if it is turned on or if it's on a different ip.")
        except (socket.error, socket.gaierror, socket.herror) as e:
            raise exceptions.ValidationError('Error while trying to connect to the module.'
                                             ' Information:\n' + str(e))

        return create_and_ret_d_box(self.env, _('Door successfully opened/closed'),
                                    _('Door will remain opened/closed for %d seconds.') % time)

    def log_door_change(self, action: int, time: int, cmd: bool = False):
        """
        :param action: 1 for door open, 0 for door close
        :param time: Range: [0, 99]
        :param cmd: If the command was created instead of
        """
        self.ensure_one()
        if time > 0:
            if cmd is False:
                if action == 1:
                    self.message_post(body=_('Opened the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Closed the door for %d seconds.') % time)
            else:
                if action == 1:
                    self.message_post(body=_('Created a command to open the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Created a command to close the door for %d seconds.') % time)
        else:
            if cmd is False:
                if action == 1:
                    self.message_post(body=_('Opened the door.') % time)
                else:
                    self.message_post(body=_('Closed the door.') % time)
            else:
                if action == 1:
                    self.message_post(body=_('Created a command to open the door.') % time)
                else:
                    self.message_post(body=_('Created a command to close the door.') % time)

    @api.constrains('apb_mode')
    def _check_apb_mode(self):
        for door in self:
            if door.apb_mode is True and len(door.reader_ids) < 2:
                raise exceptions.ValidationError('Cannot activate APB Mode for a door if it has less than 2 readers')

    def write(self, vals):
        cmd_env = self.env['hr.rfid.command']
        rel_env = self.env['hr.rfid.card.door.rel']
        for door in self:
            old_card_type = door.card_type
            old_apb_mode = door.apb_mode

            super(HrRfidDoor, door).write(vals)

            if old_card_type != door.card_type:
                rel_env.update_door_rels(door)

            if old_apb_mode != door.apb_mode:
                cmd_data = 0
                for door2 in door.controller_id.door_ids:
                    if door2.apb_mode and len(door2.reader_ids) > 1:
                        cmd_data += door2.number
                cmd_dict = {
                    'webstack_id': door.controller_id.webstack_id.id,
                    'controller_id': door.controller_id.id,
                    'cmd': 'DE',
                    'cmd_data': '%02d' % cmd_data,
                }
                cmd_env.create(cmd_dict)

        return True

    def button_act_window(self):
        self.ensure_one()
        res_model = self.env.context.get('res_model') or self._name
        if res_model == 'hr.rfid.access.group':
            name = _('Access groups with {}').format(self.name)
            domain = [('door_ids', 'in', self.id)]
        elif res_model == 'hr.rfid.event.user':
            name = _('User Events on {}').format(self.name)
            domain = [('door_id', 'in', [self.id])]
        elif res_model == 'hr.rfid.reader':
            name = _('Readers for {}').format(self.name)
            domain = [('door_ids', 'in', self.id)]
        elif res_model == 'hr.rfid.card':
            name = _('Cards for {}').format(self.name)
            domain = [('id', 'in', [rel.card_id.id for rel in self.card_rel_ids])]
        elif res_model == 'hr.rfid.zone':
            name = _('{} in zones').format(self.name)
            domain = [('id', 'in', [rel.zone_id.id for rel in self.zone_ids])]
        return {
            'name': name,
            'view_mode': 'tree,form',
            'res_model': res_model,
            'domain': domain,
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         No events for this employee.
            #     </p>'''),
        }


class HrRfidDoorOpenCloseWiz(models.TransientModel):
    _name = 'hr.rfid.door.open.close.wiz'
    _description = 'Open or close door'

    def _default_doors(self):
        return self.env['hr.rfid.door'].browse(self._context.get('active_ids'))

    doors = fields.Many2many(
        'hr.rfid.door',
        string='Doors to open/close',
        required=True,
        default=_default_doors,
    )

    time = fields.Integer(
        string='Time',
        help='Amount of time (in seconds) the doors will stay open or closed. 0 for infinity.',
        default=3,
        required=True,
    )

    def open_doors(self):
        for door in self.doors:
            door.open_close_door(out=1, time=self.time)
        return create_and_ret_d_box(self.env, 'Doors opened', 'Doors successfully opened')

    def close_doors(self):
        for door in self.doors:
            door.open_close_door(out=0, time=self.time)
        return create_and_ret_d_box(self.env, 'Door closed', 'Doors successfully closed')


class HrRfidCardDoorRel(models.Model):
    _name = 'hr.rfid.card.door.rel'
    _description = 'Card and door relation model'

    card_id = fields.Many2one(
        'hr.rfid.card',
        string='Card',
        required=True,
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        required=True,
        ondelete='cascade',
    )

    time_schedule_id = fields.Many2one(
        'hr.rfid.time.schedule',
        string='Time Schedule',
        required=True,
        ondelete='cascade',
    )

    @api.model
    def update_card_rels(self, card_id: HrRfidCard, access_group: models.Model = None):
        """
         Checks all card-door relations and updates them
         :param card_id: Card for which the relations to be checked
         :param access_group: Which access groups to go through when searching for the doors. If None will
         go through all access groups the owner of the card is in
         """
        potential_doors = card_id.get_potential_access_doors(access_group)
        for door, ts in potential_doors:
            self.check_relevance_fast(card_id, door, ts)

    @api.model
    def update_door_rels(self, door_id: models.Model, access_group: models.Model = None):
        """
        Checks all card-door relations and updates them
        :param door_id: Door for which the relations to be checked
        :param access_group: Which access groups to go through when searching for the cards. If None will
        go through all the access groups the door is in
        """
        potential_cards = door_id.get_potential_cards(access_group)
        for card, ts in potential_cards:
            self.check_relevance_fast(card, door_id, ts)

    @api.model
    def reload_door_rels(self, door_id: models.Model):
        door_id.card_rel_ids.unlink(create_cmd=False)
        self.update_door_rels(door_id)

    @api.model
    def check_relevance_slow(self, card_id: HrRfidCard, door_id: models.Model, ts_id: models.Model = None):
        """
        Check if card has access to door. If it does, create relation or do nothing if it exists,
        and if not remove relation or do nothing if it does not exist.
        :param card_id: Recordset containing a single card
        :param door_id: Recordset containing a single door
        :param ts_id: Optional parameter. If supplied, the relation will be created quicker.
        """
        card_id.ensure_one()
        door_id.ensure_one()

        if not card_id.card_ready():
            return

        potential_doors = card_id.get_potential_access_doors()
        found_door = False

        for door, ts in potential_doors:
            if door_id == door:
                if ts_id is not None and ts_id != ts:
                    raise exceptions.ValidationError(
                        'This should never happen. Please contact the developers. 95328359')
                ts_id = ts
                found_door = True
                break
        if found_door and self._check_compat_n_rdy(card_id, door_id):
            self.create_rel(card_id, door_id, ts_id)
        else:
            self.remove_rel(card_id, door_id)

    @api.model
    def check_relevance_fast(self, card_id: HrRfidCard, door_id: models.Model, ts_id: models.Model = None):
        """
        Check if card is compatible with the door. If it is, create relation or do nothing if it exists,
        and if not remove relation or do nothing if it does not exist.
        :param card_id: Recordset containing a single card
        :param door_id: Recordset containing a single door
        :param ts_id: Optional parameter. If supplied, the relation will be created quicker.
        """
        card_id.ensure_one()
        door_id.ensure_one()
        if self._check_compat_n_rdy(card_id, door_id):
            self.create_rel(card_id, door_id, ts_id)
        else:
            self.remove_rel(card_id, door_id)

    @api.model
    def create_rel(self, card_id: HrRfidCard, door_id: models.Model, ts_id: models.Model = None):
        ret = self.search([
            ('card_id', '=', card_id.id),
            ('door_id', '=', door_id.id),
        ])
        if len(ret) == 0 and self._check_compat_n_rdy(card_id, door_id):
            if ts_id is None:
                acc_grs = card_id.get_owner().mapped('hr_rfid_access_group_ids').mapped('access_group_id')
                door_rels = acc_grs.mapped('all_door_ids')
                door_rel = None
                for rel in door_rels:
                    if rel.door_id == door_id:
                        door_rel = rel
                        break
                if door_rel is None:
                    raise exceptions.ValidationError('No way this card has access to this door??? 17512849')
                ts_id = door_rel.time_schedule_id

            self.create([{
                'card_id': card_id.id,
                'door_id': door_id.id,
                'time_schedule_id': ts_id.id,
            }])

    @api.model
    def remove_rel(self, card_id: models.Model, door_id: models.Model):
        ret = self.search([
            ('card_id', '=', card_id.id),
            ('door_id', '=', door_id.id),
        ])
        if len(ret) > 0:
            ret.unlink()

    def check_rel_relevance(self):
        for rel in self:
            self.check_relevance_slow(rel.card_id, rel.door_id)

    def time_schedule_changed(self, new_ts):
        self.time_schedule_id = new_ts

    def pin_code_changed(self):
        self._create_add_card_command()

    def card_number_changed(self, old_number):
        for rel in self:
            if old_number != rel.card_id.number:
                rel._create_remove_card_command(old_number)
                rel._create_add_card_command()

    def reload_add_card_command(self):
        self._create_add_card_command()

    @api.model
    def _check_compat_n_rdy(self, card_id, door_id):
        return card_id.door_compatible(door_id) and card_id.card_ready()

    def _create_add_card_command(self):
        cmd_env = self.env['hr.rfid.command']
        for rel in self:
            door_id = rel.door_id.id
            ts_id = rel.time_schedule_id.id
            pin_code = rel.card_id.pin_code
            card_id = rel.card_id.id
            cmd_env.add_card(door_id, ts_id, pin_code, card_id)

    def _create_remove_card_command(self, number: str = None, door_id: int = None):
        cmd_env = self.env['hr.rfid.command']
        for rel in self:
            if door_id is None:
                door_id = rel.door_id.id
            if number is None:
                number = rel.card_id.number[:]
            pin_code = rel.card_id.pin_code
            cmd_env.remove_card(door_id, pin_code, card_number=number)

    @api.constrains('door_id')
    def _door_constrains(self):
        for rel in self:
            if len(rel.door_id.access_group_ids) == 0:
                raise exceptions.ValidationError('Door must be part of an access group!')

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = self.env['hr.rfid.card.door.rel']

        for vals in vals_list:
            rel = super(HrRfidCardDoorRel, self).create([vals])
            records += rel
            rel.with_user(SUPERUSER_ID)._create_add_card_command()

        return records

    def write(self, vals):
        for rel in self.with_user(SUPERUSER_ID):
            old_door = rel.door_id
            old_card = rel.card_id
            old_ts_id = rel.time_schedule_id

            super(HrRfidCardDoorRel, rel).write(vals)

            new_door = rel.door_id
            new_card = rel.card_id
            new_ts_id = rel.time_schedule_id

            if old_door != new_door or old_card != new_card:
                rel._create_remove_card_command(number=old_card.number, door_id=old_door.id)
                rel._create_add_card_command()
            elif old_ts_id != new_ts_id:
                rel._create_add_card_command()

    def unlink(self, create_cmd=True):
        if create_cmd:
            for rel in self:
                rel.with_user(SUPERUSER_ID)._create_remove_card_command()

        return super(HrRfidCardDoorRel, self).unlink()
