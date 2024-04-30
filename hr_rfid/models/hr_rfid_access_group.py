# -*- coding: utf-8 -*-
from collections import Counter

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, exceptions, _
import logging
import queue

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrRfidAccessGroup(models.Model):
    _name = 'hr.rfid.access.group'
    _inherit = ['mail.thread']
    _description = 'Access Group'

    def access_group_generate_name(self):
        env = self.env['hr.rfid.access.group'].search([])

        if len(env) == 0:
            return _('Access Group 1')
        else:
            return _('Access Group ') + str(env[-1].id + 1)

    name = fields.Char(
        string='Name',
        help='A label to help differentiate between access groups',
        default=access_group_generate_name,
        size=32,
        tracking=True,
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)

    delay_between_events = fields.Integer(
        help="Minimum time in seconds between events on listed doors."
             "The card will be rejected if this time is not pass since last event. "
             "0 means disabled. IMPORTANT: The function works ONLY with controllers(doors) with enabled External DB.",
        default=0
    )

    employee_ids = fields.One2many(
        'hr.rfid.access.group.employee.rel',
        'access_group_id',
        string='Users',
        help='Users part of this access group',
    )

    contact_ids = fields.One2many(
        'hr.rfid.access.group.contact.rel',
        'access_group_id',
        string='Contacts',
        help='Contacts part of this access group'
    )

    door_ids = fields.One2many(
        'hr.rfid.access.group.door.rel',
        'access_group_id',
        string='Doors',
        help='Doors included in this access group',
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

    inherited_ids = fields.Many2many(
        comodel_name='hr.rfid.access.group',
        relation='access_group_inheritance',
        column1='inheritor',
        column2='inherited',
        string='Inherited access groups',
    )

    inheritor_ids = fields.Many2many(
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
    )

    all_employee_ids = fields.Many2many(
        'hr.rfid.access.group.employee.rel',
        string='All employees',
        help='All employees that use this access group, including the ones from the inheritors',
        compute='_compute_all_employees',
    )

    all_contact_ids = fields.Many2many(
        'hr.rfid.access.group.contact.rel',
        string='All contacts',
        help='All contacts that use this access group, including the ones from the inheritors',
        compute='_compute_all_contacts',
    )

    def _calc_last_user_event_in_ag(self, partner_id=None, employee_id=None):
        last_event = self.env['hr.rfid.event.user']
        for ag in self:
            ag_last_event = self.env['hr.rfid.event.user'].last_event(ag.all_door_ids.mapped('door_id'), partner_id,
                                                                      employee_id, event_action=1)
            if ag_last_event and (ag_last_event.event_time >= (
                    fields.Datetime.now() + relativedelta(seconds=-1 * ag.delay_between_events))):
                last_event += ag_last_event
        return last_event

    def check_doors(self):
        errors = ''
        for g in self:
            for p in g.all_contact_ids.mapped('contact_id'):
                doors = []
                for ag in p.hr_rfid_access_group_ids.mapped('access_group_id'):
                    doors += ag.all_door_ids.mapped('door_id')
                if len(doors) != len(set(doors)):
                    counter = Counter(doors)
                    duplicates = [item for item, count in counter.items() if count > 1]
                    if self.env['ir.config_parameter'].sudo().get_param('hr_rfid.raise_if_duplicate_doors') in ['true',
                                                                                                                'True',
                                                                                                                '1']:
                        raise exceptions.ValidationError(
                            _('Partner %s have the %s door twice via different access groups. This is not allowed.') %
                            (p.name, ','.join([d.name for d in duplicates])))
                    else:
                        _logger.error(
                            'Partner %s have the %s door twice via different access groups. This is not allowed.',
                            p.name, ','.join([d.name for d in duplicates]))
                        errors += _(
                            'Partner %s have the %s door twice via different access groups. This is not allowed.') % (
                                      p.name, ','.join([d.name for d in duplicates])) + '\n'
            for p in g.all_employee_ids.mapped('employee_id'):
                doors = []
                for ag in p.hr_rfid_access_group_ids.mapped('access_group_id'):
                    doors += ag.all_door_ids.mapped('door_id')
                if len(doors) != len(set(doors)):
                    counter = Counter(doors)
                    duplicates = [item for item, count in counter.items() if count > 1]
                    if self.env['ir.config_parameter'].sudo().get_param('hr_rfid.raise_if_duplicate_doors') in ['true',
                                                                                                                'True',
                                                                                                                '1']:
                        raise exceptions.ValidationError(
                            _('Employee %s have the %s door twice via different access groups. This is not allowed.') %
                            (p.name, ','.join([d.name for d in duplicates])))
                    else:
                        _logger.error(
                            'Employee %s have the %s door twice via different access groups. This is not allowed.',
                            p.name,
                            ','.join([d.name for d in duplicates]))
                        errors += _(
                            'Employee %s have the %s door twice via different access groups. This is not allowed.') % (
                                      p.name, ','.join([d.name for d in duplicates])) + '\n'
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": _(
                    errors or "No found any door duplicates in the access groups."
                ),
                "type": "warning" if errors else "success",
                "sticky": False if errors else True,
            },
        }

    def add_doors(self, door_ids, time_schedule=None, alarm_rights=False):
        self.ensure_one()
        if time_schedule is None:
            time_schedule = self.env['hr.rfid.time.schedule'].search([], limit=1, order='number')[0]

        for door in door_ids:
            res = self.env['hr.rfid.access.group.door.rel'].search([
                ('access_group_id', '=', self.id),
                ('door_id', '=', door.id)
            ])
            if len(res) == 1:
                if res.time_schedule_id != time_schedule:
                    res.time_schedule_id = time_schedule
                if res.alarm_rights != alarm_rights:
                    res.alarm_rights = alarm_rights
            else:
                # if controller is of type iCON130 or iCON180
                if door.controller_id.hw_version in ['17', '10'] and time_schedule.number > 3:
                    raise exceptions.ValidationError(_('Door %s can only use the first 3 time schedules') %
                                                     door.name)
                self.env['hr.rfid.access.group.door.rel'].create([{
                    'access_group_id': self.id,
                    'door_id': door.id,
                    'time_schedule_id': time_schedule.id,
                    'alarm_rights': alarm_rights,
                }])
        self.check_for_ts_inconsistencies()
        self.check_doors()

    def del_doors(self, door_ids):
        rel_env = self.env['hr.rfid.access.group.door.rel']
        for door in door_ids:
            rel_env.search([
                ('access_group_id', '=', self.id),
                ('door_id', '=', door.id)
            ]).unlink()

    @api.returns('hr.rfid.door')
    def get_all_doors(self):
        return self.mapped('all_door_ids').mapped('door_id')

    @api.returns('hr.employee')
    def get_all_employees(self):
        return self.mapped('all_employee_ids').mapped('employee_id')

    @api.returns('res.partner')
    def get_all_contacts(self):
        return self.mapped('all_contact_ids').mapped('contact_id')

    @api.constrains('door_ids')
    def door_ids_constrains(self):
        for acc_gr in self:
            door_id_list = []
            for rel in acc_gr.door_ids:
                if rel.door_id.id in door_id_list:
                    raise exceptions.ValidationError('Cannot link access group to a door '
                                                     'it is already linked to.')

            relay_doors = dict()
            for rel in acc_gr.all_door_ids:
                ctrl = rel.door_id.controller_id
                if ctrl.is_relay_ctrl():
                    if ctrl in relay_doors and relay_doors.get(ctrl, False) and rel.door_id.card_type in relay_doors[
                        ctrl].mapped(
                        'card_type') and ctrl.mode == 3:
                        raise exceptions.ValidationError(
                            _('Doors "%s" and "%s" both belong to a controller that cannot give access to multiple doors with same card type in a group.')
                            % (','.join(relay_doors[ctrl].mapped('name')), rel.door_id.name)
                        )
                    if not relay_doors.get(ctrl, False):
                        relay_doors[ctrl] = self.env['hr.rfid.door'].browse([rel.door_id.id])
                    else:
                        relay_doors[ctrl] = self.env['hr.rfid.door'].browse(
                            relay_doors[ctrl].mapped('id') + [rel.door_id.id])

                door_id_list.append(rel.door_id.id)

    @api.depends('door_ids', 'inherited_ids')
    def _compute_all_doors(self):
        for acc_gr in self:
            door_ids = set()
            HrRfidAccessGroup._check_all_doors_rec(door_ids, [], acc_gr)
            acc_gr.all_door_ids = self.env['hr.rfid.access.group.door.rel'].browse(list(door_ids))

    @api.depends('employee_ids', 'inheritor_ids')
    def _compute_all_employees(self):
        for acc_gr in self:
            employee_ids = set()
            HrRfidAccessGroup._check_all_employees_rec(employee_ids, [], acc_gr)
            acc_gr.all_employee_ids = self.env['hr.rfid.access.group.employee.rel'].browse(list(employee_ids))

    @api.depends('contact_ids', 'inheritor_ids')
    def _compute_all_contacts(self):
        for acc_gr in self:
            contact_ids = set()
            HrRfidAccessGroup._check_all_contacts_rec(contact_ids, [], acc_gr)
            acc_gr.all_contact_ids = self.env['hr.rfid.access.group.contact.rel'].browse(list(contact_ids))

    @staticmethod
    def _check_all_doors_rec(door_ids: set, checked_ids: list, acc_gr):
        if acc_gr.id in checked_ids:
            return
        checked_ids.append(acc_gr.id)
        for door in acc_gr.door_ids:
            door_ids.add(door.id)
        for rec_gr in acc_gr.inherited_ids:
            HrRfidAccessGroup._check_all_doors_rec(door_ids, checked_ids, rec_gr)

    @staticmethod
    def _check_all_employees_rec(emp_ids: set, checked_ids: list, acc_gr):
        if acc_gr.id in checked_ids:
            return
        checked_ids.append(acc_gr.id)
        for employee in acc_gr.employee_ids:
            emp_ids.add(employee.id)
        for rec_gr in acc_gr.inheritor_ids:
            HrRfidAccessGroup._check_all_employees_rec(emp_ids, checked_ids, rec_gr)

    @staticmethod
    def _check_all_contacts_rec(contact_ids: set, checked_ids: list, acc_gr):
        if acc_gr.id in checked_ids:
            return
        checked_ids.append(acc_gr.id)
        for contact in acc_gr.contact_ids:
            contact_ids.add(contact.id)
        for rec_gr in acc_gr.inheritor_ids:
            HrRfidAccessGroup._check_all_contacts_rec(contact_ids, checked_ids, rec_gr)

    def check_for_ts_inconsistencies(self):
        def get_highest_acc_grs(_gr):
            if len(_gr.inheritor_ids) == 0:
                return _gr

            _hg = self.env['hr.rfid.access.group']
            for _acc_gr in _gr.inheritor_ids:
                if len(_acc_gr.inheritor_ids) == 0:
                    _hg += _acc_gr
                else:
                    _hg += get_highest_acc_grs(_acc_gr)
            return _hg

        def check_tses(_gr1, _gr2):
            _doors1 = _gr1.door_ids
            _doors2 = _gr2.door_ids
            _door_rel_env = self.env['hr.rfid.access.group.door.rel']
            _door_rel_env.check_for_ts_inconsistencies(_doors1, _doors2)

        def iterate_acc_grs(_gr, _checked_groups):
            for _gr2 in _gr.inherited_ids:
                if _gr2 in _checked_groups:
                    continue
                _checked_groups.append(_gr2)
                check_tses(_gr, _gr2)
                iterate_acc_grs(_gr2, _checked_groups)

        highest_groups = get_highest_acc_grs(self)
        for acc_gr in highest_groups:
            iterate_acc_grs(acc_gr, [])
        employees = self.all_employee_ids.mapped('employee_id')
        contacts = self.all_contact_ids.mapped('contact_id')
        employees.mapped(lambda r: r.check_for_ts_inconsistencies())
        contacts.mapped(lambda r: r.check_for_ts_inconsistencies())

    @api.constrains('inherited_ids')
    def _check_inherited_ids(self):
        env = self.env['hr.rfid.access.group']
        for acc_gr in self:
            group_order = []
            ret = HrRfidAccessGroup._check_inherited_ids_rec(acc_gr, [], group_order)
            if ret is True:
                err2 = ''
                for acc_gr_id in group_order:
                    acc_gr = env.browse(acc_gr_id)
                    err2 += '\n-> '
                    err2 += acc_gr.name
                err = _('Circular reference found in the inherited access groups: %s') % err2
                raise exceptions.ValidationError(err)

            acc_gr.check_for_ts_inconsistencies()

    @staticmethod
    def _check_inherited_ids_rec(acc_gr, visited_groups: list, group_order: list, orig_id=None):
        group_order.append(acc_gr.id)
        if acc_gr.id == orig_id:
            return True
        if orig_id is None:
            orig_id = acc_gr.id

        if acc_gr.id in visited_groups:
            return False

        visited_groups.append(acc_gr.id)

        for inh_gr in acc_gr.inherited_ids:
            res = HrRfidAccessGroup._check_inherited_ids_rec(inh_gr, visited_groups,
                                                             group_order, orig_id)
            if res is True:
                return True

        group_order.pop()
        return False

    def _create_add_door_commands(self, doors):
        card_rel_env = self.env['hr.rfid.card.door.rel']
        employees = self.all_employee_ids.mapped('employee_id')
        contacts = self.all_contact_ids.mapped('contact_id')
        cards = employees.mapped('hr_rfid_card_ids') + contacts.mapped('hr_rfid_card_ids')
        for door in doors:
            for card in cards:
                card_rel_env.check_relevance_fast(card, door)

    def _create_remove_door_commands(self, doors):
        card_rel_env = self.env['hr.rfid.card.door.rel']
        employees = self.all_employee_ids.mapped('employee_id')
        contacts = self.all_contact_ids.mapped('contact_id')
        cards = employees.mapped('hr_rfid_card_ids') + contacts.mapped('hr_rfid_card_ids')
        for door in doors:
            for card in cards:
                card_rel_env.check_relevance_slow(card, door)

    def write(self, vals):
        for acc_gr in self:
            old_doors = self.all_door_ids.mapped('door_id')

            super(HrRfidAccessGroup, acc_gr).write(vals)

            new_doors = self.all_door_ids.mapped('door_id')

            added_doors = new_doors - old_doors
            removed_doors = old_doors - new_doors

            env = self.env['hr.rfid.access.group']
            completed_groups = []
            acc_gr_to_complete = queue.Queue()
            acc_gr_to_complete.put(acc_gr.id)

            while not acc_gr_to_complete.empty():
                inh_id = acc_gr_to_complete.get()
                if inh_id in completed_groups:
                    continue
                completed_groups.append(inh_id)
                inh = env.browse(inh_id)
                HrRfidAccessGroup._create_add_door_commands(inh, added_doors)
                HrRfidAccessGroup._create_remove_door_commands(inh, removed_doors)

                for upper_inh in inh.inheritor_ids:
                    acc_gr_to_complete.put(upper_inh.id)

        return True

    # TODO Need to review and delete this
    def unlink(self):
        for acc_gr in self:
            acc_gr.door_ids.unlink()  # Unlinks the relations
            acc_gr.employee_ids.unlink()  # Unlinks the relations
            acc_gr.contact_ids.unlink()  # Unlinks the relations
        return super(HrRfidAccessGroup, self).unlink()


