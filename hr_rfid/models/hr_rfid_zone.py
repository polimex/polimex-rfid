# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, http
import logging

from odoo.addons.hr_rfid.models.hr_rfid_event_user import HrRfidUserEvent

_logger = logging.getLogger(__name__)


class HrRfidZone(models.Model):
    _name = 'hr.rfid.zone'
    _description = 'Zone'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Zone Name',
        tracking=True,
        required=True,
    )
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 default=lambda self: self.env.company)

    anti_pass_back = fields.Boolean(
        string='Anti-Pass Back',
        help="Disallow people in the zone to enter again, or leave if they're not in it",
        tracking=True,
    )

    log_out_on_exit = fields.Boolean(
        string='Logout on Exit',
        help='Whether to log people out on exit',
        tracking=True,
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        'hr_rfid_zone_door_rel',
        'zone_id',
        'door_id',
        string='Doors',
        help='Doors in this zone',
        tracking=True,
    )

    permitted_department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Permitted departments for this zone. If empty, it applies to all departments.',
        tracking=True,
    )
    permitted_employee_category_ids = fields.Many2many(
        'hr.employee.category',
        string='Tags',
        help='Permitted employee tags for this zone. If empty, it applies to all employees.',
        tracking=True,
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Employees currently in this zone',
    )

    contact_ids = fields.Many2many(
        'res.partner',
        string='Contacts',
        help='Contacts currently in this zone',
    )

    notification_ids = fields.One2many(
        comodel_name='hr.rfid.notification',
        inverse_name='zone_id',
        string='Notifications',
        tracking=True,
    )

    employee_count = fields.Char(compute='_compute_counts')
    contact_count = fields.Char(compute='_compute_counts')

    def _check_employee_permit(self, employee_id):
        res = []
        for z in self:
            if z.permitted_department_ids:
                res.append(employee_id.id in z.permitted_department_ids.member_ids.ids)
            if z.permitted_employee_category_ids:
                # res.append(set(employee_id.category_ids.ids) & set(z.permitted_employee_category_ids.ids) is not {})
                res.append(bool(set(employee_id.category_ids.ids) & set(z.permitted_employee_category_ids.ids)))
        if len(res) > 0:
            return all(res)
        else:
            return True

    @api.depends('employee_ids', 'contact_ids')
    def _compute_counts(self):
        for z in self:
            z.employee_count = len(z.employee_ids)
            z.contact_count = len(z.contact_ids)

    def person_went_through(self, event):
        person = event.employee_id or event.contact_id

        if not person:
            return

        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            person_left = (is_employee and person in zone.employee_ids) \
                          or (not is_employee and person in zone.contact_ids)
            if person_left:
                zone.person_left(person, event)
            else:
                zone.person_entered(person, event)

    def person_entered(self, person, event):
        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            if is_employee and not zone._check_employee_permit(person):
                continue
            if (is_employee and person in zone.employee_ids) \
                    or (not is_employee and person in zone.contact_ids):
                continue

            if zone.anti_pass_back:
                zone._change_apb_state(person, event, enable_exiting=True)

            if is_employee:
                zone.employee_ids = zone.employee_ids + person
            else:
                zone.contact_ids = zone.contact_ids + person

    def person_left(self, person, event=None):
        is_employee = isinstance(person, type(self.env['hr.employee']))

        for zone in self:
            if is_employee and not zone._check_employee_permit(person):
                continue
            if (is_employee and person not in zone.employee_ids) \
                    or (not is_employee and person not in zone.contact_ids):
                continue

            if event and zone.anti_pass_back or len(zone.door_ids.filtered("apb_mode")) > 0:
                zone._change_apb_state(person, event, enable_exiting=False)

            if zone.log_out_on_exit:
                HrRfidZone._log_person_out(zone, person)

            if is_employee:
                zone.employee_ids = zone.employee_ids - person
            else:
                zone.contact_ids = zone.contact_ids - person

    def clear_employees(self):
        for zone in self:
            for emp in zone.employee_ids:
                zone.person_left(emp, self.env['hr.rfid.event.user'])
            # zone.employee_ids = self.env['hr.employee']

    def clear_contacts(self):
        for zone in self:
            for cont in zone.contact_ids:
                zone.person_left(cont, self.env['hr.rfid.event.user'])
            # zone.contact_ids = self.env['res.partner']

    def _change_apb_state(self, person, event=None, enable_exiting=True):
        for zone in self:
            if not event:
                doors = zone.door_ids.filtered(lambda d: d.apb_mode)
            else:
                doors = zone.door_ids.filtered(lambda d: d.apb_mode) - event.door_id

            for card in person.hr_rfid_card_ids:
                doors.change_apb_flag(card, enable_exiting)

    def _log_person_out(self, person):
        session_storage = http.root.session_store
        sids = session_storage.list()
        person.log_person_out(sids)

    def employee_in_current_zone(self):
        self.ensure_one()
        return {
            'name': _('Employees in {}').format(self.name),
            'view_mode': 'kanban,form',
            'res_model': 'hr.employee',
            'domain': [('id', 'in', [i.id for i in self.employee_ids])],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         Buy Odoo Enterprise now to get more providers.
            #     </p>'''),
        }

    def contact_in_current_zone(self):
        self.ensure_one()
        return {
            'name': _('Contacts in {}').format(self.name),
            'view_mode': 'kanban,form',
            'res_model': 'res.partner',
            'domain': [('id', 'in', [i.id for i in self.contact_ids])],
            'type': 'ir.actions.act_window',
            # 'help': _('''<p class="o_view_nocontent">
            #         Buy Odoo Enterprise now to get more providers.
            #     </p>'''),
        }

    def _add_and_fix(self, z):
        employees_in_zone = self.env['hr.employee']
        for e in self.env['hr.employee'].search([('hr_rfid_card_ids', '!=', False)]):
            # _logger.info('Processing employee %s' % e.name)
            empl_zone_door_ids = e.get_doors() & z.door_ids
            if empl_zone_door_ids:
                e_event = self.env['hr.rfid.event.user'].search([
                    ('employee_id', '=', e.id),
                    ('door_id', 'in', empl_zone_door_ids.ids)
                ], limit=1)
                in_zone = e_event and e_event.reader_id.reader_type == '0'
                z._change_apb_state(person=e, enable_exiting=in_zone)
                if in_zone:
                    employees_in_zone += e
        z.employee_ids = employees_in_zone
        # Contacts
        contacts_in_zone = self.env['res.partner']
        for e in self.env['res.partner'].search([('hr_rfid_card_ids', '!=', False)]):
            # _logger.info('Processing partner %s' % e.name)
            contacts_zone_door_ids = e.get_doors() & z.door_ids
            if contacts_zone_door_ids:
                e_event = self.env['hr.rfid.event.user'].search([
                    ('contact_id', '=', e.id),
                    ('door_id', 'in', contacts_zone_door_ids.ids)
                ], limit=1)
                in_zone = e_event and e_event.reader_id.reader_type == '0'
                z._change_apb_state(person=e, enable_exiting=in_zone)
                if in_zone:
                    contacts_in_zone += e

        z.contact_ids = contacts_in_zone

    @api.model_create_multi
    def create(self, vals_list):
        res = self
        for vals in vals_list:
            z = super().create(vals)
            if vals.get('anti_pass_back', False):
                z.door_ids.apb_mode = True
                self._add_and_fix(z)
            res += z
        return res

    def write(self, vals):
        apb_changed = 'anti_pass_back' in vals.keys()
        doors_changed = 'door_ids' in vals.keys()
        new_apb = vals.get('anti_pass_back', None)
        res = []
        for z in self:
            old_door_ids = z.door_ids
            old_apb = z.anti_pass_back
            # Clear employees in zone
            if apb_changed or (z.anti_pass_back and doors_changed):
                vals['employee_ids'] = [(5, 0, 0)]
                vals['contact_ids'] = [(5, 0, 0)]
            res.append(super(HrRfidZone, z).write(vals))
            new_door_ids = z.door_ids

            if apb_changed or (z.anti_pass_back and doors_changed):
                if new_door_ids != old_door_ids:
                    excluded_door_ids = old_door_ids - new_door_ids
                    # excluded_door_ids = new_door_ids.filtered(lambda d: d.id not in old_door_ids.ids)
                else:
                    excluded_door_ids = self.env['hr.rfid.door']
                included_door_ids = new_door_ids - excluded_door_ids
                # Apply new APB to all doors
                included_door_ids.apb_mode = new_apb
                excluded_door_ids.apb_mode = False
                if new_apb:
                    self._add_and_fix(z)

        return all(res)

    def process_event(self, event):
        is_employee_event = isinstance(event, HrRfidUserEvent) and event.employee_id
        for zone in self:
            for notification in zone.notification_ids:
                if (
                        notification.user_event == event.event_action or notification.system_event == event.event_action) and (
                        not is_employee_event or self._check_employee_permit(event.employee_id)):
                    notification.process_event(event)


class HrRfidZoneDoorsWizard(models.TransientModel):
    _name = 'hr.rfid.zone.doors.wiz'
    _description = 'Add or remove doors to the zone'

    def _default_zone(self):
        return self.env['hr.rfid.zone'].browse(self._context.get('active_ids'))

    zone_id = fields.Many2one(
        'hr.rfid.zone',
        string='Zone',
        required=True,
        default=_default_zone,
    )

    door_ids = fields.Many2many(
        'hr.rfid.door',
        string='Doors',
        help='Which doors to add to the access group',
        required=True,
    )

    def add_doors(self):
        self.ensure_one()
        self.zone_id.door_ids = self.zone_id.door_ids + self.door_ids

    def remove_doors(self):
        self.ensure_one()
        self.zone_id.door_ids = self.zone_id.door_ids - self.door_ids
