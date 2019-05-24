# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions
import logging
import queue

_logger = logging.getLogger(__name__)


class HrRfidAccessGroup(models.Model):
    _name = 'hr.rfid.access.group'
    _inherit = ['mail.thread']
    _description = 'Access Group'

    def access_group_generate_name(self):
        env = self.env['hr.rfid.access.group'].search([])

        if len(env) == 0:
            return 'Access Group 1'
        else:
            return 'Access Group ' + str(env[-1].id + 1)

    name = fields.Char(
        string='Name',
        help='A label to help differentiate between access groups',
        default=access_group_generate_name,
        limit=32,
        track_visibility='onchange',
    )

    user_ids = fields.One2many(
        'hr.employee',
        'hr_rfid_access_group_id',
        string='Users',
        help='Users part of this access group',
    )

    contact_ids = fields.One2many(
        'res.partner',
        'hr_rfid_access_group_id',
        string='Contacts',
        help='Contacts part of this access group'
    )

    door_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'access_group_id',
        string='Doors',
        help='Doors departments from this access group can open',
    )

    default_department_ids = fields.One2many(
        'hr.department',
        'hr_rfid_default_access_group',
        string='Department (Default)',
        help='Departments that have this access group as default',
    )

    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Departments assigned to this access group',
    )

    inherited_access_groups = fields.Many2many(
        comodel_name='hr.rfid.access.group',
        relation='access_group_inheritance',
        column1='inheritor',
        column2='inherited',
        string='Inherited access groups',
    )

    inheritor_access_groups = fields.Many2many(
        comodel_name='hr.rfid.access.group',
        relation='access_group_inheritance',
        column1='inherited',
        column2='inheritor',
        string='Inheritors',
        help='Access groups that have inherited this one',
    )

    all_door_ids = fields.Many2many(
        'hr.rfid.access.group.door.rel',
        string='All doors',
        help='All doors, including inherited ones',
        compute='_compute_all_doors',
        store=True,
    )

    @api.multi
    @api.constrains('door_ids')
    def _door_ids_constrains(self):
        for acc_gr in self:
            door_id_list = []
            for rel in acc_gr.door_ids:
                if rel.door_id.id in door_id_list:
                    raise exceptions.ValidationError('Cannot link access group to a door '
                                                     'it is already linked to.')
                door_id_list.append(rel.door_id.id)

    @api.depends('door_ids', 'inherited_access_groups')
    def _compute_all_doors(self):
        for acc_gr in self:
            door_ids = set()
            HrRfidAccessGroup._check_all_doors_rec(door_ids, [], acc_gr)
            acc_gr.all_door_ids = self.env['hr.rfid.access.group.door.rel'].browse(list(door_ids))

    @staticmethod
    def _check_all_doors_rec(door_ids: set, checked_ids: list, acc_gr):
        if acc_gr.id in checked_ids:
            return
        checked_ids.append(acc_gr.id)
        for door in acc_gr.door_ids:
            door_ids.add(door.id)
        for rec_gr in acc_gr.inherited_access_groups:
            HrRfidAccessGroup._check_all_doors_rec(door_ids, checked_ids, rec_gr)

    @api.one
    @api.constrains('inherited_access_groups')
    def _check_inherited_access_groups(self):
        env = self.env['hr.rfid.access.group']
        group_order = []
        ret = HrRfidAccessGroup._check_inherited_access_groups_rec(self, [], group_order)
        if ret is True:
            err = 'Circular reference found in the inherited access groups:'
            for acc_gr_id in group_order:
                acc_gr = env.browse(acc_gr_id)
                err += '\n-> '
                err += acc_gr.name
            raise exceptions.ValidationError(err)

    @staticmethod
    def _check_inherited_access_groups_rec(acc_gr, visited_groups: list, group_order: list, orig_id=None):
        group_order.append(acc_gr.id)
        if acc_gr.id == orig_id:
            return True
        if orig_id is None:
            orig_id = acc_gr.id

        if acc_gr.id in visited_groups:
            return False

        visited_groups.append(acc_gr.id)

        for inh_gr in acc_gr.inherited_access_groups:
            res = HrRfidAccessGroup._check_inherited_access_groups_rec(inh_gr, visited_groups,
                                                                       group_order, orig_id)
            if res is True:
                return True

        group_order.pop()
        return False

    @staticmethod
    def _create_door_command(acc_gr, door_rels, command):
        for user in acc_gr.user_ids:
            pin = user.hr_rfid_pin_code
            for card in user.hr_rfid_card_ids:
                for door_rel in door_rels:
                    door_id = door_rel.door_id.id
                    ts_id = door_rel.time_schedule_id.id
                    command(door_id, ts_id, pin, card_id=card.id)

    @staticmethod
    def _create_add_door_commands(acc_gr, door_rels):
        cmd_env = acc_gr.env['hr.rfid.command']
        HrRfidAccessGroup._create_door_command(acc_gr, door_rels, cmd_env.add_card)

    @staticmethod
    def _create_remove_door_commands(acc_gr, door_rels):
        cmd_env = acc_gr.env['hr.rfid.command']
        HrRfidAccessGroup._create_door_command(acc_gr, door_rels, cmd_env.remove_card)

    # NOTE No need for create method because we can't add users or contacts on creation anyway

    @api.multi
    def write(self, vals):
        for acc_gr in self:
            old_doors = self.all_door_ids

            super(HrRfidAccessGroup, acc_gr).write(vals)

            new_doors = self.all_door_ids

            added_doors = new_doors - old_doors
            removed_doors = old_doors - new_doors

            env = self.env['hr.rfid.access.group']
            completed_groups = [ ]
            acc_gr_to_complete = queue.Queue()
            acc_gr_to_complete.put(acc_gr.id)

            while not acc_gr_to_complete.empty():
                # inh_id = inheritor_id, inh = inheritor
                inh_id = acc_gr_to_complete.get()
                if inh_id in completed_groups:
                    continue
                completed_groups.append(inh_id)
                inh = env.browse(inh_id)
                HrRfidAccessGroup._create_add_door_commands(inh, added_doors)
                HrRfidAccessGroup._create_remove_door_commands(inh, removed_doors)

                for upper_inh in inh.inheritor_access_groups:
                    acc_gr_to_complete.put(upper_inh.id)

        return True

    # TODO Check if we actually need this unlink?
    @api.multi
    def unlink(self):
        for acc_gr in self:
            acc_gr.all_door_ids.unlink()

        return super(HrRfidAccessGroup, self).unlink()