class HrRfidAccessGroupDoorRel(models.Model):
    _name = 'hr.rfid.access.group.door.rel'
    _description = 'Relation between access groups and doors'

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
    card_type = fields.Many2one(
        comodel_name='hr.rfid.card.type',
        related='door_id.card_type'
    )

    time_schedule_id = fields.Many2one(
        'hr.rfid.time.schedule',
        string='Time schedule',
        help='Time schedule for the door/access group combination',
        default=lambda self: self.env['hr.rfid.time.schedule'].search([], limit=1, order='number')[0].id,
        required=True,
        ondelete='cascade',
    )
    alarm_rights = fields.Boolean(
        help='Give alarm rights for this door. The user can Arm/Disarm door.',
        default=False,
        required=True
    )

    @api.model
    def check_for_ts_inconsistencies(self, rels1, rels2):
        for door_rel in rels1:
            for door_rel2 in rels2[:]:
                if door_rel.door_id == door_rel2.door_id:
                    if door_rel.time_schedule_id != door_rel2.time_schedule_id:
                        raise exceptions.ValidationError(
                            _('Time schedule does not match for door "%s" in access groups "%s" and "%s"')
                            % (door_rel.door_id.name, door_rel.access_group_id.name,
                               door_rel2.access_group_id.name))
                    rels2 -= door_rel2

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        card_door_rel_env = self.env['hr.rfid.card.door.rel']

        records = super(HrRfidAccessGroupDoorRel, self).create(vals)

        records.mapped('access_group_id').door_ids_constrains()

        for rel in records:
            card_door_rel_env.update_door_rels(rel.door_id, rel.access_group_id)
            rel.door_id.controller_id.write_ts_id(rel.time_schedule_id)

        return records

    def write(self, vals):
        raise exceptions.ValidationError('Not permitted to write here (hr.rfid.access.group.door.rel)')

    def unlink(self):
        for rel in self:
            door_id = rel.door_id
            ts_id = rel.time_schedule_id
            cards = door_id.get_cards(access_groups=rel.access_group_id)
            super(HrRfidAccessGroupDoorRel, rel).unlink()
            door_id.controller_id.delete_ts_id(ts_id)
            for card, ts, alarm_right in cards:
                self.env['hr.rfid.card.door.rel'].check_relevance_slow(card, door_id, alarm_right)


