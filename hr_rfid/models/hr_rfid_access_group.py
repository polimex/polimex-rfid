# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import logging
import queue

_logger = logging.getLogger(__name__)


class HrRfidAccessGroup(models.Model):
    _name = 'hr.rfid.access.group'
    _inherit = ['mail.thread']

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

    # TODO Maybe use BFS instead of DFS to remove the recursion aspect?
    @api.depends('door_ids', 'inherited_access_groups')
    def _compute_all_doors(self):
        door_ids = set()
        HrRfidAccessGroup._check_all_doors_rec(door_ids, [], self)
        self.all_door_ids = self.env['hr.rfid.access.group.door.rel'].browse(list(door_ids))

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
        acc_env = self.env['hr.rfid.access.group']
        to_check = queue.Queue()
        for acc_gr in self.inherited_access_groups:
            to_check.put(acc_gr.id)
        while not to_check.empty():
            check_id = to_check.get()
            if self.id == check_id:
                # TODO Show the path to the circular reference, we need DFS for that i think *gulp*
                raise exceptions.ValidationError('Circular reference found in the inherited access groups!')
            acc_gr = acc_env.browse(check_id)
            for acc_gr in acc_gr.inherited_access_groups:
                to_check.put(acc_gr.id)

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

            # TODO Create commands for access group inheritors
            HrRfidAccessGroup._create_add_door_commands(acc_gr, added_doors)
            HrRfidAccessGroup._create_remove_door_commands(acc_gr, removed_doors)
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
        return self.env.context.get('access_group_id', None)

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
        rel = self.env['hr.rfid.access.group.door.rel'].browse(rel_id)
        cmd_env = self.env['hr.rfid.command']

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)

    @api.model
    def door_changed(self, rel_id, prev_door_id):
        """
        Call after you change the door
        :param rel_id: The id of the relation
        :param prev_door_id: The id of the previous door
        """
        rel = self.env['hr.rfid.access.group.door.rel'].browse(rel_id)
        prev_door = self.env['hr.rfid.door'].browse(prev_door_id)
        cmd_env = self.env['hr.rfid.command']

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.remove_card(prev_door.id, rel.time_schedule_id.id,
                                    user.hr_rfid_pin_code, card_id=card.id)
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id, user.hr_rfid_pin_code,
                                 card_id=card.id)

    @api.model
    def access_group_changed(self, rel_id, prev_acc_gr_id):
        # """
        # Call after you change the access_group
        # :param rel_id: The id of the access group
        # :param prev_acc_gr_id: The id of the previous access group
        # """
        rel = self.env['hr.rfid.access.group.door.rel'].browse(rel_id)
        prev_acc_gr = self.env['hr.rfid.access.group'].browse(prev_acc_gr_id)
        cmd_env = self.env['hr.rfid.command']

        for user in prev_acc_gr.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)

        for user in rel.access_group_id.user_ids:
            for card in user.hr_rfid_card_ids:
                cmd_env.add_card(rel.door_id.id, rel.time_schedule_id.id,
                                 user.hr_rfid_pin_code, card_id=card.id)

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        records = self.env['hr.rfid.access.group.door.rel']
        for vals in vals_list:
            rec = super(HrRfidAccessGroupDoorRel, self).create([vals])
            # Pretend the time schedule changed, it does the same bloody thing
            # as creating the thing anyway
            self.time_schedule_changed(rec.id)
            records += rec
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

            env = self.env['hr.rfid.access.groupd.door.rel']

            if old_acc_gr_id != new_acc_gr_id:
                env.access_group_changed(rel, old_acc_gr_id)

            if old_door_id != new_door_id:
                env.door_changed(rel, old_door_id)

            if old_ts_id != new_ts_id:
                env.time_schedule_changed(rel)

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



















