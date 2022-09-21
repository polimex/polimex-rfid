import base64
import socket

import requests

from odoo import fields, models, api, _, exceptions, SUPERUSER_ID
import http.client
import json

from odoo.addons.hr_rfid.models.hr_rfid_card import HrRfidCard
from odoo.addons.hr_rfid.models.hr_rfid_event_system import HrRfidSystemEvent
from odoo.addons.hr_rfid.models.hr_rfid_event_user import HrRfidUserEvent


class HrRfidDoor(models.Model):
    _name = 'hr.rfid.door'
    _description = 'Door'
    _inherit = ['mail.thread', 'balloon.mixin']
    _order = "controller_id,number"

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
        tracking=True
    )

    card_type = fields.Many2one(
        comodel_name='hr.rfid.card.type',
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
        comodel_name='hr.rfid.ctrl',
        string='Controller',
        help='Controller that manages the door',
        required=True,
        readonly=True,
        ondelete='cascade',
        tracking=True
    )

    hotel_readers = fields.Integer(related='controller_id.hotel_readers')

    access_group_ids = fields.One2many(
        comodel_name='hr.rfid.access.group.door.rel',
        inverse_name='door_id',
        string='Door Access Groups',
        help='The access groups this door is a part of',
    )

    reader_ids = fields.Many2many(
        comodel_name='hr.rfid.reader',
        relation='hr_rfid_reader_door_rel',
        column1='door_id',
        column2='reader_id',
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

    lock_time = fields.Integer(
        help='The unlock time in seconds.',
        compute='_compute_lock_time',
        inverse='_set_lock_time',
        tracking = True
    )
    lock_state = fields.Boolean(
        help='If in the controller check box for read state is True, the status is present.',
        compute='_compute_lock_status',
        inverse='_set_lock_state',
        tracking = True
    )
    lock_output = fields.Integer(
        help='The Lock Output on controller for this door',
        compute='_compute_lock_output'
    )
    alarm_line_ids = fields.One2many(
        comodel_name='hr.rfid.ctrl.alarm',
        inverse_name='door_id',
        # auto_join=True,
        help='Alarm lines connected to this door'
    )
    alarm_state = fields.Selection([
        ('no_alarm', 'No Alarm functionality'),
        ('arm', 'Armed'),
        ('disarm', 'Disarmed'),
    ],
        compute='_compute_alarm_state',
    )
    siren_state = fields.Boolean(
        related='controller_id.siren_state'
    )
    emergency_state = fields.Selection(
        related='controller_id.emergency_state'
    )
    th_id = fields.One2many(
        comodel_name='hr.rfid.ctrl.th',
        inverse_name='door_id'
    )
    temperature = fields.Float(
        related='th_id.temperature'
    )
    humidity = fields.Float(
        related='th_id.humidity'
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
    reader_count = fields.Char(compute='_compute_counts')
    card_count = fields.Char(compute='_compute_counts')
    zone_count = fields.Char(compute='_compute_counts')
    alarm_lines_count = fields.Char(compute='_compute_counts')
    user_event_count = fields.Char(compute='_compute_counts')
    system_event_count = fields.Char(compute='_compute_counts')

    @api.constrains('apb_mode')
    def _check_apb_mode(self):
        for door in self:
            if door.apb_mode is True and len(door.reader_ids) < 2:
                raise exceptions.ValidationError('Cannot activate APB Mode for a door if it has less than 2 readers')

    @api.depends('access_group_ids', 'reader_ids', 'card_rel_ids', 'zone_ids', 'alarm_line_ids')
    def _compute_counts(self):
        for r in self:
            r.access_group_count = len(r.access_group_ids)
            r.reader_count = len(r.reader_ids)
            r.card_count = len(r.card_rel_ids)
            r.zone_count = len(r.zone_ids)
            r.alarm_lines_count = len(r.alarm_line_ids)
            r.user_event_count = self.env['hr.rfid.event.user'].search_count([('door_id', '=', r.id)])
            r.system_event_count = self.env['hr.rfid.event.system'].search_count([('door_id', '=', r.id)])

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
            d.controller_id.change_output_state(20, int(d.hb_dnd), 99)
            if d.hb_dnd:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed | 1
            else:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed - 1

    def _set_hb_clean(self):
        for d in self:
            d.controller_id.change_output_state(21, int(d.hb_dnd), 99)
            if d.hb_clean:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed | 2
            else:
                d.controller_id.hotel_readers_buttons_pressed = d.controller_id.hotel_readers_buttons_pressed - 2

    @api.depends('alarm_line_ids.armed')
    def _compute_alarm_state(self):
        for d in self:
            if d.alarm_line_ids:
                d.alarm_state = d.alarm_line_ids[0].armed
            else:
                d.alarm_state = 'no_alarm'

    @api.depends('controller_id.io_table')
    def _compute_lock_time(self):
        for d in self:
            io_line = None
            if d.reader_ids:
                io_line = d._get_io_line(1, d.reader_ids[0].number)
            if io_line:
                d.lock_time = io_line[0][1]
            else:
                d.lock_time = 0

    def _set_lock_time(self):
        for d in self:
            for r in d.reader_ids:
                io_line = d._get_io_line(1, r.number)
                io_line = [(i[0], d.lock_time) for i in io_line]
                d._set_io_line(1, io_line, r.number)

    @api.depends('reader_ids')
    def _compute_lock_output(self):
        for d in self:
            if d.controller_id.is_relay_ctrl():
                d.lock_output = d.number
            else:
                io_line = None
                if d.reader_ids:
                    io_line = d._get_io_line(1, d.reader_ids[0].number)
                if io_line:
                    d.lock_output = io_line[0][0]
                else:
                    d.lock_output = 0

    @api.depends('controller_id.outputs')
    def _compute_lock_status(self):
        for d in self:
            if d.lock_output > 0:
                d.lock_state = (d.controller_id.output_states & 2 ** (d.lock_output - 1)) == 2 ** (d.lock_output - 1)
            else:
                d.lock_state = False

    def _set_lock_state(self):
        for d in self:
            d.controller_id.change_output_state(self.lock_output, int(d.lock_state), 99)

    def _get_io_line(self, event: int, reader_number: int):
        '''
        Read IO line based on reader events 1,2,3,4 (Card OK, Card Error, Card TS Error, Card APB Error)
        Return:
            Array of tuple (out number, time)
        '''
        self.ensure_one()
        line_number = 3 + (reader_number - 1) * 4 + (event - 1)
        line = self.controller_id._get_io_line(line_number)
        out_time = []
        for i in range(8):
            if line and line[i] > 0:
                out_time.append((i + 1, line[i]))
        return out_time

    def _set_io_line(self, event: int, outs: [tuple], reader_number: int):
        '''
        Write IO Line based on reader event and array of tuple (out number, time)
        '''
        self.ensure_one()
        line_number = 3 + (reader_number - 1) * 4 + (event - 1)
        line = self.controller_id._get_io_line(line_number)
        for o in outs:
            line[o[0] - 1] = o[1]
        self.controller_id._set_io_line(line_number, line)

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
            alarm_right = rel.alarm_rights
            employees = acc_gr.mapped('all_employee_ids').mapped('employee_id')
            contacts = acc_gr.mapped('all_contact_ids').mapped('contact_id')
            cards = employees.mapped('hr_rfid_card_ids') + contacts.mapped('hr_rfid_card_ids')
            for card in cards:
                ret.append((card, ts_id, alarm_right))
        return ret

    def open_door(self):
        self.ensure_one()
        cmd_id = self.controller_id.change_output_state(self.lock_output, 1, self.lock_time)
        self.log_door_change(1, self.lock_time, cmd_id)
        if self.controller_id.webstack_id.behind_nat:
            return self.balloon_warning_sticky(
                title=_('Open door command success'),
                message=_('Because the webstack is behind NAT, we have to wait for the webstack to call us, '
                          'so we created a command. The door will open/close as soon as possible.'),
                links=cmd_id and [{
                    'label': cmd_id.name,
                    'model': 'hr.rfid.command',
                    'res_id': cmd_id.id,
                    'action': 'hr_rfid.hr_rfid_command_action'
                }] or None
            )
        else:
            return self.balloon_success(
                title=_('Open door command success'),
                message=_('Success opening')
            )

    def close_door(self):
        self.ensure_one()
        cmd_id = self.controller_id.change_output_state(self.lock_output, 0, self.lock_time)
        self.log_door_change(0, self.lock_time, cmd_id)
        if self.controller_id.webstack_id.behind_nat:
            return self.balloon_warning_sticky(
                title=_('Close door command success'),
                message=_('Because the webstack is behind NAT, we have to wait for the webstack to call us, '
                          'so we created a command. The door will open/close as soon as possible.'),
                links=[{
                    'label': cmd_id.name,
                    'model': 'hr.rfid.command',
                    'res_id': cmd_id.id,
                    'action': 'hr_rfid.hr_rfid_command_action'
                }]
            )
        else:
            return self.balloon_success(
                title=_('Close door command success'),
                message=_('Closing success')
            )

    def arm_door(self):
        return self.with_user(SUPERUSER_ID).alarm_line_ids.arm()

    def disarm_door(self):
        return self.with_user(SUPERUSER_ID).alarm_line_ids.disarm()

    def siren_off(self):
        for s in self.with_user(SUPERUSER_ID):
            s.controller_id.siren_state = False
        return self.balloon_success(
            title=_('Siren Control'),
            message=_('Siren turned Off successful')
        )

    def siren_on(self):
        for s in self.with_user(SUPERUSER_ID):
            s.controller_id.siren_state = True
        return self.balloon_success(
            title=_('Siren Control'),
            message=_('Siren turned On successful')
        )

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
                    self.message_post(body=_('Opened the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Closed the door for %d seconds.') % time)
            else:
                if action == 1:
                    self.message_post(body=_('Created a command to open the door for %d seconds.') % time)
                else:
                    self.message_post(body=_('Created a command to close the door for %d seconds.') % time)

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
        view_mode = None
        res_model = self.env.context.get('res_model') or self._name
        if res_model == 'hr.rfid.access.group':
            name = _('Access groups with {}').format(self.name)
            domain = [('door_ids.door_id', '=', self.id)]
        elif res_model == 'hr.rfid.event.user':
            name = _('User Events on {}').format(self.name)
            domain = [('door_id', 'in', [self.id])]
        elif res_model == 'hr.rfid.event.system':
            name = _('System Events on {}').format(self.name)
            domain = [('door_id', 'in', [self.id])]
        elif res_model == 'hr.rfid.reader':
            name = _('Readers for {}').format(self.name)
            domain = [('door_ids', 'in', self.id)]
        elif res_model == 'hr.rfid.card':
            name = _('Cards for {}').format(self.name)
            domain = [('id', 'in', [rel.card_id.id for rel in self.card_rel_ids])]
        elif res_model == 'hr.rfid.zone':
            name = _('{} in zones').format(self.name)
            domain = [('door_id', 'in', [rel.zone_id.id for rel in self.zone_ids])]
        elif res_model == 'hr.rfid.ctrl.alarm':
            name = _('Alarm lines for {}').format(self.name)
            domain = [('door_id', 'in', [rel.door_id.id for rel in self.alarm_line_ids])]
        elif res_model == 'hr.rfid.ctrl.th.log':
            name = _('Temperature and Humidity Log for {}').format(self.name)
            domain = [('th_id', '=', self.th_id.id)]
            view_mode = 'graph,pivot,tree'
        return {
            'name': name,
            'view_mode': view_mode or 'tree,form',
            'res_model': res_model,
            'domain': domain,
            'type': 'ir.actions.act_window',
        }

    # Door commands
    def add_card(self, ts_id, pin_code, card_id):
        for door in self:
            time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)
            card = self.env['hr.rfid.card'].browse(card_id)
            card_number = card.number

            if door.controller_id.is_relay_ctrl():
                return door.controller_id._add_card_to_relay(door.id, card_id)

            for reader in door.reader_ids:
                ts_code = [0, 0, 0, 0]
                ts_code[reader.number - 1] = time_schedule.number
                ts_code = '%02X%02X%02X%02X' % (ts_code[0], ts_code[1], ts_code[2], ts_code[3])
                door.controller_id.add_remove_card(
                    card_number, pin_code, ts_code,
                    rights_data=1 << (reader.number - 1),
                    rights_mask=1 << (reader.number - 1),

                )

    def _add_card_to_relay(self, card_id):
        for door in self:
            card = self.env['hr.rfid.card'].browse(card_id)
            ctrl = door.controller_id

            if ctrl.mode == 1:
                rdata = 1 << (door.number - 1)
                rmask = rdata
            elif ctrl.mode == 2:
                rdata = 1 << (door.number - 1)
                if door.reader_ids.number == 2:
                    rdata *= 0x10000
                rmask = rdata
            elif ctrl.mode == 3:
                rdata = door.number
                rmask = -1
            else:
                raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                                 % (ctrl.name, ctrl.mode))
            ctrl._add_remove_card_relay(card.number, rdata, rmask)

    def remove_card(self, pin_code, card_number=None, card_id=None):
        for door in self:
            if card_id is not None:
                card = self.env['hr.rfid.card'].browse(card_id)
                card_number = card.number

            if door.controller_id.is_relay_ctrl():
                return door._remove_card_from_relay(card_number)

            for reader in door.reader_ids:
                door.controller_id.add_remove_card(card_number, pin_code, '00000000',
                                                   0, 1 << (reader.number - 1))

    def _remove_card_from_relay(self, card_number):
        for door in self:
            if door.controller_id.mode == 1:
                rmask = 1 << (door.number - 1)
            elif door.controller_id.mode == 2:
                rmask = 1 << (door.number - 1)
                if door.reader_ids.number == 2:
                    rmask *= 0x10000
            elif door.controller_id.mode == 3:
                rmask = -1
            else:
                raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                                 % (door.controller_id.name, door.controller_id.mode))

            door.controller_id._add_remove_card_relay(card_number, 0, rmask)

    def change_apb_flag(self, card, can_exit=True):
        for door in self:
            if door.number == 1:
                rights = 0x40  # Bit 7
            else:
                rights = 0x20  # Bit 6
            door.controller_id.add_remove_card(card.number, card.get_owner().hr_rfid_pin_code,
                                               '00000000', rights if can_exit else 0, rights)