class HrRfidAccessGroupDoorRel(models.Model):
    _name = 'hr.rfid.access.group.door.rel'

    def _get_cur_access_group_id(self):
        return self.env['hr.rfid.access.group'].browse(self._context.get('active_id'))

    def _get_cur_door_id(self):
        return self.env.context.get('door_id', None)

    access_group_id = fields.Many2one(
        'hr.rfid.access.group',
        string='Access Group',
        default=_get_cur_access_group_id,
        required=True,
    )

    door_id = fields.Many2one(
        'hr.rfid.door',
        string='Door',
        default=_get_cur_door_id,
        required=True,
        ondelete='cascade',
    )

    time_schedule_id = fields.Many2one(
        'hr.rfid.time.schedule',
        string='Time schedule',
        help='Time schedule for the door/access group combination',
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_time_schedule_0').id,
        required=True,
        ondelete='cascade',
    )

    @api.model
    def time_schedule_changed(self, rel_id):
        """
        Call after you change the time schedule
        :param rel_id: The id of the relation
        """
        rel = self.browse(rel_id)
        cmd_env = self.env['hr.rfid.command']

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)
        for contact in rel.access_group_id.contact_ids:
            for card in contact.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 contact.hr_rfid_pin_code, card_id=card.id)

    @api.model
    def door_changed(self, rel_id, prev_door_id):
        """
        Call after you change the door
        :param rel_id: The id of the relation
        :param prev_door_id: The id of the previous door
        """
        rel = self.browse(rel_id)
        prev_door = self.env['hr.rfid.door'].browse(prev_door_id)
        cmd_env = self.env['hr.rfid.command']

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.remove_card(prev_door.id, rel.time_schedule_id.id,
                                    user.hr_rfid_pin_code, card_id=card.id)
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id, user.hr_rfid_pin_code,
                                 card_id=card.id)
        for contact in rel.access_group_id.contact_ids:
            for card in contact.hr_rfid_card_ids:
                cmd_env.remove_card(prev_door.id, rel.time_schedule_id.id,
                                    contact.hr_rfid_pin_code, card_id=card.id)
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 contact.hr_rfid_pin_code, card_id=card.id)

    @api.model
    def access_group_changed(self, rel_id, prev_acc_gr_id):
        """
        Call after you change the access_group
        :param rel_id: The id of the access group
        :param prev_acc_gr_id: The id of the previous access group
        """
        rel = self.browse(rel_id)
        prev_acc_gr = self.env['hr.rfid.access.group'].browse(prev_acc_gr_id)
        cmd_env = self.env['hr.rfid.command']

        for user in prev_acc_gr.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)
        for contact in prev_acc_gr.contact_ids:
            for card in contact.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 contact.hr_rfid_pin_code, card_id=card.id)

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)
        for contact in rel.access_group_id.contact_ids:
            for card in contact.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 contact.hr_rfid_pin_code, card_id=card.id)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        records = self.env['hr.rfid.access.group.door.rel']
        for val in vals:
            rel = super(HrRfidAccessGroupDoorRel, self).create([val])
            records += rel
            self.time_schedule_changed(rel.id)

        return records

    @api.multi
    def write(self, vals):
        for rel in self:
            old_acc_gr_id = rel.access_group_id.id
            old_door_id = rel.door_id.id
            old_ts_id = rel.time_schedule_id.id

            super(HrRfidAccessGroupDoorRel, rel).write(vals)

            new_acc_gr_id = rel.access_group_id.id
            new_door_id = rel.door_id.id
            new_ts_id = rel.time_schedule_id.id

            if old_acc_gr_id != new_acc_gr_id:
                self.access_group_changed(rel.id, old_acc_gr_id)

            if old_door_id != new_door_id:
                self.door_changed(rel.id, old_door_id)

            if old_ts_id != new_ts_id:
                self.time_schedule_changed(rel.id)

        return True

    @api.multi
    def unlink(self):
        cmd_env = self.env['hr.rfid.command']

        for rel in self:
            for user in rel.access_group_id.user_ids:
                for card in user.hr_rfid_card_ids:
                    cmd_env.remove_card(rel.door_id.id, rel.time_schedule_id.id,
                                        user.hr_rfid_pin_code, card_id=card.id)

        ret = super(HrRfidAccessGroupDoorRel, self).unlink()
        return ret