def _check_overlap(ranges):
    # Sort the ranges based on start time
    # Replace False with datetime.now()
    modified_ranges = [(start, end if end is not False else fields.Datetime.now()) for (start, end) in ranges]
    sorted_ranges = sorted(modified_ranges, key=lambda x: x[0])

    # Iterate over the ranges and check for overlap
    for i in range(len(sorted_ranges) - 1):
        # If the end time of the current range is greater than the start time of the next range
        if sorted_ranges[i][1] > sorted_ranges[i + 1][0]:
            return True  # Overlap found

    return False  # No overlaps


class HrRfidAccessGroupRelations(models.AbstractModel):
    _name = 'hr.rfid.access.group.rel'
    _description = 'Relation between access groups and employees'

    state = fields.Boolean(
        default=False,
        compute='_compute_state',
        store=True,
    )
    internal_state = fields.Boolean(default=False)

    access_group_id = fields.Many2one(
        'hr.rfid.access.group',
        string='Access Group',
        required=True,
    )
    # TODO New field. Need to implemented in cron job tasks!!!
    activate_on = fields.Datetime(
        string='Activation Date',
        help='Access group will activate itself from the contact '
             'on the  date. ',
        default=lambda self: fields.Datetime.now(),
        index=True,
    )

    expiration = fields.Datetime(
        string='Expiration Date',
        help='Access group will remove itself from the contact '
             'on the expiration date. Will never expire if blank.',
        index=True,
    )

    visits_counting = fields.Boolean(
        help='If True, the access group will counting visits. \n'
             'The feature is used for RFID services in general.',
        default=False
    )
    permitted_visits = fields.Integer(
        help='After reaching the allowed visits for this group, the group will be deactivated.\n'
             'Zero visits exclude the function for automatic deactivation.',
        default=0
    )
    visits_counter = fields.Integer(
        help='Real visits this group will be deactivated. 0 mean',
        default=0
    )

    def _deactivate(self):
        raise exceptions.ValidationError('Not implemented yet!')

    def _activate(self):
        raise exceptions.ValidationError('Not implemented yet!')

    def inc_visits(self):
        for s in self:
            s.visits_counter += 1

    def _active_state_change(self, new_state):
        for agr in self:
            if new_state:  # activating rights
                self._activate()
            else:  # de-activating rights
                self._deactivate()
            agr.internal_state = new_state

    @api.depends('activate_on', 'expiration', 'visits_counting', 'permitted_visits', 'visits_counter')
    def _compute_state(self):
        for agr in self:
            res = [agr.activate_on <= fields.Datetime.now()]
            if agr.expiration:
                res.append(agr.expiration >= fields.Datetime.now())
            if agr.visits_counting and agr.permitted_visits > 0:
                res.append(agr.visits_counter < agr.permitted_visits)
            if agr.internal_state != all(res):
                agr._active_state_change(all(res))
            agr.state = all(res)

    @api.model
    def _check_expirations(self):
        # _logger.info('Checking access group expirations...')

        expired_records = self.search_read([('state', '=', False), ('expiration', '<', fields.Datetime.now())], ['id'])
        # _logger.info('Expired records: %d', len(expired_records))

        future_records = self.search_read([('state', '=', False), ('activate_on', '>', fields.Datetime.now())], ['id'])
        # _logger.info('Future records: %d', len(future_records))

        active_records = self.search_read([
            ('state', '=', True),
            '|',
            ('expiration', '=', False),
            ('expiration', '>', fields.Datetime.now())],
            ['id'])
        # _logger.info('Active records: %d', len(active_records))

        finished_count_records = self.search_read([
            ('state', '=', False),
            ('visits_counting', '=', True)],
            fields=['id', 'permitted_visits', 'visits_counter']
        )
        finished_count_records = [{'id': r['id']} for r in finished_count_records if
                                  r['permitted_visits'] == r['visits_counter']]
        # _logger.info('Active records: %d', len(active_records))

        records_for_check = self.search([
            ('id',
             'not in',
             [r['id'] for r in expired_records + future_records + active_records + finished_count_records])
        ])
        # _logger.info('Records for check: %d', len(records_for_check))

        records_for_check._compute_state()

    def filter_by_door(self, door_id, active_only=True):
        res = self.env[self._name]
        if active_only:
            return self.filtered(
                lambda agr: door_id in agr.access_group_id.door_ids.mapped('door_id') and agr.state)
        else:
            return self.filtered(
                lambda agr: door_id in agr.access_group_id.door_ids.mapped('door_id'))

    def _filter_active(self, dt=None):
        res = self.env[self._name]
        for_date = dt or fields.Datetime.now()
        for agcr in self:
            if agcr.activate_on <= for_date and (
                    not agcr.expiration or agcr.expiration > for_date):
                res += agcr
        return res

    def _filter_inactive(self):
        return self - self._filter_active()

    def ag_ready(self):
        res = []
        for ag in self:
            res.append(ag.activate_on and ag.activate_on <= fields.Datetime.now() or True)
            res.append(ag.expiration and ag.expiration > fields.Datetime.now() or True)
        return len(res) > 0 and all(res) or False

    def write(self, vals):
        super().write(vals)
        if set(vals.keys()).intersection(
                set(['activate_on', 'expiration', 'visits_counting', 'permitted_visits', 'visits_counter'])):
            self.mapped('state')


