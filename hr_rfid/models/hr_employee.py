# -*- coding: utf-8 -*-
import itertools

from odoo import api, fields, models, exceptions, http, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    hr_rfid_pin_code = fields.Char(
        string='User pin code',
        help="Pin code for this user, four zeroes means that the user has no pin code.",
        size=4,
        default='0000',
        tracking=True,
        groups="hr_rfid.hr_rfid_group_officer"
    )

    hr_rfid_access_group_ids = fields.One2many(
        'hr.rfid.access.group.employee.rel',
        'employee_id',
        string='Access Groups',
        help='Which access groups the user is a part of',
        tracking=True,
        groups="hr_rfid.hr_rfid_group_officer"
    )

    hr_rfid_card_ids = fields.One2many(
        'hr.rfid.card',
        'employee_id',
        string='RFID Card',
        help='Cards owned by the employee',
        context={'active_test': False},
        groups="hr_rfid.hr_rfid_group_officer"
    )

    hr_rfid_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'employee_id',
        string='RFID Events',
        help='Events concerning this employee',
        groups="hr_rfid.hr_rfid_group_officer"
    )

    in_zone_ids = fields.Many2many(
        'hr.rfid.zone',
        compute='_compute_zones_for_employee',
        groups="hr_rfid.hr_rfid_group_officer"

    )

    employee_event_count = fields.Char(
        compute='_compute_employee_event_count',
        groups="hr_rfid.hr_rfid_group_officer"
    )
    employee_doors_count = fields.Char(
        compute='_compute_employee_event_count',
        groups="hr_rfid.hr_rfid_group_officer"
    )

    def _compute_employee_event_count(self):
        for e in self:
            e.employee_event_count = self.env['hr.rfid.event.user'].search_count([('employee_id', '=', e.id)])
            e.employee_doors_count = len(e.get_doors())

    def button_employee_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.rfid.event.user',
            'domain': [('employee_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    No events for this employee.
                </p>'''),
        }

    def button_doors_list(self):
        self.ensure_one()
        return {
            'name': _('Doors accessible from {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.rfid.door',
            'domain': [('id', 'in', self.get_doors().mapped('id'))],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    No accessible doors for this employee.
                </p>'''),
        }

    def _compute_zones_for_employee(self):
        for e in self:
            e.in_zone_ids = self.env['hr.rfid.zone'].search([]).filtered(lambda z: e in z.employee_ids)

    def add_acc_gr(self, access_groups, expiration=None):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        for emp in self:
            for acc_gr in access_groups:
                rel = rel_env.search([
                    ('employee_id', '=', emp.id),
                    ('access_group_id', '=', acc_gr.id),
                ])
                if rel:
                    rel.expiration = expiration
                    continue
                emp.check_for_ts_inconsistencies_when_adding(acc_gr)
                creation_dict = {
                    'employee_id': emp.id,
                    'access_group_id': acc_gr.id,
                }
                if expiration is not None and expiration is not False:
                    creation_dict['expiration'] = str(expiration)
                rel_env.create(creation_dict)

    def remove_acc_gr(self, access_groups):
        rel_env = self.env['hr.rfid.access.group.employee.rel']
        rel_env.search([
            ('employee_id', 'in', self.ids),
            ('access_group_id', 'in', access_groups.ids)
        ]).unlink()

    @api.returns('hr.rfid.door')
    def get_doors(self, excluding_acc_grs=None, including_acc_grs=None):
        if excluding_acc_grs is None:
            excluding_acc_grs = self.env['hr.rfid.access.group']
        if including_acc_grs is None:
            including_acc_grs = self.env['hr.rfid.access.group']

        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        acc_grs = acc_grs - excluding_acc_grs
        acc_grs = acc_grs + including_acc_grs
        return acc_grs.mapped('all_door_ids').mapped('door_id')

    def check_for_ts_inconsistencies_when_adding(self, new_acc_grs):
        acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']
        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        for acc_gr1 in acc_grs:
            for acc_gr2 in new_acc_grs:
                door_rels1 = acc_gr1.all_door_ids
                door_rels2 = acc_gr2.all_door_ids
                acc_gr_door_rel_env.check_for_ts_inconsistencies(door_rels1, door_rels2)

    def check_for_ts_inconsistencies(self):
        acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']
        for acc_gr1, acc_gr2 in itertools.combinations(self.hr_rfid_access_group_ids.mapped('access_group_id'), 2):
            acc_gr_door_rel_env.check_for_ts_inconsistencies(acc_gr1.all_door_ids, acc_gr2.all_door_ids)
        # acc_gr_door_rel_env = self.env['hr.rfid.access.group.door.rel']
        # acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        # for i in range(len(acc_grs)):
        #     for j in range(i + 1, len(acc_grs)):
        #         door_rels1 = acc_grs[i].all_door_ids
        #         door_rels2 = acc_grs[j].all_door_ids
        #         acc_gr_door_rel_env.check_for_ts_inconsistencies(door_rels1, door_rels2)

    @api.constrains('hr_rfid_access_group_ids')
    def check_access_group(self):
        for user in self:
            user.check_for_ts_inconsistencies()
            user.hr_rfid_access_group_ids.mapped('access_group_id').check_doors()
            for acc_gr_rel in user.hr_rfid_access_group_ids:
                acc_gr = acc_gr_rel.access_group_id
                if acc_gr not in user.department_id.hr_rfid_allowed_access_groups:
                    raise exceptions.ValidationError('Access group must be one of the access '
                                                     'groups assigned to the department!')

            doors = user.hr_rfid_access_group_ids.mapped('access_group_id') \
                .mapped('all_door_ids').mapped('door_id')
            user.hr_rfid_access_group_ids.mapped('access_group_id').check_doors()
            relay_doors = dict()
            for door in doors:
                ctrl = door.controller_id
                if ctrl.is_relay_ctrl():
                    if ctrl in relay_doors and relay_doors.get(ctrl, False) and door.card_type in relay_doors[
                        ctrl].mapped(
                            'card_type') and ctrl.mode == 3:
                        raise exceptions.ValidationError(
                            _('Doors "%s" and "%s" both belong to a controller that cannot give access to multiple doors with same card type in a group.')
                            % (','.join(relay_doors[ctrl].mapped('name')), door.name)
                        )
                    if not relay_doors.get(ctrl, False):
                        relay_doors[ctrl] = self.env['hr.rfid.door'].browse([door.id])
                    else:
                        relay_doors[ctrl] = self.env['hr.rfid.door'].browse(
                            relay_doors[ctrl].mapped('id') + [door.id])

    @api.constrains('hr_rfid_pin_code')
    def _check_pin_code(self):
        for user in self:
            pin = user.hr_rfid_pin_code
            if len(pin) != 4:
                raise exceptions.ValidationError('Pin code must have exactly 4 characters')

            # If char is not a valid decimal number, int(char, 10) will raise an error
            try:
                for char in str(pin):
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Invalid pin code, digits must be from 0 to 9')

    def generate_random_barcode_card(self):
        self.ensure_one()
        new_card_hex, card_number = self.env['hr.rfid.card'].create_bc_card()
        self.write({
            'hr_rfid_card_ids': [(0, 0, {
                'number': card_number,
                'card_type': self.env.ref('hr_rfid.hr_rfid_card_type_barcode').id
            })]
        })

    @api.model_create_multi
    def create(self, vals_list):
        records = super(HrEmployee, self).create(vals_list)

        for rec in records:
            rec.add_acc_gr(rec.department_id.hr_rfid_default_access_group)

        return records

    def write(self, vals):
        for user in self:
            old_pin_code = user.hr_rfid_pin_code[:]
            old_dep = user.department_id
            old_active = user.active

            super(HrEmployee, user).write(vals)

            new_pin_code = user.hr_rfid_pin_code
            new_dep = user.department_id
            new_active = user.active

            if old_active != new_active:
                user.hr_rfid_card_ids.write({'active': new_active})

            if old_dep != new_dep:
                new_dep_acc_grs = new_dep.hr_rfid_allowed_access_groups
                for acc_gr_rel in user.hr_rfid_access_group_ids:
                    if acc_gr_rel.access_group_id not in new_dep_acc_grs:
                        acc_gr_rel.unlink()
                if new_dep.hr_rfid_default_access_group:
                    user.add_acc_gr(new_dep.hr_rfid_default_access_group)

            if old_pin_code != new_pin_code:
                user.hr_rfid_card_ids.mapped('door_rel_ids').pin_code_changed()

    def unlink(self):
        for emp in self:
            emp.hr_rfid_card_ids.unlink()
            emp.hr_rfid_access_group_ids.unlink()
        return super(HrEmployee, self).unlink()

    def log_person_out(self, sids=None):
        for emp in self:
            if not emp.user_id:
                continue
            user = emp.user_id
            session_storage = http.root.session_store
            if sids is None:
                sids = session_storage.list()
            for sid in sids:
                session = session_storage.get(sid)
                if session['uid'] == user.id:
                    session_storage.delete(session)