class HrRfidAccessGroupWizard(models.TransientModel):
    _name = 'hr.rfid.access.group.wizard'
    _description = 'Add or remove doors to the access group'

    def _default_acc_gr(self):
        return self.env['hr.rfid.access.group'].browse(self._context.get('active_ids'))

    def _default_acc_gr_doors(self):
        acc_gr = self._default_acc_gr()
        doors = self.env['hr.rfid.door']
        for door_rel in acc_gr.door_ids:
            doors += door_rel.door_id
        return doors

    acc_gr_id = fields.Many2many(
        'hr.rfid.access.group',
        string='Access Group',
        required=True,
        default=_default_acc_gr,
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        'my_door_ids',
        'wiz',
        'door',
        string='Doors',
        help='Which doors to add to the access group',
        required=True,
    )

    acc_gr_doors = fields.Many2many(
        'hr.rfid.door',
        'custom_door_ids',
        'wiz',
        'door',
        string='All access group doors',
        default=_default_acc_gr_doors,
    )

    time_schedule_id = fields.Many2one(
        'hr.rfid.time.schedule',
        string='Time Schedule',
        help='Time schedule for the door/access group combination',
        required=True,
        default=lambda self: self.env.ref('hr_rfid.hr_rfid_time_schedule_0').id,
    )

    @api.multi
    def add_doors(self):
        self.ensure_one()
        rel_env = self.env['hr.rfid.access.group.door.rel']
        for door in self.door_ids:
            res = rel_env.search([ ('access_group_id', '=', self.acc_gr_id.id),
                                   ('door_id', '=', door.id) ])
            if len(res) == 1:
                res.time_schedule_id = self.time_schedule_id
            else:
                rel_env.create([{
                    'access_group_id': self.acc_gr_id.id,
                    'door_id': door.id,
                    'time_schedule_id': self.time_schedule_id.id,
                }])
        return {}

    @api.multi
    def del_doors(self):
        self.ensure_one()
        rel_env = self.env['hr.rfid.access.group.door.rel']
        for door in self.door_ids:
            res = rel_env.search([ ('access_group_id', '=', self.acc_gr_id.id),
                                   ('door_id', '=', door.id) ])
            if len(res) > 0:
                res.unlink()





