class HrRfidAccessGroupEmployeeRel(models.Model):
    _name = 'hr.rfid.access.group.employee.rel'
    _description = 'Relation between access groups and employees'
    _inherit = ['hr.rfid.access.group.rel']

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )

    @api.constrains('access_group_id', 'employee_id', 'activate_on', 'expiration')
    def _check_constrains_contacts(self):
        employee_ids = self.mapped('employee_id')
        for p in employee_ids:
            p_rel_ids = self.search([('employee_id', '=', p.id)])
            for ag_id in p_rel_ids.mapped('access_group_id'):
                rel_ranges = [(rel.activate_on, rel.expiration) for rel in
                              p_rel_ids.filtered(lambda ag: ag.access_group_id == ag_id)]
                if _check_overlap(rel_ranges):
                    raise ValidationError(
                        _('Overlap found between access group(%s) active period ranges for (%s)', ag_id.name, p.name))

    def _deactivate(self):
        for rel in self:
            cards = rel.employee_id.hr_rfid_card_ids.filtered(lambda c: c.card_ready())
            doors = rel.access_group_id.all_door_ids.mapped('door_id')
            self.env['hr.rfid.card.door.rel']._remove_cards(cards, doors)
            # for card in cards:
            #     for door in doors:
            #         self.env['hr.rfid.card.door.rel'].check_relevance_slow(card, door)

    def _activate(self):
        for rel in self:
            cards = rel.employee_id.hr_rfid_card_ids.filtered(lambda c: c.card_ready())
            for card in cards:
                self.env['hr.rfid.card.door.rel'].update_card_rels(card, rel.access_group_id)

    @api.model_create_multi
    def create(self, vals_list):
        # card_door_rel_env = self.env['hr.rfid.card.door.rel']

        records = super(HrRfidAccessGroupEmployeeRel, self).create(vals_list)
        records.mapped('employee_id').check_access_group()
        records.mapped('state')  # recalc new states

        return records

    def write(self, vals):
        if 'employee_id' in vals:
            raise exceptions.ValidationError('Cannot change the employee of the relation!')
        card_door_rel_env = self.env['hr.rfid.card.door.rel']
        for rel in self:
            old_acc_gr = rel.access_group_id
            super(HrRfidAccessGroupEmployeeRel, rel).write(vals)
            new_acc_gr = rel.access_group_id

            rel.employee_id.check_access_group()

            if new_acc_gr != old_acc_gr:
                # Potentially remove old rels
                cards = rel.employee_id.hr_rfid_card_ids
                doors = old_acc_gr.all_door_ids.mapped('door_id')
                for card in cards:
                    for door in doors:
                        card_door_rel_env.check_relevance_slow(card, door)

                # Potentially create new rels
                cards = rel.employee_id.hr_rfid_card_ids
                for card in cards:
                    card_door_rel_env.update_card_rels(card, new_acc_gr)

    def unlink(self):
        self._deactivate()
        super(HrRfidAccessGroupEmployeeRel, self).unlink()


