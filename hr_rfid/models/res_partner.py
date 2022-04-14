# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, http, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    hr_rfid_pin_code = fields.Char(
        string='Contact pin code',
        help="Pin code for this contact, four zeroes means that the contact has no pin code.",
        size=4,
        default='0000',
        tracking=True,
    )

    hr_rfid_access_group_ids = fields.One2many(
        'hr.rfid.access.group.contact.rel',
        'contact_id',
        string='Access Group',
        help='Which access group the contact is a part of',
        tracking=True,
    )

    hr_rfid_card_ids = fields.One2many(
        'hr.rfid.card',
        'contact_id',
        string='RFID Card',
        help='Cards owned by the contact',
    )

    hr_rfid_event_ids = fields.One2many(
        'hr.rfid.event.user',
        'contact_id',
        string='RFID Events',
        help='Events concerning this contact',
    )

    is_employee = fields.Boolean(compute='_compute_is_employee')

    partner_event_count = fields.Char(compute='_compute_partner_event_count')
    partner_doors_count = fields.Char(compute='_compute_partner_event_count')

    def _compute_partner_event_count(self):
        for e in self:
            e.partner_event_count = self.env['hr.rfid.event.user'].search_count([('contact_id', '=', e.id)])
            e.partner_doors_count = len(e.get_doors())

    def _compute_is_employee(self):
        empl_partners = self.env['resource.resource'].search([('user_id', '!=', False)]).mapped('user_id.partner_id.id')
        for p in self:
            p.is_employee = p.id in empl_partners

    def button_partner_events(self):
        self.ensure_one()
        return {
            'name': _('Events for {}').format(self.name),
            'view_mode': 'tree,form',
            'res_model': 'hr.rfid.event.user',
            'domain': [('contact_id', '=', self.id)],
            'type': 'ir.actions.act_window',
            'help': _('''<p class="o_view_nocontent">
                    No events for this partner.
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
                    No accessible doors for this partner.
                </p>'''),
        }

    def add_acc_gr(self, access_groups, expiration=None):
        rel_env = self.env['hr.rfid.access.group.contact.rel']
        for cont in self:
            for acc_gr in access_groups:
                rel = rel_env.search([
                    ('contact_id', '=', cont.id),
                    ('access_group_id', '=', acc_gr.id),
                ])
                if rel:
                    rel.expiration = expiration
                    continue
                cont.check_for_ts_inconsistencies_when_adding(acc_gr)
                creation_dict = {
                    'contact_id': cont.id,
                    'access_group_id': acc_gr.id,
                }
                if expiration is not None and expiration is not False:
                    creation_dict['expiration'] = str(expiration)
                rel_env.create(creation_dict)

    def remove_acc_gr(self, access_groups):
        rel_env = self.env['hr.rfid.access.group.contact.rel']
        rel_env.search([
            ('contact_id', 'in', self.ids),
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
        acc_grs = self.hr_rfid_access_group_ids.mapped('access_group_id')
        for i in range(len(acc_grs)):
            for j in range(i + 1, len(acc_grs)):
                door_rels1 = acc_grs[i].all_door_ids
                door_rels2 = acc_grs[i].all_door_ids
                acc_gr_door_rel_env.check_for_ts_inconsistencies(door_rels1, door_rels2)

    @api.constrains('hr_rfid_access_group_ids')
    def check_access_group(self):
        for user in self:
            user.check_for_ts_inconsistencies()

            doors = user.hr_rfid_access_group_ids.mapped('access_group_id'). \
                mapped('all_door_ids').mapped('door_id')
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
        for contact in self:
            pin = contact.hr_rfid_pin_code
            if len(pin) != 4:
                raise exceptions.ValidationError('Pin code must have exactly 4 characters')

            # If char is not a valid hex number, int(char, 16) will raise an error
            try:
                for char in str(pin):
                    int(char, 10)
            except ValueError:
                raise exceptions.ValidationError('Invalid pin code, digits must be from 0 to 9')

    def write(self, vals):
        for user in self:
            old_pin_code = user.hr_rfid_pin_code[:]
            old_active = user.active
            super(ResPartner, user).write(vals)

            if old_active != user.active:
                user.hr_rfid_card_ids.write({'active':user.active})

            if old_pin_code != user.hr_rfid_pin_code:
                user.hr_rfid_card_ids.mapped('door_rel_ids').pin_code_changed()

    def unlink(self):
        for cont in self:
            cont.hr_rfid_card_ids.unlink()
            cont.hr_rfid_access_group_ids.unlink()
        return super(ResPartner, self).unlink()

    def log_person_out(self, sids=None):
        for cont in self:
            if not cont.user_id:
                continue
            user = cont.user_id
            session_storage = http.root.session_store
            if sids is None:
                sids = session_storage.list()
            for sid in sids:
                session = session_storage.get(sid)
                if session['uid'] == user.id:
                    session_storage.delete(session)

    @api.model
    def generate_partner(self, name, parent_id=None, card_number: str = None, unlink_card_if_exsist=True,
                         access_group_id=None):
        '''
        Require:
            name
        Optional:
            parent_id: int - res.partner.id
            card_number: str
            unlink_card_if_exsist:bool
            access_group_id: hr.rfid.access.group.id
        Context:
            activate_on: datetime
            deactivate_on: datetime
        '''
        partner_dict = {
            "name": name,
            "parent_id": parent_id or None,
        }
        if card_number is not None:
            card_number = ('0000000000' + card_number)[-10:]
            existing_card = self.env['hr.rfid.card'].with_context(active_test=False).search(
                [('number', '=', card_number)])
            if unlink_card_if_exsist:
                existing_card.unlink()
                existing_card = None
            if existing_card:
                partner_dict.update({
                    'hr_rfid_card_ids': [(4, existing_card.id, 0), (1, existing_card.id, {
                        # 'number': card_number,
                        'activate_on': self.env.context.get('activate_on') or fields.Datetime.now(),
                        'deactivate_on': self.env.context.get('deactivate_on') or fields.Datetime.now(),
                    })]})
            else:
                partner_dict.update({
                    'hr_rfid_card_ids': [(0, 0, {
                        'number': card_number,
                        'activate_on': self.env.context.get('activate_on') or fields.Datetime.now(),
                        'deactivate_on': self.env.context.get('deactivate_on') or fields.Datetime.now(),
                    })]})
        if access_group_id is not None:
            partner_dict.update({
                'hr_rfid_access_group_ids': [(0, 0, {
                    'access_group_id': access_group_id.id,
                    'activate_on': self.env.context.get('activate_on') or fields.Datetime.now(),
                    'expiration': self.env.context.get('deactivate_on') or fields.Datetime.now(),
                })]
            })
        partner_id = self.env['res.partner'].create(partner_dict)
        return partner_id

    def add_access_group(self, access_group_id, activate_on=None, expire_on=None, visits: int = 0):
        '''
        Adding access group
        '''
        for p in self:
            if access_group_id in p.hr_rfid_access_group_ids.mapped('access_group_id.id'):
                existing = p.hr_rfid_access_group_ids.filtered(lambda ag: ag.access_group_id.id == access_group_id)
                existing.visits_counting = visits > 0
                existing.write({
                    'activate_on': (activate_on < existing.activate_on) and activate_on or existing.activate_on,
                    'expiration': (expire_on > existing.expire_on) and expire_on or existing.expire_on,
                })

                if (existing.permited_visits + visits) > 0:
                    existing.permited_visits += visits
                else:
                    existing.permited_visits = None

            else:
                p.write({'hr_rfid_access_group_ids': [(0, 0, {
                    'access_group_id': access_group_id,
                    'activate_on': activate_on or fields.Datetime.now(),
                    'expiration': expire_on or None,
                    'visits_counting': visits > 0,
                    'permited_visits': visits
                })]})

    def add_card_number(self, card_number, activate_on=None, expire_on=None):
        for p in self:
            if card_number in p.hr_rfid_card_ids.mapped('number'):
                existing = p.hr_rfid_card_ids.filtered(lambda c: c.number == card_number)
                existing.write({
                    'activate_on': (activate_on < existing.activate_on) and activate_on or existing.activate_on,
                    'deactivate_on': (expire_on > existing.deactivate_on) and expire_on or existing.deactivate_on,
                })
            else:
                p.write({
                    'hr_rfid_card_ids': [(0, 0, {
                        'number': card_number,
                        'activate_on': activate_on or fields.Datetime.now(),
                        'deactivate_on': expire_on or None,
                    })]})
