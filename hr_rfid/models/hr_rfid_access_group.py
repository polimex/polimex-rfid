# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class HrRfidAccessGroup(models.Model):
    _name = 'hr.rfid.access.group'

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
    )

    user_ids = fields.One2many(
        'hr.employee',
        'hr_rfid_access_group_id',
        string='Users',
        help='Users part of this access group',
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

    @api.multi
    def write(self, vals):
        for acc_gr in self:
            old_door_ids = {}
            old_ts_ids = set()
            acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']

            if 'door_ids' in vals:
                door_id_changes = vals['door_ids']

                for change in door_id_changes:
                    if change[0] == 1:
                        if 'door_id' in change[2]:
                            old_door_ids[change[1]] = change[2]['door_id']
                        if 'time_schedule_id' in change[2]:
                            old_ts_ids.add(change[2]['time_schedule_id'])

            super(HrRfidAccessGroup, acc_gr).write(vals)

            for rel_id, prev_door_id in old_door_ids.items():
                acc_gr_door_rel_env.door_changed(rel_id, prev_door_id)

            for rel_id in old_ts_ids:
                acc_gr_door_rel_env.time_schedule_changed(rel_id)

        return True

    @api.multi
    def unlink(self):
        for acc_gr in self:
            acc_gr.door_ids.unlink()

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
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        rec = super(HrRfidAccessGroupDoorRel, self).create(vals)
        # Pretend the time schedule changed, it does the same bloody thing
        # as creating the thing anyway
        self.time_schedule_changed(rec.id)
        return rec

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
        """
        Call after you change the access_group
        :param rel_id: The id of the access group
        :param prev_acc_gr_id: The id of the previous access group
        """
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




