class HrRfidAccessGroupContactRel(models.Model):
    _name = 'hr.rfid.access.group.contact.rel'
    _description = 'Relation between access groups and contacts'
    _inherit = ['hr.rfid.access.group.rel']

    contact_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
    )

    @api.constrains('access_group_id', 'contact_id', 'activate_on', 'expiration')
    def _check_constrains_contacts(self):
        partner_ids = self.mapped('contact_id')
        for p in partner_ids:
            p_rel_ids = self.search([('contact_id', '=', p.id)])
            for ag_id in p_rel_ids.mapped('access_group_id'):
                rel_ranges = [(rel.activate_on, rel.expiration) for rel in
                              p_rel_ids.filtered(lambda ag: ag.access_group_id == ag_id)]
                if _check_overlap(rel_ranges):
                    raise ValidationError(
                        _('Overlap found between access group(%s) active period ranges for (%s)', ag_id.name, p.name))

    def _deactivate(self):
        for rel in self:
            cards = rel.contact_id.hr_rfid_card_ids.filtered(lambda c: c.card_ready())
            doors = rel.access_group_id.all_door_ids.mapped('door_id')
            self.env['hr.rfid.card.door.rel']._remove_cards(cards, doors)
            # for card in cards:
            #     for door in doors:
            #         self.env['hr.rfid.card.door.rel'].check_relevance_slow(card, door)

    def _activate(self):
        for rel in self:
            cards = rel.contact_id.hr_rfid_card_ids.filtered(lambda c: c.card_ready())
            for card in cards:
                self.env['hr.rfid.card.door.rel'].update_card_rels(card, rel.access_group_id)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(HrRfidAccessGroupContactRel, self).create(vals_list)
        records.mapped('contact_id').check_access_group()
        records._compute_state()
        # records.mapped('state') # recalc new states
        # records._filter_active()._activate()

        return records

    def write(self, vals):
        if 'contact_id' in vals:
            raise exceptions.ValidationError('Cannot change the employee of the relation!')
        card_door_rel_env = self.env['hr.rfid.card.door.rel']
        for rel in self:
            old_acc_gr = rel.access_group_id
            super(HrRfidAccessGroupContactRel, rel).write(vals)
            new_acc_gr = rel.access_group_id

            rel.contact_id.check_access_group()

            if (new_acc_gr != old_acc_gr):
                # Potentially remove old rels
                cards = rel.contact_id.hr_rfid_card_ids
                doors = old_acc_gr.all_door_ids.mapped('door_id')
                for card in cards:
                    for door in doors:
                        card_door_rel_env.check_relevance_slow(card, door)

                # Potentially create new rels
                cards = rel.contact_id.hr_rfid_card_ids
                for card in cards:
                    card_door_rel_env.update_card_rels(card, new_acc_gr)

    def unlink(self):
        self._deactivate()
        super(HrRfidAccessGroupContactRel, self).unlink()


class HrRfidAccessGroupWizard(models.TransientModel):
    _name = 'hr.rfid.access.group.wizard'
    _description = 'Add or remove doors to the access group'

    def _default_acc_gr(self):
        return self.env['hr.rfid.access.group'].browse(self._context.get('active_ids'))

    def _default_acc_gr_doors(self):
        acc_gr = self._default_acc_gr()
        return acc_gr.door_ids.mapped('door_id')

    acc_gr_id = fields.Many2one(
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
        default=lambda self: self.env['hr.rfid.time.schedule'].search([], limit=1, order='number')[0].id,
    )

    alarm_rights = fields.Boolean(
        help='Give alarm rights for this door. The user can Arm/Disarm door.',
        default=False,
        required=True
    )

    def add_doors(self):
        self.acc_gr_id.add_doors(self.door_ids, self.time_schedule_id, self.alarm_rights)

    def del_doors(self):
        self.acc_gr_id.del_doors(self.door_ids)