class HrRfidDoorOpenCloseWiz(models.TransientModel):
    _name = 'hr.rfid.door.open.close.wiz'
    _inherit = ['balloon.mixin']
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
            door.controller_id.change_output_state(door.lock_output, 1, time=self.time)
        return self.balloon_success(
            title=_('Doors opened'),
            message=_('Doors successfully opened')
        )

    def close_doors(self):
        for door in self.doors:
            door.controller_id.change_output_state(door.lock_output, 0, time=self.time)
        return self.balloon_success(
            title=_('Doors closed'),
            message=_('Doors successfully closed')
        )


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
    alarm_right = fields.Boolean(
        required=True,
        default=False
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
        for door, ts, alarm_right in potential_doors:
            self.check_relevance_fast(card_id, door, ts, alarm_right)

    @api.model
    def update_door_rels(self, door_id: models.Model, access_group: models.Model = None):
        """
        Checks all card-door relations and updates them
        :param door_id: Door for which the relations to be checked
        :param access_group: Which access groups to go through when searching for the cards. If None will
        go through all the access groups the door is in
        """
        potential_cards = door_id.get_potential_cards(access_group)
        for card, ts, alarm_right in potential_cards:
            self.check_relevance_fast(card, door_id, ts, alarm_right)

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

        for door, ts, alarm_right in potential_doors:
            if door_id == door:
                if ts_id and ts_id != ts:
                    raise exceptions.ValidationError(
                        'This should never happen. Please contact the developers. (%s != %s)' % (str(ts_id), str(ts))
                    )
                ts_id = ts
                found_door = True
                break
        if found_door and self._check_compat_n_rdy(card_id, door_id):
            self.create_rel(card_id, door_id, ts_id, alarm_right)
        else:
            self.remove_rel(card_id, door_id)

    @api.model
    def check_relevance_fast(self, card_id: HrRfidCard, door_id: models.Model, ts_id: models.Model = None,
                             alarm_right: bool = False):
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
            self.create_rel(card_id, door_id, ts_id, alarm_right)
        else:
            self.remove_rel(card_id, door_id)

    @api.model
    def create_rel(self, card_id: HrRfidCard, door_id: models.Model, ts_id: models.Model = None,
                   alarm_right: bool = False):
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
                'alarm_right': alarm_right,
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
            alarm_right = rel.alarm_right
            cmd_env.add_card(door_id, ts_id, pin_code, card_id, alarm_right)

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
