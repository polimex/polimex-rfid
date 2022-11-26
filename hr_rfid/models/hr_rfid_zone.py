# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, http


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
    )

    log_out_on_exit = fields.Boolean(
        string='Logout on Exit',
        help='Whether to log people out on exit',
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

    employee_count = fields.Char(compute='_compute_counts')
    contact_count = fields.Char(compute='_compute_counts')

    @api.depends('employee_ids','contact_ids')
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
            zone.employee_ids = self.env['hr.employee']

    def clear_contacts(self):
        for zone in self:
            for cont in zone.contact_ids:
                zone.person_left(cont, self.env['hr.rfid.event.user'])
            zone.contact_ids = self.env['res.partner']

    def _change_apb_state(self, person, event, enable_exiting=True):
        for zone in self:
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
